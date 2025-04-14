from decimal import Decimal

from django.db.models import Q, Sum
from django.shortcuts import redirect
from django.views.generic import CreateView, UpdateView, DeleteView,ListView,DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction

from Tanbakhsystem.utils import parse_jalali_date_jdate
from budgets.budget_calculations import get_budget_details, check_budget_status, calculate_remaining_budget
from core.PermissionBase import PermissionBaseView
from budgets.models import BudgetPeriod, BudgetTransaction, BudgetHistory
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
    template_name = 'budgets/budget/budgetperiod_form.html'
    success_url = reverse_lazy('budgetperiod_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

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
    from Tanbakhsystem.utils import parse_jalali_date

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '')
        status = self.request.GET.get('status', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')

        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(organization__name__icontains=q))
        if status:
            status_map = {
                'active': Q(is_active=True),
                'inactive': Q(is_active=False),
                'locked': Q(lock_condition='MANUAL'),
                'completed': Q(is_completed=True),
            }
            queryset = queryset.filter(status_map.get(status, Q()))

        try:
            if date_from:
                queryset = queryset.filter(start_date__gte=parse_jalali_date_jdate(date_from))
            if date_to:
                queryset = queryset.filter(end_date__lte=parse_jalali_date_jdate(date_to))
        except Exception as e:
            logger.error(f"Date filtering error: {str(e)}")

        return queryset.order_by('-start_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()  # برای محاسبه status_summary
        for period in context['budget_periods']:
            period.remaining_amount = max(period.total_amount - (period.total_allocated or Decimal('0')), Decimal('0'))
            period.status, period.status_message = check_budget_status(period)
            if period.status in ('warning', 'locked', 'completed'):
                messages.warning(self.request, f"{period.name}: {period.status_message}")
                from django.contrib.contenttypes.models import ContentType
                BudgetHistory.objects.create(
                    content_type=ContentType.objects.get_for_model(BudgetPeriod),
                    object_id=period.pk,
                    action='STATUS_CHECK',
                    details=f"وضعیت: {period.status} - {period.status_message}",
                    created_by=self.request.user
                )

        context['query'] = self.request.GET.get('q', '')
        context['status'] = self.request.GET.get('status', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['status_summary'] = {
            'active': queryset.filter(is_active=True).count(),
            'locked': queryset.filter(lock_condition='MANUAL').count(),
            'completed': queryset.filter(is_completed=True).count(),
            'total': queryset.count(),
        }
        logger.debug(f"BudgetPeriodListView context: {context}")
        return context


class BudgetPeriodDetailView(PermissionBaseView, DetailView):
    model = BudgetPeriod
    template_name = 'budgets/budget/budgetperiod_detail.html'
    context_object_name = 'budget_period'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # صفحه‌بندی تراکنش‌ها
        transactions = BudgetTransaction.objects.filter(
            allocation__budget_period=self.object
        ).order_by('-timestamp')
        from django.core.paginator import Paginator
        paginator = Paginator(transactions, 10)
        page_number = self.request.GET.get('page')
        context['transactions'] = paginator.get_page(page_number)
        # جزئیات بودجه
        try:
            context['budget_details'] = get_budget_details(self.object)
        except Exception as e:
            logger.error(f"Error in get_budget_details: {str(e)}")
            messages.error(self.request, _('خطایی در محاسبه جزئیات بودجه رخ داد.'))
            context['budget_details'] = {
                'total_budget': Decimal('0'),
                'total_allocated': Decimal('0'),
                'remaining_budget': Decimal('0'),
                'status': 'error',
                'status_message': 'خطا در محاسبه'
            }
        # اعلان وضعیت
        try:
            status_dict = check_budget_status(self.object)
            status = status_dict['status']
            message = status_dict['message']
            if status in ('warning', 'locked', 'completed'):
                messages.warning(self.request, message)
        except Exception as e:
            logger.error(f"Error in check_budget_status: {str(e)}")
            messages.error(self.request, _('خطایی در بررسی وضعیت بودجه رخ داد.'))
        logger.debug(f"BudgetPeriodDetailView context: {context}")
        return context