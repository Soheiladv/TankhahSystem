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

def can_edit_approval(user, tankhah, stage):
    """
    بررسی می‌کند که آیا کاربر اجازه تأیید/رد فاکتور یا آیتم‌های فاکتور در مرحله فعلی را دارد.
    :param user: کاربر فعلی
    :param tankhah: تنخواه مرتبط با فاکتور
    :param stage: مرحله فعلی گردش کار
    :return: True اگر کاربر دسترسی دارد، False در غیر این صورت
    """
    logger.debug(f"شروع بررسی دسترسی برای کاربر: {user.username}, تنخواه: {tankhah.number}, مرحله: {stage.name}")

    if not user.is_authenticated:
        logger.debug(f"کاربر {user.username} احراز هویت نشده است")
        return False

    user_post = user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
    if not user_post:
        logger.debug(f"کاربر {user.username} هیچ پست فعالی ندارد")
        return False

    user_level = user_post.post.level
    logger.debug(f"سطح کاربر {user.username}: {user_level}")

    if getattr(user, 'is_hq', False) or user_post.post.organization.is_core:
        logger.debug(f"کاربر {user.username} به دلیل HQ یا سازمان core دسترسی کامل دارد")
        return True

    access_rule_exists = AccessRule.objects.filter(
        organization=user_post.post.organization,
        stage=stage,
        action_type__in=['APPROVE', 'REJECT'],
        entity_type__in=['FACTOR', 'FACTORITEM'],
        min_level__lte=user_level,  # سطح کاربر باید بزرگ‌تر یا مساوی min_level باشد
        branch=user_post.post.branch or '',
        is_active=True
    ).exists()
    logger.debug(f"وجود قانون دسترسی برای کاربر {user.username} در مرحله {stage.name}: {access_rule_exists}")

    if not access_rule_exists:
        logger.debug(f"کاربر {user.username} قانون دسترسی لازم برای مرحله {stage.name} ندارد")
        return False

    higher_level_approval = ApprovalLog.objects.filter(
        tankhah=tankhah,
        stage__order__gte=stage.order,
        action='APPROVE',
        post__level__lt=user_level,  # سطوح بالاتر (level کوچکتر)
        content_type__model__in=['factor', 'factoritem'],
        object_id__in=(
            Factor.objects.filter(tankhah=tankhah).values_list('id', flat=True).union(
                FactorItem.objects.filter(factor__tankhah=tankhah).values_list('id', flat=True)
            )
        )
    ).exists()
    logger.debug(f"وجود تأیید سطح بالاتر برای تنخواه {tankhah.number}: {higher_level_approval}")

    if higher_level_approval:
        logger.debug(f"کاربر {user.username} نمی‌تواند اقدام کند: سطح بالاتری (سطح < {user_level}) تأیید کرده است")
        return False

    required_lower_levels = AccessRule.objects.filter(
        organization=user_post.post.organization,
        stage=stage,
        action_type__in=['APPROVE', 'REJECT'],
        entity_type__in=['FACTOR', 'FACTORITEM'],
        min_level__gt=user_level,  # سطوح پایین‌تر (level بزرگتر)
        is_active=True
    ).values_list('min_level', flat=True).distinct()
    logger.debug(f"سطوح پایین‌تر موردنیاز برای مرحله {stage.name}: {list(required_lower_levels)}")

    for lower_level in required_lower_levels:
        lower_approval_exists = ApprovalLog.objects.filter(
            tankhah=tankhah,
            post__level=lower_level,
            action='APPROVE',
            content_type__model__in=['factor', 'factoritem'],
            object_id__in=(
                Factor.objects.filter(tankhah=tankhah).values_list('id', flat=True).union(
                    FactorItem.objects.filter(factor__tankhah=tankhah).values_list('id', flat=True)
                )
            )
        ).exists()
        logger.debug(f"وجود تأیید برای سطح {lower_level} در تنخواه {tankhah.number}: {lower_approval_exists}")

        if not lower_approval_exists:
            logger.debug(f"کاربر {user.username} نمی‌تواند اقدام کند: سطح پایین‌تر {lower_level} هنوز تأیید نکرده است")
            return False

    logger.debug(f"کاربر {user.username} مجاز به ویرایش در مرحله {stage.name} است")
    return True