from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.views.generic import DetailView
from accounts.models import CustomUser
from budgets.models import PaymentOrder
from core.PermissionBase import PermissionBaseView
from notificationApp.utils import send_notification
from tankhah.models import  ApprovalLog
from core.models import PostAction, UserPost, AccessRule
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
        if payment_order.status not in ['DRAFT', 'PENDING_APPROVAL', 'PENDING_SIGNATURES']:
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
                stage=payment_order.current_stage,  # استفاده از current_stage دستور پرداخت
                action_type=action_type,
                entity_type=content_type.model.upper(),
                is_active=True
        ).exists():
            messages.error(request, _(f"شما مجاز به {action_type.lower()} این دستور پرداخت نیستید."))
            return redirect('payment_order_sign', pk=payment_order.pk)

        try:
            with transaction.atomic():
                # ثبت لاگ
                ApprovalLog.objects.create(
                    tankhah=payment_order.tankhah,
                    user=user,
                    action=action_type,
                    stage=payment_order.current_stage,
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
                        # ارسال اعلان به خزانه‌دار
                        notify_users = CustomUser.objects.filter(
                            userpost__post__name='خزانه‌دار', userpost__is_active=True
                        ).distinct()

                        send_notification(self.request.user, users=None, posts=None, verb='payment_order_issued',
                                          description=f"دستور پرداخت {payment_order.order_number} صادر شد و آماده پرداخت است.", target=self.object,
                                          entity_type=None, priority='MEDIUM')
                        # notify.send(
                        #     sender=user,
                        #     recipient=notify_users,
                        #     verb='payment_order_issued',
                        #     action_object=payment_order,
                        #     description=
                        # )
                    else:
                        payment_order.status = 'PENDING_SIGNATURES'
                        messages.success(request, _("امضای شما ثبت شد."))
                        # ارسال اعلان به امضاکنندگان بعدی
                        next_posts = AccessRule.objects.filter(
                            organization=payment_order.tankhah.organization,
                            stage=payment_order.current_stage,
                            action_type='SIGN_PAYMENT',
                            entity_type='PAYMENTORDER',
                            is_active=True
                        ).exclude(post=user_post.post).select_related('post')
                        for rule in next_posts:
                            pass
                            # send_notification_to_post_users(rule.post, payment_order)
                else:  # reject
                    payment_order.status = 'CANCELED'
                    messages.success(request, _("دستور پرداخت رد شد."))
                    # ارسال اعلان به ایجادکننده
                    # notify.send(
                    #     sender=user,
                    #     recipient=payment_order.created_by,
                    #     verb='payment_order_canceled',
                    #     action_object=payment_order,
                    #     description=f"دستور پرداخت {payment_order.order_number} توسط {user.get_full_name()} رد شد."
                    # )

                payment_order.save()

        except Exception as e:
            logger.error(f"Error processing PaymentOrder {payment_order.order_number}: {e}", exc_info=True)
            messages.error(request, _("خطا در پردازش دستور پرداخت."))
            return redirect('payment_order_sign', pk=payment_order.pk)

        return redirect('payment_order_sign', pk=payment_order.pk)