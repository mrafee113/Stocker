from scrapy.item import Item
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class MycodalCompanyPipeline:
    def __init__(self):
        self.items: dict[str, Item] = dict()

    def close_spider(self, spider):
        if len(self.items) > 0:
            self.export_to_db(self.items)
            self.items.clear()

    def process_item(self, item, spider):
        adaptor = ItemAdapter(item)
        valid, reason = self.validate_fields(adaptor)
        if not valid:
            raise DropItem(reason)

        mycodal_id = adaptor.get('mycodal_id')
        if mycodal_id in self.items:
            raise DropItem(f'mycodal_id={mycodal_id} was redundant. dropped item.')
        self.items[mycodal_id] = item

        if len(self.items) > 100:
            items = self.items
            self.items = dict()
            self.export_to_db(items)

        return item

    @classmethod
    def validate_fields(cls, adaptor) -> tuple[bool, str]:
        pass  # todo

    @classmethod
    def export_to_db(cls, items: dict[str, Item]):
        pass  # todo
