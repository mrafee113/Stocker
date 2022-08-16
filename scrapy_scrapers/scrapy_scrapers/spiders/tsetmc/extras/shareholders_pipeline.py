from utils.web.scrapy import Pipeline
from resources.models import Company, ShareHolder, TickerShare


class TseTmcShareholdersPipeline(Pipeline):
    @classmethod
    def validate_item(cls, adapter) -> tuple[bool, str]:
        for key in set(cls.item_to_db_map().keys()) - {'change'}:
            if key not in adapter:
                return False, key

        return True, str()

    @classmethod
    def item_to_db_map(cls):
        return {
            k: k for k in
            {'tsetmc_index', 'shareholder_id', 'shareholder_name', 'number_of_shares', 'shares_percentage', 'change'}
        }

    @classmethod
    def export_to_db(cls, items: list[dict]):
        shareholder_ids = ShareHolder.objects.values_list('shareholder_id', flat=True)
        to_create_objs = list()
        for item in items:
            if item['shareholder_id'] not in shareholder_ids:
                to_create_objs.append(
                    ShareHolder(shareholder_id=item['shareholder_id'], name=item['shareholder_name']))
        ShareHolder.objects.bulk_create(to_create_objs, ignore_conflicts=True)

        company_index_to_ids = {cindex: cid for cindex, cid in Company.objects.values_list('tsetmc_index', 'id')}
        shareholder_id_to_id = {sid: dbid for sid, dbid in ShareHolder.objects.values_list('shareholder_id', 'id')}
        to_create_objs = list()
        for item in items:
            if item['tsetmc_index'] not in company_index_to_ids or item['shareholder_id'] not in shareholder_id_to_id:
                continue  # todo: log warning

            index = item['tsetmc_index']
            shareholder_id = item['shareholder_id']
            del item['tsetmc_index'], item['shareholder_id'], item['shareholder_name']
            if 'change' in item and not isinstance(item['change'], int):
                del item['change']
            to_create_objs.append(
                TickerShare(company_id=company_index_to_ids[index],
                            shareholder_id=shareholder_id_to_id[shareholder_id],
                            **item)
            )
        TickerShare.objects.bulk_create(to_create_objs, ignore_conflicts=True)
