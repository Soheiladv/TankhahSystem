# version_tracker/templatetags/version_tags.py
from django import template
from version_tracker.models import FinalVersion
from django.utils.translation import gettext_lazy as _

register = template.Library()

@register.simple_tag
def get_final_version():
    try:
        final_version = FinalVersion.objects.filter(is_active=True).latest('release_date')
        return final_version.version_number
    except FinalVersion.DoesNotExist:
        return _("نسخه نهایی تعریف نشده")