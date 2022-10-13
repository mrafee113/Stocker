from itemadapter import ItemAdapter
from utils.web.scrapy import Pipeline
from resources.models import Company


class TseTmcOverviewPipeline(Pipeline):
    store_temporarily = True
    temporary_storage = 'cache'
    cache_key = 'overview'
    item_type = dict
    dict_key = 'tsetmc_index'

    @classmethod
    def item_to_db_map(cls) -> dict:
        return {k: k for k in [
            'title', 'explanation', 'tsetmc_index'
        ]}

    @classmethod
    def validate_item(cls, adapter: ItemAdapter) -> tuple[bool, str]:
        if 'title' not in adapter:
            return False, 'title'

        return True, str()

    @classmethod
    def export_to_db(cls, items: dict):
        indexes = list(items.keys())
        companies = Company.objects.filter(tsetmc_index__in=indexes)
        if not len(companies):
            return
        for tsetmc_index, item in items.items():
            if not item:
                continue
            item = item[0]
            for company in companies:
                if company.tsetmc_index == item['tsetmc_index']:
                    company.tsetmc_overview_title = item['title']
                    if 'explanation' in item and item['explanation'] is not None:
                        company.tsetmc_market_explanation = item['explanation']
                    break
        Company.objects.bulk_update(companies, ['tsetmc_overview_title', 'tsetmc_market_explanation'])
