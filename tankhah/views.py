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
from core.PermissionBase import get_lowest_access_level, get_initial_stage_order
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
        with transaction.atomic():
            self.object = form.save(commit=False)
            initial_stage = WorkflowStage.objects.order_by('-order').first()  # پایین‌ترین order
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
                logger.info(f"Notification sent to {approvers.count()} approvers for stage {initial_stage.name}")
        messages.success(self.request, 'تنخواه با موفقیت ثبت شد.')
        return super().form_valid(form)

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
from django.db import models


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
        tankhah = Tankhah.objects.get(pk=pk)
        user_posts = request.user.userpost_set.all()

        # چک دسترسی
        is_hq_user = any(p.post.organization.org_type == 'HQ' for p in user_posts)
        can_approve = is_hq_user and any(p.post.name in ['کارشناس بهره‌برداری', 'مدیر', 'معاونت بهره‌برداری', 'معاونت مالی و اداری'] for p in user_posts)
        if not can_approve or not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
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
                approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                if approvers.exists():
                    notify.send(sender=request.user, recipient=approvers, verb='تنخواه برای تأیید آماده است', target=tankhah)
            else:
                # مرحله آخر: پرداخت
                if any(p.post.name == 'معاونت مالی و اداری' for p in user_posts):
                    payment_number = request.POST.get('payment_number', '')
                    if payment_number:
                        tankhah.status = 'PAID'
                        tankhah.hq_status = 'PAID'
                        tankhah.payment_number = payment_number
                        tankhah.is_locked = True
                        tankhah.is_archived = True  # آرشیو کردن
                        tankhah.save()
                        messages.success(request, _('تنخواه پرداخت شد، قفل و آرشیو شد.'))
                    else:
                        messages.error(request, _('لطفاً شماره پرداخت را وارد کنید.'))
                        return redirect('dashboard_flows')
                else:
                    tankhah.status = 'COMPLETED'
                    tankhah.hq_status = 'COMPLETED'
                    tankhah.is_locked = True
                    tankhah.is_archived = True  # آرشیو کردن
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
class FactorListView(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tankhah/factor_list.html'
    context_object_name = 'factors'
    paginate_by = 10
    extra_context = {'title': _('لیست فاکتورها')}
    permission_codenames = [
    'tankhah.a_factor_view'
    #     'Tankhah.Tankhah_view', 'Tankhah.Tankhah_update', 'Tankhah.Tankhah_add',
    #     'Tankhah.Tankhah_approve', 'Tankhah.Tankhah_part_approve', 'Tankhah.FactorItem_approve',
    #     'Tankhah.edit_full_Tankhah', 'Tankhah.Tankhah_hq_view', 'Tankhah.Tankhah_hq_approve',
    #     'Tankhah.Tankhah_HQ_OPS_PENDING', 'Tankhah.Tankhah_HQ_OPS_APPROVED', 'Tankhah.FactorItem_approve'
    ]

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
        # نمایش رکورد های قفل شده
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
            # قفل شدن: اگه مرحله تأییدکننده پایین‌تر (order کمتر) از مرحله فعلی باشه
            factor.is_locked = factor.locked_by_stage is not None and factor.locked_by_stage.order < current_stage_order
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

class FactorCreateView1(PermissionBaseView, CreateView):
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


class FactorCreateView(PermissionBaseView, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/factor_form.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.a_factor_add']
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = Tankhah.objects.get(id=self.kwargs.get('tankhah_id')) if 'tankhah_id' in self.kwargs else None
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

        # فقط توی مرحله اولیه (بالاترین order) اجازه ثبت
        initial_stage_order = WorkflowStage.objects.order_by('-order').first().order
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

                # بدون تغییر مرحله یا تأیید خودکار
                self.object.status = 'PENDING'  # فاکتور در انتظار تأیید
                self.object.save()

            messages.success(self.request, 'فاکتور با موفقیت ثبت شد.')
            return super().form_valid(form)
        else:
            logger.info(f"Errors: {item_formset.errors}, {document_form.errors}, {tankhah_document_form.errors}")
            return self.form_invalid(form)

class FactorUpdateView1(PermissionBaseView, UpdateView):
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

class FactorUpdateView(PermissionBaseView, UpdateView):
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
class FactorDeleteView(PermissionBaseView, DeleteView):
    model = Factor
    template_name = 'tankhah/factor_confirm_delete.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.a_factor_delete']
    check_organization = True

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        initial_stage_order = WorkflowStage.objects.order_by('-order').first().order
        if obj.status != 'PENDING' and not request.user.has_perm('tankhah.Factor_full_edit'):
            raise PermissionDenied(_('فاکتور تأییدشده یا ردشده قابل حذف نیست.'))
        if obj.tankhah.current_stage.order != initial_stage_order:
            raise PermissionDenied(_('فقط در مرحله اولیه می‌توانید فاکتور را حذف کنید.'))
        if obj.locked_by_stage and obj.locked_by_stage.order < obj.tankhah.current_stage.order:
            raise PermissionDenied(_('این فاکتور توسط مرحله بالاتر قفل شده و قابل حذف نیست.'))
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(self.request, _('فاکتور با موفقیت حذف شد.'))
        return redirect(self.success_url)

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
class FactorItemApproveView1(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_item_approve.html'
    permission_codenames = ['tankhah.FactorItem_approve']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object
        FactorItemApprovalFormSet = formset_factory(FactorItemApprovalForm, extra=0)
        initial_data = [{'item_id': item.id, 'action': item.status} for item in factor.items.all()]

        context['formset'] = FactorItemApprovalFormSet(self.request.POST or None, initial=initial_data)
        context['item_form_pairs'] = zip(factor.items.all(), context['formset'])
        context['approval_logs'] = ApprovalLog.objects.filter(factor_item__factor=factor)
        context['title'] = _('تأیید ردیف‌های فاکتور') + f" - {factor.number}"
        return context

    def post(self, request, *args, **kwargs):
        factor = self.get_object()
        tankhah = factor.tankhah
        user_posts = request.user.userpost_set.all()

        logger.info(f"Processing POST for factor {factor.number}, tankhah {tankhah.number}, current_stage: {tankhah.current_stage.name} (order: {tankhah.current_stage.order})")
        logger.info(f"User posts: {[p.post.name for p in user_posts]}")
        # چک دسترسی و قفل/آرشیو
        if tankhah.is_locked or tankhah.is_archived:
            messages.error(request, _('این تنخواه قفل یا آرشیو شده و قابل تغییر نیست.'))
            return redirect('factor_item_approve', pk=factor.pk)

        # چک مجوز تأیید توی این مرحله
        can_approve = any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts)
        if not can_approve:
            logger.warning(f"User {request.user.username} not authorized to approve stage {tankhah.current_stage.name}")
            messages.error(request, _('شما مجاز به تأیید در این مرحله نیستید.'))
            return redirect('factor_item_approve', pk=factor.pk)

        # ساخت فرم‌ست
        FactorItemApprovalFormSet = formset_factory(FactorItemApprovalForm, extra=0)
        initial_data = [{'item_id': item.id, 'action': item.status} for item in factor.items.all()]
        formset = FactorItemApprovalFormSet(request.POST, initial=initial_data)

        if formset.is_valid():
            with transaction.atomic():
                all_approved = True
                any_rejected = False
                bulk_approve = request.POST.get('bulk_approve') == 'on'

                for form, item in zip(formset, factor.items.all()):
                    action = 'APPROVE' if bulk_approve else form.cleaned_data['action']
                    if action in ['APPROVE', 'REJECT']:
                        ApprovalLog.objects.create(
                            factor_item=item,
                            user=request.user,
                            action=action,
                            stage=tankhah.current_stage,
                            comment=form.cleaned_data.get('comment', ''),
                            post=user_posts.first().post if user_posts.exists() else None
                        )
                        item.status = action
                        item.save()
                        logger.info(f"Item {item.id} status updated to {action}")
                        if action == 'REJECT':
                            all_approved = False
                            any_rejected = True
                        elif action != 'APPROVE':
                            all_approved = False

                if all_approved and factor.items.exists():
                    factor.status = 'APPROVED'
                    factor.locked_by_stage = tankhah.current_stage
                    factor.save()
                    logger.info(f"Factor {factor.number} approved")

                    if all(f.status == 'APPROVED' for f in tankhah.factors.all()):
                        next_stage = WorkflowStage.objects.filter(order__lt=tankhah.current_stage.order).order_by('-order').first()
                        if next_stage:
                            tankhah.current_stage = next_stage
                            tankhah.status = 'PENDING'
                            tankhah.save()
                            logger.info(f"Tankhah {tankhah.number} moved to stage {next_stage.name} (order: {next_stage.order})")
                            approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                            if approvers.exists():
                                notify.send(request.user, recipient=approvers, verb='تنخواه در انتظار تأیید', target=tankhah)
                                messages.info(request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                        else:
                            tankhah.status = 'COMPLETED'
                            tankhah.save()
                            logger.info(f"Tankhah {tankhah.number} completed")
                            messages.success(request, _('تنخواه تکمیل شد.'))
                elif any_rejected:
                    factor.status = 'REJECTED'
                    tankhah.status = 'REJECTED'
                    factor.save()
                    tankhah.save()
                    logger.info(f"Factor {factor.number} and tankhah {tankhah.number} rejected")
                    messages.error(request, _('فاکتور و تنخواه رد شدند.'))
                else:
                    factor.status = 'PENDING'
                    factor.save()
                    logger.info(f"Factor {factor.number} still pending")
                    messages.warning(request, _('برخی ردیف‌ها هنوز تأیید نشده‌اند.'))

            messages.success(request, _('تغییرات با موفقیت ثبت شدند.'))
            return redirect('factor_item_approve', pk=factor.pk)
        else:
            logger.warning(f"Formset invalid: {formset.errors}")
            messages.error(request, _('فرم نامعتبر است. لطفاً ورودی‌ها را بررسی کنید.'))
            self.object = factor
            return self.render_to_response(self.get_context_data(formset=formset))

    def handle_no_permission(self):
        messages.error(self.request, _('شما مجوز لازم برای تأیید این فاکتور را ندارید.'))
        return redirect('factor_list')
class FactorItemApproveView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_item_approve.html'
    permission_codenames = ['tankhah.FactorItem_approve']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object
        FactorItemApprovalFormSet = formset_factory(FactorItemApprovalForm, extra=0)
        initial_data = [{'item_id': item.id, 'action': item.status} for item in factor.items.all()]

        context['formset'] = FactorItemApprovalFormSet(self.request.POST or None, initial=initial_data)
        context['item_form_pairs'] = zip(factor.items.all(), context['formset'])
        context['approval_logs'] = ApprovalLog.objects.filter(factor_item__factor=factor)
        context['title'] = _('تأیید ردیف‌های فاکتور') + f" - {factor.number}"
        return context

    def post(self, request, *args, **kwargs):
        factor = self.get_object()
        tankhah = factor.tankhah
        user_posts = request.user.userpost_set.all()

        logger.info(f"Processing POST for factor {factor.number}, tankhah {tankhah.number}, current_stage: {tankhah.current_stage.name} (order: {tankhah.current_stage.order})")
        logger.info(f"User posts: {[p.post.name for p in user_posts]}")
        # چک دسترسی و قفل/آرشیو
        if tankhah.is_locked or tankhah.is_archived:
            messages.error(request, _('این تنخواه قفل یا آرشیو شده و قابل تغییر نیست.'))
            return redirect('factor_item_approve', pk=factor.pk)

        # چک مجوز تأیید توی این مرحله
        can_approve = any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts)
        if not can_approve:
            logger.warning(f"User {request.user.username} not authorized to approve stage {tankhah.current_stage.name}")
            messages.error(request, _('شما مجاز به تأیید در این مرحله نیستید.'))
            return redirect('factor_item_approve', pk=factor.pk)

        # ساخت فرم‌ست
        FactorItemApprovalFormSet = formset_factory(FactorItemApprovalForm, extra=0)
        initial_data = [{'item_id': item.id, 'action': item.status} for item in factor.items.all()]
        formset = FactorItemApprovalFormSet(request.POST, initial=initial_data)

        if formset.is_valid():
            with transaction.atomic():
                all_approved = True
                any_rejected = False
                bulk_approve = request.POST.get('bulk_approve') == 'on'

                for form, item in zip(formset, factor.items.all()):
                    action = 'APPROVE' if bulk_approve else form.cleaned_data['action']
                    if action in ['APPROVE', 'REJECT']:
                        ApprovalLog.objects.create(
                            factor_item=item,
                            user=request.user,
                            action=action,
                            stage=tankhah.current_stage,
                            comment=form.cleaned_data.get('comment', ''),
                            post=user_posts.first().post if user_posts.exists() else None
                        )
                        item.status = action
                        item.save()
                        if action == 'REJECT':
                            all_approved = False
                            any_rejected = True
                            tankhah.last_stopped_post = user_posts.first().post if user_posts.exists() else None  # ثبت پست ردکننده
                            tankhah.save()

                if any_rejected:
                    factor.tankhah = None
                    factor.status = 'REJECTED'
                    factor.save()
                    messages.warning(request, _('فاکتور رد شد و از تنخواه جدا شد.'))
                    return redirect('factor_item_approve', pk=factor.pk)

                if all_approved and factor.items.exists():
                    factor.status = 'APPROVED'
                    factor.locked_by_stage = tankhah.current_stage
                    factor.save()
                    if all(f.status == 'APPROVED' for f in tankhah.factors.all()):
                        next_stage = WorkflowStage.objects.filter(order__gt=tankhah.current_stage.order).order_by(
                            'order').first()
                        if next_stage:
                            tankhah.current_stage = next_stage
                            tankhah.status = 'PENDING'
                            tankhah.last_stopped_post = None  # پاک کردن پست متوقف‌شده
                            tankhah.save()
                        else:
                            # مرحله آخر
                            if any(p.post.name == 'معاونت مالی و اداری' for p in user_posts):
                                payment_number = request.POST.get('payment_number', '')
                                if payment_number:
                                    tankhah.status = 'PAID'
                                    tankhah.payment_number = payment_number
                                    tankhah.is_locked = True
                                    tankhah.is_archived = True
                                    tankhah.last_stopped_post = None  # پاک کردن پست متوقف‌شده
                                    tankhah.save()

                                    logger.info(f"Tankhah {tankhah.number} completed")
                                    messages.success(request, _('تنخواه تکمیل شد.'))
                elif any_rejected:
                    factor.status = 'REJECTED'
                    tankhah.status = 'REJECTED'
                    factor.save()
                    tankhah.save()
                    logger.info(f"Factor {factor.number} and tankhah {tankhah.number} rejected")
                    messages.error(request, _('فاکتور و تنخواه رد شدند.'))
                else:
                    factor.status = 'PENDING'
                    factor.save()
                    logger.info(f"Factor {factor.number} still pending")
                    messages.warning(request, _('برخی ردیف‌ها هنوز تأیید نشده‌اند.'))

            messages.success(request, _('تغییرات با موفقیت ثبت شدند.'))
            return redirect('factor_item_approve', pk=factor.pk)
        else:
            logger.warning(f"Formset invalid: {formset.errors}")
            messages.error(request, _('فرم نامعتبر است. لطفاً ورودی‌ها را بررسی کنید.'))
            self.object = factor
            return self.render_to_response(self.get_context_data(formset=formset))


    def handle_no_permission(self):
        messages.error(self.request, _('شما مجوز لازم برای تأیید این فاکتور را ندارید.'))
        return redirect('factor_list')

class FactorItemRejectView(PermissionBaseView, View):
    permission_codenames = ['tankhah.FactorItem_approve']

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
