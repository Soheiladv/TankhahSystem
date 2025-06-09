import logging
from django.db.models import Max
from core.models import UserPost, AccessRule
from tankhah.models import ApprovalLog, Factor, FactorItem
from django.utils import timezone
from core.models import AccessRule, UserPost
from tankhah.models import Factor

logger = logging.getLogger("can_edit_approval")


def old__can_edit_approval(user, tankhah, stage):
    """
    چک می‌کند آیا کاربر می‌تواند تأیید/رد یا مرحله را تغییر دهد.
    کاربر می‌تواند تا قبل از اینکه سطح بالاتر تأیید را ببیند تغییر دهد، صرف‌نظر از مرحله فعلی.
    """
    # user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
    user_post = UserPost.objects.filter(user=user, is_active=True, end_date__isnull=True).first()
    if not user_post:
        logger.info(f"No active UserPost found for user {user.username}")
        return False
    # اگر کاربر HQ است، دسترسی کامل
    if user_post.post.organization.is_core:
        return True

    user_level = user_post.post.level
    max_change_level = user_post.post.max_change_level

    # آیا سطح بالاتری تأیید را دیده است؟
    higher_approval_seen = ApprovalLog.objects.filter(
        tankhah=tankhah,
        post__level__gt=user_level,
        seen_by_higher=True
    ).exists()

    # آیا تأیید سطح بالاتری بعد از این مرحله ثبت شده است؟
    higher_approval = ApprovalLog.objects.filter(
        tankhah=tankhah,
        stage__order__gt=stage.order,
        action__in=['APPROVE', 'REJECT']
    ).aggregate(Max('post__level'))['post__level__max']

    logger.info(f"can_edit_approval: user_level={user_level}, max_change_level={max_change_level}, "
                f"stage_order={stage.order}, higher_approval={higher_approval}, "
                f"higher_approval_seen={higher_approval_seen}")

    # کاربر می‌تواند تغییر دهد اگر:
    # 1. سطح بالاتری هنوز تأیید را ندیده باشد
    # 2. یا هیچ تأیید سطح بالاتری بعد از این مرحله وجود نداشته باشد
    return (
            not higher_approval_seen and
            (higher_approval is None or user_level >= higher_approval)
    )

def can_edit_approval(user, tankhah, stage):
    """
    بررسی می‌کنه که آیا کاربر اجازه ویرایش (تأیید/رد) فاکتور یا آیتم‌های فاکتور در مرحله فعلی تنخواه رو داره.
    ترتیب: از پایین به بالا (سطح پایین‌تر باید اول تأیید کنه).
    """
    if not user.is_authenticated:
        logger.debug(f"کاربر {user.username} احراز هویت نشده است.")
        return False

    user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
    if not user_post:
        logger.debug(f"کاربر {user.username} هیچ پست فعالی ندارد.")
        return False

    # معافیت کاربران HQ یا سازمان core
    if getattr(user, 'is_hq', False) or user_post.post.organization.is_core:
        logger.debug(f"کاربر {user.username} به دلیل HQ یا سازمان core مجاز به ویرایش است.")
        return True

    # بررسی دسترسی کاربر فعلی برای FACTOR و FACTORITEM
    access_rule_exists = AccessRule.objects.filter(
        organization=user_post.post.organization,
        stage=stage,
        action_type__in=['APPROVE', 'REJECT'],
        entity_type__in=['FACTOR', 'FACTORITEM'],
        min_level__lte=user_post.post.level,
        branch=user_post.post.branch or '',
        is_active=True
    ).exists()

    if not access_rule_exists:
        logger.debug(f"کاربر {user.username} دسترسی لازم برای ویرایش در مرحله {stage} ندارد.")
        return False

    # بررسی تأیید سطوح پایین‌تر (سطوح با min_level بیشتر)
    required_lower_levels = AccessRule.objects.filter(
        organization=user_post.post.organization,
        stage=stage,
        action_type__in=['APPROVE', 'REJECT'],
        entity_type__in=['FACTOR', 'FACTORITEM'],
        min_level__gt=user_post.post.level,
        is_active=True
    ).values_list('min_level', flat=True).distinct()

    for lower_level in required_lower_levels:
        lower_approval_exists = ApprovalLog.objects.filter(
            tankhah=tankhah,
            post__level=lower_level,
            action__in=['APPROVE', 'REJECT'],
            content_type__model__in=['factor', 'factoritem'],
            object_id__in=(
                Factor.objects.filter(tankhah=tankhah).values_list('id', flat=True).union(
                    FactorItem.objects.filter(factor__tankhah=tankhah).values_list('id', flat=True)
                )
            )
        ).exists()

        if not lower_approval_exists:
            logger.debug(
                f"کاربر {user.username} نمی‌تواند ویرایش کند چون سطح پایین‌تر (level={lower_level}) هنوز تأیید نکرده."
            )
            return False

    logger.debug(f"کاربر {user.username} مجاز به ویرایش در مرحله {stage} است.")
    return True