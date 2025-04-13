from django.core.exceptions import ValidationError
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.db.models import Sum
from django.db import transaction
from decimal import Decimal
import logging

from budgets.BudgetAllocation.forms_BudgetAllocation import BudgetAllocationForm
from budgets.models import BudgetPeriod, BudgetAllocation
from core.PermissionBase import PermissionBaseView
from core.models import Organization, Project, OrganizationType

logger = logging.getLogger(__name__)

class BudgetAllocationCreateView(PermissionBaseView, CreateView):
    model = BudgetAllocation
    form_class = BudgetAllocationForm
    template_name = 'budgets/budget/budgetallocation_form.html'
    success_url = reverse_lazy('budgetallocation_list')

    def _get_budget_period(self):
        budget_period_id = self.request.GET.get('budget_period') or self.request.POST.get('budget_period')
        if not budget_period_id:
            logger.warning("No budget_period_id provided in request")
            return None
        try:
            budget_period = BudgetPeriod.objects.get(id=budget_period_id, is_active=True)
            logger.debug(f"Retrieved budget_period: {budget_period}")
            return budget_period
        except (BudgetPeriod.DoesNotExist, ValueError) as e:
            logger.warning(f"Invalid budget_period_id: {budget_period_id}, error: {str(e)}")
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budget_period = self._get_budget_period()
        context['budget_period'] = budget_period
        context['title'] = _('ایجاد تخصیص بودجه جدید')
        allowed_org_types = OrganizationType.objects.filter(
            is_budget_allocatable=True
        ).values_list('id', flat=True)
        context['organizations'] = Organization.objects.filter(
            org_type__in=allowed_org_types,
            is_active=True
        )
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
            context['locked_percentage'] = budget_period.locked_percentage or 0
            context['warning_threshold'] = budget_period.warning_threshold or 10
        else:
            context['total_amount'] = Decimal('0')
            context['remaining_amount'] = Decimal('0')
            context['remaining_percent'] = 0
            context['locked_percentage'] = 0
            context['warning_threshold'] = 10
            messages.warning(self.request, _('دوره بودجه انتخاب‌شده نامعتبر است یا یافت نشد.'))

        logger.debug(f"Context data: {context}")
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        budget_period = self._get_budget_period()
        if not budget_period:
            raise ValidationError(_("دوره بودجه معتبر انتخاب نشده است."))
        kwargs['budget_period'] = budget_period
        kwargs['user'] = self.request.user
        logger.debug(f"Form kwargs: {kwargs}")
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, _('تخصیص بودجه با موفقیت ثبت شد.'))
            logger.info("BudgetAllocation created successfully")
            return response
        except Exception as e:
            logger.error(f"Error saving budget allocation: {str(e)}")
            messages.error(self.request, _('خطایی در ثبت تخصیص بودجه رخ داد: ') + str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.error(f"Form errors: {form.errors.as_json()}")
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید.'))
        return self.render_to_response(self.get_context_data(form=form))