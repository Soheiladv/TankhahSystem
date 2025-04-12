# budgets/budget_calculations.py
import logging
from decimal import Decimal
from django.db.models import Sum, Q


logger = logging.getLogger(__name__)

def calculate_total_allocated(entity=None, filters=None):
    """محاسبه مجموع بودجه تخصیص‌یافته"""
    from budgets.models import ProjectBudgetAllocation,BudgetAllocation
    from core.models import Organization , Project
    queryset = BudgetAllocation.objects.all()
    if entity:
        if isinstance(entity, Organization):
            queryset = queryset.filter(organization=entity)
        elif isinstance(entity, Project):
            queryset = ProjectBudgetAllocation.objects.filter(project=entity)
    if filters:
        queryset = _apply_filters(queryset, filters)
    total = queryset.aggregate(total=Sum('allocated_amount'))['total'] or Decimal("0")
    logger.debug(f"calculate_total_allocated: entity={entity}, filters={filters}, total={total}")
    return total

def _calculate_remaining_budget(obj):
    """محاسبه بودجه باقی‌مانده برای هر سطح"""
    from budgets.models import BudgetPeriod, BudgetAllocation,ProjectBudgetAllocation
    from tankhah.models import Tankhah

    if isinstance(obj, BudgetPeriod):
        allocated = BudgetAllocation.objects.filter(budget_period=obj).aggregate(Sum('allocated_amount'))['allocated_amount__sum'] or Decimal('0')
        return max(obj.total_amount - allocated, Decimal('0'))
    elif isinstance(obj, BudgetAllocation):
        used = ProjectBudgetAllocation.objects.filter(budget_allocation=obj).aggregate(Sum('allocated_amount'))['allocated_amount__sum'] or Decimal('0')
        return max(obj.allocated_amount - used, Decimal('0'))
    elif isinstance(obj, ProjectBudgetAllocation):
        consumed = Tankhah.objects.filter(project_budget_allocation=obj).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        return max(obj.allocated_amount - consumed, Decimal('0'))
    return Decimal('0')

def calculate_remaining_budget(entity=None, filters=None):
    """محاسبه مانده بودجه"""
    from budgets.models import ProjectBudgetAllocation,BudgetAllocation,BudgetPeriod
    from core.models import Organization , Project,SubProject

    if isinstance(entity, BudgetPeriod):
        total_allocated = calculate_total_allocated(filters={'budget_period': entity})
        remaining = entity.total_amount - total_allocated
    elif isinstance(entity, Organization):
        allocations = BudgetAllocation.objects.filter(organization=entity)
        if filters:
            allocations = _apply_filters(allocations, filters)
        remaining = sum(ba.get_remaining_amount() for ba in allocations)
    elif isinstance(entity, Project):
        allocations = ProjectBudgetAllocation.objects.filter(project=entity)
        remaining = sum(pba.get_remaining_amount() for pba in allocations)
    elif isinstance(entity, SubProject):
        allocations = ProjectBudgetAllocation.objects.filter(subproject=entity)
        remaining = sum(pba.get_remaining_amount() for pba in allocations)
    else:
        total_budget = BudgetPeriod.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal("0")
        total_allocated = calculate_total_allocated(filters=filters)
        remaining = total_budget - total_allocated
    logger.debug(f"calculate_remaining_budget: entity={entity}, filters={filters}, remaining={remaining}")
    return remaining

def get_budget_status(entity, filters=None):
    """بررسی وضعیت بودجه"""
    from budgets.models import ProjectBudgetAllocation,BudgetAllocation,BudgetPeriod
    from core.models import Organization , Project,SubProject
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
        allocations = ProjectBudgetAllocation.objects.filter(project=entity)
        if not allocations.exists():
            status, message = 'no_budget', 'هیچ بودجه‌ای تخصیص نیافته است.'
        else:
            active_count = allocations.filter(budget_allocation__budget_period__is_active=True).count()
            status = 'active' if active_count > 0 else 'inactive'
            message = f"{active_count} تخصیص فعال از {allocations.count()} کل"
    elif isinstance(entity, SubProject):
        allocations = ProjectBudgetAllocation.objects.filter(subproject=entity)
        if not allocations.exists():
            status, message = 'no_budget', 'هیچ بودجه‌ای تخصیص نیافته است.'
        else:
            active_count = allocations.filter(budget_allocation__budget_period__is_active=True).count()
            status = 'active' if active_count > 0 else 'inactive'
            message = f"{active_count} تخصیص فعال از {allocations.count()} کل"
    else:
        status, message = 'unknown', 'وضعیت نامشخص'
    logger.debug(f"get_budget_status: entity={entity}, status={status}, message={message}")
    return {'status': status, 'message': message}

def _apply_filters(queryset, filters):
    """اعمال فیلترها روی queryset"""
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
    logger.debug(f"_apply_filters: filters={filters}, queryset count={queryset.count()}")
    return queryset

