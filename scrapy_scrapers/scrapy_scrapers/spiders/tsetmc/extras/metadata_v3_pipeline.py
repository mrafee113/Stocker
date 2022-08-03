from itemadapter import ItemAdapter

from utils.web.scrapy import Pipeline
from resources.models import Company, IndustryGroup


class TseTmcMetadataV3Pipeline(Pipeline):
    def validate_item(self, adaptor: ItemAdapter) -> tuple[bool, str]:
        if all(map(lambda x: x not in adaptor, set(self.item_to_db_map()) - {'index'})):
            return False, ', '.join(list(self.item_to_db_map().keys()))

        if 'index' not in adaptor:
            return False, 'index'

        return True, str()

    @classmethod
    def item_to_db_map(cls):
        return {
                   'title': 'tsetmc_title',
                   'industry_group': 'tsetmc_industry_group',
                   'index': 'tsetmc_index'
               } | {
                   k: k for k in
                   {'ci_sin', 'base_volume'}
               }

    @classmethod
    def export_to_db(cls, items: list[dict]):
        items = {kw['tsetmc_index']: kw for kw in items if 'tsetmc_index' in kw}
        objs = Company.objects.filter(tsetmc_index__in=list(items.keys()))
        fields = list(set(cls.item_to_db_map().values()) - {'tsetmc_index'})
        changed_objs_indexes = list()
        for idx, obj in enumerate(objs):
            item = items[obj.tsetmc_index]
            # todo: log isic change... VERY IMPORTANT
            changed = False
            for key in fields:
                if key in item and getattr(obj, key) != item[key]:
                    if key != 'tsetmc_industry_group':
                        setattr(obj, key, item[key])
                    changed = True

            if changed:
                changed_objs_indexes.append(idx)
        objs = [objs[idx] for idx in changed_objs_indexes]
        if not objs:
            return

        industry_group_objs = IndustryGroup.objects.all()
        industry_groups = set()
        for obj in objs:
            item = items[obj.tsetmc_index]
            if 'tsetmc_industry_group' in item:
                industry_groups |= {item['tsetmc_industry_group']}
        for idx, obj in enumerate(industry_group_objs):
            if obj.name in industry_groups:
                industry_groups -= {obj.name}
        IndustryGroup.objects.bulk_create([
            IndustryGroup(name=name) for name in industry_groups
        ])
        del industry_group_objs, industry_groups

        industry_group_objs = IndustryGroup.objects.all()
        for obj in objs:
            item = items[obj.tsetmc_index]
            if 'tsetmc_industry_group' not in item:
                continue
            industry_group = [ig for ig in industry_group_objs if ig.name == item['tsetmc_industry_group']]
            if not industry_group:
                continue
            industry_group = industry_group[0]
            obj.tsetmc_industry_group = industry_group

        Company.objects.bulk_update(objs, fields=fields)
        # todo: log objs changed.
