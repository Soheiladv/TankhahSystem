from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import redirect
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from budgets.get_budget_details import get_budget_details
from budgets.models import BudgetTransaction, BudgetAllocation
from budgets.BudgetReturn.forms_BudgetReturm import BudgetReturnForm
from budgets.budget_calculations import (get_project_remaining_budget,
                                         get_project_remaining_budget,
                                         get_project_total_budget,
                                         get_project_used_budget,
                                         check_budget_status, get_organization_budget
                                         )
from core.PermissionBase import PermissionBaseView
import logging
logger = logging.getLogger(__name__)

from django.core.cache import cache

""""گزارش‌گیری بودجه برگشتی:"""
from budgets.models import BudgetHistory,   BudgetTransaction
def get_returned_budgets(budget_period):
    from django.contrib.contenttypes.models import ContentType
    from budgets.models import  BudgetAllocation
    return BudgetHistory.objects.filter(
        content_type=ContentType.objects.get_for_model(BudgetAllocation),
        action='RETURN',
        content_object__budget_period=budget_period
    ).values('amount', 'details', 'created_at', 'created_by__username')


class gemini_BudgetReturnView(PermissionBaseView, CreateView):
    """
    نمای ثبت تراکنش بازگشت بودجه.

    این View به کاربران اجازه می‌دهد تا مبلغی را از یک تخصیص بودجه مشخص بازگردانند.
    شامل بررسی‌های امنیتی، اعتبارسنجی و کشینگ برای بهبود عملکرد است.
    """
    model = BudgetTransaction
    form_class = BudgetReturnForm
    template_name = 'budgets/budget_return_form.html'
    # کد دسترسی مورد نیاز برای این عملیات
    permission_codenames = ['budgets.BudgetTransaction_add']
    # بررسی می‌کند که آیا کاربر به سازمان مربوطه دسترسی دارد یا خیر
    check_organization = True
    # URL موفقیت‌آمیز پس از ثبت فرم (اینجا با استفاده از get_success_url تعیین می‌شود)
    success_url = None

    def get_allocation(self):
        """
        شیء تخصیص بودجه (BudgetAllocation) را بر اساس allocation_id از URL بازیابی می‌کند.
        دسترسی کاربر به سازمان مربوطه را بررسی می‌کند.
        در صورت عدم وجود تخصیص یا عدم دسترسی، Http404 یا PermissionDenied صادر می‌کند.
        """
        try:
            # از select_related برای بهینه‌سازی کوئری و جلوگیری از N+1 problem استفاده می‌شود
            allocation = BudgetAllocation.objects.select_related(
                'budget_period', 'organization', 'project', 'subproject', 'created_by'
            ).get(pk=self.kwargs['allocation_id'], is_active=True)

            # بررسی دسترسی کاربر به سازمان
            user_organizations = self.request.user.get_authorized_organizations()
            if not user_organizations.filter(pk=allocation.organization.pk).exists():
                logger.warning(
                    f"User {self.request.user.username} attempted to access allocation "
                    f"{self.kwargs['allocation_id']} without organization permission."
                )
                raise PermissionDenied(_('متاسفانه دسترسی مجاز ندارید.'))
            return allocation
        except BudgetAllocation.DoesNotExist:
            logger.error(f"Allocation {self.kwargs['allocation_id']} does not exist or is inactive.")
            raise Http404(_('تخصیص بودجه مورد نظر یافت نشد یا غیرفعال است.'))

    def dispatch(self, request, *args, **kwargs):
        """
        این متد قبل از فراخوانی هر متد دیگر (مانند get یا post) اجرا می‌شود.
        مسئول بررسی اولیه وجود تخصیص و دسترسی به آن است.
        """
        try:
            # تلاش برای بازیابی تخصیص. اگر ناموفق باشد، Exception صادر می‌شود.
            # نیازی به ذخیره نتیجه نیست، فقط بررسی می‌کنیم که Exception صادر نشود.
            self.get_allocation()
        except (Http404, PermissionDenied) as e:
            messages.error(self.request, str(e))
            # در صورت بروز خطا، کاربر به لیست تخصیص‌ها هدایت می‌شود.
            return redirect('project_budget_allocation_list')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        آرگومان‌های اضافی را برای فرم (allocation و user) فراهم می‌کند.
        """
        kwargs = super().get_form_kwargs()
        kwargs['allocation'] = self.get_allocation()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """
        اطلاعات اضافی مورد نیاز برای رندرینگ تمپلیت را فراهم می‌کند.
        از کش برای بهینه‌سازی دریافت اطلاعات بودجه استفاده می‌کند.
        """
        context = super().get_context_data(**kwargs)
        allocation = self.get_allocation()
        project = allocation.project
        organization = allocation.organization
        budget_period = allocation.budget_period

        # استفاده از کش برای جلوگیری از کوئری‌های مکرر پایگاه داده
        cache_key = f"budget_context_{allocation.pk}"
        cached_context = cache.get(cache_key)

        if cached_context:
            context.update(cached_context)
            logger.debug(f"Budget context loaded from cache for allocation ID: {allocation.pk}")
        else:
            # فراخوانی توابع مربوط به جزئیات بودجه
            context_data = {
                'allocation': allocation,
                'project': project,
                'organization': organization,
                'total_budget': get_project_total_budget(project) if project else 0,
                'used_budget': get_project_used_budget(project) if project else 0,
                'remaining_budget': get_project_remaining_budget(project) if project else 0,
                'org_budget': get_organization_budget(organization),
                'budget_details': get_budget_details(entity=project) if project else {},
                'budget_status': check_budget_status(budget_period)[0] if budget_period else '',
                'budget_status_message': check_budget_status(budget_period)[1] if budget_period else '',
            }
            # ذخیره در کش برای 5 دقیقه (300 ثانیه)
            cache.set(cache_key, context_data, timeout=300)
            context.update(context_data)
            logger.debug(f"Budget context generated and cached for allocation ID: {allocation.pk}")

        return context

    def form_valid(self, form):
        """
        زمانی که فرم ارسالی معتبر است فراخوانی می‌شود.
        تراکنش را ذخیره کرده و پیام موفقیت نمایش می‌دهد.
        """
        try:
            instance = form.save()
            messages.success(self.request, _("تراکنش بازگشت بودجه با موفقیت ثبت شد."))
            logger.info(
                f"User {self.request.user.username} created return transaction "
                f"for allocation {self.get_allocation().id} with amount {instance.amount:,.0f}."
            )
            # فراخوانی متد والد برای هدایت به success_url
            return super().form_valid(form)
        except ValidationError as e:
            # در صورت بروز خطاهای اعتبارسنجی در save فرم، آن را به فرم اضافه می‌کند
            logger.error(
                f"Error creating return transaction for allocation {self.get_allocation().id}: {str(e)}"
            )
            form.add_error(None, str(e))
            # بازگرداندن فرم نامعتبر برای نمایش خطاها به کاربر
            return self.form_invalid(form)

    def get_success_url(self):
        """
        URL هدایت پس از ثبت موفقیت‌آمیز فرم را برمی‌گرداند.
        """
        return reverse_lazy(
            'project_budget_allocation_detail',
            kwargs={'pk': self.kwargs['allocation_id']}
        )

    def _get_organization_from_object(self, obj):
        """
        متدی کمکی برای کلاس PermissionBaseView برای استخراج سازمان از شیء.
        """
        return obj.organization
class gemini___BudgetReturnView(PermissionBaseView, CreateView):
    """
    نمای ثبت تراکنش بازگشت بودجه.

    این View به کاربران اجازه می‌دهد تا مبلغی را از یک تخصیص بودجه مشخص بازگردانند.
    شامل بررسی‌های امنیتی، اعتبارسنجی و کشینگ برای بهبود عملکرد است.
    """
    model = BudgetTransaction
    form_class = BudgetReturnForm
    template_name = 'budgets/budget_return_form.html'
    # کد دسترسی مورد نیاز برای این عملیات
    permission_codenames = ['budgets.BudgetTransaction_add']
    # بررسی می‌کند که آیا کاربر به سازمان مربوطه دسترسی دارد یا خیر
    check_organization = True
    # URL موفقیت‌آمیز پس از ثبت فرم (اینجا با استفاده از get_success_url تعیین می‌شود)
    success_url = None

    def get_allocation(self):
        """
        شیء تخصیص بودجه (BudgetAllocation) را بر اساس allocation_id از URL بازیابی می‌کند.
        دسترسی کاربر به سازمان مربوطه را بررسی می‌کند.
        در صورت عدم وجود تخصیص یا عدم دسترسی، Http404 یا PermissionDenied صادر می‌کند.
        """
        try:
            # از select_related برای بهینه‌سازی کوئری و جلوگیری از N+1 problem استفاده می‌شود
            allocation = BudgetAllocation.objects.select_related(
                'budget_period', 'organization', 'project', 'subproject', 'created_by'
            ).get(pk=self.kwargs['allocation_id'], is_active=True)

            # بررسی دسترسی کاربر به سازمان
            user_organizations = self.request.user.get_authorized_organizations()
            if not user_organizations.filter(pk=allocation.organization.pk).exists():
                logger.warning(
                    f"User {self.request.user.username} attempted to access allocation "
                    f"{self.kwargs['allocation_id']} without organization permission."
                )
                raise PermissionDenied(_('متاسفانه دسترسی مجاز ندارید.'))
            return allocation
        except BudgetAllocation.DoesNotExist:
            logger.error(f"Allocation {self.kwargs['allocation_id']} does not exist or is inactive.")
            raise Http404(_('تخصیص بودجه مورد نظر یافت نشد یا غیرفعال است.'))

    def dispatch(self, request, *args, **kwargs):
        """
        این متد قبل از فراخوانی هر متد دیگر (مانند get یا post) اجرا می‌شود.
        مسئول بررسی اولیه وجود تخصیص و دسترسی به آن است.
        """
        try:
            # تلاش برای بازیابی تخصیص. اگر ناموفق باشد، Exception صادر می‌شود.
            # نیازی به ذخیره نتیجه نیست، فقط بررسی می‌کنیم که Exception صادر نشود.
            self.get_allocation()
        except (Http404, PermissionDenied) as e:
            messages.error(self.request, str(e))
            # در صورت بروز خطا، کاربر به لیست تخصیص‌ها هدایت می‌شود.
            return redirect('project_budget_allocation_list')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        آرگومان‌های اضافی را برای فرم (allocation و user) فراهم می‌کند.
        """
        kwargs = super().get_form_kwargs()
        kwargs['allocation'] = self.get_allocation()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """
        اطلاعات اضافی مورد نیاز برای رندرینگ تمپلیت را فراهم می‌کند.
        از کش برای بهینه‌سازی دریافت اطلاعات بودجه استفاده می‌کند.
        """
        context = super().get_context_data(**kwargs)
        allocation = self.get_allocation()
        project = allocation.project
        organization = allocation.organization
        budget_period = allocation.budget_period

        # استفاده از کش برای جلوگیری از کوئری‌های مکرر پایگاه داده
        cache_key = f"budget_context_{allocation.pk}"
        cached_context = cache.get(cache_key)

        if cached_context:
            context.update(cached_context)
            logger.debug(f"Budget context loaded from cache for allocation ID: {allocation.pk}")
        else:
            # فراخوانی توابع مربوط به جزئیات بودجه
            from budgets.get_budget_details import get_budget_details
            context_data = {
                'allocation': allocation,
                'project': project,
                'organization': organization,
                'total_budget': get_project_total_budget(project) if project else 0,
                'used_budget': get_project_used_budget(project) if project else 0,
                'remaining_budget': get_project_remaining_budget(project) if project else 0,
                'org_budget': get_organization_budget(organization),
                'budget_details': get_budget_details(entity=project) if project else {},
                'budget_status': check_budget_status(budget_period)[0] if budget_period else '',
                'budget_status_message': check_budget_status(budget_period)[1] if budget_period else '',
            }
            # ذخیره در کش برای 5 دقیقه (300 ثانیه)
            cache.set(cache_key, context_data, timeout=300)
            context.update(context_data)
            logger.debug(f"Budget context generated and cached for allocation ID: {allocation.pk}")

        return context

    def form_valid(self, form):
        """
        زمانی که فرم ارسالی معتبر است فراخوانی می‌شود.
        تراکنش را ذخیره کرده و پیام موفقیت نمایش می‌دهد.
        """
        try:
            instance = form.save()
            messages.success(self.request, _("تراکنش بازگشت بودجه با موفقیت ثبت شد."))
            logger.info(
                f"User {self.request.user.username} created return transaction "
                f"for allocation {self.get_allocation().id} with amount {instance.amount:,.0f}."
            )
            # فراخوانی متد والد برای هدایت به success_url
            return super().form_valid(form)
        except ValidationError as e:
            # در صورت بروز خطاهای اعتبارسنجی در save فرم، آن را به فرم اضافه می‌کند
            logger.error(
                f"Error creating return transaction for allocation {self.get_allocation().id}: {str(e)}"
            )
            form.add_error(None, str(e))
            # بازگرداندن فرم نامعتبر برای نمایش خطاها به کاربر
            return self.form_invalid(form)

    def get_success_url(self):
        """
        URL هدایت پس از ثبت موفقیت‌آمیز فرم را برمی‌گرداند.
        """
        return reverse_lazy(
            'project_budget_allocation_detail',
            kwargs={'pk': self.kwargs['allocation_id']}
        )

    def _get_organization_from_object(self, obj):
        """
        متدی کمکی برای کلاس PermissionBaseView برای استخراج سازمان از شیء.
        """
        return obj.organization

