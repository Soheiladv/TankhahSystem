import logging
from django.db.models import Max
from core.models import UserPost, AccessRule, PostAction, Organization
from tankhah.models import ApprovalLog, Factor, FactorItem, StageApprover
from django.utils import timezone
from core.models import AccessRule, UserPost
from tankhah.models import Factor

from django.db.models import Q


logger = logging.getLogger("can_edit_approval")

from django.db.models import Q
import logging

def __can_edit_approval(user, tankhah, current_stage, factor=None):
    """
    بررسی می‌کند که آیا کاربر مجاز به ویرایش یا تأیید یک فاکتور در مرحله فعلی است یا خیر.

    سناریوهای بررسی دسترسی:
    1.  **دسترسی کامل (سوپریوزر/HQ/پرمیشن عمومی):** کاربر دارای بالاترین سطح دسترسی است.
    2.  **پرمیشن مستقیم `factor_approve`:** کاربر دارای پرمیشن صریح برای تأیید فاکتور است.
    3.  **بررسی قوانین دسترسی (AccessRule):**
        * **قانون اختصاصی پست:** آیا یک قانون دسترسی برای پست دقیق کاربر در این مرحله تعریف شده است؟
        * **قانون عمومی شعبه/سطح:** اگر قانون اختصاصی پست وجود نداشت، آیا یک قانون عمومی برای شعبه و سطح کاربر تعریف شده است؟
    4.  **بررسی وضعیت قفل/آرشیو:** اطمینان از اینکه تنخواه و فاکتور قفل یا آرشیو نشده‌اند.
    5.  **بررسی اقدامات قبلی در مراحل بالاتر:** جلوگیری از تأیید فاکتور در مراحل پایین‌تر اگر قبلاً در مراحل بالاتر اقدامی صورت گرفته باشد.
    6.  **بررسی اقدامات قبلی کاربر در مرحله فعلی:** جلوگیری از اقدام مجدد توسط همان کاربر در همان مرحله.

    Args:
        user (CustomUser): آبجکت کاربر جاری.
        tankhah (Tankhah): آبجکت تنخواه مربوطه.
        current_stage (WorkflowStage): آبجکت مرحله جاری در گردش کار.
        factor (Factor, optional): آبجکت فاکتور مربوطه. اگر None باشد، بررسی برای تنخواه بدون فاکتور است.

    Returns:
        bool: True اگر کاربر دسترسی داشته باشد، False در غیر این صورت.
    """
    logger.info(
        f"[can_edit_approval] آغاز بررسی دسترسی برای کاربر {user.username} در مرحله {current_stage.name} "
        f"(ترتیب: {current_stage.order}), تنخواه: {tankhah.number}, فاکتور: {factor.number if factor else 'نامشخص'}"
    )

    # === 1. بررسی دسترسی کامل (سوپریوزر، HQ یا پرمیشن عمومی) ===
    # این بخش به کاربرانی با سطح دسترسی بالا (مانند مدیران سیستم یا کاربران HQ) اجازه می‌دهد تا
    # بدون نیاز به AccessRule خاص، عملیات را انجام دهند.
    try:
        user_org_ids = set()
        user_posts_query = user.userpost_set.filter(is_active=True, end_date__isnull=True).select_related(
            'post__organization')
        for user_post_entry in user_posts_query:
            org = user_post_entry.post.organization
            user_org_ids.add(org.id)
            current_org_for_hq_check = org
            while current_org_for_hq_check and current_org_for_hq_check.parent_organization:
                current_org_for_hq_check = current_org_for_hq_check.parent_organization
                user_org_ids.add(current_org_for_hq_check.id)

        # فرض بر این است که مدل Organization و فیلد is_core در دسترس است
        is_hq_user = any(
            Organization.objects.filter(id=org_id, is_core=True).exists()
            for org_id in user_org_ids
        )

        if user.is_superuser or is_hq_user or user.has_perm('tankhah.Tankhah_view_all'):
            logger.info(
                f"[can_edit_approval] کاربر {user.username} (superuser/HQ/Tankhah_view_all) دسترسی کامل دارد."
            )
            return True
    except Exception as e:
        logger.error(f"[can_edit_approval] خطایی در بررسی دسترسی‌های عمومی رخ داد: {e}")
        # ادامه بررسی برای موارد خاص یا بازگرداندن False اگر خطا بحرانی باشد
        # در اینجا، ما ادامه می‌دهیم تا AccessRule بررسی شود.

    # === 2. بررسی پرمیشن مستقیم factor_approve ===
    # این سناریو به کاربرانی که پرمیشن خاص 'tankhah.factor_approve' را دارند، اجازه می‌دهد.
    if user.has_perm('tankhah.factor_approve'):
        logger.info(f"[can_edit_approval] کاربر {user.username} دارای پرمیشن 'tankhah.factor_approve' است.")
        return True

    # === 3. بررسی AccessRule (قوانین دسترسی) ===
    # این بخش پیچیده‌ترین بخش است که تعیین می‌کند آیا کاربر بر اساس نقش سازمانی خود
    # و قوانین تعریف شده، مجاز به انجام عملیات هست یا خیر.

    # دریافت پست فعال کاربر
    # در سیستم شما، کاربر باید حداقل یک پست فعال برای بررسی AccessRule داشته باشد.
    user_post_obj = user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
    if not user_post_obj:
        logger.warning(f"[can_edit_approval] کاربر {user.username} هیچ پست فعالی برای بررسی AccessRule ندارد.")
        return False

    # کوئری واحد برای جستجوی AccessRule
    # این کوئری تلاش می‌کند تا هر نوع قانون دسترسی (اختصاصی پست یا عمومی شعبه/سطح) را پیدا کند.

    # شرایط پایه برای تمام قوانین دسترسی مربوط به این عملیات
    base_conditions = Q(
        organization=tankhah.organization,  # سازمان باید با سازمان تنخواه/فاکتور مطابقت داشته باشد
        stage=current_stage,
        action_type='APPROVE',
        entity_type='FACTOR',
        is_active=True
    )

    # شرط برای قوانین اختصاصی پست (post__id__in)
    specific_post_condition = Q(post=user_post_obj.post)

    # شرط برای قوانین عمومی شعبه/سطح (post__isnull=True)
    # این قوانین برای پست‌های خاصی نیستند، بلکه برای هر کاربری در یک شعبه و سطح مشخص اعمال می‌شوند.
    generic_branch_level_condition = Q(
        post__isnull=True,
        branch=user_post_obj.post.branch,  # قانون برای شعبه‌ای است که پست کاربر در آن قرار دارد
        min_level__lte=user_post_obj.post.level  # سطح پست کاربر باید حداقل سطح مجاز تعریف شده در قانون باشد
    )

    # ترکیب شرایط با OR: اگر هر یک از این دو نوع قانون دسترسی وجود داشته باشد.
    # این کوئری به دنبال حداقل یک AccessRule می‌گردد که یا اختصاصی پست کاربر باشد یا یک قانون عمومی شعبه/سطح که کاربر شرایط آن را دارد.
    # فرض می‌کنیم مدل AccessRule و فیلدهای آن در دسترس هستند.
    has_access_rule = AccessRule.objects.filter(
        base_conditions & (specific_post_condition | generic_branch_level_condition)
    ).exists()

    logger.debug(
        f"[can_edit_approval] بررسی AccessRule برای کاربر {user.username}, پست {user_post_obj.post.name}, "
        f"شعبه {user_post_obj.post.branch.name if user_post_obj.post.branch else 'نامشخص'}, "
        f"سطح {user_post_obj.post.level}, مرحله {current_stage.name}, "
        f"سازمان {tankhah.organization.name if tankhah.organization else 'نامشخص'}, نتیجه: {has_access_rule}"
    )

    if not has_access_rule:
        logger.warning(
            f"[can_edit_approval] کاربر {user.username} بر اساس AccessRule، دسترسی تأیید برای مرحله {current_stage.name} ندارد."
        )
        return False


    # فرض می‌کنیم Factor دارای فیلد `last_action_by_post_level` است که سطح کاربری که آخرین اقدام را انجام داده را نگه می‌دارد.
    # این فیلد باید هر بار که یک ApprovalLog ثبت می‌شود، به‌روز شود.
    if factor.status in ['APPROVED', 'REJECTED', 'PARTIAL']:
        # بررسی می‌کنیم آیا لاگی از یک سطح بالاتر وجود دارد که این فاکتور را به این وضعیت رسانده باشد.
        # این نیاز دارد که ApprovalLog فیلدی برای `post_level` کاربر داشته باشد.
        latest_log_for_factor = ApprovalLog.objects.filter(
            factor=factor
        ).order_by('-timestamp').first()

        if latest_log_for_factor and latest_log_for_factor.post_level is not None:
            if user_post_obj.post_level < latest_log_for_factor.post_level:
                # اگر کاربر فعلی در پستی پایین‌تر از آخرین کسی که اقدام کرده است،
                # و فاکتور در وضعیت نهایی (تأیید/رد) باشد، اجازه تغییر ندارد.
                return False

    # === 4. بررسی وضعیت قفل/آرشیو ===
    # این بخش اطمینان حاصل می‌کند که فاکتور یا تنخواه مربوطه قفل یا آرشیو نشده باشند،
    # زیرا عملیات تأیید روی موارد قفل شده یا آرشیو شده مجاز نیست.
    if tankhah.is_locked or tankhah.is_archived:
        logger.warning(
            f"[can_edit_approval] تنخواه {tankhah.number} قفل شده (is_locked={tankhah.is_locked}) یا "
            f"آرشیو شده (is_archived={tankhah.is_archived})."
        )
        return False
    if factor and (factor.is_locked or factor.is_archived):
        logger.warning(
            f"[can_edit_approval] فاکتور {factor.number} قفل شده (is_locked={factor.is_locked}) یا "
            f"آرشیو شده (is_archived={factor.is_archived})."
        )
        return False

    # === 5. بررسی اقدامات قبلی در مراحل بالاتر ===
    # این سناریو از این جلوگیری می‌کند که کاربر در مرحله‌ای پایین‌تر، فاکتوری را تأیید کند
    # که قبلاً در مراحل بالاتر توسط شخص دیگری بررسی (تأیید یا رد) شده و به مرحله بالاتر "دیده‌شده" باشد.
    if current_stage.order > 1:  # این بررسی فقط برای مراحلی پس از مرحله اول معنی‌دار است.
        query_filter = Q(factor=factor) if factor else Q(tankhah=tankhah, factor__isnull=True)
        has_higher_action = ApprovalLog.objects.filter(
            query_filter,
            stage__order__lt=current_stage.order,  # اقدامات در مراحل با ترتیب کمتر (یعنی بالاتر در گردش کار)
            action__in=['APPROVE', 'REJECT'],
            seen_by_higher=True  # این فرض بر این است که یک فیلد 'seen_by_higher' در مدل ApprovalLog وجود دارد
        ).exists()
        if has_higher_action:
            logger.warning(
                f"[can_edit_approval] اقدامات قبلی در مراحل بالاتر (ترتیب کمتر از {current_stage.order}) برای "
                f"فاکتور {factor.number if factor else 'نامشخص'} یافت شد. دسترسی رد شد."
            )
            return False

    # === 6. بررسی اقدامات قبلی کاربر در مرحله فعلی ===
    # این سناریو از این جلوگیری می‌کند که یک کاربر بیش از یک بار در همان مرحله،
    # یک فاکتور را تأیید یا رد کند (جلوگیری از تأیید/رد چندباره توسط یک نفر).
    query_filter = Q(factor=factor) if factor else Q(tankhah=tankhah, factor__isnull=True)
    has_previous_action_by_user_in_current_stage = ApprovalLog.objects.filter(
        query_filter,
        user=user,
        stage=current_stage,
        action__in=['APPROVE', 'REJECT', 'STATUS_CHANGE']
    ).exists()
    if has_previous_action_by_user_in_current_stage:
        logger.warning(
            f"[can_edit_approval] کاربر {user.username} قبلاً در مرحله {current_stage.name} برای "
            f"فاکتور {factor.number if factor else 'نامشخص'} اقدام کرده است. دسترسی رد شد."
        )
        return False

    # === همه بررسی‌ها با موفقیت انجام شد ===
    logger.info(
        f"[can_edit_approval] کاربر {user.username} مجاز به ویرایش در مرحله {current_stage.name} است. دسترسی اعطا شد.")
    return True

