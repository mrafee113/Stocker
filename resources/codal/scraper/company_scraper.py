import tqdm
import termcolor
import validators
import urllib.parse
import email_validator

from django.conf import settings
from utils.datetime import fa_to_en
from utils.web.selenium import DriverHandler, web_driver
from selenium.webdriver.remote.webelement import WebElement


class MyCodalCompanyScraper:
    H = DriverHandler

    @classmethod
    def scrape(cls):
        tickers: list[dict] = cls.scrape_publishers_list()
        cls.scrape_publishers_detail(tickers)
        tickers: dict = cls.post_process(tickers)
        cls.write_to_file(tickers)

    @classmethod
    def write_to_file(cls, tickers: dict):
        from resources.tsetmc.controller import TseTmcController
        tickers = {index: {'codal': details} for index, details in tickers.items()}
        TseTmcController.append_data_entry(tickers)

    @classmethod
    def post_process(cls, tickers: list[dict]) -> dict:
        for ticker in tickers:
            ticker['prune'] = False
            if 'index_kwargs' not in ticker:
                ticker['prune'] = True
            else:
                ticker.update(ticker['index_kwargs'])
                del ticker['index_kwargs']

            necessary_keys = ['mycodal_id', 'ISIN']
            for key in necessary_keys:
                if key not in ticker:
                    ticker['prune'] = True

            if ticker['prune']:
                continue

            if 'symbol' in ticker:
                ticker['codal_info_link'] = settings.CODAL_INFO_URL.format(symbol=ticker["symbol"].replace(" ", "%20"))
                ticker['codal_reports_link'] = settings.CODAL_REPORTS_URL.\
                    format(symbol=ticker["symbol"].replace(" ", "%20"))
            ticker['mycodal_reports_link'] = settings.MYCODAL_REPORTS_URL.format(mycodal_id=ticker['mycodal_id'])

        for idx in sorted([idx for idx, kw in enumerate(tickers) if kw['prune']], reverse=True):
            # decreasing list index
            del tickers[idx]
        for ticker in tickers:
            del ticker['prune']
        if not tickers:
            return dict()

        isins = [ticker['ISIN'] for ticker in tickers]
        if len(isins) != len(set(isins)):
            print(termcolor.colored('WARNING! there are duplicates in isin of tickers.', 'yellow'))

        #  also create dictionary(ISIN:kwargs)
        from resources.tsetmc.controller import TseTmcController
        isin_dict = dict()
        for ticker in tickers:
            isin_dict[ticker['ISIN']] = ticker
        del tickers

        output = dict()
        isins_to_indexes = TseTmcController.isins_to_indexes(force_reload=True)
        for isin, details in isin_dict.items():
            if isin not in isins_to_indexes:
                print(termcolor.colored(f'WARNING! isin {isin} was not available in tsetmc.', 'yellow'))
                continue
            output[isins_to_indexes[isin]] = details

        return output

    @classmethod
    def scrape_publishers_list(cls) -> list[dict]:
        driver = web_driver()
        url = settings.MYCODAL_COMPANY_LIST_URL
        driver.get(url.format(page_number=1))
        data = list()

        main_panel_xpath = '//body/div[@id="content"]/div[@class="index-bg"]/section[@class="filter-company"]' \
                           '/div/div/div[@class="col-12 "]'

        max_page_xpath = f'{main_panel_xpath}/div[@id="pagination"]/div/div/ul/li[last()]/a'
        max_page = cls.H.get_attr(cls.H.get_element(driver, raise_exception=True, xpath=max_page_xpath),
                                  raise_exception=True, attr='text', prop=True)
        max_page = int(max_page.replace('»', '').strip())
        for page in tqdm.tqdm(range(1, max_page + 1), desc='scraping publishers list'):
            rows_xpath = f'{main_panel_xpath}/table[@class="table-bordered table-striped rwd-table ' \
                         f'table-hover publisher-table"]' \
                         f'/tbody[@id="template-container"]/tr[@class="gradeX"]'
            rows = cls.H.get_element(driver, xpath=rows_xpath, many=True)
            if not cls.H.validate(rows, validation=lambda x: len(x) > 0):
                driver.get(url.format(page_number=page + 1))
                continue

            for row in rows:
                data.append(cls.scrape_publishers_list_row(row))

            if page == max_page:
                break
            driver.get(url.format(page_number=page + 1))

        driver.close()
        return data

    @classmethod
    def scrape_publishers_list_row(cls, row: WebElement) -> dict:
        kwargs = dict()

        symbol = cls.H.get_element(row, xpath='./td[1]/a')
        mycodal_info_link = cls.H.get_attr(symbol, attr='href')
        cls.H.add_validated(kwargs, 'mycodal_info_link', mycodal_info_link, tipe=str, validation=validators.url)
        cls.H.add_validated(kwargs, 'mycodal_id', mycodal_info_link, tipe=str, validation=validators.url,
                            post=lambda x: [i for i in urllib.parse.urlparse(x).path.split('/') if i][-1])

        symbol = cls.H.get_attr(symbol, attr='text', prop=True)
        cls.H.add_validated(kwargs, 'symbol', symbol, tipe=str,
                            post=lambda x: x.strip())

        company_name = cls.H.get_attr(cls.H.get_element(row, xpath='./td[2]/span/span'),
                                      attr='text', prop=True)
        cls.H.add_validated(kwargs, 'company_name', company_name, tipe=str, value_exc='-')

        company_type = cls.H.get_attr(cls.H.get_element(row, xpath='./td[4]/span'),
                                      attr='text', prop=True)
        cls.H.add_validated(kwargs, 'company_type', company_type, tipe=str, value_exc='-')

        acceptance_type = cls.H.get_attr(cls.H.get_element(row, xpath='./td[5]/span'),
                                         attr='text', prop=True)
        cls.H.add_validated(kwargs, 'acceptance_type', acceptance_type, tipe=str, value_exc='-')

        industry_group = cls.H.get_attr(cls.H.get_element(row, xpath='./td[6]/span'),
                                        attr='text', prop=True)
        cls.H.add_validated(kwargs, 'industry_group', industry_group, tipe=str, value_exc='-')

        company_website = cls.H.get_attr(cls.H.get_element(row, xpath='./td[8]/a'),
                                         attr='href')
        cls.H.add_validated(kwargs, 'company_website', company_website, tipe=str, none=False,
                            validation=validators.url)

        return kwargs

    @classmethod
    def scrape_publishers_detail(cls, tickers: list[dict]):
        driver = web_driver(headless=True)
        for data in tqdm.tqdm(tickers, desc='scraping publisher details'):
            if 'mycodal_info_link' not in data:
                continue

            driver.get(data['mycodal_info_link'])
            rows_xpath = '//body/div[@id="content"]/div/div/div/div[2]/div[@id="subcontent"]' \
                         '/div[@class=" detail-col "]/div/div/table/tbody/tr'
            rows = cls.H.get_element(driver, xpath=rows_xpath, many=True)
            cls.scrape_publisher_detail_index(data, rows)

            driver.get(urllib.parse.urljoin(data['mycodal_info_link'], 'board'))
            rows = cls.H.get_element(driver, xpath=rows_xpath, many=True)
            cls.scrape_publisher_detail_board_members(data, rows)

            driver.get(urllib.parse.urljoin(data['mycodal_info_link'], 'similar_publisher'))
            content_xpath = '//body/div[@id="content"]/div/div/div/div[2]/div[@id="subcontent"]' \
                            '//div[@class="similar_publishers"]/ul'
            content = cls.H.get_element(driver, xpath=content_xpath)
            if cls.H.validate(content):
                publishers = cls.H.get_element(content, xpath='./li/a', many=True)
                cls.scrape_publisher_detail_similars(data, publishers)

            driver.get(urllib.parse.urljoin(data['mycodal_info_link'], 'contact'))
            rows = cls.H.get_element(driver, xpath=rows_xpath, many=True)
            cls.scrape_publisher_detail_contact_info(data, rows)

        driver.close()

    @classmethod
    def scrape_publisher_detail_index(cls, data: dict, rows: list[WebElement]):
        kwargs = dict()
        for row in rows:
            tds = cls.H.get_element(row, xpath='./td', many=True)
            if len(tds) != 2:
                continue

            key, value = [cls.H.get_attr(td, attr='text', prop=True)
                          for td in tds]
            if key == 'مدیرعامل':
                cls.H.add_validated(kwargs, 'company_ceo', value, tipe=str, value_exc='-', post=lambda x: x.strip())
            elif key == 'مدیرمالی':
                cls.H.add_validated(kwargs, 'company_cfo', value, tipe=str, value_exc='-', post=lambda x: x.strip())
            elif key == 'ماهیت':
                cls.H.add_validated(kwargs, 'company_essence', value, tipe=str, value_exc='-', post=lambda x: x.strip())
            elif key == 'سرمایه ثبت شده':
                cls.H.add_validated(kwargs, 'company_registered_capital', value, tipe=str, value_exc='-',
                                    post=lambda x: int(fa_to_en(x.replace(',', '')).strip()))
            elif key == 'سرمایه ثبت نشده':
                cls.H.add_validated(kwargs, 'company_unregistered_capital', value, tipe=str, value_exc='-',
                                    post=lambda x: int(fa_to_en(x.replace(',', '')).strip()))
            elif key == 'کد ملی':
                cls.H.add_validated(kwargs, 'company_national_id', value, tipe=str, value_exc='-',
                                    post=lambda x: fa_to_en(x).strip())
            elif key == 'ISIC':
                cls.H.add_validated(kwargs, 'ISIC', value, tipe=str, value_exc='-',
                                    post=lambda x: fa_to_en(x).strip())
            elif key == 'ISIN':
                cls.H.add_validated(kwargs, 'ISIN', value, tipe=str, value_exc='-', post=lambda x: x.strip())
            elif key == 'پایان سال مالی':
                cls.H.add_validated(kwargs, 'company_financial_end_of_year', value, tipe=str, value_exc='--/--',
                                    post=lambda x: {'month': int(x.strip().split('/')[0]),
                                                    'day': int(x.strip().split('/')[1])})

        if kwargs:
            data['index_kwargs'] = kwargs

    @classmethod
    def scrape_publisher_detail_board_members(cls, data: dict, rows: list[WebElement]):
        members = list()
        for row in rows:
            tds = cls.H.get_element(row, xpath='./td', many=True)
            if len(tds) != 3:
                continue

            tds = [cls.H.get_attr(td, attr='text', prop=True) for td in tds]
            members.append({'institution': tds[0],
                            'representor': tds[1],
                            'post': tds[2]})

        data['board_of_directors'] = members

    @classmethod
    def scrape_publisher_detail_similars(cls, data: dict, publishers: list[WebElement]):
        publishers_data = list()
        for publisher in publishers:
            kwargs = dict()
            cls.H.add_validated(kwargs, 'name',
                                cls.H.get_attr(publisher, attr='text', prop=True),
                                tipe=str)
            href = cls.H.get_attr(publisher, attr='href')
            cls.H.add_validated(kwargs, 'mycodal_info_link', href, tipe=str, validation=validators.url)
            cls.H.add_validated(kwargs, 'mycodal_id', href, tipe=str, validation=validators.url,
                                post=lambda x: [i for i in urllib.parse.urlparse(x).path.split('/') if i][-1])

            publishers_data.append(kwargs)

        data['similar_publishers'] = publishers_data

    @classmethod
    def scrape_publisher_detail_contact_info(cls, data: dict, rows: list[WebElement]):
        kwargs = dict()
        for row in rows:
            tds = cls.H.get_element(row, xpath='./td', many=True)
            if len(tds) != 2:
                continue

            key, value = [cls.H.get_attr(td, attr='text', prop=True) for td in tds]
            if key == 'آدرس کارخانه ':
                cls.H.add_validated(kwargs, 'company_address', value, tipe=str, value_exc='-',
                                    post=lambda x: x.strip())
            elif key == 'تلفن کارخانه ':
                cls.H.add_validated(kwargs, 'company_phone', value, tipe=str, value_exc='-',
                                    post=lambda x: fa_to_en(x.strip()))
            elif key == 'آدرس امور سهام ':
                cls.H.add_validated(kwargs, 'stock_affairs_address', value, tipe=str, value_exc='-',
                                    post=lambda x: x.strip())
            elif key == 'تلفن امور سهام ':
                cls.H.add_validated(kwargs, 'stock_affairs_phone', value, tipe=str, value_exc='-',
                                    post=lambda x: fa_to_en(x.strip()))
            elif key == 'آدرس دفتر مرکزی ':
                cls.H.add_validated(kwargs, 'main_office_address', value, tipe=str, value_exc='-',
                                    post=lambda x: x.strip())
            elif key == 'تلفن دفتر مرکزی ':
                cls.H.add_validated(kwargs, 'main_office_phone', value, tipe=str, value_exc='-',
                                    post=lambda x: fa_to_en(x.strip()))
            elif key == 'ایمیل':
                cls.H.add_validated(kwargs, 'email', value, tipe=str, value_exc='-',
                                    validation=email_validator.validate_email, post=lambda x: x.strip())

        if kwargs:
            data['contact_info'] = kwargs
