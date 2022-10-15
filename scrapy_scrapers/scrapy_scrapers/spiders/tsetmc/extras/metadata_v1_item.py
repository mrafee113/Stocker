from scrapy.item import Item, Field

from utils.farsi import replace_arabic
from utils.web.scrapy import ScrapyHandler as H
from utils.web.itemloader import TFCompose, ItemLoader


class TseTmcMetadataV1Item(Item):
    index: str = Field()
    symbol: str = Field()
    name: str = Field()
    isin: str = Field()


class TseTmcMetadataV1Loader(ItemLoader):
    default_item_class = TseTmcMetadataV1Item

    # index should be processed while added.
    symbol_in = TFCompose(H.pvalidate(tipe=str, value_exc=str()), str.strip, replace_arabic)
    name_in = TFCompose(H.pvalidate(tipe=str, value_exc=str()), str.strip,
                        lambda x: x.replace('\u200c', str()), replace_arabic)
    isin_in = TFCompose(H.pvalidate(tipe=str, value_exc=str()), str.strip, replace_arabic)
