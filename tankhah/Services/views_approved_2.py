from django.views.generic import ListView, DetailView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.contenttypes.models import ContentType

from core.PermissionBase import PermissionBaseView
from notificationApp.models import NotificationRule
from notificationApp.views import send_notification
from tankhah.models import Factor, FactorItem, ApprovalLog, AccessRule, Post, ItemCategory
from tankhah.Services.forms_approved_2 import FactorForm, FactorItemFormSet, FactorRejectForm, FactorTempApproveForm, \
    FactorChangeStageForm, FactorBatchApproveForm
from django.utils import timezone
from django.contrib.auth.decorators import permission_required
from django.utils.translation import gettext_lazy as _
import logging
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.contenttypes.models import ContentType
from tankhah.models import Factor, FactorItem, ApprovalLog, AccessRule, Post, Tankhah
from budgets.models import  PaymentOrder

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from budgets.models import BudgetTransaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
from django.db.models import Q, Sum
from django.contrib.auth.decorators import permission_required

logger = logging.getLogger(__name__)


# داشبورد تحلیلی
class DashboardView___(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = 'tankhah/S/dashboard.html'
    permission_required = 'tankhah.factor_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_posts = user.userpost_set.filter(is_active=True)
        org_ids = set(up.post.organization.id for up in user_posts)

        # آمار فاکتورها
        context['total_factors'] = Factor.objects.filter(
            tankhah__organization__id__in=org_ids, is_deleted=False
        ).count()
        context['pending_factors'] = Factor.objects.filter(
            tankhah__organization__id__in=org_ids, status='PENDING_APPROVAL', is_deleted=False
        ).count()
        context['rejected_factors'] = Factor.objects.filter(
            tankhah__organization__id__in=org_ids, status='REJECTED', is_deleted=False
        ).count()
        from django.db.models import Avg
        context['avg_approval_time'] = ApprovalLog.objects.filter(
            factor__tankhah__organization__id__in=org_ids, action='APPROVE'
        ).aggregate(avg_time=Avg('timestamp'))['avg_time']
        return context


# لیست فاکتورها
class FactorListView__(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tankhah/S/factor_list_.html'
    context_object_name = 'factors'
    # permission_required = 'tankhah.factor_view'

    def get_queryset(self):
        user = self.request.user
        user_posts = user.userpost_set.filter(is_active=True)
        org_ids = set(up.post.organization.id for up in user_posts)
        queryset = Factor.objects.filter(
            tankhah__organization__id__in=org_ids,
            is_deleted=False
        ).select_related('tankhah', 'created_by', 'category').order_by('-created_at')

        # فیلترهای پیشرفته
        status = self.request.GET.get('status')
        category = self.request.GET.get('category')
        if status:
            queryset = queryset.filter(status=status)
        if category:
            queryset = queryset.filter(category__id=category)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Factor.STATUS_CHOICES
        context['categories'] = ItemCategory.objects.all()
        context['can_batch_approve'] = self.request.user.has_perm('tankhah.factor_approve')
        return context

# ایجاد فاکتور جدید
class FactorCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/S/factor_edit.html'
    success_url = reverse_lazy('tankhah:factor_list')
    permission_required = 'tankhah.factor_add'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST)
        else:
            context['item_formset'] = FactorItemFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.number = form.instance.generate_number()
            if item_formset.is_valid():
                self.object = form.save(commit=False)
                self.object.save(current_user=self.request.user)
                item_formset.instance = self.object
                item_formset.save()
                ApprovalLog.objects.create(
                    factor=self.object,
                    action='CREATE',
                    stage=self.object.tankhah.current_stage,
                    user=self.request.user,
                    post=self.request.user.userpost_set.filter(is_active=True).first().post,
                    content_type=ContentType.objects.get_for_model(self.object),
                    object_id=self.object.id,
                    comment=_("فاکتور جدید ایجاد شد.")
                )
                messages.success(self.request, _("فاکتور با موفقیت ایجاد شد."))
                send_notification(
                    sender=self.request.user,
                    posts=NotificationRule.objects.filter(
                        entity_type='FACTOR',
                        action='CREATED',
                        is_active=True
                    ).first().recipients.all() if NotificationRule.objects.filter(
                        entity_type='FACTOR',
                        action='CREATED',
                        is_active=True
                    ).exists() else [],
                    verb='CREATED',
                    description=f"فاکتور {self.object.number} ایجاد شد.",
                    target=self.object,
                    entity_type='FACTOR',
                    priority='MEDIUM'
                )
                return super().form_valid(form)
            else:
                return self.form_invalid(form)

# جزئیات فاکتور
class FactorDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Factor
    template_name = 'tankhah/factor_detail.html'
    context_object_name = 'factor'
    permission_required = 'tankhah.factor_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.select_related('factor').all()
        context['approval_logs'] = self.object.approval_logs.select_related('user', 'stage', 'post').order_by(
            '-timestamp')
        context['can_approve'] = self.object.can_approve(self.request.user)
        context['can_reject'] = self.request.user.has_perm('tankhah.factor_reject')
        context['can_unlock'] = self.request.user.has_perm('tankhah.factor_unlock')
        context['can_change_stage'] = self.request.user.has_perm('tankhah.Stepchange')
        context[
            'can_issue_payment'] = self.object.status == 'APPROVED' and self.object.tankhah.current_stage.triggers_payment_order
        return context


# ویرایش فاکتور
class FactorEditView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/factor_edit.html'
    success_url = reverse_lazy('tankhah:factor_list')
    permission_required = 'tankhah.factor_update'

    def get_queryset(self):
        return Factor.objects.filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST, instance=self.object)
        else:
            context['item_formset'] = FactorItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        with transaction.atomic():
            if item_formset.is_valid():
                self.object = form.save(commit=False)
                self.object.save(current_user=self.request.user)
                item_formset.instance = self.object
                item_formset.save()
                ApprovalLog.objects.create(
                    factor=self.object,
                    action='EDIT',
                    stage=self.object.tankhah.current_stage,
                    user=self.request.user,
                    post=self.request.user.userpost_set.filter(is_active=True).first().post,
                    content_type=ContentType.objects.get_for_model(self.object),
                    object_id=self.object.id,
                    comment=_("فاکتور ویرایش شد.")
                )
                messages.success(self.request, _("فاکتور با موفقیت ویرایش شد."))
                self.notify_users(self.object)
                return super().form_valid(form)
            else:
                return self.form_invalid(form)

    def notify_users(self, factor):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'factor_{factor.tankhah.organization.id}',
            {
                'type': 'factor_update',
                'message': f'فاکتور {factor.number} ویرایش شد.'
            }
        )


