import logging

from django.contrib import messages
from django.db import models
from django.db.models import Max
from core.models import UserPost, Status, PostAction, Organization
from tankhah.models import ApprovalLog, Factor, FactorItem, StageApprover
from django.utils import timezone
from core.models import Status, UserPost
from tankhah.models import Factor

from django.db.models import Q
from django.db.models import Q

def can_edit_approval____________________________(user, tankhah, current_stage, factor=None):
    """
    نسخه نهایی و ترکیبی برای بررسی دسترسی کاربر جهت اقدام روی ردیف‌های فاکتور.
    این نسخه هم قوانین خاص (مبتنی بر پست) و هم قوانین عمومی (مبتنی بر سطح/شعبه) را پشتیبانی می‌کند.
    """
    logger.debug(
        f"[can_edit_approval] Checking access for user '{user.username}' in stage '{current_stage.stage if current_stage else 'N/A'}'")

    # 1. بررسی‌های اولیه
    if not user.is_authenticated or not current_stage or tankhah.is_locked or (factor and factor.is_locked):
        logger.warning("[can_edit_approval] Initial checks failed (auth, stage, or lock). DENIED.")
        return False

    # 2. دسترسی کامل
    if _user_has_super_access(user):
        return True

    # 3. بررسی پست فعال
    user_posts = _get_active_user_posts(user)
    if not user_posts.exists():
        logger.warning(f"[can_edit_approval] User '{user.username}' has no active posts. DENIED.")
        return False

    # 4. بررسی موانع گردش کار
    if _check_workflow_blockers(user, factor, current_stage, user_posts):
        return False

    # 5. بررسی قوانین دسترسی (ترکیب قوانین خاص و عمومی)
    user_post_ids = list(user_posts.values_list('post_id', flat=True))
    max_user_level = user_posts.aggregate(max_level=Max('post__level'))['max_level'] or 0

    # کوئری پایه برای قوانین این مرحله
    base_rule_query = Q(
        organization=tankhah.organization,
        stage_order=current_stage.stage_order,
        entity_type='FACTORITEM',
        is_active=True,
        # **تغییر کلیدی:** SUBMIT را به اقدامات مجاز اضافه می‌کنیم
        # action_type__in=['APPROVE', 'REJECT', 'SUBMIT', 'FINAL_APPROVE'] # فعلا خذف تا بعد
    )

    # قوانین خاص: مستقیماً به پست کاربر اشاره دارند
    specific_post_rule = Q(post_id__in=user_post_ids)

    # قوانین عمومی: به پست خاصی اشاره ندارند و بر اساس سطح و شعبه عمل می‌کنند
    generic_rule = Q(post__isnull=True, min_level__lte=max_user_level)

    # برای قوانین عمومی، باید شعبه نیز مطابقت داشته باشد
    branch_conditions = Q()
    user_branches = {up.post.branch for up in user_posts}
    for branch in user_branches:
        if branch:
            branch_conditions |= Q(branch=branch)
        else:
            branch_conditions |= Q(branch__isnull=True)

    if branch_conditions: # فقط اگر کاربر شعبه‌ای داشت، این شرط را اضافه کن
        generic_rule.add(branch_conditions, Q.AND)

    # اجرای کوئری نهایی
    has_access = AccessRule.objects.filter(base_rule_query & (specific_post_rule | generic_rule)).exists()

    if has_access:
        logger.info(f"[can_edit_approval] Access GRANTED for '{user.username}' based on specific or generic rules.")
    else:
        logger.warning(f"[can_edit_approval] No applicable access rule found for '{user.username}'. DENIED.")

    return has_access

