import logging

from django.http import JsonResponse

from budgets.models import BudgetAllocation, BudgetTransaction
from core.models import Organization, Project, WorkflowStage, UserPost, SubProject
from tankhah.forms import TankhahForm
from tankhah.models import Factor

logger = logging.getLogger(__name__)
from django.db.models import Sum, Prefetch
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, View
from django.views.generic.list import ListView
from notifications.signals import notify
from accounts.models import CustomUser
from budgets.budget_calculations import get_project_total_budget, get_project_remaining_budget, \
    get_subproject_total_budget, get_subproject_remaining_budget

from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView
from django.contrib import messages
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from jalali_date import date2jalali
from tankhah.models import Tankhah, ApprovalLog
from tankhah.forms import TankhahStatusForm
from django.contrib.contenttypes.models import ContentType
import jdatetime
from decimal import Decimal
# tankhah/views.py
from core.views import PermissionBaseView
from django.utils.translation import gettext_lazy as _
from jdatetime import date as jdate
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
                notify.send(
                    sender=self.request.user,
                    recipient=approvers,
                    verb='تنخواه برای تأیید آماده است',
                    target=self.object
                )
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
from tankhah.forms import TankhahForm  # فرمی که در بالا تعریف کردیم
from core.models import WorkflowStage, Organization, Project, SubProject
from budgets.models import BudgetAllocation
# from accounts.models import CustomUser # اگر برای notify لازم است
# از django.contrib.auth import get_user_model
# User = get_user_model()

# توابع محاسباتی بودجه (اگر در context برای نمایش اطلاعات بودجه استفاده می‌شوند)
from budgets.budget_calculations import get_project_total_budget, get_project_remaining_budget, \
    get_subproject_remaining_budget

logger = logging.getLogger("tankhah_views")


class TankhahCreateView(PermissionBaseView, CreateView):
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

