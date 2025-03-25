import logging

import jdatetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
from jalali_date.fields import JalaliDateField
from notifications.signals import notify

from accounts.models import CustomUser
# Local imports
from core.PermissionBase import PermissionBaseView
from core.models import UserPost, Post, WorkflowStage
from .forms import (
    ApprovalForm, FactorItemApprovalForm, FactorApprovalForm, TanbakhDocumentForm, FactorDocumentForm, FactorForm,
    FactorItemFormSet, TanbakhForm, TanbakhStatusForm
)
from .models import (
    Factor, ApprovalLog, FactorItem, TanbakhDocument, FactorDocument, Tanbakh)
from .utils import restrict_to_user_organization

# Logger configuration
logger = logging.getLogger(__name__)


# -------
###########################################
class DashboardView(PermissionBaseView, TemplateView):
    template_name = 'tanbakh/tanbakh_dashboard.html'
    extra_context = {'title': _('داشبورد مدیریت تنخواه')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # لینک‌ها بر اساس پرمیشن‌ها
        context['links'] = {
            'tanbakh': [
                {'url': 'tanbakh_list', 'label': _('لیست تنخواه‌ها'), 'icon': 'fas fa-list',
                 'perm': 'tanbakh.Tanbakh_view'},
                {'url': 'tanbakh_create', 'label': _('ایجاد تنخواه'), 'icon': 'fas fa-plus',
                 'perm': 'tanbakh.Tanbakh_add'},
            ],
            'factor': [
                {'url': 'factor_list', 'label': _('لیست فاکتورها'), 'icon': 'fas fa-file-invoice',
                 'perm': 'tanbakh.a_factor_view'},
                {'url': 'factor_create', 'label': _('ایجاد فاکتور'), 'icon': 'fas fa-plus',
                 'perm': 'tanbakh.a_factor_add'},
            ],
            'approval': [
                {'url': 'approval_list', 'label': _('لیست تأییدات'), 'icon': 'fas fa-check-circle',
                 'perm': 'tanbakh.Approval_view'},
                {'url': 'approval_create', 'label': _('ثبت تأیید'), 'icon': 'fas fa-plus',
                 'perm': 'tanbakh.Approval_add'},
            ],
        }

        # فیلتر کردن لینک‌ها بر اساس دسترسی کاربر
        for section in context['links']:
            context['links'][section] = [link for link in context['links'][section] if user.has_perm(link['perm'])]

        return context


# ثبت و ویرایش تنخواه
# @method_decorator(has_permission('Tanbakh_add'), name='dispatch')
class TanbakhManageView(PermissionBaseView, CreateView):
    model = Tanbakh
    form_class = TanbakhForm
    template_name = 'tanbakh/tanbakh_manage.html'
    success_url = reverse_lazy('tanbakh_list')

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


# تأیید و ویرایش تنخواه
# @method_decorator(has_permission('Tanbakh_part_approve'), name='dispatch')
class TanbakhUpdateView(PermissionBaseView, UpdateView):
    model = Tanbakh
    form_class = TanbakhForm
    template_name = 'tanbakh/tanbakh_manage.html'
    success_url = reverse_lazy('tanbakh_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user_post = self.request.user.userpost_set.filter(post__organization=self.object.organization).first()
        if not user_post or user_post.post.branch != self.object.current_stage:
            messages.error(self.request, _('شما اجازه تأیید در این مرحله را ندارید.'))
            return self.form_invalid(form)
        next_post = Post.objects.filter(parent=user_post.post, organization=self.object.organization).first() or \
                    Post.objects.filter(organization__org_type='HQ', branch=self.object.current_stage, level=1).first()
        if next_post:
            self.object.last_stopped_post = next_post
        self.object.save()
        messages.success(self.request, _('تنخواه با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش و تأیید تنخواه') + f" - {self.object.number}"
        return context


# -------
class TanbakhCreateView(PermissionBaseView, CreateView):
    model = Tanbakh
    form_class = TanbakhForm
    template_name = 'tanbakh/tanbakh_form.html'
    success_url = reverse_lazy('tanbakh_list')
    context_object_name = 'tanbakh'
    permission_codenames = ['tanbakh.tanbakh_add']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    check_organization = True  # فعال کردن چک سازمان

    def get_form_kwargs(self):
        """ارسال کاربر به فرم برای فیلتر کردن گزینه‌ها"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """ثبت تنخواه با پایین‌ترین مرحله و ارسال اعلان"""
        tanbakh = form.instance
        tanbakh.created_by = self.request.user
        tanbakh.status = 'DRAFT'

        # تنظیم پایین‌ترین مرحله
        try:
            first_stage = WorkflowStage.objects.order_by('-order').first()  # بالاترین order = پایین‌ترین مرحله
            print(f'first_stage : {first_stage}')
            if not first_stage:
                logger.error("No workflow stages defined!")
                messages.error(self.request, _('هیچ مرحله‌ای در سیستم تعریف نشده است.'))
                return self.form_invalid(form)
            if first_stage.order != 1:  # اطمینان از اینکه پایین‌ترین مرحله order=1 است
                logger.warning(f"First stage {first_stage.name} has order {first_stage.order}, expected 1")
            tanbakh.current_stage = first_stage
            logger.info(f"Setting tanbakh {tanbakh.number} to stage: {first_stage.name} (order={first_stage.order})")
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
                target=tanbakh
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


class TanbakhListView1(PermissionBaseView, PermissionRequiredMixin, ListView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_list.html'
    context_object_name = 'tanbakhs'
    paginate_by = 10
    extra_context = {'title': _('لیست تنخواه‌ها')}

    # لیست مجوزها
    permission_required = (
        'tanbakh.Tanbakh_view', 'Tanbakh_update', 'Tanbakh_add',
        'tanbakh.Tanbakh_approve',
        'tanbakh.Tanbakh_part_approve',
        'tanbakh.FactorItem_approve', 'edit_full_tanbakh',
        'Tanbakh_hq_view',
        'Tanbakh_hq_approve', 'Tanbakh_HQ_OPS_PENDING', 'Tanbakh_HQ_OPS_APPROVED', "FactorItem_approve"
    )

    def has_permission(self):
        # چک کردن اینکه کاربر حداقل یکی از مجوزها را دارد
        return any(self.request.user.has_perm(perm) for perm in self.get_permission_required())

    def get_queryset(self):
        user = self.request.user
        user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()]
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)
        queryset = Tanbakh.objects.all() if is_hq_user else Tanbakh.objects.filter(organization__in=user_orgs)

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
        context['tanbakhs'] = context['object_list']
        context['show_archived'] = self.request.GET.get('show_archived', 'false') == 'true'
        return context


class TanbakhListView(PermissionBaseView, ListView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_list.html'
    context_object_name = 'tanbakhs'
    paginate_by = 10
    permission_required = (
        'tanbakh.Tanbakh_view', 'Tanbakh_update', 'Tanbakh_add', 'tanbakh.Tanbakh_approve',
        'tanbakh.Tanbakh_part_approve', 'tanbakh.FactorItem_approve', 'edit_full_tanbakh',
        'Tanbakh_hq_view', 'Tanbakh_hq_approve', 'Tanbakh_HQ_OPS_PENDING', 'Tanbakh_HQ_OPS_APPROVED',
        'tanbakh.FactorItem_approve'
    )

    def has_permission(self):
        return any(self.request.user.has_perm(perm) for perm in self.get_permission_required())

    def get_queryset(self):
        """فیلتر کردن تنخواه‌ها بر اساس سازمان کاربر"""
        qs = super().get_queryset()
        user = self.request.user
        user_orgs = [up.post.organization for up in
                     self.request.user.userpost_set.all()] if self.request.user.userpost_set.exists() else []
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False

        # اگر کاربر HQ است، همه تنخواه‌ها را نشان بده، در غیر این صورت فقط تنخواه‌های سازمان کاربر
        queryset = Tanbakh.objects.all() if is_hq_user else Tanbakh.objects.filter(organization__in=user_orgs)

        if not is_hq_user and not self.request.user.is_superuser:
            qs = qs.filter(organization__in=user_orgs)
            # فیلتر بر اساس stage اگر در URL باشد
        stage_id = self.request.GET.get('stage')
        if stage_id:
            qs = qs.filter(current_stage_id=stage_id)

        # فیلتر آرشیو
        if not self.request.GET.get('show_archived'):
            queryset = queryset.filter(is_archived=False)

        # فیلتر جستجو
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(number__icontains=query) | queryset.filter(organization__name__icontains=query)

        # فیلتر مرحله
        stage = self.request.GET.get('stage')
        if stage:
            queryset = queryset.filter(current_stage__order=stage)

        # بررسی وجود تنخواه‌ها برای دیباگ
        if not queryset.exists() and not is_hq_user and not user_orgs:
            messages.warning(self.request, _('شما به هیچ سازمانی متصل نیستید و تنخواهی نمایش داده نمی‌شود.'))
        elif not queryset.exists():
            messages.info(self.request, _('هیچ تنخواهی با این شرایط یافت نشد.'))

        return queryset.order_by('-date')  # مرتب‌سازی بر اساس تاریخ

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_orgs = [up.post.organization for up in
                     self.request.user.userpost_set.all()] if self.request.user.userpost_set.exists() else []
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False

        context['is_hq_user'] = is_hq_user
        context['user_orgs'] = user_orgs
        # context['is_hq_user'] = any(org.org_type == 'HQ' for org in user_orgs)
        context['query'] = self.request.GET.get('q', '')
        context['stage'] = self.request.GET.get('stage', '')
        context['show_archived'] = self.request.GET.get('show_archived', 'false') == 'true'

        # انتخاب نام سازمان برای نمایش
        if is_hq_user:
            context['org_display_name'] = _('دفتر مرکزی')
        elif user_orgs:
            context['org_display_name'] = user_orgs[0].name  # نام اولین سازمان کاربر
        else:
            context['org_display_name'] = _('بدون سازمان')
        return context


class TanbakhDetailView(PermissionBaseView, PermissionRequiredMixin, DetailView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_detail.html'
    context_object_name = 'tanbakh'

    # مجوزهای نمایشی (حداقل یکی لازم است)
    permission_required = (
        'tanbakh.Tanbakh_view', 'Tanbakh_update',
        'tanbakh.Tanbakh_hq_view', 'Tanbakh_HQ_OPS_APPROVED', 'edit_full_tanbakh'
    )

    def has_permission(self):
        # کاربر باید حداقل یکی از مجوزهای نمایشی را داشته باشد
        return any(self.request.user.has_perm(perm) for perm in self.get_permission_required())

    def get_object(self, queryset=None):
        tanbakh = get_object_or_404(Tanbakh, pk=self.kwargs['pk'])
        restrict_to_user_organization(self.request.user, tanbakh.organization)
        return tanbakh

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['factors'] = self.object.factors.all()
        context['title'] = _('جزئیات تنخواه') + f" - {self.object.number}"
        context['approval_logs'] = ApprovalLog.objects.filter(tanbakh=self.object).order_by('timestamp')
        context['current_date'] = jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M')  # تاریخ فعلی برای چاپ
        context['status_form'] = TanbakhStatusForm(instance=self.object)
        context['title'] = _('جزئیات تنخواه') + f" - {self.object.number}"

        # تبدیل تاریخ‌ها به شمسی
        if self.object.date:
            context['jalali_date'] = jdatetime.date.fromgregorian(date=self.object.date).strftime('%Y/%m/%d %H:%M')
        for factor in context['factors']:
            factor.jalali_date = jdatetime.date.fromgregorian(date=factor.date).strftime('%Y/%m/%d %H:%M')
        for approval in context['approval_logs']:
            approval.jalali_date = jdatetime.datetime.fromgregorian(datetime=approval.timestamp).strftime(
                '%Y/%m/%d %H:%M')

        # دسته‌بندی برای دفتر مرکزی
        user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()]
        context['is_hq'] = any(org.org_type == 'HQ' for org in user_orgs)
        context['can_approve'] = self.request.user.has_perm('tanbakh.Tanbakh_approve') or \
                                 self.request.user.has_perm('tanbakh.Tanbakh_part_approve') or \
                                 self.request.user.has_perm('tanbakh.FactorItem_approve')
        return context


# @method_decorator(has_permission('Tanbakh_delete'), name='dispatch')
class TanbakhDeleteView(PermissionBaseView, DeleteView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_confirm_delete.html'
    success_url = reverse_lazy('tanbakh_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تنخواه با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


# ویو تأیید:
class TanbakhApproveView(PermissionBaseView, View):
    permission_codenames = ['tanbakh.tanbakh_approve']

    def get(self, request, pk):
        tanbakh = Tanbakh.objects.get(pk=pk)
        user_posts = request.user.userpost_set.all()
        if not any(p.post.stageapprover_set.filter(stage=tanbakh.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه تأیید این مرحله را ندارید.'))
            return redirect('dashboard_flows')

        next_stage = WorkflowStage.objects.filter(order__lt=tanbakh.current_stage.order).order_by('-order').first()
        if next_stage:
            tanbakh.current_stage = next_stage
            tanbakh.status = 'PENDING'
            tanbakh.save()
            messages.success(request, _('تنخواه با موفقیت تأیید شد و به مرحله بعدی منتقل شد.'))
            # اعلان به تأییدکنندگان مرحله بعدی
            approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
            if approvers.exists():
                notify.send(sender=request.user, recipient=approvers, verb='تنخواه برای تأیید آماده است',
                            target=tanbakh)
        else:
            tanbakh.status = 'COMPLETED'
            tanbakh.save()
            messages.success(request, _('تنخواه با موفقیت تکمیل شد.'))
        return redirect('dashboard_flows')


# ویو رد:
class TanbakhRejectView(PermissionBaseView, View):
    permission_codenames = ['tanbakh.tanbakh_approve']

    def get(self, request, pk):
        tanbakh = Tanbakh.objects.get(pk=pk)
        user_posts = request.user.userpost_set.all()
        if not any(p.post.stageapprover_set.filter(stage=tanbakh.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه رد این مرحله را ندارید.'))
            return redirect('dashboard_flows')

        tanbakh.status = 'REJECTED'
        tanbakh.save()
        messages.error(request, _('تنخواه رد شد.'))
        return redirect('dashboard_flows')


# ویو نهایی تنخواه تایید یا رد شده
class TanbakhFinalApprovalView(UpdateView):
    """ویو نهایی تنخواه تایید یا رد شده """
    model = Tanbakh
    fields = ['status']
    template_name = 'tanbakh/tanbakh_final_approval.html'
    success_url = reverse_lazy('tanbakh_list')

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
class ApprovalLogListView(PermissionBaseView, ListView):
    model = ApprovalLog
    template_name = 'tanbakh/approval_log_list.html'
    context_object_name = 'logs'
    paginate_by = 10

    def get_queryset(self):
        return ApprovalLog.objects.filter(tanbakh__number=self.kwargs['tanbakh_number']).order_by('-timestamp')


# --- Factor Views ---
from django.utils.translation import gettext_lazy as _
from persiantools.jdatetime import JalaliDate  # ایمپورت درست
from datetime import datetime

# tanbakh/views.py
from django.views.generic.list import ListView
from django.db.models import Q
from .models import Factor
from core.views import PermissionBaseView
from django.utils.translation import gettext_lazy as _
from datetime import datetime
from jalali_date import date2jalali  # برای نمایش، ولی برای پارس برعکسش رو دستی می‌کنیم

class FactorListView(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tanbakh/factor_list.html'
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
            queryset = Factor.objects.filter(tanbakh__organization__in=user_orgs)

        query = self.request.GET.get('q', '').strip()
        date_query = self.request.GET.get('date', '').strip()
        status_query = self.request.GET.get('status', '').strip()

        if query or date_query or status_query:
            filter_conditions = Q()
            if query:
                filter_conditions |= (
                    Q(number__icontains=query) |
                    Q(tanbakh__number__icontains=query) |
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
    template_name = 'tanbakh/factor_detail.html'  # تمپلیت نمایشی جدید
    context_object_name = 'factor'
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    permission_codename = 'tanbakh.a_factor_view'
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.get_object()
        tanbakh = factor.tanbakh

        context['title'] = _('جزئیات فاکتور') + f" - {factor.number}"
        context['tanbakh'] = tanbakh
        context['tanbakh_documents'] = tanbakh.documents.all()

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
    template_name = 'tanbakh/factor_form.html'
    success_url = reverse_lazy('factor_list')
    context_object_name = 'factor'
    permission_codenames = ['tanbakh.a_factor_add']
    permission_denied_message = 'متاسفانه دسترسی مجاز ندارید'
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tanbakh = Tanbakh.objects.get(id=self.kwargs.get('tanbakh_id', None)) if 'tanbakh_id' in self.kwargs else None
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES)
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
            context['tanbakh_document_form'] = TanbakhDocumentForm(self.request.POST, self.request.FILES)
        else:
            context['item_formset'] = FactorItemFormSet()
            context['document_form'] = FactorDocumentForm()
            context['tanbakh_document_form'] = TanbakhDocumentForm()
        context['title'] = 'ایجاد فاکتور جدید'
        context['tanbakh'] = tanbakh
        if tanbakh:
            context['tanbakh_documents'] = tanbakh.documents.all()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        document_form = context['document_form']
        tanbakh_document_form = context['tanbakh_document_form']
        tanbakh = form.cleaned_data['tanbakh']

        if tanbakh.status not in ['DRAFT', 'PENDING']:
            messages.error(self.request, 'فقط می‌توانید برای تنخواه‌های پیش‌نویس یا در انتظار فاکتور ثبت کنید.')
            return self.form_invalid(form)

        initial_stage_order = WorkflowStage.objects.order_by('-order').first().order
        if tanbakh.current_stage.order != initial_stage_order:
            messages.error(self.request, 'فقط در مرحله اولیه می‌توانید فاکتور ثبت کنید.')
            return self.form_invalid(form)

        allowed_orgs = [tanbakh.organization]
        try:
            restrict_to_user_organization(self.request.user, allowed_orgs)  # استفاده از تابع ایمپورت‌شده
        except PermissionDenied as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        if item_formset.is_valid() and document_form.is_valid() and tanbakh_document_form.is_valid():
            with transaction.atomic():
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()

                # ذخیره اسناد فاکتور
                factor_files = self.request.FILES.getlist('files')
                for file in factor_files:
                    FactorDocument.objects.create(factor=self.object, file=file)

                # ذخیره اسناد تنخواه
                tanbakh_files = self.request.FILES.getlist('documents')
                for file in tanbakh_files:
                    TanbakhDocument.objects.create(tanbakh=tanbakh, document=file)

                next_stage = WorkflowStage.objects.filter(order__lt=tanbakh.current_stage.order).order_by(
                    '-order').first()
                if next_stage:
                    tanbakh.current_stage = next_stage
                    tanbakh.status = 'PENDING'
                    tanbakh.save()
                    logger.info(f"Tanbakh {tanbakh.number} moved to stage {next_stage.name} (order={next_stage.order})")
                    approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                    if approvers.exists():
                        notify.send(
                            sender=self.request.user,
                            recipient=approvers,
                            verb='تنخواه برای تأیید آماده است',
                            target=tanbakh
                        )
                        logger.info(f"Notification sent to {approvers.count()} approvers for stage {next_stage.name}")
                else:
                    logger.warning(f"No next stage found for tanbakh {tanbakh.number}")

            messages.success(self.request, 'فاکتور با موفقیت ثبت شد.')
            return super().form_valid(form)
        return self.form_invalid(form)

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return super().handle_no_permission()


# tanbakh/views.py (ادامه)
class FactorUpdateView(PermissionBaseView, UpdateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tanbakh/factor_form.html'
    success_url = reverse_lazy('factor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tanbakh = self.object.tanbakh
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, instance=self.object)
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
            context['tanbakh_document_form'] = TanbakhDocumentForm(self.request.POST, self.request.FILES)
        else:
            context['item_formset'] = FactorItemFormSet(instance=self.object)
            context['document_form'] = FactorDocumentForm()
            context['tanbakh_document_form'] = TanbakhDocumentForm()
        context['title'] = _('ویرایش فاکتور') + f" - {self.object.number}"
        context['tanbakh'] = tanbakh
        context['tanbakh_documents'] = tanbakh.documents.all()
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
        if not request.user.has_perm('tanbakh.Factor_full_edit') and getattr(obj, 'is_finalized', False):
            raise PermissionDenied(_('شما اجازه ویرایش این فاکتور را ندارید.'))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        if self.object:
            tanbakh = self.object.tanbakh
            restrict_to_user_organization(self.request.user, tanbakh.organization)
            kwargs['tanbakh'] = tanbakh
        return kwargs

    def form_valid(self, form):
        try:
            initial_stage_order = WorkflowStage.objects.order_by('-order').first().order
            if self.object.tanbakh.current_stage.order != initial_stage_order or getattr(self.object, 'is_finalized',
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
        tanbakh_document_form = context['tanbakh_document_form']

        if item_formset.is_valid() and document_form.is_valid() and tanbakh_document_form.is_valid():
            with transaction.atomic():
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()

                # ذخیره اسناد جدید فاکتور
                factor_files = self.request.FILES.getlist('files')
                for file in factor_files:
                    FactorDocument.objects.create(factor=self.object, file=file)

                # ذخیره اسناد جدید تنخواه
                tanbakh_files = self.request.FILES.getlist('documents')
                for file in tanbakh_files:
                    TanbakhDocument.objects.create(tanbakh=self.object.tanbakh, document=file)

            messages.success(self.request, _('فاکتور با موفقیت به‌روزرسانی شد.'))
            return super().form_valid(form)
        return self.form_invalid(form)


class FactorDeleteView(PermissionBaseView, DeleteView):
    model = Factor
    template_name = 'tanbakh/factor_confirm_delete.html'
    success_url = reverse_lazy('factor_list')
    permission_required = 'tanbakh.Factor_delete'

    def post(self, request, *args, **kwargs):
        factor = self.get_object()
        user_post = self.request.user.userpost_set.first().post if self.request.user.userpost_set.exists() else None

        if factor.tanbakh.current_stage.order != 1 or factor.status != 'REJECTED' or user_post.level != 1:
            messages.error(self.request, _('فقط کاربران سطح پایین می‌توانند فاکتور ردشده در مرحله اولیه را حذف کنند.'))
            return redirect('factor_list')

        return super().post(request, *args, **kwargs)

    def handle_no_permission(self):
        messages.error(self.request, _('شما مجوز لازم برای حذف این فاکتور را ندارید.'))
        return redirect('factor_list')

    def dispatch(self, request, *args, **kwargs):
        factor = self.get_object()
        if factor.tanbakh.current_stage.order != 1:
            messages.error(request, _('حذف فاکتور فقط در مرحله اولیه امکان‌پذیر است.'))
            return redirect('factor_list')
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('فاکتور با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


############################################################################################################
"""  ویو برای تأیید فاکتور"""


class FactorApproveView(UpdateView):
    model = Factor
    form_class = FactorApprovalForm  # فرض می‌کنیم این فرم وجود دارد
    template_name = 'tanbakh/factor_approval.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tanbakh.a_factor_view', 'tanbakh.a_factor_update']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('تأیید فاکتور') + f" - {self.object.number}"
        context['items'] = self.object.items.all()
        return context

    def form_valid(self, form):
        factor = self.object
        tanbakh = factor.tanbakh
        user_posts = self.request.user.userpost_set.all()

        # چک دسترسی به سازمان
        try:
            restrict_to_user_organization(self.request.user, [tanbakh.organization])
        except PermissionDenied as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        # چک اینکه کاربر تأییدکننده این مرحله است
        if not any(p.post.stageapprover_set.filter(stage=tanbakh.current_stage).exists() for p in user_posts):
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
                all_factors_approved = all(f.status == 'APPROVED' for f in tanbakh.factors.all())
                if all_factors_approved:
                    next_stage = WorkflowStage.objects.filter(order__lt=tanbakh.current_stage.order).order_by(
                        '-order').first()
                    if next_stage:
                        tanbakh.current_stage = next_stage
                        tanbakh.status = 'PENDING'
                        tanbakh.save()
                        logger.info(f"Tanbakh {tanbakh.number} moved to stage {next_stage.name}")

                        # ارسال اعلان به تأییدکنندگان مرحله بعدی
                        approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                        if approvers.exists():
                            notify.send(
                                sender=self.request.user,
                                recipient=approvers,
                                verb='تنخواه برای تأیید آماده است',
                                target=tanbakh
                            )
                            messages.info(self.request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                    else:
                        tanbakh.status = 'COMPLETED'
                        tanbakh.save()
                        logger.info(f"Tanbakh {tanbakh.number} completed")
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
    template_name = 'tanbakh/factor_item_approve.html'
    permission_codenames = ['tanbakh.FactorItem_approve', 'tanbakh.Tanbakh_view', 'tanbakh.Tanbakh_hq_view',
                            'tanbakh.Tanbakh_hq_approve']

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
        tanbakh = factor.tanbakh
        user = request.user
        user_posts = user.userpost_set.all()

        # چک دسترسی به سازمان
        try:
            restrict_to_user_organization(user, [tanbakh.organization])
        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('dashboard_flows')

        # چک تأییدکننده مرحله
        if not any(p.post.stageapprover_set.filter(stage=tanbakh.current_stage).exists() for p in user_posts):
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
                            stage=tanbakh.current_stage,
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
                    if all(f.status == 'APPROVED' and f.is_finalized for f in tanbakh.factors.all()):
                        next_stage = WorkflowStage.objects.filter(order__lt=tanbakh.current_stage.order).order_by(
                            '-order').first()
                        if next_stage:
                            tanbakh.current_stage = next_stage
                            tanbakh.status = 'PENDING'
                            tanbakh.save()
                            approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                            if approvers.exists():
                                notify.send(request.user, recipient=approvers, verb='تنخواه در انتظار تأیید شما',
                                            target=tanbakh)
                            messages.info(request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                        else:
                            tanbakh.status = 'COMPLETED'
                            tanbakh.save()
                            messages.info(request, "تنخواه تأیید و تکمیل شد.")
                elif any_rejected:
                    factor.status = 'REJECTED'
                    factor.is_finalized = True
                    factor.save()
                    tanbakh.status = 'REJECTED'
                    tanbakh.save()
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


############################################################################################################
class FactorItemRejectView(PermissionBaseView, View):
    permission_codenames = ['tanbakh.FactorItem_approve']

    def get(self, request, pk):
        item = get_object_or_404(FactorItem, pk=pk)
        factor = item.factor
        tanbakh = factor.tanbakh
        user_posts = request.user.userpost_set.all()

        # چک دسترسی
        try:
            restrict_to_user_organization(request.user, [tanbakh.organization])
        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('dashboard_flows')

        if not any(p.post.stageapprover_set.filter(stage=tanbakh.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه رد این ردیف را ندارید.'))
            return redirect('dashboard_flows')

        item.status = 'REJECTED'
        item.save()
        factor.status = 'REJECTED'
        tanbakh.status = 'REJECTED'
        factor.save()
        tanbakh.save()
        messages.error(request, _('ردیف فاکتور رد شد و فاکتور و تنخواه نیز رد شدند.'))
        return redirect('dashboard_flows')


# ---######## Approval Views ---
class ApprovalListView(PermissionBaseView, ListView):
    model = ApprovalLog
    template_name = 'tanbakh/approval_list.html'
    context_object_name = 'approvals'
    paginate_by = 10
    extra_context = {'title': _('لیست تأییدات')}


class ApprovalDetailView(PermissionBaseView, DetailView):
    model = ApprovalLog
    template_name = 'tanbakh/approval_detail.html'
    context_object_name = 'approval'
    extra_context = {'title': _('جزئیات تأیید')}


class ApprovalCreateView(PermissionRequiredMixin, CreateView):
    model = ApprovalLog
    form_class = ApprovalForm
    template_name = 'tanbakh/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'tanbakh.Approval_add'

    def form_valid(self, form):
        form.instance.user = self.request.user
        user_post = UserPost.objects.filter(user=self.request.user).first()
        user_level = user_post.post.level if user_post else 0

        if form.instance.tanbakh:
            tanbakh = form.instance.tanbakh
            current_status = tanbakh.status
            branch = form.instance.action

            # بررسی مرحله فعلی (اگر current_stage وجود داشته باشد)
            if hasattr(tanbakh, 'current_stage') and branch != tanbakh.current_stage:
                messages.error(self.request, _('شما نمی‌توانید در این مرحله تأیید کنید.'))
                return self.form_invalid(form)

            if form.instance.action:
                if branch == 'COMPLEX' and current_status == 'PENDING' and user_level <= 2:
                    tanbakh.status = 'APPROVED'
                    tanbakh.hq_status = 'SENT_TO_HQ'
                    if hasattr(tanbakh, 'current_stage'):
                        tanbakh.current_stage = 'OPS'
                elif branch == 'OPS' and current_status == 'APPROVED' and user_level > 2:
                    tanbakh.hq_status = 'HQ_OPS_APPROVED'
                    if hasattr(tanbakh, 'current_stage'):
                        tanbakh.current_stage = 'FIN'
                elif branch == 'FIN' and tanbakh.hq_status == 'HQ_OPS_APPROVED' and user_level > 3:
                    tanbakh.hq_status = 'HQ_FIN_PENDING'
                    tanbakh.status = 'PAID'
                    if hasattr(tanbakh, 'current_stage'):
                        tanbakh.current_stage = 'FIN'  # پایان جریان
                else:
                    messages.error(self.request, _('شما اجازه تأیید در این مرحله را ندارید یا وضعیت نادرست است.'))
                    return self.form_invalid(form)
            else:
                tanbakh.status = 'REJECTED'
            tanbakh.last_stopped_post = user_post.post if user_post else None
            tanbakh.save()

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

    def get_initial(self):
        initial = super().get_initial()
        initial['tanbakh'] = self.request.GET.get('tanbakh')
        initial['factor'] = self.request.GET.get('factor')
        initial['factor_item'] = self.request.GET.get('factor_item')
        return initial


class ApprovalUpdateView(PermissionRequiredMixin, UpdateView):
    model = ApprovalLog
    form_class = ApprovalForm
    template_name = 'tanbakh/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'tanbakh.Approval_update'

    def form_valid(self, form):
        messages.success(self.request, _('تأیید با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)


class ApprovalDeleteView(PermissionRequiredMixin, DeleteView):
    model = ApprovalLog
    template_name = 'tanbakh/approval_confirm_delete.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'tanbakh.Approval_delete'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تأیید با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


# -- وضعیت تنخواه
@login_required
def upload_tanbakh_documents(request, tanbakh_id):
    tanbakh = Tanbakh.objects.get(id=tanbakh_id)
    if request.method == 'POST':
        form = TanbakhDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('documents')
            for file in files:
                TanbakhDocument.objects.create(tanbakh=tanbakh, document=file)
            messages.success(request, 'اسناد با موفقیت آپلود شدند.')
            return redirect('tanbakh_detail', pk=tanbakh.id)
        else:
            messages.error(request, 'خطایی در آپلود اسناد رخ داد.')
    else:
        form = TanbakhDocumentForm()

    return render(request, 'tanbakh/upload_documents.html', {
        'form': form,
        'tanbakh': tanbakh,
        'existing_documents': tanbakh.documents.all()
    })
