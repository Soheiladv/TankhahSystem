import logging
from django.db.models import Max
from core.models import UserPost, AccessRule, PostAction, Organization
from tankhah.models import ApprovalLog, Factor, FactorItem, StageApprover
from django.utils import timezone
from core.models import AccessRule, UserPost
from tankhah.models import Factor

from django.db.models import Q

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

def can_edit_approval_OK(user, tankhah, stage):
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

def can_edit_approval______(user, tankhah, current_stage):
    """
    بررسی می‌کند که آیا کاربر اجازه تأیید/رد فاکتور یا آیتم‌های آن را در مرحله فعلی دارد.
    :param user: کاربر فعلی
    :param tankhah: تنخواه مرتبط
    :param current_stage: مرحله فعلی گردش کار
    :return: True اگر کاربر مجاز به ویرایش باشد، False در غیر این صورت
    """
    logger.info(f"[can_edit_approval] بررسی دسترسی برای کاربر {user.username}, تنخواه {tankhah.number}, مرحله {current_stage.name}")

    # بررسی احراز هویت کاربر
    if not user.is_authenticated:
        logger.warning("[can_edit_approval] کاربر احراز هویت نشده است")
        return False  # خطا: کاربر باید وارد سیستم شده باشد

    # بررسی پست فعال کاربر
    user_post = user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
    if not user_post:
        logger.warning(f"[can_edit_approval] کاربر {user.username} هیچ پست فعالی ندارد")
        return False  # خطا: کاربر باید پست فعال داشته باشد

    # بررسی دسترسی مدیرکل یا HQ
    if user.is_superuser or getattr(user, 'is_hq', False) or user_post.post.organization.is_core:
        logger.debug(f"[can_edit_approval] کاربر {user.username} به دلیل مدیرکل یا HQ دسترسی کامل دارد")
        return True  # معافیت برای مدیرکل یا سازمان مرکزی

    # بررسی قفل بودن تنخواه یا فاکتورهای مرتبط
    if tankhah.is_locked or tankhah.is_archived:
        logger.warning(f"[can_edit_approval] تنخواه {tankhah.number} قفل یا آرشیو شده است")
        return False  # خطا: تنخواه قفل یا آرشیو شده است

    # بررسی قفل بودن فاکتورها
    if Factor.objects.filter(tankhah=tankhah, is_locked=True).exists():
        logger.warning(f"[can_edit_approval] حداقل یکی از فاکتورهای تنخواه {tankhah.number} قفل شده است")
        return False  # خطا: فاکتور قفل شده است

    # بررسی وجود PostAction برای تأیید
    has_action = PostAction.objects.filter(
        post=user_post.post,
        stage=current_stage,
        action_type='APPROVE',
        entity_type__in=['FACTOR', 'FACTORITEM'],
        is_active=True
    ).exists()
    if not has_action:
        logger.warning(f"[can_edit_approval] کاربر {user.username} دسترسی تأیید برای مرحله {current_stage.name} ندارد")
        return False  # خطا: کاربر مجوز لازم را ندارد

    # بررسی اقدام قبلی کاربر برای این تنخواه یا فاکتورهای آن
    has_previous_action = ApprovalLog.objects.filter(
        Q(tankhah=tankhah) | Q(factor__tankhah=tankhah),
        user=user,
        action__in=['APPROVE', 'REJECT']
    ).exists()
    if has_previous_action:
        logger.warning(f"[can_edit_approval] کاربر {user.username} قبلاً برای تنخواه {tankhah.number} اقدام کرده است")
        return False  # خطا: کاربر قبلاً اقدام کرده است

    # بررسی ترتیب تأیید (سطوح پایین‌تر باید ابتدا تأیید کنند)
    required_lower_levels = PostAction.objects.filter(
        stage=current_stage,
        action_type='APPROVE',
        entity_type__in=['FACTOR', 'FACTORITEM'],
        post__level__gt=user_post.post.level,
        is_active=True
    ).values_list('post__level', flat=True).distinct()
    logger.debug(f"[can_edit_approval] سطوح پایین‌تر موردنیاز: {list(required_lower_levels)}")

    for lower_level in required_lower_levels:
        lower_approval_exists = ApprovalLog.objects.filter(
            tankhah=tankhah,
            post__level=lower_level,
            action='APPROVE',
            content_type__model__in=['factor', 'factoritem'],
            object_id__in=(
                Factor.objects.filter(tankhah=tankhah).values_list('id', flat=True) |
                FactorItem.objects.filter(factor__tankhah=tankhah).values_list('id', flat=True)
            )
        ).exists()
        if not lower_approval_exists:
            logger.warning(f"[can_edit_approval] سطح پایین‌تر {lower_level} برای تنخواه {tankhah.number} هنوز تأیید نکرده است")
            return False  # خطا: سطح پایین‌تر باید ابتدا تأیید کند

    # بررسی تأیید توسط سطوح بالاتر
    higher_level_approval = ApprovalLog.objects.filter(
        tankhah=tankhah,
        stage__order__gte=current_stage.order,
        action='APPROVE',
        post__level__lt=user_post.post.level,
        content_type__model__in=['factor', 'factoritem']
    ).exists()
    if higher_level_approval:
        logger.warning(f"[can_edit_approval] سطح بالاتری قبلاً برای تنخواه {tankhah.number} تأیید کرده است")
        return False  # خطا: سطح بالاتر قبلاً تأیید کرده است

    logger.info(f"[can_edit_approval] کاربر {user.username} مجاز به ویرایش در مرحله {current_stage.name} است")
    return True