def can_edit_approval__(user, tankhah, current_stage, factor=None):
    logger.info(f"[can_edit_approval] بررسی دسترسی برای کاربر {user.username} در مرحله {current_stage.name} "
                f"(ترتیب: {current_stage.order}), تنخواه: {tankhah.number}, فاکتور: {factor.number if factor else 'نامشخص'}")

    if not user.is_authenticated:
        logger.warning("[can_edit_approval] کاربر احراز هویت نشده است")
        return False

    user_org_ids = set()
    user_posts_query = user.userpost_set.filter(is_active=True, end_date__isnull=True).select_related('post__organization')
    for user_post_entry in user_posts_query:
        org = user_post_entry.post.organization
        user_org_ids.add(org.id)
        current_org = org
        while current_org.parent_organization:
            current_org = current_org.parent_organization
            user_org_ids.add(current_org.id)

    is_hq_user = any(Organization.objects.filter(id=org_id, is_core=True).exists() for org_id in user_org_ids)
    if user.is_superuser or is_hq_user or user.has_perm('tankhah.Tankhah_view_all'):
        logger.info(f"[can_edit_approval] کاربر {user.username} (superuser/HQ/Tankhah_view_all) دسترسی کامل دارد")
        return True

    if user.has_perm('tankhah.factor_approve'):
        logger.info(f"[can_edit_approval] کاربر {user.username} دارای پرمیشن 'tankhah.factor_approve' است")
        return True

    user_post = user_posts_query.first()
    if not user_post:
        logger.warning(f"[can_edit_approval] کاربر {user.username} هیچ پست فعالی ندارد")
        return False

    base_conditions = Q(
        organization=tankhah.organization,
        stage=current_stage,
        action_type='APPROVE',
        entity_type='FACTOR',
        is_active=True
    )
    specific_post_condition = Q(post=user_post.post)
    generic_branch_level_condition = Q(
        post__isnull=True,
        branch=user_post.post.branch,
        min_level__lte=user_post.post.level
    )
    has_access_rule = AccessRule.objects.filter(base_conditions & (specific_post_condition | generic_branch_level_condition)).exists()
    if not has_access_rule:
        logger.warning(f"[can_edit_approval] کاربر {user.username} بر اساس AccessRule دسترسی ندارد")
        return False

    if tankhah.is_locked or tankhah.is_archived:
        logger.warning(f"[can_edit_approval] تنخواه {tankhah.number} قفل یا آرشیو شده است")
        return False
    if factor and (factor.is_locked or factor.is_archived):
        logger.warning(f"[can_edit_approval] فاکتور {factor.number} قفل یا آرشیو شده است")
        return False

    # بررسی اقدامات قبلی در مراحل بالاتر فقط برای فاکتور خاص
    if factor:
        has_higher_action = ApprovalLog.objects.filter(
            factor=factor,
            stage__order__lt=current_stage.order,
            action__in=['APPROVED', 'REJECTED']
        ).exists()
    else:
        has_higher_action = ApprovalLog.objects.filter(
            tankhah=tankhah,
            factor__isnull=True,
            stage__order__lt=current_stage.order,
            action__in=['APPROVED', 'REJECTED']
        ).exists()
    if has_higher_action:
        logger.warning(f"[can_edit_approval] اقدامات قبلی در مراحل بالاتر برای فاکتور {factor.number if factor else 'نامشخص'} یافت شد")
        return False

    # بررسی اقدامات قبلی کاربر فقط برای فاکتور خاص
    if factor:
        has_previous_action = ApprovalLog.objects.filter(
            factor=factor,
            user=user,
            stage=current_stage,
            action__in=['APPROVED', 'REJECTED', 'STAGE_CHANGE']
        ).exists()
    else:
        has_previous_action = ApprovalLog.objects.filter(
            tankhah=tankhah,
            factor__isnull=True,
            user=user,
            stage=current_stage,
            action__in=['APPROVED', 'REJECTED', 'STAGE_CHANGE']
        ).exists()
    if has_previous_action:
        logger.warning(f"[can_edit_approval] کاربر {user.username} قبلاً در مرحله {current_stage.name} اقدام کرده است")
        return False

    logger.info(f"[can_edit_approval] کاربر {user.username} مجاز به ویرایش در مرحله {current_stage.name} است")
    return True


