from utils.web.scrapy import Pipeline
from resources.models import Company


class TseTmcOldIndexesPipeline(Pipeline):
    @classmethod
    def item_to_db_map(cls):
        return {
            'symbol': 'tsetmc_symbol',
            'old_indexes': 'tsetmc_old_indexes'
        }

    @classmethod
    def export_to_db(cls, items: list[dict]):
        items = {kw['tsetmc_symbol']: kw for kw in items if 'tsetmc_symbol' in kw}
        objs = Company.objects.filter(tsetmc_symbol__in=list(items.keys()))
        changed_objs_indexes = list()
        for idx, obj in enumerate(objs):
            item = items[obj.tsetmc_symbol]
            old_indexes = item['tsetmc_old_indexes']
            if not old_indexes:
                continue

            obj_indexes = set(obj.tsetmc_old_indexes)
            item_indexes = set(old_indexes)
            union_indexes = obj_indexes | item_indexes
            if len(union_indexes) > len(obj_indexes):
                obj.tsetmc_old_indexes = list(union_indexes)
                changed_objs_indexes.append(idx)

        objs = [objs[idx] for idx in changed_objs_indexes]
        if objs:
            Company.objects.bulk_update(objs, fields=['tsetmc_old_indexes'])
        # todo: log objs changed.
