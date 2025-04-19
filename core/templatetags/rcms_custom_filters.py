from django import template
from django.utils import numberformat
from decimal import Decimal

register = template.Library()


@register.filter
def thousand_separator(value):
    try:
        value = float(value)
        return "{:,.2f}".format(value)
    except (ValueError, TypeError):
        return value


@register.filter
def prepend_dollars(dollars):
    if dollars:
        dollars = round(float(dollars), 2)
        return "$%s%s" % (intcomma(int(dollars)), ("%0.2f" % dollars)[-3:])
    return ''


@register.filter
def absolute(value):
    try:
        return abs(value)
    except (ValueError, TypeError):
        return value


#
# @register.filter
# def get_current_tenant(unit):
#     tenant_history = TenantHistory.objects.filter(unit=unit, move_out_date__isnull=True).first()
#     if tenant_history and tenant_history.tenant:
#         return tenant_history.tenant
#     return '---'


from django import template

register = template.Library()


@register.filter
def exclude(form, field_name):
    return [bound_field for bound_field in form if bound_field.name != field_name]


# '''
# این فیلتر، مقدار مربوط به کلید key را از دیکشنری dictionary برمی‌گرداند. اگر کلید وجود نداشته باشد، یک لیست خالی برمی‌گرداند.
# '''
@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    یک فیلتر سفارشی برای استخراج مقدار یک کلید از دیکشنری.
    """
    return dictionary.get(key, [])


#####  اعداد فارسی
register = template.Library()


@register.filter
def to_persian_number(value):
    persian_numbers = {
        '0': '۰',
        '1': '۱',
        '2': '۲',
        '3': '۳',
        '4': '۴',
        '5': '۵',
        '6': '۶',
        '7': '۷',
        '8': '۸',
        '9': '۹',
    }
    value = str(value)
    for eng, per in persian_numbers.items():
        value = value.replace(eng, per)
    return value


from django.contrib.humanize.templatetags.humanize import intcomma
import re


@register.filter
def to_persian_number_with_comma1(value):
    if value is None:
        return ''

    # پالت اعداد فارسی
    persian_numbers = {
        '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
        '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹',
        ',': '،'
    }

    # تابع جایگزینی اعداد
    def replace_number(match):
        num = match.group(0)
        try:
            num_int = int(num)
            formatted_value = intcomma(num_int) if num_int >= 1000 else str(num_int)
            for eng, per in persian_numbers.items():
                formatted_value = formatted_value.replace(eng, per)
            return formatted_value
        except (ValueError, TypeError):
            return num

    result = re.sub(r'\d+', replace_number, str(value))
    return result


from django.utils.numberformat import format as number_format


@register.filter
def to_persian_number_with_comma(value):
    if value is None:
        return ''

    persian_numbers = str.maketrans("0123456789,", "۰۱۲۳۴۵۶۷۸۹،")

    def convert_numbers(match):
        number = match.group(0)
        try:
            # افزودن جداکننده هزارگان با تنظیمات مشخص
            formatted_number = number_format(
                int(number),
                decimal_sep='.',  # جداکننده اعشار (که اینجا استفاده نمی‌شه چون عدد صحیح داریم)
                thousand_sep=',',  # جداکننده هزارگان
                use_l10n=False  # چون جداکننده رو خودمون مشخص کردیم، نیازی به L10N نیست
            )
        except ValueError:
            formatted_number = number  # اگر تبدیل نشد، همان مقدار اصلی رو برگردون
        return formatted_number.translate(persian_numbers)  # تبدیل اعداد انگلیسی به فارسی

    # جستجوی تمامی اعداد داخل متن و تبدیل آن‌ها
    return re.sub(r'\d+', convert_numbers, str(value))


#############################
@register.filter
def sum_attr(items, attr):
    """Custom Filter for Summing Attributes"""
    return sum(getattr(item, attr, 0) for item in items)


@register.filter
def sum_expenses(queryset):
    """
    مجموع مقادیر expense_amount را محاسبه می‌کند.
    """
    return sum(item.expense_amount for item in queryset)


@register.filter
def sum_balances(queryset):
    """
    مجموع مقادیر balance را محاسبه می‌کند.
    """
    return sum(item.balance for item in queryset)


@register.filter(name='abs_value_float')
def abs_value_float(value):
    """
    این فیلتر مقدار منفی را به مثبت تبدیل می‌کند.
    """
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value

####
import logging
logger = logging.getLogger(__name__)

@register.filter(name='format_negative')
def format_negative(value):
    """نمایش عدد با جداکننده هزارگان و تبدیل به فارسی. اعداد منفی درون پرانتز قرار می‌گیرند."""
    if value is None:
        return "۰"

    try:
        value = float(value)
        # جداسازی سه‌رقمی دستی
        abs_value = abs(int(value))
        formatted_number = "{:,}".format(abs_value)  # استفاده از format داخلی پایتون
        logger.debug(f"Manually formatted number: {formatted_number}")

        # تبدیل به فارسی
        persian_numbers = str.maketrans("0123456789,", "۰۱۲۳۴۵۶۷۸۹،")
        formatted_number = formatted_number.translate(persian_numbers)

        if value < 0:
            return f"({formatted_number})"
        return formatted_number

    except (ValueError, TypeError) as e:
        logger.error(f"Error formatting number {value}: {str(e)}")
        return "۰"




def number_to_farsi_words(number):
    """
    تبدیل عدد به حروف فارسی
    مثال: 1234567 -> یک میلیون و دویست و سی و چهار هزار و پانصد و شصت و هفت
    """
    if not isinstance(number, (int, float, str)):
        return ""

    try:
        number = int(float(str(number).replace(",", "")))
    except (ValueError, TypeError):
        return ""

    if number == 0:
        return "صفر"

    units = ["", "هزار", "میلیون", "میلیارد", "تریلیون"]
    digits = [
        "", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه",
        "ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده",
        "هفده", "هجده", "نوزده"
    ]
    tens = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]
    hundreds = ["", "صد", "دویست", "سیصد", "چهارصد", "پانصد", "ششصد", "هفتصد", "هشتصد", "نهصد"]

    def convert_chunk(num):
        if num == 0:
            return ""
        result = []
        if num >= 100:
            result.append(hundreds[num // 100])
            num %= 100
        if num >= 20:
            result.append(tens[num // 10])
            num %= 10
        if num > 0:
            result.append(digits[num])
        return " و ".join(filter(None, result))

    result = []
    unit_index = 0
    while number > 0:
        chunk = number % 1000
        if chunk > 0:
            chunk_text = convert_chunk(chunk)
            if unit_index > 0:
                chunk_text += " " + units[unit_index]
            result.insert(0, chunk_text)
        number //= 1000
        unit_index += 1

    return " و ".join(filter(None, result)) if result else ""

@register.filter
def div(value, arg):
    """Divides value by arg and returns the result."""
    try:
        value = Decimal(value)
        arg = Decimal(arg)
        if arg == 0:
            return Decimal('0')
        return value / arg
    except (ValueError, TypeError, ZeroDivisionError):
        return Decimal('0')

@register.filter
def mul(value, arg):
    """Multiplies value by arg."""
    try:
        value = Decimal(value)
        arg = Decimal(arg)
        return value * arg
    except (ValueError, TypeError):
        return Decimal('0')


@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg) if float(arg) != 0 else 0
    except (ValueError, TypeError):
        return 0
