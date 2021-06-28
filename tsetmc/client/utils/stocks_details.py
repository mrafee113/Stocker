import os
import bs4
import json
import time
import helium
import requests

from math import sqrt
from pathlib import Path
from concurrent import futures
from django.conf import settings
from typing import Dict, Union, Iterable, List
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webelement import WebElement

_stocks_details = None


class StockController:
    path = settings.STOCK_DETAILS_FILEPATH

    @classmethod
    def stocks_details(cls, force_reload=False) -> dict:
        global _stocks_details
        if not cls.validate_file():
            cls.init_file()

        if _stocks_details is None or force_reload:
            with open(cls.path, encoding='utf-8') as file:
                _stocks_details = json.load(file)

        return _stocks_details

    @classmethod
    def get_details(cls, symbol: str = None, index: str = None) -> dict:
        if symbol is not None:
            return cls.stocks_details()[symbol]
        if index is not None:
            return cls.stocks_details()[cls.get_symbol(index)]

    @classmethod
    def get_index(cls, symbol: str) -> str:
        return cls.stocks_details()[symbol]['index']

    @classmethod
    def get_symbol(cls, index: str) -> str:
        for symbol, details in cls.stocks_details().items():
            if details['index'] == index:
                return symbol
        raise KeyError('index not found using symbol')

    @classmethod
    def get_all_symbols(cls) -> list:
        return list(cls.stocks_details().keys())

    @classmethod
    def get_all_indexes(cls) -> list:
        return [details['index'] for symbol, details in cls.stocks_details().items()]

    @classmethod
    def init_file(cls):
        Path(os.path.dirname(cls.path)).mkdir(parents=True, exist_ok=True)
        with open(cls.path, 'w', encoding='utf-8') as file:
            json.dump(dict(), file)

    @classmethod
    def validate_file(cls):
        return os.path.exists(cls.path) and os.path.isfile(cls.path)

    @classmethod
    def append_data_entry(cls, data: Dict[str, dict]):
        """Does support multiple entries.
        Usage: append_data_entry(data={"name1": {data1}, "name2": {data2}})
        """
        if not cls.validate_file():
            cls.init_file()

        with open(cls.path, 'r+', encoding='utf-8') as file:
            file_data: dict = json.load(file)

            for k, v in data.items():
                if k in file_data:
                    file_data[k].update(v)
                else:
                    file_data[k] = v

            file.seek(0)
            json.dump(file_data, file, ensure_ascii=False, indent=2)

    @classmethod
    def scrape_metadata(cls, refresh_indexes=False):
        if refresh_indexes:
            cls.scrape_symbols_and_indexes()

        force_reload_details = False
        if refresh_indexes:
            force_reload_details = True

        stock_details = cls.stocks_details(force_reload_details)
        indexes = [detail['index'] for detail in stock_details.values()]
        responses: Dict[str, requests.Response] = cls._retrieve_stocks(indexes)

        data = dict()
        scrape_map = {
            'instrument_id': 'InstrumentID',
            'ci_sin': 'CIsin',
            'title': 'Title',
            'group_name': 'LSecVal',
            'base_volume': 'BaseVol'
        }
        for symbol, details in stock_details.items():
            response = responses[details['index']]
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
            data[symbol] = kw

        cls.append_data_entry(data)

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
        with futures.ThreadPoolExecutor(max_workers=len(sections)) as executor:
            for sec_idx, section in enumerate(sections):
                future = executor.submit(cls._request_stocks, section)
                future_to_sec_idx[future] = sec_idx

            for future in futures.as_completed(future_to_sec_idx):
                responses = future.result()

                for index, response in responses.items():
                    result_list[index] = response

        return result_list

    @classmethod
    def _request_stocks(cls, section: List[str]):
        responses = dict()
        for index in section:
            url = settings.TSE_STOCK_DETAILS_URL.format(ticker_index=index)
            responses[index] = requests.get(url)
            time.sleep(0.1)

        return responses

    @classmethod
    def scrape_symbols_and_indexes(cls):
        if not cls.validate_file():
            cls.init_file()

        url = settings.TSE_STOCKS_URL
        try:
            web_driver = helium.start_chrome(url, headless=True)
        except WebDriverException as exc:
            print(f'Warning. {exc}')

        time.sleep(5)
        main_xpath = '//div[@class="other" and @id="main"]'
        abstract_stock_xpath = '//child::div[@class="{c}"]'

        def get_stock_xpath(cid):
            return f'{abstract_stock_xpath[:-1]} and @id="{cid}"]'

        info_xpath = '//child::div[1]/child::a[@class="inst"]'
        main_element = cls.get_element(web_driver, main_xpath)
        stock_sections = cls.get_element(main_element, abstract_stock_xpath, many=True)
        stocks_id = list()
        for stock_section in stock_sections:
            stock_id = cls.get_attr(stock_section, 'id')
            if stock_id is None or not stock_id or not isinstance(stock_id, str):
                continue
            stocks_id.append(stock_id.strip())

        data = dict()
        for stock_id in stocks_id:
            stock_xpath = get_stock_xpath(stock_id)
            stock_info_xpath = stock_xpath + info_xpath
            info_element = cls.get_element(main_element, stock_info_xpath)
            symbol = info_element.text
            if symbol is None or not symbol or not isinstance(symbol, str):
                continue
            data[symbol.strip()] = {'index': stock_id}

        try:
            web_driver.close()
            helium.kill_browser()
        except Exception as exc:
            print(exc)

        cls.append_data_entry(data)

    @classmethod
    def get_element(cls, el: WebElement, xpath: str, many=False) -> Union[WebElement, None, Iterable[WebElement]]:
        try:
            if many:
                return el.find_elements_by_xpath(xpath)
            return el.find_element_by_xpath(xpath)
        except Exception as exc:
            print(exc)

    @classmethod
    def get_attr(cls, el: WebElement, attr: str) -> Union[str, None]:
        try:
            return el.get_attribute(attr)
        except Exception as exc:
            print(exc)
