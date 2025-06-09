# import logging
# from decimal import Decimal
# from django.db.models import Sum, Q
# from django.core.cache import cache
# from django.utils import timezone
# from Tanbakhsystem.utils import parse_jalali_date
# from django.utils.translation import gettext_lazy as _
#
#
# logger = logging.getLogger(__name__)
#
#
#
# def calculate_total_allocated(entity=None, filters=None):
#     from budgets.models import BudgetAllocation
#     if filters is None:
#         filters = {}
#     queryset = BudgetAllocation.objects.all()
#
#     if entity:
#         from core.models import Organization
#         if isinstance(entity, Organization):
#             queryset = queryset.filter(organization=entity)
#         else:
#             logger.warning(f"Invalid entity type for calculate_total_allocated: {type(entity)}")
#             return Decimal('0')
#
#     if 'budget_period' in filters:
#         queryset = queryset.filter(budget_period=filters['budget_period'])
#     if 'date_from' in filters:
#         date_from = parse_jalali_date(filters['date_from']) if isinstance(filters['date_from'], str) else filters[
#             'date_from']
#         queryset = queryset.filter(allocation_date__gte=date_from)
#     if 'date_to' in filters:
#         date_to = parse_jalali_date(filters['date_to']) if isinstance(filters['date_to'], str) else filters['date_to']
#         queryset = queryset.filter(allocation_date__lte=date_to)
#     if 'is_active' in filters:
#         queryset = queryset.filter(is_active=filters['is_active'])
#
#     total = queryset.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
#     logger.debug(f"calculate_total_allocated: entity={entity}, filters={filters}, total={total}")
#     return total
#
#
# def calculate_remaining_budget(obj=None, filters=None):
#     from budgets.models import BudgetPeriod, BudgetAllocation, ProjectBudgetAllocation
#     from tankhah.models import Tankhah
#     from core.models import Organization
#     from decimal import Decimal
#
#     cache_key = f"remaining_budget_{type(obj).__name__ if obj else 'global'}_{obj.pk if obj else '0'}"
#     if filters:
#         cache_key += f"_{hash(str(filters))}"
#     cached_result = cache.get(cache_key)
#     if cached_result is not None:
#         logger.debug(f"Returning cached remaining_budget for {cache_key}: {cached_result}")
#         return cached_result
#
#     if obj:
#         if isinstance(obj, BudgetPeriod):
#             allocated = BudgetAllocation.objects.filter(budget_period=obj)
#             if filters:
#                 allocated = apply_filters(allocated, filters)
#             allocated = allocated.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
#             result = max(obj.total_amount - allocated, Decimal('0'))
#         elif isinstance(obj, BudgetAllocation):
#             used = ProjectBudgetAllocation.objects.filter(budget_allocation=obj)
#             if filters:
#                 used = apply_filters(used, filters)
#             used = used.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
#             result = max(obj.allocated_amount - used, Decimal('0'))
#         elif isinstance(obj, ProjectBudgetAllocation):
#             consumed = Tankhah.objects.filter(project_budget_allocation=obj)
#             if filters:
#                 consumed = apply_filters(consumed, filters)
#             consumed = consumed.aggregate(total=Sum('amount'))['total'] or Decimal('0')
#             result = max(obj.allocated_amount - consumed, Decimal('0'))
#         elif isinstance(obj, Organization):
#             total_budget = BudgetPeriod.objects.filter(organization=obj, is_active=True, is_completed=False)
#             if filters:
#                 total_budget = apply_filters(total_budget, filters)
#             total_budget = total_budget.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
#             total_allocated = BudgetAllocation.objects.filter(organization=obj)
#             if filters:
#                 total_allocated = apply_filters(total_allocated, filters)
#             total_allocated = total_allocated.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
#             result = max(total_budget - total_allocated, Decimal('0'))
#         else:
#             logger.warning(f"Invalid object type for calculate_remaining_budget: {type(obj)}")
#             result = Decimal('0')
#     else:
#         total_budget = BudgetPeriod.objects.all()
#         if filters:
#             total_budget = apply_filters(total_budget, filters)
#         total_budget = total_budget.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
#         total_allocated = BudgetAllocation.objects.all()
#         if filters:
#             total_allocated = apply_filters(total_allocated, filters)
#         total_allocated = total_allocated.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
#         result = max(total_budget - total_allocated, Decimal('0'))
#
#     cache.set(cache_key, result, timeout=300)
#     logger.debug(f"calculate_remaining_budget: obj={obj}, filters={filters}, result={result}")
#     return result
#
#
# def check_budget_status(obj):
#     """چک کردن وضعیت بودجه"""
#     from budgets.models import BudgetPeriod
#     if not isinstance(obj, BudgetPeriod):
#         logger.warning(f"Invalid object type for check_budget_status: {type(obj)}")
#         return 'unknown', 'وضعیت نامشخص'
#
#     cache_key = f"budget_status_{obj.pk}"
#     cached_result = cache.get(cache_key)
#     if cached_result is not None:
#         logger.debug(f"Returning cached budget_status for {cache_key}: {cached_result}")
#         return cached_result
#
#     remaining = calculate_remaining_budget(obj)
#     locked = obj.get_locked_amount()
#     warning = obj.get_warning_amount()
#
#     if not obj.is_active:
#         result = 'inactive', _('دوره غیرفعال است.')
#     elif obj.is_completed:
#         result = 'completed', _('بودجه تمام‌شده است.')
#     elif remaining <= 0 and obj.lock_condition == 'ZERO_REMAINING':
#         obj.is_completed = True
#         obj.is_active = False
#         obj.save()
#         result = 'completed', _('بودجه به صفر رسیده و تمام‌شده است.')
#     elif obj.lock_condition == 'AFTER_DATE' and obj.end_date < timezone.now().date():
#         obj.is_active = False
#         obj.save()
#         result = 'locked', _('دوره به دلیل پایان تاریخ قفل شده است.')
#     elif obj.lock_condition == 'MANUAL' and remaining <= locked:
#         result = 'locked', _('بودجه به حد قفل‌شده رسیده است.')
#     elif remaining <= warning:
#         result = 'warning', _('بودجه به آستانه هشدار رسیده است.')
#     else:
#         result = 'normal', _('وضعیت عادی')
#     # if result in ('completed', 'locked', 'inactive'):
#     #     BudgetHistory.objects.create(
#     #         content_type=ContentType.objects.get_for_model(BudgetPeriod),
#     #         object_id=obj.pk,
#     #         action='STATUS_CHANGE',
#     #         details=f"وضعیت به {result} تغییر کرد: {message}"
#     #     )
#     # result+=  status, message
#     cache.set(cache_key, result, timeout=300)
#     logger.debug(f"check_budget_status: obj={obj}, result={result}")
#     return result
#
#
# def apply_filters(queryset, filters):
#     if not filters:
#         return queryset
#     if 'date_from' in filters:
#         date_from = parse_jalali_date(filters['date_from']) if isinstance(filters['date_from'], str) else filters[
#             'date_from']
#         queryset = queryset.filter(allocation_date__gte=date_from)
#     if 'date_to' in filters:
#         date_to = parse_jalali_date(filters['date_to']) if isinstance(filters['date_to'], str) else filters['date_to']
#         queryset = queryset.filter(allocation_date__lte=date_to)
#     if 'is_active' in filters:
#         queryset = queryset.filter(budget_period__is_active=filters['is_active'])
#     if 'budget_period' in filters:
#         queryset = queryset.filter(budget_period=filters['budget_period'])
#     logger.debug(f"apply_filters: filters={filters}, queryset count={queryset.count()}")
#     return queryset
#
#
# def get_budget_details(entity=None, filters=None):
#     from budgets.models import BudgetPeriod, BudgetAllocation, ProjectBudgetAllocation
#     from core.models import Organization, Project, SubProject
#
#     cache_key = f"budget_details_{type(entity).__name__}_{entity.pk if entity else 'global'}"
#     cached_result = cache.get(cache_key)
#     if cached_result is not None:
#         logger.debug(f"Returning cached budget_details for {cache_key}: {cached_result}")
#         return cached_result
#
#     if isinstance(entity, BudgetPeriod):
#         total_budget = entity.total_amount
#         total_allocated = BudgetAllocation.objects.filter(budget_period=entity).aggregate(
#             total=Sum('allocated_amount')
#         )['total'] or Decimal('0')
#         remaining = calculate_remaining_budget(entity)
#         status = check_budget_status(entity)
#     elif isinstance(entity, Organization):
#         total_budget = BudgetAllocation.objects.filter(organization=entity).aggregate(
#             total=Sum('allocated_amount')
#         )['total'] or Decimal('0')
#         total_allocated = calculate_total_allocated(entity=entity, filters=filters)
#         remaining = calculate_remaining_budget(entity)
#         status = get_budget_status(entity, filters)
#     elif isinstance(entity, Project):
#         total_budget = ProjectBudgetAllocation.objects.filter(project=entity).aggregate(
#             total=Sum('allocated_amount')
#         )['total'] or Decimal('0')
#         total_allocated = calculate_total_allocated(entity=entity, filters=filters)
#         remaining = calculate_remaining_budget(entity)
#         status = get_budget_status(entity, filters)
#     elif isinstance(entity, SubProject):
#         total_budget = ProjectBudgetAllocation.objects.filter(subproject=entity).aggregate(
#             total=Sum('allocated_amount')
#         )['total'] or Decimal('0')
#         total_allocated = calculate_total_allocated(entity=entity, filters=filters)
#         remaining = calculate_remaining_budget(entity)
#         status = get_budget_status(entity, filters)
#     else:
#         total_budget = BudgetPeriod.objects.aggregate(
#             total=Sum('total_amount')
#         )['total'] or Decimal('0')
#         total_allocated = calculate_total_allocated(filters=filters)
#         remaining = calculate_remaining_budget(filters=filters)
#         status = get_budget_status(None, filters)
#
#     details = {
#         'total_budget': total_budget,
#         'total_allocated': total_allocated,
#         'remaining_budget': remaining,
#         'status': status['status'],
#         'status_message': status['message']
#     }
#
#     cache.set(cache_key, details, timeout=300)
#     logger.info(f"get_budget_details: entity={entity}, filters={filters}, details={details}")
#     return details
#
# def calculate_allocation_percentages(allocations):
#     total_percentage = Decimal("0")
#     for allocation in allocations:
#         allocation.percentage = (
#             (allocation.allocated_amount / allocation.budget_period.total_amount * Decimal("100"))
#             if allocation.budget_period.total_amount else Decimal("0")
#         )
#         total_percentage += allocation.percentage
#     logger.debug(f"calculate_allocation_percentages: total_percentage={total_percentage}, count={len(allocations)}")
#     return total_percentage
#
#
# def get_organization_budget(organization) -> Decimal:
#     #     total = calculate_total_allocated(entity=organization)
#     #     logger.debug(f"get_organization_budget: org={organization}, total={total}")
#     #     return total
#
#     # from core.models import Organization
#     # from budgets.models import BudgetPeriod
#     # def get_organization_budget(organization: core.models.Organization) -> Decimal:
#     """محاسبه بودجه کل سازمان بر اساس دوره‌های بودجه فعال.
#     """
#     from budgets.models import BudgetPeriod
#
#     total_budget = BudgetPeriod.objects.filter(organization=organization,is_active=True,is_completed=False).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
#     return total_budget
#
# def get_project_total_budget(project):
#     from budgets.models import ProjectBudgetAllocation
#     total = ProjectBudgetAllocation.objects.filter(project=project, subproject__isnull=True).aggregate(
#         total=Sum('allocated_amount')
#     )['total'] or Decimal("0")
#     logger.debug(f"get_project_total_budget: project={project}, total={total}")
#     return total
#
#
# def get_project_used_budget(project):
#     from budgets.models import ProjectBudgetAllocation
#     subproject_budget = ProjectBudgetAllocation.objects.filter(project=project, subproject__isnull=False).aggregate(
#         total=Sum('allocated_amount')
#     )['total'] or Decimal("0")
#     tankhah_budget = project.tankhah_set.filter(status='PAID').aggregate(
#         total=Sum('amount')
#     )['total'] or Decimal("0")
#     total = subproject_budget + tankhah_budget
#     logger.debug(
#         f"get_project_used_budget: project={project}, subproject={subproject_budget}, tankhah={tankhah_budget}, total={total}")
#     return total
#
#
# def get_project_remaining_budget(project):
#     """محاسبه بودجه باقی‌مانده پروژه"""
#     from budgets.models import ProjectBudgetAllocation
#     allocations = ProjectBudgetAllocation.objects.filter(project=project)
#     total_allocated = allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
#     # فرض می‌کنیم مصرف‌ها از BudgetTransaction ثبت می‌شوند
#     from budgets.models import BudgetTransaction
#     consumptions = BudgetTransaction.objects.filter(
#         allocation__project_allocations__project=project,
#         transaction_type='CONSUMPTION'
#     ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#     returns = BudgetTransaction.objects.filter(
#         allocation__project_allocations__project=project,
#         transaction_type='RETURN'
#     ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#     return max(total_allocated - consumptions + returns, Decimal('0'))
#
#
# def get_subproject_total_budget(subproject):
#     from budgets.models import ProjectBudgetAllocation
#     total = ProjectBudgetAllocation.objects.filter(subproject=subproject).aggregate(
#         total=Sum('allocated_amount')
#     )['total'] or Decimal("0")
#     logger.debug(f"get_subproject_total_budget: subproject={subproject}, total={total}")
#     return total
#
#
# def get_subproject_used_budget(subproject):
#     total = subproject.tankhah_set.filter(status='PAID').aggregate(
#         total=Sum('amount')
#     )['total'] or Decimal("0")
#     logger.debug(f"get_subproject_used_budget: subproject={subproject}, total={total}")
#     return total
#
#
# def get_subproject_remaining_budget(subproject):
#     """محاسبه بودجه باقی‌مانده زیرپروژه"""
#     from budgets.models import ProjectBudgetAllocation
#     allocations = ProjectBudgetAllocation.objects.filter(subproject=subproject)
#     total_allocated = allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
#     from budgets.models import BudgetTransaction
#     consumptions = BudgetTransaction.objects.filter(
#         allocation__project_allocations__subproject=subproject,
#         transaction_type='CONSUMPTION'
#     ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#     returns = BudgetTransaction.objects.filter(
#         allocation__project_allocations__subproject=subproject,
#         transaction_type='RETURN'
#     ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#     return max(total_allocated - consumptions + returns, Decimal('0'))
#
#
#
#
# def can_delete_budget(entity):
#     from core.models import Project, SubProject
#     if isinstance(entity, Project):
#         can_delete = not entity.tankhah_set.exists() and not entity.subprojects.exists()
#     elif isinstance(entity, SubProject):
#         can_delete = not entity.tankhah_set.exists()
#     else:
#         can_delete = False
#     logger.debug(f"can_delete_budget: entity={entity}, can_delete={can_delete}")
#     return can_delete
#
#
# def get_locked_amount(obj):
#     from budgets.models import BudgetPeriod
#     if isinstance(obj, BudgetPeriod):
#         return (obj.total_amount * obj.locked_percentage) / Decimal('100')
#     return Decimal('0')
#
#
# def get_warning_amount(obj):
#     from budgets.models import BudgetPeriod
#     if isinstance(obj, BudgetPeriod):
#         return (obj.total_amount * obj.warning_threshold) / Decimal('100')
#     return Decimal('0')
#
# def get_budget_status(entity, filters=None):
#     """
#        تابع وضعیت بودجه برای سازمان‌ها، پروژه‌ها، و زیرپروژه‌ها
#        فرض: مشابه check_budget_status اما برای موجودیت‌های دیگر
#        """
#     """بررسی وضعیت بودجه"""
#     from budgets.models import BudgetPeriod, BudgetAllocation, ProjectBudgetAllocation
#     from core.models import Organization, Project, SubProject
#
#     # cache_key = f"budget_status_{type(entity).__name__}_{entity.pk}"
#     # cached_result = cache.get(cache_key)
#     # if cached_result is not None:
#     #     logger.debug(f"Returning cached budget_status for {cache_key}: {cached_result}")
#     #     return cached_result
#
#     if isinstance(entity, BudgetPeriod):
#         status, message = entity.check_budget_status()
#     elif isinstance(entity, Organization):
#         allocations = BudgetAllocation.objects.filter(organization=entity)
#         if filters:
#             allocations = apply_filters(allocations, filters)
#         if not allocations.exists():
#             status, message = 'no_budget', 'هیچ بودجه‌ای تخصیص نیافته است.'
#         else:
#             active_count = allocations.filter(budget_period__is_active=True).count()
#             status = 'active' if active_count > 0 else 'inactive'
#             message = f"{active_count} تخصیص فعال از {allocations.count()} کل"
#     elif isinstance(entity, (Project, SubProject)):
#         allocations = ProjectBudgetAllocation.objects.filter(
#             Q(project=entity) if isinstance(entity, Project) else Q(subproject=entity)
#         )
#         if not allocations.exists():
#             status, message = 'no_budget', 'هیچ بودجه‌ای تخصیص نیافته است.'
#         else:
#             active_count = allocations.filter(budget_allocation__budget_period__is_active=True).count()
#             status = 'active' if active_count > 0 else 'inactive'
#             message = f"{active_count} تخصیص فعال از {allocations.count()} کل"
#     else:
#         status, message = 'unknown', 'وضعیت نامشخص'
#
#     result = {'status': status, 'message': message}
#     # cache.set(cache_key, result, timeout=300)
#     logger.debug(f"get_budget_status: entity={entity}, result={result}")
#     return result
