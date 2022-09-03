import jdatetime

from scrapy.item import Item, Field
from datetime import date
from utils.web.scrapy import ScrapyHandler as H
from utils.web.itemloader import TFCompose, ItemLoader


class TseTmcDPSItem(Item):
    tsetmc_index: str = Field()
    issuance_date: date = Field()
    assembly_date: date = Field()
    fiscal_date: date = Field()
    dividends: int = Field()
    dps: int = Field()


class TseTmcDPSLoader(ItemLoader):
    default_item_class = TseTmcDPSItem

    date_processor = TFCompose(
        H.pvalidate(
            tipe=str, value_exc=str(),
            validation=lambda x: isinstance(jdatetime.datetime.strptime(x.strip(), '%Y/%m/%d'), jdatetime.datetime)
        ),
        str.strip, lambda x: jdatetime.datetime.strptime(x, '%Y/%m/%d').date().togregorian()
    )

    int_processor = TFCompose(
        H.pvalidate(tipe=str, value_exc='0.00', validation=lambda x: isinstance(int(float(x)), int)),
        str.strip, float, int
    )

    issuance_date_in = date_processor
    assembly_date_in = date_processor
    fiscal_date_in = date_processor
    dividends_in = int_processor
    dps_in = int_processor
