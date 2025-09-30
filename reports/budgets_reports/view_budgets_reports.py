# budgets/views.py
import logging
from decimal import Decimal
from django.db.models import Sum
from django.views.generic import ListView, DetailView
from budgets.models import BudgetTransaction,   BudgetAllocation
from core.models import Project
from core.views import PermissionBaseView
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db.models import Q
from budgets.models import BudgetHistory, Tankhah, Factor

logger = logging.getLogger(__name__)

class ProjectBudgetReportView(PermissionBaseView, DetailView):
    """گزارش بودجه پروژه و زیرپروژه"""
    model = Project
    template_name = 'budgets/reports_budgets/project_budget_report.html'
    context_object_name = 'project'
    permission_codename = 'core.Project_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        allocations = BudgetAllocation.objects.filter(project=project)
        total_allocated = allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
        consumed = BudgetTransaction.objects.filter(
            allocation__in=allocations.values('budget_allocation'),
            allocation__project=project,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        returned = BudgetTransaction.objects.filter(
            allocation__in=allocations.values('budget_allocation'),
            allocation__project=project,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        remaining = total_allocated - (consumed - returned)

        context.update({
            'allocations': allocations,
            'total_allocated': total_allocated,
            'consumed': consumed,
            'returned': returned,
            'remaining': remaining,
        })
        return context

from django.utils.translation import gettext_lazy as _

class BudgetWarningReportView(PermissionBaseView, ListView):
    model = BudgetAllocation
    template_name = 'budgets/reports_budgets/budget_warning_report.html'
    context_object_name = 'allocations'
    permission_codename = 'budgets.BudgetAllocation_view'

    def get_queryset(self):
        queryset = super().get_queryset()
        warnings = []
        for allocation in queryset:
            # استفاده از خود «allocation» به جای فیلد ناموجود «allocation.budget_allocation»
            consumed = BudgetTransaction.objects.filter(
                allocation=allocation,
                allocation__project=allocation.project,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            returned = BudgetTransaction.objects.filter(
                allocation=allocation,
                allocation__project=allocation.project,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            total_consumed = consumed - returned
            remaining_budget = (
                Decimal(allocation.allocated_amount)
                - Decimal(
                    BudgetTransaction.objects.filter(
                        allocation=allocation,
                        transaction_type='CONSUMPTION'
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                )
                + Decimal(
                    BudgetTransaction.objects.filter(
                        allocation=allocation,
                        transaction_type='RETURN'
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                )
            )

            warning_message = None
            if total_consumed > allocation.allocated_amount:
                warning_message = _("مصرف بیش از تخصیص")
            elif remaining_budget < 0:
                warning_message = _("بودجه منفی")
            else:
                # هشدار نرم بر اساس آستانه تعریف‌شده در خود تخصیص
                try:
                    warning_amount = allocation.get_warning_amount()
                except Exception:
                    warning_amount = Decimal('0')
                if remaining_budget <= warning_amount:
                    warning_message = _("نزدیک آستانه هشدار")

            if warning_message:
                allocation.total_consumed = total_consumed
                allocation.remaining_budget = remaining_budget
                allocation.warning_message = warning_message
                warnings.append(allocation)

        return warnings


# budgets/reports.py
def get_budget_transfers(budget_period, filters=None):
    """گزارش جابجایی‌های بودجه"""
    cache_key = f"budget_transfers_{budget_period.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached budget transfers: {cache_key}")
        return cached_result

    content_types = [
        ContentType.objects.get_for_model( BudgetAllocation),
     ]
    transfers = []
    return_transactions = BudgetHistory.objects.filter(
        content_type__in=content_types,
        action='RETURN',
        content_object__budget_period=budget_period,
        transaction_id__endswith='-RETURN'
    ).select_related('created_by')

    for return_tx in return_transactions:
        transfer_id = return_tx.transaction_id.replace('-RETURN', '')
        allocation_tx = BudgetHistory.objects.filter(
            content_type__in=content_types,
            action='ALLOCATION',
            content_object__budget_period=budget_period,
            transaction_id=f"{transfer_id}-ALLOCATION"
        ).select_related('created_by').first()

        if allocation_tx:
            transfers.append({
                'transfer_id': transfer_id,
                'source': {
                    'content_type': return_tx.content_type.model,
                    'object_id': return_tx.object_id,
                    'amount': return_tx.amount,
                    'details': return_tx.details,
                    'created_at': return_tx.created_at,
                    'created_by': return_tx.created_by.username,
                },
                'destination': {
                    'content_type': allocation_tx.content_type.model,
                    'object_id': allocation_tx.object_id,
                    'amount': allocation_tx.amount,
                    'details': allocation_tx.details,
                    'created_at': allocation_tx.created_at,
                    'created_by': allocation_tx.created_by.username,
                }
            })

    if filters:
        from budgets.budget_calculations import apply_filters
        transfers = apply_filters(transfers, filters)

    cache.set(cache_key, transfers, timeout=3600)
    logger.debug(f"Cached budget transfers: {cache_key}")
    return transfers

def get_returned_budgets(budget_period, entity_type='all', filters=None):
    """گزارش بودجه‌های برگشتی"""
    cache_key = f"returned_budgets_{budget_period.pk}_{entity_type}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached returned budgets: {cache_key}")
        return cached_result

    content_types = []
    if entity_type == 'all':
        content_types = [
            ContentType.objects.get_for_model(BudgetAllocation),
         ]
    elif entity_type == 'BudgetAllocation':
        content_types = [ContentType.objects.get_for_model(BudgetAllocation)]

    queryset = BudgetHistory.objects.filter(
        content_type__in=content_types,
        action='RETURN',
        content_object__budget_period=budget_period
    ).select_related('created_by').values(
        'amount',
        'details',
        'created_at',
        'created_by__username',
        'content_type__model'
    )

    if filters:
        from budgets.budget_calculations import apply_filters
        queryset = apply_filters(queryset, filters)

    cache.set(cache_key, queryset, timeout=3600)
    logger.debug(f"Cached returned budgets: {cache_key}")
    return queryset

def get_tankhah_report(budget_period, filters=None):
    """گزارش تنخواه‌ها"""
    cache_key = f"tankhah_report_{budget_period.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached tankhah report: {cache_key}")
        return cached_result

    queryset = Tankhah.objects.filter(
        allocation__budget_period=budget_period
    ).select_related('allocation', 'project', 'project_allocation').values(
        'id',
        'status',
        'allocated_amount',
        'consumed_amount',
        'returned_amount',
        'project__name',
        'allocation__organization__name',
        'project_allocation__id',
        'is_active'
    )

    if filters:
        from budgets.budget_calculations import apply_filters
        queryset = apply_filters(queryset, filters)

    cache.set(cache_key, queryset, timeout=3600)
    logger.debug(f"Cached tankhah report: {cache_key}")
    return queryset

def get_invoice_report(budget_period, filters=None):
    """گزارش فاکتورها"""
    cache_key = f"invoice_report_{budget_period.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached invoice report: {cache_key}")
        return cached_result

    queryset = Factor.objects.filter(
        transaction__allocation__budget_period=budget_period
    ).select_related('transaction', 'project', 'tankhah').values(
        'id',
        'invoice_number',
        'amount',
        'status',
        'project__name',
        'transaction__allocation__organization__name',
        'tankhah__id',
        'created_at'
    )

    if filters:
        from budgets.budget_calculations import apply_filters
        queryset = apply_filters(queryset, filters)

    cache.set(cache_key, queryset, timeout=3600)
    logger.debug(f"Cached invoice report: {cache_key}")
    return queryset