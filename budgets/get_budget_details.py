from django.db.models import Sum, Q
from datetime import datetime
from decimal import Decimal
from budgets.models import BudgetAllocation, BudgetTransaction
from core.models import  Project
from django.utils.translation import gettext_lazy as _

from budgets.models import BudgetAllocation, BudgetTransaction
from core.models import Project, Organization
from django.utils.translation import gettext_lazy as _
import logging
logger = logging.getLogger("get_budget_details")


# def get_budget_details(entity, filters=None):
#     """
#     محاسبه جزئیات بودجه برای یک موجودیت (مثل سازمان)
#     entity: می‌تواند یک Organization یا Project باشد
#     filters: دیکشنری شامل فیلترهای تاریخ (date_from, date_to)
#     """
#     filters = filters or {}
#     date_from = filters.get('date_from')
#     date_to = filters.get('date_to')
#
#     # کش کردن نتیجه
#     # cache_key = f"budget_details_{entity.__class__.__name__}_{entity.id}"
#     # cached_data = cache.get(cache_key)
#     # if cached_data:
#     #     logger.debug(f"Cache hit for {cache_key}: {cached_data}")
#     #     return cached_data
#
#     try:
#         # تبدیل تاریخ‌های جلالی به میلادی
#         date_filter = Q()
#         if date_from:
#             try:
#                 from Tanbakhsystem.utils import parse_jalali_date
#                 date_from = parse_jalali_date(date_from, field_name=_('از تاریخ'))
#                 date_filter &= Q(allocation_date__gte=date_from)
#             except ValueError as e:
#                 logger.warning(f"Invalid date_from: {date_from}, error: {str(e)}")
#         if date_to:
#             try:
#                 from Tanbakhsystem.utils import parse_jalali_date
#                 date_to = parse_jalali_date(date_to, field_name=_('تا تاریخ'))
#                 date_filter &= Q(allocation_date__lte=date_to)
#             except ValueError as e:
#                 logger.warning(f"Invalid date_to: {date_to}, error: {str(e)}")
#
#         # فیلتر تخصیص‌های بودجه
#         budget_allocations = BudgetAllocation.objects.filter(
#             organization=entity,
#             is_active=True
#         ).filter(date_filter)
#
#         # محاسبه بودجه کل
#         total_budget = budget_allocations.aggregate(
#             total=Sum('allocated_amount')
#         )['total'] or Decimal('0')
#
#         # محاسبه تخصیص‌یافته
#         total_allocated = BudgetAllocation.objects.filter(
#             budget_allocation__in=budget_allocations
#         ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
#
#         # محاسبه تراکنش‌های مصرف و بازگشت
#         consumed = BudgetTransaction.objects.filter(
#             allocation__in=budget_allocations,
#             transaction_type='CONSUMPTION'
#         ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#         returned = BudgetTransaction.objects.filter(
#             allocation__in=budget_allocations,
#             transaction_type='RETURN'
#         ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#
#         # محاسبه مانده بودجه
#         remaining_budget = total_budget - consumed + returned
#
#         # تعداد پروژه‌ها
#         project_count = Project.objects.filter(
#             organizations=entity,
#             is_active=True
#         ).count()
#
#         # تعداد تخصیص‌ها
#         allocation_count = budget_allocations.count()
#
#         # آخرین به‌روزرسانی
#         last_update = BudgetTransaction.objects.filter(
#             allocation__in=budget_allocations
#         ).order_by('-timestamp').first()  # استفاده از timestamp به جای created_at
#         last_update_date = last_update.timestamp if last_update else None
#         if last_update_date and isinstance(last_update_date, datetime):
#             from django_jalali.templatetags.jformat import to_jalali
#             last_update_date = to_jalali(last_update_date)
#
#         # وضعیت
#         status_message = _('فعال') if entity.is_active else _('غیرفعال')
#
#         result = {
#             'total_budget': total_budget,
#             'total_allocated': total_allocated,
#             'remaining_budget': remaining_budget,
#             'project_count': project_count,
#             'allocation_count': allocation_count,
#             'last_update': last_update_date,
#             'status_message': status_message
#         }
#
#         # ذخیره در کش
#         # cache.set(cache_key, result, timeout=60*60)  # کش برای 1 ساعت
#         # logger.debug(f"Computed budget details for {cache_key}: {result}")
#         return result
#
#     except Exception as e:
#         logger.error(f"Error in get_budget_details for organization {entity}: {str(e)}")
#         return {
#             'total_budget': Decimal('0'),
#             'total_allocated': Decimal('0'),
#             'remaining_budget': Decimal('0'),
#             'project_count': 0,
#             'allocation_count': 0,
#             'last_update': None,
#             'status_message': _('نامشخص')
#         }


