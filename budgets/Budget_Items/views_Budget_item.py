from django.contrib import messages
from django.db import models
from django.db.models import Q
from django.shortcuts import redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import gettext_lazy as _

from budgets.Budget_Items.frosm_BudgetItem import BudgetItemForm
from budgets.models import BudgetItem, BudgetPeriod

from django.contrib.auth.mixins import PermissionRequiredMixin
import logging

logger = logging.getLogger(__name__)

class BudgetItemListView(PermissionRequiredMixin, ListView):
    model = BudgetItem
    template_name = 'budgets/budgetitem/budgetitem_list.html'
    context_object_name = 'budget_items'
    paginate_by = 10
    permission_required = 'budgets.view_budgetitem'

    def get_queryset(self):
        queryset = BudgetItem.objects.select_related('budget_period', 'organization')#.order_by('-created_at')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(code__icontains=query) |
                Q(budget_period__name__icontains=query) |
                Q(organization__name__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('لیست ردیف‌های بودجه')
        context['query'] = self.request.GET.get('q', '')
        return context

class BudgetItemCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = BudgetItem
    form_class = BudgetItemForm
    template_name = 'budgets/budgetitem/budgetitem_form.html'
    success_url = reverse_lazy('budgetitem_list')
    success_message = _('ردیف بودجه با موفقیت ایجاد شد.')
    permission_required = 'budgets.add_budgetitem'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد ردیف بودجه جدید')
        context['budget_periods'] = BudgetPeriod.objects.filter(is_active=True).select_related('organization')
        from core.models import Organization
        context['organizations'] = Organization.objects.filter(is_active=True).select_related('org_type')
        return context

    def form_invalid(self, form):
        logger.error(f"Form invalid: errors={form.errors.as_json()}")
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید.'))
        return super().form_invalid(form)


class BudgetItemUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = BudgetItem
    form_class = BudgetItemForm
    template_name = 'budgets/budgetitem/budgetitem_form.html'
    success_url = reverse_lazy('budgetitem_list')
    success_message = _('ردیف بودجه با موفقیت ویرایش شد.')
    permission_required = 'budgets.change_budgetitem'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش ردیف بودجه')
        return context

class BudgetItemDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = BudgetItem
    template_name = 'budgets/budgetitem/budgetitem_confirm_delete.html'
    success_url = reverse_lazy('budgetitem_list')
    success_message = _('ردیف بودجه با موفقیت حذف شد.')
    permission_required = 'budgets.delete_budgetitem'

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except models.ProtectedError:
            messages.error(request, _('نمی‌توان ردیف بودجه را حذف کرد چون تخصیص‌هایی به آن وابسته‌اند.'))
            return redirect('budgetitem_list')

class BudgetItemDetailView(PermissionRequiredMixin, DetailView):
    model = BudgetItem
    template_name = 'budgets/budgetitem/budgetitem_detail.html'
    context_object_name = 'budget_item'
    permission_required = 'budgets.view_budgetitem'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('جزئیات ردیف بودجه')
        return context