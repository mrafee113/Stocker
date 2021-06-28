from datetime import date, datetime, timedelta
from django.utils import timezone


def datetime_from_date(date_value: date):
    return timezone.localtime() - (timezone.localdate() - date_value)


def today():
    return timezone.localdate()


def now():
    return timezone.localtime()
