from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
import logging
from budgets.models import BudgetPeriod, BudgetAllocation, BudgetTransaction, ProjectBudgetAllocation
from core.models import Organization, Project
from django_jalali.db.models import jDateField
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

def get_budget_details(entity, filters=None):
    """
    محاسبه جزئیات بودجه برای یک سازمان با در نظر گرفتن فیلترهای تاریخ
    """
    filters = filters or {}
    date_from = filters.get('date_from')
    date_to = filters.get('date_to')
    is_active = filters.get('is_active')

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

        # فیلتر تخصیص‌های بودجه
        budget_allocations = BudgetAllocation.objects.filter(
            organization=entity,
            is_active=True
        ).filter(date_filter)

        # محاسبه بودجه کل
        total_budget = budget_allocations.aggregate(
            total=Sum('allocated_amount')
        )['total'] or Decimal('0')

        # محاسبه تخصیص‌یافته
        total_allocated = ProjectBudgetAllocation.objects.filter(
            budget_allocation__in=budget_allocations
        ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')

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
        project_count = Project.objects.filter(
            organizations=entity,
            is_active=True
        ).count()

        # تعداد تخصیص‌ها
        allocation_count = budget_allocations.count()

        # آخرین به‌روزرسانی
        last_update = BudgetTransaction.objects.filter(
            allocation__in=budget_allocations
        ).order_by('-created_at').first()
        last_update_date = last_update.created_at if last_update else None
        if last_update_date and isinstance(last_update_date, datetime):
            from django_jalali.templatetags.jformat import to_jalali
            last_update_date = to_jalali(last_update_date)

        # وضعیت
        status_message = _('فعال') if entity.is_active else _('غیرفعال')

        return {
            'total_budget': total_budget,
            'total_allocated': total_allocated,
            'remaining_budget': remaining_budget,
            'project_count': project_count,
            'allocation_count': allocation_count,
            'last_update': last_update_date,
            'status_message': status_message
        }

    except Exception as e:
        logger.error(f"Error in get_budget_details for organization {entity}: {str(e)}")
        return {
            'total_budget': Decimal('0'),
            'total_allocated': Decimal('0'),
            'remaining_budget': Decimal('0'),
            'project_count': 0,
            'allocation_count': 0,
            'last_update': None,
            'status_message': _('نامشخص')
        }