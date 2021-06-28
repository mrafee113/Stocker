from .client_type_records_downloader import ClientTypeRecordsDownloader
from .price_records_downloader import PriceRecordsDownloader
from .shareholders_downloader import ShareholdersDownloader

from typing import Union


def download(symbols: Union[list, str]):
    ClientTypeRecordsDownloader(symbols)
    PriceRecordsDownloader(symbols)
    ShareholdersDownloader(symbols)
