from django.conf import settings
from scrapy.spiders import Spider
from scrapy.http.request import Request
from scrapy.http.response import Response

from resources.models import Company
from utils.farsi import replace_arabic
from utils.web.scrapy import parse_symbols_or_indexes_argument, ScrapyHandler as H
from .extras.old_indexes_item import TseTmcOldIndexesItem


class TseTmcMetadataV2Spider(Spider):
    """
    Uses one url. Url accepts {symbol} as input argument.
    - Uses {symbols}.len requests O(n).
    Output: list[dict]
    Dictionary Keys: symbol: str, old_indexes: list[str]
    """

    name = 'tsetmc_metadata_v2_spider'
    allowed_domains = ['tsetmc.com', 'tsetmc.ir']

    custom_settings = {'ITEM_PIPELINES': {
        'scrapy_scrapers.spiders.tsetmc.extras.old_indexes_pipeline.TseTmcOldIndexesPipeline': 300
    }}

    URL = settings.TSETMC_SYMBOL_ID_URL

    def __init__(self, *a, symbols: list = None, **kw):
        super().__init__(*a, **kw)
        self.symbols = parse_symbols_or_indexes_argument(symbols)

    @classmethod
    def format_url(cls, symbol):
        return cls.URL.format(symbol=symbol)

    def start_requests(self):
        symbols = Company.objects.all().values_list('tsetmc_symbol', flat=True) if self.symbols == 'all' else \
            self.symbols
        for symbol in symbols:
            yield Request(url=self.format_url(symbol), callback=self.parse,
                          cb_kwargs={'symbol': symbol})

    def parse(self, response: Response, **kw):
        symbol = response.cb_kwargs['symbol']
        data = response.xpath('//body').get()
        if not H.validate(data, tipe=str, value_exc=str()):
            return

        data = data.split(';')
        old_indexes = list()
        for info in data:
            if info.strip() == "":
                continue
            info = info.split(',')
            if len(info) < 8:
                continue
            if replace_arabic(info[0]) == symbol:
                if info[7] != '1':
                    old_indexes.append(info[2])

        validator = H.pvalidate(tipe=str, value_exc=str(), post=lambda x: replace_arabic(x.strip()))
        old_indexes = list(filter(None, [validator(oi) for oi in old_indexes]))
        if old_indexes:
            yield TseTmcOldIndexesItem(symbol=symbol, old_indexes=old_indexes)
