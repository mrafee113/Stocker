import pandas as pd

from time import sleep
from django.conf import settings

from utils.web import requests_retry_session
from resources.tsetmc.downloader.abstract_downloader import AbstractDownloader


class ClientTypeRecordsDownloader(AbstractDownloader):
    path = settings.STOCKS_CLIENT_TYPE_DATA_PATH
    file_type = 'csv'

    @classmethod
    def get(cls, ticker_index: str, pbar):
        url = settings.TSE_STOCK_CLIENT_TYPE_DATA_FILE_URL.format(ticker_index=ticker_index)
        with requests_retry_session() as session:
            response = session.get(url, timeout=20)
        pbar.update(1)
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
    def get_attr(cls, index: str):
        return index

    @classmethod
    def save(cls, df: pd.DataFrame, path):
        df.to_csv(path)