# تأیید سریع فاکتور
class FactorApproveView__(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'tankhah.factor_approve'

    def post(self, request, pk):
        factor = get_object_or_404(Factor, pk=pk, is_deleted=False)
        if not factor.can_approve(request.user):
            raise PermissionDenied(_("شما مجوز تأیید این فاکتور را ندارید."))
        with transaction.atomic():
            new_status = 'APPROVED' if factor.tankhah.current_stage.is_final_stage else 'APPROVED_INTERMEDIATE'
            factor.status = new_status
            factor.save(current_user=request.user)
            if factor.tankhah.current_stage.auto_advance:
                next_stage = AccessRule.objects.filter(
                    organization=factor.tankhah.organization,
                    entity_type='FACTOR',
                    stage_order__gt=factor.tankhah.current_stage.stage_order,
                    is_active=True
                ).order_by('stage_order').first()
                if next_stage:
                    factor.tankhah.current_stage = next_stage
                    factor.tankhah.save()
            messages.success(request, _("فاکتور با موفقیت تأیید شد."))
            self.notify_users(factor)
        return redirect('tankhah:factor_detail', pk=factor.pk)

    def notify_users(self, factor):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'factor_{factor.tankhah.organization.id}',
            {
                'type': 'factor_update',
                'message': f'فاکتور {factor.number} تأیید شد.'
            }
        )


# رد فاکتور
class FactorRejectView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'tankhah.factor_reject'
    template_name = 'tankhah/factor_reject.html'

    def get(self, request, pk):
        factor = get_object_or_404(Factor, pk=pk, is_deleted=False)
        form = FactorRejectForm()
        return render(request, self.template_name, {'form': form, 'factor': factor})

    def post(self, request, pk):
        factor = get_object_or_404(Factor, pk=pk, is_deleted=False)
        form = FactorRejectForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                factor.status = 'REJECTED'
                factor.rejected_reason = form.cleaned_data['rejected_reason']
                factor.is_locked = True
                factor.save(current_user=request.user)
                ApprovalLog.objects.create(
                    factor=factor,
                    action='REJECT',
                    stage=factor.tankhah.current_stage,
                    user=request.user,
                    post=request.user.userpost_set.filter(is_active=True).first().post,
                    content_type=ContentType.objects.get_for_model(factor),
                    object_id=factor.id,
                    comment=form.cleaned_data['rejected_reason']
                )
                messages.success(request, _("فاکتور با موفقیت رد شد."))
                self.notify_users(factor)
                return redirect('tankhah:factor_detail', pk=factor.pk)
        return render(request, self.template_name, {'form': form, 'factor': factor})

    def notify_users(self, factor):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'factor_{factor.tankhah.organization.id}',
            {
                'type': 'factor_update',
                'message': f'فاکتور {factor.number} رد شد: {factor.rejected_reason}'
            }
        )


