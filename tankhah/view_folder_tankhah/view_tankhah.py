import logging
import jdatetime

from tankhah.forms import TankhahForm
from tankhah.models import Tankhah

logger = logging.getLogger(__name__)
from decimal import Decimal
from django.db.models import Q, Sum
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, View
from django.views.generic.list import ListView
from notifications.signals import notify
from django.contrib import messages
from persiantools.jdatetime import JalaliDate  # ایمپورت درست
from accounts.models import CustomUser
from budgets.budget_calculations import get_project_total_budget, get_project_remaining_budget, \
    get_subproject_total_budget, get_subproject_remaining_budget
from tankhah.utils import restrict_to_user_organization

# tankhah/views.py
from core.views import PermissionBaseView
from django.utils.translation import gettext_lazy as _
from django.db import models
# -------
class TankhahCreateView(PermissionBaseView, CreateView):
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

    def form_valid(self, form):
        logger.info(f"فرم معتبر است. داده‌ها: {form.cleaned_data}")
        with transaction.atomic():
            self.object = form.save(commit=False)
            from core.models import WorkflowStage
            initial_stage = WorkflowStage.objects.order_by('order').first()
            if not initial_stage:
                messages.error(self.request, _("مرحله اولیه جریان کاری تعریف نشده است."))
                return self.form_invalid(form)

            subproject = form.cleaned_data.get('subproject')
            self.object.subproject = subproject

            # تنظیم فیلدهای اولیه
            self.object.subproject = form.cleaned_data.get('subproject')
            self.object.organization = form.cleaned_data['organization']
            self.object.current_stage = initial_stage
            self.object.status = 'DRAFT'
            self.object.created_by = self.request.user

            # تنظیم budget_allocation
            from budgets.models import ProjectBudgetAllocation
            project = form.cleaned_data.get('project')
            subproject = form.cleaned_data.get('subproject')
            project_budget_allocation = form.cleaned_data.get('project_budget_allocation')

            allocation = None
            if project_budget_allocation:
                allocation = project_budget_allocation
            elif subproject:
                allocation = ProjectBudgetAllocation.objects.filter(
                    subproject=subproject,
                    budget_allocation__is_active=True
                ).first()
            elif project:
                allocation = ProjectBudgetAllocation.objects.filter(
                    project=project,
                    subproject__isnull=True,
                    budget_allocation__is_active=True
                ).first()

            if allocation:
                self.object.budget_allocation = allocation.budget_allocation
                logger.debug(f"تنظیم budget_allocation به {allocation.budget_allocation.id}")
            else:
                messages.error(self.request, _("تخصیص بودجه معتبر برای پروژه یا زیرپروژه یافت نشد."))
                return self.form_invalid(form)

            # ذخیره شیء
            self.object.save()

            # ارسال اعلان به تأییدکنندگان
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
            from core.models import SubProject
            project_id = int(self.request.POST.get('project'))
            try:
                from core.models import Project
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

        # تنظیم مقادیر بودجه
        if project:
            total_budget = get_project_total_budget(project)
            remaining_budget = get_project_remaining_budget(project)
            context['total_budget'] =total_budget
            context['remaining_budget'] = remaining_budget
            # محاسبه درصد بودجه باقی‌مانده
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
            # محاسبه درصد بودجه باقی‌مانده زیرپروژه
            context['subproject_budget_percentage'] = (
                (subproject_remaining / subproject_total * 100) if subproject_total > 0 else Decimal('0')
            )
            logger.debug(f"Subproject {subproject.id} budget: total={subproject_total}, remaining={subproject_remaining}")
        else:
            context['subproject_total_budget'] = Decimal('0')
            context['subproject_remaining_budget'] = Decimal('0')
            context['subproject_budget_percentage'] = Decimal('0')

        return context

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return super().handle_no_permission()

