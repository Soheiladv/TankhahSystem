# budgets/views.py
import logging
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView, TemplateView
from budgets.forms import BudgetPeriodForm, ProjectBudgetAllocationForm, PaymentOrderForm, \
    PayeeForm, TransactionTypeForm
from budgets.models import BudgetPeriod, BudgetAllocation, ProjectBudgetAllocation, BudgetTransaction, PaymentOrder, Payee, TransactionType
from core.PermissionBase import PermissionBaseView
from core.models import Organization, Project, SubProject
from budgets.budget_calculations import (
    get_budget_details, calculate_allocation_percentages, calculate_total_allocated,
    calculate_remaining_budget, get_budget_status, get_organization_budget,
    get_project_remaining_budget, get_subproject_remaining_budget, get_subproject_total_budget
)

logger = logging.getLogger(__name__)
# Dashboard
class BudgetDashboardView(PermissionBaseView, TemplateView):
    template_name = 'budgets/budgets_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organizations'] = Organization.objects.all()
        return context

class __BudgetPeriodCreateView(PermissionBaseView, CreateView):
    model = BudgetPeriod
    form_class = BudgetPeriodForm
    # form_class = BudgetPeriodForm
    template_name = 'budgets/budget/budgetperiod_form.html'
    success_url = reverse_lazy('budgetperiod_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        existing = BudgetPeriod.objects.filter(
            organization=form.instance.organization,
            start_date__year=form.instance.start_date.year
        )
        if existing.exists():
            messages.warning(
                self.request,
                f"هشدار: {existing.count()} بودجه دیگر برای این سازمان در سال {form.instance.start_date.year} وجود دارد."
            )
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'دوره بودجه {form.instance.name} با موفقیت ایجاد شد.')
            return response

class __BudgetPeriodUpdateView(PermissionBaseView, UpdateView):
    model = BudgetPeriod
    form_class = BudgetPeriodForm
    template_name = 'budgets/budget/budgetperiod_form.html'
    success_url = reverse_lazy('budgetperiod_list')

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'دوره بودجه {form.instance.name} با موفقیت به‌روزرسانی شد.')
            return response


