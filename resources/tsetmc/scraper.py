import os
import bs4
import time
import tqdm
import requests

from math import sqrt
from concurrent import futures
from django.conf import settings
from typing import Dict, List
from selenium.webdriver.common.keys import Keys

from utils.web import get_random_user_agent
from utils.web.selenium import DriverHandler, web_driver


class TseTmcCompanyScraper:
    H = DriverHandler

    @classmethod
    def scrape_metadata(cls, refresh_indexes=False):
        from resources.tsetmc.controller import TseTmcController
        if refresh_indexes:
            cls.scrape_symbols_and_indexes()

        force_reload_details = False
        if refresh_indexes:
            force_reload_details = True

        stock_details = TseTmcController.stocks_details(force_reload_details)
        indexes = list(stock_details.keys())
        responses: Dict[str, requests.Response] = cls._retrieve_stocks(indexes)

        data = dict()
        scrape_map = {
            'instrument_id': 'InstrumentID',
            'ci_sin': 'CIsin',
            'title': 'Title',
            'group_name': 'LSecVal',
            'base_volume': 'BaseVol'
        }
        for index, details in tqdm.tqdm(stock_details.items(),
                                        desc='scraping metadata from webpages'):
            response = responses[index]
            soup = bs4.BeautifulSoup(response.content, 'html.parser')
            body = soup.findChild(name='html').findChild(name='body')
            div = body.findChild(name='div', attrs={'class': 'MainContainer'})
            script = div.findChild(name='form', attrs={'id': 'form1'}).findChild(name='script')

            new_details = script.string.replace('var ', '').replace(';', '').split(',')
            new_details = [[d.split('=')[0], d.split('=')[1].replace("'", '')] for d in new_details]
            new_details = {d[0]: d[1] for d in new_details}

            kw = {
                kw_key: new_details[tse_key]
                for kw_key, tse_key in scrape_map.items()
            }
            data[index] = kw

        TseTmcController.append_data_entry(data)

    @classmethod
    def _retrieve_stocks(cls, indexes: List[str]) -> dict:
        _indexes = indexes[:]
        sec_size = int(sqrt(len(indexes)))
        sections: List[list] = list()
        while len(_indexes) >= sec_size:
            sections.append(_indexes[:sec_size])
            _indexes = _indexes[sec_size:]
        sections.append(_indexes[:])

        result_list = dict()
        future_to_sec_idx = dict()
        with tqdm.tqdm(total=len(indexes), desc='retrieving stocks metadata') as pbar:
            with futures.ThreadPoolExecutor(max_workers=len(sections)) as executor:
                for sec_idx, section in enumerate(sections):
                    future = executor.submit(cls._request_stocks, section, pbar)
                    future_to_sec_idx[future] = sec_idx

                for future in futures.as_completed(future_to_sec_idx):
                    responses = future.result()

                    for index, response in responses.items():
                        result_list[index] = response

        return result_list

    @classmethod
    def _request_stocks(cls, section: List[str], pbar: tqdm.tqdm):
        responses = dict()
        for index in section:
            url = settings.TSE_STOCK_DETAILS_URL.format(ticker_index=index)
            responses[index] = requests.get(url, headers={'User-Agent': get_random_user_agent()})
            pbar.update(1)
            time.sleep(0.1)

        return responses

    @classmethod
    def scrape_symbols_and_indexes(cls):
        from resources.tsetmc.controller import TseTmcController
        if not TseTmcController.validate_file():
            TseTmcController.init_file()

        url = settings.TSE_STOCKS_URL
        driver = web_driver()
        driver.get(url)
        time.sleep(5)

        # calibrate watchMarket settings
        # take note of the incremental number for "ModalWindowOuter{number}"
        #  and also "ModalWindowInner{number}"
        def open_setting_dialogue():
            settings_button_xpath = '//body/div[@id="SettingsDesc"]/div[1]/a[@class="TopIcon MwIcon MwSetting"]'
            cls.H.call_attr(cls.H.get_element(driver, xpath=settings_button_xpath),
                            raise_exception=True, attr='click')

        open_setting_dialogue()

        box3_xpath = '//body//div[@id="ModalWindowOuter{}"]//div[@id="ModalWindowInner{}"]//div[@class="box3"]'

        refresh_rate_xpath = box3_xpath.format(*'11') + '//div[@class="content"]/input'
        refresh_rate = cls.H.get_element(driver, xpath=refresh_rate_xpath)
        cls.H.call_attr(refresh_rate, raise_exception=True, attr='clear')
        refresh_rate.send_keys('50')  # cannot pass non-kw-args to DriverHandler.call_attr
        refresh_rate.send_keys(Keys.RETURN)
        time.sleep(0.5)

        all_tickers_button_xpath = box3_xpath.format(*'11') + '//div[@aria-label="نمایش همه نمادها در دیده بان"]'
        cls.H.call_attr(cls.H.get_element(driver, xpath=all_tickers_button_xpath),
                        raise_exception=True, attr='click')
        time.sleep(2)

        open_setting_dialogue()
        farabourse_button_xpath = box3_xpath.format(*'22') + '//div[@aria-label="نمایش اوراق بازار پایه در دیده بان"]'
        cls.H.call_attr(cls.H.get_element(driver, xpath=farabourse_button_xpath),
                        raise_exception=True, attr='click')
        time.sleep(2)

        close_settings_dialogue_xpath = '//body//div[@id="ModalWindowOuter3"]/div[@class="popup_close"]'
        cls.H.call_attr(cls.H.get_element(driver, xpath=close_settings_dialogue_xpath),
                        raise_exception=True, attr='click')

        # download stocks html file
        download_dialogue_xpath = '//body/div[@id="SettingsDesc"]/div[1]/a[@class="TopIcon MwIcon MwExcel"]'
        cls.H.call_attr(cls.H.get_element(driver, xpath=download_dialogue_xpath),
                        raise_exception=True, attr='click')

        download_button_xpath = '//body/div[@id="ModalWindowOuter4"]/section/div/div/div[3]/div[@class="awesome tra"]'
        cls.H.call_attr(cls.H.get_element(driver, xpath=download_button_xpath),
                        raise_exception=True, attr='click')

        # scrape
        # fixme: find file based on date and time of download
        downloaded_file_path = os.path.join(settings.FIREFOX_DOWNLOAD_DIR, 'MarketWatch.htm')
        time.sleep(2)
        if not os.path.exists(downloaded_file_path):
            raise FileNotFoundError('tsetmc MarketWatch.htm file not found. probably not downloaded.')
        driver.get(f'file://{downloaded_file_path}')

        main_xpath = '//div[@class="other" and @id="main"]'
        abstract_stock_xpath = '//child::div[@class="{c}"]'

        def get_stock_xpath(cid):
            return f'{abstract_stock_xpath[:-1]} and @id="{cid}"]'

        info_xpath = '//child::div[1]/child::a[@class="inst"]'
        main_element = cls.H.get_element(driver, raise_exception=True, xpath=main_xpath)
        stock_sections = cls.H.get_element(main_element, raise_exception=True, xpath=abstract_stock_xpath, many=True)
        stocks_id = list()
        for stock_section in tqdm.tqdm(stock_sections, desc='retrieving stock ids'):
            stock_id = cls.H.get_attr(stock_section, attr='id')
            if cls.H.validate(stock_id, tipe=str, value_exc=""):
                stocks_id.append(stock_id.strip())

        data = dict()
        for stock_id in tqdm.tqdm(stocks_id, desc='retrieving stock symbols'):
            stock_xpath = get_stock_xpath(stock_id)
            stock_info_xpath = stock_xpath + info_xpath
            symbol = cls.H.get_attr(cls.H.get_element(main_element, xpath=stock_info_xpath),
                                    attr='text', prop=True)
            if cls.H.validate(symbol, tipe=str, value_exc=""):
                data[stock_id] = {'symbol': symbol.strip()}

        driver.close()
        os.remove(downloaded_file_path)

        TseTmcController.append_data_entry(data)
        TseTmcController.dump_symbol_to_index_list()
