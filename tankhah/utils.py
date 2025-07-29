
import logging

from django.core.exceptions import PermissionDenied
from core.models import Organization
from django.contrib.contenttypes.models import ContentType
from tankhah.models import ApprovalLog
from core.models import AccessRule

logger = logging.getLogger('Util_Tankhah')
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
def get_factor_current_stage___(factor):
    logger.debug(f"[get_factor_current_stage] Fetching stage for factor {factor.factornumber}")
    try:
        # ابتدا بررسی ApprovalLog برای آخرین مرحله ثبت‌شده
        last_log = ApprovalLog.objects.filter(
            factor=factor,
            stage__isnull=False
        ).order_by('-timestamp').first()
        if last_log and last_log.stage:
            logger.debug(f"[get_factor_current_stage] Found stage_order {last_log.stage.stage_order} from ApprovalLog")
            return last_log.stage.stage_order  # عدد stage_order رو برگردون
        # در غیر این صورت، stage_order تنخواه رو برگردون
        stage = factor.tankhah.current_stage
        if stage:
            logger.debug(f"[get_factor_current_stage] Found stage_order {stage.stage_order} from AccessRule")
            return stage.stage_order
        # اگه هیچ مرحله‌ای پیدا نشد، مقدار پیش‌فرض (مثلاً 1)
        logger.debug(f"[get_factor_current_stage] No stage found, defaulting to 1")
        return 1
    except Exception as e:
        logger.error(f"[get_factor_current_stage] Error fetching stage for factor {factor.factornumber}: {e}", exc_info=True)
        return 1  # مقدار پیش‌فرض در صورت خطا

def get_factor_current_stage(factor):
    """
    تعیین مرحله فعلی فاکتور بر اساس آخرین ApprovalLog.
    اگر هیچ ApprovalLog وجود نداشته باشد، اولین stage_order از AccessRule (stage_order=1) را برمی‌گرداند.
    """
    logger.debug(f"[get_factor_current_stage] Fetching stage for factor {factor.number}")
    try:

        last_log = ApprovalLog.objects.filter(
                factor=factor,
                content_type=ContentType.objects.get_for_model(factor),
                object_id=factor.id
            ).order_by('-timestamp').first()

        if last_log and last_log.stage:
            logger.debug(f"[get_factor_current_stage] Found stage_order {last_log.stage} from ApprovalLog")
            return last_log.stage

        first_rule = AccessRule.objects.filter(
            entity_type='FACTOR',
            action_type='APPROVED',
            stage_order=1,
            is_active=True
        ).first()
        if first_rule:
            logger.debug(f"[get_factor_current_stage] Found stage_order {first_rule.stage_order} from AccessRule")
            return first_rule.stage_order
        logger.debug("[get_factor_current_stage] No ApprovalLog or AccessRule found, returning default stage 1")
        if factor:
            latest_log = ApprovalLog.objects.filter(factor=factor).order_by('-timestamp').first()
            if latest_log and latest_log.stage:
                logger.debug(
                    f"[get_factor_current_stage] Found stage_order {latest_log.stage.stage_order} from ApprovalLog")
                return latest_log.stage.stage_order
            elif factor.tankhah.current_stage:
                logger.debug(
                    f"[get_factor_current_stage] Using tankhah current stage: {factor.tankhah.current_stage.stage_order}")
                return factor.tankhah.current_stage.stage_order
        logger.debug("[get_factor_current_stage] No stage found, returning default stage_order=1")
        return 1

    except Exception as e:
        logger.error(f"[get_factor_current_stage] Error for factor {factor.number}: {str(e)}", exc_info=True)
        return 1