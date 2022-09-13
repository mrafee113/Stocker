from utils.web.scrapy import Pipeline
from resources.models import Company, TickerPrice


class TseTmcPriceRecordsPipeline(Pipeline):
    @classmethod
    def item_to_db_map(cls):
        return {
            k: k for k in
            {'tsetmc_index', 'date', 'open', 'high', 'low', 'adj_close', 'value', 'volume', 'count', 'close'}
        }

    @classmethod
    def export_to_db(cls, items: list[dict]):
        company_index_to_ids = {cindex: cid for cindex, cid in Company.objects.values_list('tsetmc_index', 'id')}
        to_create_objs = list()
        for item in items:
            if item['tsetmc_index'] not in company_index_to_ids:
                continue  # todo: log warning

            index = item['tsetmc_index']
            del item['tsetmc_index']
            to_create_objs.append(TickerPrice(company_id=company_index_to_ids[index], **item))
        TickerPrice.objects.bulk_create(to_create_objs, ignore_conflicts=True)
