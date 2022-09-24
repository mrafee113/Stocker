from utils.web.scrapy import Pipeline
from resources.models import Company, DPS


class TseTmcDPSPipeline(Pipeline):
    store_temporarily = True
    temporary_storage = 'cache'
    cache_key = 'dps'
    item_type = dict
    dict_key = 'tsetmc_index'

    @classmethod
    def item_to_db_map(cls):
        return {k: k for k in [
            'issuance_date', 'assembly_date', 'fiscal_date',
            'dividends', 'dps', 'tsetmc_index'
        ]}

    @classmethod
    def export_to_db(cls, items: dict):
        companies = Company.objects.values_list('id', 'tsetmc_index')
        index_to_id_map = {pair[1]: pair[0] for pair in companies}
        objs = list()
        for index, items in items.items():
            for item in items:
                item.pop('tsetmc_index')
                cid = index_to_id_map[index]
                objs.append(DPS(company_id=cid, **item))
        DPS.objects.bulk_create(objs, ignore_conflicts=True)
