# tanbakh/utils.py
from django.core.exceptions import PermissionDenied
import logging

from core.tests import CustomUser

logger = logging.getLogger(__name__)
def restrict_to_user_organization(user, allowed_orgs=None):
    """
    محدود کردن دسترسی به سازمان‌های کاربر.
    :param user: کاربر فعلی
    :param allowed_orgs: لیست سازمان‌های مجاز (اختیاری)
    :return: لیست سازمان‌های کاربر یا None برای HQ/Superuser
    """
    user_orgs = [up.post.organization for up in user.userpost_set.all()] if user.userpost_set.exists() else []
    is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False

    if user.is_superuser or is_hq_user:
        logger.info(f"User {user} is superuser or HQ, full access granted")
        return None  # دسترسی کامل

    if allowed_orgs is not None:
        # اگر allowed_orgs یک شیء تکی باشد، آن را به لیست تبدیل می‌کنیم
        if not isinstance(allowed_orgs, (list, tuple, set)):
            allowed_orgs = [allowed_orgs]
        if not any(org in user_orgs for org in allowed_orgs):
            logger.warning(f"User {user} has no access to organizations: {allowed_orgs}")
            raise PermissionDenied("شما به این سازمان دسترسی ندارید.")
    return user_orgs

