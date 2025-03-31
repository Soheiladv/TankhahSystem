import logging
import jdatetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.forms import formset_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
from jalali_date.fields import JalaliDateField
from notifications.signals import notify
from accounts.models import CustomUser
# Local imports
from core.models import UserPost, Post, WorkflowStage
from .forms import (
    ApprovalForm, FactorItemApprovalForm, FactorApprovalForm, TankhahDocumentForm, FactorDocumentForm, FactorForm,
    FactorItemFormSet, TankhahForm, TankhahStatusForm
)
from .models import (
    Factor, ApprovalLog, FactorItem, TankhahDocument, FactorDocument, Tankhah, StageApprover)
from .utils import restrict_to_user_organization

# Logger configuration
logger = logging.getLogger(__name__)
# --- Factor Views ---
from django.utils.translation import gettext_lazy as _
from persiantools.jdatetime import JalaliDate  # ایمپورت درست
from datetime import datetime
# tankhah/views.py
from django.views.generic.list import ListView
from django.db.models import Q
from .models import Factor
from core.views import PermissionBaseView
from django.utils.translation import gettext_lazy as _
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

class TankhahCreateView(PermissionBaseView, CreateView):
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
        """ثبت تنخواه با پایین‌ترین مرحله و ارسال اعلان"""
        tankhah = form.instance
        tankhah.created_by = self.request.user
        tankhah.status = 'DRAFT'

        # تنظیم پایین‌ترین مرحله
        try:
            first_stage = WorkflowStage.objects.order_by('-order').first()  # بالاترین order = پایین‌ترین مرحله
            print(f'first_stage : {first_stage}')
            if not first_stage:
                logger.error("No workflow stages defined!")
                messages.error(self.request, _('هیچ مرحله‌ای در سیستم تعریف نشده است.'))
                return self.form_invalid(form)
            # if first_stage.order != 1:  # اطمینان از اینکه پایین‌ترین مرحله order=1 است
            #     logger.warning(f"First stage {first_stage.name} has order {first_stage.order}, expected 1")
            # Tankhah.current_stage = first_stage
            # logger.info(f"Setting Tankhah {Tankhah.number} to stage: {first_stage.name} (order={first_stage.order})")

            tankhah.current_stage = first_stage

            # چک سازمان
            if self.check_organization:
                user_orgs = [up.post.organization for up in
                             self.request.user.userpost_set.all()] if self.request.user.userpost_set.exists() else []
                is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False
                if not is_hq_user and tankhah.organization not in user_orgs:
                    logger.warning(f"User {self.request.user} has no access to organization {tankhah.organization}")
                    messages.error(self.request, "شما به این سازمان دسترسی ندارید.")
                    return self.form_invalid(form)

        except Exception as e:
            logger.error(f"Error setting stage: {str(e)}")
            messages.error(self.request, _('خطا در تنظیم مرحله تنخواه.'))
            return self.form_invalid(form)

        # ذخیره تنخواه
        response = super().form_valid(form)

        # ارسال اعلان به تأییدکنندگان مرحله اول
        approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=first_stage)
        if approvers.exists():
            notify.send(
                sender=self.request.user,
                recipient=approvers,
                verb='تنخواه جدیدی ایجاد شد',
                target=tankhah
            )
            logger.info(f"Notification sent to {approvers.count()} approvers for stage {first_stage.name}")
        else:
            logger.warning(f"No approvers found for stage {first_stage.name}")

        messages.success(self.request, _('تنخواه با موفقیت ثبت شد.'))
        return response

    def get_context_data(self, **kwargs):
        """اضافه کردن عنوان به کنتکست"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد تنخواه جدید')
        return context

    def handle_no_permission(self):
        """مدیریت خطای عدم دسترسی"""
        messages.error(self.request, self.permission_denied_message)
        return super().handle_no_permission()
# تأیید و ویرایش تنخواه
from django.contrib.auth.mixins import UserPassesTestMixin
class TankhahUpdateView(UserPassesTestMixin, UpdateView):
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
class TankhahListView1(PermissionBaseView, PermissionRequiredMixin, ListView):
    model = Tankhah
    template_name = 'tankhah/tankhah_list.html'
    context_object_name = 'Tankhahs'
    paginate_by = 10
    extra_context = {'title': _('لیست تنخواه‌ها')}

    # لیست مجوزها
    permission_required = (
        'Tankhah.Tankhah_view', 'Tankhah_update', 'Tankhah_add',
        'Tankhah.Tankhah_approve',
        'Tankhah.Tankhah_part_approve',
        'Tankhah.FactorItem_approve', 'edit_full_Tankhah',
        'Tankhah_hq_view',
        'Tankhah_hq_approve', 'Tankhah_HQ_OPS_PENDING', 'Tankhah_HQ_OPS_APPROVED', "FactorItem_approve"
    )

    def has_permission(self):
        # چک کردن اینکه کاربر حداقل یکی از مجوزها را دارد
        return any(self.request.user.has_perm(perm) for perm in self.get_permission_required())

    def get_queryset(self):
        user = self.request.user
        user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()]
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)
        queryset = Tankhah.objects.all() if is_hq_user else Tankhah.objects.filter(organization__in=user_orgs)

        if not self.request.GET.get('show_archived'):
            queryset = queryset.filter(is_archived=False)
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(number__icontains=query) | queryset.filter(organization__name__icontains=query)
        stage = self.request.GET.get('stage')
        if stage:
            queryset = queryset.filter(current_stage__order=stage)
        return queryset
        # logger.info('is_hq_user: {}'.format(is_hq_user))
        # query = self.request.GET.get('q', '')
        # if query:
        #     queryset = queryset.filter(
        #         Q(number__icontains=query) |
        #         Q(organization__name__icontains=query) |
        #         Q(project__name__icontains=query, project__isnull=False) |
        #         Q(status__icontains=query) |
        #         Q(letter_number__icontains=query)
        #  )
        #     if not queryset.exists():
        #         messages.info(self.request, _('هیچ تنخواهی با این مشخصات یافت نشد.'))
        # return queryset.order_by('date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('لیست تنخواه‌ها')
        user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()]
        context['user_orgs'] = user_orgs
        context['is_hq_user'] = any(org.org_type == 'HQ' for org in user_orgs)
        context['query'] = self.request.GET.get('q', '')
        context['stage'] = self.request.GET.get('stage', '')
        context['Tankhahs'] = context['object_list']
        context['show_archived'] = self.request.GET.get('show_archived', 'false') == 'true'
        return context
class TankhahListView(PermissionBaseView, ListView):
    model = Tankhah
    template_name = 'tankhah/tankhah_list.html'
    context_object_name = 'Tankhahs'
    paginate_by = 10
    permission_codenames = ['tankhah.Tankhah_view']  # فرمت درست

    def get_queryset(self):
        user = self.request.user
        logger.info(f"User: {user}, is_superuser: {user.is_superuser}")

        # اگه تابع دیگه دسترسی رو چک کرده، فقط تنخواه‌ها رو برگردون
        queryset = Tankhah.objects.all()
        logger.info(f"Initial queryset count: {queryset.count()}")

        if not self.request.GET.get('show_archived'):
            queryset = queryset.filter(is_archived=False)
            logger.info(f"Filtered by archived count: {queryset.count()}")

        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(number__icontains=query) | queryset.filter(organization__name__icontains=query, organization__isnull=False)
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
    permission_codenames = ['Tankhah.Tankhah_approve']

    def get(self, request, pk):
        tankhah = Tankhah.objects.get(pk=pk)
        user_posts = request.user.userpost_set.all()
        if not any(p.post.stageapprover_set.filter(stage=Tankhah.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه تأیید این مرحله را ندارید.'))
            return redirect('dashboard_flows')

        next_stage = WorkflowStage.objects.filter(order__lt=Tankhah.current_stage.order).order_by('-order').first()
        if next_stage:
            Tankhah.current_stage = next_stage
            Tankhah.status = 'PENDING'
            Tankhah.save()
            messages.success(request, _('تنخواه با موفقیت تأیید شد و به مرحله بعدی منتقل شد.'))
            # اعلان به تأییدکنندگان مرحله بعدی
            approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
            if approvers.exists():
                notify.send(sender=request.user, recipient=approvers, verb='تنخواه برای تأیید آماده است',
                            target=Tankhah)
        else:
            Tankhah.status = 'COMPLETED'
            Tankhah.save()
            messages.success(request, _('تنخواه با موفقیت تکمیل شد.'))
        return redirect('dashboard_flows')
# ویو رد:
class TankhahRejectView(PermissionBaseView, View):
    permission_codenames = ['Tankhah.Tankhah_approve']

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
class FactorListView(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tankhah/factor_list.html'
    context_object_name = 'factors'
    paginate_by = 10
    extra_context = {'title': _('لیست فاکتورها')}

    def get_queryset(self):
        user = self.request.user
        user_posts = user.userpost_set.all()
        if not user_posts.exists():
            return Factor.objects.none()

        user_orgs = [up.post.organization for up in user.userpost_set.all()]
        is_hq_user = any(up.post.organization.org_type == 'HQ' for up in user.userpost_set.all())

        if is_hq_user:
            queryset = Factor.objects.all()
        else:
            queryset = Factor.objects.filter(tankhah__organization__in=user_orgs)

        query = self.request.GET.get('q', '').strip()
        date_query = self.request.GET.get('date', '').strip()
        status_query = self.request.GET.get('status', '').strip()

        if query or date_query or status_query:
            filter_conditions = Q()
            if query:
                filter_conditions |= (
                    Q(number__icontains=query) |
                    Q(Tankhah__number__icontains=query) |
                    Q(amount__icontains=query) |
                    Q(description__icontains=query)
                )
            if date_query:
                try:
                    if len(date_query) == 4:  # فقط سال
                        year = int(date_query)
                        gregorian_year = year - 621
                        filter_conditions &= Q(date__year=gregorian_year)
                    else:  # تاریخ کامل
                        year, month, day = map(int, date_query.split('-'))
                        gregorian_date = JalaliDate(year, month, day).to_gregorian()
                        filter_conditions &= Q(date=gregorian_date)
                except (ValueError, Exception):
                    filter_conditions &= Q(date__isnull=True)
            if status_query:
                filter_conditions &= Q(status=status_query)
            queryset = queryset.filter(filter_conditions).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['date_query'] = self.request.GET.get('date', '')
        context['status_query'] = self.request.GET.get('status', '')
        context['is_hq'] = any(up.post.organization.org_type == 'HQ' for up in self.request.user.userpost_set.all())
        return context
class FactorDetailView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_detail.html'  # تمپلیت نمایشی جدید
    context_object_name = 'factor'
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    permission_codename = 'tankhah.a_factor_view'
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.get_object()
        tankhah = factor.tankhah

        context['title'] = _('جزئیات فاکتور') + f" - {factor.number}"
        context['tankhah'] = tankhah
        context['tankhah_documents'] = tankhah.documents.all()

        # محاسبه جمع کل و جمع هر آیتم
        items_with_total = [
            {'item': item, 'total': item.amount * item.quantity}
            for item in factor.items.all()
        ]
        context['items_with_total'] = items_with_total
        context['total_amount'] = sum(item['total'] for item in items_with_total)
        context['difference'] = factor.amount - context['total_amount'] if factor.amount else 0

        return context

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return redirect('factor_list')
class FactorCreateView(PermissionBaseView, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/factor_form.html'
    success_url = reverse_lazy('factor_list')
    context_object_name = 'factor'
    permission_codenames = ['Tankhah.a_factor_add']
    permission_denied_message = 'متاسفانه دسترسی مجاز ندارید'
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = Tankhah.objects.get(id=self.kwargs.get('tankhah_id', None)) if 'tankhah_id' in self.kwargs else None
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES)
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
            context['Tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES)
        else:
            context['item_formset'] = FactorItemFormSet()
            context['document_form'] = FactorDocumentForm()
            context['Tankhah_document_form'] = TankhahDocumentForm()
        context['title'] = 'ایجاد فاکتور جدید'
        context['Tankhah'] = tankhah
        if tankhah:  # فقط اگه tankhah مقدار داشته باشه
            context['Tankhah_documents'] = tankhah.documents.all()
        else:
            context['Tankhah_documents'] = []  # اگه None باشه، لیست خالی برگردون
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        document_form = context['document_form']
        Tankhah_document_form = context['Tankhah_document_form']
        Tankhah = form.cleaned_data['tankhah']

        if Tankhah.status not in ['DRAFT', 'PENDING']:
            messages.error(self.request, 'فقط می‌توانید برای تنخواه‌های پیش‌نویس یا در انتظار فاکتور ثبت کنید.')
            return self.form_invalid(form)

        initial_stage_order = WorkflowStage.objects.order_by('-order').first().order
        if Tankhah.current_stage.order != initial_stage_order:
            messages.error(self.request, 'فقط در مرحله اولیه می‌توانید فاکتور ثبت کنید.')
            return self.form_invalid(form)

        allowed_orgs = [Tankhah.organization]
        try:
            restrict_to_user_organization(self.request.user, allowed_orgs)  # استفاده از تابع ایمپورت‌شده
        except PermissionDenied as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        if item_formset.is_valid() and document_form.is_valid() and Tankhah_document_form.is_valid():
            with transaction.atomic():
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()

                # ذخیره اسناد فاکتور
                factor_files = self.request.FILES.getlist('files')
                for file in factor_files:
                    FactorDocument.objects.create(factor=self.object, file=file)

                # ذخیره اسناد تنخواه
                Tankhah_files = self.request.FILES.getlist('documents')
                for file in Tankhah_files:
                    TankhahDocument.objects.create(Tankhah=Tankhah, document=file)

                next_stage = WorkflowStage.objects.filter(order__lt=Tankhah.current_stage.order).order_by(
                    '-order').first()
                if next_stage:
                    Tankhah.current_stage = next_stage
                    Tankhah.status = 'PENDING'
                    Tankhah.save()
                    logger.info(f"Tankhah {Tankhah.number} moved to stage {next_stage.name} (order={next_stage.order})")
                    approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                    if approvers.exists():
                        notify.send(
                            sender=self.request.user,
                            recipient=approvers,
                            verb='تنخواه برای تأیید آماده است',
                            target=Tankhah
                        )
                        logger.info(f"Notification sent to {approvers.count()} approvers for stage {next_stage.name}")
                else:
                    logger.warning(f"No next stage found for Tankhah {Tankhah.number}")

            messages.success(self.request, 'فاکتور با موفقیت ثبت شد.')
            return super().form_valid(form)
        return self.form_invalid(form)

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return super().handle_no_permission()
class FactorUpdateView(PermissionBaseView, UpdateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/factor_form.html'
    success_url = reverse_lazy('factor_list')

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
            context['Tankhah_document_form'] = TankhahDocumentForm()
        context['title'] = _('ویرایش فاکتور') + f" - {self.object.number}"
        context['tankhah'] = tankhah
        context['tankhah_documents'] = tankhah.documents.all()
        total_amount = sum(item.amount * item.quantity for item in self.object.items.all())
        # context['difference'] = total_amount - context['total_amount'] if total_amount else 0
        context['total_amount'] = total_amount
        return context

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if getattr(obj, 'locked', False):  # چک می‌کنیم که locked وجود داره یا نه
            raise PermissionDenied("این فاکتور قفل شده و قابل ویرایش نیست.")
        return obj

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not request.user.has_perm('tankhah.Factor_full_edit') and getattr(obj, 'is_finalized', False):
            raise PermissionDenied(_('شما اجازه ویرایش این فاکتور را ندارید.'))
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
        try:
            initial_stage_order = WorkflowStage.objects.order_by('-order').first().order
            if self.object.Tankhah.current_stage.order != initial_stage_order or getattr(self.object, 'is_finalized',
                                                                                         False):
                messages.error(self.request,
                               _('فقط در مرحله اولیه و قبل از نهایی شدن می‌توانید فاکتور را ویرایش کنید.'))
                return self.form_invalid(form)
        except AttributeError:
            logger.error("No workflow stages defined in the system!")
            messages.error(self.request, _('هیچ مرحله‌ای در سیستم تعریف نشده است.'))
            return self.form_invalid(form)

        context = self.get_context_data()
        item_formset = context['item_formset']
        document_form = context['document_form']
        Tankhah_document_form = context['Tankhah_document_form']

        if item_formset.is_valid() and document_form.is_valid() and Tankhah_document_form.is_valid():
            with transaction.atomic():
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()

                # ذخیره اسناد جدید فاکتور
                factor_files = self.request.FILES.getlist('files')
                for file in factor_files:
                    FactorDocument.objects.create(factor=self.object, file=file)

                # ذخیره اسناد جدید تنخواه
                Tankhah_files = self.request.FILES.getlist('documents')
                for file in Tankhah_files:
                    TankhahDocument.objects.create(Tankhah=self.object.Tankhah, document=file)

            messages.success(self.request, _('فاکتور با موفقیت به‌روزرسانی شد.'))
            return super().form_valid(form)
        return self.form_invalid(form)
class FactorDeleteView(PermissionBaseView, DeleteView):
    model = Factor
    template_name = 'tankhah/factor_confirm_delete.html'
    success_url = reverse_lazy('factor_list')
    permission_required = 'Tankhah.Factor_delete'

    def post(self, request, *args, **kwargs):
        factor = self.get_object()
        user_post = self.request.user.userpost_set.first().post if self.request.user.userpost_set.exists() else None

        if factor.Tankhah.current_stage.order != 1 or factor.status != 'REJECTED' or user_post.level != 1:
            messages.error(self.request, _('فقط کاربران سطح پایین می‌توانند فاکتور ردشده در مرحله اولیه را حذف کنند.'))
            return redirect('factor_list')

        return super().post(request, *args, **kwargs)

    def handle_no_permission(self):
        messages.error(self.request, _('شما مجوز لازم برای حذف این فاکتور را ندارید.'))
        return redirect('factor_list')

    def dispatch(self, request, *args, **kwargs):
        factor = self.get_object()
        if factor.Tankhah.current_stage.order != 1:
            messages.error(request, _('حذف فاکتور فقط در مرحله اولیه امکان‌پذیر است.'))
            return redirect('factor_list')
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('فاکتور با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)
"""  ویو برای تأیید فاکتور"""
class FactorApproveView(UpdateView):
    model = Factor
    form_class = FactorApprovalForm  # فرض می‌کنیم این فرم وجود دارد
    template_name = 'tankhah/factor_approval.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['Tankhah.a_factor_view', 'Tankhah.a_factor_update']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('تأیید فاکتور') + f" - {self.object.number}"
        context['items'] = self.object.items.all()
        return context

    def form_valid(self, form):
        factor = self.object
        Tankhah = factor.Tankhah
        user_posts = self.request.user.userpost_set.all()

        # چک دسترسی به سازمان
        try:
            restrict_to_user_organization(self.request.user, [Tankhah.organization])
        except PermissionDenied as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        # چک اینکه کاربر تأییدکننده این مرحله است
        if not any(p.post.stageapprover_set.filter(stage=Tankhah.current_stage).exists() for p in user_posts):
            messages.error(self.request, _('شما مجاز به تأیید در این مرحله نیستید.'))
            return self.form_invalid(form)

        with transaction.atomic():
            # ذخیره فرم (مثلاً توضیحات)
            self.object = form.save()

            # اگر همه ردیف‌ها تأیید شده باشند
            all_items_approved = all(item.status == 'APPROVED' for item in self.object.items.all())
            if all_items_approved:
                factor.status = 'APPROVED'
                factor.save()
                logger.info(f"Factor {factor.number} approved by {self.request.user}")

                # چک همه فاکتورهای تنخواه
                all_factors_approved = all(f.status == 'APPROVED' for f in Tankhah.factors.all())
                if all_factors_approved:
                    next_stage = WorkflowStage.objects.filter(order__lt=Tankhah.current_stage.order).order_by(
                        '-order').first()
                    if next_stage:
                        Tankhah.current_stage = next_stage
                        Tankhah.status = 'PENDING'
                        Tankhah.save()
                        logger.info(f"Tankhah {Tankhah.number} moved to stage {next_stage.name}")

                        # ارسال اعلان به تأییدکنندگان مرحله بعدی
                        approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                        if approvers.exists():
                            notify.send(
                                sender=self.request.user,
                                recipient=approvers,
                                verb='تنخواه برای تأیید آماده است',
                                target=Tankhah
                            )
                            messages.info(self.request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                    else:
                        Tankhah.status = 'COMPLETED'
                        Tankhah.save()
                        logger.info(f"Tankhah {Tankhah.number} completed")
                        messages.success(self.request, _('تنخواه تکمیل شد.'))
                else:
                    messages.success(self.request, _('فاکتور تأیید شد اما هنوز فاکتورهای دیگری در انتظار تأیید هستند.'))
            else:
                messages.warning(self.request, _('برخی ردیف‌ها هنوز تأیید نشده‌اند.'))

        return super().form_valid(form)

    def handle_no_permission(self):
        messages.error(self.request, _('شما مجوز لازم برای تأیید این فاکتور را ندارید.'))
        return redirect('factor_list')
"""تأیید آیتم‌های فاکتور"""
class FactorItemApproveView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_item_approve.html'
    permission_codenames = ['Tankhah.FactorItem_approve', 'Tankhah.Tankhah_view', 'Tankhah.Tankhah_hq_view',
                            'Tankhah.Tankhah_hq_approve']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.get_object()

        # ایجاد فرم‌ست برای ردیف‌ها
        FactorItemApprovalFormSet = formset_factory(FactorItemApprovalForm, extra=0)
        initial_data = [{'item_id': item.id, 'action': item.status} for item in factor.items.all()]

        if self.request.POST:
            formset = FactorItemApprovalFormSet(self.request.POST)
        else:
            formset = FactorItemApprovalFormSet(initial=initial_data)

        context['item_form_pairs'] = zip(factor.items.all(), formset)
        context['formset'] = formset
        context['approval_logs'] = ApprovalLog.objects.filter(factor_item__factor=factor)
        return context

    def post(self, request, *args, **kwargs):
        factor = self.get_object()
        Tankhah = factor.tankhah
        user = request.user
        user_posts = user.userpost_set.all()

        # چک دسترسی به سازمان
        try:
            restrict_to_user_organization(user, [Tankhah.organization])
        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('dashboard_flows')

        # چک تأییدکننده مرحله
        if not any(p.post.stageapprover_set.filter(stage=Tankhah.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما مجاز به تأیید در این مرحله نیستید.'))
            return redirect('factor_item_approve', pk=factor.pk)

        FactorItemApprovalFormSet = formset_factory(FactorItemApprovalForm, extra=0)
        formset = FactorItemApprovalFormSet(request.POST)

        with transaction.atomic():
            if formset.is_valid():
                all_approved = True
                any_rejected = False
                bulk_approve = request.POST.get('bulk_approve') == 'on'

                for form, item in zip(formset, factor.items.all()):
                    action = 'APPROVE' if bulk_approve else form.cleaned_data['action']

                    if action in ['APPROVE', 'REJECT']:
                        ApprovalLog.objects.create(
                            factor_item=item,
                            user=user,
                            action=action,
                            stage=Tankhah.current_stage,
                            comment=form.cleaned_data['comment'],
                            post=user_posts.first().post if user_posts.exists() else None
                        )
                        item.status = action
                        item.save()
                        if action == 'REJECT':
                            all_approved = False
                            any_rejected = True
                        elif action != 'APPROVE':
                            all_approved = False

                if all_approved and factor.items.exists():
                    factor.status = 'APPROVED'
                    factor.is_finalized = True
                    factor.save()
                    logger.info(f"Factor {factor.number} approved")

                    # اگر همه فاکتورها تأیید شدند
                    if all(f.status == 'APPROVED' and f.is_finalized for f in Tankhah.factors.all()):
                        next_stage = WorkflowStage.objects.filter(order__lt=Tankhah.current_stage.order).order_by(
                            '-order').first()
                        if next_stage:
                            Tankhah.current_stage = next_stage
                            Tankhah.status = 'PENDING'
                            Tankhah.save()
                            approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                            if approvers.exists():
                                notify.send(request.user, recipient=approvers, verb='تنخواه در انتظار تأیید شما',
                                            target=Tankhah)
                            messages.info(request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                        else:
                            Tankhah.status = 'COMPLETED'
                            Tankhah.save()
                            messages.info(request, "تنخواه تأیید و تکمیل شد.")
                elif any_rejected:
                    factor.status = 'REJECTED'
                    factor.is_finalized = True
                    factor.save()
                    Tankhah.status = 'REJECTED'
                    Tankhah.save()
                    messages.error(request, _('فاکتور و تنخواه رد شدند.'))
                else:
                    factor.status = 'PENDING'
                    factor.save()

                messages.success(request, _('تغییرات با موفقیت ثبت شدند.'))
                return redirect('factor_item_approve', pk=factor.pk)
            else:
                messages.error(request, _('فرم نامعتبر است. لطفاً ورودی‌ها را بررسی کنید.'))
                return self.get(request, *args, **kwargs)

    def handle_no_permission(self):
        messages.error(self.request, _('شما مجوز لازم برای تأیید این فاکتور را ندارید.'))
        return redirect('factor_list')
class FactorItemRejectView(PermissionBaseView, View):
    permission_codenames = ['Tankhah.FactorItem_approve']

    def get(self, request, pk):
        item = get_object_or_404(FactorItem, pk=pk)
        factor = item.factor
        Tankhah = factor.Tankhah
        user_posts = request.user.userpost_set.all()

        # چک دسترسی
        try:
            restrict_to_user_organization(request.user, [Tankhah.organization])
        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('dashboard_flows')

        if not any(p.post.stageapprover_set.filter(stage=Tankhah.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه رد این ردیف را ندارید.'))
            return redirect('dashboard_flows')

        item.status = 'REJECTED'
        item.save()
        factor.status = 'REJECTED'
        Tankhah.status = 'REJECTED'
        factor.save()
        Tankhah.save()
        messages.error(request, _('ردیف فاکتور رد شد و فاکتور و تنخواه نیز رد شدند.'))
        return redirect('dashboard_flows')
# ---######## Approval Views ---
class ApprovalListView(PermissionBaseView, ListView):
    model = ApprovalLog
    template_name = 'tankhah/approval_list.html'
    context_object_name = 'approvals'
    paginate_by = 10
    extra_context = {'title': _('لیست تأییدات')}
class ApprovalLogListView(PermissionBaseView, ListView):
    model = ApprovalLog
    template_name = 'tankhah/approval_log_list.html'
    context_object_name = 'logs'
    paginate_by = 10

    def get_queryset(self):
        return ApprovalLog.objects.filter(Tankhah__number=self.kwargs['Tankhah_number']).order_by('-timestamp')
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
        user_post = UserPost.objects.filter(user=self.request.user).first()
        user_level = user_post.post.level if user_post else 0

        if form.instance.Tankhah:
            Tankhah = form.instance.Tankhah
            current_status = Tankhah.status
            branch = form.instance.action

            # بررسی مرحله فعلی (اگر current_stage وجود داشته باشد)
            if hasattr(Tankhah, 'current_stage') and branch != Tankhah.current_stage:
                messages.error(self.request, _('شما نمی‌توانید در این مرحله تأیید کنید.'))
                return self.form_invalid(form)

            if form.instance.action:
                if branch == 'COMPLEX' and current_status == 'PENDING' and user_level <= 2:
                    Tankhah.status = 'APPROVED'
                    Tankhah.hq_status = 'SENT_TO_HQ'
                    if hasattr(Tankhah, 'current_stage'):
                        Tankhah.current_stage = 'OPS'
                elif branch == 'OPS' and current_status == 'APPROVED' and user_level > 2:
                    Tankhah.hq_status = 'HQ_OPS_APPROVED'
                    if hasattr(Tankhah, 'current_stage'):
                        Tankhah.current_stage = 'FIN'
                elif branch == 'FIN' and Tankhah.hq_status == 'HQ_OPS_APPROVED' and user_level > 3:
                    Tankhah.hq_status = 'HQ_FIN_PENDING'
                    Tankhah.status = 'PAID'
                    if hasattr(Tankhah, 'current_stage'):
                        Tankhah.current_stage = 'FIN'  # پایان جریان
                else:
                    messages.error(self.request, _('شما اجازه تأیید در این مرحله را ندارید یا وضعیت نادرست است.'))
                    return self.form_invalid(form)
            else:
                Tankhah.status = 'REJECTED'
            Tankhah.last_stopped_post = user_post.post if user_post else None
            Tankhah.save()

        elif form.instance.factor:
            factor = form.instance.factor
            factor.status = 'APPROVED' if form.instance.action else 'REJECTED'
            factor.save()

        elif form.instance.factor_item:
            item = form.instance.factor_item
            # اگر FactorItem فیلد status داشته باشد
            if hasattr(item, 'status'):
                item.status = 'APPROVED' if form.instance.action else 'REJECTED'
                item.save()
            else:
                messages.warning(self.request, _('ردیف فاکتور فاقد وضعیت است و تأیید اعمال نشد.'))

        messages.success(self.request, _('تأیید با موفقیت ثبت شد.'))
        return super().form_valid(form)

    def can_approve_user(user, tankhah):
        current_stage = tankhah.current_stage
        approver_posts = StageApprover.objects.filter(stage=current_stage).values_list('post', flat=True)
        user_posts = user.userpost_set.values_list('post', flat=True)
        return bool(set(user_posts) & set(approver_posts))

    def get_initial(self):
        initial = super().get_initial()
        initial['Tankhah'] = self.request.GET.get('Tankhah')
        initial['factor'] = self.request.GET.get('factor')
        initial['factor_item'] = self.request.GET.get('factor_item')
        return initial

    def dispatch(self, request, *args, **kwargs):
            self.object = self.get_object()
            tankhah = self.object.factor.tankhah
            if not self.can_approve_user(request.user, tankhah):
                raise PermissionDenied("شما مجاز به تأیید در این مرحله نیستید.")
            return super().dispatch(request, *args, **kwargs)
class ApprovalUpdateView(PermissionRequiredMixin, UpdateView):
    model = ApprovalLog
    form_class = ApprovalForm
    template_name = 'tankhah/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'Tankhah.Approval_update'

    def form_valid(self, form):
        messages.success(self.request, _('تأیید با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)
class ApprovalDeleteView(PermissionRequiredMixin, DeleteView):
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
