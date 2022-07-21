import json
from typing import Union

from scrapy.exceptions import UsageError

from utils.web.scrapy import ScrapyHandler


def parse_symbols_or_indexes_argument(symbols: Union[None, str, list[str]], raise_exception=True) -> Union[
    None, str, list[str]]:
    if isinstance(symbols, str) and symbols != 'all':
        try:
            symbols = json.loads(symbols)
        except json.JSONDecodeError:
            pass

    valid = ScrapyHandler.validate(symbols, tipe=list, value_exc=list()) and \
            all(map(lambda x: ScrapyHandler.validate(x, tipe=str, value_exc=str()), symbols))
    if not valid and symbols != 'all' and isinstance(symbols, str):
        if raise_exception:
            raise UsageError(f'symbols={symbols} is invalid. '
                             f'It has to be either "all" or a json-serializable list of strings.')
        return

    return symbols if valid or symbols == 'all' else 'all'
