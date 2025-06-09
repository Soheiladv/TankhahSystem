from django import template
from django.utils import numberformat
from decimal import Decimal, InvalidOperation

from django.contrib.humanize.templatetags.humanize import intcomma
import re

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


@register.filter
def lookup(dictionary, key):
    return dictionary.get(key)

#
# @register.filter
# def get_current_tenant(unit):
#     tenant_history = TenantHistory.objects.filter(unit=unit, move_out_date__isnull=True).first()
#     if tenant_history and tenant_history.tenant:
#         return tenant_history.tenant
#     return '---'


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
        # logger.debug(f"Manually formatted number: {formatted_number}")

        # تبدیل به فارسی
        persian_numbers = str.maketrans("0123456789,", "۰۱۲۳۴۵۶۷۸۹،")
        formatted_number = formatted_number.translate(persian_numbers)

        if value < 0:
            return f"({formatted_number})"
        return formatted_number

    except (ValueError, TypeError) as e:
        logger.error(f"Error formatting number {value}: {str(e)}")
        return "۰"


@register.filter
def dict_get(dictionary, key):
    return dictionary.get(key)

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



@register.filter(name='subtract')
def subtract(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return ''


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Allows accessing dictionary values using a variable key in Django templates.
    Usage: {{ my_dictionary|get_item:my_key_variable }}
    Returns None if the key doesn't exist or the input is not a dictionary.
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key) # Using .get() is safer than dictionary[key]
    return None


# ... سایر فیلترها و رجیستر ...

@register.simple_tag
def calculate_row_total(quantity, amount):
    """Calculates the row total (quantity * amount)."""
    from decimal import InvalidOperation
    try:
        # استفاده از Decimal برای دقت بیشتر در محاسبات مالی
        qty = Decimal(str(quantity)) if quantity is not None else Decimal('1')
        amt = Decimal(str(amount)) if amount is not None else Decimal('0')
        # اگر quantity صفر یا منفی بود، آن را 1 در نظر بگیر (مگر اینکه منطق دیگری لازم باشد)
        effective_qty = qty if qty > 0 else Decimal('1')
        total = effective_qty * amt
        # گرد کردن به عدد صحیح برای نمایش ریال
        return total.quantize(Decimal('0'))
    except (ValueError, TypeError, InvalidOperation):
        return Decimal('0')


@register.filter
def get_field_label(form, field_name):
    """Returns the label of a form field."""
    try:
        return form.fields[field_name].label
    except KeyError:
        return field_name

@register.filter
def get_item(list_obj, index):
    """Returns an item from a list by index."""
    try:
        return list_obj[int(index)]
    except (IndexError, TypeError, ValueError):
        return None

IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
ICON_MAP = {
    'pdf': 'fa-file-pdf text-danger',
    'doc': 'fa-file-word text-primary',
    'docx': 'fa-file-word text-primary',
    'xls': 'fa-file-excel text-success',
    'xlsx': 'fa-file-excel text-success',
    'ppt': 'fa-file-powerpoint text-warning',
    'pptx': 'fa-file-powerpoint text-warning',
    'zip': 'fa-file-archive text-secondary',
    'rar': 'fa-file-archive text-secondary',
    'txt': 'fa-file-alt text-secondary',
    'csv': 'fa-file-csv text-success',
    # Add more as needed
}
import  os
@register.filter
def get_file_icon(filename):
    if not filename:
        return 'fa-file text-muted'
    try:
        ext = os.path.splitext(str(filename))[1].lower().strip('.')
        # Check if it's a known image type first
        if f'.{ext}' in IMAGE_EXTENSIONS:
            return 'fa-file-image text-info' # Default icon for images if preview fails
        return ICON_MAP.get(ext, 'fa-file text-muted') # Get specific icon or default
    except Exception:
        return 'fa-file text-muted'

@register.filter
def is_image_file(filename):
     if not filename:
         return False
     try:
         ext = os.path.splitext(str(filename))[1].lower()
         return ext in IMAGE_EXTENSIONS
     except Exception:
         return False
#
@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def lookup(value, key):
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


# @register.filter
# def split(value, delimiter):
# #     """فیلتر split: فرض کردم split تعریف شده (برای جدا کردن rule_label). اگه نیست، بگو تا جایگزین کنم یا تعریفش کنم:"""
#     return value.split(delimiter)

@register.filter
def split(value, separator):
    #     """فیلتر split: فرض کردم split تعریف شده (برای جدا کردن rule_label). اگه نیست، بگو تا جایگزین کنم یا تعریفش کنم:"""
    return value.split(separator)

@register.filter
def startswith(value, prefix):
    return value.startswith(prefix)
#
@register.filter
def endswith(value, suffix):
    return value.endswith(suffix)


@register.filter
def get_project_status_color(percentage):
    try:
        percentage = float(percentage)
        if percentage < 50:
            return '#2ecc71'  # سبز
        elif 50 <= percentage < 80:
            return '#f1c40f'  # زرد
        else:
            return '#e74c3c'  # قرمز
    except (ValueError, TypeError):
        return '#6c757d'  # خاکستری برای ورودی نامعتبر


@register.filter
def is_false(value):
    """
    بررسی می‌کند که آیا مقدار دقیقاً False است.
    """
    return value is False


@register.filter
def action_display(value):
    action_map = {
        'APPROVE': 'تأیید',
        'REJECT': 'رد',
        'STAGE_CHANGE': 'تغییر مرحله',
        'PENDING': 'در انتظار',
    }
    return action_map.get(value, value)



def action_display(value):
    action_map = {
        'APPROVE': 'تأیید',
        'REJECT': 'رد',
        'STAGE_CHANGE': 'تغییر مرحله',
        'PENDING': 'در انتظار',
    }
    return action_map.get(value, value)


from urllib.parse import urlencode
@register.filter
def urlencode_without_page(query_dict, exclude_key):
    """
    Encodes a QueryDict into a URL parameter string, excluding a specified key.
    Useful for pagination to maintain other GET parameters.
    """
    # Convert QueryDict to a mutable dictionary
    params = query_dict.copy()

    # Remove the specified key if it exists
    if exclude_key in params:
        del params[exclude_key]

    # urlencode the remaining parameters
    # The `doseq=True` argument handles lists of values for a single key
    # e.g., ?param=a&param=b
    return "&" + urlencode(params, doseq=True) if params else ""

###################################################
@register.filter(name='sub')
def sub(value, arg):
    """
    یک مقدار را از مقدار دیگر کم می‌کند.
    مثال: {{ 100|sub:consumed_percentage }}
    """
    try:
        return Decimal(value) - Decimal(arg)
    except (ValueError, TypeError, InvalidOperation):
        return Decimal(value)

@register.filter(name='percentage_of')
def percentage_of(value, total):
    """
       مقدار ورودی را به عنوان درصدی از کل محاسبه می‌کند.
       برای جلوگیری از خطای تقسیم بر صفر، اگر کل صفر باشد، صفر برمی‌گرداند.
       مثال در تمپلیت: {{ consumed_amount|percentage_of:total_amount }}
       """
    try:
        value = Decimal(value); total = Decimal(total)
        return (value / total) * 100 if total != 0 else Decimal(0)
    except (ValueError, TypeError, InvalidOperation):
        return Decimal(0)
