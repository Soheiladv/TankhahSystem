# myapp/templatetags/my_filters.py
from django import template
from django.contrib.auth.models import Permission
import logging

logger = logging.getLogger(__name__)

register = template.Library()


@register.filter
def has_permission(user, codename):
    if user.is_superuser:
        return True

    for role in user.roles.all():
        logger.info(f"Checking role: {role.name}")
        if role.permissions.filter(codename=codename).exists():
            logger.info(f"Permission {codename} found for role {role.name}.")
            return True
    logger.error(f"Permission denied for user: {user}")
    return False