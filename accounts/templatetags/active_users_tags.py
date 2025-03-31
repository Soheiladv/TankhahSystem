from django import template
from django.utils.timezone import now
from datetime import timedelta
from ..models import ActiveUser

register = template.Library()

@register.simple_tag
def get_active_users_count():
    return ActiveUser.objects.filter(
        last_activity__gte=now() - timedelta(minutes=30),
        is_active=True
    ).count()

@register.simple_tag
def get_max_active_users():
    return ActiveUser.get_max_active_users()