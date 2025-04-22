# budget_calculations.py
import logging
from decimal import Decimal
from django.db.models import Sum, Q
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from Tanbakhsystem.utils import parse_jalali_date

logger = logging.getLogger(__name__)
"""
توضیحات فایل budget_calculations.py:
ساختار: توابع به دسته‌های سازمان، پروژه، زیرپروژه، تنخواه، و فاکتور تقسیم شده‌اند.
کش: استفاده از django.core.cache برای ذخیره نتایج محاسبات و بهبود عملکرد.
فیلترهای پویا: تابع apply_filters برای اعمال فیلترهای زمانی، دوره بودجه، و وضعیت.
مدیریت تراکنش‌ها: در نظر گرفتن تراکنش‌های CONSUMPTION و RETURN در محاسبات.
فاکتورها: توابع جدید برای محاسبه بودجه فاکتورها و آیتم‌های آن‌ها.
سازگاری: استفاده از مدل‌های موجود و ادغام توابع شما (مانند get_project_remaining_budget).
"""
# === توابع عمومی ===
def apply_filters(queryset, filters=None):
    """
    اعمال فیلترهای پویا روی کوئری‌ست
    """
    if not filters:
        return queryset
    if 'date_from' in filters:
        date_from = parse_jalali_date(filters['date_from']) if isinstance(filters['date_from'], str) else filters['date_from']
        queryset = queryset.filter(allocation_date__gte=date_from)
    if 'date_to' in filters:
        date_to = parse_jalali_date(filters['date_to']) if isinstance(filters['date_to'], str) else filters['date_to']
        queryset = queryset.filter(allocation_date__lte=date_to)
    if 'is_active' in filters:
        queryset = queryset.filter(is_active=filters['is_active'])
    if 'budget_period' in filters:
        queryset = queryset.filter(budget_period=filters['budget_period'])
    logger.debug(f"apply_filters: filters={filters}, queryset count={queryset.count()}")
    return queryset

# === توابع بودجه سازمان ===
def get_organization_total_budget(organization, filters=None):
    """
    محاسبه بودجه کل تخصیص‌یافته به سازمان بر اساس دوره‌های بودجه فعال
    """
    from budgets.models import BudgetPeriod
    queryset = BudgetPeriod.objects.filter(organization=organization, is_active=True, is_completed=False)
    if filters:
        queryset = apply_filters(queryset, filters)
    total_budget = queryset.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    logger.debug(f"get_organization_total_budget: organization={organization}, total={total_budget}")
    return total_budget

def get_organization_remaining_budget(organization, filters=None):
    """
    محاسبه بودجه باقی‌مانده سازمان
    """
    from budgets.models import BudgetAllocation
    total_budget = get_organization_total_budget(organization, filters)
    allocated = BudgetAllocation.objects.filter(organization=organization)
    if filters:
        allocated = apply_filters(allocated, filters)
    total_allocated = allocated.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
    remaining = max(total_budget - total_allocated, Decimal('0'))
    logger.debug(f"get_organization_remaining_budget: organization={organization}, remaining={remaining}")
    return remaining

def get_organization_budget(organization) -> Decimal:
    """محاسبه بودجه کل سازمان بر اساس دوره‌های بودجه فعال.
    """
    #     total = calculate_total_allocated(entity=organization)
    #     logger.debug(f"get_organization_budget: org={organization}, total={total}")
    #     return total

    # from core.models import Organization
    # from budgets.models import BudgetPeriod
    # def get_organization_budget(organization: core.models.Organization) -> Decimal:

    from budgets.models import BudgetPeriod

    total_budget = BudgetPeriod.objects.filter(organization=organization,is_active=True,is_completed=False).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    return total_budget

# === توابع بودجه پروژه ===
def get_project_total_budget(project, filters=None):
    """
    محاسبه بودجه کل تخصیص‌یافته به پروژه
    """
    from budgets.models import ProjectBudgetAllocation
    cache_key = f"project_total_budget_{project.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached project_total_budget for {cache_key}: {cached_result}")
        return cached_result

    queryset = ProjectBudgetAllocation.objects.filter(project=project, subproject__isnull=True)
    if filters:
        queryset = apply_filters(queryset, filters)
    total = queryset.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
    cache.set(cache_key, total, timeout=300)
    logger.debug(f"get_project_total_budget: project={project}, total={total}")
    return total