# تأیید و ویرایش تنخواه
class TankhahUpdateView(PermissionBaseView, UpdateView):
    model =  Tankhah
    form_class =  TankhahForm
    template_name = 'tankhah/Tankhah_manage.html'
    success_url = reverse_lazy('tankhah_list')

    def test_func(self):
        # فقط سوپر‌یوزرها یا استف‌ها دسترسی دارن
        return self.request.user.is_superuser or self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, _('شما اجازه دسترسی به این صفحه را ندارید.'))
        return super().handle_no_permission()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.get_object()
        context['title'] = _('ویرایش و تأیید تنخواه') + f" - {tankhah.number}"
        context['can_edit'] = self.request.user.has_perm('tankhah.Tankhah_update') or self.request.user.is_staff

        # وضعیت‌های قفل‌کننده تنخواه
        locked_statuses = ['REJECTED', 'APPROVED', 'PAID', 'HQ_OPS_APPROVED', 'SENT_TO_HQ']
        has_factors = tankhah.factors.exists()  # چک کردن وجود فاکتور
        is_locked = has_factors or tankhah.status in locked_statuses

        context['is_locked'] = is_locked
        # دلیل قفل شدن
        if is_locked:
            if has_factors:
                context['lock_reason'] = _('این تنخواه قابل ویرایش نیست چون فاکتور ثبت‌شده دارد.')
            else:
                context['lock_reason'] = _('این تنخواه قابل ویرایش نیست چون در وضعیت "{}" است.').format(
                    tankhah.get_status_display())
        else:
            context['lock_reason'] = ''

        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tankhah = self.get_object()
        # اگه قفل شده، همه فیلدها رو غیرفعال کن
        locked_statuses = ['REJECTED', 'APPROVED', 'PAID', 'HQ_OPS_APPROVED', 'SENT_TO_HQ']
        if tankhah.factors.exists() or tankhah.status in locked_statuses:
            for field in form.fields.values():
                field.disabled = True
        return form

    def form_valid(self, form):
        tankhah = self.get_object()
        # اگه فاکتور داره یا رد/تأیید شده، نذار تغییر کنه
        locked_statuses = ['REJECTED', 'APPROVED', 'PAID', 'HQ_OPS_APPROVED', 'SENT_TO_HQ']
        if tankhah.factors.exists() or tankhah.status in locked_statuses:
            reason = _('فاکتور ثبت‌شده دارد') if tankhah.factors.exists() else _('در وضعیت "{}" است').format(
                tankhah.get_status_display())
            messages.error(self.request, _('این تنخواه قابل ویرایش نیست چون {}').format(reason))
            return self.form_invalid(form)

        user_post = self.request.user.userpost_set.filter(post__organization=tankhah.organization).first()
        if not user_post or user_post.post.branch != tankhah.current_stage:
            messages.error(self.request, _('شما اجازه تأیید در این مرحله را ندارید.'))
            return self.form_invalid(form)

        next_post = 'core.Post'.objects.filter(parent=user_post.post, organization=tankhah.organization).first() or \
                    'core.Post'.objects.filter(organization__org_type='HQ', branch=tankhah.current_stage, level=1).first()
        if next_post:
            tankhah.last_stopped_post = next_post
        tankhah.save()
        messages.success(self.request, _('تنخواه با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)
# -------
class TankhahListView(PermissionBaseView, ListView):
    model = Tankhah
    template_name = 'tankhah/tankhah_list.html'
    context_object_name = 'tankhahs'
    paginate_by = 10
    extra_context = {'title': _('لیست تنخواه‌ها')}
    check_organization = True
    permission_codenames = ['tankhah.Tankhah_view']

    def get_queryset(self):
        user = self.request.user
        logger.info(f"[TankhahListView] User: {user}, is_superuser: {user.is_superuser}")

        user_posts = UserPost.objects.filter(
            user=user, is_active=True, end_date__isnull=True
        ).select_related('post__organization', 'post__organization__org_type')
        user_org_pks = [up.post.organization.pk for up in user_posts if up.post and up.post.organization]
        is_hq_user = (
                user.is_superuser or
                user.has_perm('tankhah.Tankhah_view_all') or
                any(up.post.organization.org_type and up.post.organization.org_type.org_type == 'HQ'
                    for up in user_posts if up.post and up.post.organization)
        )

        logger.info(
            f"[TankhahListView] User: {user.username}, is_hq_user: {is_hq_user}, User org PKs: {user_org_pks}"
        )

        if is_hq_user:
            queryset = Tankhah.objects.all()
            logger.debug("[TankhahListView] HQ user access: fetching all Tankhahs.")
        elif user_org_pks:
            queryset = Tankhah.objects.filter(organization__pk__in=user_org_pks)
            logger.debug(f"[TankhahListView] Filtered for user organizations: {user_org_pks}")
        else:
            queryset = Tankhah.objects.none()
            logger.info("[TankhahListView] User has no associated organizations. Returning empty queryset.")

        show_archived = self.request.GET.get('show_archived', 'false').lower() == 'true'
        queryset = queryset.filter(is_archived=show_archived)
        logger.debug(f"[TankhahListView] نمایش آرشیو: {show_archived}, تعداد: {queryset.count()}")

        query = self.request.GET.get('q', '').strip()
        date_query = self.request.GET.get('date', '').strip()
        amount_query = self.request.GET.get('amount', '').strip()
        remaining_query = self.request.GET.get('remaining', '').strip()
        stage = self.request.GET.get('stage', '').strip()

        filter_conditions = Q()

        if query:
            filter_conditions &= (
                    Q(number__icontains=query) |
                    Q(organization__name__icontains=query) |
                    Q(project__name__icontains=query) |
                    Q(subproject__name__icontains=query) |
                    Q(description__icontains=query)
            )
            logger.debug(f"[TankhahListView] جستجو '{query}', تعداد: {queryset.filter(filter_conditions).count()}")

        if date_query:
            try:
                parts = date_query.split('-')
                if len(parts) == 1:
                    year = int(parts[0])
                    gregorian_year = year - 621
                    filter_conditions &= Q(date__year=gregorian_year)
                elif len(parts) == 2:
                    year, month = map(int, parts)
                    jalali_date = jdate(year, month, 1)
                    gregorian_date = jalali_date.togregorian()
                    filter_conditions &= Q(date__year=gregorian_date.year, date__month=gregorian_date.month)
                elif len(parts) == 3:
                    year, month, day = map(int, parts)
                    jalali_date = jdate(year, month, day)
                    gregorian_date = jalali_date.togregorian()
                    filter_conditions &= Q(date=gregorian_date)
                else:
                    raise ValueError("Invalid date format")
            except ValueError as e:
                logger.warning(f"[TankhahListView] خطای فرمت تاریخ: {date_query}, error: {str(e)}")
                messages.error(self.request, _('فرمت تاریخ نامعتبر است (1403، 1403-05، یا 1403-05-15).'))
                filter_conditions &= Q(date__isnull=True)
            logger.debug(
                f"[TankhahListView] فیلتر تاریخ '{date_query}', تعداد: {queryset.filter(filter_conditions).count()}")

        if amount_query:
            try:
                amount = Decimal(amount_query.replace(',', ''))
                filter_conditions &= Q(amount=amount)
            except (ValueError, Decimal.InvalidOperation):
                logger.warning(f"[TankhahListView] خطای فرمت مبلغ: {amount_query}")
                messages.error(self.request, _('مبلغ باید عدد باشد.'))
                filter_conditions &= Q(amount__isnull=True)
            logger.debug(
                f"[TankhahListView] فیلتر مبلغ '{amount_query}', تعداد: {queryset.filter(filter_conditions).count()}")

        if remaining_query:
            try:
                remaining = Decimal(remaining_query.replace(',', ''))
                tankhah_ids = [
                    t.id for t in queryset
                    if abs((t.get_remaining_budget() or Decimal('0')) - remaining) < Decimal('0.01')
                ]
                filter_conditions &= Q(id__in=tankhah_ids)
            except (ValueError, Decimal.InvalidOperation):
                logger.warning(f"[TankhahListView] خطای فرمت باقیمانده: {remaining_query}")
                messages.error(self.request, _('باقیمانده باید عدد باشد.'))
                filter_conditions &= Q(id__in=[])
            logger.debug(
                f"[TankhahListView] فیلتر باقیمانده '{remaining_query}', تعداد: {queryset.filter(filter_conditions).count()}")

        if stage:
            try:
                filter_conditions &= Q(current_stage__order=int(stage))
            except ValueError:
                logger.warning(f"[TankhahListView] خطای فرمت مرحله: {stage}")
                messages.error(self.request, _('مرحله باید عدد باشد.'))
            logger.debug(f"[TankhahListView] فیلتر مرحله {stage}, تعداد: {queryset.filter(filter_conditions).count()}")

        if filter_conditions:
            queryset = queryset.filter(filter_conditions)
            if not queryset.exists():
                messages.info(self.request, _('هیچ تنخواهی یافت نشد.'))
                logger.info("[TankhahListView] هیچ تنخواهی با شرایط فیلتر یافت نشد")

        final_queryset = queryset.select_related(
            'project', 'subproject', 'organization', 'current_stage',
            'created_by', 'project_budget_allocation', 'project_budget_allocation__budget_item',
            'project_budget_allocation__budget_period'
        ).prefetch_related(
            Prefetch(
                'factors',
                queryset=Factor.objects.filter(status__in=['APPROVED', 'PAID']),
                to_attr='paid_and_approved_factors'
            )
        ).order_by('organization__name', 'project__name', '-date')

        logger.debug(f"[TankhahListView] تعداد تنخواه‌های نهایی: {final_queryset.count()}")
        return final_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        logger.info(f"[TankhahListView] ایجاد کنتکست برای کاربر: {user}")

        user_posts = UserPost.objects.filter(
            user=user, is_active=True, end_date__isnull=True
        ).select_related('post__organization', 'post__organization__org_type')
        user_orgs = [up.post.organization for up in user_posts if up.post and up.post.organization]
        user_org_pks = [org.pk for org in user_orgs]
        is_hq_user = (
                user.is_superuser or
                user.has_perm('tankhah.Tankhah_view_all') or
                any(up.post.organization.org_type and up.post.organization.org_type.org_type == 'HQ'
                    for up in user_posts if up.post and up.post.organization)
        )

        logger.debug(
            f"[TankhahListView] get_context_data - is_hq_user: {is_hq_user}, org_pks: {user_org_pks}"
        )

        context['is_hq_user'] = is_hq_user
        context['user_orgs'] = user_orgs
        context['query'] = self.request.GET.get('q', '')
        context['date_query'] = self.request.GET.get('date', '')
        context['amount_query'] = self.request.GET.get('amount', '')
        context['remaining_query'] = self.request.GET.get('remaining', '')
        context['stage'] = self.request.GET.get('stage', '')
        context['show_archived'] = self.request.GET.get('show_archived', 'false').lower() == 'true'
        context['org_display_name'] = (
            _('دفتر مرکزی') if is_hq_user else (user_orgs[0].name if user_orgs else _('بدون سازمان'))
        )

        tankhah_list = context[self.context_object_name]
        grouped_by_org = {}

        org_budget_cache = {}
        org_ids = (
            [org.id for org in user_orgs] if not is_hq_user else
            list(set(tankhah.organization_id for tankhah in tankhah_list if tankhah.organization_id))
        )

        budget_periods = list(
            set(tankhah.project_budget_allocation.budget_period_id
                for tankhah in tankhah_list
                if tankhah.project_budget_allocation)
        )

        for org_id in org_ids:
            if org_id:
                org_budget_cache[org_id] = (
                        BudgetAllocation.objects.filter(
                            organization_id=org_id,
                            budget_period_id__in=budget_periods
                        ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
                )

        for tankhah in tankhah_list:
            try:
                org = tankhah.organization
                org_key = org.name if org else _('بدون شعبه')
                project_key = tankhah.project.name if tankhah.project else _('بدون پروژه')

                if org_key not in grouped_by_org:
                    grouped_by_org[org_key] = {
                        'organization': org,
                        'projects': {},
                        'total_amount': Decimal('0'),
                        'total_remaining': Decimal('0')
                    }

                if project_key not in grouped_by_org[org_key]['projects']:
                    grouped_by_org[org_key]['projects'][project_key] = {
                        'project': tankhah.project,
                        'tankhahs': [],
                        'total_amount': Decimal('0'),
                        'total_remaining': Decimal('0')
                    }

                tankhah_amount = tankhah.amount or Decimal('0')
                tankhah_remaining = tankhah.get_remaining_budget() or Decimal('0')
                grouped_by_org[org_key]['projects'][project_key]['tankhahs'].append(tankhah)
                grouped_by_org[org_key]['projects'][project_key]['total_amount'] += tankhah_amount
                grouped_by_org[org_key]['projects'][project_key]['total_remaining'] += tankhah_remaining
                grouped_by_org[org_key]['total_amount'] += tankhah_amount
                grouped_by_org[org_key]['total_remaining'] += tankhah_remaining

                project = tankhah.project
                if project:
                    tankhah.project_total_budget = get_project_total_budget(project) or Decimal('0')
                    tankhah.project_remaining_budget = get_project_remaining_budget(project) or Decimal('0')
                    tankhah.project_allocated_budget = tankhah.project_total_budget
                    tankhah.project_consumed_percentage = (
                        round(
                            (tankhah.project_total_budget - tankhah.project_remaining_budget) /
                            tankhah.project_total_budget * 100
                        ) if tankhah.project_total_budget > 0 else 0
                    )
                else:
                    tankhah.project_total_budget = Decimal('0')
                    tankhah.project_remaining_budget = Decimal('0')
                    tankhah.project_allocated_budget = Decimal('0')
                    tankhah.project_consumed_percentage = 0

                tankhah.branch_total_budget = org_budget_cache.get(
                    tankhah.organization_id if org else None, Decimal('0')
                )
                tankhah.tankhah_used_budget = (
                        BudgetTransaction.objects.filter(
                            allocation=tankhah.project_budget_allocation,
                            transaction_type='CONSUMPTION',
                            related_tankhah=tankhah
                        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                ) if tankhah.project_budget_allocation else Decimal('0')
                tankhah.factor_used_budget = (
                        tankhah.factors.aggregate(total=Sum('amount'))['total'] or Decimal('0')
                )

            except Exception as e:
                logger.error(f"[TankhahListView] خطا در محاسبه بودجه تنخواه {tankhah.number}: {str(e)}")
                tankhah.project_total_budget = Decimal('0')
                tankhah.project_remaining_budget = Decimal('0')
                tankhah.project_allocated_budget = Decimal('0')
                tankhah.project_consumed_percentage = 0
                tankhah.branch_total_budget = Decimal('0')
                tankhah.tankhah_used_budget = Decimal('0')
                tankhah.factor_used_budget = Decimal('0')

        context['grouped_by_org'] = grouped_by_org
        context['errors'] = []
        logger.debug(f"[TankhahListView] تعداد شعبه‌ها: {len(grouped_by_org)}")
        return context
class LD__TankhahDetailView( PermissionBaseView,DetailView): #PermissionBaseView,
    model = Tankhah
    template_name = 'tankhah/tankhah_detail.html'
    context_object_name = 'Tankhah'
    permission_codenames = ['tankhah.Tankhah_detail']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    check_organization = True

    # def has_permission(self):
    #     return any(self.request.user.has_perm(perm) for perm in self.get_permission_required())

    # def get_object(self, queryset=None):
    #     tankhah = get_object_or_404(Tankhah, pk=self.kwargs['pk'])
    #     user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()]
    #     is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)
    #     if not is_hq_user and tankhah.organization not in user_orgs:
    #         logger.warning(f"User {self.request.user.username} attempted to access unauthorized Tankhah {tankhah.pk}")
    #         raise PermissionDenied(_('شما اجازه دسترسی به این تنخواه را ندارید.'))
    #     return tankhah

    def get_queryset(self):
        return Tankhah.objects.select_related(
            'organization', 'project', 'project_budget_allocation', 'subproject'
        ).prefetch_related('factors', 'approval_logs')

    def post(self, request, *args, **kwargs):
        tankhah = self.get_object()
        form = TankhahStatusForm(request.POST, instance=tankhah)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, _('وضعیت تنخواه با موفقیت به‌روزرسانی شد.'))
                logger.info(f"Tankhah {tankhah.pk} status updated by user {request.user.username}")
                return redirect('tankhah_detail', pk=tankhah.pk)
            except Exception as e:
                logger.error(f"Error updating Tankhah {tankhah.pk} status: {str(e)}", exc_info=True)
                messages.error(request, _('خطایی در به‌روزرسانی وضعیت رخ داد.'))
        else:
            messages.error(request, _('فرم نامعتبر است. لطفاً ورودی‌ها را بررسی کنید.'))
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object
        context['factors'] = tankhah.factors.all()
        context['title'] = _('جزئیات تنخواه') + f" - {tankhah.number}"
        context['approval_logs'] = ApprovalLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Tankhah),
            object_id=tankhah.pk
        ).order_by('timestamp')
        context['current_date'] = jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M')
        context['status_form'] = TankhahStatusForm(instance=tankhah)

        # لاگ مقادیر
        remaining_budget = tankhah.get_remaining_budget()
        logger.debug(f"Tankhah {tankhah.pk}: amount={tankhah.amount}, remaining_budget={remaining_budget}")

        # تنظیم مقادیر برای context
        context['amount'] = tankhah.amount if tankhah.amount is not None else Decimal('0')
        context['remaining_budget'] = remaining_budget if remaining_budget is not None else Decimal('0')

        # تبدیل تاریخ‌ها به شمسی
        if tankhah.date:
            context['jalali_date'] = date2jalali(tankhah.date).strftime('%Y/%m/%d')
        for factor in context['factors']:
            factor.jalali_date = date2jalali(factor.date).strftime('%Y/%m/%d')
        for approval in context['approval_logs']:
            approval.jalali_date = jdatetime.datetime.fromgregorian(datetime=approval.timestamp).strftime('%Y/%m/%d %H:%M')

        # دسته‌بندی برای دفتر مرکزی و دسترسی‌ها
        user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()]
        context['is_hq'] = any(org.org_type == 'HQ' for org in user_orgs)
        context['can_approve'] = (
            tankhah.status in ['DRAFT', 'PENDING'] and
            any(
                p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists()
                for p in self.request.user.userpost_set.all()
            ) and (
                self.request.user.has_perm('tankhah.Tankhah_approve') or
                self.request.user.has_perm('tankhah.Tankhah_part_approve') or
                self.request.user.has_perm('tankhah.FactorItem_approve')
            )
        )
        return context

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

