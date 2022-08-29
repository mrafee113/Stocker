import pandas as pd

from io import StringIO
from django.conf import settings
from scrapy.spiders import Spider
from scrapy.http.request import Request
from scrapy.http.response import Response

from resources.models import Company
from utils.web.scrapy import ScrapyHandler as H, parse_symbols_or_indexes_argument
from .extras.price_records_item import TseTmcPriceRecordItem


class TseTmcPriceRecordsSpider(Spider):
    """
    Uses one urls, which needs tsetmc_index.
    - Uses one request per url.
    Output: list[dict]
    Dictionary Keys: tsetmc_index, date, open, high, low, adj_close, value, volume, count, close
    """

    name = 'tsetmc_price_records_spider'
    allowed_domains = ['tsetmc.com', 'tsetmc.ir']

    custom_settings = {
        'ITEM_PIPELINES':
            {'scrapy_scrapers.spiders.tsetmc.extras.price_records_pipeline.TseTmcPriceRecordsPipeline': 300}
    }

    URL = settings.TSE_STOCK_PRICE_DATA__FILE_URL

    def __init__(self, *a, indexes: list = None, **kw):
        super().__init__(*a, **kw)
        self.indexes = parse_symbols_or_indexes_argument(indexes)

    @classmethod
    def format_url(cls, index: str):
        return cls.URL.format(ticker_index=index)

    def start_requests(self):
        indexes = Company.objects.values_list('tsetmc_index', flat=True) if self.indexes == 'all' else \
            self.indexes
        for index in indexes:
            url = self.format_url(index)
            print('-' * 100 + ' ' + url)
            yield Request(url=url, callback=self.parse, cb_kwargs={'index': index})

    def parse(self, response: Response, **kwargs):
        text_header = '<TICKER>,<DTYYYYMMDD>,<FIRST>,<HIGH>,<LOW>,<CLOSE>,<VALUE>,<VOL>,<OPENINT>,<PER>,<OPEN>,<LAST>'
        if not hasattr(response, 'text') or H.validate(response.text, tipe=str, value_exc=str()) is None \
                or not response.text.startswith(text_header):
            return  # todo: log warning

        items: list[TseTmcPriceRecordItem] = list()
        index = response.cb_kwargs['index']
        print('-' * 100 + ' ' + index)
        field_mapper = {
            "<DTYYYYMMDD>": "date",
            "<FIRST>": "open",
            "<HIGH>": "high",
            "<LOW>": "low",
            "<LAST>": "close",
            "<VOL>": "volume",
            "<CLOSE>": "adj_close",
            "<OPENINT>": "count",
            "<VALUE>": "value"
        }

        df = StringIO(response.text)
        df = pd.read_csv(df)
        if not len(df):
            return
        df = df.iloc[::-1]
        df = df.rename(columns=field_mapper)
        df = df.drop(columns=["<PER>", "<OPEN>", "<TICKER>"])
        df.date = pd.to_datetime(df.date, format="%Y%m%d")
        for field in field_mapper.values():
            if field in ['date', 'count']:
                continue

            setattr(df, field, getattr(df, field).astype(int))

        index_series = pd.Series([index] * len(df), index=df.index)
        df = df.assign(tsetmc_index=index_series)
        df = df.to_dict('records')
        for d in df:
            d['date'] = d['date'].date()
            items.append(TseTmcPriceRecordItem(d))

        for item in items:
            yield item
