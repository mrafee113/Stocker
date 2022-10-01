import pytz
import jdatetime

from typing import Union
from django.utils import timezone
from datetime import date, datetime


def datetime_from_date(date_value: date):
    return timezone.localtime() - (timezone.localdate() - date_value)


def today():
    return timezone.localdate()


def now():
    return timezone.localtime()


def fa_to_en(fa_text: str) -> str:
    fa_digit_range = range(ord('۰'), ord('۹') + 1)
    diff = abs(ord('۰') - ord('0'))
    for char in fa_text:
        if ord(char) in fa_digit_range:
            fa_text = fa_text.replace(char, chr(ord(char) - diff))

    return fa_text


def process_jalali_date(jdate_text: str) -> Union[date, datetime]:
    en_date_text = fa_to_en(jdate_text)
    try:
        dt = jdatetime.datetime.strptime(en_date_text, '%Y/%m/%d').togregorian().date()
    except ValueError:
        dt = jdatetime.datetime.strptime(en_date_text, '%Y/%m/%d %H:%M:%S').togregorian()

    if isinstance(dt, datetime):
        return timezone.make_aware(dt, pytz.timezone('Asia/Tehran'))
    else:
        return dt


def dt_to_str(dt: Union[date, datetime]) -> str:
    if isinstance(dt, datetime):
        return dt.strftime('%Y/%m/%d %H:%M:%S')
    elif isinstance(dt, date):
        return dt.strftime('%Y/%m/%d')
    else:
        raise TypeError('dt should be of type datetime or date')


def dt_from_str(dt_text: str) -> Union[date, datetime]:
    dt_text = dt_text.strip()
    try:
        return datetime.strptime(dt_text, '%Y/%m/%d %H:%M:%S')
    except ValueError:
        return datetime.strptime(dt_text, '%Y/%m/%d').date()


fa_to_en_month_map = {
    'فروردین': 'Farvardin',
    'اردیبهشت': 'Ordibehesht',
    'خرداد': 'Khordad',
    'تیر': 'Tir',
    'مرداد': 'Mordad',
    'شهریور': 'Shahrivar',
    'مهر': 'Mehr',
    'آبان': 'Aban',
    'آذر': 'Azar',
    'دی': 'Dey',
    'بهمن': 'Bahman',
    'اسفند': 'Esfand'
}


def fa_to_en_jalali_month(month: str) -> int:
    from utils.farsi import replace_arabic

    month = replace_arabic(month).strip()
    if month not in fa_to_en_month_map:
        raise ValueError(f'value {month} was not in predefined months.')

    month = fa_to_en_month_map[month]
    return jdatetime.datetime.strptime(month, '%B').month
