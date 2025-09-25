from django.core.exceptions import ValidationError
from django.utils import timezone
from django.views.generic.edit import CreateView
from accounts.models import CustomUser
from notificationApp.utils import send_notification
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.db.models import Sum, Q
from django.db import transaction

from BudgetsSystem.utils import parse_jalali_date, to_english_digits
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

class BudgetAllocationListView(PermissionBaseView, ListView):
    model = BudgetAllocation
    template_name = 'budgets/budget/budgetallocation_list.html'
    context_object_name = 'budget_allocations'
    paginate_by = 10
    # permission_required = 'budgets.view_budgetallocation'

    def get_queryset(self):
        # همان کد قبلی بدون تغییر
        queryset = BudgetAllocation.objects.all().select_related('organization', 'project', 'budget_period',
                                                                 'budget_item')
        logger.info(f"BudgetAllocationListView queryset: {queryset.count()} records")

        query = self.request.GET.get('q', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        budget_item_id = self.request.GET.get('budget_item')
        organization_id = self.request.GET.get('organization')
        allocation_date = self.request.GET.get('allocation_date')

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

        # فیلتر نمایش منقضی/غیرمنقضی (پیش‌فرض: غیرمنقضی)
        from django.utils import timezone as _tz
        expired_only = self.request.GET.get('expired_only', 'false').lower() in ('true', '1')
        current_date = _tz.now().date()
        expired_ids = []
        non_expired_ids = []
        for alloc in queryset.select_related('budget_period'):
            bp = alloc.budget_period
            is_expired = False
            if bp:
                is_expired = (bp.end_date < current_date) or bool(bp.is_completed)
            if is_expired:
                expired_ids.append(alloc.id)
            else:
                non_expired_ids.append(alloc.id)
        if expired_only:
            queryset = queryset.filter(id__in=expired_ids) if expired_ids else queryset.none()
        else:
            queryset = queryset.filter(id__in=non_expired_ids) if non_expired_ids else queryset.none()

        return queryset.order_by('-allocation_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization_id = self.request.GET.get('organization')
        budget_period_id = self.request.GET.get('budget_period')
        budget_item_id = self.request.GET.get('budget_item')
        project_id = self.request.GET.get('project')  # اضافه کردن فیلتر پروژه
        allocation_date = self.request.GET.get('allocation_date')  # اضافه کردن فیلتر پروژه

        # مقداردهی اولیه
        total_budget = Decimal('0')
        remaining_budget = Decimal('0')
        allocated_percentage = Decimal('0')
        remaining_percentage = Decimal('0')
        total_allocated = Decimal('0')

        # محاسبه بودجه دوره
        if budget_period_id:
            try:
                budget_period = BudgetPeriod.objects.get(id=budget_period_id, is_active=True)
                total_budget = budget_period.total_amount or Decimal('0')
                remaining_budget = budget_period.get_remaining_amount() or Decimal('0')
                total_allocated = BudgetAllocation.objects.filter(budget_period=budget_period).aggregate(
                    total=Sum('allocated_amount')
                )['total'] or Decimal('0')

                if total_budget > 0:
                    allocated_percentage = (total_allocated / total_budget) * Decimal('100')
                    remaining_percentage = (remaining_budget / total_budget) * Decimal('100')

                logger.info(
                    f"Budget period {budget_period.id}: total={total_budget}, "
                    f"remaining={remaining_budget}, allocated={total_allocated}, "
                    f"allocated_percentage={allocated_percentage:.2f}%, "
                    f"remaining_percentage={remaining_percentage:.2f}%"
                )
            except BudgetPeriod.DoesNotExist:
                logger.warning(f"Invalid budget_period_id: {budget_period_id}")
                context['status_message'] = _('دوره بودجه انتخاب‌شده نامعتبر است.')
        else:
            total_allocated = context['budget_allocations'].aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')
            total_budget = BudgetPeriod.objects.filter(is_active=True).aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0')
            remaining_budget = BudgetPeriod.objects.filter(is_active=True).aggregate(
                total=Sum('total_amount') - Sum('total_allocated')
            )['total'] or Decimal('0')

            if total_budget > 0:
                allocated_percentage = (total_allocated / total_budget) * Decimal('100')
                remaining_percentage = (remaining_budget / total_budget) * Decimal('100')

        # محاسبه اطلاعات ردیف بودجه
        budget_item_data = {}
        if budget_item_id:
            try:
                budget_item = BudgetItem.objects.get(id=budget_item_id, is_active=True)
                budget_period = budget_item.budget_period
                budget_item_total = budget_period.total_amount or Decimal('0')
                budget_item_allocated = BudgetAllocation.objects.filter(budget_item=budget_item).aggregate(
                    total=Sum('allocated_amount')
                )['total'] or Decimal('0')
                budget_item_remaining = budget_item_total - budget_item_allocated
                budget_item_allocated_percentage = (
                    (budget_item_allocated / budget_item_total * Decimal('100'))
                    if budget_item_total > 0 else Decimal('0')
                )
                budget_item_remaining_percentage = (
                    (budget_item_remaining / budget_item_total * Decimal('100'))
                    if budget_item_total > 0 else Decimal('0')
                )

                budget_item_data = {
                    'total': budget_item_total,
                    'remaining': budget_item_remaining,
                    'allocated': budget_item_allocated,
                    'allocated_percentage': budget_item_allocated_percentage,
                    'remaining_percentage': budget_item_remaining_percentage,
                }
            except BudgetItem.DoesNotExist:
                logger.warning(f"Invalid budget_item_id: {budget_item_id}")
                context['status_message'] = _('ردیف بودجه انتخاب‌شده نامعتبر است.')

        # محاسبه اطلاعات پروژه
        project_data = {}
        if project_id:
            try:
                project = Project.objects.get(id=project_id, is_active=True)
                project_allocations = BudgetAllocation.objects.filter(project=project)
                project_total = project_allocations.aggregate(
                    total=Sum('allocated_amount')
                )['total'] or Decimal('0')
                project_remaining = project.get_remaining_budget() or Decimal('0')
                project_allocated_percentage = (
                    (project_total / project_total * Decimal('100'))
                    if project_total > 0 else Decimal('0')
                )
                project_remaining_percentage = (
                    (project_remaining / project_total * Decimal('100'))
                    if project_total > 0 else Decimal('0')
                )

                project_data = {
                    'total': project_total,
                    'remaining': project_remaining,
                    'allocated': project_total,
                    'allocated_percentage': project_allocated_percentage,
                    'remaining_percentage': project_remaining_percentage,
                }
                logger.info(
                    f"Project {project.id}: total={project_total}, "
                    f"remaining={project_remaining}, allocated_percentage={project_allocated_percentage:.2f}%, "
                    f"remaining_percentage={project_remaining_percentage:.2f}%"
                )
            except Project.DoesNotExist:
                logger.warning(f"Invalid project_id: {project_id}")
                context['status_message'] = _('پروژه انتخاب‌شده نامعتبر است.')

        context.update({
            'total_budget': total_budget,
            'remaining_budget': remaining_budget,
            'total_allocated': total_allocated,
            'allocated_percentage': allocated_percentage,
            'remaining_percentage': remaining_percentage,
            'budget_item_data': budget_item_data,
            'project_data': project_data,  # اضافه کردن اطلاعات پروژه
            'budget_items': BudgetItem.objects.filter(is_active=True).select_related('organization', 'budget_period'),
            'organizations': Organization.objects.filter(is_active=True),
            'budget_periods': BudgetPeriod.objects.filter(is_active=True),
            'projects': Project.objects.filter(is_active=True),  # اضافه کردن پروژه‌ها برای فیلتر
            'status': 'filtered',
            'status_message': context.get('status_message', _('نمایش تخصیص‌های فیلترشده')),
            'query': self.request.GET.get('q', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'selected_budget_item': budget_item_id,
            'selected_organization': organization_id,
            'selected_budget_period': budget_period_id,
            'selected_project': project_id,
            'selected_allocation_date': allocation_date,  # ✅ اصلاح شد
            'expired_only': self.request.GET.get('expired_only', 'false').lower() in ('true','1'),
            'today': timezone.now().date(),
        })

        logger.debug(f"BudgetAllocationListView context: {context}")
        return context
class BudgetAllocationDetailView(PermissionBaseView, DetailView):
    model = BudgetAllocation
    template_name = 'budgets/budget/budgetallocation_detail.html'
    context_object_name = 'budget_allocation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from budgets.get_budget_details import get_budget_details
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

class BudgetAllocationUpdateView(PermissionBaseView, UpdateView):
    model = BudgetAllocation
    form_class = BudgetAllocationForm
    template_name = 'budgets/budget/budgetallocation_form.html'
    success_url = reverse_lazy('budgetallocation_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش تخصیص بودجه')
        context['budget_period'] = self.object.budget_period
        from django.utils import timezone
        context['today'] = timezone.now().date()
        context['total_amount'] = self.object.budget_period.total_amount or Decimal('0')
        context['remaining_amount'] = self.object.budget_period.get_remaining_amount() + self.object.allocated_amount
        context['remaining_percent'] = (
            (context['remaining_amount'] / context['total_amount'] * 100)
            if context['total_amount'] else 0
        )
        context['locked_percentage'] = self.object.budget_period.locked_percentage or 0
        context['warning_threshold'] = self.object.budget_period.warning_threshold or 10
        context['budget_items'] = BudgetItem.objects.filter(
            budget_period=self.object.budget_period,
            is_active=True
        ).select_related('organization')
        context['organizations'] = Organization.objects.filter(is_active=True).select_related('org_type')
        context['projects'] = Project.objects.filter(is_active=True).select_related('category')
        return context

    @transaction.atomic
    def form_valid(self, form):
        old_amount = self.get_object().allocated_amount
        new_amount = form.instance.allocated_amount
        difference = new_amount - old_amount
        remaining = self.get_object().budget_period.get_remaining_amount() + old_amount

        budget_period = form.cleaned_data['budget_period']
        is_locked, lock_message = budget_period.is_locked
        if is_locked:
            from django.http import request
            messages.error(request, lock_message)
            # Prevent saving the allocation
            return self.form_invalid(form)

        if new_amount > remaining:
            messages.error(self.request, f'مبلغ تخصیص بیشتر از باقی‌مانده بودجه ({remaining:,.0f} ریال) است.')
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

class BudgetAllocationCreateView(PermissionBaseView, CreateView):
    model = BudgetAllocation
    form_class = BudgetAllocationForm
    template_name = 'budgets/budget/budgetallocation_form.html'
    success_url = reverse_lazy('budgetallocation_list')
    permission_required = 'budgets.add_budgetallocation'

    def get_initial(self):
        initial = super().get_initial()
        budget_period_id = self.request.GET.get('budget_period')
        if budget_period_id:
            try:
                budget_period = BudgetPeriod.objects.get(pk=budget_period_id)
                initial['budget_period'] = budget_period
                initial['allocation_date'] = timezone.now().date()
                initial['is_active'] = True
                initial['is_stopped'] = False
                logger.info(f"Set initial budget_period: ID={budget_period.id}, name={budget_period.name}")
            except BudgetPeriod.DoesNotExist:
                logger.error(f"BudgetPeriod with ID={budget_period_id} not found")
        return initial

    def _get_budget_period(self):
        budget_period_id = self.request.GET.get('budget_period') or self.request.POST.get('budget_period')
        logger.debug(f"Getting budget_period with ID: {budget_period_id}")
        if not budget_period_id:
            logger.warning("No budget_period_id provided")
            return None
        try:
            # اجازه استفاده از دوره‌های منقضی/غیرفعال برای مشاهده و تخصیص (مطابق نیاز کاربر)
            budget_period = BudgetPeriod.objects.get(id=budget_period_id)
            logger.info(f"Retrieved budget_period: ID={budget_period.id}, name={budget_period.name}")
            return budget_period
        except (BudgetPeriod.DoesNotExist, ValueError) as e:
            logger.warning(f"Invalid budget_period_id: {budget_period_id}, error: {str(e)}")
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budget_period = self._get_budget_period()

        context['title'] = _('ایجاد تخصیص بودجه جدید')

        allowed_org_types = OrganizationType.objects.filter(is_budget_allocatable=True).values_list('id', flat=True)
        context['organizations'] = Organization.objects.filter(
            org_type__in=allowed_org_types, is_active=True
        ).select_related('org_type')

        if budget_period:
            context['budget_period'] = budget_period
            # برای جلوگیری از افزونگی، همه آیتم‌های فعال را نمایش بده (فرم هم همین را انجام می‌دهد)
            context['budget_items'] = BudgetItem.objects.filter(
                is_active=True
            ).select_related('organization')
            context['total_amount'] = budget_period.total_amount or Decimal('0')
            context['remaining_amount'] = budget_period.get_remaining_amount() or Decimal('0')
            context['remaining_percent'] = (
                (context['remaining_amount'] / context['total_amount'] * 100)
                if context['total_amount'] else 0
            )
            context['locked_percentage'] = budget_period.locked_percentage or 0
            context['warning_threshold'] = budget_period.warning_threshold or 10
            logger.info(f"Budget period data: total={context['total_amount']}, remaining={context['remaining_amount']}")
        else:
            context['budget_period'] = None
            context['budget_items'] = BudgetItem.objects.filter(
                organization__org_type__in=allowed_org_types, is_active=True
            ).select_related('organization')
            context['total_amount'] = Decimal('0')
            context['remaining_amount'] = Decimal('0')
            context['remaining_percent'] = 0
            context['locked_percentage'] = 0
            context['warning_threshold'] = 10
            messages.warning(self.request, _('دوره بودجه انتخاب‌شده نامعتبر است.'))

        context['projects'] = Project.objects.filter(is_active=True).select_related('category')
        logger.debug(f"Loaded {context['projects'].count()} projects")

        # for template badge (active/expired)
        from django.utils import timezone as _tz
        context['today'] = _tz.now().date()

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        budget_period = self._get_budget_period()
        if not budget_period:
            logger.warning("No valid budget period for form")
            messages.warning(self.request, _("دوره بودجه معتبر انتخاب نشده است."))
            kwargs['budget_period'] = None
        else:
            kwargs['budget_period'] = budget_period
        kwargs['user'] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"Starting dispatch in BudgetAllocationCreateView for user: {request.user.username}")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        logger.info(f"Form valid for BudgetAllocation, saving...")
        try:
            budget_period = form.cleaned_data['budget_period']
            # is_locked, lock_message = budget_period.is_period_locked
            is_locked, lock_message = budget_period.is_locked  # تغییر از is_period_locked به is_locked
            if is_locked:
                messages.error(self.request, lock_message)
                return self.form_invalid(form)

            with transaction.atomic():
                response = super().form_valid(form)
                logger.info(f"BudgetAllocation created with ID: {self.object.pk}")
                messages.success(self.request, _('تخصیص بودجه با موفقیت ثبت شد.'))
                # ارسال اعلان به کاربران مجاز شعبه
                try:
                    org = self.object.organization
                    if org:
                        recipients = CustomUser.objects.filter(is_active=True, userpost__post__organization=org).distinct()
                        if recipients.exists():
                            send_notification(
                                actor=self.request.user,
                                users=list(recipients),
                                posts=None,
                                verb=_('تخصیص بودجه جدید'),
                                description=_('مبلغ %(amount)s ریال برای دوره %(period)s ثبت شد.') % {
                                    'amount': f"{self.object.allocated_amount:,.0f}",
                                    'period': budget_period.name,
                                },
                                target=self.object,
                                entity_type='BudgetAllocation',
                                priority='MEDIUM'
                            )
                            logger.info(f"Notification sent to {recipients.count()} users for organization {org.id}")
                        else:
                            logger.warning("No recipients found for budget allocation notification")
                except Exception as notif_err:
                    logger.error(f"Failed to send allocation notification: {notif_err}")
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