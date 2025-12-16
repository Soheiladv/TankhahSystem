# budgets/views.py
import json
import logging
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView, TemplateView

# from budgets.ProjectBudgetAllocation.forms_ProjectBudgetAllocation import ProjectBudgetAllocationForm
from budgets.forms import   TransactionTypeForm
from budgets.models import BudgetPeriod, BudgetAllocation,  BudgetTransaction, PaymentOrder, \
    Payee, TransactionType
from core.PermissionBase import PermissionBaseView
from core.models import Organization, SubProject, Project

from core.templatetags.rcms_custom_filters import number_to_farsi_words


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.views import View

logger = logging.getLogger(__name__)
# Dashboard
class BudgetDashboardView__old(PermissionBaseView, TemplateView):
    template_name = 'budgets/budgets_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organizations'] = Organization.objects.all()
        return context

class BudgetDashboardView(PermissionBaseView, TemplateView):  # یا PermissionRequiredMixin اگر لازم باشد
    template_name = 'budgets/budgets_dashboard.html'

    def get_total_allocated_amount(self):
        """
        محاسبه جمع کل مبلغ تخصیص‌یافته (allocated_amount) در تمام تخصیص‌های فعال.
        نتیجه کش می‌شود تا عملکرد داشبورد بالا بماند.
        """
        cache_key = 'dashboard_total_allocated_amount'
        # from django.core import cache
        from django.core.cache import cache
        total = cache.get(cache_key)

        if total is None:
            try:
                # فقط تخصیص‌های فعال را در نظر می‌گیریم
                result = BudgetAllocation.objects.filter(
                    is_active=True
                ).aggregate(total_allocated=Sum('allocated_amount'))

                total = result['total_allocated'] or Decimal('0')
                # کش برای ۵ دقیقه (۳۰۰ ثانیه) - قابل تنظیم بر اساس نیاز
                cache.set(cache_key, total, timeout=300)
                logger.debug(f"Calculated total allocated amount: {total}")
            except Exception as e:
                logger.error(f"Error calculating total allocated amount: {str(e)}", exc_info=True)
                total = Decimal('0')

        return total

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # اضافه کردن جمع کل بودجه تخصیص‌یافته به context
        total_allocated = self.get_total_allocated_amount()
        context['total_allocated_amount'] = total_allocated
        context['total_allocated_formatted'] = f"{total_allocated:,.0f}"

        # سازمان‌ها برای فیلتر یا نمایش دیگر (اگر قبلاً داشتید)
        from core.models import Organization
        context['organizations'] = Organization.objects.all()

        logger.info(f"BudgetDashboardView rendered with total_allocated_amount={total_allocated}")
        return context

# استفاده در تمپلیت‌ها
# جزئیات تخصیص: {% url 'project_budget_allocation_detail' allocation.pk %}
# ویرایش تخصیص: {% url 'project_budget_allocation_edit' allocation.pk %}
# لیست تراکنش‌ها: {% url 'budget_transaction_list' allocation_id=allocation.id %}
# گزارش بودجه پروژه: {% url 'project_budget_report' project.pk %}
# گزارش هشدارها: {% url 'budget_warning_report' %}


# --- Organization Budget ---
class OrganizationBudgetAllocationListView(PermissionBaseView, ListView):
    model = BudgetAllocation
    template_name = 'budgets/budget/organization_budgetallocation_list.html'
    context_object_name = 'budget_allocations'
    paginate_by = 10

    def get_queryset(self):
        org_id = self.kwargs.get('org_id')
        return BudgetAllocation.objects.filter(organization_id=org_id).order_by('-allocation_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org_id = self.kwargs.get('org_id')
        organization = get_object_or_404(Organization, id=org_id)
        context['organization'] = organization
        from budgets.get_budget_details import get_budget_details
        context['budget_details'] = get_budget_details(organization)
        logger.debug(f"OrganizationBudgetAllocationListView context: {context}")
        return context

# --- TransactionType CRUD ---
class TransactionTypeListView(PermissionBaseView, ListView):
    model = TransactionType
    template_name = 'budgets/transactiontype/transactiontype_list.html'
    context_object_name = 'transaction_types'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(description__icontains=query))
        approval = self.request.GET.get('requires_extra_approval')
        if approval == 'yes':
            queryset = queryset.filter(requires_extra_approval=True)
        elif approval == 'no':
            queryset = queryset.filter(requires_extra_approval=False)
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['requires_extra_approval'] = self.request.GET.get('requires_extra_approval', '')
        logger.debug(f"TransactionTypeListView context: {context}")
        return context
class TransactionTypeDetailView(PermissionBaseView, DetailView):
    model = TransactionType
    template_name = 'budgets/transactiontype/transactiontype_detail.html'
    context_object_name = 'transaction_type'
class TransactionTypeCreateView(PermissionBaseView, CreateView):
    model = TransactionType
    form_class = TransactionTypeForm
    template_name = 'budgets/transactiontype/transactiontype_form.html'
    success_url = reverse_lazy('transactiontype_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'نوع تراکنش {form.instance.name} با موفقیت ایجاد شد.')
            return response
class TransactionTypeUpdateView(PermissionBaseView, UpdateView):
    model = TransactionType
    form_class = TransactionTypeForm
    template_name = 'budgets/transactiontype/transactiontype_form.html'
    success_url = reverse_lazy('transactiontype_list')

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'نوع تراکنش {form.instance.name} با موفقیت به‌روزرسانی شد.')
            return response
class TransactionTypeDeleteView(PermissionBaseView, DeleteView):
    model = TransactionType
    template_name = 'budgets/transactiontype/transactiontype_confirm_delete.html'
    success_url = reverse_lazy('transactiontype_list')

    def post(self, request, *args, **kwargs):
        transaction_type = self.get_object()
        with transaction.atomic():
            transaction_type.delete()
            messages.success(request, f'نوع تراکنش {transaction_type.name} با موفقیت حذف شد.')
        return redirect(self.success_url)

@method_decorator(csrf_protect, name='dispatch')
class NumberToWordsView(View):
    """پیاده‌سازی API برای تبدیل پویا"""
    def post(self, request):
        try:
            data = json.loads(request.body)
            number = data.get('number')
            words = number_to_farsi_words(number)
            logger.debug(f"Converted number {number} to words: {words}")
            return JsonResponse({'words': words})
        except Exception as e:
            logger.error(f"Error converting number to words: {str(e)}")
            return JsonResponse({'error': 'Invalid input'}, status=400)


def budget_Help(request):
    return render(request, template_name='help/budget_Period_help.html')