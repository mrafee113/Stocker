import os
import json
import subprocess

from scrapy.item import Item
from pathlib import PosixPath
from django.conf import settings
from scrapy.spiders import Spider
from itemadapter import ItemAdapter
from datetime import datetime, date
from django.core.cache import caches
from scrapy.exceptions import DropItem


class Pipeline:
    folder: PosixPath = NotImplementedError
    item_date_attributes: list[str] = ['date']
    store_temporarily: bool = False
    temporary_storage: str = 'file'
    item_type: type = list
    dict_key: str = NotImplementedError
    cache_key: str = NotImplementedError

    @classmethod
    def item_to_db_map(cls) -> dict:
        raise NotImplementedError()

    @classmethod
    def export_to_db(cls, items: list[dict]):
        raise NotImplementedError()

    @property
    def filename(self) -> str:
        return NotImplementedError

    def __init__(self):
        self.items = self.item_type()

    def open_spider(self, spider: Spider):
        spider.pipeline = self

    def close_spider(self, spider: Spider):
        if len(self.items) > 0:
            if self.store_temporarily:
                match self.temporary_storage:
                    case 'file':
                        self.export_to_file(self.filename)
                    case 'cache':
                        self.export_to_cache()
                self.run_subprocess()
            else:
                self.export_to_db(self.items)

    def process_item(self, item: Item, spider: Spider):
        adapter = ItemAdapter(item)
        validated, reason = self.validate_item(adapter)
        if validated:
            adapter = self.convert_item(adapter)
            if self.item_type == list:
                self.items.append(adapter)
            elif self.item_type == dict:
                key = adapter.get(self.dict_key)
                if key not in self.items or not self.items[key]:
                    self.items[key] = list()
                self.items[key].append(adapter)
        else:
            DropItem(f"Item not validated. reason={reason}")

        return item

    @classmethod
    def convert_item(cls, adapter: ItemAdapter) -> dict:
        return {
            v: adapter.get(k)
            for k, v in cls.item_to_db_map().items()
        }

    @classmethod
    def validate_item(cls, adapter: ItemAdapter) -> tuple[bool, str]:
        for key in cls.item_to_db_map().keys():
            if key not in adapter:
                return False, key

        return True, str()

    def convert_dates(self, to: str):
        for item in self.items:
            for date_attr in self.item_date_attributes:
                dt = item[date_attr]
                match to:
                    case 'python':
                        try:
                            value = datetime.strptime(dt, '%Y/%m/%d %H:%M')
                        except ValueError:
                            value = datetime.strptime(dt, '%Y/%m/%d').date()
                        item[date_attr] = value
                    case 'json':
                        item[date_attr] = dt.strftime('%Y/%m/%d') if isinstance(dt, date) else \
                            dt.strftime('%Y/%m/%d %H:%M')

    def export_to_file(self, filename: str):
        self.folder.mkdir(exist_ok=True)
        file = self.folder / f'{filename}.json'
        self.convert_dates('json')
        with open(file, 'w') as file:
            json.dump(self.items, file)

    def import_from_file(self, filename: str):
        file = self.folder / f'{filename}.json'
        if file.exists():
            with open(file) as file:
                self.items.extend(json.load(file))

            self.convert_dates('python')

    def export_to_cache(self):
        cache = caches['default']
        cache.set(self.cache_key, self.items)

    def import_from_cache(self):
        cache = caches['default']
        self.items = cache.get(self.cache_key)
        cache.set(self.cache_key, dict())

    @classmethod
    def load_data_into_db(cls):
        pipeline = cls()
        match cls.temporary_storage:
            case 'file':
                for file in cls.folder.iterdir():
                    if not file.is_file():
                        continue
                    suffix = file.suffix.replace('.', '')
                    if not suffix or suffix != 'json':
                        continue
                    name = str(file.name).replace(f'.{suffix}', str())
                    if not name.isnumeric():
                        continue

                    pipeline.import_from_file(name)
                    os.remove(str(file))

            case 'cache':
                pipeline.import_from_cache()

        pipeline.export_to_db(pipeline.items)

    @classmethod
    def run_subprocess(cls):
        cmd = f'/home/mehdi/.venvs/stocker/bin/python {settings.BASE_DIR / "manage.py"} subprocess_pipeline ' \
              f'--package {cls.__module__} --pipeline {cls.__name__}'
        print('-' * 100 + '\n' + cmd + '\n' + '-' * 100)
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        process.communicate()