def get_project_used_budget(project, filters=None):
    """
    محاسبه بودجه مصرف‌شده پروژه (شامل تنخواه‌ها و زیرپروژه‌ها)
    """
    from budgets.models import BudgetTransaction
    cache_key = f"project_used_budget_{project.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached project_used_budget for {cache_key}: {cached_result}")
        return cached_result

    # مصرف از تنخواه‌های پرداخت‌شده
    tankhah_budget = project.tankhah_set.filter(status='PAID')
    if filters:
        tankhah_budget = apply_filters(tankhah_budget, filters)
    tankhah_budget = tankhah_budget.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # مصرف از زیرپروژه‌ها
    from budgets.models import ProjectBudgetAllocation
    subproject_budget = ProjectBudgetAllocation.objects.filter(project=project, subproject__isnull=False)
    if filters:
        subproject_budget = apply_filters(subproject_budget, filters)
    subproject_budget = subproject_budget.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')

    # مصرف‌های ثبت‌شده در تراکنش‌ها
    consumptions = BudgetTransaction.objects.filter(
        allocation__project_allocations__project=project,
        transaction_type='CONSUMPTION'
    )
    if filters:
        consumptions = apply_filters(consumptions, filters)
    consumptions = consumptions.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    total = tankhah_budget + subproject_budget + consumptions
    cache.set(cache_key, total, timeout=300)
    logger.debug(f"get_project_used_budget: project={project}, tankhah={tankhah_budget}, subproject={subproject_budget}, total={total}")
    return total

def get_project_remaining_budget(project, filters=None):
    """
    محاسبه بودجه باقی‌مانده پروژه با در نظر گرفتن تراکنش‌های مصرف و بازگشت
    """
    from budgets.models import BudgetTransaction
    cache_key = f"project_remaining_budget_{project.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached project_remaining_budget for {cache_key}: {cached_result}")
        return cached_result

    total_allocated = get_project_total_budget(project, filters)
    consumptions = BudgetTransaction.objects.filter(
        allocation__project_allocations__project=project,
        transaction_type='CONSUMPTION'
    )
    if filters:
        consumptions = apply_filters(consumptions, filters)
    consumptions = consumptions.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    returns = BudgetTransaction.objects.filter(
        allocation__project_allocations__project=project,
        transaction_type='RETURN'
    )
    if filters:
        returns = apply_filters(returns, filters)
    returns = returns.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    remaining = max(total_allocated - consumptions + returns, Decimal('0'))
    cache.set(cache_key, remaining, timeout=300)
    logger.debug(f"get_project_remaining_budget: project={project}, remaining={remaining}")
    return remaining

# === توابع بودجه زیرپروژه ===
def get_subproject_total_budget(subproject, filters=None):
    """
    محاسبه بودجه کل تخصیص‌یافته به زیرپروژه
    """
    from budgets.models import ProjectBudgetAllocation
    cache_key = f"subproject_total_budget_{subproject.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached subproject_total_budget for {cache_key}: {cached_result}")
        return cached_result

    queryset = ProjectBudgetAllocation.objects.filter(subproject=subproject)
    if filters:
        queryset = apply_filters(queryset, filters)
    total = queryset.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
    cache.set(cache_key, total, timeout=300)
    logger.debug(f"get_subproject_total_budget: subproject={subproject}, total={total}")
    return total

def get_subproject_used_budget(subproject, filters=None):
    """
    محاسبه بودجه مصرف‌شده زیرپروژه
    """
    cache_key = f"subproject_used_budget_{subproject.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached subproject_used_budget for {cache_key}: {cached_result}")
        return cached_result

    total = subproject.tankhah_set.filter(status='PAID')
    if filters:
        total = apply_filters(total, filters)
    total = total.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    cache.set(cache_key, total, timeout=300)
    logger.debug(f"get_subproject_used_budget: subproject={subproject}, total={total}")
    return total

def get_subproject_remaining_budget(subproject, filters=None):
    """
    محاسبه بودجه باقی‌مانده زیرپروژه با در نظر گرفتن تراکنش‌های مصرف و بازگشت
    """
    from budgets.models import BudgetTransaction
    cache_key = f"subproject_remaining_budget_{subproject.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached subproject_remaining_budget for {cache_key}: {cached_result}")
        return cached_result

    total_allocated = get_subproject_total_budget(subproject, filters)
    consumptions = BudgetTransaction.objects.filter(
        allocation__project_allocations__subproject=subproject,
        transaction_type='CONSUMPTION'
    )
    if filters:
        consumptions = apply_filters(consumptions, filters)
    consumptions = consumptions.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    returns = BudgetTransaction.objects.filter(
        allocation__project_allocations__subproject=subproject,
        transaction_type='RETURN'
    )
    if filters:
        returns = apply_filters(returns, filters)
    returns = returns.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    remaining = max(total_allocated - consumptions + returns, Decimal('0'))
    cache.set(cache_key, remaining, timeout=300)
    logger.debug(f"get_subproject_remaining_budget: subproject={subproject}, remaining={remaining}")
    return remaining

