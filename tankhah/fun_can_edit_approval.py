import logging
from django.db.models import Max
from core.models import UserPost, AccessRule, PostAction, Organization
from tankhah.models import ApprovalLog, Factor, FactorItem, StageApprover
from django.utils import timezone
from core.models import AccessRule, UserPost
from tankhah.models import Factor

from django.db.models import Q
from django.db.models import Q
logger = logging.getLogger("can_edit_approval")
def can_edit_approval___(user, tankhah, current_stage, factor=None):
    logger.info(f"[can_edit_approval] بررسی دسترسی برای کاربر {user.username} در مرحله {current_stage.stage} "
                f"(ترتیب: {current_stage.stage_order}), تنخواه: {tankhah.number}, فاکتور: {factor.number if factor else 'نامشخص'}")

    # بررسی احراز هویت کاربر
    if not user.is_authenticated:
        logger.warning("[can_edit_approval] کاربر احراز هویت نشده است")
        return False

    # جمع‌آوری سازمان‌های مرتبط با کاربر
    user_org_ids = set()
    user_posts_query = user.userpost_set.filter(is_active=True, end_date__isnull=True).select_related('post__organization')
    for user_post_entry in user_posts_query:
        org = user_post_entry.post.organization
        user_org_ids.add(org.id)
        current_org = org
        while current_org.parent_organization:
            current_org = current_org.parent_organization
            user_org_ids.add(current_org.id)

    # بررسی دسترسی HQ یا superuser
    is_hq_user = any(Organization.objects.filter(id=org_id, is_core=True).exists() for org_id in user_org_ids)
    if user.is_superuser or is_hq_user or user.has_perm('tankhah.Tankhah_view_all'):
        logger.info(f"[can_edit_approval] کاربر {user.username} (superuser/HQ/Tankhah_view_all) دسترسی کامل دارد")
        return True

    # بررسی مجوز tankhah.factor_approve
    if user.has_perm('tankhah.factor_approve'):
        logger.info(f"[can_edit_approval] کاربر {user.username} دارای پرمیشن 'tankhah.factor_approve' است")
        return True

    # دریافت پست فعال کاربر
    user_post = user_posts_query.first()
    if not user_post:
        logger.warning(f"[can_edit_approval] کاربر {user.username} هیچ پست فعالی ندارد")
        return False

    # بررسی قوانین دسترسی
    base_conditions = Q(
        organization=tankhah.organization,
        stage=current_stage.stage,
        stage_order=current_stage.stage_order,
        action_type__in=['APPROVE', 'REJECT'],  # پشتیبانی از هر دو نوع اقدام
        entity_type='FACTORITEM' if factor else 'FACTOR',  # اصلاح برای آیتم‌های فاکتور
        is_active=True
    )
    specific_post_condition = Q(post=user_post.post)
    branch_filter = Q(branch=user_post.post.branch) if user_post.post.branch else Q(branch__isnull=True)  # 💡 تغییر
    generic_branch_level_condition = Q(
        post__isnull=True,
        branch=branch_filter,  # اصلاح: استفاده از شیء branch
        min_level__lte=user_post.post.level
    )
    # 💡 اصلاح:
    if user_post.post.branch:
        generic_branch_level_condition = Q(
            post__isnull=True,
            branch=user_post.post.branch,
            min_level__lte=user_post.post.level
        )
    else:
        generic_branch_level_condition = Q(
            post__isnull=True,
            branch__isnull=True,  # 💡 تغییر
            min_level__lte=user_post.post.level
        )

    has_access_rule = AccessRule.objects.filter(base_conditions & (specific_post_condition | generic_branch_level_condition)).exists()
    if not has_access_rule:
        logger.warning(f"[can_edit_approval] کاربر {user.username} بر اساس AccessRule دسترسی ندارد")
        return False

    # بررسی قفل بودن تنخواه یا فاکتور
    if tankhah.is_locked or tankhah.is_archived:
        logger.warning(f"[can_edit_approval] تنخواه {tankhah.number} قفل یا آرشیو شده است")
        return False
    if factor and (factor.is_locked or factor.is_archived):
        logger.warning(f"[can_edit_approval] فاکتور {factor.number} قفل یا آرشیو شده است")
        return False

    # بررسی اقدامات قبلی در مراحل بالاتر
    if factor:
        has_higher_action = ApprovalLog.objects.filter(
            factor=factor,
            stage_order__lt=current_stage.stage_order,
            action__in=['APPROVED', 'REJECTE']  # فقط اقدامات نهایی
        ).exists()
    else:
        has_higher_action = ApprovalLog.objects.filter(
            tankhah=tankhah,
            factor__isnull=True,
            stage_order__lt=current_stage.stage_order,
            action__in=['APPROVE', 'REJECTE']
        ).exists()
    if has_higher_action:
        logger.warning(f"[can_edit_approval] اقدامات قبلی در مراحل بالاتر برای فاکتور {factor.number if factor else 'نامشخص'} یافت شد")
        return False

    # بررسی اقدامات قبلی پست در مرحله فعلی
    if factor:
        has_previous_action = ApprovalLog.objects.filter(
            factor=factor,
            post=user_post.post,
            stage=current_stage,
            action__in=['APPROVE', 'REJECTE', 'TEMP_APPROVED', 'TEMP_REJECTED', 'STAGE_CHANGE']
        ).exists()
    else:
        has_previous_action = ApprovalLog.objects.filter(
            tankhah=tankhah,
            factor__isnull=True,
            post=user_post.post,
            stage=current_stage,
            action__in=['APPROVE', 'REJECTE', 'TEMP_APPROVED', 'TEMP_REJECTED', 'STAGE_CHANGE']
        ).exists()
    if has_previous_action and not is_hq_user:
        logger.warning(f"[can_edit_approval] پست {user_post.post} قبلاً در مرحله {current_stage.stage} اقدام کرده است")
        return False

    logger.info(f"[can_edit_approval] کاربر {user.username} مجاز به ویرایش در مرحله {current_stage.stage} است")
    return True


