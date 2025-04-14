import jdatetime
from django.forms import forms
from django.utils.translation import gettext_lazy as _


def convert_jalali_to_gregorian(date_str):
    """تبدیل تاریخ شمسی (Jalali) به میلادی (Gregorian)"""
    try:
        jalali_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
        gregorian_date = jalali_date.togregorian()
        return gregorian_date.date()
    except ValueError:
        raise forms.ValidationError(_('تاریخ واردشده معتبر نیست. فرمت: 1403/06/15'))


def convert_gregorian_to_jalali(gregorian_date):
    """تبدیل تاریخ میلادی (Gregorian) به شمسی (Jalali) و نمایش با اعداد فارسی"""
    if gregorian_date:
        jalali_date = jdatetime.date.fromgregorian(date=gregorian_date)
        return convert_to_farsi_numbers(jalali_date.strftime('%Y/%m/%d'))
    return ''


def convert_to_farsi_numbers(value):
    """تبدیل اعداد انگلیسی به فارسی"""
    english_digits = "0123456789"
    farsi_digits = "۰۱۲۳۴۵۶۷۸۹"
    translation_table = str.maketrans(english_digits, farsi_digits)
    return str(value).translate(translation_table)

# Tanbakhsystem/tankhah/utils.py
def to_english_digits(value):
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    translation_table = str.maketrans(persian_digits, english_digits)
    return value.translate(translation_table)

#  /utils.py
#   تبدیل تاریخ
#

def parse_jalali_date_jdate(date_str):
    try:
        return jdatetime.datetime.strptime(date_str, "%Y/%m/%d").date().togregorian()
    except ValueError:
        raise ValueError("فرمت تاریخ نامعتبر است (مثال: 1404/01/01)")
#
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import jdatetime
from django.utils import timezone

def parse_jalali_date(date_str, field_name="تاریخ"):
    """
    تبدیل تاریخ شمسی (مثل '1404/01/17') به تاریخ میلادی (datetime.date).
    اگر تاریخ نامعتبر یا خالی باشه، خطای مناسب تولید می‌کنه.
    """
    if not date_str:
        raise ValidationError(_('لطفاً {field_name} را وارد کنید.').format(field_name=field_name))
    try:
        # تبدیل اعداد فارسی به انگلیسی
        date_str = ''.join([chr(ord(c) - 1728) if '۰' <= c <= '۹' else c for c in str(date_str)])
        j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
        g_date = timezone.make_aware(j_date.togregorian())
        return g_date.date()
    except ValueError:
        raise ValidationError(_('لطفاً {field_name} معتبر وارد کنید (مثل ۱۴۰۴/۰۱/۱۷).').format(field_name=field_name))

def format_jalali_date(date_obj):
    """
    تبدیل تاریخ میلادی به رشته شمسی (مثل '1404/01/17').
    اگر تاریخ None باشه، رشته خالی برمی‌گردونه.
    """
    if not date_obj:
        return ''
    try:
        j_date = jdatetime.date.fromgregorian(date=date_obj)
        return j_date.strftime('%Y/%m/%d')
    except (TypeError, ValueError):
        return ''
