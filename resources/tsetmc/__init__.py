# from .general import *
# from resources.tsetmc.controller import TseTmcController
#
#
# # fixme
# def populate_db(klass=None):
#     if klass is None:
#         from tsetmc.models import Stock
#         klass = Stock
#     from django.conf import settings
#
#     ctrl = TseTmcController
#     for symbol, details in ctrl.stocks_details().items():
#         index = details['index']
#         url = settings.TSE_STOCK_DETAILS_URL.format(ticker_index=index)
#         klass.objects.get_or_create(index=index,
#                                     defaults={'symbol': symbol, 'url': url})