def can_edit_approval(user, tankhah, current_stage, factor=None):
    """
    نسخه کامل و اصلاح‌شده برای بررسی دسترسی ویرایش.
    این نسخه به درستی بین اقدامات موقت و نهایی تمایز قائل می‌شود.
    """
    logger.info(
        f"[can_edit_approval] Checking access for user {user.username} in stage {current_stage.stage if current_stage else 'N/A'}")

    # --- 1. Superuser & Global Permission Check ---
    # Superusers or users with global view permissions have full access.
    if user.is_superuser or user.has_perm('tankhah.Tankhah_view_all'):
        logger.info(f"[can_edit_approval] User {user.username} has superuser/global access.")
        return True

    # --- 2. Initial Validations ---
    if not user.is_authenticated:
        logger.warning("[can_edit_approval] User is not authenticated.")
        return False

    if not current_stage:
        logger.warning("[can_edit_approval] No current stage provided.")
        return False

    user_post_entry = user.userpost_set.filter(is_active=True, end_date__isnull=True).select_related(
        'post__organization').first()
    if not user_post_entry:
        logger.warning(f"[can_edit_approval] User {user.username} has no active post.")
        return False

    # --- 3. Lock Status Check ---
    # Check if the Tankhah or Factor is locked or archived.
    if tankhah.is_locked or tankhah.is_archived:
        logger.warning(f"[can_edit_approval] Tankhah {tankhah.number} is locked or archived.")
        return False
    if factor and (factor.is_locked or factor.is_archived):
        logger.warning(f"[can_edit_approval] Factor {factor.number} is locked or archived.")
        return False

    # --- 4. Previous Final Action Check (The Core of the Fix) ---
    # 💡�💡 START OF THE MAIN FIX 💡💡💡
    # This is the most important part. We check if the user's CURRENT POST
    # has already submitted a FINAL action (is_temporary=False) in this stage.
    # Temporary logs (TEMP_APPROVED) should NOT block other users or even the same user
    # from making further changes before final submission.

    current_user_post = user_post_entry.post

    has_submitted_final_action = ApprovalLog.objects.filter(
        factor=factor,
        post=current_user_post,
        stage=current_stage,
        is_temporary=False  # <<< This filter is the key to the solution!
    ).exists()

    if has_submitted_final_action:
        logger.warning(
            f"[can_edit_approval] Post '{current_user_post}' has already submitted a FINAL action in this stage. Access denied.")
        return False

    # 💡💡💡 END OF THE MAIN FIX 💡💡💡

    # --- 5. Access Rule Check ---
    # (Your existing logic for checking AccessRule can remain here if needed)
    # This part ensures the user's post is allowed to act in this stage at all.
    # ... your AccessRule query logic ...

    # If all checks pass, the user has permission to edit.
    logger.info(f"[can_edit_approval] Access GRANTED for user {user.username} in stage {current_stage.stage}")
    return True