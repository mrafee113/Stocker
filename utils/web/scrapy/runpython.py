import os

from django.conf import settings as django_settings
from scrapy.crawler import CrawlerRunner, CrawlerProcess, Crawler
from scrapy.utils.project import get_project_settings


# todo: create timer decorator
# todo: add logging
# todo: add testing... maybe? maybe not?

def scrapy_crawler(spider_name: str, **spider_kwargs):
    cur_dir = os.getcwd()
    os.chdir(os.path.join(django_settings.BASE_DIR, 'scrapy_scrapers'))
    os.environ['SCRAPY_SETTINGS_MODULE'] = 'scrapy_scrapers.settings'
    settings = get_project_settings()
    spider_loader = CrawlerRunner._get_spider_loader(settings)
    spider_klass = spider_loader.load(spider_name)

    process = CrawlerProcess(settings)
    crawler = Crawler(spider_klass, settings=settings)
    process.crawl(crawler, **spider_kwargs)
    process.start()
    os.chdir(cur_dir)
    return {'settings': settings, 'process': process, 'crawler': crawler, 'spider_class': spider_klass}
