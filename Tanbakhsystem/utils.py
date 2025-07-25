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

from datetime import datetime
import jdatetime
from django.utils import timezone
import re


def parse_jalali_date(date_str):
    """
    تبدیل رشته تاریخ جلالی (مثل 1403/01/17 یا 1403-01-17) به تاریخ گرگوری آگاه از منطقه زمانی.

    :param date_str: رشته تاریخ (مثل '1403/01/17' یا '1403-01-17')
    :return: شیء datetime آگاه از منطقه زمانی
    :raises ValueError: اگر فرمت تاریخ نامعتبر باشد
    """
    if not date_str:
        raise ValueError("رشته تاریخ خالی است.")

    # حذف فاصله‌ها و جایگزینی جداکننده‌های مختلف با /
    date_str = date_str.strip()
    date_str = re.sub(r'[-.]', '/', date_str)

    # بررسی فرمت تاریخ با regex
    if not re.match(r'^\d{4}/\d{2}/\d{2}$', date_str):
        raise ValueError("فرمت تاریخ باید به صورت YYYY/MM/DD باشد (مثال: 1403/01/17)")

    try:
        # تبدیل رشته به تاریخ جلالی
        year, month, day = map(int, date_str.split('/'))
        jalali_date = jdatetime.date(year, month, day)
        # تبدیل به تاریخ گرگوری
        gregorian_date = jalali_date.togregorian()
        # تبدیل به datetime آگاه از منطقه زمانی
        dt = datetime(gregorian_date.year, gregorian_date.month, gregorian_date.day)
        return timezone.make_aware(dt)
    except (ValueError, jdatetime.JalaliDateError) as e:
        raise ValueError(f"فرمت تاریخ نامعتبر است: {str(e)}")

def parse_jalali_date__(date_str, field_name="تاریخ"):
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
