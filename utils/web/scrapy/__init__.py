from .handler import ScrapyHandler
from .runpython import scrapy_crawler
from .spider import parse_symbols_or_indexes_argument
from .pipeline import Pipeline

import termcolor


def debug_print(*s, c='cyan'):
    print(termcolor.colored(' '.join(list(map(str, s))), c))
