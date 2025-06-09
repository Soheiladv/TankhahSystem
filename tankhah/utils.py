
import logging

from django.core.exceptions import PermissionDenied
from core.models import Organization
logger = logging.getLogger(__name__)
def ok__restrict_to_user_organization(user, allowed_orgs=None):
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


def restrict_to_user_organization(user):
    """
    محدود کردن دسترسی به سازمان‌های کاربر.
    :param user: کاربر فعلی
    :return: QuerySet سازمان‌های مجاز کاربر یا None برای دسترسی کامل (HQ/Superuser)
    """
    if not user or not user.is_authenticated:
        logger.warning("Attempt to restrict organization for anonymous user.")
        return Organization.objects.none()

    # QuerySet سازمان‌های کاربر
    # ** مهم: فرض می‌کنیم مدل Organization یک فیلد ForeignKey به نام org_type دارد **
    # ** که به مدل OrganizationType لینک شده و OrganizationType فیلدی مثل code یا name دارد **
    user_orgs_qs = Organization.objects.filter(
        post__userpost__user=user
    ).select_related('org_type').distinct() # select_related org_type

    if not user_orgs_qs.exists():
        logger.info(f"User {user.username} has no associated organizations.")
        return Organization.objects.none()

    # --- Corrected HQ check ---
    # Filter based on the field in the OrganizationType model that holds 'HQ'
    # Replace 'code' with the actual field name in your OrganizationType model (e.g., 'name', 'type_code')
    is_hq_user = user_orgs_qs.filter(org_type__fname='HQ').exists() # Use related field lookup

    if user.is_superuser or is_hq_user:
        logger.info(f"User {user.username} is superuser or HQ, returning None for full access.")
        return None  # دسترسی کامل

    logger.info(f"User {user.username} restricted to organizations: {list(user_orgs_qs.values_list('id', flat=True))}")
    # Return the QuerySet directly, no need to convert to list here
    return user_orgs_qs

# --- Logic for allowed_orgs is removed as discussed before ---
# This check should happen where allowed_orgs context is available.