# تأیید موقت
class FactorTempApproveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'tankhah.factor_approve'
    template_name = 'tankhah/factor_temp_approve.html'

    def get(self, request, pk):
        factor = get_object_or_404(Factor, pk=pk, is_deleted=False)
        form = FactorTempApproveForm()
        return render(request, self.template_name, {'form': form, 'factor': factor})

    def post(self, request, pk):
        factor = get_object_or_404(Factor, pk=pk, is_deleted=False)
        form = FactorTempApproveForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                factor.status = 'APPROVED_INTERMEDIATE'
                factor.save(current_user=request.user)
                ApprovalLog.objects.create(
                    factor=factor,
                    action='APPROVE',
                    stage=factor.tankhah.current_stage,
                    user=request.user,
                    post=request.user.userpost_set.filter(is_active=True).first().post,
                    content_type=ContentType.objects.get_for_model(factor),
                    object_id=factor.id,
                    comment=form.cleaned_data['comment'],
                    is_temporary=True
                )
                # تنظیم یادآور برای مهلت
                # اینجا می‌توانید منطق یادآور (مثلاً با Celery) اضافه کنید
                messages.success(request, _("فاکتور به‌صورت موقت تأیید شد."))
                self.notify_users(factor)
                return redirect('tankhah:factor_detail', pk=factor.pk)
        return render(request, self.template_name, {'form': form, 'factor': factor})

    def notify_users(self, factor):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'factor_{factor.tankhah.organization.id}',
            {
                'type': 'factor_update',
                'message': f'فاکتور {factor.number} به‌صورت موقت تأیید شد.'
            }
        )


# تغییر مرحله
class FactorChangeStageView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'tankhah.Stepchange'
    template_name = 'tankhah/factor_change_stage.html'

    def get(self, request, pk):
        factor = get_object_or_404(Factor, pk=pk, is_deleted=False)
        form = FactorChangeStageForm(factor=factor)
        return render(request, self.template_name, {'form': form, 'factor': factor})

    def post(self, request, pk):
        factor = get_object_or_404(Factor, pk=pk, is_deleted=False)
        form = FactorChangeStageForm(request.POST, factor=factor)
        if form.is_valid():
            with transaction.atomic():
                new_stage = form.cleaned_data['new_stage']
                if new_stage.stage_order > factor.tankhah.current_stage.stage_order:
                    factor.status = 'PENDING_APPROVAL'
                factor.tankhah.current_stage = new_stage
                factor.tankhah.save()
                ApprovalLog.objects.create(
                    factor=factor,
                    action='STATUS_CHANGE',
                    stage=new_stage,
                    user=request.user,
                    post=request.user.userpost_set.filter(is_active=True).first().post,
                    content_type=ContentType.objects.get_for_model(factor),
                    object_id=factor.id,
                    comment=form.cleaned_data['comment']
                )
                messages.success(request, _("مرحله فاکتور با موفقیت تغییر کرد."))
                self.notify_users(factor)
                return redirect('tankhah:factor_detail', pk=factor.pk)
        return render(request, self.template_name, {'form': form, 'factor': factor})

    def notify_users(self, factor):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'factor_{factor.tankhah.organization.id}',
            {
                'type': 'factor_update',
                'message': f'مرحله فاکتور {factor.number} تغییر کرد.'
            }
        )


