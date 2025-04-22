import logging
from decimal import Decimal

from  django.utils import timezone
import jdatetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
from notifications.signals import notify

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from accounts.models import CustomUser
from budgets.budget_calculations import get_project_total_budget, get_project_remaining_budget, \
    get_subproject_total_budget, get_subproject_remaining_budget
from core.PermissionBase import get_lowest_access_level, get_initial_stage_order
# Local imports
from core.models import UserPost, Post, WorkflowStage, PostHistory, SubProject, Project
from .forms import (
    ApprovalForm, FactorItemApprovalForm, FactorApprovalForm, TankhahDocumentForm, FactorDocumentForm, FactorForm,
    FactorItemFormSet, TankhahForm, TankhahStatusForm
)
from .fun_can_edit_approval import can_edit_approval
from .models import (
    ApprovalLog, FactorItem, TankhahDocument, FactorDocument, StageApprover, Notification)
from .utils import restrict_to_user_organization

# Logger configuration
logger = logging.getLogger(__name__)
from django.contrib import messages
from .models import Tankhah
from persiantools.jdatetime import JalaliDate  # ایمپورت درست
# tankhah/views.py
from django.views.generic.list import ListView
from django.db.models import Q
from .models import Factor
from core.views import PermissionBaseView
from django.utils.translation import gettext_lazy as _
from django.db import models
# -------
###########################################
class DashboardView(PermissionBaseView, TemplateView):
    template_name = 'tankhah/Tankhah_dashboard.html'
    extra_context = {'title': _('داشبورد مدیریت تنخواه')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # لینک‌ها بر اساس پرمیشن‌ها
        context['links'] = {
            'Tankhah': [
                {'url': 'tankhah_list', 'label': _('لیست تنخواه‌ها'), 'icon': 'fas fa-list',
                 'perm': 'Tankhah.tankhah_view'},
                {'url': 'tankhah_create', 'label': _('ایجاد تنخواه'), 'icon': 'fas fa-plus',
                 'perm': 'tankhah.tankhah_add'},
            ],
            'factor': [
                {'url': 'factor_list', 'label': _('لیست فاکتورها'), 'icon': 'fas fa-file-invoice',
                 'perm': 'tankhah.a_factor_view'},
                {'url': 'factor_create', 'label': _('ایجاد فاکتور'), 'icon': 'fas fa-plus',
                 'perm': 'tankhah.a_factor_add'},
            ],
            'approval': [
                {'url': 'approval_list', 'label': _('لیست تأییدات'), 'icon': 'fas fa-check-circle',
                 'perm': 'tankhah.Approval_view'},
                {'url': 'approval_create', 'label': _('ثبت تأیید'), 'icon': 'fas fa-plus',
                 'perm': 'tankhah.Approval_add'},
            ],
        }

        # فیلتر کردن لینک‌ها بر اساس دسترسی کاربر
        for section in context['links']:
            context['links'][section] = [link for link in context['links'][section] if user.has_perm(link['perm'])]

        return context
# ثبت و ویرایش تنخواه
# @method_decorator(has_permission('Tankhah_add'), name='dispatch')
class TankhahManageView(PermissionBaseView, CreateView):
    model = Tankhah
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

def get_subprojects(request):
    logger.info('ورود به تابع get_subprojects')
    project_id = request.GET.get('project_id')
    if not project_id:
        logger.warning('project_id دریافت نشد')
        return JsonResponse({'subprojects': []}, status=400)

    try:
        project_id = int(project_id)
        user_orgs = set(up.post.organization for up in request.user.userpost_set.all())
        logger.info(f'project_id: {project_id}, user_orgs: {user_orgs}')

        project = Project.objects.get(id=project_id)
        logger.info(f'پروژه {project_id}: {project.name}')

        # همه ساب‌پروژه‌ها رو بر اساس project_id برگردون، بدون فیلتر سازمان
        subprojects = SubProject.objects.filter(project_id=project_id).values('id', 'name')
        logger.info(f'subprojects found: {list(subprojects)}')
        return JsonResponse({'subprojects': list(subprojects)})
    except Project.DoesNotExist:
        logger.error(f'پروژه با id {project_id} یافت نشد')
        return JsonResponse({'subprojects': []}, status=404)
    except ValueError:
        logger.error(f'project_id نامعتبر: {project_id}')
        return JsonResponse({'subprojects': []}, status=400)
    except Exception as e:
        logger.error(f'خطا در get_subprojects: {str(e)}')
        return JsonResponse({'subprojects': []}, status=500)

def get_subprojects(request):
    logger.info('ورود به تابع get_subprojects')
    project_id = request.GET.get('project_id')
    if not project_id:
        logger.warning('project_id دریافت نشد')
        return JsonResponse({'subprojects': []}, status=400)

    try:
        project_id = int(project_id)
        logger.info(f'project_id: {project_id}')

        project = Project.objects.get(id=project_id)
        logger.info(f'پروژه {project_id}: {project.name}')

        # همه ساب‌پروژه‌ها رو بدون فیلتر سازمان برگردون
        subprojects = SubProject.objects.filter(project_id=project_id).values('id', 'name')
        logger.info(f'subprojects found: {list(subprojects)}')
        return JsonResponse({'subprojects': list(subprojects)})
    except Project.DoesNotExist:
        logger.error(f'پروژه با id {project_id} یافت نشد')
        return JsonResponse({'subprojects': []}, status=404)
    except ValueError:
        logger.error(f'project_id نامعتبر: {project_id}')
        return JsonResponse({'subprojects': []}, status=400)
    except Exception as e:
        logger.error(f'خطا در get_subprojects: {str(e)}')
        return JsonResponse({'subprojects': []}, status=500)

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

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save(commit=False)
            initial_stage = WorkflowStage.objects.order_by('order').first()
            if not initial_stage:
                messages.error(self.request, _("مرحله اولیه جریان کاری تعریف نشده است."))
                return self.form_invalid(form)

            user_orgs = set(up.post.organization for up in self.request.user.userpost_set.filter(is_active=True))
            if not user_orgs:
                messages.error(self.request, _("شما به هیچ سازمانی دسترسی ندارید."))
                return self.form_invalid(form)

            project = form.cleaned_data['project']
            project_orgs = set(project.organizations.all())
            if not project_orgs.intersection(user_orgs):
                messages.error(self.request, _("این پروژه با سازمان شما هماهنگ نیست."))
                return self.form_invalid(form)

            subproject = form.cleaned_data.get('subproject')
            if subproject and subproject.project != project:
                messages.error(self.request, _("زیرپروژه باید متعلق به پروژه انتخاب‌شده باشد."))
                return self.form_invalid(form)

            self.object.subproject = subproject
            self.object.organization = form.cleaned_data['organization']
            self.object.current_stage = initial_stage
            self.object.status = 'DRAFT'
            self.object.created_by = self.request.user
            self.object.save()

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

        # تنظیم مقادیر بودجه
        if project:
            context['total_budget'] = get_project_total_budget(project)
            context['remaining_budget'] = get_project_remaining_budget(project)
        else:
            context['total_budget'] = Decimal('0')
            context['remaining_budget'] = Decimal('0')

        if subproject:
            context['subproject_total_budget'] = get_subproject_total_budget(subproject)
            context['subproject_remaining_budget'] = get_subproject_remaining_budget(subproject)
        else:
            context['subproject_total_budget'] = Decimal('0')
            context['subproject_remaining_budget'] = Decimal('0')

        return context

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return super().handle_no_permission()

class old__TankhahCreateView(PermissionBaseView, CreateView):
    model = Tankhah
    form_class = TankhahForm
    template_name = 'tankhah/Tankhah_form.html'
    success_url = reverse_lazy('tankhah_list')
    context_object_name = 'Tankhah'
    permission_codenames = ['tankhah.Tankhah_add']  # فرمت درست
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    check_organization = True  # فعال کردن چک سازمان

    def get_form_kwargs(self):
        """ارسال کاربر به فرم برای فیلتر کردن گزینه‌ها"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save(commit=False)
            initial_stage = WorkflowStage.objects.order_by('order').first()
            # logger.info(f'initial_stage is: {initial_stage}')
            if not initial_stage:
                messages.error(self.request, _("مرحله اولیه جریان کاری تعریف نشده است."))
                return self.form_invalid(form)

            # گرفتن سازمان کاربر
            # user_orgs = set(up.post.organization for up in self.request.user.userpost_set.all())
            user_orgs = set(up.post.organization for up in self.request.user.userpost_set.filter(is_active=True))
            if not user_orgs:
                messages.error(self.request, "شما به هیچ سازمانی دسترسی ندارید.")
                return self.form_invalid(form)

                # گرفتن پروژه از فرم
                project = form.cleaned_data['project']
                # چک کردن هماهنگی پروژه با سازمان کاربر
                project_orgs = set(project.organizations.all())
                if not project_orgs.intersection(user_orgs):
                    messages.error(self.request, "این پروژه با سازمان شما هماهنگ نیست.")
                    return self.form_invalid(form)

                # گرفتن ساب‌پروژه از فرم
                subproject = form.cleaned_data.get('subproject')
                if not subproject:
                    subproject = SubProject.objects.filter(project=project, organization__in=user_orgs).first()
                    if not subproject:
                        messages.error(self.request, "هیچ زیرپروژه‌ای برای این پروژه و سازمان شما یافت نشد.")
                        return self.form_invalid(form)

                # مقداردهی فیلدها
                self.object.subproject = subproject
                self.object.organization = form.cleaned_data['organization']  # از فرم می‌گیریم
                self.object.current_stage = initial_stage
                self.object.status = 'DRAFT'
                self.object.created_by = self.request.user
                self.object.save()

            # نوتیفیکیشن برای تأییدکنندگان مرحله اولیه
            approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=initial_stage)
            if approvers.exists():
                notify.send(
                    sender=self.request.user,
                    recipient=approvers,
                    verb='تنخواه برای تأیید آماده است',
                    target=self.object
                )
                # logger.info(f"Notification sent to {approvers.count()} approvers for stage {initial_stage.name}")

        messages.success(self.request, 'تنخواه با موفقیت ثبت شد.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد تنخواه جدید')

        if 'project' in self.request.POST:
            try:
                project_id = int(self.request.POST.get('project'))
                project = Project.objects.get(id=project_id)
                context['total_budget'] = get_project_total_budget(project)
                context['remaining_budget'] = get_project_remaining_budget(project)
                if 'subproject' in self.request.POST:
                    subproject_id = int(self.request.POST.get('subproject'))
                    subproject = SubProject.objects.get(id=subproject_id)
                    context['subproject_total_budget'] = get_subproject_total_budget(subproject)
                    context['subproject_remaining_budget'] = get_subproject_remaining_budget(subproject)
            except (ValueError, Project.DoesNotExist, SubProject.DoesNotExist):
                context['total_budget'] = Decimal('0')
                context['remaining_budget'] = Decimal('0')
                context['subproject_total_budget'] = Decimal('0')
                context['subproject_remaining_budget'] = Decimal('0')
        else:
            context['total_budget'] = Decimal('0')
            context['remaining_budget'] = Decimal('0')
            context['subproject_total_budget'] = Decimal('0')
            context['subproject_remaining_budget'] = Decimal('0')

        return context

    def handle_no_permission(self):
        """مدیریت خطای عدم دسترسی"""
        messages.error(self.request, self.permission_denied_message)
        return super().handle_no_permission()

# تأیید و ویرایش تنخواه
class TankhahUpdateView(PermissionBaseView, UpdateView):
    model = Tankhah
    form_class = TankhahForm
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

        next_post = Post.objects.filter(parent=user_post.post, organization=tankhah.organization).first() or \
                    Post.objects.filter(organization__org_type='HQ', branch=tankhah.current_stage, level=1).first()
        if next_post:
            tankhah.last_stopped_post = next_post
        tankhah.save()
        messages.success(self.request, _('تنخواه با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)
# -------
class TankhahListView(PermissionBaseView, ListView):
    model = Tankhah
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
            queryset = Tankhah.objects.all()
            logger.info("کاربر HQ هست، همه تنخواه‌ها رو می‌بینه")
        elif user_orgs:
            queryset = Tankhah.objects.filter(organization__in=user_orgs)
            logger.info(f"فیلتر تنخواه‌ها برای سازمان‌های کاربر: {user_orgs}")
        else:
            queryset = Tankhah.objects.none()
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

        final_queryset = queryset.order_by('-date')
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

        return context

class TankhahListView1(PermissionBaseView, ListView):
    model = Tankhah
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

        # شروع با تنخواه‌های مجاز
        if is_hq_user:
            queryset = Tankhah.objects.all()  # HQ همه تنخواه‌ها رو می‌بینه
            logger.info("کاربر HQ هست، همه تنخواه‌ها رو می‌بینه")
        elif user_orgs:
            queryset = Tankhah.objects.filter(organization__in=user_orgs)  # فقط تنخواه‌های سازمان کاربر
            logger.info(f"فیلتر تنخواه‌ها برای سازمان‌های کاربر: {user_orgs}")
        else:
            queryset = Tankhah.objects.none()  # اگه سازمانی نداشت، هیچی نشون نده
            logger.info("کاربر هیچ سازمانی نداره، queryset خالی برمی‌گردونه")

        # فیلترهای اضافی
        if not self.request.GET.get('show_archived'):
            queryset = queryset.filter(is_archived=False)
            logger.info(f"Filtered by archived count: {queryset.count()}")

        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                models.Q(number__icontains=query) |
                models.Q(organization__name__icontains=query)
            )
            logger.info(f"Filtered by query '{query}' count: {queryset.count()}")

        stage = self.request.GET.get('stage')
        if stage:
            queryset = queryset.filter(current_stage__order=stage)
            logger.info(f"Filtered by stage order {stage} count: {queryset.count()}")

        if not queryset.exists():
            messages.info(self.request, _('هیچ تنخواهی با این شرایط یافت نشد.'))

        final_queryset = queryset.order_by('-date')
        logger.info(f"Final queryset count: {final_queryset.count()}")
        return final_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()] if self.request.user.userpost_set.exists() else []
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
        return context

class TankhahDetailView(PermissionBaseView, PermissionRequiredMixin, DetailView):
    model = Tankhah
    template_name = 'tankhah/Tankhah_detail.html'
    context_object_name = 'Tankhah'
    permission_required = (
        'tankhah.Tankhah_view', 'tankhah.tankhah_update',
        'tankhah.Tankhah_hq_view', 'tankhah.Tankhah_HQ_OPS_APPROVED', 'tankhah.edit_full_tankhah'
    )

    def has_permission(self):
        return any(self.request.user.has_perm(perm) for perm in self.get_permission_required())

    def get_object(self, queryset=None):
        tankhah = get_object_or_404(Tankhah, pk=self.kwargs['pk'])
        restrict_to_user_organization(self.request.user, tankhah.organization)
        return tankhah

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['factors'] = self.object.factors.all()  # اصلاح: اضافه کردن .all()
        context['title'] = _('جزئیات تنخواه') + f" - {self.object.number}"
        context['approval_logs'] = ApprovalLog.objects.filter(tankhah=self.object).order_by('timestamp')
        context['current_date'] = jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M')
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
    model = Tankhah
    template_name = 'tankhah/Tankhah_confirm_delete.html'
    success_url = reverse_lazy('tankhah_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تنخواه با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)
# ویو تأیید:
class TankhahApproveView(PermissionBaseView, View):
    permission_codenames = ['tankhah.Tankhah_approve']

    def post(self, request, pk):
        tankhah = get_object_or_404(Tankhah, pk=pk)
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
        next_stage = WorkflowStage.objects.filter(order__gt=tankhah.current_stage.order).order_by('order').first()
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
        if not any(p.post.stageapprover_set.filter(stage=Tankhah.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه رد این مرحله را ندارید.'))
            return redirect('dashboard_flows')

        Tankhah.status = 'REJECTED'
        Tankhah.save()
        messages.error(request, _('تنخواه رد شد.'))
        return redirect('dashboard_flows')
# ویو نهایی تنخواه تایید یا رد شده
class TankhahFinalApprovalView(UpdateView):
    """ویو نهایی تنخواه تایید یا رد شده """
    model = Tankhah
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
                self.object.current_stage = WorkflowStage.objects.get(name='HQ_FIN')
                self.object.is_archived = True
                self.object.save()
                messages.success(self.request, _('تنخواه پرداخت و آرشیو شد.'))
            elif self.object.status == 'REJECTED':
                messages.warning(self.request, _('تنخواه رد شد.'))
        return super().form_valid(form)
###########################################
    #* ** * * ** * ** **
class FactorCreateView___(PermissionBaseView, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/factor_form.html'
    success_url = reverse_lazy('factor_list')
    context_object_name = 'factor'
    permission_denied_message = 'متاسفانه دسترسی مجاز ندارید'
    permission_codenames = ['tankhah.a_factor_add']
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = Tankhah.objects.get(id=self.kwargs.get('tankhah_id', None)) if 'tankhah_id' in self.kwargs else None
        if self.request.POST:
            factor = self.form_class(self.request.POST, user=self.request.user, tankhah=tankhah).save(commit=False)
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, instance=factor)
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES)
        else:
            context['item_formset'] = FactorItemFormSet()
            context['document_form'] = FactorDocumentForm()
            context['tankhah_document_form'] = TankhahDocumentForm()
        context['title'] = 'ایجاد فاکتور جدید'
        context['tankhah'] = tankhah
        context['tankhah_documents'] = tankhah.documents.all() if tankhah else []

        for factor in context['factors']:
            tankhah = factor.tankhah
            current_stage_order = tankhah.current_stage.order
            user = self.request.user
            user_posts = user.userpost_set.all()
            user_can_approve = any(
                p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists()
                for p in user_posts
            ) and tankhah.status in ['DRAFT', 'PENDING']
            factor.can_approve = user_can_approve

            # چک قفل بودن برای مراحل پایین‌تر
            factor.is_locked = factor.locked_by_stage is not None and factor.locked_by_stage.order > current_stage_order

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        if 'tankhah_id' in self.kwargs:
            kwargs['tankhah'] = Tankhah.objects.get(id=self.kwargs['tankhah_id'])
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        document_form = context['document_form']
        tankhah_document_form = context['tankhah_document_form']
        tankhah = form.cleaned_data['tankhah']

        # فقط در مرحله اولیه (بالاترین order) اجازه ثبت
        initial_stage_order = WorkflowStage.objects.order_by('-order').first().order  # بالاترین order
        if tankhah.current_stage.order != initial_stage_order:
            messages.error(self.request, 'فقط در مرحله اولیه می‌توانید فاکتور ثبت کنید.')
            return self.form_invalid(form)

        if tankhah.status not in ['DRAFT', 'PENDING']:
            messages.error(self.request, 'فقط برای تنخواه‌های پیش‌نویس یا در انتظار می‌توانید فاکتور ثبت کنید.')
            return self.form_invalid(form)

        if item_formset.is_valid() and document_form.is_valid() and tankhah_document_form.is_valid():
            with transaction.atomic():
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()

                # آپلود اسناد فاکتور
                factor_files = self.request.FILES.getlist('files')
                for file in factor_files:
                    FactorDocument.objects.create(factor=self.object, file=file)

                # آپلود اسناد تنخواه
                tankhah_files = self.request.FILES.getlist('documents')
                for file in tankhah_files:
                    TankhahDocument.objects.create(tankhah=tankhah, document=file)

                # تأیید خودکار توسط کارشناس
                user_posts = self.request.user.userpost_set.all()
                if any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
                    for item in self.object.items.all():
                        item.status = 'APPROVED'
                        item.save()
                        ApprovalLog.objects.create(
                            factor_item=item,
                            user=self.request.user,
                            action='APPROVE',
                            stage=tankhah.current_stage,
                            post=user_posts.first().post if user_posts.exists() else None
                        )
                    self.object.status = 'APPROVED'
                    self.object.approved_by.add(self.request.user)
                    self.object.save()

                    # انتقال به مرحله بعدی (order پایین‌تر)
                    next_stage = WorkflowStage.objects.filter(order__lt=tankhah.current_stage.order).order_by(
                        '-order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                        tankhah.status = 'PENDING'
                        tankhah.save()
                        self.object.locked_by_stage = next_stage  # قفل برای مراحل بالاتر
                        self.object.save()
                        approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                        if approvers.exists():
                            notify.send(self.request.user, recipient=approvers, verb='تنخواه برای تأیید آماده است',
                                        target=tankhah)
                            logger.info(
                                f"Notification sent to {approvers.count()} approvers for stage {next_stage.name}")

            messages.success(self.request, 'فاکتور با موفقیت ثبت و تأیید شد.')
            return super().form_valid(form)
        else:
            logger.info(f"Errors: {item_formset.errors}, {document_form.errors}, {tankhah_document_form.errors}")
            return self.form_invalid(form)

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return super().handle_no_permission()
class FactorCreateView3(PermissionBaseView, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/factor_form.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.a_factor_add']
    check_organization = True

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('tankhah.a_factor_add'):
            messages.error(request, _('شما دسترسی لازم برای ایجاد فاکتور را ندارید.'))
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            tankhah = Tankhah.objects.get(id=self.kwargs.get('tankhah_id')) if 'tankhah_id' in self.kwargs else None
        except Tankhah.DoesNotExist:
            tankhah = None
            messages.error(self.request, _('تنخواه مورد نظر یافت نشد.'))

        if self.request.POST:
            form = self.form_class(self.request.POST, user=self.request.user, tankhah=tankhah)
            # فقط اگه فرم معتبر باشه، instance رو می‌سازیم
            factor = form.instance if form.is_valid() else Factor()
            context['form'] = form
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, instance=factor)
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES)
        else:
            context['form'] = self.form_class(user=self.request.user, tankhah=tankhah)
            context['item_formset'] = FactorItemFormSet()
            context['document_form'] = FactorDocumentForm()
            context['tankhah_document_form'] = TankhahDocumentForm()


        context['title'] = _('ایجاد فاکتور جدید')
        context['tankhah'] = tankhah
        context['tankhah_documents'] = tankhah.documents.all() if tankhah else []
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        document_form = context['document_form']
        tankhah_document_form = context['tankhah_document_form']
        tankhah = form.cleaned_data['tankhah']

        initial_stage_order = WorkflowStage.objects.order_by('order').first().order if WorkflowStage.objects.exists() else None
        if tankhah.current_stage.order != initial_stage_order:
            messages.error(self.request, _('فقط در مرحله اولیه می‌توانید فاکتور ثبت کنید.'))
            return self.form_invalid(form)

        if tankhah.status not in ['DRAFT', 'PENDING']:
            messages.error(self.request, _('فقط برای تنخواه‌های پیش‌نویس یا در انتظار می‌توانید فاکتور ثبت کنید.'))
            return self.form_invalid(form)

        if item_formset.is_valid() and document_form.is_valid() and tankhah_document_form.is_valid():
            with transaction.atomic():
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()

                factor_files = self.request.FILES.getlist('files')
                for file in factor_files:
                    FactorDocument.objects.create(factor=self.object, file=file)

                tankhah_files = self.request.FILES.getlist('documents')
                for file in tankhah_files:
                    TankhahDocument.objects.create(tankhah=tankhah, document=file)

                self.object.status = 'PENDING'
                self.object.save()

            messages.success(self.request, _('فاکتور با موفقیت ثبت شد.'))
            return super().form_valid(form)
        else:
            logger.info(f"Errors: {item_formset.errors}, {document_form.errors}, {tankhah_document_form.errors}")
            return self.form_invalid(form)
class FactorUpdateView222(PermissionBaseView, UpdateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/factor_form.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.a_factor_update','tankhah.FactorDocument_update','tankhah.FactorItem_update']
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object.tankhah
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, instance=self.object)
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES)
        else:
            context['item_formset'] = FactorItemFormSet(instance=self.object)
            context['document_form'] = FactorDocumentForm()
            context['tankhah_document_form'] = TankhahDocumentForm()
        context['title'] = _('ویرایش فاکتور') + f" - {self.object.number}"
        context['tankhah'] = tankhah
        context['tankhah_documents'] = tankhah.documents.all()
        return context

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        initial_stage_order = WorkflowStage.objects.order_by('-order').first().order
        # اجازه ویرایش فقط توی مرحله اولیه یا اگه هنوز تأیید نشده باشه
        if obj.status != 'PENDING' and not request.user.has_perm('tankhah.Factor_full_edit'):
            raise PermissionDenied(_('فاکتور تأییدشده یا ردشده قابل ویرایش نیست.'))
        if obj.tankhah.current_stage.order != initial_stage_order:
            raise PermissionDenied(_('فقط در مرحله اولیه می‌توانید فاکتور را ویرایش کنید.'))
        if obj.locked_by_stage and obj.locked_by_stage.order < obj.tankhah.current_stage.order:
            raise PermissionDenied(_('این فاکتور توسط مرحله بالاتر قفل شده و قابل ویرایش نیست.'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        document_form = context['document_form']
        tankhah_document_form = context['tankhah_document_form']

        if item_formset.is_valid() and document_form.is_valid() and tankhah_document_form.is_valid():
            with transaction.atomic():
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()

                factor_files = self.request.FILES.getlist('files')
                for file in factor_files:
                    FactorDocument.objects.create(factor=self.object, file=file)

                tankhah_files = self.request.FILES.getlist('documents')
                for file in tankhah_files:
                    TankhahDocument.objects.create(tankhah=self.object.tankhah, document=file)

            messages.success(self.request, _('فاکتور با موفقیت به‌روزرسانی شد.'))
            return super().form_valid(form)
        else:
            logger.info(f"Errors: {item_formset.errors}")
            return self.form_invalid(form)
class FactorUpdateView____(PermissionBaseView, UpdateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/factor_form.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.a_factor_update']
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object.tankhah
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, instance=self.object)
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES)
        else:
            context['item_formset'] = FactorItemFormSet(instance=self.object)
            context['document_form'] = FactorDocumentForm()
            context['tankhah_document_form'] = TankhahDocumentForm()
        context['title'] = _('ویرایش فاکتور') + f" - {self.object.number}"
        context['tankhah'] = tankhah
        context['tankhah_documents'] = tankhah.documents.all()
        context['total_amount'] = sum(item.amount * item.quantity for item in self.object.items.all())
        return context


    def get_object(self, queryset=None):
            obj = super().get_object(queryset)
            if getattr(obj, 'locked', False):
                raise PermissionDenied("این فاکتور قفل شده و قابل ویرایش نیست.")
            return obj

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        lowest_level = get_lowest_access_level()  # بالاترین order (پایین‌ترین رتبه)
        initial_stage_order = get_initial_stage_order()  # پایین‌ترین order (مرحله اولیه)
        user_post = request.user.userpost_set.first().post if request.user.userpost_set.exists() else None

        initial_stage_order = WorkflowStage.objects.order_by('order').first().order  # بالاترین order
        if obj.locked_by_stage and obj.locked_by_stage.order < obj.tankhah.current_stage.order:
            raise PermissionDenied(_('این فاکتور توسط مرحله بالاتر قفل شده و قابل ویرایش نیست.'))
        if obj.tankhah.current_stage.order != initial_stage_order:
            raise PermissionDenied(_('فقط در مرحله اولیه می‌توانید فاکتور را ویرایش کنید.'))
        if obj.tankhah.status in ['APPROVED', 'SENT_TO_HQ', 'HQ_OPS_APPROVED', 'PAID']:
            raise PermissionDenied(_('فاکتور تأییدشده یا پرداخت‌شده قابل ویرایش نیست.'))
        if obj.is_finalized and not request.user.has_perm('tankhah.Factor_full_edit'):
            raise PermissionDenied(_('شما اجازه ویرایش این فاکتور نهایی‌شده را ندارید.'))

        if not request.user.is_superuser:
            # چک مرحله اولیه
            if obj.tankhah.current_stage.order != initial_stage_order:
                logger.info(f"مرحله فعلی: {obj.tankhah.current_stage.order}, مرحله اولیه: {initial_stage_order}")
                raise PermissionDenied(_('فقط در مرحله اولیه می‌توانید فاکتور را ویرایش کنید.'))
            # چک وضعیت تأییدشده
            if obj.tankhah.status in ['APPROVED', 'SENT_TO_HQ', 'HQ_OPS_APPROVED', 'PAID']:
                raise PermissionDenied(_('فاکتور تأییدشده یا پرداخت‌شده قابل ویرایش نیست.'))
            # اگه نهایی‌شده باشه و کاربر مجوز کامل نداشته باشه
            if getattr(obj, 'is_finalized', False) and not request.user.has_perm('tankhah.Factor_full_edit'):
                raise PermissionDenied(_('شما اجازه ویرایش این فاکتور نهایی‌شده را ندارید.'))
            # کاربر سطح پایین باید بتونه ویرایش کنه
            if user_post and user_post.level != lowest_level and not request.user.has_perm('tankhah.Factor_full_edit'):
                raise PermissionDenied(_('فقط کاربران سطح پایین یا دارای مجوز کامل می‌توانند ویرایش کنند.'))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        if self.object:
            tankhah = self.object.tankhah
            restrict_to_user_organization(self.request.user, tankhah.organization)
            kwargs['tankhah'] = tankhah
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        document_form = context['document_form']
        tankhah_document_form = context['tankhah_document_form']

        if item_formset.is_valid() and document_form.is_valid() and tankhah_document_form.is_valid():
            with transaction.atomic():
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()  # ذخیره ردیف‌های جدید و ویرایش‌شده

                factor_files = self.request.FILES.getlist('files')
                for file in factor_files:
                    FactorDocument.objects.create(factor=self.object, file=file)

                tankhah_files = self.request.FILES.getlist('documents')
                for file in tankhah_files:
                    TankhahDocument.objects.create(tankhah=self.object.tankhah, document=file)

            messages.success(self.request, _('فاکتور با موفقیت به‌روزرسانی شد.'))
            return super().form_valid(form)
        else:
            logger.info(f"Formset errors: {item_formset.errors}")
            return self.form_invalid(form)
## - --  -*  ** *
class FactorDeleteView1(PermissionBaseView, DeleteView):

    model = Factor
    template_name = 'tankhah/factor_confirm_delete.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.a_factor_delete']
    check_organization = True

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"شروع dispatch برای حذف فاکتور با pk={kwargs.get('pk')}, کاربر: {request.user}")
        factor = self.get_object()
        logger.info(
            f"فاکتور: {factor.number}, وضعیت: {factor.status}, مرحله تنخواه: {factor.tankhah.current_stage.order}")

        lowest_level = get_lowest_access_level()
        initial_stage_order = get_initial_stage_order()
        logger.info(f"پایین‌ترین سطح دسترسی: {lowest_level}, مرحله اولیه: {initial_stage_order}")

        if not request.user.is_superuser:
            logger.info(f"کاربر {request.user} سوپروایزر نیست، چک شرایط شروع شد")
            if factor.tankhah.current_stage.order != initial_stage_order:
                logger.info("شرط مرحله اولیه رد شد")
                messages.error(request, _('حذف فاکتور فقط در مرحله اولیه امکان‌پذیر است.'))
                return redirect('factor_list')
            if factor.tankhah.status in ['APPROVED', 'SENT_TO_HQ', 'HQ_OPS_APPROVED', 'PAID']:
                logger.info("شرط وضعیت تأییدشده رد شد")
                messages.error(request, _('فاکتور تأییدشده یا پرداخت‌شده قابل حذف نیست.'))
                return redirect('factor_list')
            user_post = request.user.userpost_set.first().post if request.user.userpost_set.exists() else None
            logger.info(
                f"پست کاربر: {user_post.name if user_post else 'هیچ پستی نیست'}, سطح: {user_post.level if user_post else 'نامشخص'}")
            # if factor.status != 'REJECTED' or (user_post and user_post.level != lowest_level):
            if factor.status != 'REJECTED' or (user_post and user_post.level < lowest_level):
                logger.info("شرط کاربر سطح پایین و فاکتور ردشده رد شد")
                messages.error(request, _('فقط کاربران سطح پایین می‌توانند فاکتور ردشده را حذف کنند.'))
                return redirect('factor_list')
        else:
            logger.info(f"کاربر {request.user} سوپروایزر است، همه محدودیت‌ها نادیده گرفته شد")

        logger.info("همه شرط‌ها تأیید شد، ادامه dispatch")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        logger.info("درخواست POST برای حذف فاکتور دریافت شد")
        return super().post(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        logger.info("حذف فاکتور با موفقیت انجام شد")
        messages.success(self.request, _('فاکتور با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)

    def handle_no_permission(self):
        logger.info("دسترسی رد شد در handle_no_permission")
        messages.error(self.request, _('شما مجوز لازم برای حذف این فاکتور را ندارید.'))
        return redirect('factor_list')
"""  ویو برای تأیید فاکتور"""
class FactorApproveView(UpdateView):
    model = Factor
    form_class = FactorApprovalForm  # فرض بر وجود این فرم
    template_name = 'tankhah/factor_approval.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.a_factor_view', 'tankhah.a_factor_update']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('تأیید فاکتور') + f" - {self.object.number}"
        context['items'] = self.object.items.all()
        return context

    def form_valid(self, form):
        factor = self.object
        tankhah = factor.tankhah
        user_posts = self.request.user.userpost_set.all()

        if not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
            messages.error(self.request, _('شما مجاز به تأیید در این مرحله نیستید.'))
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            all_items_approved = all(item.status == 'APPROVED' for item in self.object.items.all())
            if all_items_approved:
                factor.status = 'APPROVED'
                factor.approved_by.add(self.request.user)
                factor.locked_by_stage = tankhah.current_stage  # قفل برای مراحل بالاتر
                factor.save()

                all_factors_approved = all(f.status == 'APPROVED' for f in tankhah.factors.all())
                if all_factors_approved:
                    next_stage = WorkflowStage.objects.filter(order__lt=tankhah.current_stage.order).order_by('-order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                        tankhah.status = 'PENDING'
                        tankhah.save()
                        approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                        if approvers.exists():
                            notify.send(self.request.user, recipient=approvers, verb='تنخواه برای تأیید آماده است', target=tankhah)
                            messages.info(self.request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                    else:
                        tankhah.status = 'COMPLETED'
                        tankhah.save()
                        messages.success(self.request, _('تنخواه تکمیل شد.'))
                else:
                    messages.success(self.request, _('فاکتور تأیید شد اما فاکتورهای دیگر در انتظارند.'))
            else:
                messages.warning(self.request, _('برخی ردیف‌ها هنوز تأیید نشده‌اند.'))

        return super().form_valid(form)
class FactorApproveView1(PermissionBaseView,UpdateView):
    model = Factor
    form_class = FactorApprovalForm  # فرض می‌کنیم این فرم وجود دارد
    template_name = 'tankhah/factor_approval.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.a_factor_view', 'tankhah.a_factor_update']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('تأیید فاکتور') + f" - {self.object.number}"
        context['items'] = self.object.items.all()
        return context

    def form_valid(self, form):
        factor = self.object
        tankhah = factor.tankhah
        user_posts = self.request.user.userpost_set.all()

        # # چک دسترسی به سازمان
        # try:
        #     restrict_to_user_organization(self.request.user, [Tankhah.organization])
        # except PermissionDenied as e:
        #     messages.error(self.request, str(e))
        #     return self.form_invalid(form)

        # چک اینکه کاربر تأییدکننده این مرحله است
        if not any(p.post.stageapprover_set.filter(stage=Tankhah.current_stage).exists() for p in user_posts):
            messages.error(self.request, _('شما مجاز به تأیید در این مرحله نیستید.'))
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            all_items_approved = all(item.status == 'APPROVED' for item in self.object.items.all())
            if all_items_approved:
                factor.status = 'APPROVED'
                factor.approved_by.add(self.request.user)
                factor.locked_by_stage = tankhah.current_stage  # قفل برای مراحل بالاتر
                factor.save()

                all_factors_approved = all(f.status == 'APPROVED' for f in tankhah.factors.all())
                if all_factors_approved:
                    next_stage = WorkflowStage.objects.filter(order__lt=tankhah.current_stage.order).order_by('-order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                        tankhah.status = 'PENDING'
                        tankhah.save()
                        approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                        if approvers.exists():
                            notify.send(self.request.user, recipient=approvers, verb='تنخواه برای تأیید آماده است', target=tankhah)
                            messages.info(self.request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                    else:
                        tankhah.status = 'COMPLETED'
                        tankhah.save()
                        messages.success(self.request, _('تنخواه تکمیل شد.'))
                else:
                    messages.success(self.request, _('فاکتور تأیید شد اما فاکتورهای دیگر در انتظارند.'))
            else:
                messages.warning(self.request, _('برخی ردیف‌ها هنوز تأیید نشده‌اند.'))

        return super().form_valid(form)

    def handle_no_permission(self):
        messages.error(self.request, _('شما مجوز لازم برای تأیید این فاکتور را ندارید.'))
        return redirect('factor_list')
"""تأیید آیتم‌های فاکتور"""

#--------------------------------------------
"""بررسی سطح فاکتور"""
def mark_approval_seen(request, tankhah):
    user_post = UserPost.objects.filter(user=request.user, end_date__isnull=True).first()
    if user_post:
        ApprovalLog.objects.filter(
            tankhah=tankhah,
            post__level__lte=user_post.post.level,
            seen_by_higher=False
        ).update(seen_by_higher=True, seen_at=timezone.now())
        logger.info(f"Approval logs for Tankhah {tankhah.id} marked as seen by {request.user.username}")

class FactorItemApproveView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_item_approve.html'
    permission_codenames = ['tankhah.FactorItem_approve']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object
        user = self.request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        max_change_level = user_post.post.max_change_level if user_post else 0

        if user_level > factor.tankhah.current_stage.order:
            mark_approval_seen(self.request, factor.tankhah)

        FactorItemApprovalFormSet = formset_factory(FactorItemApprovalForm, extra=0)
        initial_data = [{'item_id': item.id, 'action': item.status.upper()} for item in factor.items.all()]
        context['formset'] = FactorItemApprovalFormSet(self.request.POST or None, initial=initial_data, prefix='items')
        context['item_form_pairs'] = zip(factor.items.all(), context['formset'])

        context['approval_logs'] = ApprovalLog.objects.filter(tankhah=factor.tankhah).order_by('-timestamp')
        context['title'] = _('تأیید ردیف‌های فاکتور') + f" - {factor.number}"
        context['tankhah'] = factor.tankhah
        context['can_edit'] = can_edit_approval(user, factor.tankhah, factor.tankhah.current_stage)
        context['can_change_stage'] = context['can_edit'] and factor.tankhah.current_stage.order < user_level
        context['workflow_stages'] = WorkflowStage.objects.filter(order__lte=max_change_level).order_by('order')
        context['show_payment_number'] = factor.tankhah.status == 'APPROVED' and not factor.tankhah.payment_number
        context['can_final_approve'] = context['can_edit'] and all(
            f.status == 'APPROVED' for f in factor.tankhah.factors.all())
        context['higher_approval_changed'] = ApprovalLog.objects.filter(
            tankhah=factor.tankhah,
            post__level__gt=user_level,
            action__in=['APPROVE', 'REJECT', 'STAGE_CHANGE']
        ).exists()
        # بررسی اینکه آیا تأیید نهایی قبلاً انجام شده یا نه
        context['is_final_approved'] = ApprovalLog.objects.filter(
            tankhah=factor.tankhah,
            action='STAGE_CHANGE',
            comment__contains='تأیید نهایی'
        ).exists()

        logger.info(f"Factor Item IDs: {[item.id for item in factor.items.all()]}")
        logger.info(f"Current Tankhah ID: {factor.tankhah.id}")
        logger.info(f"Approval Logs Count: {context['approval_logs'].count()}")
        logger.info(f"Factor Item Statuses: {[item.status for item in factor.items.all()]}")
        for form in context['formset']:
            logger.info(f"Form Action Value: {form['action'].value()}")

        return context

    def post(self, request, *args, **kwargs):
        factor = self.get_object()
        tankhah = factor.tankhah
        user = request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        max_change_level = user_post.post.max_change_level if user_post else 0

        logger.info(f"POST Request for Factor {factor.pk}:")
        logger.info(f"User: {user.username}, Level: {user_level}, Max Change Level: {max_change_level}")
        logger.info(f"POST Data: {request.POST}")

        if tankhah.is_locked or tankhah.is_archived:
            messages.error(request, _('این تنخواه قفل یا آرشیو شده و قابل تغییر نیست.'))
            return redirect('factor_item_approve', pk=factor.pk)

        can_edit = can_edit_approval(user, tankhah, tankhah.current_stage)
        if not can_edit:
            messages.error(request, _('تأیید توسط سطح بالاتر انجام شده یا خارج از دسترسی شماست.'))
            return redirect('factor_item_approve', pk=factor.pk)

        # تغییر مرحله دستی
        if 'change_stage' in request.POST:
            new_stage_order = int(request.POST.get('new_stage_order'))
            if factor.tankhah.current_stage.order >= user_level:
                messages.error(request, _('شما نمی‌توانید مراحل بالاتر یا برابر با سطح خود را تغییر دهید.'))
                return redirect('factor_item_approve', pk=factor.pk)
            if new_stage_order > max_change_level:
                messages.error(request,
                               _(f"سطح انتخاب‌شده ({new_stage_order}) از حداکثر سطح مجاز شما ({max_change_level}) بیشتر است."))
                return redirect('factor_item_approve', pk=factor.pk)
            new_stage = WorkflowStage.objects.filter(order=new_stage_order).first()
            if new_stage:
                tankhah.current_stage = new_stage
                tankhah.status = 'PENDING'
                tankhah.save()
                ApprovalLog.objects.create(
                    tankhah=tankhah,
                    user=user,
                    action='STAGE_CHANGE',
                    stage=new_stage,
                    comment=f"تغییر مرحله به {new_stage.name} توسط {user.get_full_name()}",
                    post=user_post.post if user_post else None
                )
                messages.success(request, _(f"مرحله تنخواه به {new_stage.name} تغییر یافت."))
            return redirect('factor_item_approve', pk=factor.pk)

        # رد کل فاکتور
        if request.POST.get('reject_factor'):
            with transaction.atomic():
                factor.status = 'REJECTED'
                factor.save()
                for item in factor.items.all():
                    item.status = 'REJECTED'
                    item.save()
                    ApprovalLog.objects.create(
                        tankhah=tankhah,
                        factor_item=item,
                        user=user,
                        action='REJECT',
                        stage=tankhah.current_stage,
                        comment='فاکتور به‌صورت کامل رد شد',
                        post=user_post.post if user_post else None
                    )
                messages.error(request, _('فاکتور به‌صورت کامل رد شد.'))
                logger.info(f"Factor {factor.pk} fully rejected by {user.username}")
            return redirect('dashboard_flows')

        # تأیید نهایی
        if request.POST.get('final_approve'):
            with transaction.atomic():
                if all(f.status == 'APPROVED' for f in tankhah.factors.all()):
                    current_stage_order = tankhah.current_stage.order
                    next_stage = WorkflowStage.objects.filter(order__gt=current_stage_order).order_by('order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                        tankhah.status = 'PENDING'
                        tankhah.save()
                        ApprovalLog.objects.create(
                            tankhah=tankhah,
                            user=user,
                            action='STAGE_CHANGE',
                            stage=next_stage,
                            comment=f"تأیید نهایی و انتقال به مرحله {next_stage.name} توسط {user.get_full_name()}",
                            post=user_post.post if user_post else None
                        )
                        messages.success(request,
                                         _(f"تأیید نهایی انجام شد و تنخواه به مرحله {next_stage.name} منتقل شد."))
                        return redirect('factor_list')
                    elif tankhah.current_stage.is_final_stage:
                        payment_number = request.POST.get('payment_number')
                        if payment_number:
                            tankhah.payment_number = payment_number
                            tankhah.status = 'PAID'
                            tankhah.save()
                            messages.success(request, _('تنخواه پرداخت شد.'))
                            return redirect('factor_list')
                        else:
                            messages.warning(request, _('شماره پرداخت وارد نشده است.'))
                    else:
                        messages.error(request, _('مرحله بعدی وجود ندارد.'))
                else:
                    messages.warning(request, _('همه فاکتورها باید تأیید شده باشند تا تأیید نهایی انجام شود.'))
                return redirect('factor_item_approve', pk=factor.pk)

        # تأیید/رد ردیف‌ها
        FactorItemApprovalFormSet = formset_factory(FactorItemApprovalForm, extra=0)
        initial_data = [{'item_id': item.id, 'action': item.status.upper()} for item in factor.items.all()]
        formset = FactorItemApprovalFormSet(request.POST, initial=initial_data, prefix='items')

        if formset.is_valid():
            with transaction.atomic():
                all_approved = True
                any_rejected = False
                bulk_approve = request.POST.get('bulk_approve') == 'on'
                bulk_reject = request.POST.get('bulk_reject') == 'on'
                has_changes = False

                for form, item in zip(formset, factor.items.all()):
                    action = 'APPROVE' if bulk_approve else ('REJECT' if bulk_reject else form.cleaned_data['action'])
                    if action != item.status:
                        has_changes = True
                        ApprovalLog.objects.create(
                            tankhah=tankhah,
                            factor_item=item,
                            user=user,
                            action=action,
                            stage=tankhah.current_stage,
                            comment=form.cleaned_data.get('comment', ''),
                            post=user_post.post if user_post else None
                        )
                        item.status = action
                        item.save()
                        logger.info(f"Item {item.id} updated to {action} by {user.username}")
                    if action == 'REJECT':
                        all_approved = False
                        any_rejected = True
                    elif action != 'APPROVE':
                        all_approved = False

                higher_approval_changed = ApprovalLog.objects.filter(
                    tankhah=tankhah,
                    post__level__gt=user_level,
                    action__in=['APPROVE', 'REJECT', 'STAGE_CHANGE']
                ).exists()

                if any_rejected:
                    factor.status = 'PENDING'
                    messages.warning(request, _('برخی ردیف‌ها رد شدند.'))
                    # انتقال به رده پایین‌تر اگر ردیفی رد شده باشد
                    current_stage_order = tankhah.current_stage.order
                    if current_stage_order > 1:  # مطمئن می‌شیم به زیر مرحله 1 نره
                        previous_stage = WorkflowStage.objects.filter(order=current_stage_order - 1).first()
                        if previous_stage:
                            tankhah.current_stage = previous_stage
                            tankhah.status = 'PENDING'
                            tankhah.save()
                            ApprovalLog.objects.create(
                                tankhah=tankhah,
                                user=user,
                                action='STAGE_CHANGE',
                                stage=previous_stage,
                                comment=f"انتقال به مرحله پایین‌تر ({previous_stage.name}) به دلیل رد ردیف",
                                post=user_post.post if user_post else None
                            )
                            messages.info(request,
                                          _(f"تنخواه به مرحله {previous_stage.name} منتقل شد به دلیل رد ردیف."))
                elif all_approved and factor.items.exists():
                    factor.status = 'APPROVED'
                    if higher_approval_changed:
                        messages.info(request,
                                      _('سطح بالاتری قبلاً تغییراتی اعمال کرده است و شما نمی‌توانید ادامه دهید.'))
                    elif not has_changes:
                        messages.info(request,
                                      _('هیچ تغییری در وضعیت ردیف‌ها رخ نداده است. برای انتقال به مرحله بعد، تأیید نهایی را بزنید.'))
                    else:
                        messages.success(request, _('فاکتور تأیید شد. برای انتقال به مرحله بعد، تأیید نهایی را بزنید.'))
                else:
                    factor.status = 'PENDING'
                    messages.warning(request, _('برخی ردیف‌ها هنوز تأیید نشده‌اند.'))
                factor.save()

                messages.success(request, _('تغییرات با موفقیت ثبت شدند.'))
            return redirect('factor_item_approve', pk=factor.pk)
        else:
            messages.error(request, _('فرم نامعتبر است.'))
            logger.error(f"Formset errors: {formset.errors}")
            self.object = factor
            return self.render_to_response(self.get_context_data(formset=formset))

class FactorItemRejectView(PermissionBaseView, View):
    permission_codenames = ['tankhah.FactorItem_approve']
    template_name = 'tankhah/factor_item_reject_confirm.html'

    def get(self, request, pk):
        item = get_object_or_404(FactorItem, pk=pk)
        factor = item.factor
        tankhah = factor.tankhah
        user_posts = request.user.userpost_set.all()

        # چک دسترسی
        try:
            restrict_to_user_organization(request.user, [tankhah.organization])
        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('dashboard_flows')

        if not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه رد این ردیف را ندارید.'))
            return redirect('dashboard_flows')

        # نمایش فرم تأیید
        return render(request, self.template_name, {
            'item': item,
            'factor': factor,
            'tankhah': tankhah,
        })

    def post(self, request, pk):
        item = get_object_or_404(FactorItem, pk=pk)
        factor = item.factor
        tankhah = factor.tankhah
        user_posts = request.user.userpost_set.all()

        # چک دسترسی
        try:
            restrict_to_user_organization(request.user, [tankhah.organization])
        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('dashboard_flows')

        if not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه رد این ردیف را ندارید.'))
            return redirect('dashboard_flows')

        # تصمیم کاربر
        keep_in_tankhah = request.POST.get('keep_in_tankhah') == 'yes'

        with transaction.atomic():
            # رد کردن ردیف فاکتور
            item.status = 'REJECTED'
            item.save()
            logger.info(f"ردیف فاکتور {item.id} رد شد توسط {request.user.username}")

            # ثبت در لاگ
            ApprovalLog.objects.create(
                tankhah=tankhah,
                factor_item=item,
                user=request.user,
                action='REJECT',
                stage=tankhah.current_stage,
                comment='رد شده توسط کاربر'
            )

            if keep_in_tankhah:
                # فاکتور توی تنخواه می‌مونه و به تأیید برمی‌گرده
                factor.status = 'PENDING'
                factor.save()
                messages.info(request, _('ردیف فاکتور رد شد و فاکتور برای تأیید دوباره در تنخواه باقی ماند.'))
            else:
                # فاکتور رد می‌شه، تنخواه دست‌نخورده می‌مونه
                factor.status = 'REJECTED'
                factor.save()
                logger.info(f"فاکتور {factor.number} رد شد توسط {request.user.username}")
                messages.error(request, _('فاکتور رد شد و از جریان تأیید خارج شد.'))

        return redirect('dashboard_flows')# ---######## Approval Views ---

class ApprovalListView1(PermissionBaseView, ListView):
    model = ApprovalLog
    template_name = 'tankhah/approval_list.html'
    context_object_name = 'approvals'
    paginate_by = 10
    extra_context = {'title': _('تاریخچه تأییدات')}

    def get_queryset(self):
        # تأییدات کاربر فعلی با اطلاعات مرتبط
        return ApprovalLog.objects.filter(user=self.request.user).select_related(
            'tankhah', 'factor_item', 'factor_item__factor', 'stage', 'post'
        ).order_by('-timestamp')
class ApprovalListView(PermissionBaseView, ListView):
    model = ApprovalLog
    template_name = 'tankhah/approval_list.html'
    context_object_name = 'approvals'
    paginate_by = 10
    extra_context = {'title': _('تاریخچه تأییدات')}

    def get_queryset(self):
        user = self.request.user
        # اگه کاربر HQ هست، همه تأییدات رو نشون بده
        if hasattr(user, 'is_hq') and user.is_hq:
            return ApprovalLog.objects.select_related(
                'tankhah', 'factor_item', 'factor_item__factor', 'stage', 'post'
            ).order_by('-timestamp')
        # در غیر این صورت، فقط تأییدات کاربر فعلی
        return ApprovalLog.objects.filter(user=user).select_related(
            'tankhah', 'factor_item', 'factor_item__factor', 'stage', 'post'
        ).order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # چک کردن امکان تغییر
        for approval in context['approvals']:
            approval.can_edit = (
                (hasattr(user, 'is_hq') and user.is_hq) or  # HQ همیشه می‌تونه تغییر بده
                (approval.user == user and  # کاربر خودش باشه
                 not ApprovalLog.objects.filter(
                     tankhah=approval.tankhah,
                     stage__order__gt=approval.stage.order,
                     action='APPROVE'
                 ).exists())  # هنوز بالادستی تأیید نکرده
            )
        return context

class ApprovalLogListView(PermissionBaseView, ListView):
    model = ApprovalLog
    template_name = 'tankhah/approval_log_list.html'
    context_object_name = 'logs'
    paginate_by = 10

    def get_queryset(self):
        # چک کن که tankhah_number توی kwargs باشه
        tankhah_number = self.kwargs.get('tankhah_number')
        if not tankhah_number:
            raise ValueError("پارامتر 'tankhah_number' در URL تعریف نشده است.")
        return ApprovalLog.objects.filter(tankhah__number=tankhah_number).order_by('-timestamp')

class ApprovalDetailView(PermissionBaseView, DetailView):
    model = ApprovalLog
    template_name = 'tankhah/approval_detail.html'
    context_object_name = 'approval'
    extra_context = {'title': _('جزئیات تأیید')}

class ApprovalCreateView(PermissionRequiredMixin, CreateView):
    model = ApprovalLog
    form_class = ApprovalForm
    template_name = 'tankhah/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'Tankhah.Approval_add'

    def form_valid(self, form):
        form.instance.user = self.request.user
        user_post = UserPost.objects.filter(user=self.request.user, end_date__isnull=True).first()  # فقط پست فعال
        user_level = user_post.post.level if user_post else 0

        # ثبت لاگ و به‌روزرسانی وضعیت
        if form.instance.tankhah:  # دقت کن که Tankhah باید tankhah باشه (کوچیک)
            tankhah = form.instance.tankhah
            current_status = tankhah.status
            branch = form.instance.action

            if hasattr(tankhah, 'current_stage') and branch != tankhah.current_stage.name:  # مقایسه با نام مرحله
                messages.error(self.request, _('شما نمی‌توانید در این مرحله تأیید کنید.'))
                return self.form_invalid(form)

            if form.instance.action == 'APPROVE':
                if branch == 'COMPLEX' and current_status == 'PENDING' and user_level <= 2:
                    tankhah.status = 'APPROVED'
                    tankhah.hq_status = 'SENT_TO_HQ'
                    tankhah.current_stage = WorkflowStage.objects.get(name='OPS')
                elif branch == 'OPS' and current_status == 'APPROVED' and user_level > 2:
                    tankhah.hq_status = 'HQ_OPS_APPROVED'
                    tankhah.current_stage = WorkflowStage.objects.get(name='FIN')
                elif branch == 'FIN' and tankhah.hq_status == 'HQ_OPS_APPROVED' and user_level > 3:
                    tankhah.hq_status = 'HQ_FIN_PENDING'
                    tankhah.status = 'PAID'
                else:
                    messages.error(self.request, _('شما اجازه تأیید در این مرحله را ندارید یا وضعیت نادرست است.'))
                    return self.form_invalid(form)
            else:
                tankhah.status = 'REJECTED'
            tankhah.last_stopped_post = user_post.post if user_post else None
            tankhah.save()

            # ثبت لاگ برای تنخواه
            form.instance.stage = tankhah.current_stage
            form.instance.post = user_post.post if user_post else None

        elif form.instance.factor:
            factor = form.instance.factor
            tankhah = factor.tankhah  # گرفتن تنخواه مرتبط
            factor.status = 'APPROVED' if form.instance.action == 'APPROVE' else 'REJECTED'
            factor.save()

            # ثبت لاگ برای فاکتور
            form.instance.tankhah = tankhah
            form.instance.stage = tankhah.current_stage if tankhah else None
            form.instance.post = user_post.post if user_post else None

        elif form.instance.factor_item:
            item = form.instance.factor_item
            tankhah = item.factor.tankhah  # گرفتن تنخواه از ردیف فاکتور
            if hasattr(item, 'status'):
                item.status = 'APPROVED' if form.instance.action == 'APPROVE' else 'REJECTED'
                item.save()
            else:
                messages.warning(self.request, _('ردیف فاکتور فاقد وضعیت است و تأیید اعمال نشد.'))

            # ثبت لاگ برای ردیف فاکتور
            form.instance.tankhah = tankhah
            form.instance.stage = tankhah.current_stage if tankhah else None
            form.instance.post = user_post.post if user_post else None

        messages.success(self.request, _('تأیید با موفقیت ثبت شد.'))
        return super().form_valid(form)

    def can_approve_user(self, user, tankhah):
        current_stage = tankhah.current_stage
        approver_posts = StageApprover.objects.filter(stage=current_stage).values_list('post', flat=True)
        user_posts = user.userpost_set.filter(end_date__isnull=True).values_list('post', flat=True)
        return bool(set(user_posts) & set(approver_posts))

    def get_initial(self):
        initial = super().get_initial()
        initial['tankhah'] = self.request.GET.get('tankhah')  # کوچیک شده
        initial['factor'] = self.request.GET.get('factor')
        initial['factor_item'] = self.request.GET.get('factor_item')
        return initial

    def dispatch(self, request, *args, **kwargs):
        # اصلاح برای گرفتن tankhah
        if 'tankhah' in request.GET:
            tankhah = Tankhah.objects.get(pk=request.GET['tankhah'])
        elif 'factor' in request.GET:
            tankhah = Factor.objects.get(pk=request.GET['factor']).tankhah
        elif 'factor_item' in request.GET:
            tankhah = FactorItem.objects.get(pk=request.GET['factor_item']).factor.tankhah
        else:
            raise PermissionDenied(_('تنخواه مشخص نشده است.'))

        if not self.can_approve_user(request.user, tankhah):
            raise PermissionDenied(_('شما مجاز به تأیید در این مرحله نیستید.'))
        return super().dispatch(request, *args, **kwargs)

class ApprovalUpdateView(PermissionBaseView, UpdateView):
    model = ApprovalLog
    form_class = ApprovalForm
    template_name = 'tankhah/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_codenames = ['tankhah.Approval_update']

    def get_queryset(self):
        return ApprovalLog.objects.filter(user=self.request.user)

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        tankhah = self.object.tankhah
        current_stage = tankhah.current_stage
        user_posts = UserPost.objects.filter(user=request.user, end_date__isnull=True).values_list('post', flat=True)
        approver_posts = StageApprover.objects.filter(stage=current_stage).values_list('post', flat=True)
        can_edit = bool(set(user_posts) & set(approver_posts))

        if not can_edit:
            raise PermissionDenied(_('شما نمی‌توانید این تأیید را ویرایش کنید، چون مرحله تغییر کرده یا دسترسی ندارید.'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        approval = form.instance
        tankhah = approval.tankhah
        user_post = UserPost.objects.filter(user=self.request.user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0

        # به‌روزرسانی وضعیت و انتقال مرحله
        if tankhah:
            current_status = tankhah.status
            branch = form.instance.action

            if tankhah.current_stage != approval.stage:
                messages.error(self.request, _('مرحله تغییر کرده و نمی‌توانید این تأیید را ویرایش کنید.'))
                return self.form_invalid(form)

            if form.instance.action == 'APPROVE':
                if branch == 'COMPLEX' and current_status == 'PENDING' and user_level <= 2:
                    tankhah.status = 'APPROVED'
                    tankhah.hq_status = 'SENT_TO_HQ'
                    next_stage = WorkflowStage.objects.filter(order__gt=tankhah.current_stage.order).order_by(
                        'order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                elif branch == 'OPS' and current_status == 'APPROVED' and user_level > 2:
                    tankhah.hq_status = 'HQ_OPS_APPROVED'
                    next_stage = WorkflowStage.objects.filter(order__gt=tankhah.current_stage.order).order_by(
                        'order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                elif branch == 'FIN' and tankhah.hq_status == 'HQ_OPS_APPROVED' and user_level > 3:
                    tankhah.hq_status = 'HQ_FIN_PENDING'
                    tankhah.status = 'PAID'
                    next_stage = None  # مرحله آخر
                else:
                    messages.error(self.request, _('شما اجازه ویرایش در این مرحله را ندارید یا وضعیت نادرست است.'))
                    return self.form_invalid(form)

                # انتقال به مرحله بعدی و اعلان
                if next_stage:
                    tankhah.save()
                    approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage,
                                                          userpost__end_date__isnull=True)
                    if approvers.exists():
                        notify.send(self.request.user, recipient=approvers, verb='تنخواه در انتظار تأیید',
                                    target=tankhah)
                    messages.info(self.request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                else:
                    tankhah.is_locked = True
                    tankhah.is_archived = True
                    tankhah.save()
                    messages.success(self.request, _('تنخواه تکمیل و آرشیو شد.'))

            elif form.instance.action == 'REJECT':
                tankhah.status = 'REJECTED'
                tankhah.last_stopped_post = user_post.post if user_post else None
                tankhah.save()
                messages.warning(self.request, _('تنخواه رد شد.'))

        messages.success(self.request, _('تأیید با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('خطا در ویرایش تأیید. لطفاً ورودی‌ها را بررسی کنید.'))
        return super().form_invalid(form)

class ApprovalDeleteView(PermissionBaseView, DeleteView):
    model = ApprovalLog
    template_name = 'tankhah/approval_confirm_delete.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'Tankhah.Approval_delete'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تأیید با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)

# -- وضعیت تنخواه
@login_required
def upload_tankhah_documents(request, tankhah_id):
    tankhah = Tankhah.objects.get(id=tankhah_id)
    if request.method == 'POST':
        form = TankhahDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('documents')
            for file in files:
                TankhahDocument.objects.create(Tankhah=Tankhah, document=file)
            messages.success(request, 'اسناد با موفقیت آپلود شدند.')
            return redirect('Tankhah_detail', pk=Tankhah.id)
        else:
            messages.error(request, 'خطایی در آپلود اسناد رخ داد.')
    else:
        form = TankhahDocumentForm()

    return render(request, 'tankhah/upload_documents.html', {
        'form': form,
        'Tankhah': Tankhah,
        'existing_documents': Tankhah.documents.all()
    })

class FactorStatusUpdateView(PermissionBaseView, View):
    permission_required = 'tankhah.FactorItem_approve'

    def post(self, request, pk, *args, **kwargs):
        factor = Factor.objects.get(pk=pk)
        tankhah = factor.tankhah
        action = request.POST.get('action')

        if tankhah.is_locked or tankhah.is_archived:
            messages.error(request, _('این تنخواه قفل یا آرشیو شده و قابل تغییر نیست.'))
            return redirect('tankhah_tracking', pk=tankhah.pk)

        user_post = request.user.userpost_set.filter(end_date__isnull=True).first()
        if action == 'REJECT' and factor.status == 'APPROVED':
            factor.status = 'REJECTED'
            tankhah.status = 'REJECTED'
            tankhah.last_stopped_post = user_post.post if user_post else None
        elif action == 'APPROVE' and factor.status == 'REJECTED':
            factor.status = 'APPROVED'
            tankhah.status = 'PENDING' if any(f.status != 'APPROVED' for f in tankhah.factors.all()) else 'APPROVED'

        factor.save()
        tankhah.save()

        # ثبت لاگ
        ApprovalLog.objects.create(
            tankhah=tankhah,
            factor=factor,
            user=request.user,
            action=action,
            stage=tankhah.current_stage,
            post=user_post.post if user_post else None
        )

        # آپدیت مرحله
        workflow_stages = WorkflowStage.objects.order_by('order')
        current_stage = tankhah.current_stage
        if not current_stage:
            tankhah.current_stage = workflow_stages.first()
            tankhah.save()

        # چک کردن تأیید همه فاکتورها توی مرحله فعلی
        approvals_in_current = ApprovalLog.objects.filter(
            tankhah=tankhah, stage=current_stage, action='APPROVE'
        ).count()
        factors_count = tankhah.factors.count()
        if approvals_in_current >= factors_count and action == 'APPROVE':
            # next_stage = workflow_stages.filter(order__gt=current_stage.order).first()
            next_stage = workflow_stages.filter(order__lt=current_stage.order).order_by('-order').first()

            if next_stage:
                tankhah.current_stage = next_stage
                tankhah.status = 'PENDING'
                tankhah.save()
                messages.info(request, _(f"تنخواه به مرحله {next_stage.name} منتقل شد."))
            elif all(f.status == 'APPROVED' for f in tankhah.factors.all()):
                tankhah.status = 'APPROVED'
                tankhah.save()
                messages.info(request, _('تنخواه کاملاً تأیید شد.'))

        messages.success(request, _('وضعیت فاکتور با موفقیت تغییر کرد.'))
        return redirect('tankhah_tracking', pk=tankhah.pk)

@require_POST
def mark_notification_as_read(request, notif_id):
    notif = Notification.objects.get(id=notif_id, user=request.user)
    notif.is_read = True
    notif.save()
    return JsonResponse({'status': 'success'})
