import tqdm
import jdatetime
import validators
import urllib.parse

from datetime import date
from collections import defaultdict
from utils.web.url import UrlManipulator
from utils.web.selenium import web_driver, DriverHandler
from utils.datetime import process_jalali_date, fa_to_en, dt_to_str

from django.conf import settings
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement


class MyCodalDocumentScraper:
    # todo: change so that only 3, 6, 9, and 12 month periods are fetched
    # todo: change so that each category is covered instead of just using text lookups

    # todo: اصلاحیه
    # todo: empty pdf
    # todo: colliding rows
    # todo: unique key is mycodal_statement_link -> statement_id
    # todo: migrate to databases...
    # todo: create json files and create modules to use them as cache to reduce database overhead.
    #  django has cache framework. it also supports file-based caching.

    main_panel_xpath = '//body/div[@id="content"]/div/section[@class="filter-company"]/div'
    nav_bar_xpath = f'{main_panel_xpath}/div[@id="pagination"]'
    rows_xpath = f'{main_panel_xpath}/div[@class="row "]/div/table/tbody/tr[@class="odd gradeX"]'
    max_page_xpath = f'{nav_bar_xpath}/div/div/ul/li[last()]/a'

    H = DriverHandler

    @classmethod
    def scrape(cls, minimized: bool = True, from_date: date = None, to_date: date = None):
        if minimized:
            cls.scrape_minimized(from_date, to_date)
        else:
            cls.scrape_maximized()

    @classmethod
    def scrape_maximized(cls):
        from resources.tsetmc.controller import TseTmcController
        driver = web_driver()
        data = defaultdict(list)
        for index, details in tqdm.tqdm(TseTmcController.stocks_details(force_reload=True, codal=True).items(),
                                        desc='scraping mycodal documents'):
            mycodal_id = details['codal']['mycodal_id']
            from_date = cls.get_from_date(codal_info=details, minimized=True)
            url = cls.url(mycodal_ids=[mycodal_id], from_date=from_date)

            max_page = cls.get_max_page_number(driver, url, url_kwargs={'page_number': 1})
            for page in range(1, max_page + 1):
                data[mycodal_id].extend(cls.scrape_page(driver, url, url_kwargs={'page_number': page}))

        driver.close()
        cls.update_last_updated_date_for_stocks(data)
        from resources.codal.controller import CodalController
        CodalController.append_data_entry(data)

    @classmethod
    def scrape_minimized(cls, from_date: date = None, to_date: date = None):
        driver = web_driver()
        data: list = list()

        if from_date is None:
            from_date = cls.get_from_date(minimized=True, minimum=jdatetime.date(1398, 1, 1).togregorian())

        # max chunk size = 30
        # good chink size = 20
        urls = cls.chunk_mycodal_ids_to_urls(20)
        urls = [cls.url(input_url=url, from_date=from_date, to_date=to_date) for url in urls]
        chunk_index = 1
        for url in tqdm.tqdm(urls, desc='chunking mycodal_ids'):
            max_page = cls.get_max_page_number(driver, url, url_kwargs={'page_number': 1})
            for page in tqdm.tqdm(range(1, max_page + 1),
                                  desc=f'scraping docs for {chunk_index}th chunk'):
                data.extend(cls.scrape_page(driver, url, {'page_number': page}, with_mycodal_id=True))
            chunk_index += 1

        data: dict = cls.indexify_flat_doc_list(data)
        driver.close()
        cls.update_last_updated_date_for_stocks(data)
        from resources.codal.controller import CodalController
        CodalController.append_data_entry(data)

    @classmethod
    def url(cls, input_url: str = None, mycodal_ids: list[str] = None, from_date: date = None, to_date: date = None) \
            -> str:
        url = settings.MYCODAL_DOCUMENT_LIST_URL if input_url is None else input_url
        parameters: list[tuple] = list()
        if any(map(lambda x: x is not None, [mycodal_ids, from_date, to_date])):
            if from_date is not None:
                parameters.append(('from_date',
                                   jdatetime.date.fromgregorian(date=from_date).strftime('%Y/%m/%d')))

            if to_date is not None:
                parameters.append(('to_date',
                                   jdatetime.date.fromgregorian(date=to_date).strftime('%Y/%m/%d')))

            if mycodal_ids is not None:
                for mid in mycodal_ids:
                    parameters.append(('symbol', mid))

        parameters.extend([
            ('title', 'صورت‌های مالی'),
            ('statement_type', '104'),
            ('per_page', '100'),
            ('page', '{page_number}')
        ])
        return UrlManipulator.querify(url, parameters)

    @classmethod
    def get_from_date(cls, codal_info: dict = None, minimized: bool = False, maximized: bool = False,
                      minimum: date = None) -> date:
        if codal_info is not None and 'doc_last_updated' in codal_info:
            from_date = codal_info['doc_last_updated']
        elif maximized:
            from resources.tsetmc.controller import TseTmcController
            from_date = TseTmcController.get_max_codal_doc_last_updated()
        elif minimized:
            if minimum is not None:
                from_date = minimum
            else:
                from_date = date(1000, 1, 1)
        else:
            return  # noqa

        return from_date

    @classmethod
    def update_last_updated_date_for_stocks(cls, documents: dict):
        from resources.tsetmc.controller import TseTmcController
        TseTmcController.append_data_entry(
            {index: {'docs_last_updated': date.today().strftime('%Y/%m/%d')}
             for index, doclist in documents.items()}
        )

    @classmethod
    def indexify_flat_doc_list(cls, doc_list: list[dict]) -> dict:
        """Presuming that doc_list is a list of docs, each doc containing a different 'mycodal_id'.
        Output would remove the 'mycodal_id' from each doc, but it would be dictionary with mycodal_id as keys."""
        from resources.tsetmc.controller import TseTmcController
        tmp = defaultdict(list)
        for doc in doc_list:
            mycodal_id = doc['mycodal_id']
            del doc['mycodal_id']
            index = TseTmcController.mycodal_id_to_indexes()[mycodal_id]
            tmp[index].append(doc)

        return tmp

    @classmethod
    def chunk_mycodal_ids_to_urls(cls, chunk_size) -> list[str]:
        from resources.tsetmc.controller import TseTmcController
        mycodal_ids = list(TseTmcController.mycodal_id_to_indexes().keys())
        chunks = [mycodal_ids[i:i + chunk_size] for i in range(0, len(mycodal_ids), chunk_size)]
        return [cls.url(mycodal_ids=chunk) for chunk in chunks]

    @classmethod
    def get_max_page_number(cls, driver: WebDriver, url: str, url_kwargs: dict = None) -> int:
        if url_kwargs is not None:
            url = url.format(**url_kwargs)
        cls.H.get_url(driver, url=url)

        max_page = cls.H.get_attr(cls.H.get_element(driver, xpath=cls.max_page_xpath), attr='text', prop=True)
        if cls.H.validate(max_page, tipe=str):
            return int(max_page.replace('»', '').strip())
        else:
            return 1

    @classmethod
    def scrape_page(cls, driver: WebDriver, url: str, url_kwargs: dict = None, with_mycodal_id=False) -> list[dict]:
        page_data = list()
        if url_kwargs is not None:
            url = url.format(**url_kwargs)
        cls.H.get_url(driver, url=url)
        if not cls.H.wait_until(driver, 180, cls.rows_xpath):
            return list()

        rows = cls.H.get_element(driver, xpath=cls.rows_xpath, many=True)
        for row in rows:
            kwargs = cls.scrape_row(row)
            if with_mycodal_id:
                cls.H.add_validated(kwargs, 'mycodal_id',
                                    cls.H.get_attr(cls.H.get_element(row, xpath='./td[1]/a'), attr='href'),
                                    tipe=str, validation=validators.url,
                                    post=lambda x: [i for i in urllib.parse.urlparse(x).path.split('/') if i][-1])

            warning = cls.H.get_element(row, xpath='./td[3]/a/img')
            if cls.H.validate(warning):
                continue

            if not all([key in kwargs for key in
                        ['pdf_link', 'release_date', 'yearly', 'period_length', 'aggregated',
                         'audited', 'period_end_date', 'mycodal_id', 'title']]):
                continue

            page_data.append(kwargs)

        return page_data

    @classmethod
    def scrape_row(cls, row: WebElement) -> dict:
        kwargs = dict()
        title = cls.H.get_element(row, xpath='./td[4]/a')
        cls.H.add_validated(kwargs, 'mycodal_statement_link', cls.H.get_attr(title, attr='href'),
                            tipe=str, validation=validators.url)
        title = cls.H.get_attr(title, attr='text', prop=True)
        if cls.H.validate(title, tipe=str, value_exc='-'):
            try:
                kwargs.update(cls.process_title(title))
            except Exception:
                pass

        cls.H.add_validated(kwargs, 'release_date',
                            cls.H.get_attr(cls.H.get_element(row, xpath='./td[6]/span'),
                                           attr='text', prop=True), tipe=str,
                            validation=lambda x: process_jalali_date(x),
                            post=lambda x: dt_to_str(process_jalali_date(x)))

        cls.H.add_validated(kwargs, 'pdf_link',
                            cls.H.get_attr(cls.H.get_element(row, xpath='./td[8]/a[5]'), attr='href'),
                            tipe=str, validation=validators.url)

        return kwargs

    @classmethod
    def process_title(cls, title: str) -> dict:
        title_kwargs = {
            'yearly': False,
            'period_length': 0,
            'period_end_date': date(1000, 1, 1),
            'aggregated': False,
            'audited': False,
            'title': title
        }

        if 'حسابرسی شده' in title:
            title_kwargs['audited'] = True

        if 'سال مالی' in title:
            title_kwargs['yearly'] = True
            title_kwargs['period_length'] = 12
        elif 'میاندوره‌ای' in title:
            interval_length_fa: str = \
                title[title.find('دوره ') + len('دوره'):title.find('ماهه')].strip()
            title_kwargs['period_length'] = int(fa_to_en(interval_length_fa))

        if 'منتهی به' in title:
            ending_date_text = ''
            for string in title.split(' '):
                temp = string
                for fa_digit in list(range(ord('۰'), ord('۹') + 1)) + list(range(ord('0'), ord('9') + 1)):
                    temp = temp.replace(chr(fa_digit), '')
                if temp == '//':
                    ending_date_text = string
                    break

            ending_date = process_jalali_date(ending_date_text)
            title_kwargs['period_end_date'] = dt_to_str(ending_date)

        if 'تلفیقی' in title:
            title_kwargs['aggregated'] = True

        return title_kwargs
