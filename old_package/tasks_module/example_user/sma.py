import pandas_ta as ta

from utilities.datetime import today, timedelta
from celery import shared_task
from tsetmc.tasks_module.abstract_task import Analysis, metadata_wrapper
from tsetmc.client import Ticker


class SMA(Analysis):
    username = 'bardiam'

    @classmethod
    def analyze(cls, ticker: Ticker):
        df = ticker.history

        columns = ['close', 'open', 'high', 'low', 'date', 'volume']
        columns = {c: c.title() for c in columns}
        df.rename(columns=columns, inplace=True)

        end = today()
        begin = today() - timedelta(days=100)
        df = df[begin:end]

        sma10 = ta.sma(df['Close'])
        sma10 = sma10.dropna()
        return sum(sma10) / len(sma10)

    @classmethod
    def conditioning(cls, analysis_results) -> bool:
        if analysis_results > 2500:
            return True
        return False


@shared_task
def sma(stocks: list[str], task: str):
    return SMA.run(stocks, task)
