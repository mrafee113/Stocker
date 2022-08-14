import decimal

from scrapy.item import Item, Field

from utils.web.scrapy import ScrapyHandler as H
from utils.web.itemloader import TFCompose, ItemLoader


class TseTmcShareholdersItem(Item):
    tsetmc_index: str = Field()
    shareholder_id: int = Field()
    shareholder_name: str = Field()
    number_of_shares: int = Field()
    shares_percentage: float = Field()
    change: int = Field()


class TseTmcShareholdersLoader(ItemLoader):
    default_item_class = TseTmcShareholdersItem

    int_processor = TFCompose(
        H.pvalidate(
            tipe=str, value_exc=str(),
            validation=lambda x: isinstance(int(x.replace(',', '').strip()), int)
        ),
        lambda x: x.replace(',', ''), str.strip, int
    )

    shareholder_id_in = TFCompose(H.pvalidate(tipe=str, value_exc=str(), validation=lambda x: isinstance(int(x), int)),
                                  str.strip, int)
    shareholder_name_in = TFCompose(H.pvalidate(tipe=str, value_exc=str()), str.strip)
    number_of_shares_in = int_processor
    shares_percentage_in = TFCompose(
        H.pvalidate(
            tipe=str, value_exc='0',
            validation=lambda x: isinstance(float(x.strip()), float)
        ),
        str.strip, float
    )
    change_in = int_processor
