from django.db.models import Q
from django.shortcuts import redirect
from django.views.generic import CreateView, UpdateView, DeleteView,ListView,DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction

from budgets.budget_calculations import get_budget_details
from core.PermissionBase import PermissionBaseView
from budgets.models import BudgetPeriod, BudgetTransaction
from budgets.BudgetPeriod.Forms_BudgetPeriod  import BudgetPeriodForm
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)

class BudgetPeriodCreateView(PermissionBaseView,CreateView):
    model = BudgetPeriod
    form_class = BudgetPeriodForm
    template_name = 'budgets/budget/budgetperiod_form.html'
    success_url = reverse_lazy('budgetperiod_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial']['created_by'] = self.request.user
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد دوره بودجه جدید')
        return context

    @transaction.atomic
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, _('دوره بودجه با موفقیت ایجاد شد.'))
            return response
        except Exception as e:
            messages.error(self.request, _('خطایی در ایجاد دوره بودجه رخ داد: ') + str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید.'))
        return self.render_to_response(self.get_context_data(form=form))

class BudgetPeriodUpdateView(PermissionBaseView,UpdateView):
    model = BudgetPeriod
    form_class = BudgetPeriodForm
    template_name = 'budgets/budget_period_form.html'
    success_url = reverse_lazy('budgetperiod_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش دوره بودجه')
        context['total_allocated'] = self.object.total_allocated
        context['remaining_amount'] = self.object.get_remaining_amount()
        return context

    @transaction.atomic
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, _('دوره بودجه با موفقیت به‌روزرسانی شد.'))
            return response
        except Exception as e:
            messages.error(self.request, _('خطایی در به‌روزرسانی دوره بودجه رخ داد: ') + str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید.'))
        return self.render_to_response(self.get_context_data(form=form))

class BudgetPeriodDeleteView(PermissionBaseView, DeleteView):
    model = BudgetPeriod
    template_name = 'budgets/budget/budgetperiod_confirm_delete.html'
    success_url = reverse_lazy('budgetperiod_list')

    def post(self, request, *args, **kwargs):
        budget_period = self.get_object()
        with transaction.atomic():
            budget_period.delete()
            messages.success(request, f'دوره بودجه {budget_period.name} با موفقیت حذف شد.')
        return redirect(self.success_url)

# --- BudgetPeriod CRUD ---
class BudgetPeriodListView(PermissionBaseView, ListView):
    model = BudgetPeriod
    template_name = 'budgets/budget/budgetperiod_list.html'
    context_object_name = 'budget_periods'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(organization__name__icontains=query))
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        return queryset.order_by('-start_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for period in context['budget_periods']:
            period.remaining_amount = period.get_remaining_amount()
            period.status, period.status_message = period.check_budget_status()
        context['query'] = self.request.GET.get('q', '')
        context['status'] = self.request.GET.get('status', '')
        logger.debug(f"BudgetPeriodListView context: {context}")
        return context

class BudgetPeriodDetailView(PermissionBaseView, DetailView):
    model = BudgetPeriod
    template_name = 'budgets/budget/budgetperiod_detail.html'
    context_object_name = 'budget_period'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transactions'] = BudgetTransaction.objects.filter(
            allocation__budget_period=self.object
        ).order_by('-timestamp')
        context['budget_details'] = get_budget_details(self.object)
        logger.debug(f"BudgetPeriodDetailView context: {context}")
        return context

