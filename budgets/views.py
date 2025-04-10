from django.db import transaction
from django.db.models import Q
from django.shortcuts import render

# Create your views here.
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from core.PermissionBase import PermissionBaseView
from .models import BudgetPeriod, BudgetAllocation, BudgetTransaction, PaymentOrder, Payee, TransactionType
from .forms import (BudgetPeriodForm, BudgetAllocationForm, BudgetTransactionForm,
                   PaymentOrderForm, PayeeForm, TransactionTypeForm)

# BudgetPeriod CRUD
class BudgetPeriodListView(PermissionBaseView, ListView):
    model = BudgetPeriod
    template_name = 'budgets/budget/budgetperiod_list.html'
    permission_codenames = ['budgets.BudgetPeriod_view']
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
        context['query'] = self.request.GET.get('q', '')
        context['status'] = self.request.GET.get('status', '')
        return context


class BudgetPeriodDetailView(PermissionBaseView, DetailView):
    model = BudgetPeriod
    template_name = 'budgets/budget/budgetperiod_detail.html'
    permission_codenames = ['budgets.BudgetPeriod_view']
    context_object_name = 'budget_period'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # اضافه کردن تاریخچه تخصیص‌ها
        context['transactions'] = BudgetTransaction.objects.filter(
            allocation__budget_period=self.object
        ).order_by('-timestamp')
        return context

