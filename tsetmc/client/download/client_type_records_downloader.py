import pandas as pd

from time import sleep
from django.conf import settings

from tsetmc.client.utils import requests_retry_session
from tsetmc.client.utils.stocks_details import StockController
from tsetmc.client.download.abstract_downloader import AbstractDownloader


class ClientTypeRecordsDownloader(AbstractDownloader):
    path = settings.STOCKS_CLIENT_TYPE_DATA_PATH
    file_type = 'csv'

    @classmethod
    def download(cls, ticker_index: str):
        url = settings.TSE_STOCK_CLIENT_TYPE_DATA_FILE_URL.format(ticker_index=ticker_index)
        with requests_retry_session() as session:
            response = session.get(url, timeout=5)
        sleep(0.5)

        if not response.text:
            return None

        data = response.text.split(';')
        data = [row.split(',') for row in data]
        return pd.DataFrame(data, columns=[
            'date',
            "individual_buy_count", "corporate_buy_count",
            "individual_sell_count", "corporate_sell_count",
            "individual_buy_vol", "corporate_buy_vol",
            "individual_sell_vol", "corporate_sell_vol",
            "individual_buy_value", "corporate_buy_value",
            "individual_sell_value", "corporate_sell_value"
        ])

    @classmethod
    def process(cls, df: pd.DataFrame):
        for i in ["individual_buy", "individual_sell",
                  "corporate_buy", "corporate_sell"]:
            df[f'{i}_mean_price'] = (df[f'{i}_value'].astype(float) /
                                     df[f'{i}_vol'].astype(float))

        df['individual_ownership_change'] = (df['corporate_sell_vol'].astype(float) -
                                             df['corporate_buy_vol'].astype(float))

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