logger = logging.getLogger("TankhahDetailView")

class TankhahDetailView(PermissionBaseView, DetailView):
    model = Tankhah
    template_name = 'tankhah/tankhah_detail.html'
    context_object_name = 'tankhah'
    permission_codenames = ['tankhah.Tankhah_detail']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    check_organization = True

    def get_queryset(self):
        return Tankhah.objects.select_related(
            'organization', 'project', 'project_budget_allocation', 'subproject', 'created_by'
        ).prefetch_related('factors', 'approval_logs')

    def post(self, request, *args, **kwargs):
        tankhah = self.get_object()
        form = TankhahStatusForm(request.POST, instance=tankhah)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, _('وضعیت تنخواه با موفقیت به‌روزرسانی شد.'))
                logger.info(f"Tankhah {tankhah.pk} status updated by user {request.user.username}")
                return redirect('tankhah_detail', pk=tankhah.pk)
            except Exception as e:
                logger.error(f"Error updating Tankhah {tankhah.pk} status: {str(e)}", exc_info=True)
                messages.error(request, _('خطایی در به‌روزرسانی وضعیت رخ داد.'))
        else:
            messages.error(request, _('فرم نامعتبر است. لطفاً ورودی‌ها را بررسی کنید.'))
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object
        logger.debug(f"Processing Tankhah {tankhah.pk} for user {self.request.user.username}")

        # اطلاعات پایه
        context['title'] = _('جزئیات تنخواه') + f" - {tankhah.number}"
        context['current_date'] = jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M')
        context['factors'] = tankhah.factors.all()
        context['approval_logs'] = ApprovalLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Tankhah),
            object_id=tankhah.pk
        ).order_by('timestamp')
        context['status_form'] = TankhahStatusForm(instance=tankhah)

        # بودجه تنخواه
        try:
            context['tankhah_total_budget'] = get_tankhah_total_budget(tankhah) or Decimal('0')
            context['tankhah_used_budget'] = get_tankhah_used_budget(tankhah) or Decimal('0')
            context['tankhah_remaining_budget'] = get_tankhah_remaining_budget(tankhah) or Decimal('0')
            logger.debug(
                f"Tankhah {tankhah.pk}: total={context['tankhah_total_budget']}, "
                f"used={context['tankhah_used_budget']}, remaining={context['tankhah_remaining_budget']}"
            )
        except Exception as e:
            logger.error(f"Error calculating tankhah budgets: {str(e)}", exc_info=True)
            context['tankhah_total_budget'] = Decimal('0')
            context['tankhah_used_budget'] = Decimal('0')
            context['tankhah_remaining_budget'] = Decimal('0')
            messages.error(self.request, _('خطایی در محاسبه بودجه تنخواه رخ داد.'))

        # بودجه پروژه
        if tankhah.project:
            try:
                context['project_total_budget'] = get_project_total_budget(tankhah.project) or Decimal('0')
                context['project_remaining_budget'] = get_project_remaining_budget(tankhah.project) or Decimal('0')
                logger.debug(
                    f"Project {tankhah.project.pk}: total={context['project_total_budget']}, "
                    f"remaining={context['project_remaining_budget']}"
                )
            except Exception as e:
                logger.error(f"Error calculating project budgets: {str(e)}", exc_info=True)
                context['project_total_budget'] = Decimal('0')
                context['project_remaining_budget'] = Decimal('0')
                messages.error(self.request, _('خطایی در محاسبه بودجه پروژه رخ داد.'))
        else:
            context['project_total_budget'] = Decimal('0')
            context['project_remaining_budget'] = Decimal('0')

        # وضعیت قفل
        try:
            is_locked, lock_message = check_tankhah_lock_status(tankhah)
            context['is_locked'] = is_locked
            context['lock_message'] = lock_message
            logger.debug(f"Tankhah {tankhah.pk} lock status: {is_locked}, message: {lock_message}")
        except Exception as e:
            logger.error(f"Error checking lock status: {str(e)}", exc_info=True)
            context['is_locked'] = True
            context['lock_message'] = _('خطا در بررسی وضعیت قفل.')
            messages.error(self.request, context['lock_message'])

        # تاریخ شمسی
        context['jalali_date'] = date2jalali(tankhah.date).strftime('%Y/%m/%d') if tankhah.date else '-'
        for factor in context['factors']:
            factor.jalali_date = date2jalali(factor.date).strftime('%Y/%m/%d') if factor.date else '-'
        for approval in context['approval_logs']:
            approval.jalali_date = jdatetime.datetime.fromgregorian(
                datetime=approval.timestamp
            ).strftime('%Y/%m/%d %H:%M')

        # دسترسی‌ها
        user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()]
        context['is_hq'] = any(org.org_type and org.org_type.org_type == 'HQ' for org in user_orgs if org.org_type)
        context['can_approve'] = (
            tankhah.status in ['DRAFT', 'PENDING'] and
            any(
                p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists()
                for p in self.request.user.userpost_set.all()
            ) and (
                self.request.user.has_perm('tankhah.Tankhah_approve') or
                self.request.user.has_perm('tankhah.Tankhah_part_approve') or
                self.request.user.has_perm('tankhah.FactorItem_approve')
            )
        )
        context['can_delete'] = (
            tankhah.status in ['DRAFT', 'REJECTED'] and
            self.request.user.has_perm('tankhah.Tankhah_delete') and
            not tankhah.factors.filter(status__in=['APPROVED', 'PAID']).exists()
        )

        # دیباگ context
        logger.debug(f"Context for Tankhah {tankhah.pk}: {context}")
        return context
