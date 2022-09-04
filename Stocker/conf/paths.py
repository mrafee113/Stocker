import os
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
join = lambda *x: os.path.join(*x)  # noqa

DATA_PATH = join(_BASE_DIR, 'data')

STOCKS_PRICE_DATA_PATH = join(DATA_PATH, 'stock_prices')
STOCKS_CLIENT_TYPE_DATA_PATH = join(DATA_PATH, 'client_type_prices')
STOCKS_SHAREHOLDERS_DATA_PATH = join(DATA_PATH, 'shareholders')
CODAL_DATA_PATH = join(DATA_PATH, 'codal_financial_statements')
STOCK_DETAILS_FILEPATH = join(DATA_PATH, 'stocks_details.json')
STOCK_SYMBOLS_FILEPATH = join(DATA_PATH, 'stocks_symbols_to_indexes.json')
STOCK_ISIN_FILEPATH = join(DATA_PATH, 'stocks_isin_to_indexes.json')
STOCK_MYCODAL_ID_FILEPATH = join(DATA_PATH, 'stocks_mycodal_id_to_indexes.json')
CODAL_METADATA_FILEPATH = join(DATA_PATH, 'codal_docs_metadata.json')

SCRAPY_JOBSDIR = join(DATA_PATH, 'scrapy_jobs')

FIREFOX_DATA_PATH = os.path.join(DATA_PATH, 'firefox')
FIREFOX_USER_DATA_DIR = os.path.join(FIREFOX_DATA_PATH, 'user-data-dir')
FIREFOX_DOWNLOAD_DIR = os.path.join(FIREFOX_DATA_PATH, 'downloads')
