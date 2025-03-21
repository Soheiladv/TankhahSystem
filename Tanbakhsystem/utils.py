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

