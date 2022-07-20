import os
import tqdm
import json
import jdatetime
import urllib.parse

from pathlib import Path
from datetime import date
from django.conf import settings
from collections import defaultdict
from utils.datetime import dt_from_str

_codal_metadata = None


class CodalController:
    metadata_path = settings.CODAL_METADATA_FILEPATH
    data_path = settings.CODAL_DATA_PATH

    @classmethod
    def metadata(cls, force_reload=False) -> dict:
        global _codal_metadata
        if not cls.validate_file(cls.metadata_path):
            cls.init_file(cls.metadata_path)

        if _codal_metadata is None or force_reload:
            with open(cls.metadata_path, encoding='utf-8') as file:
                _codal_metadata = json.load(file)

            cls._objectify_dates()

        return _codal_metadata

    @classmethod
    def _objectify_dates(cls):
        global _codal_metadata
        if _codal_metadata is None:
            return

        _tmp = defaultdict(list)
        for index, doclist in _codal_metadata.items():  # noqa
            for doc in doclist:
                doc['period_end_date'] = dt_from_str(doc['period_end_date'])
                doc['release_date'] = dt_from_str(doc['release_date'])
            _tmp[index].extend(doclist)

        _codal_metadata = _tmp

    @classmethod
    def validate_file(cls, path):
        return os.path.exists(path) and os.path.isfile(path)

    @classmethod
    def init_file(cls, path):
        Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(dict(), file)

    @classmethod
    def append_data_entry(cls, documents: dict):
        """no datetime or date objects should exist. date(time)s should be strings."""
        if not cls.validate_file(cls.metadata_path):
            cls.init_file(cls.metadata_path)

        with open(cls.metadata_path, 'r+', encoding='utf-8') as file:
            data: dict = json.load(file)
            for index, doclist in tqdm.tqdm(documents.items(), desc='appending codal docs metadata to file'):
                if index in data:
                    for doc in doclist:
                        if doc in data[index]:
                            continue
                        else:
                            data[index].append(doc)

                    data[index] = sorted(data[index], key=lambda x: x['release_date'])
                else:
                    data[index] = doclist

            file.seek(0)
            json.dump(data, file, ensure_ascii=False, indent=2)

    @classmethod
    def get_metadata(cls, index: str = None, symbol: str = None) -> list[dict]:
        if symbol is not None:
            from resources.tsetmc.controller import TseTmcController
            index = TseTmcController.get_index(symbol)

        return cls.metadata()[index]

    @classmethod
    def scrape_codal_companies(cls):
        from resources.codal.scraper.company_scraper import MyCodalCompanyScraper
        MyCodalCompanyScraper.scrape()

    @classmethod
    def scrape_codal_documents(cls, minimized=True, from_date: date = None, to_date: date = None):
        from resources.codal.scraper.document_scraper import MyCodalDocumentScraper
        MyCodalDocumentScraper.scrape(minimized, from_date, to_date)

    @classmethod
    def gen_file_name(cls, doc: dict) -> str:
        period_end_date = doc['period_end_date']
        period_end_date = jdatetime.date.fromgregorian(date=period_end_date)
        period_end_date = period_end_date.strftime('%Y_%m_%d')

        release_date = doc['release_date']
        release_date = jdatetime.datetime.fromgregorian(datetime=release_date)
        release_date = release_date.strftime('%Y_%m_%d_%H_%M_%S')

        aggregated = doc['aggregated']
        aggregated = 'aggregated' if aggregated else 'unaggregated'

        audited = doc['audited']
        audited = 'audited' if audited else 'unaudited'

        return f'{period_end_date}__{doc["period_length"]}__{release_date}__{aggregated}__{audited}'

    @classmethod
    def get_statement_id(cls, doc: dict) -> str:
        return str([i for i in urllib.parse.urlparse(doc["mycodal_statement_link"]).path.split('/') if i][-1])
