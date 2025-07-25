from django.contrib.auth import get_user_model
from django.db.models import Q, Max
from core.models import AccessRule, Organization, Post
import logging

logger = logging.getLogger('Log_check_user_factor_access')
User = get_user_model()

def check_user_factor_access(username, tankhah=None, action_type='EDIT', entity_type='FACTOR', default_stage_order=1):
    """
    بررسی دسترسی کاربر برای انجام عملیاتی (مثل ایجاد فاکتور) بر اساس پست سازمانی و AccessRule.

    :param username: نام کاربری
    :param tankhah: شیء تنخواه (اختیاری، برای محدود کردن به سازمان/پروژه تنخواه)
    :param action_type: نوع عملیات (مثل EDIT، DELETE)
    :param entity_type: نوع موجودیت (مثل FACTOR)
    :param default_stage_order: مرحله پیش‌فرض برای فاکتورها (پیش‌فرض: 1)
    :return: dict شامل اطلاعات دسترسی (has_access, allowed_stages, user_posts, user_orgs, max_post_level)
    """
    try:
        user = User.objects.get(username=username)
        if not user.is_authenticated:
            logger.warning(f"کاربر {username} احراز هویت نشده است.")
            return {
                'has_access': False,
                'allowed_stages': [],
                'user_posts': [],
                'user_orgs': [],
                'max_post_level': 1,
                'error': 'کاربر احراز هویت نشده است.'
            }

        # بررسی دسترسی کامل (superuser یا HQ یا Tankhah_view_all)
        is_hq_user = any(
            Organization.objects.filter(id=up.post.organization.id, is_core=True).exists()
            for up in user.userpost_set.filter(is_active=True, end_date__isnull=True)
        )
        if user.is_superuser or is_hq_user or user.has_perm('tankhah.Tankhah_view_all'):
            logger.info(f"کاربر {username} دسترسی کامل دارد.")
            return {
                'has_access': True,
                'allowed_stages': None,  # دسترسی به همه مراحل
                'user_posts': [up.post.id for up in user.userpost_set.filter(is_active=True, end_date__isnull=True)],
                'user_orgs': [up.post.organization.id for up in
                              user.userpost_set.filter(is_active=True, end_date__isnull=True)],
                'max_post_level': None,  # بدون محدودیت سطح
                'error': None
            }

        # دریافت پست‌های فعال کاربر
        user_posts = user.userpost_set.filter(is_active=True, end_date__isnull=True).select_related('post')
        user_post_ids = [up.post.id for up in user_posts]
        user_orgs = [up.post.organization.id for up in user_posts]
        max_post_level = user_posts.aggregate(max_level=Max('post__level'))['max_level'] or 1

        logger.debug(
            f"کاربر {username} - پست‌ها: {user_post_ids}, سازمان‌ها: {user_orgs}, حداکثر سطح: {max_post_level}")

        # بررسی قوانین دسترسی برای فاکتورها
        access_rules = AccessRule.objects.filter(
            post__id__in=user_post_ids,
            organization__id__in=user_orgs,
            action_type=action_type,
            entity_type=entity_type,
            is_active=True,
            min_level__lte=max_post_level
        )

        # اگر تنخواه مشخص شده، محدود کردن به سازمان/پروژه تنخواه
        if tankhah:
            access_rules = access_rules.filter(
                Q(organization=tankhah.organization) |
                Q(organization__in=tankhah.project.organizations.all() if tankhah.project else []) |
                Q(organization__in=tankhah.subproject.project.organizations.all() if tankhah.subproject else [])
            )

        allowed_stages = list(access_rules.values_list('stage_order', flat=True).distinct())
        has_access = access_rules.filter(stage_order=default_stage_order).exists()

        logger.debug(
            f"دسترسی کاربر {username} به فاکتور در مرحله {default_stage_order}: {has_access}, مراحل مجاز: {allowed_stages}")

        return {
            'has_access': has_access,
            'allowed_stages': allowed_stages,
            'user_posts': user_post_ids,
            'user_orgs': user_orgs,
            'max_post_level': max_post_level,
            'error': None
        }

    except User.DoesNotExist:
        logger.error(f"کاربر {username} یافت نشد.")
        return {
            'has_access': False,
            'allowed_stages': [],
            'user_posts': [],
            'user_orgs': [],
            'max_post_level': 1,
            'error': 'کاربر یافت نشد.'
        }
    except Exception as e:
        logger.error(f"خطا در بررسی دسترسی کاربر {username}: {str(e)}")
        return {
            'has_access': False,
            'allowed_stages': [],
            'user_posts': [],
            'user_orgs': [],
            'max_post_level': 1,
            'error': f'خطای غیرمنتظره: {str(e)}'
        }
'''
ورودی‌ها: نام کاربری، شیء تنخواه (اختیاری)، نوع عملیات (پیش‌فرض EDIT)، و نوع موجودیت (پیش‌فرض FACTOR).
خروجی: دیکشنری شامل:has_access: آیا کاربر دسترسی دارد یا خیر.
allowed_stages: لیست مراحل مجاز (بر اساس stage_order در AccessRule).
user_posts: لیست آیدی پست‌های فعال کاربر.
user_orgs: لیست آیدی سازمان‌های مرتبط.
max_post_level: حداکثر سطح پست کاربر.
error: پیام خطا (در صورت وجود).

منطق:ابتدا بررسی می‌کند که کاربر احراز هویت شده باشد.
اگر کاربر superuser، کاربر HQ، یا دارای مجوز Tankhah_view_all باشد، دسترسی کامل می‌گیرد.
در غیر این صورت، پست‌های فعال و سازمان‌های کاربر را استخراج می‌کند.
قوانین دسترسی (AccessRule) را بر اساس پست‌ها، سازمان‌ها، و سطح پست بررسی می‌کند.
اگر تنخواه مشخص شده باشد، دسترسی را برای مرحله فعلی تنخواه (current_stage.order) بررسی می‌کند.

مدیریت خطا: خطاها (مثل کاربر ناموجود یا خطای دسترسی به current_stage) لاگ شده و خروجی مناسب برگردانده می‌شود.
'''