import jdatetime

from datetime import date
from scrapy.item import Item, Field

from utils.web.scrapy import ScrapyHandler as H
from utils.web.itemloader import TFCompose, ItemLoader


class TseTmcCapitalIncreaseHistoryItem(Item):
    tsetmc_index: str = Field()
    prev_stocks: int = Field()
    next_stocks: int = Field()
    date: date = Field()


class TseTmcCapitalIncreaseHistoryLoader(ItemLoader):
    default_item_class = TseTmcCapitalIncreaseHistoryItem

    number_processor = TFCompose(
        H.pvalidate(
            tipe=str, value_exc=str(),
            validation=lambda x: isinstance(int(x.replace(',', '').strip()), int)
        ),
        lambda x: x.replace(',', '').strip(), int
    )

    prev_stocks_in = number_processor
    next_stocks_in = number_processor
    date_in = TFCompose(
        H.pvalidate(
            tipe=str, value_exc=str(),
            validation=lambda x: isinstance(jdatetime.datetime.strptime(x, '%Y/%m/%d').date(), jdatetime.date)
        ),
        str.strip, lambda x: jdatetime.datetime.strptime(x, '%Y/%m/%d').date().togregorian(),
    )
