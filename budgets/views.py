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

from budgets.ProjectBudgetAllocation.forms_ProjectBudgetAllocation import ProjectBudgetAllocationForm
from budgets.forms import   PaymentOrderForm, \
    PayeeForm, TransactionTypeForm
from budgets.models import BudgetPeriod, BudgetAllocation, ProjectBudgetAllocation, BudgetTransaction, PaymentOrder, \
    Payee, TransactionType
from core.PermissionBase import PermissionBaseView
from core.models import Organization, Project, SubProject, OrganizationType
from budgets.budget_calculations import (
    get_budget_details, calculate_allocation_percentages, calculate_total_allocated,
    calculate_remaining_budget, get_budget_status, get_organization_budget,
    get_project_remaining_budget, get_subproject_remaining_budget, get_subproject_total_budget, get_project_total_budget
)
from core.templatetags.rcms_custom_filters import number_to_farsi_words

logger = logging.getLogger(__name__)
# Dashboard
class BudgetDashboardView(PermissionBaseView, TemplateView):
    template_name = 'budgets/budgets_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organizations'] = Organization.objects.all()
        return context

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
        context['budget_details'] = get_budget_details(organization)
        logger.debug(f"OrganizationBudgetAllocationListView context: {context}")
        return context


# --- BudgetTransaction CRUD ---
class BudgetTransactionListView(PermissionBaseView, ListView):
    model = BudgetTransaction
    template_name = 'budgets/budget/budgettransaction_list.html'
    context_object_name = 'budget_transactions'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(allocation__budget_period__name__icontains=query) |
                Q(allocation__organization__name__icontains=query) |
                Q(description__icontains=query)
            )
        trans_type = self.request.GET.get('transaction_type')
        if trans_type:
            queryset = queryset.filter(transaction_type=trans_type)
        return queryset.order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['transaction_type'] = self.request.GET.get('transaction_type', '')
        context['transaction_types'] = BudgetTransaction.TRANSACTION_TYPES
        logger.debug(f"BudgetTransactionListView context: {context}")
        return context

class BudgetTransactionDetailView(PermissionBaseView, DetailView):
    model = BudgetTransaction
    template_name = 'budgets/budget/budgettransaction_detail.html'
    context_object_name = 'budget_transaction'

# --- PaymentOrder CRUD ---
class PaymentOrderListView(PermissionBaseView, ListView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_list.html'
    context_object_name = 'payment_orders'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(order_number__icontains=query) |
                Q(payee__name__icontains=query) |
                Q(tankhah__project__name__icontains=query)
            )
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by('-issue_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['status'] = self.request.GET.get('status', '')
        context['status_choices'] = PaymentOrder.STATUS_CHOICES
        logger.debug(f"PaymentOrderListView context: {context}")
        return context

class PaymentOrderCreateView(PermissionBaseView, CreateView):
    model = PaymentOrder
    form_class = PaymentOrderForm
    template_name = 'budgets/paymentorder/paymentorder_form.html'
    success_url = reverse_lazy('paymentorder_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'دستور پرداخت {form.instance.order_number} با موفقیت ایجاد شد.')
            return response

class PaymentOrderUpdateView(PermissionBaseView, UpdateView):
    model = PaymentOrder
    form_class = PaymentOrderForm
    template_name = 'budgets/paymentorder/paymentorder_form.html'
    success_url = reverse_lazy('paymentorder_list')

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'دستور پرداخت {form.instance.order_number} با موفقیت به‌روزرسانی شد.')
            return response

class PaymentOrderDeleteView(PermissionBaseView, DeleteView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_confirm_delete.html'
    success_url = reverse_lazy('paymentorder_list')

    def post(self, request, *args, **kwargs):
        payment_order = self.get_object()
        with transaction.atomic():
            payment_order.delete()
            messages.success(request, f'دستور پرداخت {payment_order.order_number} با موفقیت حذف شد.')
        return redirect(self.success_url)

# --- Payee CRUD ---
class PayeeListView(PermissionBaseView, ListView):
    model = Payee
    template_name = 'budgets/payee/payee_list.html'
    context_object_name = 'payees'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(national_id__icontains=query) |
                Q(iban__icontains=query)
            )
        payee_type = self.request.GET.get('payee_type')
        if payee_type:
            queryset = queryset.filter(payee_type=payee_type)
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['payee_type'] = self.request.GET.get('payee_type', '')
        context['payee_types'] = Payee.PAYEE_TYPES
        logger.debug(f"PayeeListView context: {context}")
        return context

class PayeeDetailView(PermissionBaseView, DetailView):
    model = Payee
    template_name = 'budgets/payee/payee_detail.html'
    context_object_name = 'payee'

class PayeeCreateView(PermissionBaseView, CreateView):
    model = Payee
    form_class = PayeeForm
    template_name = 'budgets/payee/payee_form.html'
    success_url = reverse_lazy('payee_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'دریافت‌کننده {form.instance.name} با موفقیت ایجاد شد.')
            return response

class PayeeUpdateView(PermissionBaseView, UpdateView):
    model = Payee
    form_class = PayeeForm
    template_name = 'budgets/payee/payee_form.html'
    success_url = reverse_lazy('payee_list')

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'دریافت‌کننده {form.instance.name} با موفقیت به‌روزرسانی شد.')
            return response

class PaymentOrderDetailView(PermissionBaseView, DetailView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_detail.html'
    permission_codenames = ['budgets.PaymentOrder_view']
    context_object_name = 'payment_order'

class PayeeDeleteView(PermissionBaseView, DeleteView):
    model = Payee
    template_name = 'budgets/payee/payee_confirm_delete.html'
    success_url = reverse_lazy('payee_list')

    def post(self, request, *args, **kwargs):
        payee = self.get_object()
        with transaction.atomic():
            payee.delete()
            messages.success(request, f'دریافت‌کننده {payee.name} با موفقیت حذف شد.')
        return redirect(self.success_url)

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


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.views import View

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