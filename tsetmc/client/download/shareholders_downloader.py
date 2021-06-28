import bs4
import pandas as pd

from time import sleep
from typing import List, Tuple
from django.conf import settings

from tsetmc.client.utils import requests_retry_session
from tsetmc.client.utils.stocks_details import StockController
from tsetmc.client.download.abstract_downloader import AbstractDownloader


class ShareholdersDownloader(AbstractDownloader):
    path = settings.STOCKS_SHAREHOLDERS_DATA_PATH
    file_type = 'csv'

    @classmethod
    def save(cls, df: pd.DataFrame, path):
        df.to_csv(path, index=False)

    @classmethod
    def get_attr(cls, symbol: str):
        try:
            ci_sin = StockController.stocks_details()[symbol]['ci_sin']
        except KeyError as exc:
            print(f'Warning! before downloading price records for {symbol}, finding ci_sin failed.')
            raise exc

        return ci_sin

    @classmethod
    def download(cls, ci_sin: str):
        url = settings.TSE_STOCK_SHAREHOLDERS_DATA_URL.format(instrument_id=ci_sin)
        page = requests_retry_session(retries=1).get(url, timeout=5)
        sleep(0.5)
        return page.content

    @classmethod
    def process(cls, page_content) -> pd.DataFrame:
        soup = bs4.BeautifulSoup(page_content, 'html.parser')
        table: bs4.PageElement = soup.find_all('table')[0]
        df: pd.DataFrame = cls._get_shareholders_html_table_as_csv(table)

        shareholders_field_map = {
            "سهامدار/دارنده": "shareholder",
            "سهم": "shares",
            "درصد": "percentage",
            "تغییر": "change",
        }
        df = df.rename(columns=shareholders_field_map)

        for header in df.columns:
            if header not in shareholders_field_map.values():
                del df[header]

        return df

    @classmethod
    def _get_shareholders_html_table_as_csv(cls, table: bs4.PageElement) -> pd.DataFrame:
        """
        given table element from shareholders page returns DatFrame
        Containing the table
        """
        header, rows = cls._get_html_table_header_and_rows(table)
        df_rows = []

        for row in rows:
            df_row = []
            for cell in row:
                cell_div = cell.find("div")
                if cell_div and cell_div.get_text() != "":
                    df_row.append(cls._convert_to_number_if_number(cell_div["title"]))
                else:
                    df_row.append(
                        cls._convert_to_number_if_number(cell.get_text().strip())
                    )
            df_rows.append(df_row)
        return pd.DataFrame(data=df_rows, columns=header)

    @classmethod
    def _get_html_table_header_and_rows(cls, table: bs4.PageElement) -> Tuple[List, List]:
        """
        return header and rows from a html table as a list
        """
        header = []
        rows = []
        table_header = table.find("tr")
        table_rows = table.find_all("tr")[1:]
        for items in table_header:
            header.append(items.get_text())

        for table_row in table_rows:
            row = []
            for cell in table_row.findAll(['th', 'td']):
                row.append(cell)
            rows.append(row)

        return header, rows

    @classmethod
    def _convert_to_number_if_number(cls, s: str):
        try:
            return float(s.replace(",", ""))
        except ValueError:
            return s
