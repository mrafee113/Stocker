import os

from pathlib import Path
from concurrent import futures
from typing import List, Union

from tsetmc.client.utils.stocks_details import StockController


class AbstractDownloader:
    path = NotImplementedError
    file_type = NotImplementedError

    def __init__(self, symbols: Union[List, str]):
        if symbols == 'all':
            symbols = StockController.get_all_symbols()
        elif isinstance(symbols, str):
            symbols = [symbols]

        self.symbols = symbols
        self._download()

    def _download(self):
        result_list = dict()  # for debugging only
        future_to_symbol = dict()
        with futures.ThreadPoolExecutor(max_workers=12) as executor:
            for symbol in self.symbols:
                try:
                    attr = self.get_attr(symbol)
                except Exception:
                    continue

                future = executor.submit(self.download, attr)
                future_to_symbol[future] = symbol

        for future in futures.as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            result = future.result()
            if result is None:
                print(f'Downloading {symbol} returned 200 but empty string.')
                continue

            result = self.process(result)
            result_list[symbol] = result
            Path(self.path).mkdir(parents=True, exist_ok=True)
            self.save(result, os.path.join(self.path, f'{symbol}.{self.file_type}'))

        if len(result_list) != len(self.symbols):
            print('Warning, download did not complete, re-run the code')

    @classmethod
    def download(cls, attr):
        raise NotImplementedError

    @classmethod
    def process(cls, result):
        raise NotImplementedError

    @classmethod
    def get_attr(cls, symbol):
        raise NotImplementedError

    @classmethod
    def save(cls, result, path):
        raise NotImplementedError
