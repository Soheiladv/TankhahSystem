# budgets/budget_calculations.py

#---
"""
calculate_total_allocated:
مجموع بودجه تخصیص‌یافته را برای یک سازمان، پروژه یا کل سیستم محاسبه می‌کند.
فیلترهای اختیاری (مثل تاریخ) را اعمال می‌کند.
calculate_remaining_budget:
مانده بودجه را برای یک BudgetPeriod، سازمان، پروژه یا کل سیستم محاسبه می‌کند.
از remaining_amount تخصیص‌ها یا تفاوت بودجه کل و تخصیص‌شده استفاده می‌کند.
get_budget_status:
وضعیت بودجه (فعال، غیرفعال، قفل‌شده) را بررسی می‌کند و پیام مرتبط را برمی‌گرداند.
_apply_filters:
تابع کمکی برای اعمال فیلترها (تاریخ، وضعیت فعال و غیره) روی queryset.
get_budget_details:
همه اطلاعات بودجه (کل، تخصیص‌یافته، مانده، وضعیت) را در یک دیکشنری جمع‌آوری می‌کند.
"""
from budgets.models import BudgetAllocation
from core.models import Organization, Project
from django.db.models import Sum, Q
from .models import BudgetPeriod, BudgetAllocation
from core.models import Organization, Project
from decimal import Decimal
import logging
logger = logging.getLogger(__name__)

#---
"""    محاسبه مجموع بودجه تخصیص‌یافته برای یک موجودیت (سازمان، پروژه، یا همه)."""
def __calculate_total_allocated(entity=None, filters=None):
    """
    محاسبه مجموع بودجه تخصیص‌یافته برای یک موجودیت (سازمان، پروژه، یا همه).

    :param entity: می‌تواند Organization، Project یا None (برای کل سیستم) باشد
    :param filters: دیکشنری فیلترها (مثل تاریخ، وضعیت)
    :return: مقدار مجموع تخصیص‌ها (Decimal)
    """
    queryset = BudgetAllocation.objects.all()

    if entity:
        if isinstance(entity, Organization):
            queryset = queryset.filter(organization=entity)
        elif isinstance(entity, Project):
            queryset = queryset.filter(id__in=entity.allocations.values('id'))

    if filters:
        queryset = _apply_filters(queryset, filters)

    total = queryset.aggregate(total=Sum('allocated_amount'))['total'] or 0
    return total

def __calculate_remaining_budget(entity=None, filters=None):
    """
    محاسبه مانده بودجه برای یک موجودیت.

    :param entity: می‌تواند BudgetPeriod، Organization، Project یا None باشد
    :param filters: دیکشنری فیلترها
    :return: مقدار مانده بودجه (Decimal)
    """
    if isinstance(entity, BudgetPeriod):
        total_allocated = calculate_total_allocated(filters={'budget_period': entity})
        return entity.total_amount - total_allocated

    elif isinstance(entity, Organization):
        total_allocated = calculate_total_allocated(entity=entity, filters=filters)
        total_remaining = BudgetAllocation.objects.filter(organization=entity).aggregate(
            total=Sum('remaining_amount')
        )['total'] or 0
        return total_remaining

    elif isinstance(entity, Project):
        total_allocated = calculate_total_allocated(entity=entity, filters=filters)
        total_remaining = entity.allocations.aggregate(
            total=Sum('remaining_amount')
        )['total'] or 0
        return total_remaining

    # برای کل سیستم
    total_budget = BudgetPeriod.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_allocated = calculate_total_allocated(filters=filters)
    return total_budget - total_allocated

def __get_budget_status(entity, filters=None):
    """
    بررسی وضعیت بودجه (فعال، غیرفعال، قفل‌شده و غیره).

    :param entity: BudgetPeriod یا Organization یا Project
    :param filters: دیکشنری فیلترها
    :return: دیکشنری شامل وضعیت و پیام
    """
    if isinstance(entity, BudgetPeriod):
        status, message = entity.check_budget_status()
        return {'status': status, 'message': message}

    elif isinstance(entity, Organization):
        allocations = BudgetAllocation.objects.filter(organization=entity)
        if filters:
            allocations = _apply_filters(allocations, filters)
        if not allocations.exists():
            return {'status': 'no_budget', 'message': 'هیچ بودجه‌ای تخصیص نیافته است.'}
        active_count = allocations.filter(budget_period__is_active=True).count()
        return {
            'status': 'active' if active_count > 0 else 'inactive',
            'message': f"{active_count} تخصیص فعال از {allocations.count()} کل"
        }

    elif isinstance(entity, Project):
        if not entity.allocations.exists():
            return {'status': 'no_budget', 'message': 'هیچ بودجه‌ای تخصیص نیافته است.'}
        active_count = entity.allocations.filter(budget_period__is_active=True).count()
        return {
            'status': 'active' if active_count > 0 else 'inactive',
            'message': f"{active_count} تخصیص فعال از {entity.allocations.count()} کل"
        }

    return {'status': 'unknown', 'message': 'وضعیت نامشخص'}