def can_edit_approval(user, tankhah, current_stage, factor=None):
    logger.info(f"[can_edit_approval] بررسی دسترسی برای کاربر {user.username} در مرحله {current_stage.stage} "
                f"(ترتیب: {current_stage.stage_order}), تنخواه: {tankhah.number}, فاکتور: {factor.number if factor else 'نامشخص'}")

    if not user.is_authenticated:
        logger.warning("[can_edit_approval] کاربر احراز هویت نشده است")
        return False

    user_org_ids = set()
    user_posts_query = user.userpost_set.filter(is_active=True, end_date__isnull=True).select_related('post__organization')
    for user_post_entry in user_posts_query:
        org = user_post_entry.post.organization
        user_org_ids.add(org.id)
        current_org = org
        while current_org.parent_organization:
            current_org = current_org.parent_organization
            user_org_ids.add(current_org.id)

    is_hq_user = any(Organization.objects.filter(id=org_id, is_core=True).exists() for org_id in user_org_ids)
    if user.is_superuser or is_hq_user or user.has_perm('tankhah.Tankhah_view_all'):
        logger.info(f"[can_edit_approval] کاربر {user.username} (superuser/HQ/Tankhah_view_all) دسترسی کامل دارد")
        return True

    if user.has_perm('tankhah.factor_approve'):
        logger.info(f"[can_edit_approval] کاربر {user.username} دارای پرمیشن 'tankhah.factor_approve' است")
        return True

    user_post = user_posts_query.first()
    if not user_post:
        logger.warning(f"[can_edit_approval] کاربر {user.username} هیچ پست فعالی ندارد")
        return False

    base_conditions = Q(
        organization=tankhah.organization,
        stage=current_stage.stage,
        stage_order=current_stage.stage_order,
        action_type='APPROVE',
        entity_type='FACTOR',
        is_active=True
    )
    specific_post_condition = Q(post=user_post.post)
    generic_branch_level_condition = Q(
        post__isnull=True,
        branch=user_post.post.branch,
        min_level__lte=user_post.post.level
    )
    has_access_rule = AccessRule.objects.filter(base_conditions & (specific_post_condition | generic_branch_level_condition)).exists()
    if not has_access_rule:
        logger.warning(f"[can_edit_approval] کاربر {user.username} بر اساس AccessRule دسترسی ندارد")
        return False

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
            action__in=['APPROVED', 'REJECTED']
        ).exists()
    else:
        has_higher_action = ApprovalLog.objects.filter(
            tankhah=tankhah,
            factor__isnull=True,
            stage_order__lt=current_stage.stage_order,
            action__in=['APPROVED', 'REJECTED']
        ).exists()
    if has_higher_action:
        logger.warning(f"[can_edit_approval] اقدامات قبلی در مراحل بالاتر برای فاکتور {factor.number if factor else 'نامشخص'} یافت شد")
        return False

    # بررسی اقدامات قبلی کاربر
    if factor:
        has_previous_action = ApprovalLog.objects.filter(
            factor=factor,
            user=user,
            stage=current_stage.stage,
            stage_order=current_stage.stage_order,
            action__in=['APPROVED', 'REJECTED', 'STAGE_CHANGE']
        ).exists()
    else:
        has_previous_action = ApprovalLog.objects.filter(
            tankhah=tankhah,
            factor__isnull=True,
            user=user,
            stage=current_stage.stage,
            stage_order=current_stage.stage_order,
            action__in=['APPROVED', 'REJECTED', 'STAGE_CHANGE']
        ).exists()
    if has_previous_action:
        logger.warning(f"[can_edit_approval] کاربر {user.username} قبلاً در مرحله {current_stage.stage} اقدام کرده است")
        return False

    logger.info(f"[can_edit_approval] کاربر {user.username} مجاز به ویرایش در مرحله {current_stage.stage} است")
    return True