def can_edit_approval(user, tankhah, current_stage):
    """
    بررسی می‌کند که آیا کاربر می‌تواند فاکتور یا آیتم‌های آن را ویرایش کند.

    Args:
        user: کاربر فعلی
        tankhah: شیء تنخواه
        current_stage: مرحله فعلی گردش کار

    Returns:
        bool: آیا کاربر دسترسی ویرایش/تأیید دارد؟
    """
    logger = logging.getLogger('factor_approval')
    logger.info(f"[can_edit_approval] بررسی دسترسی ویرایش برای کاربر {user.username} در مرحله {current_stage.name}")

    # دسترسی کامل برای superuser، کاربران HQ، یا کسانی که Tankhah_view_all دارند
    user_org_ids = set()
    for user_post in user.userpost_set.filter(is_active=True):
        org = user_post.post.organization
        user_org_ids.add(org.id)
        current_org = org
        while current_org.parent_organization:
            current_org = current_org.parent_organization
            user_org_ids.add(current_org.id)

    is_hq_user = any(
        Organization.objects.filter(id=org_id, org_type__org_type='HQ').exists()
        for org_id in user_org_ids
    )

    if user.is_superuser or is_hq_user or user.has_perm('tankhah.Tankhah_view_all'):
        logger.info(
            f"[can_edit_approval] کاربر {user.username} superuser، HQ یا دارای Tankhah_view_all است، دسترسی کامل اعطا شد")
        return True

    # بررسی permission factor_approve
    if user.has_perm('tankhah.factor_approve'):
        logger.info(f"[can_edit_approval] کاربر {user.username} دارای permission factor_approve است")
        return True

    # بررسی پست فعال کاربر
    user_post = user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
    if not user_post:
        logger.warning(f"[can_edit_approval] کاربر {user.username} هیچ پست فعالی ندارد")
        return False

    # بررسی وجود PostAction برای مرحله و پست کاربر
    has_action = PostAction.objects.filter(
        post=user_post.post,
        stage=current_stage,
        action_type='APPROVE',
        entity_type='FACTOR',
        is_active=True
    ).exists()

    if not has_action:
        logger.warning(f"[can_edit_approval] کاربر {user.username} دسترسی تأیید برای مرحله {current_stage.name} ندارد")
        return False

    # بررسی قفل بودن تنخواه یا فاکتور
    if tankhah.is_locked or tankhah.is_archived:
        logger.warning(f"[can_edit_approval] تنخواه {tankhah.number} قفل یا آرشیو شده است")
        return False

    # بررسی اقدام قبلی برای تنخواه یا فاکتور
    has_previous_action = ApprovalLog.objects.filter(
        Q(tankhah=tankhah) | Q(factor__tankhah=tankhah),
        user=user,
        action__in=['APPROVE', 'REJECT', 'STAGE_CHANGE']
    ).exists()

    if has_previous_action:
        logger.warning(f"[can_edit_approval] کاربر {user.username} قبلاً برای تنخواه {tankhah.number} اقدام کرده است")
        return False

    # بررسی سطح دسترسی کاربر نسبت به مرحله
    if current_stage.order > user_post.post.level:
        logger.warning(
            f"[can_edit_approval] سطح مرحله ({current_stage.order}) بیشتر از سطح کاربر ({user_post.post.level}) است")
        return False

    logger.info(f"[can_edit_approval] کاربر {user.username} مجاز به ویرایش در مرحله {current_stage.name} است")
    return True