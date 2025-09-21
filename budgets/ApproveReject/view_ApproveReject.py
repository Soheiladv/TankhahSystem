from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views import View
from django.http import HttpResponseRedirect
from django.contrib import messages

from budgets.models import BudgetAllocation
from core.PermissionBase import PermissionBaseView
from core.models import Status, PostAction
from tankhah.models import Tankhah, ApprovalLog
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

"""این ویو بررسی می‌کند که آیا کاربر و پست او مجوز انجام اقدام را دارند.
اقدام (تأیید یا رد) را انجام می‌دهد و وضعیت و مرحله را به‌روزرسانی می‌کند.
لاگ اقدام را در ApprovalLog ثبت می‌کند.
از تراکنش اتمیک برای اطمینان از یکپارچگی داده‌ها استفاده می‌کند
"""

class ApproveRejectView(PermissionBaseView, View):
    """اقدامات تأیید/رد
    این ویو بررسی می‌کند که آیا کاربر مجوز و پست مناسب برای انجام اقدام (APPROVE یا REJECT) را دارد.
    برای تنخواه و بودجه به‌صورت جداگانه عمل می‌کند.
    وضعیت (status) و مرحله فعلی (current_stage) موجودیت را به‌روزرسانی می‌کند.
    """
    permission_codenames = ['tankhah.Tankhah_approve', 'tankhah.Tankhah_reject', 'budgets.BudgetAllocation_approve',
                            'budgets.BudgetAllocation_reject']

    def post(self, request, entity_type, entity_id, action):
        user = request.user
        user_posts = user.userpost_set.filter(is_active=True, end_date__isnull=True).values_list('post__id', flat=True)

        # شناسایی موجودیت
        # if entity_type == 'tankhah' and action == 'APPROVE':
        if entity_type == 'tankhah':
            entity = get_object_or_404(Tankhah, id=entity_id)
            required_perm = 'tankhah.Tankhah_approve' if action == 'APPROVE' else 'tankhah.Tankhah_reject'
            entity_type_upper = 'TANKHAH'
        elif entity_type == 'budget_allocation':
            entity = get_object_or_404(BudgetAllocation, id=entity_id)
            required_perm = 'budgets.BudgetAllocation_approve' if action == 'APPROVE' else 'budgets.BudgetAllocation_reject'
            entity_type_upper = 'BUDGET_ALLOCATION'
        else:
            messages.error(request, _('نوع موجودیت نامعتبر است.'))
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', 'dashboard'))

        """اگر یک تنخواه یا تخصیص بودجه به مرحله نهایی (is_final_stage=True در WorkflowStage) برسد، می‌توان وضعیت آن را به COMPLETED یا PAID (برای تنخواه) تغییر داد:"""
        if action == 'APPROVE' and entity.current_stage.is_final_stage:
            entity.status = 'COMPLETED' if entity_type == 'budget_allocation' else 'PAID'
        # بررسی مجوز کاربر
        if not user.has_perm(required_perm):
            messages.error(request, _('شما مجوز انجام این اقدام را ندارید.'))
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', 'dashboard'))

        # بررسی مجوز پست
        if not PostAction.objects.filter(
                post__in=user_posts,
                stage=entity.current_stage,
                action_type=action,
                entity_type=entity_type_upper,
                is_active=True
        ).exists():
            messages.error(request, _('پست شما اجازه انجام این اقدام را در این مرحله ندارد.'))
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', 'dashboard'))

        with transaction.atomic():
            # انجام اقدام
            if action == 'APPROVE':
                entity.status = 'APPROVED'
                entity.approved_by.add(user)
                # انتقال به مرحله بعدی
                next_stage = WorkflowStage.objects.filter(
                    order__gt=entity.current_stage.order,
                    is_active=True
                ).order_by('order').first()
                entity.current_stage = next_stage if next_stage else entity.current_stage
                messages.success(request, _(f'{entity_type.capitalize()} با موفقیت تأیید شد.'))
            elif action == 'REJECT':
                entity.status = 'REJECTED'
                messages.success(request, _(f'{entity_type.capitalize()} با موفقیت رد شد.'))

            # ثبت در ApprovalLog
            user_post = user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
            ApprovalLog.objects.create(
                content_type=ContentType.objects.get_for_model(entity),
                object_id=entity.id,
                action=action,
                stage=entity.current_stage,
                user=user,
                post=user_post.post if user_post else None,
                comment=request.POST.get('comment', ''),
            )

            entity.save()

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', 'dashboard'))