def can_edit_approval__(user, tankhah, current_stage, factor=None):
    """
    بررسی دسترسی کاربر برای ویرایش/تأیید فاکتور یا آیتم‌های آن در مرحله فعلی.

    Args:
        user (CustomUser): کاربر فعلی.
        tankhah (Tankhah): تنخواه مربوطه.
        current_stage (AccessRule): مرحله فعلی گردش کار.
        factor (Factor, optional): فاکتور مربوطه.

    Returns:
        bool: True اگر کاربر دسترسی داشته باشد، False در غیر این صورت.
    """
    logger.debug(
        f"[can_edit_approval] Checking access for user '{user.username}' "
        f"in stage '{current_stage.stage if current_stage else 'N/A'}' "
        f"for factor '{factor.number if factor else 'N/A'}' "
        f"with tankhah '{tankhah.number if tankhah else 'N/A'}'"
    )

    # 1. بررسی احراز هویت
    logger.debug(f"[can_edit_approval] Step 1: Checking if user is authenticated")
    if not user.is_authenticated:
        logger.warning("[can_edit_approval] User is not authenticated")
        return False
    logger.debug(f"[can_edit_approval] User '{user.username}' is authenticated")

    # 2. دسترسی سوپریوزر یا کاربران با مجوز سراسری
    logger.debug(f"[can_edit_approval] Step 2: Checking superuser or global permission")
    if user.is_superuser or user.has_perm('tankhah.Tankhah_view_all'):
        logger.info(f"[can_edit_approval] User '{user.username}' has superuser/global perm. GRANTED.")
        return True
    logger.debug(f"[can_edit_approval] User '{user.username}' is not superuser and lacks 'Tankhah_view_all'")

    # 3. بررسی مرحله
    logger.debug(f"[can_edit_approval] Step 3: Checking current stage")
    if not current_stage:
        logger.warning("[can_edit_approval] No current stage provided")
        return False
    logger.debug(f"[can_edit_approval] Current stage: '{current_stage.stage}' (ID: {current_stage.id})")

    # 4. بررسی پست‌های فعال کاربر
    logger.debug(f"[can_edit_approval] Step 4: Fetching active user posts")
    user_posts = user.userpost_set.filter(is_active=True, end_date__isnull=True).select_related('post__organization')
    if not user_posts.exists():
        logger.warning(f"[can_edit_approval] No active posts for user '{user.username}'")
        return False
    user_post_ids = list(user_posts.values_list('post_id', flat=True))
    logger.debug(f"[can_edit_approval] Active posts for user: {user_post_ids}")

    # 5. بررسی دسترسی HQ
    logger.debug(f"[can_edit_approval] Step 5: Checking HQ access")
    user_orgs = set()
    for user_post in user_posts:
        org = user_post.post.organization
        user_orgs.add(org)
        parent = org.parent_organization
        while parent:
            user_orgs.add(parent)
            parent = parent.parent_organization
    if any(org.is_core for org in user_orgs):
        logger.info(f"[can_edit_approval] User '{user.username}' is an HQ user. GRANTED.")
        return True
    logger.debug(f"[can_edit_approval] User '{user.username}' is not in an HQ organization")

    # 6. بررسی قفل بودن تنخواه یا فاکتور
    logger.debug(f"[can_edit_approval] Step 6: Checking lock status")
    if tankhah.is_locked or tankhah.is_archived:
        logger.warning(f"[can_edit_approval] Tankhah '{tankhah.number}' is locked or archived")
        return False
    if factor and factor.is_locked:
        logger.warning(f"[can_edit_approval] Factor '{factor.number}' is locked")
        return False
    logger.debug(f"[can_edit_approval] Tankhah and factor are not locked")

    # 7. بررسی قوانین دسترسی (خاص و عمومی)
    logger.debug(f"[can_edit_approval] Step 7: Checking access rules")
    max_user_level = user_posts.aggregate(max_level=Max('post__level'))['max_level'] or 0
    logger.debug(f"[can_edit_approval] Max user level: {max_user_level}")
    base_rule_query = Q(
        organization=tankhah.organization,
        stage_order=current_stage.stage_order,
        action_type__in=['APPROVE', 'REJECT'],  # محدود به اقدامات مجاز
        entity_type='FACTORITEM',  # فقط FACTORITEM
        is_active=True
    )
    specific_post_rule = Q(post_id__in=user_post_ids)
    generic_rule = Q(post__isnull=True, min_level__lte=max_user_level)
    for user_post in user_posts:
        branch_filter = Q(branch=user_post.post.branch) if user_post.post.branch else Q(branch__isnull=True)
        generic_rule &= branch_filter
        logger.debug(f"[can_edit_approval] Branch filter for post {user_post.post_id}: {branch_filter}")

    access_rules = AccessRule.objects.filter(base_rule_query & (specific_post_rule | generic_rule))
    if not access_rules.exists():
        logger.warning(
            f"[can_edit_approval] No access rule found for user posts {user_post_ids} "
            f"in stage '{current_stage.stage}' with query: {base_rule_query & (specific_post_rule | generic_rule)}"
        )
        return False
    logger.debug(f"[can_edit_approval] Found access rules: {list(access_rules.values('id', 'action_type'))}")

    # 8. بررسی اقدام نهایی مقام بالاتر
    logger.debug(f"[can_edit_approval] Step 8: Checking higher-level final actions")
    higher_level_final_action_exists = ApprovalLog.objects.filter(
        factor=factor,
        stage=current_stage,
        is_temporary=False,
        post__level__gt=max_user_level
    ).exists()
    if higher_level_final_action_exists:
        logger.warning(f"[can_edit_approval] Access DENIED for '{user.username}' due to higher-level final action")
        return False
    logger.debug(f"[can_edit_approval] No higher-level final actions found")

    # 9. بررسی اقدام نهایی کاربر
    logger.debug(f"[can_edit_approval] Step 9: Checking user's final actions")
    user_has_submitted_final_action = ApprovalLog.objects.filter(
        factor=factor,
        stage=current_stage,
        is_temporary=False,
        post_id__in=user_post_ids
    ).exists()
    if user_has_submitted_final_action:
        logger.warning(f"[can_edit_approval] Access DENIED for '{user.username}' due to existing final action")
        return False
    logger.debug(f"[can_edit_approval] No final actions by user")

    logger.info(f"[can_edit_approval] Access GRANTED for user '{user.username}'")
    return True
