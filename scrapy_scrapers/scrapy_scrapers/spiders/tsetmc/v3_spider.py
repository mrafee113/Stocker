from django.conf import settings
from scrapy.spiders import Spider
from scrapy.http.request import Request
from scrapy.http.response import Response

from resources.models import Company
from utils.web.scrapy import parse_symbols_or_indexes_argument, ScrapyHandler as H
from .extras.metadata_v3_item import TseTmcMetadataV3Loader


class TseTmcMetadataV1Spider(Spider):
    """
    Uses one url, which needs tsetmc_index as argument (ticker_index=).
    - Uses one request per url.
    - Uses 40 simultaneous concurrent requests.
    Output: list[dict]
    Dictionary Keys: index, ci_sin, base_volume, title, industry_group
    """

    name = 'tsetmc_metadata_v3_spider'
    allowed_domains = ['tsetmc.com', 'tsetmc.ir']
    custom_settings = {'ITEM_PIPELINES': {
        'scrapy_scrapers.spiders.tsetmc.extras.metadata_v3_pipeline.TseTmcMetadataV3Pipeline': 300
    }, 'CONCURRENT_REQUESTS': 40}

    def __init__(self, *a, indexes: list = None, **kw):
        super().__init__(*a, **kw)
        self.indexes = parse_symbols_or_indexes_argument(indexes)

    URL = settings.TSE_STOCK_DETAILS_URL

    @classmethod
    def format_url(cls, index: str):
        return cls.URL.format(ticker_index=index)

    def start_requests(self):
        indexes = Company.objects.values_list('tsetmc_index', flat=True) if self.indexes == 'all' else \
            self.indexes
        for index in indexes:
            url = self.format_url(index)
            yield Request(url=url, callback=self.parse, cb_kwargs={'index': index})

    def parse(self, response: Response, **kwargs):
        # todo: got all responses from web but did not scrape any items within 360 objects.
        #  figure this shit out too.
        script = response.xpath('//body/div[@class="MainContainer"]/form[@id="form1"]/script')
        if script is None or not H.validate(script.get(), tipe=str, value_exc=str()):
            return
        script = script.get()
        details = script.replace('var ', '').replace(';', '').split(',')
        details = [[d.split('=')[0], d.split('=')[1].replace("'", '')] for d in details]
        details = {d[0]: d[1] for d in details}

        key_map = {
            'CIsin': 'ci_sin',
            'Title': 'title',
            'LSecVal': 'industry_group',
            'BaseVol': 'base_volume'
        }
        loader = TseTmcMetadataV3Loader()
        for tse_key, value in details.items():
            if tse_key not in key_map:
                continue
            loader.add_value(key_map[tse_key], value)

        loader.add_value('index', response.cb_kwargs['index'])

        yield loader.load_item()
