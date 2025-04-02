from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import DetailView
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.utils.translation import gettext_lazy as _
from .models import Tankhah, Factor, FactorItem, ApprovalLog, WorkflowStage
from .utils import restrict_to_user_organization


class TankhahTrackingView(PermissionRequiredMixin, DetailView):
    model = Tankhah
    template_name = 'tankhah/Reports/tankhah_tracking.html'
    context_object_name = 'tankhah'
    permission_required = 'tankhah.Tankhah_view'

    def get_object(self, queryset=None):
        # گرفتن تنخواه بر اساس شماره یا pk
        obj = super().get_object(queryset)
        user = self.request.user
        # چک دسترسی به سازمان
        if not user.is_superuser:
            user_orgs = restrict_to_user_organization(user)
            if user_orgs and obj.organization not in user_orgs:
                raise PermissionDenied(_('شما به این تنخواه دسترسی ندارید.'))
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object

        # اطلاعات تنخواه
        context['title'] = _('پیگیری تنخواه') + f" - {tankhah.number}"
        context['factors'] = tankhah.factors.all().prefetch_related('items', 'documents', 'approval_logs')
        context['documents'] = tankhah.documents.all()

        # مراحل گردش کار
        workflow_stages = WorkflowStage.objects.order_by('-order')  # از بالا (کارشناس) به پایین (مدیر)
        current_stage = tankhah.current_stage
        context['stages'] = [
            {
                'name': stage.name,
                'order': stage.order,
                'is_current': stage == current_stage,
                'is_completed': stage.order < current_stage.order if current_stage else False,
                'approvals': ApprovalLog.objects.filter(tankhah=tankhah, stage=stage).select_related('user')
            }
            for stage in workflow_stages
        ]

        # لاگ‌های کلی تنخواه
        context['approval_logs'] = ApprovalLog.objects.filter(tankhah=tankhah).select_related('user', 'stage')

        return context

    def handle_no_permission(self):
        messages.error(self.request, _('شما مجوز لازم برای مشاهده این تنخواه را ندارید.'))
        return redirect('factor_list')