def get_budget_details(entity=None, filters=None):
    """دریافت جزئیات بودجه"""
    from budgets.models import ProjectBudgetAllocation,BudgetAllocation,BudgetPeriod
    from core.models import Organization , Project,SubProject
    if isinstance(entity, BudgetPeriod):
        total_budget = entity.total_amount
        total_allocated = calculate_total_allocated(filters={'budget_period': entity})
        remaining = entity.get_remaining_amount()
    elif isinstance(entity, Organization):
        total_budget = BudgetAllocation.objects.filter(
            organization=entity
        ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal("0")
        total_allocated = calculate_total_allocated(entity=entity, filters=filters)
        remaining = calculate_remaining_budget(entity=entity, filters=filters)
    elif isinstance(entity, Project):
        total_budget = ProjectBudgetAllocation.objects.filter(
            project=entity
        ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal("0")
        total_allocated = calculate_total_allocated(entity=entity, filters=filters)
        remaining = calculate_remaining_budget(entity=entity, filters=filters)
    elif isinstance(entity, SubProject):
        total_budget = ProjectBudgetAllocation.objects.filter(
            subproject=entity
        ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal("0")
        total_allocated = calculate_total_allocated(entity=entity, filters=filters)
        remaining = calculate_remaining_budget(entity=entity, filters=filters)
    else:
        total_budget = BudgetPeriod.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal("0")
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
    total_percentage = Decimal("0")
    for allocation in allocations:
        allocation.percentage = (
            (allocation.allocated_amount / allocation.budget_period.total_amount * Decimal("100"))
            if allocation.budget_period.total_amount else Decimal("0")
        )
        total_percentage += allocation.percentage
    logger.debug(f"calculate_allocation_percentages: total_percentage={total_percentage}, count={len(allocations)}")
    return total_percentage

def get_organization_budget(organization):
    from budgets.models import BudgetPeriod
    try:
        budget = BudgetPeriod.objects.filter(organization=organization, is_active=True).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        return budget
    except Exception as e:
        print(f"Error calculating budget for {organization}: {str(e)}")
        return Decimal('0')

def __get_organization_budget(organization):
    from budgets.models import BudgetAllocation
    """بودجه کل تخصیص‌یافته به سازمان"""
    total = BudgetAllocation.objects.filter(organization=organization).aggregate(total=Sum('allocated_amount'))['total'] or Decimal("0")
    logger.debug(f"get_organization_budget: org={organization}, total={total}")
    return total

def get_project_total_budget(project):
    from budgets.models import ProjectBudgetAllocation
    """بودجه کل تخصیص‌یافته به پروژه"""
    total = ProjectBudgetAllocation.objects.filter(project=project, subproject__isnull=True).aggregate(total=Sum('allocated_amount'))['total'] or Decimal("0")
    logger.debug(f"get_project_total_budget: project={project}, total={total}")
    return total

def get_project_used_budget(project):
    """بودجه مصرف‌شده پروژه (زیرپروژه‌ها + تنخواه‌ها)"""
    from budgets.models import ProjectBudgetAllocation
    subproject_budget = ProjectBudgetAllocation.objects.filter(project=project, subproject__isnull=False).aggregate(total=Sum('allocated_amount'))['total'] or Decimal("0")
    tankhah_budget = project.tankhah_set.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or Decimal("0")
    total = subproject_budget + tankhah_budget
    logger.debug(f"get_project_used_budget: project={project}, subproject={subproject_budget}, tankhah={tankhah_budget}, total={total}")
    return total

def get_project_remaining_budget(project):
    """بودجه باقی‌مانده پروژه"""
    remaining = get_project_total_budget(project) - get_project_used_budget(project)
    logger.debug(f"get_project_remaining_budget: project={project}, remaining={remaining}")
    return remaining

def get_subproject_total_budget(subproject):
    """بودجه کل تخصیص‌یافته به زیرپروژه"""
    from budgets.models import ProjectBudgetAllocation
    total = ProjectBudgetAllocation.objects.filter(subproject=subproject).aggregate(total=Sum('allocated_amount'))['total'] or Decimal("0")
    logger.debug(f"get_subproject_total_budget: subproject={subproject}, total={total}")
    return total

def get_subproject_used_budget(subproject):
    """بودجه مصرف‌شده زیرپروژه (تنخواه‌ها)"""
    total = subproject.tankhah_set.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or Decimal("0")
    logger.debug(f"get_subproject_used_budget: subproject={subproject}, total={total}")
    return total

def get_subproject_remaining_budget(subproject):
    """بودجه باقی‌مانده زیرپروژه"""
    remaining = get_subproject_total_budget(subproject) - get_subproject_used_budget(subproject)
    logger.debug(f"get_subproject_remaining_budget: subproject={subproject}, remaining={remaining}")
    return remaining

def can_delete_budget(entity):
    """چک می‌کنه که آیا بودجه پروژه یا زیرپروژه قابل حذف هست یا نه"""
    from core.models import Project,SubProject
    if isinstance(entity, Project):
        can_delete = not entity.tankhah_set.exists() and not entity.subprojects.exists()
    elif isinstance(entity, SubProject):
        can_delete = not entity.tankhah_set.exists()
    else:
        can_delete = False
    logger.debug(f"can_delete_budget: entity={entity}, can_delete={can_delete}")
    return can_delete