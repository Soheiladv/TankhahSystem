from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.db.models import Sum
from django.db import transaction
from decimal import Decimal
import logging

from budgets import BudgetAllocation
from budgets.BudgetAllocation.BudgetAllocationForm import BudgetAllocationForm
from budgets.models import BudgetPeriod
from core.models import Organization, Project

logger = logging.getLogger(__name__)

class BudgetAllocationCreateView(CreateView):
    model = BudgetAllocation
    form_class = BudgetAllocationForm
    template_name = 'budgets/budget/budgetallocation_form.html'
    success_url = reverse_lazy('budgetallocation_list')

    def _get_budget_period(self):
        budget_period_id = self.request.GET.get('budget_period') or self.request.POST.get('budget_period')
        try:
            return BudgetPeriod.objects.get(id=budget_period_id, is_active=True)
        except (BudgetPeriod.DoesNotExist, ValueError):
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budget_period = self._get_budget_period()
        context['budget_period'] = budget_period
        context['title'] = _('ایجاد تخصیص بودجه جدید')
        context['organizations'] = Organization.objects.filter(org_type__in=['COMPLEX', 'HQ'], is_active=True)
        context['projects'] = Project.objects.filter(is_active=True)

        if budget_period:
            context['total_amount'] = budget_period.total_amount or Decimal('0')
            used_budget = BudgetAllocation.objects.filter(
                budget_period=budget_period
            ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
            context['remaining_amount'] = max(context['total_amount'] - used_budget, Decimal('0'))
            context['remaining_percent'] = (
                (context['remaining_amount'] / context['total_amount'] * 100)
                if context['total_amount'] else 0
            )
            context['locked_percentage'] = 0
            context['warning_threshold'] = 10
        else:
            context['total_amount'] = Decimal('0')
            context['remaining_amount'] = Decimal('0')
            context['remaining_percent'] = 0
            context['locked_percentage'] = 0
            context['warning_threshold'] = 10

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['budget_period'] = self._get_budget_period()
        kwargs['request'] = self.request
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, _('تخصیص بودجه با موفقیت ثبت شد.'))
            return response
        except Exception as e:
            logger.error(f"Error saving budget allocation: {str(e)}")
            messages.error(self.request, _('خطایی در ثبت تخصیص بودجه رخ داد: ') + str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.error(f"Form errors: {form.errors.as_json()}")
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید.'))
        return self.render_to_response(self.get_context_data(form=form))