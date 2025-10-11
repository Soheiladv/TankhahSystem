# ===== IMPORTS & DEPENDENCIES =====
from django.http import JsonResponse
import logging
from notificationApp.utils import send_notification

logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.views.generic import CreateView
from tankhah.Tankhah.forms_tankhah import TankhahForm
from accounts.models import CustomUser
from tankhah.models import Tankhah
from core.views import PermissionBaseView
from django.utils.translation import gettext_lazy as _
# -------
"""به‌روزرسانی پروژه‌ها بر اساس سازمان"""
from django.views.decorators.http import require_GET


# tankhah/views.py
@require_GET
def get_projects(request):
    org_id = request.GET.get('org_id')
    logger.debug(f"Request received for get_projects with org_id: {org_id}")

    if not org_id:
        logger.warning("No org_id provided in get_projects request")
        return JsonResponse({'projects': []})

    try:
        projects = Project.objects.filter(
            organizations__id=org_id,
            is_active=True
        ).distinct().order_by('name').values('id', 'name')
        projects_list = list(projects)
        logger.debug(f"Found {len(projects_list)} projects for org_id: {org_id}")
        return JsonResponse({'projects': projects_list})
    except Exception as e:
        logger.error(f"Error fetching projects for org_id {org_id}: {str(e)}")
        return JsonResponse({'projects': []}, status=500)


# tankhah/view_folder_tankhah/view_tankhah.py (یا هرجایی که این ویو قرار دارد)

import logging
from django.urls import reverse_lazy, reverse
from django.shortcuts import redirect
from django.db import transaction
from django.contrib import messages
from django.views.generic import CreateView
from django.core.exceptions import ValidationError  # برای مدیریت خطاهای مدل

from core.PermissionBase import PermissionBaseView  # یا LoginRequiredMixin
from tankhah.models import Tankhah
from tankhah.Tankhah.forms_tankhah import TankhahForm  # فرمی که در بالا تعریف کردیم
from core.models import Status, Organization, Project, SubProject
from budgets.models import BudgetAllocation
# from accounts.models import CustomUser # اگر برای notify لازم است
# از django.contrib.auth import get_user_model
# User = get_user_model()

# توابع محاسباتی بودجه (اگر در context برای نمایش اطلاعات بودجه استفاده می‌شوند)
from budgets.budget_calculations import get_project_total_budget, get_project_remaining_budget, \
    get_subproject_remaining_budget, get_subproject_total_budget
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from decimal import Decimal
import logging

from tankhah.models import Tankhah, Factor, ApprovalLog
from tankhah.forms import TankhahStatusForm
from core.views import PermissionBaseView
# معماری جدید: مدل‌ها، فرم‌ها و سرویس‌ها را وارد می‌کنیم
from core.PermissionBase import PermissionBaseView
from .services import TankhahCreationService, TankhahCreationError

# تنظیم لاگر برای این ماژول
logger = logging.getLogger("tankhah_views")


# ===== API ROUTES / VIEWS =====

