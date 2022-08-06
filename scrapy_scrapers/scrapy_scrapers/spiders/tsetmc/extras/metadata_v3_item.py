from scrapy.item import Item, Field

from utils.farsi import replace_arabic
from utils.web.scrapy import ScrapyHandler as H
from utils.web.itemloader import TFCompose, ItemLoader


class TseTmcMetadataV3Item(Item):
    ci_sin: str = Field()
    title: str = Field()
    industry_group: str = Field()
    base_volume: str = Field()
    index: str = Field()


class TseTmcMetadataV3Loader(ItemLoader):
    default_item_class = TseTmcMetadataV3Item

    ci_sin_in = TFCompose(H.pvalidate(tipe=str, value_exc=str()), str.strip)
    title_in = TFCompose(H.pvalidate(tipe=str, value_exc=str()), str.strip, replace_arabic)
    industry_group_in = TFCompose(H.pvalidate(tipe=str, value_exc=str()), str.strip, replace_arabic)
    base_volume_in = TFCompose(
        H.pvalidate(tipe=str, value_exc='1',
                    validation=lambda x: x != str() and '.' not in x and x.isdigit()),
        str.strip, int
    )
