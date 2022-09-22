import jdatetime

from scrapy.item import Item, Field
from datetime import datetime
from utils.web.scrapy import ScrapyHandler as H
from utils.web.itemloader import TFCompose, ItemLoader


class TseTmcSupervisorMsgItem(Item):
    tsetmc_index: str = Field()
    title: str = Field()
    message: str = Field()
    datetime: datetime = Field()


class TseTmcSupervisorMsgLoader(ItemLoader):
    default_item_class = TseTmcSupervisorMsgItem

    title_in = TFCompose(H.pvalidate(tipe=str, value_exc=str()), str.strip)
    message_in = TFCompose(H.pvalidate(tipe=str, value_exc=str()), str.strip)

    @staticmethod
    def parse_datetime_string(dt: str) -> datetime:
        date_part = dt.split(' ')[0]
        time_part = dt.split(' ')[1]

        year, month, day = list(map(lambda x: x.zfill(2), date_part.split('/')))
        year = f'14{year}' if int(year) < 80 else f'13{year}'

        return jdatetime.datetime.strptime(f'{year}/{month}/{day} {time_part}', '%Y/%m/%d %H:%M').togregorian()

    datetime_in = TFCompose(
        H.pvalidate(
            tipe=str, value_exc=str(),
            validation=lambda x: x.replace('/', '').replace(':', '').replace(' ', '').isnumeric()
        ),
        parse_datetime_string
    )