class BudgetReturnView(PermissionBaseView, CreateView):
    model = BudgetTransaction
    form_class = BudgetReturnForm
    template_name = 'budgets/budget_return_form.html'
    permission_codenames = ['budgets.BudgetTransaction_add']
    check_organization = True
    success_url = None

    def get_allocation(self):
        try:
            allocation = BudgetAllocation.objects.select_related(
                'budget_period', 'organization', 'project', 'subproject', 'created_by'
            ).get(pk=self.kwargs['allocation_id'], is_active=True)
            user_organizations = self.request.user.get_authorized_organizations()
            if not user_organizations.filter(pk=allocation.organization.pk).exists():
                logger.warning(
                    f"User {self.request.user.username} attempted to access allocation "
                    f"{self.kwargs['allocation_id']} without organization permission"
                )
                raise PermissionDenied(_('متاسفانه دسترسی مجاز ندارید'))
            return allocation
        except BudgetAllocation.DoesNotExist:
            logger.error(f"Allocation {self.kwargs['allocation_id']} does not exist or is inactive")
            raise Http404(_('تخصیص بودجه مورد نظر یافت نشد یا غیرفعال است.'))

    def dispatch(self, request, *args, **kwargs):
        try:
            if not self.get_allocation():
                messages.error(self.request, _('تخصیص بودجه مورد نظر یافت نشد یا غیرفعال است.'))
                return redirect('project_budget_allocation_list')
        except (Http404, PermissionDenied) as e:
            messages.error(self.request, str(e))
            return redirect('project_budget_allocation_list')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['allocation'] = self.get_allocation()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation = self.get_allocation()
        project = allocation.project
        organization = allocation.organization
        budget_period = allocation.budget_period

        # کش برای اطلاعات بودجه
        cache_key = f"budget_context_{allocation.pk}"
        cached_context = cache.get(cache_key)
        if cached_context:
            context.update(cached_context)
        else:

            from budgets.get_budget_details import get_budget_details
            context_data = {
                'allocation': allocation,
                'project': project,
                'organization': organization,
                'total_budget': get_project_total_budget(project) if project else 0,
                'used_budget': get_project_used_budget(project) if project else 0,
                'remaining_budget': get_project_remaining_budget(project) if project else 0,
                'org_budget': get_organization_budget(organization),
                'budget_details': get_budget_details(entity=project) if project else {},
                'budget_status': check_budget_status(budget_period)[0] if budget_period else '',
                'budget_status_message': check_budget_status(budget_period)[1] if budget_period else '',
            }

            cache.set(cache_key, context_data, timeout=300)
            context.update(context_data)

        return context

    def form_valid(self, form):
        try:
            instance = form.save()
            messages.success(self.request, _("تراکنش بازگشت بودجه با موفقیت ثبت شد."))
            logger.info(
                f"User {self.request.user.username} created return transaction "
                f"for allocation {self.get_allocation().id} with amount {instance.amount:,.0f}"
            )
            return super().form_valid(form)
        except ValidationError as e:
            logger.error(
                f"Error creating return transaction for allocation {self.get_allocation().id}: {str(e)}"
            )
            form.add_error(None, str(e))
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy(
            'project_budget_allocation_detail',
            kwargs={'pk': self.kwargs['allocation_id']}
        )

    def _get_organization_from_object(self, obj):
        return obj.organization
