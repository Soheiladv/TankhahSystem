from django import template
import jdatetime
from datetime import datetime

register = template.Library()


@register.filter
def to_jalali(value, format='%Y/%m/%d %H:%M:%S'):
    if not value:
        return value
    if isinstance(value, datetime):
        jalali_date = jdatetime.datetime.fromgregorian(datetime=value)
    else:
        # Attempt to handle date/datetime-like objects gracefully
        try:
            jalali_date = jdatetime.datetime.fromgregorian(datetime=value)
        except Exception:
            return value
    try:
        return jalali_date.strftime(format)
    except Exception:
        return jalali_date.strftime('%Y/%m/%d %H:%M:%S')


