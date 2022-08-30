import bs4

from time import sleep
from django.conf import settings

from utils.web import requests_retry_session
from resources.tsetmc.controller import TseTmcController
from resources.tsetmc.downloader.abstract_downloader import AbstractDownloader


# todo:
#   plus. don't store csv. store in a json, and most importantly, in DB.
class ShareholdersDownloader(AbstractDownloader):
    path = settings.STOCKS_SHAREHOLDERS_DATA_PATH
    file_type = 'csv'

    @classmethod
    def save(cls, data: list[dict], path):
        pass  # fixme please!
        # todo: save to db first. I guess.

    @classmethod
    def get_attr(cls, index: str):
        try:
            ci_sin = TseTmcController.stocks_details()[index]['ci_sin']
        except KeyError as exc:
            print(f'Warning! before downloading price records for {index}, finding ci_sin failed.')
            raise exc

        return ci_sin

    @classmethod
    def get(cls, ci_sin: str, pbar):
        url = settings.TSE_STOCK_SHAREHOLDERS_DATA_URL.format(ci_sin=ci_sin)
        page = requests_retry_session(retries=1).get(url, timeout=20)
        pbar.update(1)
        sleep(0.5)
        return page.content

    @classmethod
    def process(cls, page_content) -> list[dict]:
        soup = bs4.BeautifulSoup(page_content, 'html.parser')
        table: bs4.element.Tag = soup.find_all('table')[0]
        data = list()
        rows = table.find('tbody').find_all('tr')
        for row in rows:
            kwargs = dict()
            sh_id = row.attrs['onclick']
            sh_id = sh_id[sh_id.find("'") + 1:sh_id.find(",")]
            kwargs['shareholder_id'] = sh_id

            tds = row.find_all('td')
            kwargs['shareholder_name'] = tds[0].get_text().strip()
            kwargs['number_of_shares'] = cls.convert_to_number_if_number(tds[1].find('div').attrs['title'])
            kwargs['shares_percentage'] = cls.convert_to_number_if_number(tds[2].get_text().strip())
            kwargs['change'] = cls.convert_to_number_if_number(tds[3].get_text().strip())

            data.append(kwargs)

        return data

    @classmethod
    def convert_to_number_if_number(cls, s: str):
        try:
            return float(s.replace(",", ""))
        except ValueError:
            return s