# تأیید و ویرایش تنخواه
class TankhahUpdateView(PermissionBaseView, UpdateView):
    model = 'tankhah.Tankhah'
    form_class = 'tankhah.forms.TankhahForm'
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
class old__TankhahListView(PermissionBaseView, ListView):
    model = 'tankhah.Tankhah'
    template_name = 'tankhah/tankhah_list.html'
    context_object_name = 'Tankhahs'
    paginate_by = 10
    extra_context = {'title': _('لیست تنخواه‌ها')}
    check_organization = True
    permission_codenames = ['tankhah.Tankhah_view']

    def get_queryset(self):
        user = self.request.user
        logger.info(f"User: {user}, is_superuser: {user.is_superuser}")

        # سازمان‌های کاربر
        user_orgs = [up.post.organization for up in user.userpost_set.all()] if user.userpost_set.exists() else []
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False

        # فیلتر اولیه تنخواه‌ها
        if is_hq_user:
            queryset = 'tankhah.Tankhah'.objects.all()
            logger.info("کاربر HQ هست، همه تنخواه‌ها رو می‌بینه")
        elif user_orgs:
            queryset = 'tankhah.Tankhah'.objects.filter(organization__in=user_orgs)
            logger.info(f"فیلتر تنخواه‌ها برای سازمان‌های کاربر: {user_orgs}")
        else:
            queryset = 'tankhah.Tankhah'.objects.none()
            logger.info("کاربر هیچ سازمانی نداره، queryset خالی برمی‌گردونه")

        # فیلتر آرشیو
        show_archived = self.request.GET.get('show_archived', 'false') == 'true'
        if show_archived:
            queryset = queryset.filter(is_archived=True)
            logger.info(f"فقط آرشیوها نمایش داده می‌شن، تعداد: {queryset.count()}")
        else:
            queryset = queryset.filter(is_archived=False)
            logger.info(f"فقط غیرآرشیوها نمایش داده می‌شن، تعداد: {queryset.count()}")

        # فیلترهای اضافی
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                models.Q(number__icontains=query) |
                models.Q(organization__name__icontains=query) |
                models.Q(project__name__icontains=query) |
                models.Q(subproject__name__icontains=query)
            )

            logger.info(f"Filtered by query '{query}' count: {queryset.count()}")

        stage = self.request.GET.get('stage')
        if stage:
            queryset = queryset.filter(current_stage__order=stage)
            logger.info(f"Filtered by stage order {stage} count: {queryset.count()}")

            if not queryset.exists():
                messages.info(self.request, _('هیچ تنخواهی با این شرایط یافت نشد.'))

        # final_queryset = queryset.order_by('-date') # old
        final_queryset = queryset.select_related('project', 'subproject', 'organization', 'current_stage').order_by('-date')
        logger.info(f"Final queryset count: {final_queryset.count()}")
        return final_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_orgs = [up.post.organization for up in user.userpost_set.all()] if user.userpost_set.exists() else []
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False

        context['is_hq_user'] = is_hq_user
        context['user_orgs'] = user_orgs
        context['query'] = self.request.GET.get('q', '')
        context['stage'] = self.request.GET.get('stage', '')
        context['show_archived'] = self.request.GET.get('show_archived', 'false') == 'true'

        if is_hq_user:
            context['org_display_name'] = _('دفتر مرکزی')
        elif user_orgs:
            context['org_display_name'] = user_orgs[0].name
        else:
            context['org_display_name'] = _('بدون سازمان')

        tankhah_list_page = context[self.context_object_name] # گرفتن لیست آبجکت‌های صفحه فعلی
        for tankhah in tankhah_list_page:
            if tankhah.project:
                try:
                    # فراخوانی توابع محاسبه بودجه برای پروژه مربوطه
                    tankhah.project_total_budget_display = get_project_total_budget(tankhah.project)
                    tankhah.project_remaining_budget_display = get_project_remaining_budget(tankhah.project)
                    # محاسبه درصد مصرف شده (برای Progress Bar)
                    if tankhah.project_total_budget_display and tankhah.project_total_budget_display > 0:
                        consumed = tankhah.project_total_budget_display - tankhah.project_remaining_budget_display
                        tankhah.project_consumed_percentage = round((consumed / tankhah.project_total_budget_display) * 100)
                    else:
                        tankhah.project_consumed_percentage = 0
                except Exception as e:
                    # در صورت بروز خطا، مقادیر پیش‌فرض تنظیم کنید
                    logger.error(f"Error calculating budget for project {tankhah.project.id} in TankhahList: {e}")
                    tankhah.project_total_budget_display = Decimal('0')
                    tankhah.project_remaining_budget_display = Decimal('0')
                    tankhah.project_consumed_percentage = 0
            else:
                # اگر پروژه ندارد
                tankhah.project_total_budget_display = Decimal('0')
                tankhah.project_remaining_budget_display = Decimal('0')
                tankhah.project_consumed_percentage = 0
        # ----------------------------------------------------------

        return context

