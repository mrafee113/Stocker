TSE_STOCK_DETAILS_URL = \
    "http://tsetmc.ir/Loader.aspx?ParTree=151311&i={ticker_index}"
TSE_STOCK_PRICE_DATA__FILE_URL = \
    "http://tsetmc.ir/tsev2/data/Export-txt.aspx?t=i&a=1&b=0&i={ticker_index}"
TSE_STOCK_CLIENT_TYPE_DATA_FILE_URL = \
    "http://www.tsetmc.ir/tsev2/data/clienttype.aspx?i={ticker_index}"
TSETMC_STOCK_PRICE_MOD_HISTORY_URL = \
    'http://tsetmc.ir/Loader.aspx?Partree=15131G&i={tsetmc_index}'
TSETMC_COMPANY_CAPITAL_INCREASE_HISTORY_URL = \
    "http://tsetmc.com/Loader.aspx?Partree=15131H&i={tsetmc_index}"

TSE_STOCK_SHAREHOLDERS_DATA_URL = \
    "http://www.tsetmc.ir/Loader.aspx?Partree=15131T&c={ci_sin}"
TSETMC_SYMBOL_ID_URL = \
    "http://www.tsetmc.ir/tsev2/data/search.aspx?skey={symbol}"

TSE_STOCKS_URL = \
    'http://www.tsetmc.ir/Loader.aspx?ParTree=15131F'
TSETMC_LIST_URL = \
    "http://www.tsetmc.ir/Loader.aspx?ParTree=111C1417"
TSETMC_MARKETWATCH_INIT_URL = \
    "http://www.tsetmc.ir/tsev2/data/MarketWatchInit.aspx?h=0&r=0"

CODAL_INFO_URL = \
    "https://codal.ir/Company.aspx?Symbol={codal_symbol}"
CODAL_REPORTS_URL = \
    "https://codal.ir/ReportList.aspx?search&Symbol={codal_symbol}"
MYCODAL_REPORTS_URL = \
    "https://my.codal.ir/fa/statements/?&symbol={mycodal_id}"
MYCODAL_COMPANY_LIST_URL = \
    'https://my.codal.ir/fa/publishers/?page={page_number}&per_page=100'
MYCODAL_DOCUMENT_LIST_URL = \
    "https://my.codal.ir/fa/statements/"

GECKO_DRIVER_LATEST_RELEASE_URL = \
    "https://api.github.com/repos/mozilla/geckodriver/releases/latest"