class TankhahCreateView(PermissionBaseView, CreateView):
    """
    ویوی نهایی و کامل برای ایجاد تنخواه جدید، بر اساس معماری سرویس-محور.
    این ویو فقط مسئول هماهنگی بین درخواست کاربر، فرم و سرویس است.
    """
    # --- پیکربندی‌های اصلی کلاس ---
    model = Tankhah
    form_class = TankhahForm
    template_name = 'tankhah/Tankhah_form.html'
    permission_codename  = ['tankhah.Tankhah_add']
    # --------------------------------------------------------------------------
    # ۱. متدهای آماده‌سازی فرم و زمینه (Context)
    # --------------------------------------------------------------------------
    def get_form_kwargs(self):
        """
        این متد پارامترهای اضافی را به __init__ فرم (`TankhahForm`) ارسال می‌کند.
        ما از این متد برای پاس دادن کاربر فعلی به فرم استفاده می‌کنیم.
        """
        # کامنت فارسی: ابتدا پارامترهای پیش‌فرض را از کلاس والد می‌گیریم.
        logger.debug(f"[TankhahCreateView] get_form_kwargs: Preparing kwargs for form initialization.")
        kwargs = super().get_form_kwargs()

        # کامنت فارسی: کاربر فعلی را به دیکشنری kwargs اضافه می‌کنیم تا در فرم در دسترس باشد.
        kwargs['user'] = self.request.user
        logger.debug(f"[TankhahCreateView] get_form_kwargs: Added user '{self.request.user.username}' to kwargs.")
        return kwargs
    def get_initial(self):
        """
        این متد فرم را با مقادیر اولیه از پارامترهای URL (GET) پر می‌کند.
        این کار تجربه کاربری را بهبود می‌بخشد، مثلا وقتی از صفحه یک پروژه خاص می‌آییم.
        """
        # کامنت فارسی: ابتدا مقادیر اولیه پیش‌فرض را از کلاس والد می‌گیریم.
        logger.debug(f"[TankhahCreateView] get_initial: Reading initial data from GET parameters: {self.request.GET}")
        initial = super().get_initial()

        # کامنت فارسی: پارامترهای budget_allocation_id و project_id را از URL می‌خوانیم.
        budget_allocation_id = self.request.GET.get('budget_allocation_id')
        project_id = self.request.GET.get('project_id')

        if budget_allocation_id:
            # کامنت فارسی: اگر ID تخصیص بودجه در URL بود، سعی می‌کنیم اطلاعات کامل آن را پیدا کرده و فرم را پر کنیم.
            try:
                ba = BudgetAllocation.objects.select_related('organization', 'project', 'subproject').get(
                    pk=budget_allocation_id)
                initial['organization'] = ba.organization
                initial['project'] = ba.project
                initial['subproject'] = ba.subproject
                logger.info(f"Form initialized with data from BudgetAllocation PK {budget_allocation_id}.")
            except (ValueError, BudgetAllocation.DoesNotExist):
                logger.warning(f"BudgetAllocation with ID '{budget_allocation_id}' from GET params not found.")

        elif project_id:
            # کامنت فارسی: اگر فقط ID پروژه در URL بود، پروژه و سازمان مرتبط با آن را در فرم قرار می‌دهیم.
            try:
                project = Project.objects.prefetch_related('organizations').get(pk=project_id)
                initial['project'] = project
                if project.organizations.exists():
                    initial['organization'] = project.organizations.first()
                logger.info(f"Form initialized with data from Project PK {project_id}.")
            except (ValueError, Project.DoesNotExist):
                logger.warning(f"Project with ID '{project_id}' from GET params not found.")

        return initial
    def get_context_data(self, **kwargs):
        """
        این متد داده‌های لازم برای تمپلیت (فایل HTML) را آماده می‌کند.
        مانند عنوان صفحه و URL های مورد نیاز برای AJAX.
        """
        # کامنت فارسی: ابتدا context پیش‌فرض را از کلاس والد می‌گیریم.
        logger.debug(f"[TankhahCreateView] get_context_data: Preparing context for template.")
        context = super().get_context_data(**kwargs)

        # کامنت فارسی: عنوان صفحه و URL های AJAX را به context اضافه می‌کنیم.
        context['title'] = _('ایجاد تنخواه جدید')
        context['load_projects_url'] = reverse_lazy('ajax_load_projects')
        context['load_subprojects_url'] = reverse_lazy('ajax_load_subprojects')

        logger.debug(f"[TankhahCreateView] get_context_data: Context prepared successfully.")
        return context
    # --------------------------------------------------------------------------
    # ۲. متدهای مدیریت ارسال فرم (POST Request)
    # -------------------------------------------------------------------------
    def form_valid(self, form):
        """
        این متد قلب تپنده ویو است و تنها زمانی اجرا می‌شود که فرم معتبر باشد.
        تمام منطق کسب‌وکار به کلاس سرویس منتقل شده است.
        """
        # کامنت فارسی: داده‌های تمیز شده و اعتبارسنجی شده را از فرم استخراج می‌کنیم.
        cleaned_data = form.cleaned_data
        logger.info(
            f"[TankhahCreateView] form_valid: Form is valid for user '{self.request.user.username}'. Cleaned data: {cleaned_data}")

        # کامنت فارسی: یک نمونه از کلاس سرویس را با داده‌های فرم و کاربر فعلی می‌سازیم.
        # ** به جای ارسال kwargs['user'] در get_form_kwargs به فرم، می‌توانیم مستقیم اینجا استفاده کنیم
        service = TankhahCreationService(user=self.request.user, **cleaned_data)

        try:
            # کامنت فارسی: متد execute سرویس را فراخوانی می‌کنیم. این متد تمام کارها را انجام می‌دهد.
            logger.debug("Executing TankhahCreationService...")
            self.object = service.execute()

            # کامنت فارسی: اگر سرویس با موفقیت اجرا شد، پیام موفقیت را نمایش داده و کاربر را هدایت می‌کنیم.
            logger.info(f"Tankhah {self.object.number} (PK: {self.object.pk}) created successfully by service.")
            messages.success(self.request, _(f'تنخواه "{self.object.number}" با موفقیت ایجاد شد.'))
            return redirect(self.get_success_url())

        except TankhahCreationError as e:
            # کامنت فارسی: اگر سرویس یک خطای کسب‌وکار (قابل پیش‌بینی) برگرداند، آن را به کاربر نمایش می‌دهیم.
            logger.warning(f"Business logic validation failed during service execution: {e}")
            form.add_error(None, str(e))
            return self.form_invalid(form)

        except Exception as e:
            # کامنت فارسی: اگر یک خطای غیرمنتظره رخ دهد، آن را لاگ کرده و یک پیام عمومی به کاربر نمایش می‌دهیم.
            logger.error(f"Unexpected error during TankhahCreationService execution: {e}", exc_info=True)
            messages.error(self.request, _("یک خطای پیش‌بینی نشده در سیستم رخ داد. لطفاً با پشتیبانی تماس بگیرید."))
            return self.form_invalid(form)
    def form_invalid(self, form):
        """
        این متد زمانی اجرا می‌شود که فرم نامعتبر باشد یا خطایی در form_valid رخ دهد.
        """
        # کامنت فارسی: خطاهای فرم را برای دیباگ کردن لاگ می‌کنیم.
        logger.warning(
            f"[TankhahCreateView] form_invalid: Form submission failed for user '{self.request.user.username}'. Errors: {form.errors.as_json()}")

        # کامنت فارسی: یک پیام کلی خطا به کاربر نمایش می‌دهیم.
        messages.error(self.request, _('فرم ارسال شده دارای خطا است. لطفاً موارد مشخص شده را اصلاح نمایید.'))

        # کامنت فارسی: صفحه را دوباره با فرم پر شده و خطاهای مشخص شده رندر می‌کنیم.
        return super().form_invalid(form)
    # --------------------------------------------------------------------------
    # ۳. متد تعیین URL پس از موفقیت
    # --------------------------------------------------------------------------
    def get_success_url(self):
        """
        پس از ایجاد موفق تنخواه، کاربر به صفحه جزئیات همان تنخواه هدایت می‌شود.
        """
        # کامنت فارسی: اگر آبجکت تنخواه (self.object) با موفقیت ایجاد شده باشد، URL جزئیات آن را برمی‌گردانیم.
        if hasattr(self, 'object') and self.object:
            logger.debug(f"Redirecting to detail page for new Tankhah PK {self.object.pk}.")
            return reverse('tankhah_detail', kwargs={'pk': self.object.pk})

        # کامنت فارسی: در حالت پیش‌فرض (که نباید اتفاق بیفتد)، به لیست تنخواه‌ها برمی‌گردیم.
        logger.warning("get_success_url called but self.object is not set. Redirecting to list view.")
        return reverse_lazy('tankhah_list')
