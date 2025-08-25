import logging

import jdatetime
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
# ---
from django.views.generic import TemplateView

from accounts.has_role_permission import has_permission
from accounts.models import CustomUser
from core.models import UserPost, Post, WorkflowStage
from .forms import ApprovalForm, FactorItemApprovalForm, FactorApprovalForm
from .forms import FactorForm, FactorItemFormSet
from .forms import TanbakhForm, FactorDocumentFormSet, TanbakhApprovalForm
from .models import Factor, ApprovalLog
from .models import Tanbakh, StageApprover
from .utils import restrict_to_user_organization
from django.forms import formset_factory

logger = logging.getLogger(__name__)
from notifications.signals import notify
from .forms import TanbakhStatusForm


# -------
###########################################
class DashboardView(LoginRequiredMixin, TemplateView):
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
                 'perm': 'tanbakh.Factor_view'},
                {'url': 'factor_create', 'label': _('ایجاد فاکتور'), 'icon': 'fas fa-plus',
                 'perm': 'tanbakh.Factor_add'},
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
@method_decorator(has_permission('Tanbakh_add'), name='dispatch')
class TanbakhManageView(LoginRequiredMixin, CreateView):
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
@method_decorator(has_permission('Tanbakh_part_approve'), name='dispatch')
class TanbakhUpdateView(LoginRequiredMixin, UpdateView):
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
@method_decorator(has_permission('Tanbakh_add'), name='dispatch')
class TanbakhCreateView(LoginRequiredMixin, CreateView):
    model = Tanbakh
    form_class = TanbakhForm
    template_name = 'tanbakh/tanbakh_form.html'
    success_url = reverse_lazy('tanbakh_list')

    def dispatch(self, request, *args, **kwargs):
        if not any(up.post.organization.org_type == 'HQ' for up in request.user.userpost_set.all()):
            raise PermissionDenied("فقط کاربران دفتر مرکزی می‌توانند تنخواه ایجاد کنند.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        tanbakh = self.object
        first_stage = WorkflowStage.objects.get(order=1)
        tanbakh.current_stage = first_stage
        tanbakh.status = 'DRAFT'  # اضافه کردن وضعیت اولیه
        tanbakh.save()
        # ارسال اعلان به تأییدکنندگان مرحله اول
        approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=first_stage)
        notify.send(self.request.user, recipient=approvers, verb='تنخواه جدیدی ایجاد شد', target=tanbakh)
        messages.success(self.request, _('تنخواه با موفقیت ثبت شد.'))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد تنخواه جدید')
        return context

class TanbakhListView1(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_list.html'
    context_object_name = 'tanbakhs'
    paginate_by = 10
    extra_context = {'title': _('لیست تنخواه‌ها')}

    # لیست مجوزها
    permission_required = (
        'tanbakh.Tanbakh_view','Tanbakh_update','Tanbakh_add',
        'tanbakh.Tanbakh_approve',
        'tanbakh.Tanbakh_part_approve',
        'tanbakh.FactorItem_approve','edit_full_tanbakh',
        'Tanbakh_hq_view',
        'Tanbakh_hq_approve','Tanbakh_HQ_OPS_PENDING','Tanbakh_HQ_OPS_APPROVED',"FactorItem_approve"
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


class TanbakhListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
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
        user = self.request.user
        user_orgs = [up.post.organization for up in user.userpost_set.all()]
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)

        # اگر کاربر HQ است، همه تنخواه‌ها را نشان بده، در غیر این صورت فقط تنخواه‌های سازمان کاربر
        queryset = Tanbakh.objects.all() if is_hq_user else Tanbakh.objects.filter(organization__in=user_orgs)

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
        user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()]
        context['user_orgs'] = user_orgs
        context['is_hq_user'] = any(org.org_type == 'HQ' for org in user_orgs)
        context['query'] = self.request.GET.get('q', '')
        context['stage'] = self.request.GET.get('stage', '')
        context['show_archived'] = self.request.GET.get('show_archived', 'false') == 'true'
        return context


class TanbakhDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_detail.html'
    context_object_name = 'tanbakh'

    # مجوزهای نمایشی (حداقل یکی لازم است)
    permission_required = (
        'tanbakh.Tanbakh_view','Tanbakh_update',
        'tanbakh.Tanbakh_hq_view','Tanbakh_HQ_OPS_APPROVED','edit_full_tanbakh'
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
        context['current_date'] = jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M') # تاریخ فعلی برای چاپ
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

@method_decorator(has_permission('Tanbakh_delete'), name='dispatch')
class TanbakhDeleteView(LoginRequiredMixin, DeleteView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_confirm_delete.html'
    success_url = reverse_lazy('tanbakh_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تنخواه با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)

# ویو تأیید:
class TanbakhApproveView(UpdateView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_approve.html'
    permission_required = 'Tanbakh_approve','Tanbakh_update','FactorItem_approve'
    success_url = reverse_lazy('tanbakh_list')
    form_class = TanbakhApprovalForm

    def get_object(self, queryset=None):
        obj = get_object_or_404(Tanbakh, pk=self.kwargs['pk'])
        obj.refresh_from_db()
        if obj.status not in ['PENDING', 'DRAFT']:
            messages.error(self.request, _('این تنخواه قابل 👎تأیید نیست زیرا در وضعیت در انتظار نیست.'))
            raise ValueError("تنخواه در وضعیت غیرقابل 👎تأیید")
        return obj

    def form_valid(self, form):
        action = self.request.POST.get('action', 'APPROVE')
        tanbakh = self.get_object()
        user = self.request.user

        if action == 'RETURN':
            previous_stage = WorkflowStage.objects.filter(order__lt=tanbakh.current_stage.order).order_by('-order').first()
            if previous_stage:
                tanbakh.current_stage = previous_stage
                tanbakh.save()
                messages.info(self.request, f"تنخواه به مرحله {previous_stage.name} بازگشت.")
        elif action == 'CANCEL':
            tanbakh.canceled = True
            tanbakh.save()
            messages.info(self.request, "تنخواه لغو شد.")
        else:
            if not WorkflowStage.objects.exists():
                messages.error(self.request, _("هیچ مرحله‌ای در سیستم تعریف نشده است."))
                return self.form_invalid(form)

            stage = tanbakh.current_stage
            if not stage:
                stage = WorkflowStage.objects.order_by('order').first()
                if not stage:
                    messages.error(self.request, _("مرحله‌ای برای شروع وجود ندارد."))
                    return self.form_invalid(form)
                tanbakh.current_stage = stage
                tanbakh.save()

            if not StageApprover.objects.filter(stage=stage, post__userpost__user=user).exists():
                messages.error(self.request, _('شما مجاز به تأیید در این مرحله نیستید.'))
                return self.form_invalid(form)

            with transaction.atomic():
                ApprovalLog.objects.create(
                    tanbakh=tanbakh,
                    user=user,
                    action=action,
                    stage=stage,
                    comment=form.cleaned_data['comment'],
                    post=user.userpost_set.first().post if user.userpost_set.exists() else None
                )
                if action == 'APPROVE':
                    next_stage = WorkflowStage.objects.filter(order__gt=stage.order).order_by('order').first()
                    if next_stage:
                        tanbakh.current_stage = next_stage
                    else:
                        tanbakh.status = 'APPROVED'
                    tanbakh.approved_by.add(user)
                    if next_stage:
                        approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                        notify.send(
                            self.request.user,
                            recipient=approvers,
                            verb='تنخواه در انتظار تأیید شما',
                            target=tanbakh
                        )
                elif action == 'REJECT':
                    tanbakh.status = 'REJECTED'
                tanbakh.save()

        messages.success(self.request, _('تنخواه با موفقیت تأیید👍 شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('خطایی 😒در تأیید تنخواه رخ داد.'))
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('تأیید تنخواه')
        context['tanbakh'] = self.get_object()
        return context

# ویو رد:
class TanbakhRejectView(  UpdateView):
    model = Tanbakh
    fields = []
    template_name = 'tanbakh/tanbakh_reject.html'
    permission_required = 'Tanbakh_approve','Tanbakh_update','FactorItem_approve'
    success_url = reverse_lazy('tanbakh_list')

    def get_object(self, queryset=None):
        obj = get_object_or_404(Tanbakh, pk=self.kwargs['pk'])
        obj.refresh_from_db()
        if obj.status not in ['PENDING', 'DRAFT', 'APPROVED']:
            messages.error(self.request, _('این تنخواه قابل رد نیست زیرا در وضعیت مناسب نیست.'))
            raise ValueError("تنخواه در وضعیت غیرقابل رد")
        return obj

    def form_valid(self, form):
        tanbakh = self.get_object()
        user = self.request.user

        stage = tanbakh.current_stage
        if not stage and WorkflowStage.objects.exists():
            stage = WorkflowStage.objects.order_by('order').first()
            tanbakh.current_stage = stage
            tanbakh.save()

        ApprovalLog.objects.create(
            tanbakh=tanbakh,
            user=user,
            action='REJECT',
            stage=stage,
            comment=form.cleaned_data.get('comment', '')
        )
        tanbakh.status = 'REJECTED'
        tanbakh.save()
        messages.success(self.request, _('تنخواه با رد 👎 شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('خطایی 👎در رد تنخواه رخ داد.'))
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('رد تنخواه')
        context['tanbakh'] = self.get_object()
        return context

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
class ApprovalLogListView(LoginRequiredMixin, ListView):
    model = ApprovalLog
    template_name = 'tanbakh/approval_log_list.html'
    context_object_name = 'logs'
    paginate_by = 10

    def get_queryset(self):
        return ApprovalLog.objects.filter(tanbakh__number=self.kwargs['tanbakh_number']).order_by('-timestamp')

# --- Factor Views ---
@method_decorator(has_permission('Factor_view'), name='dispatch')
class FactorListView(LoginRequiredMixin, ListView):
    model = Factor
    template_name = 'tanbakh/factor_list.html'
    context_object_name = 'factors'
    paginate_by = 10
    extra_context = {'title': _('لیست فاکتورها')}

    def get_queryset(self):
        user = self.request.user
        user_posts = user.userpost_set.all()
        if not user_posts.exists():
            return Factor.objects.none()  # اگر کاربر به پستی متصل نیست، چیزی نشان نده

        user_orgs = [up.post.organization for up in user.userpost_set.all()]
        is_hq_user = any(up.post.organization.org_type == 'HQ' for up in user.userpost_set.all())

        if is_hq_user:
            queryset = Factor.objects.all()
        else:
            queryset = Factor.objects.filter(tanbakh__organization__in=user_orgs)

        query = self.request.GET.get('q', '').strip()
        date_query = self.request.GET.get('date', '').strip()
        if query or date_query:
            filter_conditions = Q()
            if query:
                filter_conditions |= (
                        Q(number__icontains=query) |
                        Q(tanbakh__number__icontains=query) |
                        Q(amount__icontains=query) |
                        Q(description__icontains=query) |
                        Q(status__icontains=query)
                )
            if date_query:
                filter_conditions &= Q(date=date_query)
            queryset = queryset.filter(filter_conditions).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('لیست فاکتورها')
        context['query'] = self.request.GET.get('q', '')
        context['is_hq'] = any(up.post.organization.org_type == 'HQ' for up in self.request.user.userpost_set.all())
        return context

@method_decorator(has_permission('Factor_view'), name='dispatch')
class FactorDetailView(LoginRequiredMixin, DetailView):
    model = Factor
    template_name = 'tanbakh/factor_detail.html'
    context_object_name = 'factor'
    extra_context = {'title': _('جزئیات فاکتور')}
    permission_denied_message = 'متاسفانه دسترسی مجاز ندارید'
    permission_required = 'Factor_view','Factor_update'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all()
        context['title'] = _('جزئیات فاکتور') + f" - {self.object.number}"
        return context

@method_decorator(has_permission('Factor_add'), name='dispatch')
class FactorCreateView(CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tanbakh/factor_form.html'
    success_url = reverse_lazy('factor_list')
    permission_required = 'tanbakh.Factor_add'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES)
            context['document_formset'] = FactorDocumentFormSet(self.request.POST, self.request.FILES)
        else:
            context['item_formset'] = FactorItemFormSet()
            context['document_formset'] = FactorDocumentFormSet()
        context['title'] = _('ایجاد فاکتور جدید')
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        tanbakh = self.request.POST.get('tanbakh') or (self.object.tanbakh if self.object else None)
        if tanbakh:
            tanbakh_obj = Tanbakh.objects.get(id=tanbakh)
            restrict_to_user_organization(self.request.user, tanbakh_obj.organization)
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        document_formset = context['document_formset']
        tanbakh = form.cleaned_data['tanbakh']

        # اجازه ثبت فاکتور در وضعیت DRAFT یا PENDING
        if tanbakh.status not in ['DRAFT', 'PENDING']:
            messages.error(self.request, 'فقط می‌توانید برای تنخواه‌های پیش‌نویس یا در انتظار فاکتور ثبت کنید.')
            return self.form_invalid(form)

        if tanbakh.current_stage.order != 1:
            messages.error(self.request, _('فقط در مرحله اولیه می‌توانید فاکتور ثبت کنید.'))
            return self.form_invalid(form)

        if item_formset.is_valid() and document_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()
                document_formset.instance = self.object
                document_formset.save()
                # تغییر وضعیت تنخواه به PENDING پس از ثبت فاکتور
                if tanbakh.status == 'DRAFT':
                    tanbakh.status = 'PENDING'
                    tanbakh.save()
            messages.success(self.request, _('فاکتور با موفقیت ثبت شد.'))
            return super().form_valid(form)
        return self.form_invalid(form)

@method_decorator(has_permission('Factor_update'), name='dispatch')
class FactorUpdateView( UpdateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tanbakh/factor_form.html'
    success_url = reverse_lazy('factor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, instance=self.object)
            context['document_formset'] = FactorDocumentFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context['item_formset'] = FactorItemFormSet(instance=self.object)
            context['document_formset'] = FactorDocumentFormSet(instance=self.object)
        context['title'] = _('ویرایش فاکتور') + f" - {self.object.number}"
        total_amount = sum(item.amount * item.quantity for item in self.object.items.all())
        context['total_amount'] = total_amount
        return context

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.locked:
            raise PermissionDenied("این فاکتور قفل شده و قابل ویرایش نیست.")
        return obj

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        tanbakh = self.request.POST.get('tanbakh') or (self.object.tanbakh if self.object else None)
        if tanbakh:
            tanbakh_obj = Tanbakh.objects.get(id=tanbakh)
            restrict_to_user_organization(self.request.user, tanbakh_obj.organization)
        return kwargs

    def form_valid(self, form):
        if self.object.tanbakh.current_stage.order != 1 or self.object.is_finalized:
            messages.error(self.request, _('فقط در مرحله اولیه و قبل از نهایی شدن می‌توانید فاکتور را ویرایش کنید.'))
            return self.form_invalid(form)
        context = self.get_context_data()
        item_formset = context['item_formset']
        document_formset = context['document_formset']
        if item_formset.is_valid() and document_formset.is_valid():
            self.object = form.save()
            item_formset.instance = self.object
            item_formset.save()
            document_formset.instance = self.object
            document_formset.save()
            messages.success(self.request, _('فاکتور با موفقیت به‌روزرسانی شد.'))
            return super().form_valid(form)
        return self.form_invalid(form)

@method_decorator(has_permission('Factor_delete'), name='dispatch')
class FactorDeleteView(LoginRequiredMixin, DeleteView):
    model = Factor
    template_name = 'tanbakh/factor_confirm_delete.html'
    success_url = reverse_lazy('factor_list')
    permission_required = 'tanbakh.Factor_delete'

    def dispatch(self, request, *args, **kwargs):
        factor = self.get_object()
        if factor.tanbakh.current_stage.order != 1:
            messages.error(request, _('حذف فاکتور فقط در مرحله اولیه امکان‌پذیر است.'))
            return redirect('factor_list')
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('فاکتور با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)

# - جدید رد یا تایید مدیر شبعه برای فاکتور ها و ردیف ها
@method_decorator(has_permission('Factor_update'), name='dispatch')
class FactorApprovalView(LoginRequiredMixin, UpdateView):
    model = Factor
    form_class = FactorApprovalForm  # استفاده از فرم پیشنهادی
    template_name = 'tanbakh/factor_approval.html'
    success_url = reverse_lazy('factor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('تأیید فاکتور') + f" - {self.object.number}"
        # حذف فرم‌ست و ارسال مستقیم ردیف‌ها به تمپلیت
        context['items'] = self.object.items.all()
        return context

    def form_valid(self, form):
        tanbakh = self.object.tanbakh
        if tanbakh.current_stage.order != 2:
            messages.error(self.request, _('فقط در مرحله تأیید مدیر شعبه می‌توانید اقدام کنید.'))
            return self.form_invalid(form)

        user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()]
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)
        if not is_hq_user and tanbakh.organization not in user_orgs:
            messages.error(self.request, _('شما به این فاکتور دسترسی ندارید.'))
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            all_approved = all(item.status == 'APPROVED' for item in self.object.items.all())
            if all_approved:
                tanbakh.current_stage = WorkflowStage.objects.get(order=3)
                tanbakh.status = 'APPROVED'
                tanbakh.save()
                messages.success(self.request, _('فاکتور تأیید شد و به دفتر مرکزی ارسال شد.'))
            else:
                messages.warning(self.request, _('برخی ردیف‌ها رد شده‌اند.'))
        return super().form_valid(form)

class FactorItemApproveView(DetailView):
    model = Factor
    template_name = 'tanbakh/factor_item_approve.html'
    permission_required = ('tanbakh.FactorItem_approve', 'tanbakh.Tanbakh_approve',
                           'tanbakh.Tanbakh_update', 'tanbakh.FactorItem_approve')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.get_object()

        # Create formset for all items
        FactorItemApprovalFormSet = formset_factory(FactorItemApprovalForm, extra=0)
        initial_data = [{'item_id': item.id} for item in factor.items.all()]

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
        stage = tanbakh.current_stage

        if not StageApprover.objects.filter(stage=stage, post__userpost__user=user).exists():
            messages.error(request, _('شما مجاز به تأیید در این مرحله نیستید.'))
            return redirect('factor_item_approve', pk=factor.pk)

        FactorItemApprovalFormSet = formset_factory(FactorItemApprovalForm, extra=0)
        formset = FactorItemApprovalFormSet(request.POST)

        with transaction.atomic():
            if formset.is_valid():
                all_approved = True
                any_rejected = False

                # Handle bulk approval if checkbox is selected
                bulk_approve = request.POST.get('bulk_approve') == 'on'

                for form, item in zip(formset, factor.items.all()):
                    action = 'APPROVE' if bulk_approve else form.cleaned_data['action']

                    if action in ['APPROVE', 'REJECT']:
                        ApprovalLog.objects.create(
                            factor_item=item,
                            user=user,
                            action=action,
                            stage=stage,
                            comment=form.cleaned_data['comment'],
                            post=user.userpost_set.first().post if user.userpost_set.exists() else None
                        )
                        item.status = action
                        item.save()
                        if action == 'REJECT':
                            all_approved = False
                            any_rejected = True
                        elif action != 'APPROVE':
                            all_approved = False

                # Rest of your existing logic remains the same
                if all_approved and factor.items.exists():
                    factor.status = 'APPROVED'
                    factor.is_finalized = True
                elif any_rejected:
                    factor.status = 'REJECTED'
                    factor.is_finalized = True
                else:
                    factor.status = 'PENDING'
                factor.save()

                # Workflow progression logic remains the same
                if all(f.is_finalized and f.status == 'APPROVED' for f in tanbakh.factors.all()):
                    next_stage = WorkflowStage.objects.filter(order__gt=stage.order).order_by('order').first()
                    if next_stage:
                        tanbakh.current_stage = next_stage
                        tanbakh.save()
                        approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                        notify.send(request.user, recipient=approvers, verb='تنخواه در انتظار تأیید شما',
                                    target=tanbakh)
                        messages.info(request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                    else:
                        tanbakh.status = 'APPROVED'
                        tanbakh.is_archived = True
                        tanbakh.save()
                        messages.info(request, "تنخواه تأیید و آرشیو شد.")

            messages.success(request, _('تغییرات با موفقیت ثبت شدند.'))
            return redirect('factor_item_approve', pk=factor.pk)

# --- Approval Views ---
@method_decorator(has_permission('Approval_view'), name='dispatch')
class ApprovalListView(LoginRequiredMixin, ListView):
    model = ApprovalLog
    template_name = 'tanbakh/approval_list.html'
    context_object_name = 'approvals'
    paginate_by = 10
    extra_context = {'title': _('لیست تأییدات')}

@method_decorator(has_permission('Approval_view'), name='dispatch')
class ApprovalDetailView(LoginRequiredMixin, DetailView):
    model = ApprovalLog
    template_name = 'tanbakh/approval_detail.html'
    context_object_name = 'approval'
    extra_context = {'title': _('جزئیات تأیید')}

@method_decorator(has_permission('Approval_add'), name='dispatch')
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

@method_decorator(has_permission('Approval_update'), name='dispatch')
class ApprovalUpdateView(PermissionRequiredMixin, UpdateView):
    model = ApprovalLog
    form_class = ApprovalForm
    template_name = 'tanbakh/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'tanbakh.Approval_update'

    def form_valid(self, form):
        messages.success(self.request, _('تأیید با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

@method_decorator(has_permission('Approval_delete'), name='dispatch')
class ApprovalDeleteView(PermissionRequiredMixin, DeleteView):
    model = ApprovalLog
    template_name = 'tanbakh/approval_confirm_delete.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'tanbakh.Approval_delete'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تأیید با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)

# -- وضعیت تنخواه
