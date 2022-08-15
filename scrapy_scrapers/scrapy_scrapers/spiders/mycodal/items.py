from itemloaders import ItemLoader
from scrapy.item import Item, Field

from utils.datetime import fa_to_en
from utils.web.itemloader import TFCompose
from utils.web.scrapy import ScrapyHandler as H


class MycodalCompanyItem(Item):
    symbol: str = Field()
    mycodal_info_link: str = Field()
    mycodal_id: str = Field()
    name: str = Field()
    type: str = Field()
    acceptance_type: str = Field()
    industry_group: str = Field()
    company_website: str = Field()

    # detail page
    # index
    ceo: str = Field()
    cfo: str = Field()
    essence: str = Field()
    registered_capital: int = Field()
    unregistered_capital: int = Field()
    isic: str = Field()
    isin: str = Field()
    financial_end_month: str = Field()
    financial_end_day: str = Field()

    # board members
    # dict keys: institution, representor, post
    board_members: list[dict[str, str]] = Field()

    # similar publishers
    # dict keys: name, mycodal_info_link, mycodal_id
    similar_publishers: list[dict[str, str]] = Field()


class MycodalCompanyItemLoader(ItemLoader):
    default_item_class = MycodalCompanyItem

    symbol_input_processor = TFCompose(H.pvalidate(tipe=str, post=str.strip))
    # mycodal_info_link should be processed while added.
    # mycodal_id should be processed while added.
    name_in = TFCompose(H.pvalidate(tipe=str, post=str.strip))
    type_in = TFCompose(H.pvalidate(tipe=str, post=str.strip))
    acceptance_type_in = TFCompose(H.pvalidate(tipe=str, post=str.strip))
    industry_group_in = TFCompose(H.pvalidate(tipe=str, post=str.strip))
    # website should be processed while added.

    ceo_in = TFCompose(H.pvalidate(tipe=str, value_exc='-', post=str.strip))
    cfo_in = TFCompose(H.pvalidate(tipe=str, value_exc='-', post=str.strip))
    essence_in = TFCompose(H.pvalidate(tipe=str, value_exc='-', post=str.strip))
    registered_capital_in = TFCompose(H.pvalidate(tipe=str, value_exc='-'),
                                      lambda x: int(fa_to_en(x.replace(',', '')).strip()))
    unregistered_capital = TFCompose(H.pvalidate(tipe=str, value_exc='-'),
                                     lambda x: int(fa_to_en(x.replace(',', '')).strip()))
    isic_in = TFCompose(H.pvalidate(tipe=str, value_exc='-'), lambda x: fa_to_en(x).strip())
    isin_in = TFCompose(H.pvalidate(tipe=str, value_exc='-', post=str.strip))
    # financial_end_[month/day] should be processed while added.

    board_members_in = TFCompose(
        H.pvalidate(tipe=dict),
        lambda x: x if set(x.keys()) == {'institution', 'representor', 'post'} else None,
        lambda x: x if H.validate(x['post'], tipe=str, value_exc='-') else None,
        lambda x: [x]
    )
    board_members_out = TFCompose(
        lambda x: {tuple(dictionary.values()) for dictionary in x},
        lambda values_set: [{'institution': values[0], 'representor': values[1], 'post': values[2]}
                            for values in values_set]
    )

    # similar_publishers should be processed while added.
