import os
import pandas as pd

from typing import Union
from django.conf import settings

from resources.tsetmc.controller import TseTmcController


class Ticker:
    def __init__(self, **kw):
        if 'symbol' in kw:
            self.symbol = kw['symbol']
            self.index = TseTmcController.get_index(self.symbol)
        elif 'index' in kw:
            self.index = kw['index']
            self.symbol = TseTmcController.get_symbol(self.index)

        details = TseTmcController.get_details(symbol=self.symbol)
        self.instrument_id = details['instrument_id']
        self.ci_sin = details['ci_sin']
        self.title = details['title']
        self.group_name = details['group_name']
        self.base_volume = details['base_volume']

        self.url = settings.TSE_STOCK_DETAILS_URL.format(ticker_index=self.index)
        self._client_types_url = settings.TSE_STOCK_CLIENT_TYPE_DATA_FILE_URL.format(ticker_index=self.index)

        self._price_csv_path = os.path.join(settings.STOCKS_PRICE_DATA_PATH, f'{self.index}.csv')
        self._client_type_csv_path = os.path.join(settings.STOCKS_CLIENT_TYPE_DATA_PATH, f'{self.index}.csv')
        self._shareholders_csv_path = os.path.join(settings.STOCKS_SHAREHOLDERS_DATA_PATH, f'{self.index}.csv')

        self._history: Union[pd.DataFrame, None] = None
        self._client_types: Union[pd.DataFrame, None] = None
        self._shareholders: Union[pd.DataFrame, None] = None

    @property
    def history(self) -> Union[pd.DataFrame, None]:
        if self._history is None:
            if os.path.exists(self._price_csv_path):
                self._history = pd.read_csv(self._price_csv_path, index_col=['date'], parse_dates=True)

        return self._history

    @property
    def client_types(self) -> Union[pd.DataFrame, None]:
        if self._client_types is None:
            if os.path.exists(self._client_type_csv_path):
                self._client_types = pd.read_csv(self._client_type_csv_path)

        return self._client_types

    @property
    def shareholders(self) -> Union[pd.DataFrame, None]:
        if self._shareholders is None:
            if os.path.exists(self._shareholders_csv_path):
                self._shareholders = pd.read_csv(self._shareholders_csv_path)

        return self._shareholders

    def reset_data(self):
        self._shareholders = self._client_types = self._history = None