# تأیید گروهی
class FactorBatchApproveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'tankhah.factor_approve'
    template_name = 'tankhah/factor_batch_approve.html'

    def get(self, request):
        factor_ids = request.GET.getlist('factor_ids')
        factors = Factor.objects.filter(pk__in=factor_ids, is_deleted=False)
        form = FactorBatchApproveForm()
        return render(request, self.template_name, {'form': form, 'factors': factors})

    def post(self, request):
        factor_ids = request.POST.getlist('factor_ids')
        form = FactorBatchApproveForm(request.POST)
        if form.is_valid():
            factors = Factor.objects.filter(pk__in=factor_ids, is_deleted=False)
            with transaction.atomic():
                for factor in factors:
                    if factor.can_approve(request.user):
                        new_status = 'APPROVED' if factor.tankhah.current_stage.is_final_stage else 'APPROVED_INTERMEDIATE'
                        factor.status = new_status
                        factor.save(current_user=request.user)
                        ApprovalLog.objects.create(
                            factor=factor,
                            action='APPROVE',
                            stage=factor.tankhah.current_stage,
                            user=request.user,
                            post=request.user.userpost_set.filter(is_active=True).first().post,
                            content_type=ContentType.objects.get_for_model(factor),
                            object_id=factor.id,
                            comment=form.cleaned_data['comment']
                        )
                        if factor.tankhah.current_stage.auto_advance:
                            next_stage = AccessRule.objects.filter(
                                organization=factor.tankhah.organization,
                                entity_type='FACTOR',
                                stage_order__gt=factor.tankhah.current_stage.stage_order,
                                is_active=True
                            ).order_by('stage_order').first()
                            if next_stage:
                                factor.tankhah.current_stage = next_stage
                                factor.tankhah.save()
                messages.success(request, _("فاکتورهای انتخاب‌شده با موفقیت تأیید شدند."))
                self.notify_users(factors)
            return redirect('tankhah:factor_list')
        factors = Factor.objects.filter(pk__in=factor_ids, is_deleted=False)
        return render(request, self.template_name, {'form': form, 'factors': factors})

    def notify_users(self, factor, action):
        channel_layer = get_channel_layer()
        rules = NotificationRule.objects.filter(
            entity_type='FACTOR',
            action=action,
            is_active=True
        )
        timestamp = timezone.now().isoformat()
        for rule in rules:
            for post in rule.recipients.all():
                group_name = f"post_{post.id}"
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'notify',
                        'message': f"فاکتور {factor.number} {rule.get_action_display()} شد.",
                        'entity_type': 'FACTOR',
                        'action': action,
                        'priority': rule.priority,
                        'timestamp': timestamp
                    }
                )


# صدور دستور پرداخت
class FactorIssuePaymentView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'tankhah.factor_approve'

    def post(self, request, pk):
        factor = get_object_or_404(Factor, pk=pk, is_deleted=False)
        if not factor.tankhah.current_stage.triggers_payment_order:
            raise PermissionDenied(_("این مرحله اجازه صدور دستور پرداخت ندارد."))
        if factor.amount > factor.get_remaining_budget():
            raise ValidationError(_("بودجه کافی برای صدور دستور پرداخت وجود ندارد."))
        with transaction.atomic():
            factor.status = 'PAID'
            factor.is_locked = True
            factor.save(current_user=request.user)
            PaymentOrder.objects.create(
                tankhah=factor.tankhah,
                action_type='ISSUE_PAYMENT_ORDER',
                amount=factor.amount,
                stage=factor.tankhah.current_stage,
                post=request.user.userpost_set.filter(is_active=True).first().post,
                user=request.user,
                description=f"دستور پرداخت برای فاکتور {factor.number}",
                reference_number=f"PAY-FAC-{factor.number}"
            )
            BudgetTransaction.objects.create(
                allocation=factor.tankhah.project_budget_allocation,
                transaction_type='CONSUMPTION',
                amount=factor.amount,
                related_obj=factor,
                created_by=request.user,
                description=f"مصرف بودجه توسط فاکتور پرداخت شده {factor.number}",
                transaction_id=f"TX-FAC-{factor.number}"
            )
            messages.success(request, _("دستور پرداخت با موفقیت صادر شد."))
            self.notify_users(factor)
        return redirect('tankhah:factor_detail', pk=factor.pk)

    def notify_users(self, factor):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'factor_{factor.tankhah.organization.id}',
            {
                'type': 'factor_update',
                'message': f'دستور پرداخت برای فاکتور {factor.number} صادر شد.'
            }
        )


# باز کردن قفل فاکتور
class FactorUnlockView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'tankhah.factor_unlock'

    def post(self, request, pk):
        factor = get_object_or_404(Factor, pk=pk, is_deleted=False)
        factor.unlock(request.user)
        messages.success(request, _("فاکتور با موفقیت باز شد."))
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'factor_{factor.tankhah.organization.id}',
            {
                'type': 'factor_update',
                'message': f'فاکتور {factor.number} باز شد.'
            }
        )
        return redirect('tankhah:factor_detail', pk=factor.pk)


# گزارش‌گیری
class FactorReportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'tankhah.factor_view'
    template_name = 'tankhah/factor_report.html'

    def get(self, request):
        user = request.user
        user_posts = user.userpost_set.filter(is_active=True)
        org_ids = set(up.post.organization.id for up in user_posts)
        factors = Factor.objects.filter(
            tankhah__organization__id__in=org_ids,
            is_deleted=False
        ).select_related('tankhah', 'created_by', 'category')

        # فیلترهای گزارش
        status = request.GET.get('status')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if status:
            factors = factors.filter(status=status)
        if start_date:
            factors = factors.filter(date__gte=start_date)
        if end_date:
            factors = factors.filter(date__lte=end_date)

        context = {
            'factors': factors,
            'status_choices': Factor.STATUS_CHOICES,
            'total_amount': factors.aggregate(total=Sum('amount'))['total'] or 0,
        }
        return render(request, self.template_name, context)