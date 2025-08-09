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

# -------
class old__TankhahCreateView(PermissionBaseView, CreateView):
    model = Tankhah
    form_class = TankhahForm
    template_name = 'tankhah/Tankhah_form.html'
    success_url = reverse_lazy('tankhah_list')
    context_object_name = 'Tankhah'
    permission_codenames = ['tankhah.Tankhah_add']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    check_organization = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_invalid(self, form):
        logger.info(f"فرم نامعتبر است. خطاها: {form.errors}")
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید.'))
        return super().form_invalid(form)

    def generate_tankhah_number(self, tankhah):
        date_str = tankhah.date.strftime('%Y%m%d')
        org_code = tankhah.organization.code[:6]
        proj_code = tankhah.project.code[:6]
        count = Tankhah.objects.filter(date=tankhah.date).count() + 1
        return f"تنخواه-{date_str}-{org_code}-{proj_code}-{count:03d}"

    def form_valid(self, form):
        logger.info(f"فرم معتبر است. داده‌ها: {form.cleaned_data}")
        with transaction.atomic():
            self.object = form.save(commit=False)
            # ثبت تنخواه
            tankhah = form.save(commit=False)
            tankhah.created_by = self.request.user
            tankhah.number = self.generate_tankhah_number(tankhah)
            # پیدا کردن تخصیص بودجه
            project = form.cleaned_data['project']
            subproject = form.cleaned_data.get('subproject')
            organization = form.cleaned_data['organization']
            from budgets.models import BudgetAllocation
            try:
                project_allocation = BudgetAllocation.objects.filter(
                    project=project,
                    subproject=subproject if subproject else None,
                    budget_allocation__is_active=True,
                    budget_allocation__organization=organization
                ).select_related('budget_allocation').first()

                if not project_allocation:
                    logger.error(
                        f"No active budget allocation found for project {project.id}, org {form.cleaned_data['organization'].id}")
                    form.add_error(None, _("تخصیص بودجه فعالی برای این پروژه/زیرپروژه یافت نشد."))
                    return self.form_invalid(form)

                # بررسی بودجه باقی‌مانده
                remaining_budget = project_allocation.get_remaining_amount()
                if tankhah.amount > remaining_budget:
                    logger.error(
                        f"Insufficient remaining budget: {remaining_budget} for tankhah amount: {tankhah.amount}")
                    form.add_error('amount', _("مبلغ تنخواه بیشتر از بودجه باقی‌مانده است."))
                    return self.form_invalid(form)

                tankhah.budget_allocation = project_allocation.budget_allocation

                # تنظیم مرحله اولیه جریان کاری
                from core.models import WorkflowStage
                initial_stage = WorkflowStage.objects.order_by('order').first()
                if not initial_stage:
                    logger.error("No initial workflow stage defined")
                    form.add_error(None, _("مرحله اولیه جریان کاری تعریف نشده است."))
                    return self.form_invalid(form)
                tankhah.current_stage = initial_stage
                tankhah.status = 'DRAFT'  # ابتدا DRAFT، بعداً در جریان کاری PAID شود
                tankhah.save()

            except Exception as e:
                logger.error(f"Error creating tankhah {tankhah.number}: {str(e)}")
                form.add_error(None, f"خطا در ثبت تنخواه: {str(e)}")
                return self.form_invalid(form)

            approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=initial_stage)
            if approvers.exists():
                send_notification(self.request.user, users=None, posts=None,  verb='تنخواه برای تأیید آماده است',  description=approvers, target=self.object,
                                  entity_type=None, priority='MEDIUM'  )
                logger.info(f"Notification sent to {approvers.count()} approvers for stage {initial_stage.name}")

        messages.success(self.request, _('تنخواه با موفقیت ثبت شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد تنخواه جدید')

        # مدیریت بودجه‌ها برای درخواست‌های GET و POST
        project = None
        subproject = None

        # بررسی درخواست POST
        if self.request.method == 'POST' and 'project' in self.request.POST:
            from core.models import SubProject,Project
            try:
                project_id = int(self.request.POST.get('project'))
                project = Project.objects.get(id=project_id)
                if 'subproject' in self.request.POST and self.request.POST.get('subproject'):
                    subproject_id = int(self.request.POST.get('subproject'))
                    subproject = SubProject.objects.get(id=subproject_id)
            except (ValueError, Project.DoesNotExist, SubProject.DoesNotExist) as e:
                logger.error(f"Error fetching project/subproject: {str(e)}")
                project = None
                subproject = None

        # برای حالت ویرایش یا بارگذاری اولیه با داده‌های فرم
        elif self.request.method == 'GET' and self.form_class and hasattr(self, 'object') and self.object:
            project = self.object.project
            subproject = self.object.subproject

        # تنظیم سازمان‌های مجاز در context
        context['organizations'] = Organization.objects.filter(
            org_type__is_budget_allocatable=True,
            is_active=True
        ).order_by('name')

        # تنظیم مقادیر بودجه
        if project:
            total_budget = get_project_total_budget(project)
            remaining_budget = get_project_remaining_budget(project)
            context['total_budget'] = total_budget
            context['remaining_budget'] = remaining_budget
            context['project_budget_percentage'] = (
                (remaining_budget / total_budget * 100) if total_budget > 0 else Decimal('0')
            )
            logger.debug(f"Project {project.id} budget: total={total_budget}, remaining={remaining_budget}")
        else:
            context['total_budget'] = Decimal('0')
            context['remaining_budget'] = Decimal('0')
            context['project_budget_percentage'] = Decimal('0')

        if subproject:
            subproject_total = get_subproject_total_budget(subproject)
            subproject_remaining = get_subproject_remaining_budget(subproject)
            context['subproject_total_budget'] = subproject_total
            context['subproject_remaining_budget'] = subproject_remaining
            context['subproject_budget_percentage'] = (
                (subproject_remaining / subproject_total * 100) if subproject_total > 0 else Decimal('0')
            )
            logger.debug(
                f"Subproject {subproject.id} budget: total={subproject_total}, remaining={subproject_remaining}")
        else:
            context['subproject_total_budget'] = Decimal('0')
            context['subproject_remaining_budget'] = Decimal('0')
            context['subproject_budget_percentage'] = Decimal('0')

        return context

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return super().handle_no_permission()


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
from core.models import WorkflowStage, Organization, Project, SubProject
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
from budgets.budget_calculations import (
    get_tankhah_total_budget,
    get_tankhah_used_budget,
    get_tankhah_remaining_budget,
    get_project_total_budget,
    get_project_remaining_budget,
    check_tankhah_lock_status,
)

logger = logging.getLogger("tankhah_views")

class TankhahCreateView_______________(PermissionBaseView, CreateView):
    model = Tankhah
    form_class = TankhahForm
    template_name = 'tankhah/Tankhah_form.html'  # مسیر صحیح تمپلیت شما
    context_object_name = 'form'  # استفاده از 'form' برای سازگاری با CreateView
    permission_codenames = ['tankhah.Tankhah_add']  # پرمیشن صحیح

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        # پاس دادن initial_project_budget_allocation_pk اگر از URL GET آمده
        if 'budget_allocation_id' in self.request.GET:  # نام پارامتر URL
            kwargs['initial_project_budget_allocation_pk'] = self.request.GET.get('budget_allocation_id')
        return kwargs

    def get_initial(self):
        """
        مقادیر اولیه برای فیلدهای فرم از کوئری پارامترهای URL (GET).
        این توسط __init__ فرم هم استفاده می‌شود.
        """
        initial = super().get_initial()
        budget_allocation_id_from_get = self.request.GET.get('budget_allocation_id')
        project_id_from_get = self.request.GET.get('project_id')
        organization_id_from_get = self.request.GET.get('organization_id')
        # ... سایر پارامترهای اولیه مورد نیاز ...

        logger.debug(
            f"TankhahCreateView get_initial - GET params: ba_id={budget_allocation_id_from_get}, proj_id={project_id_from_get}, org_id={organization_id_from_get}")

        if budget_allocation_id_from_get:
            try:
                ba = BudgetAllocation.objects.select_related(
                    'organization', 'project', 'subproject'
                ).get(pk=int(budget_allocation_id_from_get))
                initial['project_budget_allocation'] = ba.pk
                if ba.organization: initial['organization'] = ba.organization.pk
                if ba.project: initial['project'] = ba.project.pk
                if ba.subproject: initial['subproject'] = ba.subproject.pk
                logger.info(
                    f"Initial data for form set from BudgetAllocation (PK from GET: {budget_allocation_id_from_get})")
            except (ValueError, BudgetAllocation.DoesNotExist):
                logger.warning(f"BudgetAllocation with ID '{budget_allocation_id_from_get}' from GET params not found.")
            except Exception as e:
                logger.error(f"Error in get_initial processing budget_allocation_id: {e}", exc_info=True)

        # اگر فقط project_id از GET آمده (مثلاً از صفحه لیست پروژه‌ها)
        elif project_id_from_get and not initial.get('project'):
            try:
                project_instance = Project.objects.get(pk=int(project_id_from_get))
                initial['project'] = project_instance.pk
                # سعی کن سازمان را هم از پروژه بگیری (اولین سازمان مرتبط یا یک سازمان پیش‌فرض)
                if project_instance.organizations.exists():
                    initial['organization'] = project_instance.organizations.first().pk
                logger.info(f"Initial data for form set from Project ID {project_id_from_get}")
            except (ValueError, Project.DoesNotExist):
                logger.warning(f"Project with ID '{project_id_from_get}' from GET params not found.")

        # اگر فقط organization_id از GET آمده
        elif organization_id_from_get and not initial.get('organization'):
            initial['organization'] = organization_id_from_get
            logger.info(f"Initial data for form set with Organization ID {organization_id_from_get}")

        return initial

    def form_valid(self, form):
        logger.info(
            f"TankhahCreateView form_valid. User: {self.request.user.username}. Cleaned data: {form.cleaned_data}")
        try:
            with transaction.atomic():
                self.object = form.save(commit=False)  # ذخیره موقت فرم

                # تنظیم created_by
                if not self.object.created_by and self.request.user.is_authenticated:
                    self.object.created_by = self.request.user

                # تنظیم project_budget_allocation از cleaned_data
                project_budget_allocation = form.cleaned_data.get('project_budget_allocation')
                if not project_budget_allocation:
                    logger.error(
                        "CRITICAL: project_budget_allocation is None in form_valid after form.save(commit=False).")
                    form.add_error(None, _("خطای داخلی: منبع بودجه به درستی به تنخواه متصل نشده است."))
                    return self.form_invalid(form)

                self.object.project_budget_allocation = project_budget_allocation

                # تنظیم مرحله اولیه گردش کار
                initial_stage_qs = WorkflowStage.objects.filter(is_active=True)
                if hasattr(WorkflowStage, 'entity_type'):
                    initial_stage_qs = initial_stage_qs.filter(entity_type='TANKHAH')
                    logger.info(f'initial_stage_qs Create Tankhah : {initial_stage_qs}')
                initial_stage = initial_stage_qs.order_by('order').first()

                if not initial_stage:
                    logger.error("No initial/active workflow stage defined for Tankhahs.")
                    form.add_error(None, _("خطای سیستمی: مرحله اولیه گردش کاری برای تنخواه تعریف نشده است."))
                    return self.form_invalid(form)

                self.object.current_stage = initial_stage
                self.object.status = 'DRAFT'
                logger.debug(f"Tankhah initial stage: {initial_stage.name}, Status: {self.object.status}")

                # ذخیره مدل
                self.object.save()
                logger.info(f"Tankhah {self.object.number} (PK: {self.object.pk}) created successfully.")
                messages.success(self.request,
                                 _('تنخواه "{num}" با موفقیت ایجاد شد. لطفاً فاکتورهای مربوطه را از طریق صفحه جزئیات اضافه نمایید.').format(
                                     num=self.object.number))

                return redirect(self.get_success_url())

        except ValidationError as e:
            logger.warning(
                f"ValidationError during Tankhah save in form_valid: {e.message_dict if hasattr(e, 'message_dict') else e}")
            if hasattr(e, 'message_dict'):
                for field, errors_list in e.message_dict.items():
                    form.add_error(field if field != '__all__' else None, errors_list)
            else:
                form.add_error(None, e.messages if hasattr(e, 'messages') else str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Unexpected error in TankhahCreateView form_valid: {e}", exc_info=True)
            messages.error(self.request, _("خطای پیش‌بینی نشده‌ای هنگام ایجاد تنخواه رخ داد."))
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.warning(
            f"TankhahCreateView form_invalid. User: {self.request.user.username}. Errors: {form.errors.as_json()}")
        messages.error(self.request, _('فرم ارسال شده دارای خطا است. لطفاً موارد مشخص شده را اصلاح نمایید.'))
        return super().form_invalid(form)

    def get_success_url(self):
        if self.object:
            return reverse('tankhah_detail', kwargs={'pk': self.object.pk})
        return reverse_lazy('tankhah_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد تنخواه جدید')

        # URL ها برای AJAX در تمپلیت (باید در urls.py تعریف شوند)
        context['load_projects_url'] = reverse_lazy('ajax_load_projects')  # نام URL برای API پروژه‌ها
        context['load_subprojects_url'] = reverse_lazy('ajax_load_subprojects')  # نام URL برای API زیرپروژه‌ها
        context['load_budget_allocations_url'] = reverse_lazy(
            'ajax_load_allocations_for_tankhah')  # نام URL برای API تخصیص‌ها

        # نمایش اطلاعات بودجه اولیه اگر فرم با initial data پر شده
        form = context.get('form')
        if form and form.initial:
            # ... (منطق نمایش اطلاعات بودجه پروژه/زیرپروژه مانند قبل، اگر لازم است) ...
            pass

        logger.debug(f"TankhahCreateView get_context_data prepared. Title: {context['title']}")
        return context


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
    permission_codenames = ['tankhah.Tankhah_add']

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
    # --------------------------------------------------------------------------

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
