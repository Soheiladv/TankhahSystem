from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from notifications.signals import notify
from accounts.models import CustomUser
from core.models import UserPost
from .models import Tankhah, ApprovalLog, WorkflowStage
from core.views import PermissionBaseView
from .utils import restrict_to_user_organization


class TankhahTrackingView(PermissionBaseView, DetailView):
    model = Tankhah
    template_name = 'tankhah/Reports/tankhah_tracking.html'
    context_object_name = 'tankhah'
    permission_required = 'tankhah.Tankhah_view'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if not user.is_superuser:
            user_orgs = restrict_to_user_organization(user)
            if user_orgs and obj.organization not in user_orgs:
                raise PermissionDenied(_('شما به این تنخواه دسترسی ندارید.'))
        return obj

    def post(self, request, *args, **kwargs):
        tankhah = self.get_object()
        if 'archive' in request.POST and not tankhah.is_archived:
            tankhah.is_archived = True
            tankhah.archived_at = timezone.now()
            tankhah.save()
            messages.success(request, _('تنخواه با موفقیت آرشیو شد.'))
        return redirect('tankhah_tracking', pk=tankhah.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object
        user_post = UserPost.objects.filter(user=self.request.user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0

        # اطلاعات تنخواه
        context['title'] = _('پیگیری تنخواه') + f" - {tankhah.number}"
        context['factors'] = tankhah.factors.all().prefetch_related('items__approval_logs', 'documents', 'approval_logs')
        context['documents'] = tankhah.documents.all()

        # آپدیت مراحل گردش کار
        workflow_stages = WorkflowStage.objects.order_by('order')  # از 1 به بالا
        current_stage = tankhah.current_stage
        if not current_stage:  # اگر مرحله فعلی تنظیم نشده
            tankhah.current_stage = workflow_stages.first()  # order=1
            tankhah.save()

        # بررسی پیشرفت مراحل
        stages_data = []
        for stage in workflow_stages:
            approvals = ApprovalLog.objects.filter(
                tankhah=tankhah,
                stage=stage
            ).select_related('user', 'post') | ApprovalLog.objects.filter(
                factor__tankhah=tankhah,
                stage=stage
            ).select_related('user', 'post') | ApprovalLog.objects.filter(
                factor_item__factor__tankhah=tankhah,
                stage=stage
            ).select_related('user', 'post')

            is_completed = approvals.filter(action='APPROVE').exists() and stage.order < tankhah.current_stage.order
            if not is_completed and approvals.filter(action='APPROVE').exists() and stage == tankhah.current_stage:
                # انتقال به مرحله بعدی
                # next_stage = workflow_stages.filter(order__gt=stage.order).first()
                # next_stage = workflow_stages.filter(order__lt=stage.order).order_by('-order').first()
                next_stage = workflow_stages.filter(order__gt=stage.order).order_by('order').first()  # از 1 به 2 به 3
                if next_stage:
                    tankhah.current_stage = next_stage
                    tankhah.save()
                elif all(f.status == 'APPROVED' for f in tankhah.factors.all()):
                    tankhah.status = 'APPROVED'
                    tankhah.save()

            stages_data.append({
                'name': stage.name,
                'order': stage.order,
                'is_current': stage == tankhah.current_stage,
                'is_completed': is_completed,
                'approvals': approvals,
                'approvers': [
                    f"{approver.post.name} ({userpost.user.get_full_name()})"
                    for approver in stage.stageapprover_set.prefetch_related('post__userpost_set__user').all()
                    for userpost in approver.post.userpost_set.filter(end_date__isnull=True)
                ],
            })
        context['stages'] = stages_data

        # چک مجوز تغییر وضعیت فاکتور
        context['can_approve_factor'] = self.request.user.has_perm('tankhah.FactorItem_approve')

        # چک رده بالاتر و ثبت "دیده شدن"
        if user_level > (tankhah.last_stopped_post.level if tankhah.last_stopped_post else 0):
            logs_to_update = ApprovalLog.objects.filter(tankhah=tankhah, seen_by_higher=False).exclude(user=self.request.user)
            if logs_to_update.exists():
                logs_to_update.update(seen_by_higher=True, seen_at=timezone.now())
                lower_users = CustomUser.objects.filter(
                    userpost__post__level__lt=user_level,
                    userpost__end_date__isnull=True
                ).distinct()
                notify.send(
                    self.request.user,
                    recipient=lower_users,
                    verb='تنخواه شما توسط رده بالاتر دیده شد',
                    target=tankhah
                )

        # خلاصه آماری
        factors = tankhah.factors.all()
        context['stats'] = {
            'total_amount': sum(f.amount for f in factors),
            'approved_amount': sum(f.amount for f in factors if f.status == 'APPROVED'),
            'rejected_amount': sum(f.amount for f in factors if f.status == 'REJECTED'),
            'pending_amount': sum(f.amount for f in factors if f.status == 'PENDING'),
        }
        context['can_archive'] = not tankhah.is_archived and self.request.user.has_perm('tankhah.Tankhah_change')

        return context

    def handle_no_permission(self):
        messages.error(self.request, _('شما مجوز لازم برای مشاهده این تنخواه را ندارید.'))
        return redirect('factor_list')