class BudgetPeriodCreateView(PermissionBaseView, CreateView):
    model = BudgetPeriod
    form_class = BudgetPeriodForm
    template_name = 'budgets/budget/budgetperiod_form.html'
    permission_codenames = ['budgets.BudgetPeriod_add']
    success_url = reverse_lazy('budgetperiod_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'دوره بودجه {form.instance.name} با موفقیت ایجاد شد.')
        return super().form_valid(form)


class BudgetPeriodUpdateView(PermissionBaseView, UpdateView):
    model = BudgetPeriod
    form_class = BudgetPeriodForm
    template_name = 'budgets/budget/budgetperiod_form.html'
    permission_codenames = ['budgets.BudgetPeriod_update']
    success_url = reverse_lazy('budgetperiod_list')

    def form_valid(self, form):
        messages.success(self.request, f'دوره بودجه {form.instance.name} با موفقیت به‌روزرسانی شد.')
        return super().form_valid(form)

class BudgetPeriodDeleteView(PermissionBaseView, DeleteView):
    model = BudgetPeriod
    template_name = 'budgets/budget/budgetperiod_confirm_delete.html'
    permission_codenames = ['budgets.BudgetPeriod_delete']
    success_url = reverse_lazy('budgetperiod_list')
    def post(self, request, *args, **kwargs):
        budget_period = self.get_object()
        messages.success(request, f'دوره بودجه {budget_period.name} با موفقیت حذف شد.')
        return super().post(request, *args, **kwargs)

# BudgetAllocation CRUD
# BudgetAllocation CRUD
class BudgetAllocationListView(PermissionBaseView, ListView):
    model = BudgetAllocation
    template_name = 'budgets/budget/budgetallocation_list.html'
    permission_codenames = ['budgets.BudgetAllocation_view']
    context_object_name = 'budget_allocations'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(budget_period__name__icontains=query) | Q(organization__name__icontains=query)
            )
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(allocation_date__gte=date_from)
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(allocation_date__lte=date_to)
        return queryset.order_by('-allocation_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        return context


class BudgetAllocationDetailView(PermissionBaseView, DetailView):
    model = BudgetAllocation
    template_name = 'budgets/budget/budgetallocation_detail.html'
    permission_codenames = ['budgets.BudgetAllocation_view']
    context_object_name = 'budget_allocation'


class BudgetAllocationCreateView(PermissionBaseView, CreateView):
    model = BudgetAllocation
    form_class = BudgetAllocationForm
    template_name = 'budgets/budget/budgetallocation_form.html'
    permission_codenames = ['budgets.BudgetAllocation_add']
    success_url = reverse_lazy('budgetallocation_list')

    def _get_budget_period(self):
        budget_period_id = self.request.GET.get('budget_period') or self.request.POST.get('budget_period')
        if budget_period_id:
            try:
                return BudgetPeriod.objects.get(id=budget_period_id)
            except BudgetPeriod.DoesNotExist:
                messages.error(self.request, 'دوره بودجه موردنظر یافت نشد.')
                return None
        return None

    def _calculate_budget_metrics(self, budget_period):
        """Calculate various budget metrics for context"""
        if not budget_period:
            return {}
        return {
            'budget_period': budget_period,
            'remaining_amount': budget_period.remaining_amount,
            'total_amount': budget_period.total_amount,
            'remaining_percent': (budget_period.remaining_amount / budget_period.total_amount * 100
                                  if budget_period.total_amount > 0 else 0),
            'locked_amount': budget_period.get_locked_amount(),
            'warning_amount': budget_period.get_warning_amount(),
            'locked_percentage': budget_period.locked_percentage,
            'warning_threshold': budget_period.warning_threshold,
            'budget_status': budget_period.check_budget_status()[0]
        }

    def get_context_data(self, **kwargs):
        """Add budget period information to template context"""
        context = super().get_context_data(**kwargs)
        budget_period = self._get_budget_period()
        if budget_period:
            context.update(self._calculate_budget_metrics(budget_period))
        return context

    def _validate_allocation(self, form):
        """Validate budget allocation against period constraints"""
        budget_period = form.instance.budget_period
        new_remaining = budget_period.remaining_amount - form.instance.allocated_amount
        locked_amount = budget_period.get_locked_amount()

        if new_remaining < locked_amount:
            messages.error(
                self.request,
                f'نمی‌توانید بیشتر از بودجه قفل‌شده ({budget_period.locked_percentage}%) تخصیص دهید. '
                f'حداقل {locked_amount} باید باقی بماند.'
            )
            return False
        return True

    def _create_budget_transaction(self, allocation):
        """Create a budget transaction record"""
        BudgetTransaction.objects.create(
            allocation=allocation,
            transaction_type='ALLOCATION',
            amount=allocation.allocated_amount,
            user=self.request.user,
            description=f'تخصیص بودجه به {allocation.organization.name}'
        )

    def _update_budget_period(self, budget_period, allocated_amount):
        """Update budget period remaining amount"""
        budget_period.remaining_amount -= allocated_amount
        budget_period.save()
        return budget_period.check_budget_status()

    @transaction.atomic
    def form_valid(self, form):
        """Handle valid form submission"""
        if not self._validate_allocation(form):
            return self.form_invalid(form)

        form.instance.created_by = self.request.user
        allocation = form.save()

        self._create_budget_transaction(allocation)

        status, message = self._update_budget_period(
            form.instance.budget_period,
            form.instance.allocated_amount
        )

        if status == 'warning':
            messages.warning(self.request, message)
        elif status == 'locked':
            messages.error(self.request, message)

        messages.success(
            self.request,
            f'تخصیص بودجه به {form.instance.organization.name} با موفقیت ثبت شد.'
        )
        budget_period = self._get_budget_period()
        if not budget_period:
            messages.error(self.request, 'دوره بودجه مشخص نشده است.')
            return self.form_invalid(form)
        form.instance.budget_period = budget_period

        return super().form_valid(form)


class BudgetAllocationUpdateView(PermissionBaseView, UpdateView):
    model = BudgetAllocation
    form_class = BudgetAllocationForm
    template_name = 'budgets/budget/budgetallocation_form.html'
    permission_codenames = ['budgets.BudgetAllocation_update']
    success_url = reverse_lazy('budgetallocation_list')

    def form_valid(self, form):
        old_amount = self.get_object().allocated_amount
        new_amount = form.instance.allocated_amount
        budget_period = form.instance.budget_period
        difference = new_amount - old_amount

        if difference != 0:
            budget_period.remaining_amount -= difference
            budget_period.save()
            BudgetTransaction.objects.create(
                allocation=form.instance,
                transaction_type='ADJUSTMENT_INCREASE' if difference > 0 else 'ADJUSTMENT_DECREASE',
                amount=abs(difference),
                user=self.request.user,
                description=f'تغییر تخصیص بودجه به {form.instance.organization.name}'
            )
        messages.success(self.request, f'تخصیص بودجه به {form.instance.organization.name} با موفقیت به‌روزرسانی شد.')
        return super().form_valid(form)


class BudgetAllocationDeleteView(PermissionBaseView, DeleteView):
    model = BudgetAllocation
    template_name = 'budgets/budget/budgetallocation_confirm_delete.html'
    permission_codenames = ['budgets.BudgetAllocation_delete']
    success_url = reverse_lazy('budgetallocation_list')

    def post(self, request, *args, **kwargs):
        allocation = self.get_object()
        budget_period = allocation.budget_period
        budget_period.remaining_amount += allocation.allocated_amount
        budget_period.save()
        messages.success(request, f'تخصیص بودجه به {allocation.organization.name} با موفقیت حذف شد.')
        return super().post(request, *args, **kwargs)


# BudgetTransaction CRUD
class BudgetTransactionListView(PermissionBaseView, ListView):
    model = BudgetTransaction
    template_name = 'budgets/budget/budgettransaction_list.html'
    permission_codenames = ['budgets.BudgetTransaction_view']
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
        return context


class BudgetTransactionDetailView(PermissionBaseView, DetailView):
    model = BudgetTransaction
    template_name = 'budgets/budget/budgettransaction_detail.html'
    permission_codenames = ['budgets.BudgetTransaction_view']
    context_object_name = 'budget_transaction'


# PaymentOrder CRUD
class PaymentOrderListView(PermissionBaseView, ListView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_list.html'
    permission_codenames = ['budgets.PaymentOrder_view']
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
        return context


class PaymentOrderDetailView(PermissionBaseView, DetailView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_detail.html'
    permission_codenames = ['budgets.PaymentOrder_view']
    context_object_name = 'payment_order'


class PaymentOrderCreateView(PermissionBaseView, CreateView):
    model = PaymentOrder
    form_class = PaymentOrderForm
    template_name = 'budgets/paymentorder/paymentorder_form.html'
    permission_codenames = ['budgets.PaymentOrder_add']
    success_url = reverse_lazy('paymentorder_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'دستور پرداخت {form.instance.order_number} با موفقیت ایجاد شد.')
        return super().form_valid(form)


class PaymentOrderUpdateView(PermissionBaseView, UpdateView):
    model = PaymentOrder
    form_class = PaymentOrderForm
    template_name = 'budgets/paymentorder/paymentorder_form.html'
    permission_codenames = ['budgets.PaymentOrder_update']
    success_url = reverse_lazy('paymentorder_list')

    def form_valid(self, form):
        messages.success(self.request, f'دستور پرداخت {form.instance.order_number} با موفقیت به‌روزرسانی شد.')
        return super().form_valid(form)


class PaymentOrderDeleteView(PermissionBaseView, DeleteView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_confirm_delete.html'
    permission_codenames = ['budgets.PaymentOrder_delete']
    success_url = reverse_lazy('paymentorder_list')

    def post(self, request, *args, **kwargs):
        payment_order = self.get_object()
        messages.success(request, f'دستور پرداخت {payment_order.order_number} با موفقیت حذف شد.')
        return super().post(request, *args, **kwargs)


# Payee CRUD
class PayeeListView(PermissionBaseView, ListView):
    model = Payee
    template_name = 'budgets/payee/payee_list.html'
    permission_codenames = ['budgets.Payee_view']
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
        return context


class PayeeDetailView(PermissionBaseView, DetailView):
    model = Payee
    template_name = 'budgets/payee/payee_detail.html'
    permission_codenames = ['budgets.Payee_view']
    context_object_name = 'payee'


class PayeeCreateView(PermissionBaseView, CreateView):
    model = Payee
    form_class = PayeeForm
    template_name = 'budgets/payee/payee_form.html'
    permission_codenames = ['budgets.Payee_add']
    success_url = reverse_lazy('payee_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'دریافت‌کننده {form.instance.name} با موفقیت ایجاد شد.')
        return super().form_valid(form)


class PayeeUpdateView(PermissionBaseView, UpdateView):
    model = Payee
    form_class = PayeeForm
    template_name = 'budgets/payee/payee_form.html'
    permission_codenames = ['budgets.Payee_update']
    success_url = reverse_lazy('payee_list')

    def form_valid(self, form):
        messages.success(self.request, f'دریافت‌کننده {form.instance.name} با موفقیت به‌روزرسانی شد.')
        return super().form_valid(form)


class PayeeDeleteView(PermissionBaseView, DeleteView):
    model = Payee
    template_name = 'budgets/payee/payee_confirm_delete.html'
    permission_codenames = ['budgets.Payee_delete']
    success_url = reverse_lazy('payee_list')

    def post(self, request, *args, **kwargs):
        payee = self.get_object()
        messages.success(request, f'دریافت‌کننده {payee.name} با موفقیت حذف شد.')
        return super().post(request, *args, **kwargs)


# TransactionType CRUD
class TransactionTypeListView(PermissionBaseView, ListView):
    model = TransactionType
    template_name = 'budgets/transactiontype/transactiontype_list.html'
    permission_codenames = ['budgets.TransactionType_view']
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
        return context


class TransactionTypeDetailView(PermissionBaseView, DetailView):
    model = TransactionType
    template_name = 'budgets/transactiontype/transactiontype_detail.html'
    permission_codenames = ['budgets.TransactionType_view']
    context_object_name = 'transaction_type'


class TransactionTypeCreateView(PermissionBaseView, CreateView):
    model = TransactionType
    form_class = TransactionTypeForm
    template_name = 'budgets/transactiontype/transactiontype_form.html'
    permission_codenames = ['budgets.TransactionType_add']
    success_url = reverse_lazy('transactiontype_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'نوع تراکنش {form.instance.name} با موفقیت ایجاد شد.')
        return super().form_valid(form)


class TransactionTypeUpdateView(PermissionBaseView, UpdateView):
    model = TransactionType
    form_class = TransactionTypeForm
    template_name = 'budgets/transactiontype/transactiontype_form.html'
    permission_codenames = ['budgets.TransactionType_update']
    success_url = reverse_lazy('transactiontype_list')

    def form_valid(self, form):
        messages.success(self.request, f'نوع تراکنش {form.instance.name} با موفقیت به‌روزرسانی شد.')
        return super().form_valid(form)


class TransactionTypeDeleteView(PermissionBaseView, DeleteView):
    model = TransactionType
    template_name = 'budgets/transactiontype/transactiontype_confirm_delete.html'
    permission_codenames = ['budgets.TransactionType_delete']
    success_url = reverse_lazy('transactiontype_list')

    def post(self, request, *args, **kwargs):
        transaction_type = self.get_object()
        messages.success(request, f'نوع تراکنش {transaction_type.name} با موفقیت حذف شد.')
        return super().post(request, *args, **kwargs)