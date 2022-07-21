import os
import tqdm

from pathlib import Path
from concurrent import futures
from typing import List, Union

from resources.tsetmc.controller import TseTmcController


class AbstractDownloader:
    path = NotImplementedError
    file_type = NotImplementedError

    @classmethod
    def download(cls, symbols: Union[List, str] = None, indexes: Union[List, str] = None):
        if indexes is not None:
            if indexes == 'all':
                indexes = TseTmcController.get_all_indexes()
            elif isinstance(indexes, str):
                indexes = [indexes]
        elif symbols is not None:
            if symbols == 'all':
                symbols = TseTmcController.get_all_symbols()
            elif isinstance(symbols, str):
                symbols = [symbols]

            indexes = [TseTmcController.get_index(symbol) for symbol in symbols]
        else:
            raise ValueError("No values provided for indexes or symbols.")

        result_list = dict()  # for debugging only
        future_to_index = dict()
        description = str(cls.__name__)
        with tqdm.tqdm(total=len(indexes), desc=description) as pbar:
            with futures.ThreadPoolExecutor(max_workers=12) as executor:
                for index in indexes:
                    try:
                        attr = cls.get_attr(index)
                    except Exception:
                        continue

                    future = executor.submit(cls.get, attr, pbar)
                    future_to_index[future] = index

            for future in futures.as_completed(future_to_index):
                index = future_to_index[future]
                result = future.result()
                if result is None:
                    print(f'Downloading {index} returned 200 but empty string.')
                    continue

                result = cls.process(result)
                result_list[index] = result
                Path(self.path).mkdir(parents=True, exist_ok=True)  # noqa
                self.save(result, os.path.join(self.path, f'{index}.{self.file_type}'))  # noqa

        if len(result_list) != len(indexes):
            print(f'Warning, download did not complete, re-run the code. '
                  f'supposed={len(indexes)} != reality={len(result_list)}')

    @classmethod
    def get(cls, attr, pbar: tqdm.tqdm):
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
