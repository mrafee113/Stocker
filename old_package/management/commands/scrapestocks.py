# from django.core.management.base import BaseCommand
#
# from resources.tsetmc.scraper import TseTmcCompanyScraper
# from resources.tsetmc import populate_db
#
#
# class Command(BaseCommand):
#     help = "Scrapes tsetmc.com and gathers stocks symbols and indexes."
#
#     def handle(self, *args, **options):
#         ctrl = TseTmcCompanyScraper
#         ctrl.scrape_symbols_and_indexes()
#         self.stdout.write('Symbols and indexes have been scraped from tsetmc.com.')
#         ctrl.scrape_metadata()
#         self.stdout.write('Stock metadata have been scraped from tsctmc.com.')
#         populate_db()
#         self.stdout.write('Stock database table has been populated with stocks metadata.')
