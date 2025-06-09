# budgets/views.py
from django.views.generic.edit import UpdateView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse, Http404
from django.db import transaction
from django.db.models import Sum, Q
from django.core.exceptions import ValidationError
from decimal import Decimal
# from .models import BudgetAllocation, BudgetTransaction
# from .forms import BudgetAllocationForm  # فرم هماهنگ با BudgetAllocation
import logging
from django.utils.translation import gettext_lazy as _

from budgets.BudgetAllocation.forms_BudgetAllocation import BudgetAllocationForm
from budgets.models import BudgetAllocation, BudgetTransaction
from core.models import SubProject

# تنظیم لاگر برای ثبت جزئیات خطاها و رویدادها
logger = logging.getLogger(__name__)
from core.PermissionBase import  PermissionBaseView

class Project__Budget__Allocation__Edit__View(PermissionBaseView, UpdateView):
    # مدل ویو: از BudgetAllocation استفاده می‌کنیم که تخصیص بودجه به پروژه/زیرپروژه رو مدیریت می‌کنه
    model = BudgetAllocation
    # فرم: از فرم جدید BudgetAllocationForm استفاده می‌کنیم که برای BudgetAllocation طراحی شده
    form_class = BudgetAllocationForm
    # تمپلیت: همون تمپلیت قبلی که داده‌های تخصیص و سازمان رو نمایش می‌ده
    template_name = 'budgets/budget/project_budget_allocation_edit.html'

    def get_object(self, queryset=None):
        logger.debug(
            f"Attempting to get BudgetAllocation with pk={self.kwargs['pk']} for user={self.request.user}")
        try:
            allocation = BudgetAllocation.objects.get(pk=self.kwargs['pk'])
        except BudgetAllocation.DoesNotExist:
            logger.error(f"BudgetAllocation with pk={self.kwargs['pk']} does not exist")
            raise Http404(_("تخصیص موردنظر یافت نشد"))

        authorized_orgs = self.request.user.get_authorized_organizations()
        logger.debug(f"Authorized organizations: {list(authorized_orgs.values('id', 'name'))}")
        logger.debug(f"Allocation organization: {allocation.budget_allocation.organization}")
        if allocation.budget_allocation.organization not in authorized_orgs:
            logger.error(
                f"User {self.request.user} does not have access to organization {allocation.budget_allocation.organization} (ID: {allocation.budget_allocation.organization.id})")
            raise Http404(
                _("شما به سازمان این تخصیص ({} - {}) دسترسی ندارید").format(
                    allocation.budget_allocation.organization.id,
                    allocation.budget_allocation.organization.name
                )
            )

        if not allocation.budget_allocation.budget_period.is_active:
            logger.warning(f"Budget period {allocation.budget_allocation.budget_period.id} is inactive")
            messages.warning(self.request, _("دوره بودجه این تخصیص بسته شده است، اما می‌توانید ویرایش کنید."))

        logger.info(
            f"Successfully retrieved allocation👍💸 {allocation.id} for organization {allocation.budget_allocation.organization}")
        return allocation

    def get_form_kwargs(self):
        """
        ارسال پارامترهای اضافی به فرم.
        - user: برای ثبت کاربر ویرایش‌کننده.
        - organization_id: برای فیلتر کردن پروژه‌ها و زیرپروژه‌ها در فرم.
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        try:
            kwargs['organization_id'] = self.get_object().budget_allocation.organization.id
            logger.debug(f"Passing organization_id={kwargs['organization_id']} to form")
        except AttributeError as e:
            logger.error(f"Failed to get organization_id: {str(e)}")
            raise
        return kwargs

    def get_context_data(self, **kwargs):
        """
               ارسال داده‌های اضافی به تمپلیت برای نمایش خلاصه بودجه.
               - organization: برای نمایش نام سازمان و ریدایرکت‌ها.
               - total_org_budget: بودجه کل تخصیص‌شده به سازمان.
               - consumed_amount: مبلغ مصرف‌شده برای این تخصیص.
               - remaining_org_budget: بودجه باقی‌مانده.
               - allocation: خود تخصیص برای نمایش جزئیات.
        """
        context = super().get_context_data(**kwargs)
        allocation = self.get_object()
        organization = allocation.budget_allocation.organization
        budget_allocation = allocation.budget_allocation
        logger.debug(f"Preparing context for allocation {allocation.id}, organization {organization.name}")

        # محاسبه بودجه کل سازمان
        total_org_budget = budget_allocation.allocated_amount
        logger.debug(f"Total organization budget: {total_org_budget}")

        # پیدا کردن subproject‌های مرتبط با این تخصیص
        subprojects = SubProject.objects.filter(allocations=allocation)

        # محاسبه مبلغ مصرف‌شده برای این تخصیص
        consumed = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            allocation__project=allocation.project,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        returned = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            allocation__project=allocation.project,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        consumed_amount = consumed - returned
        logger.debug(f"Consumed: {consumed}, Returned: {returned}, Net consumed: {consumed_amount}")

        # محاسبه بودجه باقی‌مانده
        remaining_org_budget = (Decimal(total_org_budget) - Decimal(BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')) +
                                Decimal(BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')))
        logger.debug(f"Remaining organization budget: {remaining_org_budget}")

        context.update({
            'organization': organization,
            'total_org_budget': total_org_budget,
            'consumed_amount': consumed_amount,
            'remaining_org_budget': remaining_org_budget,
            'allocation': allocation,
            'subprojects': subprojects,
        })
        return context

    def validate_allocation_amount(self, allocation, new_amount):
        """
        اعتبارسنجی مبلغ تخصیص.
        - چک می‌کنه که مبلغ جدید از مبلغ مصرف‌شده کمتر نباشه.
        - چک می‌کنه که مبلغ جدید از بودجه باقی‌مانده بیشتر نباشه.
        - اگه خطایی رخ بده، ValidationError پرت می‌کنه.
        """
        logger.debug(f"Validating new amount {new_amount} for allocation {allocation.id}")
        budget_allocation = allocation.budget_allocation

        consumed = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            allocation__project=allocation.project,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        returned = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            allocation__project=allocation.project,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_consumed = consumed - returned
        logger.debug(f"Total consumed for validation: {total_consumed}")

        if new_amount < total_consumed:
            logger.warning(f"Validation failed: New amount {new_amount} is less than consumed {total_consumed}")
            raise ValidationError(
                f"مبلغ تخصیص ({new_amount:,.0f} ریال) نمی‌تواند کمتر از مبلغ مصرف‌شده ({total_consumed:,.0f} ریال) باشد."
            )

        remaining_budget = budget_allocation.allocated_amount - BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0') + BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        logger.debug(f"Remaining budget for validation: {remaining_budget}")

        if new_amount > remaining_budget:
            logger.warning(f"Validation failed: New amount {new_amount} exceeds remaining budget {remaining_budget}")
            raise ValidationError(
                f"مبلغ تخصیص ({new_amount:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) باشد."
            )

    def form_valid(self, form):
        """
        ذخیره فرم با اعتبارسنجی و پاسخ AJAX.
        - مبلغ جدید رو اعتبارسنجی می‌کنه.
        - تخصیص رو ذخیره می‌کنه و کاربر ویرایش‌کننده رو ثبت می‌کنه.
        - درصد باقی‌مانده رو محاسبه می‌کنه.
        - برای درخواست‌های AJAX پاسخ JSON برمی‌گردونه.
        - برای درخواست‌های معمولی پیام موفقیت نمایش می‌ده و ریدایرکت می‌کنه.
        """
        try:
            with transaction.atomic():
                old_amount = self.object.allocated_amount
                new_amount = form.cleaned_data['allocated_amount']
                logger.debug(f"Form valid, processing update for allocation {self.object.id}, old_amount={old_amount}, new_amount={new_amount}")

                # اعتبارسنجی مبلغ تخصیص
                self.validate_allocation_amount(self.object, new_amount)

                allocation = form.save(commit=False)
                allocation.modified_by = self.request.user
                allocation.save()
                logger.info(f"Allocation {allocation.id} updated successfully by user {self.request.user}")

                # محاسبه درصد باقی‌مانده
                consumed = BudgetTransaction.objects.filter(
                    allocation=allocation.budget_allocation,
                    project=allocation.project,
                    subproject=allocation.subproject,
                    transaction_type='CONSUMPTION'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                returned = BudgetTransaction.objects.filter(
                    allocation=allocation.budget_allocation,
                    project=allocation.project,
                    subproject=allocation.subproject,
                    transaction_type='RETURN'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                remaining = allocation.allocated_amount - consumed + returned
                remaining_percent = (
                    (Decimal(remaining )/ Decimal(allocation.allocated_amount * 100)) if allocation.allocated_amount > 0 else Decimal('0')
                )
                logger.debug(f"Remaining amount: {remaining}, Remaining percent: {remaining_percent}")

                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    logger.debug("Returning AJAX response")
                    return JsonResponse({
                        'success': True,
                        'allocated_amount': f"{allocation.allocated_amount:,.0f}",
                        'remaining_percent': f"{remaining_percent:.1f}",
                        'is_active': allocation.is_active,
                        'organization_id': allocation.budget_allocation.organization.id
                    })

                messages.success(self.request, _("تخصیص بودجه با موفقیت ویرایش شد"))
                logger.debug("Redirecting to success URL")
                return super().form_valid(form)

        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            form.add_error('allocated_amount', str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Unexpected error in form_valid: {str(e)}", exc_info=True)
            form.add_error(None, _("خطایی در ذخیره تخصیص رخ داد."))
            return self.form_invalid(form)

    def form_invalid(self, form):
        """
        مدیریت خطاهای فرم.
        - برای درخواست‌های AJAX خطاها رو به‌صورت JSON برمی‌گردونه.
        - برای درخواست‌های معمولی پیام خطا نمایش می‌ده و فرم رو رندر می‌کنه.
        """
        logger.error(f"Form invalid, errors: {form.errors}")
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = {field: errors for field, errors in form.errors.items()}
            logger.debug(f"Returning AJAX error response: {errors}")
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)

        messages.error(self.request, _("لطفاً خطاهای فرم را بررسی کنید"))
        return super().form_invalid(form)

    def get_success_url(self):
        """
        URL ریدایرکت پس از ذخیره موفق.
        - به لیست تخصیص‌ها با organization_id درست هدایت می‌کنه.
        """
        try:
            organization_id = self.object.budget_allocation.organization.id
            logger.debug(f"Redirecting to project_budget_allocation_list with organization_id={organization_id}")
            return reverse_lazy('project_budget_allocation_list', kwargs={'organization_id': organization_id})
        except AttributeError as e:
            logger.error(f"Failed to get organization_id for redirect: {str(e)}")
            return reverse_lazy('organization_list')

    def dispatch(self, request, *args, **kwargs):
        """
        مدیریت دسترسی و خطاها.
        - تخصیص رو با get_object می‌گیره.
        - اگه خطایی رخ بده (مثل تخصیص ناموجود یا عدم دسترسی)، ریدایرکت به organization_list می‌کنه.
        """
        logger.debug(f"Dispatching request for allocation edit, pk={self.kwargs.get('pk')}, user={self.request.user}")
        try:
            allocation = self.get_object()
            logger.info(f"Accessing edit view for allocation {allocation.id}")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error accessing allocation: {str(e)}", exc_info=True)
            messages.error(request, _("تخصیص موردنظر یافت نشد یا شما دسترسی ندارید"))
            return redirect('organization_list')