# === توابع بودجه تنخواه ===
def get_tankhah_total_budget(tankhah, filters=None):
    """
    محاسبه بودجه کل تخصیص‌یافته به تنخواه
    """
    total = tankhah.amount
    logger.debug(f"get_tankhah_total_budget: tankhah={tankhah.number}, total={total}")
    return total

def get_tankhah_used_budget(tankhah, filters=None):
    """
    محاسبه بودجه مصرف‌شده تنخواه (بر اساس فاکتورهای پرداخت‌شده)
    """
    from tankhah.models import Factor
    cache_key = f"tankhah_used_budget_{tankhah.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached tankhah_used_budget for {cache_key}: {cached_result}")
        return cached_result

    factors = Factor.objects.filter(tankhah=tankhah, status='PAID')
    if filters:
        factors = apply_filters(factors, filters)
    total = factors.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    cache.set(cache_key, total, timeout=300)
    logger.debug(f"get_tankhah_used_budget: tankhah={tankhah.number}, total={total}")
    return total

def get_tankhah_remaining_budget(tankhah, filters=None):
    """
    محاسبه بودجه باقی‌مانده تنخواه
    """
    cache_key = f"tankhah_remaining_budget_{tankhah.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached tankhah_remaining_budget for {cache_key}: {cached_result}")
        return cached_result

    total_budget = get_tankhah_total_budget(tankhah, filters)
    used_budget = get_tankhah_used_budget(tankhah, filters)
    remaining = max(total_budget - used_budget, Decimal('0'))
    cache.set(cache_key, remaining, timeout=300)
    logger.debug(f"get_tankhah_remaining_budget: tankhah={tankhah.number}, remaining={remaining}")
    return remaining

# === توابع بودجه فاکتور ===
def get_factor_total_budget(factor, filters=None):
    """
    محاسبه بودجه کل فاکتور (مجموع آیتم‌های فاکتور)
    """
    total = factor.total_amount()
    logger.debug(f"get_factor_total_budget: factor={factor.number}, total={total}")
    return total

def get_factor_used_budget(factor, filters=None):
    """
    محاسبه بودجه مصرف‌شده فاکتور (آیتم‌های تأییدشده یا پرداخت‌شده)
    """
    cache_key = f"factor_used_budget_{factor.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached factor_used_budget for {cache_key}: {cached_result}")
        return cached_result

    total = factor.items.filter(status__in=['APPROVED', 'PAID'])
    if filters:
        total = apply_filters(total, filters)
    total = total.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    cache.set(cache_key, total, timeout=300)
    logger.debug(f"get_factor_used_budget: factor={factor.number}, total={total}")
    return total

def get_factor_remaining_budget(factor, filters=None):
    """
    محاسبه بودجه باقی‌مانده فاکتور
    """
    cache_key = f"factor_remaining_budget_{factor.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached factor_remaining_budget for {cache_key}: {cached_result}")
        return cached_result

    total_budget = get_factor_total_budget(factor, filters)
    used_budget = get_factor_used_budget(factor, filters)
    remaining = max(total_budget - used_budget, Decimal('0'))
    cache.set(cache_key, remaining, timeout=300)
    logger.debug(f"get_factor_remaining_budget: factor={factor.number}, remaining={remaining}")
    return remaining