class TankhahDeleteView(PermissionBaseView, DeleteView):
    model = 'tankhah.Tankhah'
    template_name = 'tankhah/Tankhah_confirm_delete.html'
    success_url = reverse_lazy('tankhah_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تنخواه با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)
# ویو تأیید:
class TankhahApproveView(PermissionBaseView, View):
    permission_codenames = ['tankhah.Tankhah_approve']

    def post(self, request, pk):
        tankhah = get_object_or_404( Tankhah, pk=pk)
        user_posts = request.user.userpost_set.all()

        logger.info(f"Processing POST for tankhah {tankhah.number}, current_stage: {tankhah.current_stage.name} (order: {tankhah.current_stage.order})")
        logger.info(f"User posts: {[p.post.name for p in user_posts]}")

        # چک دسترسی به مرحله فعلی
        can_approve = any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts)
        if not can_approve:
            logger.warning(f"User {request.user.username} not authorized to approve stage {tankhah.current_stage.name}")
            messages.error(request, _('شما اجازه تأیید این مرحله را ندارید.'))
            return redirect('dashboard_flows')

        # اگه قفل یا آرشیو شده، اجازه تغییر نده
        if tankhah.is_locked or tankhah.is_archived:
            messages.error(request, _('این تنخواه قفل یا آرشیو شده و قابل تغییر نیست.'))
            return redirect('dashboard_flows')

        # پیدا کردن مرحله بعدی
        from core.models import WorkflowStage
        next_stage =   WorkflowStage.objects.filter(order__gt=tankhah.current_stage.order).order_by('order').first()
        with transaction.atomic():
            if next_stage:
                tankhah.current_stage = next_stage
                tankhah.status = 'PENDING'
                tankhah.save()
                messages.success(request, _('تنخواه با موفقیت تأیید شد و به مرحله بعدی منتقل شد.'))

                # ارسال نوتیفیکیشن به تأییدکنندگان مرحله بعدی
                approvers = CustomUser.objects.filter(
                    userpost__post__stageapprover_set__stage=next_stage,
                    userpost__post__organization=tankhah.organization
                ).distinct()
                if approvers.exists():
                    notify.send(
                        sender=request.user,
                        recipient=approvers,
                        verb='تنخواه برای تأیید آماده است',
                        target=tankhah
                    )
                    logger.info(f"Notification sent to {approvers.count()} users for stage {next_stage.name}")
                else:
                    logger.warning(f"No approvers found for stage {next_stage.name}")
            else:
                # مرحله آخر: پرداخت
                authorized_final_posts = [approver.post.name for approver in tankhah.current_stage.stageapprover_set.all()]
                if any(p.post.name in authorized_final_posts for p in user_posts):
                    payment_number = request.POST.get('payment_number', '').strip()
                    if not payment_number:
                        messages.error(request, _('لطفاً شماره پرداخت را وارد کنید.'))
                        return redirect('dashboard_flows')
                    tankhah.status = 'PAID'
                    tankhah.hq_status = 'PAID'
                    tankhah.payment_number = payment_number
                    tankhah.is_locked = True
                    tankhah.is_archived = True
                    tankhah.save()
                    messages.success(request, _('تنخواه پرداخت شد، قفل و آرشیو شد.'))
                else:
                    tankhah.status = 'COMPLETED'
                    tankhah.hq_status = 'COMPLETED'
                    tankhah.is_locked = True
                    tankhah.is_archived = True
                    tankhah.save()
                    messages.success(request, _('تنخواه تکمیل شد، قفل و آرشیو شد.'))

        return redirect('dashboard_flows')
