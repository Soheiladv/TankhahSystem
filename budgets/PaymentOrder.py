from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import DetailView

from budgets.models import PaymentOrder
from core.PermissionBase import PermissionBaseView
from tankhah.models import  ApprovalLog
from core.models import PostAction, UserPost
from django.contrib.contenttypes.models import ContentType
import logging
from django.utils.translation import gettext_lazy as _
 

class PaymentOrderSignView(PermissionBaseView, DetailView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/payment_order_sign.html'
    permission_required = 'tankhah.PaymentOrder_sign'
    context_object_name = 'payment_order'

    def post(self, request, *args, **kwargs):
        logger = logging.getLogger('payment_order_sign')
        payment_order = self.get_object()
        user = request.user
        user_post = UserPost.objects.filter(user=user, is_active=True, end_date__isnull=True).first()
        if not user_post:
            messages.error(request, _("شما پست فعالی ندارید."))
            return redirect('payment_order_sign', pk=payment_order.pk)

        # بررسی وضعیت دستور پرداخت
        if payment_order.status not in ['DRAFT', 'PENDING_SIGNATURES']:
            messages.error(request, _("این دستور پرداخت قابل امضا یا رد نیست."))
            return redirect('payment_order_sign', pk=payment_order.pk)

        # تعیین نوع اقدام
        action = request.POST.get('action')
        if action not in ['approve', 'reject']:
            messages.error(request, _("اقدام نامعتبر است."))
            return redirect('payment_order_sign', pk=payment_order.pk)

        # بررسی دسترسی
        content_type = ContentType.objects.get_for_model(PaymentOrder)
        action_type = 'SIGN_PAYMENT' if action == 'approve' else 'REJECT'
        if not PostAction.objects.filter(
            post=user_post.post,
            stage=payment_order.tankhah.current_stage,
            action_type=action_type,
            entity_type=content_type.model.upper(),
            is_active=True
        ).exists():
            messages.error(request, _(f"شما مجاز به {action_type.lower()} این دستور پرداخت نیستید."))
            return redirect('payment_order_sign', pk=payment_order.pk)

        # ثبت لاگ
        ApprovalLog.objects.create(
            tankhah=payment_order.tankhah,
            user=user,
            action=action_type,
            stage=payment_order.tankhah.current_stage,
            post=user_post.post,
            content_type=content_type,
            object_id=payment_order.id,
            comment=request.POST.get('comment', '')
        )

        # به‌روزرسانی وضعیت
        if action == 'approve':
            signatures = ApprovalLog.objects.filter(
                content_type=content_type,
                object_id=payment_order.id,
                action='SIGN_PAYMENT'
            ).count()
            if signatures >= payment_order.min_signatures:
                payment_order.status = 'ISSUED'
                messages.success(request, _("دستور پرداخت با موفقیت صادر شد."))
            else:
                payment_order.status = 'PENDING_SIGNATURES'
                messages.success(request, _("امضای شما ثبت شد."))
        else:  # reject
            payment_order.status = 'CANCELED'
            messages.success(request, _("دستور پرداخت رد شد."))

        payment_order.save()
        return redirect('payment_order_sign', pk=payment_order.pk)