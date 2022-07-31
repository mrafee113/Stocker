from utils.web.scrapy import Pipeline
from resources.models import CorporateIndividualEntry, Company


class TseTmcCorporateIndividualPipeline(Pipeline):
    store_temporarily = True
    temporary_storage = 'cache'
    cache_key = 'corporate_individual_data'
    item_type = dict
    dict_key = 'tsetmc_index'

    @classmethod
    def item_to_db_map(cls):
        return {k: k for k in [
            'tsetmc_index', 'date',
            'individual_buy_count', 'corporate_buy_count', 'individual_sell_count', 'corporate_sell_count',
            'individual_buy_volume', 'corporate_buy_volume', 'individual_sell_volume', 'corporate_sell_volume',
            'individual_buy_value', 'corporate_buy_value', 'individual_sell_value', 'corporate_sell_value',
            'individual_buy_avg', 'corporate_buy_avg', 'individual_sell_avg', 'corporate_sell_avg',
            'ownership_change'
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
                objs.append(CorporateIndividualEntry(company_id=cid, **item))
        CorporateIndividualEntry.objects.bulk_create(objs, ignore_conflicts=True)
