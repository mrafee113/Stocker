import bs4

from lxml import html
from django.conf import settings
from scrapy.spiders import Spider
from scrapy.http.request import Request
from scrapy.http.response import Response

from resources.models import Company
from utils.web.scrapy import parse_symbols_or_indexes_argument
from .extras.shareholders_item import TseTmcShareholdersItem, TseTmcShareholdersLoader


class TseTmcShareholdersSpider(Spider):
    """
    Uses one urls, which needs isin (tsetmc_instrument_id).
    - Uses one request per url.
    Output: list[dict]
    Dictionary Keys: tsetmc_index, shareholder_id, shareholder_name, number_of_shares, shares_percentage, change
    """

    name = 'tsetmc_shareholders_spider'
    allowed_domains = ['tsetmc.com', 'tsetmc.ir']

    custom_settings = {
        'ITEM_PIPELINES':
            {'scrapy_scrapers.spiders.tsetmc.extras.shareholders_pipeline.TseTmcShareholdersPipeline': 300}
    }

    URL = settings.TSE_STOCK_SHAREHOLDERS_DATA_URL

    def __init__(self, *a, indexes: list = None, **kw):
        super().__init__(*a, **kw)
        self.indexes = parse_symbols_or_indexes_argument(indexes)

    @classmethod
    def format_url(cls, ci_sin: str):
        return cls.URL.format(ci_sin=ci_sin)

    def start_requests(self):
        ci_sins = Company.objects.all() if self.indexes == 'all' else Company.objects. \
            filter(tsetmc_index__in=self.indexes)
        ci_sins = ci_sins.exclude(isin__exact=str()).values_list('tsetmc_index', 'ci_sin')
        for index, isin in ci_sins:
            url = self.format_url(isin)
            yield Request(url=url, callback=self.parse, cb_kwargs={'index': index})

    def parse(self, response: Response, **kwargs):
        index = response.cb_kwargs['index']
        soup = bs4.BeautifulSoup(response.body, 'html.parser')
        doc: html.HtmlElement = html.document_fromstring(str(soup))
        items: list[TseTmcShareholdersItem] = list()
        rows = doc.xpath('//body//table/tbody/tr')
        for row in rows:
            loader = TseTmcShareholdersLoader()
            loader.add_value('tsetmc_index', index)

            if 'onclick' not in row.attrib:
                continue
            sh_id = row.attrib['onclick']
            sh_id = sh_id[sh_id.find("'") + 1: sh_id.find(",")]
            loader.add_value('shareholder_id', sh_id)

            tds = row.xpath('./td')
            shareholder_name = tds[0].text_content().strip()
            loader.add_value('shareholder_name', shareholder_name)
            shares_percentage = tds[2].text_content().strip()
            loader.add_value('shares_percentage', shares_percentage)

            number_of_shares = tds[1].xpath('./div')
            if not len(number_of_shares) or 'title' not in number_of_shares[0].attrib:
                continue
            number_of_shares = number_of_shares[0].attrib['title']
            loader.add_value('number_of_shares', number_of_shares)

            change = tds[3].xpath('./div')
            if len(change) and 'title' in number_of_shares[0].attrib:
                change = change.attrib['title']
                loader.add_value('change', change)

            item = loader.load_item()
            items.append(item)

        for item in items:
            yield item
