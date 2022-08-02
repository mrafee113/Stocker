from django.conf import settings
from scrapy.spiders import Spider
from scrapy.http.request import Request
from scrapy.http.response import Response
from scrapy.selector import SelectorList

from resources.models import Company
from utils.web.scrapy import ScrapyHandler as H, parse_symbols_or_indexes_argument
from .extras.capital_increase_history_item import TseTmcCapitalIncreaseHistoryItem, \
    TseTmcCapitalIncreaseHistoryLoader


class TseTmcCapitalIncreaseHistorySpider(Spider):
    """
    Uses one urls, which needs tsetmc_index.
    - Uses one request per url.
    Output: list[dict]
    Dictionary Keys: tsetmc_index, prev_stocks, next_stocks, date
    """

    name = 'tsetmc_capital_increase_history_spider'
    allowed_domains = ['tsetmc.com', 'tsetmc.ir']

    custom_settings = {
        'ITEM_PIPELINES':
            {'scrapy_scrapers.spiders.tsetmc.extras.capital_increase_history_pipeline.'
             'TseTmcCapitalIncreaseHistoryPipeline': 300}
    }

    URL = settings.TSETMC_COMPANY_CAPITAL_INCREASE_HISTORY_URL

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

        items: list[TseTmcCapitalIncreaseHistoryItem] = list()
        for row in rows:
            date = row.xpath('./td[1]/text()')
            next_stocks, prev_stocks = [row.xpath(f'./td[{i}]/div').css('::attr(title)') for i in range(2, 4)]
            if not all(map(
                    lambda y: (H.validate(y, tipe=SelectorList, validation=lambda x: len(y) == 1)),
                    (date, next_stocks, prev_stocks)
            )):
                continue
                # fixme: log warning

            loader = TseTmcCapitalIncreaseHistoryLoader()
            date, next_stocks, prev_stocks = [d.get() for d in (date, next_stocks, prev_stocks)]

            loader.add_value('tsetmc_index', index)
            loader.add_value('date', date)
            loader.add_value('next_stocks', next_stocks)
            loader.add_value('prev_stocks', prev_stocks)
            items.append(loader.load_item())

        for item in items:
            yield item
