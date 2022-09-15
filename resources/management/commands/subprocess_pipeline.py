import importlib

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Scrapes tsetmc.com and gathers stocks symbols and indexes."

    def add_arguments(self, parser):
        parser.add_argument('--package', type=str, required=True)
        parser.add_argument('--pipeline', type=str, required=True)

    def handle(self, *args, **options):
        pipelines = importlib.import_module(options['package'])
        pipeline_class = getattr(pipelines, options['pipeline'])
        pipeline = pipeline_class()
        pipeline.load_data_into_db()
