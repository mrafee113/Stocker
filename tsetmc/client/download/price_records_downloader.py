import pandas as pd

from time import sleep
from io import StringIO
from requests import HTTPError
from django.conf import settings

from tsetmc.client.utils import requests_retry_session
from tsetmc.client.utils.stocks_details import StockController
from tsetmc.client.download.abstract_downloader import AbstractDownloader


class PriceRecordsDownloader(AbstractDownloader):
    path = settings.STOCKS_PRICE_DATA_PATH
    file_type = 'csv'

    @classmethod
    def download(cls, ticker_index: str):
        url = settings.TSE_STOCK_PRICE_DATA__FILE_URL.format(ticker_index=ticker_index)
        with requests_retry_session() as session:
            response = session.get(url, timeout=10)
        sleep(0.5)

        try:
            response.raise_for_status()
        except HTTPError:
            return cls.download(ticker_index)  # tries until maximum recursion depth exceeded

        data = StringIO(response.text)
        return pd.read_csv(data)

    @classmethod
    def process(cls, df: pd.DataFrame):
        df = df.iloc[::-1]

        history_field_map = {
            "<DTYYYYMMDD>": "date",
            "<FIRST>": "open",
            "<HIGH>": "high",
            "<LOW>": "low",
            "<LAST>": "close",
            "<VOL>": "volume",
            "<CLOSE>": "adjClose",
            "<OPENINT>": "count",
            "<VALUE>": "value"
        }
        df = df.rename(columns=history_field_map)

        df = df.drop(columns=["<PER>", "<OPEN>", "<TICKER>"])
        df.date = pd.to_datetime(df.date, format='%Y%m%d')
        df.set_index('date', inplace=True)
        return df

    @classmethod
    def get_attr(cls, symbol: str):
        try:
            index = StockController.stocks_details()[symbol]['index']
        except KeyError as exc:
            print(f'Warning! before downloading price records for {symbol}, finding index failed.')
            raise exc

        return index

    @classmethod
    def save(cls, df: pd.DataFrame, path):
        df.to_csv(path)
