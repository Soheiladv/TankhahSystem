from django import template

register = template.Library()
import  os

IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
PDF_ICON = 'fa-file-pdf text-danger'
WORD_ICON = 'fa-file-word text-primary'
EXCEL_ICON = 'fa-file-excel text-success'
ARCHIVE_ICON = 'fa-file-archive text-warning'
DEFAULT_ICON = 'fa-file text-secondary'
#

@register.filter(name='filename_only')
def filename_only(filepath):
    """فقط نام فایل را از مسیر کامل برمی‌گرداند"""
    try:
        return os.path.basename(str(filepath))
    except:
        return str(filepath)

@register.filter(name='get_file_extension')
def get_file_extension(filename):
    """پسوند فایل را با حروف کوچک برمی‌گرداند (مثلا .pdf)"""
    try:
        return os.path.splitext(str(filename))[1].lower()
    except:
        return ''

@register.filter(name='is_image_extension')
def is_image_extension(extension):
    """چک می‌کند آیا پسوند مربوط به تصویر است یا نه"""
    return extension in IMAGE_EXTENSIONS

@register.filter(name='get_file_icon')
def get_file_icon(extension):
    """کلاس آیکون Font Awesome مناسب برای پسوند فایل را برمی‌گرداند"""
    if extension == '.pdf':
        return PDF_ICON
    elif extension in ['.doc', '.docx','txt','pdf']:
        return WORD_ICON
    elif extension in ['.xls', '.xlsx']:
        return EXCEL_ICON
    elif extension in ['.zip', '.rar', '.7z']:
        return ARCHIVE_ICON
    # می‌توانید برای انواع دیگر هم اضافه کنید
    else:
        return DEFAULT_ICON


@register.filter(name='add_class')
def add_class(field, css):
    """کلاس CSS را به ویجت فیلد فرم اضافه می‌کند"""
    return field.as_widget(attrs={"class": css})