def ___apply_filters(queryset, filters):
    """
    اعمال فیلترهای مختلف روی queryset.

    :param queryset: QuerySet اولیه
    :param filters: دیکشنری شامل فیلترها (مثل date_from، date_to، is_active)
    :return: QuerySet فیلترشده
    """
    if not filters:
        return queryset

    if 'date_from' in filters:
        queryset = queryset.filter(allocation_date__gte=filters['date_from'])
    if 'date_to' in filters:
        queryset = queryset.filter(allocation_date__lte=filters['date_to'])
    if 'is_active' in filters:
        queryset = queryset.filter(budget_period__is_active=filters['is_active'])
    if 'budget_period' in filters:
        queryset = queryset.filter(budget_period=filters['budget_period'])

    return queryset

def __get_budget_details(entity=None, filters=None):
    """
    دریافت جزئیات بودجه برای یک موجودیت یا کل سیستم.

    :param entity: Organization، Project، BudgetPeriod یا None
    :param filters: دیکشنری فیلترها
    :return: دیکشنری شامل تمام اطلاعات بودجه
    """
    if isinstance(entity, BudgetPeriod):
        total_budget = entity.total_amount
        total_allocated = calculate_total_allocated(filters={'budget_period': entity})
        remaining = entity.get_remaining_amount()

    elif isinstance(entity, Organization):
        total_budget = BudgetPeriod.objects.filter(
            allocations__organization=entity
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        total_allocated = calculate_total_allocated(entity=entity, filters=filters)
        remaining = calculate_remaining_budget(entity=entity, filters=filters)

    elif isinstance(entity, Project):
        total_budget = entity.allocations.aggregate(
            total=Sum('budget_period__total_amount')
        )['total'] or 0
        total_allocated = calculate_total_allocated(entity=entity, filters=filters)
        remaining = calculate_remaining_budget(entity=entity, filters=filters)

    else:  # کل سیستم
        total_budget = BudgetPeriod.objects.aggregate(total=Sum('total_amount'))['total'] or 0
        total_allocated = calculate_total_allocated(filters=filters)
        remaining = calculate_remaining_budget(filters=filters)

    status = get_budget_status(entity, filters)
    return {
        'total_budget': total_budget,
        'total_allocated': total_allocated,
        'remaining_budget': remaining,
        'status': status['status'],
        'status_message': status['message']
    }


def test_get_budget_status(self):
    status = get_budget_status(self.budget_period)
    self.assertEqual(status['status'], "normal")


def calculate_total_allocated(entity=None, filters=None):
    """محاسبه مجموع بودجه تخصیص‌یافته"""
    queryset = BudgetAllocation.objects.all()
    if entity:
        if isinstance(entity, Organization):
            queryset = queryset.filter(organization=entity)
        elif isinstance(entity, Project):
            queryset = queryset.filter(id__in=entity.allocations.values('id'))
    if filters:
        queryset = _apply_filters(queryset, filters)
    total = queryset.aggregate(total=Sum('allocated_amount'))['total'] or 0
    logger.info(f"calculate_total_allocated: entity={entity}, filters={filters}, total={total}")
    return total


def calculate_remaining_budget(entity=None, filters=None):
    """محاسبه مانده بودجه"""
    if isinstance(entity, BudgetPeriod):
        total_allocated = calculate_total_allocated(filters={'budget_period': entity})
        remaining = entity.total_amount - total_allocated
    elif isinstance(entity, Organization):
        total_remaining = BudgetAllocation.objects.filter(organization=entity).aggregate(
            total=Sum('remaining_amount')
        )['total'] or 0
        remaining = total_remaining
    elif isinstance(entity, Project):
        total_remaining = entity.allocations.aggregate(
            total=Sum('remaining_amount')
        )['total'] or 0
        remaining = total_remaining
    else:
        total_budget = BudgetPeriod.objects.aggregate(total=Sum('total_amount'))['total'] or 0
        total_allocated = calculate_total_allocated(filters=filters)
        remaining = total_budget - total_allocated
    logger.info(f"calculate_remaining_budget: entity={entity}, filters={filters}, remaining={remaining}")
    return remaining


def get_budget_status(entity, filters=None):
    """بررسی وضعیت بودجه"""
    if isinstance(entity, BudgetPeriod):
        status, message = entity.check_budget_status()
    elif isinstance(entity, Organization):
        allocations = BudgetAllocation.objects.filter(organization=entity)
        if filters:
            allocations = _apply_filters(allocations, filters)
        if not allocations.exists():
            status, message = 'no_budget', 'هیچ بودجه‌ای تخصیص نیافته است.'
        else:
            active_count = allocations.filter(budget_period__is_active=True).count()
            status = 'active' if active_count > 0 else 'inactive'
            message = f"{active_count} تخصیص فعال از {allocations.count()} کل"
    elif isinstance(entity, Project):
        if not entity.allocations.exists():
            status, message = 'no_budget', 'هیچ بودجه‌ای تخصیص نیافته است.'
        else:
            active_count = entity.allocations.filter(budget_period__is_active=True).count()
            status = 'active' if active_count > 0 else 'inactive'
            message = f"{active_count} تخصیص فعال از {entity.allocations.count()} کل"
    else:
        status, message = 'unknown', 'وضعیت نامشخص'
    logger.info(f"get_budget_status: entity={entity}, status={status}, message={message}")
    return {'status': status, 'message': message}


def _apply_filters(queryset, filters):
    """اعمال فیلترها روی queryset"""
    if 'date_from' in filters:
        queryset = queryset.filter(allocation_date__gte=filters['date_from'])
    if 'date_to' in filters:
        queryset = queryset.filter(allocation_date__lte=filters['date_to'])
    if 'is_active' in filters:
        queryset = queryset.filter(budget_period__is_active=filters['is_active'])
    if 'budget_period' in filters:
        queryset = queryset.filter(budget_period=filters['budget_period'])
    logger.debug(f"_apply_filters: filters={filters}, queryset count={queryset.count()}")
    return queryset


def get_budget_details(entity=None, filters=None):
    """دریافت جزئیات بودجه"""
    if isinstance(entity, BudgetPeriod):
        total_budget = entity.total_amount
        total_allocated = calculate_total_allocated(filters={'budget_period': entity})
        remaining = entity.get_remaining_amount()
    elif isinstance(entity, Organization):
        total_budget = BudgetPeriod.objects.filter(
            allocations__organization=entity
        ).distinct().aggregate(total=Sum('total_amount'))['total'] or 0
        total_allocated = calculate_total_allocated(entity=entity, filters=filters)
        remaining = calculate_remaining_budget(entity=entity, filters=filters)
    elif isinstance(entity, Project):
        total_budget = entity.allocations.aggregate(
            total=Sum('budget_period__total_amount')
        )['total'] or 0
        total_allocated = calculate_total_allocated(entity=entity, filters=filters)
        remaining = calculate_remaining_budget(entity=entity, filters=filters)
    else:  # کل سیستم
        total_budget = BudgetPeriod.objects.aggregate(total=Sum('total_amount'))['total'] or 0
        total_allocated = calculate_total_allocated(filters=filters)
        remaining = calculate_remaining_budget(filters=filters)

    status = get_budget_status(entity, filters)
    details = {
        'total_budget': total_budget,
        'total_allocated': total_allocated,
        'remaining_budget': remaining,
        'status': status['status'],
        'status_message': status['message']
    }
    logger.info(f"get_budget_details: entity={entity}, filters={filters}, details={details}")
    return details


def calculate_allocation_percentages(allocations):
    """محاسبه درصد تخصیص برای هر ردیف و جمع کل"""
    for allocation in allocations:
        allocation.percentage = (
            (allocation.allocated_amount / allocation.budget_period.total_amount * Decimal("100"))
            if allocation.budget_period.total_amount else Decimal("0")
        )
    total_percentage = sum(allocation.percentage for allocation in allocations) if allocations else Decimal("0")
    logger.info(
        f"calculate_allocation_percentages: total_percentage={total_percentage}, allocations_count={len(allocations)}")
    return total_percentage