def can_edit_approval (user, tankhah, current_stage, factor=None):
    """
    نسخه نهایی و ترکیبی برای بررسی دسترسی کاربر جهت اقدام روی ردیف‌های فاکتور.
    این نسخه هم قوانین خاص (مبتنی بر پست) و هم قوانین عمومی (مبتنی بر سطح/شعبه) را پشتیبانی می‌کند.
    """
    logger.debug(
        f"[can_edit_approval] Checking access for user '{user.username}' in stage '{current_stage.stage if current_stage else 'N/A'}'")

    # 1. بررسی‌های اولیه
    if not user.is_authenticated or not current_stage or tankhah.is_locked or (factor and factor.is_locked):
        logger.warning("[can_edit_approval] Initial checks failed (auth, stage, or lock). DENIED.")
        return False

    # 2. دسترسی کامل
    if _user_has_super_access(user):
        return True

    # 3. بررسی پست فعال
    user_posts = _get_active_user_posts(user)
    if not user_posts.exists():
        logger.warning(f"[can_edit_approval] User '{user.username}' has no active posts. DENIED.")
        return False

    # 4. بررسی موانع گردش کار
    if _check_workflow_blockers(user, factor, current_stage, user_posts):
        return False

    # 5. بررسی قوانین دسترسی (ترکیب قوانین خاص و عمومی)
    user_post_ids = list(user_posts.values_list('post_id', flat=True))
    max_user_level = user_posts.aggregate(max_level=Max('post__level'))['max_level'] or 0

    # کوئری پایه برای قوانین این مرحله
    base_rule_query = Q(
        organization=tankhah.organization,
        stage_order=current_stage.stage_order,
        entity_type='FACTORITEM',
        is_active=True
    )

    # قوانین خاص: مستقیماً به پست کاربر اشاره دارند
    specific_post_rule = Q(post_id__in=user_post_ids)

    # قوانین عمومی: به پست خاصی اشاره ندارند و بر اساس سطح و شعبه عمل می‌کنند
    generic_rule = Q(post__isnull=True, min_level__lte=max_user_level)

    # برای قوانین عمومی، باید شعبه نیز مطابقت داشته باشد
    # ما یک Q object پیچیده برای تمام شعبه‌های ممکن کاربر می‌سازیم
    branch_conditions = Q()
    for up in user_posts:
        if up.post.branch:
            branch_conditions |= Q(branch=up.post.branch)
        else:
            branch_conditions |= Q(branch__isnull=True)

    generic_rule.add(branch_conditions, Q.AND)

    # اجرای کوئری نهایی
    has_access = AccessRule.objects.filter(base_rule_query & (specific_post_rule | generic_rule)).exists()

    if has_access:
        logger.info(f"[can_edit_approval] Access GRANTED for '{user.username}' based on specific or generic rules.")
    else:
        logger.warning(f"[can_edit_approval] No applicable access rule found for '{user.username}'. DENIED.")

    return has_access
