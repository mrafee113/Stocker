from datetime import date
from scrapy.item import Item, Field


class TseTmcPriceRecordItem(Item):
    tsetmc_index: str = Field()
    date: date = Field()
    open: int = Field()
    high: int = Field()
    low: int = Field()
    adj_close: int = Field()
    value: int = Field()
    volume: int = Field()
    count: int = Field()
    close: int = Field()
