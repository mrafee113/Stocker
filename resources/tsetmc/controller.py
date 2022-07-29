import os
import json
import tqdm

from pathlib import Path
from datetime import datetime, date
from django.conf import settings
from typing import Dict, Union

_stocks_details: Union[dict, None] = None
_symbols_to_indexes: Union[dict, None] = None
_isins_to_indexes: Union[dict, None] = None
_mycodal_id_to_indexes: Union[dict, None] = None


class TseTmcController:
    path = settings.STOCK_DETAILS_FILEPATH

    @classmethod
    def stocks_details(cls, force_reload=False, codal=False) -> dict:
        global _stocks_details
        if not cls.validate_file():
            cls.init_file()

        if _stocks_details is None or force_reload:
            with open(cls.path, encoding='utf-8') as file:
                _stocks_details = json.load(file)

        if codal:
            return {k: v for k, v in _stocks_details.items()}

        return _stocks_details

    @classmethod
    def symbols_to_indexes(cls, force_reload=False) -> dict:
        global _symbols_to_indexes
        path = settings.STOCK_SYMBOLS_FILEPATH
        if not os.path.exists(path) and not os.path.isfile(path):
            cls.dump_symbol_to_index_list()

        if _symbols_to_indexes is None or force_reload:
            with open(path, encoding='utf-8') as file:
                _symbols_to_indexes = json.load(file)

        return _symbols_to_indexes

    @classmethod
    def dump_symbol_to_index_list(cls):
        output = dict()
        for index, details in cls.stocks_details(force_reload=True).items():
            output[details['symbol']] = index
            if 'codal' in details:
                output[details['codal']['symbol']] = index

        with open(settings.STOCK_SYMBOLS_FILEPATH, 'w', encoding='utf-8') as file:
            json.dump(output, file, ensure_ascii=False, indent=2)

    @classmethod
    def isins_to_indexes(cls, force_reload=False) -> dict:
        global _isins_to_indexes
        path = settings.STOCK_ISIN_FILEPATH
        if not os.path.exists(path) and not os.path.isfile(path):
            cls.dump_isin_to_index_list()

        if _isins_to_indexes is None or force_reload:
            with open(path, encoding='utf-8') as file:
                _isins_to_indexes = json.load(file)

        return _isins_to_indexes

    @classmethod
    def dump_isin_to_index_list(cls):
        # isin = instrument_id
        output = dict()
        for index, details in cls.stocks_details(force_reload=True).items():
            output[details['instrument_id']] = index

        with open(settings.STOCK_ISIN_FILEPATH, 'w', encoding='utf-8') as file:
            json.dump(output, file, ensure_ascii=False, indent=2)

    @classmethod
    def mycodal_id_to_indexes(cls, force_reload=False) -> dict:
        global _mycodal_id_to_indexes
        path = settings.STOCK_MYCODAL_ID_FILEPATH
        if not os.path.exists(path) and not os.path.isfile(path):
            cls.dump_mycodal_id_to_index_list()

        if _mycodal_id_to_indexes is None or force_reload:
            with open(path, encoding='utf-8') as file:
                _mycodal_id_to_indexes = json.load(file)

        return _mycodal_id_to_indexes

    @classmethod
    def dump_mycodal_id_to_index_list(cls):
        output = dict()
        for index, details in cls.stocks_details(force_reload=True).items():
            if 'codal' not in details:
                continue
            output[details['codal']['mycodal_id']] = index

        with open(settings.STOCK_MYCODAL_ID_FILEPATH, 'w', encoding='utf-8') as file:
            json.dump(output, file, ensure_ascii=False, indent=2)

    @classmethod
    def get_max_codal_doc_last_updated(cls) -> date:
        last_date = date(1000, 1, 1)
        for index, details in cls.stocks_details().items():
            if 'docs_last_updated' in details:
                last_date = max(last_date, datetime.strptime(details['docs_last_updated'], '%Y/%m/%d').date())

        return last_date

    @classmethod
    def get_codal_doc_last_updated(cls, index: str) -> date:
        details = cls.get_details(index=index)
        if 'doc_last_updated' in details:
            return datetime.strptime(details['docs_last_updated'], '%Y/%m/%d').date()
        else:
            return date(1000, 1, 1)

    @classmethod
    def get_details(cls, symbol: str = None, index: str = None) -> dict:
        if symbol is not None:
            return cls.stocks_details()[cls.get_index(symbol)]
        if index is not None:
            return cls.stocks_details()[index]

    @classmethod
    def get_index(cls, symbol: str) -> str:
        return cls.symbols_to_indexes()[symbol]

    @classmethod
    def get_symbol(cls, index: str) -> str:
        return cls.stocks_details()[index]['symbol']

    @classmethod
    def get_all_symbols(cls) -> list:
        return list(cls.symbols_to_indexes().keys())

    @classmethod
    def get_all_indexes(cls, codal: bool = False) -> list:
        return list(cls.stocks_details(codal=codal).keys())

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

            for k, v in tqdm.tqdm(data.items(), desc='appending data to file'):
                if k in file_data:
                    file_data[k].update(v)
                else:
                    file_data[k] = v

            file.seek(0)
            json.dump(file_data, file, ensure_ascii=False, indent=2)
