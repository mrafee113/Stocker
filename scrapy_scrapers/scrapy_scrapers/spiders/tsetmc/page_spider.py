import jdatetime

from lxml import html
from django.conf import settings
from scrapy.spiders import Spider
from scrapy.http.request import Request
from scrapy.http.response import Response
from playwright.async_api._generated import Page
from playwright._impl._api_types import TimeoutError as PlaywrightTimeoutError

from resources.models import Company
from utils.farsi import replace_arabic
from utils.datetime import fa_to_en_jalali_month, fa_to_en_month_map, fa_to_en
from utils.web.scrapy import parse_symbols_or_indexes_argument, ScrapyHandler as H

from .extras.dps_item import TseTmcDPSItem, TseTmcDPSLoader
from .extras.supervisor_message_item import TseTmcSupervisorMsgItem, TseTmcSupervisorMsgLoader
from .extras.corporate_individual_item import TseTmcCorporateIndividualItem, TseTmcCorporateIndividualLoader
from .extras.overview_item import TseTmcOverviewItem, TseTmcOverviewLoader


# todo: fix doc for data output
class TseTmcPageSpider(Spider):
    """
    Uses one url, which needs tsetmc_index as argument (ticker_index=).
    - Uses one request per tsetmc_index.
    - Uses 10 simultaneous concurrent requests.
    Corporate Individual Data
        Output: list[dict]
        Dictionary Keys: tsetmc_index, date,
            individual_buy_count, corporate_buy_count, individual_sell_count, corporate_sell_count,
            individual_buy_volume, corporate_buy_volume, individual_sell_volume, corporate_sell_volume,
            individual_buy_value, corporate_buy_value, individual_sell_value, corporate_sell_value,
            individual_buy_avg, corporate_buy_avg, individual_sell_avg, corporate_sell_avg,
            ownership_change
    DPS DATA
        Output: list[dict]
        Dictionary Keys: tsetmc_index,
            assembly_date, fiscal_year, issuance_date,
            dividends, dps
    """

    name = 'tsetmc_page_spider'
    allowed_domains = ['tsetmc.com', 'uat.tsetmc.com', 'tsetmc.ir']
    custom_settings = {
        'ITEM_PIPELINES': {'scrapy_scrapers.spiders.tsetmc.extras.page_pipeline.TseTmcPagePipeline': 300},
        # fixme: use four pipelines here instead of using a main big pipeline
        'CONCURRENT_REQUESTS': 10,
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        'TWISTED_REACTOR': "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 120000,
        # 'PLAYWRIGHT_LAUNCH_OPTIONS': {'slow_mo': 50,
        #                               'headless': False}  # todo: remove
    }
    main_xpath = '//body/div[@class="MainContainer"]/form'
    parsers = ['corporate_individual', 'dps', 'supervisor_message', 'overview']

    def __init__(self, *a, parser: str = None, indexes: list = None, **kw):
        super().__init__(*a, **kw)
        self.indexes = parse_symbols_or_indexes_argument(indexes)
        if parser is not None and parser not in self.parsers:
            raise ValueError('kw argument must be either None, "corporate_individual" or "dps"')
        self.parser = parser

    URL = settings.TSE_STOCK_DETAILS_URL

    @classmethod
    def format_url(cls, index: str):
        return cls.URL.format(ticker_index=index)

    def start_requests(self):
        indexes = Company.objects.values_list('tsetmc_index', flat=True) if self.indexes == 'all' else \
            self.indexes
        for index in indexes:
            url = self.format_url(index)
            yield Request(url=url, callback=self.parse, cb_kwargs={'index': index},
                          meta={'playwright': True, 'playwright_include_page': True},
                          errback=self.errback_close_page)

    @classmethod
    async def errback_close_page(cls, failure):
        await failure.requst.meta('playwright_page')

    async def parse(self, response: Response, **kwargs):
        page: Page = response.meta['playwright_page']
        main_xpath = '//body/div[@class="MainContainer"]/form'
        button_panel_xpath = f'{main_xpath}/div[2]/div/ul'

        button_panel = page.locator(f'xpath={button_panel_xpath}')
        await button_panel.wait_for()

        # btw, this is the shittiest way to scrape a shitty website like tsetmc.com
        async def init_panels() -> dict:
            _inner_html = await button_panel.inner_html()
            _inner_html = f'<html><body><ul>{_inner_html}</ul></body></html>'
            _doc = html.document_fromstring(_inner_html)
            _elements = _doc.xpath('//body/ul/li')
            _panels = dict()
            for idx, _el in enumerate(_elements):
                _panels[_el.text_content()] = idx

            return _panels

            # _panels = button_panel.locator('xpath=./li')
            # _elements = dict()
            # _count = await _panels.count()
            # for _c in range(0, _count):
            #     _el = _panels.nth(_c)
            #     _text = await _el.text_content()
            #     _elements[_text] = _el
            # return _elements

        panels = await init_panels()

        async def evaluate_panel(inner_text: str):
            if inner_text not in panels:
                return False

            idx = panels[inner_text]
            await page.evaluate("""
            function get_button_panel() {
                var button_panel = document.evaluate('//body/div[@class="MainContainer"]/form/div[@id="tabs"]/div/ul',
                    document, null, XPathResult.ANY_UNORDERED_NODE_TYPE, null).singleNodeValue;
                var panel = button_panel.getElementsByTagName("a")[""" + str(idx) + """]
                panel.click();
            }
            """.strip())
            return True

            # if inner_text in panels:
            #     await page.evaluate("function click_btn(button) {button.click();}", panels[inner_text])
            #     return True
            # return False

            # await page.evaluate("""
            # function get_button_panel(inner_text) {
            #     var button_panel = document.evaluate('//body/div[@class="MainContainer"]/form/div[@id="tabs"]/div/ul',
            #         document, null, XPathResult.ANY_UNORDERED_NODE_TYPE, null).singleNodeValue;
            #     var panels = button_panel.getElementsByTagName("a")
            #
            #     for (let panel of panels) {
            #         if (panel.innerText == inner_text) {panel.click(); return true;}
            #     }
            #     return false;
            # }
            # """.strip(), inner_text)

        parser_map = {
            'corporate_individual': ("حقیقی-حقوقی", 'parse_corporate_individual_data'),
            'dps': ('DPS', 'parse_dps'),
            'supervisor_message': ('پیام ناظر', 'parse_supervisor_messages'),
            'overview': ('در یک نگاه', 'parse_overview')
        }
        data = list()
        for parser in self.parsers:
            if self.parser is None or self.parser == parser:
                evaluated = await evaluate_panel(parser_map[parser][0])
                if not evaluated:
                    continue

                parse_method = getattr(self, parser_map[parser][1])
                items = await parse_method(page, response)
                data.extend(items)

        await page.close()
        return data

    async def parse_overview(self, page: Page, response: Response):
        title_xpath = f'{self.main_xpath}/div[@id="MainBox"]/div[@class="header bigheader"]'
        title = page.locator(f'xpath={title_xpath}')
        await title.wait_for()

        inner_html = await page.inner_html('//body')
        inner_html = f'<html><body>{inner_html}</body></html>'
        doc: html.HtmlElement = html.document_fromstring(inner_html)

        title = doc.xpath(title_xpath)
        title = title[0].text

        divs_xpath = f'{self.main_xpath}/div[@id="MainBox"]/div[@id="MainContent"]/div[@id="TopBox"]/div'
        divs = doc.xpath(divs_xpath)
        explanation = divs[1].text if len(divs) == 5 else str()

        loader = TseTmcOverviewLoader()
        tsetmc_index = response.cb_kwargs['index']
        loader.add_value('tsetmc_index', tsetmc_index)
        loader.add_value('title', title)
        loader.add_value('explanation', explanation)

        item: TseTmcOverviewItem = loader.load_item()
        return [item]

    async def parse_supervisor_messages(self, page: Page, response: Response):
        table_xpath = f'{self.main_xpath}/div[@id="MainBox"]/div[@id="TseMsgContent"]/div/div[@class="content"]' \
                      f'/table/tbody'
        rows_xpath = f'{table_xpath}/tr'

        table = page.locator(f'xpath={table_xpath}')
        await table.wait_for()

        inner_html = await page.inner_html('//body')
        inner_html = f'<html><body>{inner_html}</body></html>'
        doc: html.HtmlElement = html.document_fromstring(inner_html)
        rows = doc.xpath(rows_xpath)
        if len(rows) < 1:
            return

        items: list[TseTmcSupervisorMsgItem] = list()
        tsetmc_index = response.cb_kwargs['index']
        for base_iter in range(0, len(rows), 2):
            loader = TseTmcSupervisorMsgLoader()
            loader.add_value('tsetmc_index', tsetmc_index)

            header, message = rows[base_iter], rows[base_iter + 1]
            message = message.xpath('./td')[0].text_content()
            header = header.xpath('./th')
            title, datetime_value = header
            title, datetime_value = title.text_content(), datetime_value.text_content()

            loader.add_value('title', title)
            loader.add_value('datetime', datetime_value)
            loader.add_value('message', message)

            items.append(loader.load_item())

        return items

    async def parse_dps(self, page: Page, response: Response):
        table_xpath = f'{self.main_xpath}/div[@id="MainBox"]/div[@id="DPSContent"]/table/tbody'
        rows_xpath = f'{table_xpath}/tr'

        table = page.locator(f'xpath={table_xpath}')
        await table.wait_for()

        inner_html = await page.inner_html('//body')
        inner_html = f'<html><body>{inner_html}</body></html>'
        doc: html.HtmlElement = html.document_fromstring(inner_html)
        rows = doc.xpath(rows_xpath)
        if len(rows) < 3:
            return  # todo: log warning.

        items: list[TseTmcDPSItem] = list()
        rows = rows[2:]
        tsetmc_index = response.cb_kwargs['index']
        for row in rows:
            loader = TseTmcDPSLoader()
            loader.add_value('tsetmc_index', tsetmc_index)

            issuance_date, assembly_date, fiscal_date, _, dividends, _, dps = \
                [td.text_content() for td in row.xpath('./td')]
            loader.add_value('issuance_date', issuance_date)
            loader.add_value('assembly_date', assembly_date)
            loader.add_value('fiscal_date', fiscal_date)
            loader.add_value('dividends', dividends)
            loader.add_value('dps', dps)
            items.append(loader.load_item())

        return items

    async def parse_corporate_individual_data(self, page: Page, response: Response, **kwargs):
        table_xpath = f'{self.main_xpath}/div[@id="MainBox"]/div[@id="ClientTypeContent"]' \
                      f'/div/div[@class="content"]/table[2]/tbody[2]'
        rows_xpath = f'{table_xpath}/tr'

        table = page.locator(f'xpath={table_xpath}')
        await table.wait_for()

        year = await self.eval_corporate_individual_year(page)
        items: list[TseTmcCorporateIndividualItem] = list()
        while True:
            # load
            table = page.locator(f'xpath={table_xpath}')
            try:
                await table.wait_for(timeout=2000)
            except (TimeoutError, PlaywrightTimeoutError):
                break

            # parse
            inner_html = await page.inner_html('//body')
            inner_html = f'<html><body>{inner_html}</body></html>'
            doc: html.HtmlElement = html.document_fromstring(inner_html)
            rows = doc.xpath(rows_xpath)
            items.extend(self.parse_corporate_individual_rows(rows, year))

            # next
            await page.evaluate('() => document.getElementsByClassName("awesome green")[1].click();')
            year = await self.eval_corporate_individual_year(page)

        tsetmc_index = response.cb_kwargs['index']
        for item in items:
            item['tsetmc_index'] = tsetmc_index

        return items

    @classmethod
    async def eval_corporate_individual_year(cls, page) -> int:
        year = await page.locator('xpath=//td[@id="YearPart"]').inner_text()
        year = int(year.strip())
        return year

    @classmethod
    def parse_corporate_individual_rows(cls, rows: list[html.HtmlElement], year: int) -> \
            list[TseTmcCorporateIndividualItem]:
        items: list[TseTmcCorporateIndividualItem] = list()
        for base_iter in range(0, len(rows), 6):
            loader = TseTmcCorporateIndividualLoader()
            numbers = rows[base_iter + 0].xpath('./td')

            month = numbers[0].xpath('./div[1]')[0].text_content()
            if not H.validate(month, tipe=str, value_exc=str(),
                              validation=lambda x: replace_arabic(x).strip() in fa_to_en_month_map):
                continue
            month = str(fa_to_en_jalali_month(month)).zfill(2)

            day = numbers[0].xpath('./div[2]')[0].text_content()
            if not H.validate(day, tipe=str, value_exc=str(),
                              validation=lambda x: isinstance(int(fa_to_en(x).strip()), int)):
                continue
            day = fa_to_en(day).strip().zfill(2)

            date_string = f'{year}/{month}/{day}'
            from utils.web.scrapy import debug_print
            if not H.validate(date_string, tipe=str, validation= \
                    lambda x: isinstance(jdatetime.datetime.strptime(x, '%Y/%m/%d'), jdatetime.datetime)):
                debug_print(f'date_string={date_string}')
                continue
            loader.add_value('date', date_string)

            loader.add_value('individual_buy_count', numbers[2].text_content())
            loader.add_value('corporate_buy_count', numbers[3].text_content())
            loader.add_value('individual_sell_count', numbers[4].text_content())
            loader.add_value('corporate_sell_count', numbers[5].text_content())

            volumes = rows[base_iter + 1].xpath('./td')

            def get_v(x):
                return x.xpath('./div[1]')[0].attrib.get('title', None)

            loader.add_value('individual_buy_volume', get_v(volumes[1]))
            loader.add_value('corporate_buy_volume', get_v(volumes[2]))
            loader.add_value('individual_sell_volume', get_v(volumes[3]))
            loader.add_value('corporate_sell_volume', get_v(volumes[4]))

            values = rows[base_iter + 2].xpath('./td')
            loader.add_value('individual_buy_value', get_v(values[1]))
            loader.add_value('corporate_buy_value', get_v(values[2]))
            loader.add_value('individual_sell_value', get_v(values[3]))
            loader.add_value('corporate_sell_value', get_v(values[4]))

            avg_price = rows[base_iter + 3].xpath('./td')
            loader.add_value('individual_buy_avg', avg_price[1].text_content())
            loader.add_value('corporate_buy_avg', avg_price[2].text_content())
            loader.add_value('individual_sell_avg', avg_price[3].text_content())
            loader.add_value('corporate_sell_avg', avg_price[4].text_content())

            loader.add_value('ownership_change', rows[base_iter + 4].xpath('.//div')[0].text_content())

            items.append(loader.load_item())

        return items
