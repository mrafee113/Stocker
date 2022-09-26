from scrapy.item import Item, Field
from utils.web.scrapy import ScrapyHandler as H
from utils.web.itemloader import TFCompose, ItemLoader


class TseTmcOverviewItem(Item):
    tsetmc_index: str = Field()
    title: str = Field()
    explanation: str = Field()


class TseTmcOverviewLoader(ItemLoader):
    default_item_class = TseTmcOverviewItem

    title_in = TFCompose(H.pvalidate(tipe=str, value_exc=str()))
    explanation_in = TFCompose(H.pvalidate(tipe=str, value_exc=str()))
