from utils.web.scrapy import Pipeline
from resources.models import Company


class TseTmcMetadataV1Pipeline(Pipeline):
    @classmethod
    def item_to_db_map(cls):
        return {
                   'index': 'tsetmc_index',
                   'symbol': 'tsetmc_symbol'
               } | {
                   k: k for k in
                   {'name', 'isin'}
               }

    @classmethod
    def export_to_db(cls, items: list[dict]):
        downloaded_items = {kw['tsetmc_symbol']: kw for kw in items if 'tsetmc_symbol' in kw}
        all_symbols = Company.objects.values_list('tsetmc_symbol')
        existing_symbols, new_symbols = list(), list()
        for symbol, kw in downloaded_items.items():
            if symbol in all_symbols:
                existing_symbols.append(symbol)
            else:
                new_symbols.append(symbol)

        new_objs = [Company(**downloaded_items[symbol]) for symbol in new_symbols]
        if new_objs:
            Company.objects.bulk_create(new_objs)
        # todo: log new objs created.

        objs = Company.objects.filter(tsetmc_symbol__in=existing_symbols)
        changed_objs_indexes = list()
        for idx, obj in enumerate(objs):
            item = downloaded_items[obj.tsetmc_symbol]
            # todo: log isin change... VERY IMPORTANT
            changed = False
            for key in ['name', 'isin', 'tsetmc_index']:
                if getattr(obj, key) != item[key]:
                    setattr(obj, key, item[key])
                    changed = True

            if changed:
                changed_objs_indexes.append(idx)

        objs = [objs[idx] for idx in changed_objs_indexes]
        if objs:
            Company.objects.bulk_update(objs, fields=['name', 'isin', 'tsetmc_index'])
        # todo: log objs changed.

        # todo: log duplicates removed.
        if objs or new_objs:
            Company.delete_duplicates('tsetmc_symbol')
            Company.delete_duplicates('tsetmc_index')
            Company.delete_duplicates('tsetmc_symbol', 'tsetmc_index')
