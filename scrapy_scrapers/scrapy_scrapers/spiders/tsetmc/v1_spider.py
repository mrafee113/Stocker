from django.conf import settings
from scrapy.spiders import Spider
from scrapy.http.request import Request
from scrapy.http.response import Response

from utils.farsi import replace_arabic
from utils.web.scrapy import ScrapyHandler as H
from .extras.metadata_v1_item import TseTmcMetadataV1Item, TseTmcMetadataV1Loader


class TseTmcMetadataV1Spider(Spider):
    """
    Uses two urls, neither of which need any input arguments.
    - Uses one request per url.
    Output: list[dict]
    Dictionary Keys: symbol, index, name, isin
    """

    name = 'tsetmc_metadata_v1_spider'
    allowed_domains = ['tsetmc.com', 'tsetmc.ir']

    custom_settings = {'ITEM_PIPELINES': {
        'scrapy_scrapers.spiders.tsetmc.extras.metadata_v1_pipeline.TseTmcMetadataV1Pipeline': 300
    }}

    SYMBOLS_LIST_URL = settings.TSETMC_LIST_URL
    MARKET_WATCH_INIT_URL = settings.TSETMC_MARKETWATCH_INIT_URL

    def start_requests(self):
        yield Request(url=self.SYMBOLS_LIST_URL, callback=self.parse_symbols_list_url)
        yield Request(url=self.MARKET_WATCH_INIT_URL, callback=self.parse_market_watch_url)

    def parse(self, response: Response, **kwargs):
        pass

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

    @classmethod
    def parse_symbols_list_url(cls, response: Response, **kw):
        table = response.xpath('//table')
        table_rows = table.xpath('./tr')[1:]
        items: list[TseTmcMetadataV1Item] = list()
        for table_row in table_rows:
            loader = TseTmcMetadataV1Loader(selector=table_row)
            deleted = table_row.xpath('./td[8]/a/text()').get()
            if deleted is not None and deleted.startswith('حذف-'):
                continue

            loader.add_xpath('isin', './td[1]/text()')
            loader.add_xpath('symbol', './td[7]/a/text()')
            loader.add_xpath('name', './td[8]/a/text()')
            loader.add_value('index', table_row.xpath('./td[7]/a').css('::attr(href)').get(),
                             H.pvalidate(tipe=str, value_exc=str()), str.strip,
                             lambda x: x.partition('inscode=')[2], replace_arabic)

            items.append(loader.load_item())

        for item in items:
            yield item

    @classmethod
    def parse_market_watch_url(cls, response: Response, **kw):
        groups = response.xpath('//body').get().split('@')
        if len(groups) < 3:
            raise LookupError("symbols information from market watch page is not valid.")

        items: list[TseTmcMetadataV1Item] = list()
        symbols_data = groups[2].split(';')
        for symbol_data in symbols_data:
            index, isin, symbol, name, *_ = symbol_data.split(',')

            loader = TseTmcMetadataV1Loader()
            loader.add_value('index', index, H.pvalidate(tipe=str, value_exc=str()), str.strip, replace_arabic)
            loader.add_value('isin', isin)
            loader.add_value('symbol', symbol)
            loader.add_value('name', name)

            items.append(loader.load_item())

        for item in items:
            yield item
