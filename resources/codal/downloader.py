import json
import os
import tqdm
import copy
import jdatetime

from time import sleep
from pathlib import Path
from concurrent import futures
from typing import List, Union
from requests import HTTPError
from django.conf import settings

from resources.codal.controller import CodalController
from utils.web import requests_retry_session, get_random_user_agent
from resources.tsetmc.controller import TseTmcController


# fixme
class AbstractDownloader:

    def __init__(self, indexes: Union[List, str]):
        if indexes == 'all':
            indexes = TseTmcController.get_all_indexes(codal=True)
        elif isinstance(indexes, str):
            indexes = [indexes]

        self.indexes = indexes
        Path(settings.CODAL_DATA_PATH).mkdir(parents=True, exist_ok=True)
        self._download()

    def _download(self):
        result_counter = 0  # for debugging only
        document_counter = 0  # same as above
        future_to_index = dict()
        downloaded_docs = list()
        description = str(self.__class__).split('.')[-1][:-2]  # <class '__main__.{class_name}'>
        with tqdm.tqdm(total=len(self.indexes), desc=description) as pbar:
            with futures.ThreadPoolExecutor(max_workers=12) as executor:
                documents = list()
                for index in self.indexes:
                    documents.extend(self.get_documents(index))
                document_counter = len(documents)
                for doc in documents:
                    if doc['downloaded'] and doc['relative_file_path'] is not None:
                        continue
                    try:
                        attrs = self.get_attributes(doc)
                    except Exception:
                        continue

                    future = executor.submit(self.download, attrs, pbar)
                    future_to_index[future] = index

            for future in futures.as_completed(future_to_index):
                index = future_to_index[future]
                result, attrs = future.result()
                if result is None:
                    print(f'Downloading {index}::{attrs["release_date"]} returned 200 but empty string.')
                    continue

                result_counter += 1
                self.save(result, attrs)
                downloaded_docs.append(attrs)

        if result_counter != len(self.indexes):
            print(f'Warning, download did not complete, re-run the code. '
                  f'supposed={len(self.indexes)} != reality={result_counter}')

    @classmethod
    def download(cls, attrs: dict, pbar) -> tuple[bytes, dict]:
        url = attrs['pdf_link']
        with requests_retry_session() as session:
            response = session.get(url, timeout=120, headers={'User-Agent': get_random_user_agent()})
        pbar.update(1)
        sleep(0.5)

        try:
            response.raise_for_status()
        except HTTPError:
            return cls.download(attrs, pbar)  # tries until maximum recursion depth exceeded

        return response.content, attrs

    @classmethod
    def get_attributes(cls, doc: dict) -> dict:
        return {
            k: v
            for k, v in doc.items()
            if k not in ['mycodal_statement_link']
        }

    @classmethod
    def save(cls, pdf: bytes, attrs: dict):
        path = cls.get_file_path(attrs)
        with open(path, 'wb') as file:
            file.write(pdf)

    @classmethod
    def get_file_path(cls, attrs: dict) -> str:
        index_path = os.path.join(settings.CODAL_DATA_PATH, attrs['index'])
        Path(index_path).mkdir(parents=True, exist_ok=True)

        year = jdatetime.date.fromgregorian(date=attrs['period_end_date']).strftime('%Y')
        year_path = os.path.join(index_path, year)
        Path(year_path).mkdir(exist_ok=True)

        file_name = CodalController.gen_file_name(attrs)
        file_name = f'{file_name}.pdf'

        return os.path.join(year_path, file_name)

    @classmethod
    def get_documents(cls, index: str) -> list[dict]:
        metadatas = CodalController.metadata()
        if index in metadatas:
            docs = list()
            for doc in metadatas[index]:
                doc = copy.deepcopy(doc)
                doc['index'] = index
                docs.append(doc)

            return docs

        return list()

    # @classmethod
    # def update_codal_metadata(cls, downloaded_docs: list[dict]):
    #     # todo: move to controller
    #     _tmp = defaultdict(list)
    #     for doc in downloaded_docs:
    #         index = doc['index']
    #         del doc['index']
    #         doc['file_path'] = cls.get_file_path(doc)
    #         _tmp[index].append(doc)
    #
    #     _tmp = defaultdict(list)
    #     downloaded_docs: dict[list] = _tmp
    #     for index, docs in CodalController.metadata():
    #         doclist = list()
    #         for doc1 in docs:
    #             for doc2 in downloaded_docs[index]:
    #                 if all([doc1[key] == doc2[key]
    #                         for key in ['release_date', 'period_length', 'period_end_date', 'aggregated', 'audited']]):
    #                     doc = copy.deepcopy(doc1)
    #                     doc['downloaded'] = True
    #                     doc['file_path'] = doc2['file_path']
    #                     doclist.append(doc)
    #         _tmp[index] = doclist
    #
    #     # fixme: name is .new. fix after test passed
    #     with open(settings.CODAL_METADATA_FILEPATH + '.new', 'w', encoding='utf-8') as file:
    #         json.dump(_tmp, file, ensure_ascii=False, index=2)
    #     # fixme: highly dangerous
