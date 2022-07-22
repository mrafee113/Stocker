import os
import pickle

from pathlib import Path
from scrapy import signals
from scrapy.settings import BaseSettings
from scrapy.exceptions import NotConfigured


# todo: include pipeline cache
class CustomSpiderState:
    """Store and load spider state during a scraping job"""

    def __init__(self, jobdirs: dict = None):
        self.jobdirs = jobdirs
        self.jobdir = None

    @classmethod
    def job_dirs(cls, settings: BaseSettings) -> dict:
        return settings['SPIDER_JOBDIRS']

    @classmethod
    def ensure_path(cls, path: str):
        Path(path).mkdir(exist_ok=True, parents=True)

    @classmethod
    def from_crawler(cls, crawler):
        jobdir = cls.job_dirs(crawler.settings)
        if not jobdir:
            raise NotConfigured

        obj = cls(jobdir)

        crawler.signals.connect(obj.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(obj.spider_opened, signal=signals.spider_opened)
        return obj

    def set_jobdir(self, spider):
        if spider.name in self.jobdirs:
            self.jobdir = self.jobdirs[spider.name]
            self.ensure_path(self.jobdir)
        else:
            raise NotConfigured('fucked up the jobdirs dict... oops.')

    def spider_closed(self, spider):
        if self.jobdir is None:
            self.set_jobdir(spider)

        if self.jobdir:
            with open(self.statefn, 'wb') as f:
                pickle.dump(spider.state, f, protocol=4)

    def spider_opened(self, spider):
        if self.jobdir is None:
            self.set_jobdir(spider)

        if self.jobdir and os.path.exists(self.statefn):
            with open(self.statefn, 'rb') as f:
                spider.state = pickle.load(f)

        else:
            spider.state = {}

    @property
    def statefn(self):
        return os.path.join(self.jobdir, 'spider.state')
