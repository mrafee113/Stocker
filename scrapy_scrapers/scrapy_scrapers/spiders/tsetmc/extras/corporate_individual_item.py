import jdatetime

from scrapy.item import Item, Field
from datetime import date, datetime
from utils.datetime import fa_to_en
from utils.web.scrapy import ScrapyHandler as H
from utils.web.itemloader import TFCompose, ItemLoader


class TseTmcCorporateIndividualItem(Item):
    tsetmc_index: str = Field()
    date: date = Field()

    individual_buy_count: int = Field()
    corporate_buy_count: int = Field()
    individual_sell_count: int = Field()
    corporate_sell_count: int = Field()

    individual_buy_volume: int = Field()
    corporate_buy_volume: int = Field()
    individual_sell_volume: int = Field()
    corporate_sell_volume: int = Field()

    individual_buy_value: int = Field()
    corporate_buy_value: int = Field()
    individual_sell_value: int = Field()
    corporate_sell_value: int = Field()

    individual_buy_avg: float = Field()
    corporate_buy_avg: float = Field()
    individual_sell_avg: float = Field()
    corporate_sell_avg: float = Field()

    ownership_change: int = Field()


def process_big_number_abbr(number: str) -> int:
    if 'B' in number.upper():
        multiplier = 10 ** 9
    elif 'M' in number.upper():
        multiplier = 10 ** 6
    else:
        multiplier = 1

    number = number.replace(',', '').upper().replace('B', '').replace('M', '').strip()
    return int(float(number) * multiplier)


class TseTmcCorporateIndividualLoader(ItemLoader):
    default_item_class = TseTmcCorporateIndividualItem

    date_in = TFCompose(H.pvalidate(
        tipe=str, validation=lambda x: isinstance(datetime.strptime(fa_to_en(x).strip(), '%Y/%m/%d'), datetime)),
        str.strip, fa_to_en,
        lambda x: jdatetime.datetime.strptime(x.strip(), '%Y/%m/%d').togregorian().date(),
    )

    int_processor = TFCompose(
        H.pvalidate(tipe=str, validation=lambda x: isinstance(int(x.strip().replace(',', '')), int)),
        str.strip, lambda x: x.replace(',', ''), int
    )

    float_processor = TFCompose(
        H.pvalidate(tipe=str, validation=lambda x: isinstance(float(x), float)),
        str.strip, float
    )

    individual_buy_count_in = int_processor
    corporate_buy_count_in = int_processor
    individual_sell_count_in = int_processor
    corporate_sell_count_in = int_processor

    individual_buy_volume_in = int_processor
    corporate_buy_volume_in = int_processor
    individual_sell_volume_in = int_processor
    corporate_sell_volume_in = int_processor

    individual_buy_value_in = int_processor
    corporate_buy_value_in = int_processor
    individual_sell_value_in = int_processor
    corporate_sell_value_in = int_processor

    individual_buy_avg_in = float_processor
    corporate_buy_avg_in = float_processor
    individual_sell_avg_in = float_processor
    corporate_sell_avg_in = float_processor

    ownership_change_in = TFCompose(H.pvalidate(tipe=str), str.strip, process_big_number_abbr, H.pvalidate(tipe=int))