# === توابع وضعیت بودجه ===
def check_budget_status(obj, filters=None):
    """
    بررسی وضعیت بودجه برای دوره‌های بودجه
    """
    from budgets.models import BudgetPeriod
    if not isinstance(obj, BudgetPeriod):
        logger.warning(f"Invalid object type for check_budget_status: {type(obj)}")
        return 'unknown', _('وضعیت نامشخص')

    cache_key = f"budget_status_{obj.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached budget_status for {cache_key}: {cached_result}")
        return cached_result

    remaining = get_organization_remaining_budget(obj.organization, filters)
    locked = get_locked_amount(obj)
    warning = get_warning_amount(obj)

    if not obj.is_active:
        result = 'inactive', _('دوره غیرفعال است.')
    elif obj.is_completed:
        result = 'completed', _('بودجه تمام‌شده است.')
    elif remaining <= 0 and obj.lock_condition == 'ZERO_REMAINING':
        obj.is_completed = True
        obj.is_active = False
        obj.save()
        result = 'completed', _('بودجه به صفر رسیده و تمام‌شده است.')
    elif obj.lock_condition == 'AFTER_DATE' and obj.end_date < timezone.now().date():
        obj.is_active = False
        obj.save()
        result = 'locked', _('دوره به دلیل پایان تاریخ قفل شده است.')
    elif obj.lock_condition == 'MANUAL' and remaining <= locked:
        result = 'locked', _('بودجه به حد قفل‌شده رسیده است.')
    elif remaining <= warning:
        result = 'warning', _('بودجه به آستانه هشدار رسیده است.')
    else:
        result = 'normal', _('وضعیت عادی')

    cache.set(cache_key, result, timeout=300)
    logger.debug(f"check_budget_status: obj={obj}, result={result}")
    return result

def get_budget_status(entity, filters=None):
    """
    بررسی وضعیت بودجه برای موجودیت‌های مختلف (سازمان، پروژه، زیرپروژه)
    """
    from budgets.models import BudgetPeriod, BudgetAllocation, ProjectBudgetAllocation
    from core.models import Organization, Project, SubProject

    cache_key = f"budget_status_{type(entity).__name__}_{entity.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached budget_status for {cache_key}: {cached_result}")
        return cached_result

    if isinstance(entity, BudgetPeriod):
        status, message = check_budget_status(entity, filters)
    elif isinstance(entity, Organization):
        allocations = BudgetAllocation.objects.filter(organization=entity)
        if filters:
            allocations = apply_filters(allocations, filters)
        if not allocations.exists():
            status, message = 'no_budget', _('هیچ بودجه‌ای تخصیص نیافته است.')
        else:
            active_count = allocations.filter(budget_period__is_active=True).count()
            status = 'active' if active_count > 0 else 'inactive'
            message = _(f"{active_count} تخصیص فعال از {allocations.count()} کل")
    elif isinstance(entity, (Project, SubProject)):
        allocations = ProjectBudgetAllocation.objects.filter(
            Q(project=entity) if isinstance(entity, Project) else Q(subproject=entity)
        )
        if filters:
            allocations = apply_filters(allocations, filters)
        if not allocations.exists():
            status, message = 'no_budget', _('هیچ بودجه‌ای تخصیص نیافته است.')
        else:
            active_count = allocations.filter(budget_allocation__budget_period__is_active=True).count()
            status = 'active' if active_count > 0 else 'inactive'
            message = _(f"{active_count} تخصیص فعال از {allocations.count()} کل")
    else:
        status, message = 'unknown', _('وضعیت نامشخص')

    result = {'status': status, 'message': message}
    cache.set(cache_key, result, timeout=300)
    logger.debug(f"get_budget_status: entity={entity}, result={result}")
    return result

# === توابع کمکی ===
def get_locked_amount(obj):
    """
    محاسبه مقدار قفل‌شده بودجه
    """
    from budgets.models import BudgetPeriod
    if isinstance(obj, BudgetPeriod):
        return (obj.total_amount * obj.locked_percentage) / Decimal('100')
    return Decimal('0')

def get_warning_amount(obj):
    """
    محاسبه آستانه هشدار بودجه
    """
    from budgets.models import BudgetPeriod
    if isinstance(obj, BudgetPeriod):
        return (obj.total_amount * obj.warning_threshold) / Decimal('100')
    return Decimal('0')

def calculate_allocation_percentages(allocations):
    """
    محاسبه درصد تخصیص بودجه
    """
    total_percentage = Decimal("0")
    for allocation in allocations:
        allocation.percentage = (
            (allocation.allocated_amount / allocation.budget_period.total_amount * Decimal("100"))
            if allocation.budget_period.total_amount else Decimal("0")
        )
        total_percentage += allocation.percentage
    logger.debug(f"calculate_allocation_percentages: total_percentage={total_percentage}, count={len(allocations)}")
    return total_percentage

def can_delete_budget(entity):
    """
    بررسی امکان حذف بودجه
    """
    from core.models import Project, SubProject
    if isinstance(entity, Project):
        can_delete = not entity.tankhah_set.exists() and not entity.subprojects.exists()
    elif isinstance(entity, SubProject):
        can_delete = not entity.tankhah_set.exists()
    else:
        can_delete = False
    logger.debug(f"can_delete_budget: entity={entity}, can_delete={can_delete}")
    return can_delete