#
# فایل: tankhah/Factor/Approved/fun_can_edit_approval.py (نسخه کامل و نهایی)
#
def _user_has_super_access(user):
    """بررسی می‌کند آیا کاربر دسترسی کامل (سوپریوزر یا پرمیشن کلی) دارد یا خیر."""
    has_access = user.is_superuser or user.has_perm('tankhah.Tankhah_view_all')
    if has_access:
        logger.info(f"[can_edit_approval] User '{user.username}' has superuser/global perm. GRANTED.")
    return has_access
def _get_active_user_posts(user):
    """پست‌های فعال کاربر را به همراه بهینه‌سازی کوئری برمی‌گرداند."""
    return user.userpost_set.filter(is_active=True).select_related('post__organization', 'post__branch')
def _check_workflow_blockers(user, factor, current_stage, user_posts):
    """
    بررسی می‌کند آیا موانع گردش کار (اقدام تکراری یا اقدام سطح بالاتر) وجود دارد یا خیر.
    """
    if not factor:  # اگر فاکتور هنوز ایجاد نشده، مانعی وجود ندارد
        return False

    post_ids = list(user_posts.values_list('post_id', flat=True))
    max_user_level = user_posts.aggregate(max_level=Max('post__level'))['max_level'] or 0
    logger.warning(f'CHECK in _check_workflow_blockers Function: post_ids: {post_ids} , max_level: {max_user_level}')
    # بررسی اقدام تکراری توسط خود کاربر
    if ApprovalLog.objects.filter(factor=factor, stage_rule=current_stage, is_temporary=False, post_id__in=post_ids).exists():
        logger.warning(
            f"[can_edit_approval] DENIED for '{user.username}': User has already submitted a final action in this stage.")
        return True  # مانع وجود دارد

    # بررسی اقدام نهایی توسط یک کاربر با سطح بالاتر
    if ApprovalLog.objects.filter(factor=factor, stage_rule=current_stage, is_temporary=False,
                                  post__level__gt=max_user_level
                                  ).exists():
        logger.warning(
            f"[can_edit_approval] DENIED for '{user.username}': A higher-level user has already submitted a final action.")
        return True  # مانع وجود دارد

    return False  # هیچ مانعی وجود ندارد

# ----------------------------------------+
#
# فایل جدید: tankhah/permissions.py
from django.db.models import Max, Q
logger = logging.getLogger('ApprovalPermissions')