def get_budget_details(entity, filters=None):
    """
    محاسبه جزئیات بودجه برای یک موجودیت (مثل سازمان یا پروژه)
    entity: می‌تواند یک Organization یا Project باشد
    filters: دیکشنری شامل فیلترهای تاریخ (date_from, date_to)
    """
    filters = filters or {}
    date_from = filters.get('date_from')
    date_to = filters.get('date_to')

    try:
        # تبدیل تاریخ‌های جلالی به میلادی
        date_filter = Q()
        if date_from:
            try:
                from Tanbakhsystem.utils import parse_jalali_date
                date_from = parse_jalali_date(date_from, field_name=_('از تاریخ'))
                date_filter &= Q(allocation_date__gte=date_from)
            except ValueError as e:
                logger.warning(f"Invalid date_from: {date_from}, error: {str(e)}")
        if date_to:
            try:
                from Tanbakhsystem.utils import parse_jalali_date
                date_to = parse_jalali_date(date_to, field_name=_('تا تاریخ'))
                date_filter &= Q(allocation_date__lte=date_to)
            except ValueError as e:
                logger.warning(f"Invalid date_to: {date_to}, error: {str(e)}")

        # تعیین فیلتر تخصیص‌ها بر اساس نوع موجودیت
        allocation_filter = Q(is_active=True)
        if isinstance(entity, Organization):
            allocation_filter &= Q(organization=entity)
        elif isinstance(entity, Project):
            allocation_filter &= Q(project=entity)
        else:
            raise ValueError(f"Entity must be Organization or Project, got {type(entity)}")

        # فیلتر تخصیص‌های بودجه
        budget_allocations = BudgetAllocation.objects.filter(allocation_filter).filter(date_filter)

        # محاسبه بودجه کل
        total_budget = budget_allocations.aggregate(
            total=Sum('allocated_amount')
        )['total'] or Decimal('0')

        # محاسبه تخصیص‌یافته (برای تخصیص‌های زیرمجموعه)
        total_allocated = budget_allocations.aggregate(
            total=Sum('allocated_amount')
        )['total'] or Decimal('0')

        # محاسبه تراکنش‌های مصرف و بازگشت
        consumed = BudgetTransaction.objects.filter(
            allocation__in=budget_allocations,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        returned = BudgetTransaction.objects.filter(
            allocation__in=budget_allocations,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # محاسبه مانده بودجه
        remaining_budget = total_budget - consumed + returned

        # تعداد پروژه‌ها
        project_count = 0
        if isinstance(entity, Organization):
            project_count = Project.objects.filter(
                organizations=entity,
                is_active=True
            ).count()
        elif isinstance(entity, Project):
            project_count = 1  # خود پروژه

        # تعداد تخصیص‌ها
        allocation_count = budget_allocations.count()

        # آخرین به‌روزرسانی
        last_update = BudgetTransaction.objects.filter(
            allocation__in=budget_allocations
        ).order_by('-timestamp').first()
        last_update_date = last_update.timestamp if last_update else None
        if last_update_date and isinstance(last_update_date, datetime):
            from django_jalali.templatetags.jformat import to_jalali
            last_update_date = to_jalali(last_update_date)

        # وضعیت
        status_message = _('فعال') if entity.is_active else _('غیرفعال')

        result = {
            'total_budget': total_budget,
            'total_allocated': total_allocated,
            'remaining_budget': remaining_budget,
            'project_count': project_count,
            'allocation_count': allocation_count,
            'last_update': last_update_date,
            'status_message': status_message
        }

        # ذخیره در کش (فعلاً غیرفعال)
        # cache_key = f"budget_details_{entity.__class__.__name__}_{entity.id}"
        # cache.set(cache_key, result, timeout=60*60)
        # logger.debug(f"Computed budget details for {cache_key}: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in get_budget_details for entity {entity}: {str(e)}")
        return {
            'total_budget': Decimal('0'),
            'total_allocated': Decimal('0'),
            'remaining_budget': Decimal('0'),
            'project_count': 0,
            'allocation_count': 0,
            'last_update': None,
            'status_message': _('نامشخص')
        }