class TankhahListView(PermissionBaseView, ListView):
    model = 'tankhah.Tankhah'
    template_name = 'tankhah/tankhah_list.html'
    context_object_name = 'tankhahs'
    paginate_by = 10
    extra_context = {'title': _('لیست تنخواه‌ها')}
    check_organization = True
    permission_codenames = ['tankhah.Tankhah_view']

    def get_queryset(self):
        user = self.request.user
        logger.info(f"User: {user}, is_superuser: {user.is_superuser}")

        # سازمان‌های کاربر
        user_orgs = [up.post.organization for up in user.userpost_set.filter(is_active=True, end_date__isnull=True)] if user.userpost_set.exists() else []
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False

        # فیلتر اولیه تنخواه‌ها
        from tankhah.models import Tankhah
        if is_hq_user:
            queryset =   Tankhah.objects.all()
            logger.info("کاربر HQ هست، همه تنخواه‌ها را می‌بیند")
        elif user_orgs:
            queryset =   Tankhah.objects.filter(organization__in=user_orgs)
            logger.info(f"فیلتر تنخواه‌ها برای سازمان‌های کاربر: {[org.name for org in user_orgs]}")
        else:
            queryset =  Tankhah.objects.none()
            logger.info("کاربر هیچ سازمانی ندارد، queryset خالی برمی‌گردد")

        # فیلتر آرشیو
        show_archived = self.request.GET.get('show_archived', 'false') == 'true'
        queryset = queryset.filter(is_archived=show_archived)
        logger.info(f"نمایش آرشیو: {show_archived}, تعداد: {queryset.count()}")

        # فیلترهای اضافی
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(number__icontains=query) |
                Q(organization__name__icontains=query) |
                Q(project__name__icontains=query) |
                Q(subproject__name__icontains=query)
            )
            logger.info(f"فیلتر با عبارت '{query}'، تعداد: {queryset.count()}")

        stage = self.request.GET.get('stage')
        if stage:
            queryset = queryset.filter(current_stage__order=stage)
            logger.info(f"فیلتر بر اساس مرحله {stage}، تعداد: {queryset.count()}")
            if not queryset.exists():
                messages.info(self.request, _('هیچ تنخواهی با این شرایط یافت نشد.'))

        # بهینه‌سازی کوئری با select_related و prefetch_related
        # final_queryset = queryset.select_related(
        #     'project', 'subproject', 'organization', 'current_stage', 'budget_allocation'
        # ).prefetch_related('factors').order_by('-date') #
        from django.db.models import Prefetch
        from tankhah.models import Factor
        final_queryset = queryset.select_related(
            'project', 'subproject', 'organization', 'current_stage', 'budget_allocation'
        ).prefetch_related(
            Prefetch('factors', queryset= Factor.objects.filter(status__in=['APPROVED', 'PAID']))
        ).order_by('-date') #کوئری بهینه تر

        logger.info(f"تعداد تنخواه‌های نهایی: {final_queryset.count()}")
        return final_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_orgs = [up.post.organization for up in user.userpost_set.filter(is_active=True, end_date__isnull=True)] if user.userpost_set.exists() else []
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False

        # اطلاعات پایه context
        context['is_hq_user'] = is_hq_user
        context['user_orgs'] = user_orgs
        context['query'] = self.request.GET.get('q', '')
        context['stage'] = self.request.GET.get('stage', '')
        context['show_archived'] = self.request.GET.get('show_archived', 'false') == 'true'
        context['org_display_name'] = _('دفتر مرکزی') if is_hq_user else (user_orgs[0].name if user_orgs else _('بدون سازمان'))

        # پردازش تنخواه‌ها
        tankhah_list_page = context[self.context_object_name]
        for tankhah in tankhah_list_page:
            try:
                # اطلاعات بودجه پروژه
                project = tankhah.project
                if project:
                    # تخصیص بودجه به پروژه
                    tankhah.project_total_budget = get_project_total_budget(project)
                    tankhah.project_remaining_budget = get_project_remaining_budget(project)
                    tankhah.project_allocated_budget = tankhah.project_total_budget  # معادل دریافتی پروژه

                    # درصد مصرف بودجه پروژه
                    if tankhah.project_total_budget > 0:
                        consumed = tankhah.project_total_budget - tankhah.project_remaining_budget
                        tankhah.project_consumed_percentage = round((consumed / tankhah.project_total_budget) * 100)
                    else:
                        tankhah.project_consumed_percentage = 0
                else:
                    tankhah.project_total_budget = Decimal('0')
                    tankhah.project_remaining_budget = Decimal('0')
                    tankhah.project_allocated_budget = Decimal('0')
                    tankhah.project_consumed_percentage = 0

                # اطلاعات بودجه شعبه (سازمان)
                organization = tankhah.organization
                from budgets.models import BudgetAllocation
                if organization:
                    tankhah.branch_total_budget = BudgetAllocation.objects.filter(
                        organization=organization,
                        budget_period=tankhah.budget_allocation.budget_period
                    ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
                else:
                    tankhah.branch_total_budget = Decimal('0')

                # میزان استفاده‌شده در تنخواه
                from budgets.models import BudgetTransaction
                tankhah.tankhah_used_budget = BudgetTransaction.objects.filter(
                    allocation=tankhah.budget_allocation,
                    transaction_type='CONSUMPTION',
                    related_tankhah=tankhah
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

                # میزان استفاده‌شده توسط فاکتورهای تأییدشده
                tankhah.factor_used_budget = 'tankhah.Factor'.objects.filter(
                    tankhah=tankhah,
                    status__in=['APPROVED', 'PAID']
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            except Exception as e:
                logger.error(f"خطا در محاسبه بودجه برای تنخواه {tankhah.number}: {str(e)}")
                tankhah.project_total_budget = Decimal('0')
                tankhah.project_remaining_budget = Decimal('0')
                tankhah.project_allocated_budget = Decimal('0')
                tankhah.project_consumed_percentage = 0
                tankhah.branch_total_budget = Decimal('0')
                tankhah.tankhah_used_budget = Decimal('0')
                tankhah.factor_used_budget = Decimal('0')
                # context['errors'].append(f"خطا در تنخواه {tankhah.number}: {str(e)}")

        return context

class TankhahDetailView(PermissionBaseView, PermissionRequiredMixin, DetailView):
    model = 'tankhah.Tankhah'
    template_name = 'tankhah/Tankhah_detail.html'
    context_object_name = 'Tankhah'
    permission_required = (
        'tankhah.Tankhah_view', 'tankhah.tankhah_update',
        'tankhah.Tankhah_hq_view', 'tankhah.Tankhah_HQ_OPS_APPROVED', 'tankhah.edit_full_tankhah'
    )

    def has_permission(self):
        return any(self.request.user.has_perm(perm) for perm in self.get_permission_required())

    def get_object(self, queryset=None):
        tankhah = get_object_or_404('tankhah.Tankhah', pk=self.kwargs['pk'])
        restrict_to_user_organization(self.request.user, tankhah.organization)
        return tankhah

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['factors'] = self.object.factors.all()  # اصلاح: اضافه کردن .all()
        context['title'] = _('جزئیات تنخواه') + f" - {self.object.number}"
        context['approval_logs'] = 'tankhah.ApprovalLog'.objects.filter(tankhah=self.object).order_by('timestamp')
        context['current_date'] = jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M')
        from tankhah.forms import TankhahStatusForm
        context['status_form'] = TankhahStatusForm(instance=self.object)

        # تبدیل تاریخ‌ها به شمسی
        if self.object.date:
            context['jalali_date'] = jdatetime.date.fromgregorian(date=self.object.date).strftime('%Y/%m/%d %H:%M')
        for factor in context['factors']:
            factor.jalali_date = jdatetime.date.fromgregorian(date=factor.date).strftime('%Y/%m/%d %H:%M')
        for approval in context['approval_logs']:
            approval.jalali_date = jdatetime.datetime.fromgregorian(datetime=approval.timestamp).strftime('%Y/%m/%d %H:%M')

        # دسته‌بندی برای دفتر مرکزی
        user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()]
        context['is_hq'] = any(org.org_type == 'HQ' for org in user_orgs)
        context['can_approve'] = self.request.user.has_perm('tankhah.Tankhah_approve') or \
                                 self.request.user.has_perm('tankhah.Tankhah_part_approve') or \
                                 self.request.user.has_perm('tankhah.FactorItem_approve')
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
        tankhah = get_object_or_404('tankhah.Tankhah', pk=pk)
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
        next_stage = 'core.WorkflowStage'.objects.filter(order__gt=tankhah.current_stage.order).order_by('order').first()
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
        tankhah = 'tankhah.Tankhah'.objects.get(pk=pk)
        user_posts = request.user.userpost_set.all()
        if not any(p.post.stageapprover_set.filter(stage='tankhah.Tankhah'.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه رد این مرحله را ندارید.'))
            return redirect('dashboard_flows')

        'tankhah.Tankhah'.status = 'REJECTED'
        'tankhah.Tankhah'.save()
        messages.error(request, _('تنخواه رد شد.'))
        return redirect('dashboard_flows')
# ویو نهایی تنخواه تایید یا رد شده
class TankhahFinalApprovalView(PermissionBaseView,UpdateView):
    """ویو نهایی تنخواه تایید یا رد شده """
    model = 'tankhah.Tankhah'
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
    model = 'tankhah.Tankhah'
    form_class = 'tankhah.forms.TankhahForm'
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

