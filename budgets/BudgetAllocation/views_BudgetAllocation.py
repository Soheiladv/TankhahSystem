from django.core.exceptions import ValidationError
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.db.models import Sum, Q
from django.db import transaction

from budgets.BudgetAllocation.forms_BudgetAllocation import BudgetAllocationForm
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView, TemplateView

from decimal import Decimal
import logging
from django.http import JsonResponse

from budgets.budget_calculations import calculate_allocation_percentages
from budgets.models import BudgetPeriod, BudgetAllocation, BudgetTransaction
from core.PermissionBase import PermissionBaseView
from core.models import Organization, Project, OrganizationType

logger = logging.getLogger(__name__)
def get_projects_by_organization(request):
    """ویو برای دریافت پروژه‌های یک سازمان به صورت AJAX"""
    org_id = request.GET.get('organization_id')

    if org_id:
        try:
            projects = Project.objects.filter(
                organizations__id=org_id,
                is_active=True
            ).values('id', 'name', 'code')
            return JsonResponse({'projects': list(projects)})
        except ValueError:
            pass

    return JsonResponse({'projects': []})

class BudgetAllocationCreateView(PermissionBaseView, CreateView):
    model = BudgetAllocation
    form_class = BudgetAllocationForm
    template_name = 'budgets/budget/budgetallocation_form.html'
    success_url = reverse_lazy('budgetallocation_list')
    permission_required = 'budgets.add_budgetallocation'

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

        # سازمان‌های قابل تخصیص بودجه
        allowed_org_types = OrganizationType.objects.filter(
            is_budget_allocatable=True
        ).values_list('id', flat=True)

        context['organizations'] = Organization.objects.filter(
            org_type__in=allowed_org_types,
            is_active=True
        ).select_related('org_type')

        # پروژه‌های فعال
        context['projects'] = Project.objects.filter(is_active=True).select_related('category')

        # محاسبه اطلاعات بودجه
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

        # logger.debug(f"Context data: {context}")
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

class _BudgetAllocationCreateView(CreateView):
    model = BudgetAllocation
    form_class = BudgetAllocationForm
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
        context['organizations'] = Organization.objects.filter(is_budget_allocatable=True
        ).values_list('id', flat=True)
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

# ---------------------------------


# --- BudgetAllocation CRUD ---
class BudgetAllocationListView(PermissionBaseView, ListView):
    model = BudgetAllocation
    template_name = 'budgets/budget/budgetallocation_list.html'
    context_object_name = 'budget_allocations'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('budget_period', 'organization', 'project')
        query = self.request.GET.get('q', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')

        if query:
            queryset = queryset.filter(
                Q(budget_period__name__icontains=query) |
                Q(organization__name__icontains=query) |
                Q(project__name__icontains=query)
            )


        from Tanbakhsystem.utils import parse_jalali_date
        from Tanbakhsystem.utils import to_english_digits

        if date_from:
            try:
                date_from = parse_jalali_date(to_english_digits(date_from))
                queryset = queryset.filter(allocation_date__gte=date_from)
            except ValueError:
                logger.warning(f"Invalid date_from format: {date_from}")

        if date_to:
            try:
                date_to = parse_jalali_date(to_english_digits(date_to))
                queryset = queryset.filter(allocation_date__lte=date_to)
            except ValueError:
                logger.warning(f"Invalid date_to format: {date_to}")

        return queryset.order_by('-allocation_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {}

        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')

        if date_from:
            try:
                filters['date_from'] = parse_jalali_date(to_english_digits(date_from))
            except ValueError:
                logger.warning(f"Invalid date_from in filters: {date_from}")

        if date_to:
            try:
                filters['date_to'] = parse_jalali_date(to_english_digits(date_to))
            except ValueError:
                logger.warning(f"Invalid date_to in filters: {date_to}")

        # فقط جزئیات تخصیص‌های فیلترشده
        total_allocated = context['budget_allocations'].aggregate(
            total=Sum('allocated_amount')
        )['total'] or Decimal('0')
        total_remaining = sum(
            allocation.get_remaining_amount() for allocation in context['budget_allocations']
        )

        context.update({
            'total_budget': None,  # بودجه کلان محاسبه نمی‌شود مگر درخواست شود
            'total_allocated': total_allocated,
            'remaining_budget': total_remaining,
            'status': 'filtered',
            'status_message': _('نمایش تخصیص‌های فیلترشده')
        })

        context['total_percentage'] = calculate_allocation_percentages(context['budget_allocations'])
        context['query'] = self.request.GET.get('q', '')
        context['date_from'] = date_from
        context['date_to'] = date_to

        logger.debug(f"BudgetAllocationListView context: {context}")
        return context


class BudgetAllocationDetailView(PermissionBaseView, DetailView):
    model = BudgetAllocation
    template_name = 'budgets/budget/budgetallocation_detail.html'
    context_object_name = 'budget_allocation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from budgets.budget_calculations import get_budget_details
        context['budget_details'] = get_budget_details(self.object)
        logger.debug(f"BudgetAllocationDetailView context: {context}")
        return context
class BudgetAllocationUpdateView(PermissionBaseView, UpdateView):
    model = BudgetAllocation
    form_class = BudgetAllocationForm
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
        from django.shortcuts import redirect
        return redirect(self.success_url)
