# budgets/views.py
import logging
from decimal import Decimal

from django.db.models import Sum
from django.views.generic import ListView, DetailView

from budgets.models import BudgetTransaction, ProjectBudgetAllocation
from core.PermissionBase import PermissionBaseView
from core.models import Project

logger = logging.getLogger(__name__)
from core.views import PermissionBaseView

class ProjectBudgetReportView(PermissionBaseView, DetailView):
    """گزارش بودجه پروژه و زیرپروژه"""
    model = Project
    template_name = 'budgets/reports_budgets/project_budget_report.html'
    context_object_name = 'project'
    permission_codename = 'core.Project_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        allocations = ProjectBudgetAllocation.objects.filter(project=project)
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


class BudgetWarningReportView(PermissionBaseView, ListView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/reports_budgets/budget_warning_report.html'
    context_object_name = 'allocations'
    permission_codename = 'budgets.ProjectBudgetAllocation_view'

    def get_queryset(self):
        queryset = super().get_queryset()
        warnings = []
        for allocation in queryset:
            budget_allocation = allocation.budget_allocation
            consumed = BudgetTransaction.objects.filter(
                allocation=budget_allocation,
                allocation__project=allocation.project,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            returned = BudgetTransaction.objects.filter(
                allocation=budget_allocation,
                allocation__project=allocation.project,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            total_consumed = consumed - returned
            remaining_budget =Decimal(  budget_allocation.allocated_amount) -Decimal(  BudgetTransaction.objects.filter(
                allocation=budget_allocation,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0') )+Decimal(  BudgetTransaction.objects.filter(
                allocation=budget_allocation,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0'))

            warning_message = None
            if total_consumed > allocation.allocated_amount:
                warning_message = _("مصرف بیش از تخصیص")
            elif remaining_budget < 0:
                warning_message = _("بودجه منفی")

            if warning_message:
                allocation.total_consumed = total_consumed
                allocation.remaining_budget = remaining_budget
                allocation.warning_message = warning_message
                warnings.append(allocation)

        return warnings