# --- BudgetAllocation CRUD ---
class BudgetAllocationListView(PermissionBaseView, ListView):
    model = BudgetAllocation
    template_name = 'budgets/budget/budgetallocation_list.html'
    context_object_name = 'budget_allocations'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('budget_period', 'organization')
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
        filters = {}
        if 'date_from' in self.request.GET:
            filters['date_from'] = self.request.GET['date_from']
        if 'date_to' in self.request.GET:
            filters['date_to'] = self.request.GET['date_to']
        budget_details = get_budget_details(filters=filters)
        context.update(budget_details)
        context['total_percentage'] = calculate_allocation_percentages(context['budget_allocations'])
        context['query'] = self.request.GET.get('q', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        logger.debug(f"BudgetAllocationListView context: {context}")
        return context

class BudgetAllocationDetailView(PermissionBaseView, DetailView):
    model = BudgetAllocation
    template_name = 'budgets/budget/budgetallocation_detail.html'
    context_object_name = 'budget_allocation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['budget_details'] = get_budget_details(self.object)
        logger.debug(f"BudgetAllocationDetailView context: {context}")
        return context

class __A__BudgetAllocationCreateView(PermissionBaseView, CreateView):  # فرض کردم PermissionBaseView نیازی نیست
    model = BudgetAllocation
    form_class = ProjectBudgetAllocationForm
    template_name = 'budgets/budget/budgetallocation_form.html'
    success_url = reverse_lazy('budgetallocation_list')

    def _get_budget_period(self):
        budget_period_id = self.request.GET.get('budget_period') or self.request.POST.get('budget_period')
        if budget_period_id:
            try:
                return BudgetPeriod.objects.get(id=budget_period_id)
            except BudgetPeriod.DoesNotExist:
                messages.error(self.request, _('دوره بودجه موردنظر یافت نشد.'))
                return None
        return None

    def get_form_kwargs(self):
        """پاس دادن سازمان‌ها به فرم"""
        kwargs = super().get_form_kwargs()
        kwargs['organizations'] = Organization.objects.all()  # لیست سازمان‌ها
        return kwargs

    def get_context_data(self, **kwargs):
        context =  super().get_context_data(**kwargs)
        budget_period = self._get_budget_period()
        if budget_period:
            budget_details = get_budget_details(budget_period)
            context.update({
                'budget_period': budget_period,
                'total_amount': budget_period.total_amount,
                'remaining_amount': budget_period.get_remaining_amount(),
                'remaining_percent': (
                    (budget_period.get_remaining_amount() / budget_period.total_amount * 100)
                    if budget_period.total_amount else 0
                ),
                'warning_threshold': budget_period.warning_threshold,
                'locked_percentage': budget_period.locked_percentage,
                'budget_details': budget_details,
            })
        context['organizations'] = Organization.objects.all()  # برای اطمینان
        logger.debug(f"BudgetAllocationCreateView context: {context}")
        return context

    @transaction.atomic
    def form_valid(self, form):
        budget_period = self._get_budget_period()
        if not budget_period:
            messages.error(self.request, _('دوره بودجه مشخص نشده است.'))
            return self.form_invalid(form)

        form.instance.budget_period = budget_period
        form.instance.created_by = self.request.user
        try:
            response = super().form_valid(form)
            BudgetTransaction.objects.create(
                allocation=form.instance,
                transaction_type='ALLOCATION',
                amount=form.instance.allocated_amount,
                created_by=self.request.user,
                description=f'تخصیص بودجه به {form.instance.organization.name}'
            )
            status = get_budget_status(budget_period)
            if status['status'] in ['warning', 'locked']:
                messages.warning(self.request, status['message'])
            messages.success(self.request, f'تخصیص بودجه به {form.instance.organization.name} با موفقیت ثبت شد.')
            return response
        except Exception as e:
            logger.error(f"Error on create: {str(e)}")
            messages.error(self.request, str(e))
            return self.form_invalid(form)

class BudgetAllocationCreateView(CreateView):
    model = BudgetAllocation
    form_class = ProjectBudgetAllocationForm
    template_name = 'budgets/budget/budgetallocation_form.html'
    success_url = reverse_lazy('budgetallocation_list')

    def _get_budget_period(self):
        budget_period_id = self.request.GET.get('budget_period') or self.request.POST.get('budget_period')
        try:
            return BudgetPeriod.objects.get(id=budget_period_id)
        except (BudgetPeriod.DoesNotExist, ValueError):
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budget_period = self._get_budget_period()
        context['budget_period'] = budget_period
        context['organizations'] = Organization.objects.filter(org_type__in=['COMPLEX', 'HQ'])
        context['projects'] = Project.objects.filter(is_active=True)
        if budget_period:
            context['total_amount'] = budget_period.total_amount
            used_budget = BudgetAllocation.objects.filter(budget_period=budget_period).aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')
            context['remaining_amount'] = budget_period.total_amount - used_budget
            context['remaining_percent'] = (context['remaining_amount'] / budget_period.total_amount * 100) if budget_period.total_amount else 0
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
class BudgetAllocationUpdateView(PermissionBaseView, UpdateView):
    model = BudgetAllocation
    form_class = ProjectBudgetAllocationForm
    template_name = 'budgets/budget/budgetallocation_form.html'
    success_url = reverse_lazy('budgetallocation_list')

    @transaction.atomic
    def form_valid(self, form):
        old_amount = self.get_object().allocated_amount
        new_amount = form.instance.allocated_amount
        difference = new_amount - old_amount
        remaining = self.get_object().budget_period.get_remaining_amount() + old_amount
        if new_amount > remaining:
            messages.error(self.request, f'مبلغ تخصیص بیشتر از باقی‌مانده بودجه ({remaining}) است.')
            return self.form_invalid(form)

        response = super().form_valid(form)
        if difference != 0:
            transaction_type = 'ADJUSTMENT_INCREASE' if difference > 0 else 'ADJUSTMENT_DECREASE'
            BudgetTransaction.objects.create(
                allocation=form.instance,
                transaction_type=transaction_type,
                amount=abs(difference),
                created_by=self.request.user,
                description=f'تغییر تخصیص بودجه به {form.instance.organization.name}'
            )
        messages.success(self.request, f'تخصیص بودجه به {form.instance.organization.name} با موفقیت به‌روزرسانی شد.')
        return response

class BudgetAllocationDeleteView(PermissionBaseView, DeleteView):
    model = BudgetAllocation
    template_name = 'budgets/budget/budgetallocation_confirm_delete.html'
    success_url = reverse_lazy('budgetallocation_list')

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        allocation = self.get_object()
        allocation.delete()
        messages.success(request, f'تخصیص بودجه به {allocation.organization.name} با موفقیت حذف شد.')
        return redirect(self.success_url)

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

# --- ProjectBudgetAllocation CRUD ---
class ProjectBudgetAllocationListView(PermissionBaseView, ListView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_list.html'
    context_object_name = 'allocations'

    def get_queryset(self):
        organization_id = self.kwargs['organization_id']
        organization = get_object_or_404(Organization, id=organization_id)
        queryset = ProjectBudgetAllocation.objects.filter(
            budget_allocation__organization=organization
        ).select_related('project', 'subproject', 'budget_allocation__budget_period')
        logger.info(f"Allocations for org {organization_id}: {list(queryset.values('id', 'allocated_amount'))}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = get_object_or_404(Organization, id=self.kwargs['organization_id'])
        context['organization'] = organization
        context['budget_details'] = get_budget_details(organization)
        logger.debug(f"ProjectBudgetAllocationListView context: {context}")
        return context

class ProjectBudgetAllocationDetailView(PermissionBaseView, DetailView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_detail.html'
    context_object_name = 'allocation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['budget_details'] = get_budget_details(self.object.project)
        logger.debug(f"ProjectBudgetAllocationDetailView context: {context}")
        return context

class ProjectBudgetAllocationCreateView(PermissionBaseView, CreateView):
    model = ProjectBudgetAllocation
    form_class = ProjectBudgetAllocationForm
    template_name = 'budgets/budget/project_budget_allocation.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization_id'] = self.kwargs['organization_id']
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        remaining = form.instance.budget_allocation.get_remaining_amount()
        if form.instance.allocated_amount > remaining:
            messages.error(self.request, f'مبلغ تخصیص بیشتر از باقی‌مانده بودجه شعبه ({remaining}) است.')
            return self.form_invalid(form)
        try:
            response = super().form_valid(form)
            logger.info(f"New allocation saved: {self.object.pk} - {self.object.allocated_amount}")
            messages.success(self.request, _("تخصیص بودجه با موفقیت ثبت شد"))
            return response
        except ValidationError as e:
            logger.error(f"Validation error on create: {str(e)}")
            form.add_error('allocated_amount', str(e))
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('project_budget_allocation_list',
                            kwargs={'organization_id': self.kwargs['organization_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = get_object_or_404(Organization, id=self.kwargs['organization_id'])
        budget_periods = BudgetPeriod.objects.filter(organization=organization, is_active=True)
        if not budget_periods.exists():
            messages.warning(self.request, _("هیچ دوره بودجه فعالی برای این شعبه یافت نشد"))
            context.update({
                'organization': organization,
                'form': None,
                'projects': [],
                'budget_details': get_budget_details(organization)
            })
            return context

        budget_allocations = BudgetAllocation.objects.filter(budget_period__in=budget_periods)
        if not budget_allocations.exists():
            messages.warning(self.request, _("هیچ تخصیص بودجه‌ای برای این دوره‌ها یافت نشد"))
            context.update({
                'organization': organization,
                'form': None,
                'projects': [],
                'budget_details': get_budget_details(organization)
            })
            return context

        total_org_budget = get_organization_budget(organization)
        budget_allocation = budget_allocations.first()
        budget_period = budget_allocation.budget_period
        projects = Project.objects.filter(organizations=organization, is_active=True)

        for project in projects:
            project.total_budget = get_project_total_budget(project)
            project.remaining_budget = get_project_remaining_budget(project)
            project.remaining_percent = (
                (project.remaining_budget / project.total_budget * 100)
                if project.total_budget > 0 else 0
            )
            project.total_percent = (
                (project.total_budget / total_org_budget * 100)
                if total_org_budget > 0 else 0
            )
            for subproject in project.subprojects.filter(is_active=True):
                subproject.total_budget = get_subproject_total_budget(subproject)
                subproject.remaining_budget = get_subproject_remaining_budget(subproject)
                subproject.remaining_percent = (
                    (subproject.remaining_budget / subproject.total_budget * 100)
                    if subproject.total_budget > 0 else 0
                )
                subproject.total_percent = (
                    (subproject.total_budget / project.total_budget * 100)
                    if project.total_budget > 0 else 0
                )

        context.update({
            'organization': organization,
            'budget_allocation': budget_allocation,
            'budget_period': budget_period,
            'total_org_budget': total_org_budget,
            'remaining_amount': budget_period.get_remaining_amount(),
            'remaining_percent': (
                (context['remaining_amount'] / budget_period.total_amount * 100)
                if budget_period.total_amount > 0 else 0
            ),
            'warning_threshold': budget_period.warning_threshold,
            'projects': projects,
            'budget_details': get_budget_details(organization)
        })
        logger.debug(f"ProjectBudgetAllocationCreateView context: {context}")
        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            Organization.objects.get(id=self.kwargs['organization_id'])
        except Organization.DoesNotExist:
            logger.error(f"Organization with id={self.kwargs['organization_id']} not found")
            messages.error(request, _("سازمان موردنظر یافت نشد"))
            return redirect('budgetperiod_list')
        return super().dispatch(request, *args, **kwargs)

class ProjectBudgetAllocationEditView(PermissionBaseView, UpdateView):
    model = ProjectBudgetAllocation
    form_class = ProjectBudgetAllocationForm
    template_name = 'budgets/budget/project_budget_allocation_edit.html'
    context_object_name = 'allocation'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization_id'] = self.object.budget_allocation.organization_id
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        old_amount = self.get_object().allocated_amount
        new_amount = form.instance.allocated_amount
        remaining = self.get_object().budget_allocation.get_remaining_amount() + old_amount
        if new_amount > remaining:
            messages.error(self.request, f'مبلغ تخصیص بیشتر از باقی‌مانده بودجه شعبه ({remaining}) است.')
            return self.form_invalid(form)
        try:
            response = super().form_valid(form)
            logger.info(f"Allocation {self.object.pk} updated")
            messages.success(self.request, _("تخصیص بودجه با موفقیت ویرایش شد"))
            return response
        except ValidationError as e:
            logger.error(f"Validation error on edit: {str(e)}")
            form.add_error(None, str(e))
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('project_budget_allocation_list',
                            kwargs={'organization_id': self.object.budget_allocation.organization_id})

class ProjectBudgetAllocationDeleteView(PermissionBaseView, DeleteView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_delete.html'
    context_object_name = 'allocation'

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        logger.info(f"Allocation {self.object.pk} deleted")
        success_url = self.get_success_url()
        self.object.delete()
        messages.success(self.request, _("تخصیص بودجه با موفقیت حذف شد"))
        return redirect(success_url)

    def get_success_url(self):
        return reverse_lazy('project_budget_allocation_list',
                            kwargs={'organization_id': self.object.budget_allocation.organization_id})

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