def check_approval_permissions(user, tankhah, factor, current_stage):
    """
    تابع نهایی و یکپارچه برای بررسی دسترسی و استخراج اقدامات مجاز.
    این تابع یک دیکشنری حاوی 'can_edit' و 'allowed_actions' برمی‌گرداند.
    """
    logger.debug(
        f"--- [START Permission Check] User: '{user.username}', Factor: {factor.pk}, Stage: '{current_stage.stage}' ---")

    # دیکشنری خروجی پیش‌فرض
    permissions = {'can_edit': False, 'allowed_actions': []}

    # --- مرحله ۱: بررسی‌های اولیه و موانع ---
    if not user.is_authenticated or not current_stage or tankhah.is_locked or factor.is_locked:
        logger.warning("Initial checks failed (auth, stage, or lock). Access DENIED.")
        return permissions

    # دسترسی کامل برای سوپریوزر (اما همچنان باید پست فعال داشته باشد تا اقداماتش ثبت شود)
    if user.is_superuser:
        logger.info("User is a superuser. Granting provisional access, pending active post check.")

    user_posts_qs = user.userpost_set.filter(is_active=True).select_related('post', 'post__branch')
    if not user_posts_qs.exists():
        logger.warning(f"User '{user.username}' has no active post. Access DENIED.")
        return permissions

    # --- مرحله ۲: بررسی موانع گردش کار ---
    post_ids = list(user_posts_qs.values_list('post_id', flat=True))
    max_user_level = user_posts_qs.aggregate(max_level=Max('post__level'))['max_level'] or 0

    if ApprovalLog.objects.filter(factor=factor, stage_rule=current_stage, is_temporary=False,
                                  post_id__in=post_ids).exists():
        logger.warning("Workflow Blocker: User has already submitted a final action in this stage. Access DENIED.")
        return permissions

    if ApprovalLog.objects.filter(factor=factor, stage_rule=current_stage, is_temporary=False,
                                  post__level__gt=max_user_level).exists():
        logger.warning("Workflow Blocker: A higher-level user has already submitted a final action. Access DENIED.")
        return permissions

    logger.debug("No workflow blockers found.")

    # --- مرحله ۳: کوئری اصلی برای پیدا کردن قوانین دسترسی (ترکیبی) ---
    if user.is_superuser:
        # برای سوپریوزر، تمام اقدامات ممکن در گردش کار را برمی‌گردانیم
        from tankhah.constants import ACTION_TYPES, ACTIONS_WITHOUT_STAGE
        permissions['allowed_actions'] = [code for code, label in ACTION_TYPES if code not in ACTIONS_WITHOUT_STAGE]
        permissions['can_edit'] = True
        logger.info(f"Superuser access GRANTED. Actions: {permissions['allowed_actions']}")
        return permissions

    base_query = Q(organization=tankhah.organization, stage_order=current_stage.stage_order, entity_type='FACTORITEM',
                   is_active=True)
    specific_rule = Q(post_id__in=post_ids)
    generic_rule = Q(post__isnull=True, min_level__lte=max_user_level)

    branch_conditions = Q()
    for up in user_posts_qs:
        branch_conditions |= Q(branch=up.post.branch) if up.post.branch else Q(branch__isnull=True)
    generic_rule.add(branch_conditions, Q.AND)

    # استفاده از مدل‌های جدید گردش کار
    from core.models import Transition, Action, Status
    
    # پیدا کردن transition های مجاز برای کاربر
    user_posts = user_posts_qs.values_list('post', flat=True)
    
    # کوئری برای transition های مجاز
    allowed_transitions = Transition.objects.filter(
        from_status=current_stage,
        organization=tankhah.organization,
        entity_type__code='FACTOR',
        is_active=True,
        allowed_posts__in=user_posts
    ).distinct()
    
    allowed_actions = list(allowed_transitions.values_list('action__code', flat=True).distinct())

    if allowed_actions:
        permissions['can_edit'] = True
        permissions['allowed_actions'] = allowed_actions
        logger.info(f"Access GRANTED based on rules. Actions: {allowed_actions}")
    else:
        logger.warning("No applicable access rule found for this user in this stage. Access DENIED.")

    logger.debug(f"--- [END Permission Check] ---")
    return permissions