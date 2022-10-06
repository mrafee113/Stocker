from .client_type_records_downloader import ClientTypeRecordsDownloader
from .price_records_downloader import PriceRecordsDownloader
from .shareholders_downloader import ShareholdersDownloader

from typing import Union


def download(symbols: Union[list, str] = None, indexes: Union[list, str] = None):
    ClientTypeRecordsDownloader.download(symbols=symbols, indexes=indexes)
    PriceRecordsDownloader.download(symbols=symbols, indexes=indexes)
    ShareholdersDownloader.download(symbols=symbols, indexes=indexes)