# ویو رد:
class TankhahRejectView(PermissionBaseView, View):
    permission_codenames = ['tankhah.Tankhah_approve']
    def get(self, request, pk):
        tankhah = Tankhah.objects.get(pk=pk)
        user_posts = request.user.userpost_set.all()
        if not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه رد این مرحله را ندارید.'))
            return redirect('dashboard_flows')

        tankhah.status = 'REJECTED'
        tankhah.Tankhah.save()
        messages.error(request, _('تنخواه رد شد.'))
        return redirect('dashboard_flows')
# ویو نهایی تنخواه تایید یا رد شده
class TankhahFinalApprovalView(PermissionBaseView,UpdateView):
    """ویو نهایی تنخواه تایید یا رد شده """
    model =   Tankhah
    fields = ['status']
    template_name = 'tankhah/Tankhah_final_approval.html'
    success_url = reverse_lazy('tankhah_list')

    def form_valid(self, form):
        user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()]
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)
        if not is_hq_user:
            messages.error(self.request, _('فقط دفتر مرکزی می‌تواند تأیید نهایی کند.'))
            return self.form_invalid(form)

        # جلوگیری از تأیید اگر تنخواه در مراحل پایین‌تر باشد
        if self.object.current_stage.order < 4:  # قبل از HQ_OPS
            messages.error(self.request, _('تنخواه هنوز در جریان مراحل شعبه است و قابل تأیید نیست.'))
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            if self.object.status == 'PAID':
                self.object.current_stage = 'tankhah.WorkflowStage'.objects.get(name='HQ_FIN')
                self.object.is_archived = True
                self.object.save()
                messages.success(self.request, _('تنخواه پرداخت و آرشیو شد.'))
            elif self.object.status == 'REJECTED':
                messages.warning(self.request, _('تنخواه رد شد.'))
        return super().form_valid(form)

class TankhahManageView(PermissionBaseView, CreateView):
    model =  Tankhah
    form_class = TankhahForm
    template_name = 'tankhah/tankhah_manage.html'
    success_url = reverse_lazy('tankhah_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _('تنخواه با موفقیت ثبت یا به‌روزرسانی شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('مدیریت تنخواه')
        return context

