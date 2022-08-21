import requests
import validators
import urllib.parse

from functools import partial
from lxml import html
from scrapy.spiders import Spider
from itemadapter import ItemAdapter

from django.conf import settings
from scrapy.selector import Selector
from scrapy.http.request import Request
from scrapy.http.response import Response
from django.utils.functional import cached_property

from utils.web.url import UrlManipulator
from utils.web import get_random_user_agent
from utils.web.scrapy import ScrapyHandler as H
from .items import MycodalCompanyItem, MycodalCompanyItemLoader


# todo: add state status for emergency
# todo: migrate all urls to django.settings
class MycodalCompanySpider(Spider):
    name = 'mycodal_company_spider'
    allowed_domains = ['my.codal.ir']
    custom_settings = {
        'EXTENSIONS': {
            'scrapy_scrapers.extensions.CustomSpiderState': 400,
        },
        'PIPELINES': {
            'scrapy_scrapers.spiders.mycodal.pipelines.MycodalCompanyPipeline'
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, 'state'):  # this is for code inspection only..
            self.state = {}

    URL = settings.MYCODAL_COMPANY_LIST_URL

    @classmethod
    def get_max_page(cls) -> int:
        try:
            response = requests.get(cls.URL.format(page_number=1), headers={'User-Agent': get_random_user_agent()})
            doc = html.document_fromstring(response.content)
            max_page_xpath = '//body/div[@id="content"]/div[@class="index-bg"]/section[@class="filter-company"]' \
                             '/div/div/div[@class="col-12 "]/div[@id="pagination"]/div/div/ul/li[last()]/a'
            max_page = doc.xpath(max_page_xpath)  # fixme: exception raised.
            max_page = max_page[0].text
            max_page = int(max_page.replace('»', '').strip())
            return max_page
        except Exception as e:
            raise LookupError(f"mycodal_company_scraper failed. max_page_xpath not located. exc={e}")

    @classmethod
    def format_url(cls, page_number: int) -> str:
        return cls.URL.format(page_number=page_number)

    def start_requests(self):
        max_page = self.get_max_page()
        urls = [self.format_url(page) for page in range(1, max_page + 1)]
        for idx, url in enumerate(urls):
            yield Request(url=url, dont_filter=True, cb_kwargs={'request_index': idx}, callback=self.parse)

    def parse(self, response: Response, **kwargs):
        items: list[MycodalCompanyItem] = list()
        rows_xpath = '//body/div[@id="content"]/div[@class="index-bg"]/section[@class="filter-company"]' \
                     '/div/div/div[@class="col-12 "]/table[@class="table-bordered table-striped rwd-table ' \
                     'table-hover publisher-table"]/tbody[@id="template-container"]/tr[@class="gradeX"]'
        rows = response.xpath(rows_xpath)
        for row in rows:
            loader = MycodalCompanyItemLoader(response=row)
            loader.add_xpath('symbol', './td[1]/a/text()')

            loader.add_value('mycodal_info_link', row.xpath('./td[1]/a').css('::attr(href)').get(),
                             H.pvalidate(tipe=str, post=str.strip, value_exc='//#'),
                             partial(UrlManipulator.urlify, scheme='https', netloc=self.allowed_domains[0]),
                             H.pvalidate(validation=validators.url))
            loader.add_value('mycodal_id', row.xpath('./td[1]/a').css('::attr(href)').get(),
                             H.pvalidate(tipe=str, post=str.strip, value_exc='//#'),
                             lambda x: [i for i in x.split('/') if i][-1],
                             lambda x: x if isinstance(x, str) and all(map(str.isdigit, x)) else None)
            loader.add_xpath('name', './td[2]/span/span/text()')
            loader.add_xpath('type', './td[4]/span/text()')
            loader.add_xpath('acceptance_type', './td[5]/span/text()')
            loader.add_xpath('industry_group', './td[6]/span/text()')

            loader.add_value('website', row.xpath('./td[8]/a').css('::attr(href)').get(),
                             H.pvalidate(tipe=str, post=str.strip, value_exc='//#'),
                             lambda x: x.replace('//', ''),
                             partial(UrlManipulator.urlify, scheme='http'),
                             H.pvalidate(tipe=str, validation=validators.url))

            items.append(loader.load_item())

        for item in items:
            adaptor = ItemAdapter(item)
            mycodal_id = adaptor['mycodal_id']
            mycodal_info_link = adaptor['mycodal_info_link']
            if mycodal_id is None or mycodal_info_link is None:
                continue  # todo: log

            cb_kwargs = response.cb_kwargs
            cb_kwargs.update({
                'mycodal_info_link': mycodal_info_link,
                'item': item
            })
            yield Request(url=mycodal_info_link, callback=self.parse_index_page, cb_kwargs=response.cb_kwargs)

    @classmethod
    def extract_cb_kwargs(cls, response: Response):
        if any(map(lambda x: x not in response.cb_kwargs, ['mycodal_info_link', 'item'])):
            return False, None, None, None
        return (
            True,
            response.cb_kwargs['mycodal_info_link'],
            response.cb_kwargs['item']
        )

    def parse_index_page(self, response: Response, **kwargs):
        valid, mycodal_info_link, item = self.extract_cb_kwargs(response)
        if not valid:
            return  # todo: log
        loader = MycodalCompanyItemLoader(item=item)

        rows_xpath = '//body/div[@id="content"]/div/div/div/div[2]/div[@id="subcontent"]' \
                     '/div[@class=" detail-col "]/div/div/table/tbody/tr'
        rows = response.xpath(rows_xpath)
        for row in rows:
            tds = row.xpath('./td/text()')
            tds = list(map(str.strip, filter(
                lambda x: x is None or not isinstance(x, str),
                [td.get() for td in tds if isinstance(td, Selector)]
            )))
            if len(tds) != 2:
                continue

            key, value = tds
            key_map = {
                'مدیرعامل': 'ceo',
                'مدیرمالی': 'cfo',
                'ماهیت': 'essence',
                'سرمایه ثبت شده': 'registered_capital',
                'سرمایه ثبت نشده': 'unregistered_capital',
                'ISIC': 'isic',
                'ISIN': 'isin',
                'پایان سال مالی': 'financial_end_of_year'
            }
            key = key_map[key]

            if key == 'financial_end_of_year' and H.validate(value, tipe=str, value_exc='--/--'):
                month, day = list(map(int, value.split('/')))
                loader.add_value('financial_end_month', month)
                loader.add_value('financial_end_day', day)
            else:
                loader.add_value(key, value)

        response.cb_kwargs['item'] = loader.load_item()
        yield Request(urllib.parse.urljoin(mycodal_info_link, 'board'),
                      callback=self.parse_board_members_page, cb_kwargs=response.cb_kwargs)

    def parse_board_members_page(self, response: Response, **kwargs):
        valid, mycodal_info_link, item = self.extract_cb_kwargs(response)
        if not valid:
            return  # todo: log
        loader = MycodalCompanyItemLoader(item=item)

        rows_xpath = '//body/div[@id="content"]/div/div/div/div[2]/div[@id="subcontent"]' \
                     '/div[@class=" detail-col "]/div/div/table/tbody/tr'
        rows = response.xpath(rows_xpath)
        for row in rows:
            tds = row.xpath('./td/text()')
            tds = list(map(str.strip, filter(
                lambda x: x is None or not isinstance(x, str),
                [td.get() for td in tds if isinstance(td, Selector)]
            )))
            if len(tds) != 3:
                continue

            loader.add_value('board_members', {'institution': tds[0], 'representor': tds[1], 'post': tds[2]})

        response.cb_kwargs['item'] = loader.load_item()
        yield Request(urllib.parse.urljoin(mycodal_info_link, 'similar_publisher'),
                      callback=self.parse_similar_publishers_page, cb_kwargs=response.cb_kwargs)

    def parse_similar_publishers_page(self, response: Response, **kwargs):
        valid, mycodal_info_link, item = self.extract_cb_kwargs(response)
        if not valid:
            return  # todo: log
        loader = MycodalCompanyItemLoader(item=item)

        publishers_xpath = '//body/div[@id="content"]/div/div/div/div[2]/div[@id="subcontent"]' \
                           '//div[@class="similar_publishers"]/ul/li/a'
        publishers = response.xpath(publishers_xpath)
        for publisher in publishers:
            name = publisher.xpath('./text()').get()
            mycodal_info_link = publisher.css('::attr(href)').get()
            if H.validate(mycodal_info_link, tipe=str, value_exc='//#'):
                mycodal_id = [i for i in mycodal_info_link.split('/') if i][-1]
                mycodal_info_link = H.urlify(scheme='https', netloc=self.allowed_domains[0],
                                             path=mycodal_info_link)
            else:
                mycodal_id = None

            if not H.validate(name, tipe=str, value_exc='-') or \
                    not H.validate(mycodal_info_link, tipe=str, value_exc='//#',
                                   validation=validators.url) or \
                    not H.validate(mycodal_id, tipe=str,
                                   validation=lambda x: all(map(lambda y: isinstance(y, int), x))):
                continue

            loader.add_value('similar_publishers', {'name': name, 'mycodal_info_link': mycodal_info_link,
                                                    'mycodal_id': mycodal_id})

        yield loader.load_item()
