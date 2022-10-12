from django.conf import settings
from scrapy.spiders import Spider
from scrapy.http.request import Request
from scrapy.http.response import Response
from scrapy.selector import SelectorList

from resources.models import Company
from utils.web.scrapy import ScrapyHandler as H, parse_symbols_or_indexes_argument
from .extras.price_mod_history_item import TseTmcPriceModHistoryItem, TseTmcPriceModHistoryLoader


class TseTmcPriceModificationHistorySpider(Spider):
    """
    Uses one urls, which needs tsetmc_index.
    - Uses one request per url.
    Output: list[dict]
    Dictionary Keys: tsetmc_index, prev_price, next_price, date
    """

    name = 'tsetmc_price_mod_history_spider'
    allowed_domains = ['tsetmc.com', 'tsetmc.ir']

    custom_settings = {
        'ITEM_PIPELINES':
            {'scrapy_scrapers.spiders.tsetmc.extras.price_mod_history_pipeline.TseTmcPriceModHistoryPipeline': 300}
    }

    URL = settings.TSETMC_STOCK_PRICE_MOD_HISTORY_URL

    def __init__(self, *a, indexes: list = None, **kw):
        super().__init__(*a, **kw)
        self.indexes = parse_symbols_or_indexes_argument(indexes)

    @classmethod
    def format_url(cls, index: str):
        return cls.URL.format(tsetmc_index=index)

    def start_requests(self):
        indexes = Company.objects.values_list('tsetmc_index', flat=True) if self.indexes == 'all' else \
            self.indexes
        for index in indexes:
            url = self.format_url(index)
            yield Request(url=url, callback=self.parse, cb_kwargs={'index': index})

    def parse(self, response: Response, **kwargs):
        index = response.cb_kwargs['index']
        rows = response.xpath('//body//tbody/tr')
        if not H.validate(rows, tipe=SelectorList, validation=lambda x: len(rows) > 0):
            return
            # fixme: log warning.

        items: list[TseTmcPriceModHistoryItem] = list()
        for row in rows:
            row = row.xpath('./td/text()')
            if not H.validate(row, tipe=SelectorList, validation=lambda x: len(row) == 3):
                continue
                # fixme: log warning

            loader = TseTmcPriceModHistoryLoader()
            date, next_price, prev_price = [d.get() for d in row]

            loader.add_value('tsetmc_index', index)
            loader.add_value('date', date)
            loader.add_value('next_price', next_price)
            loader.add_value('prev_price', prev_price)
            items.append(loader.load_item())

        for item in items:
            yield item
