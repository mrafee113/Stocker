from utils.web.scrapy import Pipeline
from resources.models import Company, CapitalIncrease


class TseTmcCapitalIncreaseHistoryPipeline(Pipeline):
    @classmethod
    def item_to_db_map(cls):
        return {
            k: k for k in
            {'tsetmc_index', 'prev_stocks', 'next_stocks', 'date'}
        }

    @classmethod
    def export_to_db(cls, items: list[dict]):
        company_index_to_ids = {cindex: cid for cindex, cid in Company.objects.values_list('tsetmc_index', 'id')}
        to_create_objs = list()
        for item in items:
            if item['tsetmc_index'] not in company_index_to_ids:
                continue

            index = item['tsetmc_index']
            del item['tsetmc_index']
            to_create_objs.append(CapitalIncrease(company_id=company_index_to_ids[index], **item))

        n = CapitalIncrease.objects.bulk_create(to_create_objs)
