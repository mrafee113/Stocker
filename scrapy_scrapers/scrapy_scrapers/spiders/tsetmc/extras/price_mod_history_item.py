import jdatetime

from datetime import date
from scrapy.item import Item, Field

from utils.web.scrapy import ScrapyHandler as H
from utils.web.itemloader import TFCompose, ItemLoader


class TseTmcPriceModHistoryItem(Item):
    tsetmc_index: str = Field()
    prev_price: int = Field()
    next_price: int = Field()
    date: date = Field()


class TseTmcPriceModHistoryLoader(ItemLoader):
    default_item_class = TseTmcPriceModHistoryItem

    int_processor = TFCompose(
        H.pvalidate(
            tipe=str, value_exc='0',
            validation=lambda x: isinstance(int(x.replace(',', '').strip()), int)
        ),
        lambda x: x.replace(',', ''), str.strip, int
    )

    prev_price_in = int_processor
    next_price_in = int_processor
    date_in = TFCompose(
        H.pvalidate(
            tipe=str, value_exc=str(),
            validation=lambda x: isinstance(jdatetime.datetime.strptime(x, '%Y/%m/%d').date(), jdatetime.date)
        ),
        str.strip, lambda x: jdatetime.datetime.strptime(x, '%Y/%m/%d').date().togregorian(),
    )
