from django import template
from django.utils.safestring import mark_safe
from core.models import FontSettings

register = template.Library()

@register.simple_tag
def get_default_font():
    """دریافت فونت پیش‌فرض سیستم"""
    return FontSettings.get_default_font()

@register.simple_tag
def get_active_fonts():
    """دریافت تمام فونت‌های فعال"""
    return FontSettings.get_active_fonts()

@register.simple_tag
def get_font_stats():
    """دریافت آمار فونت‌ها"""
    total = FontSettings.objects.count()
    active = FontSettings.objects.filter(is_active=True).count()
    inactive = total - active
    
    return {
        'total': total,
        'active': active,
        'inactive': inactive
    }

@register.simple_tag
def get_system_font_css():
    """تولید CSS برای فونت‌های سیستم"""
    fonts = FontSettings.get_active_fonts()
    css_rules = []
    
    for font in fonts:
        css_rule = font.get_css_font_face()
        if css_rule:
            css_rules.append(css_rule)
    
    # اضافه کردن CSS برای فونت پیش‌فرض
    default_font = FontSettings.get_default_font()
    if default_font:
        css_rules.append(f"""
body, .system-font {{
    font-family: '{default_font.family_name}', 'Tahoma', sans-serif !important;
}}""")
    
    return mark_safe('\n'.join(css_rules))

@register.inclusion_tag('core/font_css_include.html')
def include_system_fonts():
    """شامل کردن فونت‌های سیستم در صفحه"""
    try:
        fonts = FontSettings.get_active_fonts()
        default_font = FontSettings.get_default_font()
    except:
        fonts = []
        default_font = None
    
    return {
        'fonts': fonts,
        'default_font': default_font
    }
