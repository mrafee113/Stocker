from scrapy.item import Item, Field


class TseTmcOldIndexesItem(Item):
    """TseTmcMetadataV2Item"""
    symbol: str = Field()
    old_indexes: list = Field()
