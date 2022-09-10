from .dps_item import TseTmcDPSItem
from .overview_item import TseTmcOverviewItem
from .supervisor_message_item import TseTmcSupervisorMsgItem
from .corporate_individual_item import TseTmcCorporateIndividualItem

from .dps_pipeline import TseTmcDPSPipeline
from .overview_pipeline import TseTmcOverviewPipeline
from .supervisor_message_pipeline import TseTmcSupervisorMsgPipeline
from .corporate_individual_pipeline import TseTmcCorporateIndividualPipeline


class TseTmcPagePipeline:
    def __init__(self):
        self.corporate_individual_pipeline = TseTmcCorporateIndividualPipeline()
        self.dps_pipeline = TseTmcDPSPipeline()
        self.supervisor_message_pipeline = TseTmcSupervisorMsgPipeline()
        self.overview_pipeline = TseTmcOverviewPipeline()

    def open_spider(self, spider):
        spider.pipeline = self

    def close_spider(self, spider):
        for pipeline in [pipe for pipe in dir(self) if pipe.endswith('_pipeline')]:
            getattr(self, pipeline).close_spider(spider)

    def process_item(self, item, spider):
        if isinstance(item, TseTmcCorporateIndividualItem):
            self.corporate_individual_pipeline.process_item(item, spider)
        elif isinstance(item, TseTmcOverviewItem):
            self.overview_pipeline.process_item(item, spider)
        elif isinstance(item, TseTmcDPSItem):
            self.dps_pipeline.process_item(item, spider)
        elif isinstance(item, TseTmcSupervisorMsgItem):
            self.supervisor_message_pipeline.process_item(item, spider)
