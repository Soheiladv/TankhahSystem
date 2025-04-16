from django.core.exceptions import ValidationError
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.db.models import Sum, Q
from django.db import transaction

from Tanbakhsystem.utils import parse_jalali_date, to_english_digits
from budgets.BudgetAllocation.forms_BudgetAllocation import BudgetAllocationForm
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView, TemplateView

from decimal import Decimal
import logging
from django.http import JsonResponse

from budgets.budget_calculations import calculate_allocation_percentages
from budgets.models import BudgetPeriod, BudgetAllocation, BudgetTransaction, BudgetItem
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
 # ---------------------------------
# --- BudgetAllocation CRUD ---
class BudgetAllocationCreateView(PermissionBaseView, CreateView):
    model = BudgetAllocation
    form_class = BudgetAllocationForm
    template_name = 'budgets/budget/budgetallocation_form.html'
    success_url = reverse_lazy('budgetallocation_list')
    permission_required = 'budgets.add_budgetallocation'

    def _get_budget_period(self):
        budget_period_id = self.request.GET.get('budget_period') or self.request.POST.get('budget_period')
        logger.debug(f"Getting budget_period with ID: {budget_period_id}")
        if not budget_period_id:
            logger.warning("No budget_period_id provided")
            return None
        try:
            budget_period = BudgetPeriod.objects.get(id=budget_period_id, is_active=True)
            logger.info(f"Retrieved budget_period: ID={budget_period.id}, name={budget_period.name}")
            return budget_period
        except (BudgetPeriod.DoesNotExist, ValueError) as e:
            logger.warning(f"Invalid budget_period_id: {budget_period_id}, error: {str(e)}")
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budget_period = self._get_budget_period()
        context['budget_period'] = budget_period
        context['title'] = _('ایجاد تخصیص بودجه جدید')

        allowed_org_types = OrganizationType.objects.filter(is_budget_allocatable=True).values_list('id', flat=True)
        context['organizations'] = Organization.objects.filter(
            org_type__in=allowed_org_types, is_active=True
        ).select_related('org_type')

        if budget_period:
            context['budget_items'] = BudgetItem.objects.filter(
                budget_period=budget_period,
                is_active=True
            ).select_related('organization')
            context['total_budget'] = context['budget_items'].aggregate(total=Sum('total_amount'))['total'] or Decimal(
                '0')

            context['remaining_budget_item'] = Decimal('0')
            budget_item_id = self.request.GET.get('budget_item')
            if budget_item_id:
                try:
                    budget_item = BudgetItem.objects.get(id=budget_item_id, budget_period=budget_period)
                    context['remaining_budget_item'] = budget_item.get_remaining_amount()
                except BudgetItem.DoesNotExist:
                    logger.warning(f"Invalid budget_item_id: {budget_item_id}")

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
            logger.info(f"Budget period data: total={context['total_amount']}, remaining={context['remaining_amount']}")
        else:
            context['budget_items'] = BudgetItem.objects.none()
            context['total_budget'] = Decimal('0')
            context['remaining_budget_item'] = Decimal('0')
            context['total_amount'] = Decimal('0')
            context['remaining_amount'] = Decimal('0')
            context['remaining_percent'] = 0
            context['locked_percentage'] = 0
            context['warning_threshold'] = 10
            messages.warning(self.request, _('دوره بودجه انتخاب‌شده نامعتبر است.'))

        context['projects'] = Project.objects.filter(is_active=True).select_related('category')
        logger.debug(f"Loaded {context['projects'].count()} projects")

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        budget_period = self._get_budget_period()
        if not budget_period:
            logger.error("No valid budget period for form")
            messages.error(self.request, _("دوره بودجه معتبر انتخاب نشده است."))
            kwargs['budget_period'] = None
        else:
            kwargs['budget_period'] = budget_period
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        logger.debug("Form is valid, starting save process")
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                logger.info(f"BudgetAllocation created with ID: {self.object.pk}")
                messages.success(self.request, _('تخصیص بودجه با موفقیت ثبت شد.'))
                return response
        except ValidationError as e:
            logger.error(f"Validation error saving budget allocation: {str(e)}")
            form.add_error(None, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Unexpected error saving budget allocation: {str(e)}", exc_info=True)
            form.add_error(None, _('خطایی در ثبت تخصیص بودجه رخ داد: ') + str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.error(f"Form invalid: errors={form.errors.as_json()}")
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید.'))
        return self.render_to_response(self.get_context_data(form=form))


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

class BudgetAllocationListView(PermissionBaseView, ListView):
    model = BudgetAllocation
    template_name = 'budgets/budget/budgetallocation_list.html'
    context_object_name = 'budget_allocations'
    paginate_by = 10

    def get_queryset(self):
        queryset = BudgetAllocation.objects.all().select_related('organization', 'project', 'budget_period', 'budget_item')
        logger.info(f"BudgetAllocationListView queryset: {queryset.count()} records")

        query = self.request.GET.get('q', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        budget_item_id = self.request.GET.get('budget_item')
        organization_id = self.request.GET.get('organization')

        if query:
            queryset = queryset.filter(
                Q(budget_period__name__icontains=query) |
                Q(budget_item__name__icontains=query) |
                Q(organization__name__icontains=query) |
                Q(project__name__icontains=query)
            )

        if budget_item_id:
            queryset = queryset.filter(budget_item_id=budget_item_id)
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

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
        organization_id = self.request.GET.get('organization')
        budget_item_id = self.request.GET.get('budget_item')

        # بودجه کل فعال شعبه
        total_budget = Decimal('0')
        if organization_id:
            total_budget = BudgetItem.objects.filter(
                organization_id=organization_id,
                is_active=True
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        # تخصیص‌ها و باقی‌مانده تخصیص
        total_allocated = context['budget_allocations'].aggregate(
            total=Sum('allocated_amount')
        )['total'] or Decimal('0')
        total_remaining_allocation = context['budget_allocations'].aggregate(
            total=Sum('remaining_amount')
        )['total'] or Decimal('0')

        # باقی‌مانده ردیف بودجه
        total_remaining_budget_item = Decimal('0')
        if budget_item_id:
            try:
                budget_item = BudgetItem.objects.get(id=budget_item_id, is_active=True)
                total_remaining_budget_item = budget_item.get_remaining_amount()
            except BudgetItem.DoesNotExist:
                logger.warning(f"Invalid budget_item_id: {budget_item_id}")

        context.update({
            'total_budget': total_budget,
            'total_allocated': total_allocated,
            'total_remaining_allocation': total_remaining_allocation,
            'total_remaining_budget_item': total_remaining_budget_item,
            'budget_items': BudgetItem.objects.filter(is_active=True).select_related('organization', 'budget_period'),
            'organizations': Organization.objects.filter(is_active=True),
            'status': 'filtered',
            'status_message': _('نمایش تخصیص‌های فیلترشده'),
            'query': self.request.GET.get('q', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'selected_budget_item': budget_item_id,
            'selected_organization': organization_id,
        })

        logger.debug(f"BudgetAllocationListView context: total_budget={total_budget}, total_remaining_budget_item={total_remaining_budget_item}")
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