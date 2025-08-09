from django.db import transaction
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic.edit import UpdateView

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from core.PermissionBase import PermissionBaseView
from core.models import Post, AccessRule
from notificationApp.utils import send_notification
from tankhah.models import Tankhah, Factor , StageApprover, ApprovalLog, CustomUser
from budgets.models import PaymentOrder, Payee
from notificationApp.models import  NotificationRule
import logging
logger = logging.getLogger('EnhancedTankhahUpdateStatusView')


class EnhancedTankhahUpdateStatusView(PermissionBaseView, UpdateView):
    model = Tankhah
    fields = ['status', 'current_stage']
    template_name = 'budgets/paymentorder/tankhah_update_status.html'
    permission_required = 'tankhah.change_tankhah'

    def get_success_url(self):
        return reverse_lazy('tankhah_detail', kwargs={'pk': self.object.pk})

    def send_notifications(self, entity, action, priority, description):
        from django.contrib.contenttypes.models import ContentType
        entity_type = entity.__class__.__name__.upper()
        rules = NotificationRule.objects.filter(entity_type=entity_type, action=action, is_active=True)
        for rule in rules:
            for post in rule.recipients.all():
                users = CustomUser.objects.filter(userpost__post=post, userpost__is_active=True)
                for user in users:
                    send_notification(self.request.user, users=None, posts=None, verb=None, description=None, target=None,
                                          entity_type=None, priority='MEDIUM'
                    )
                    if rule.channel == 'EMAIL':
                        send_mail(
                            subject=description,
                            message=description,
                            from_email='system@example.com',
                            recipient_list=[user.email],
                            fail_silently=True
                        )
            # به‌روزرسانی داشبورد بلادرنگ
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'{entity_type.lower()}_updates',
                {
                    'type': f'{entity_type.lower()}_update',
                    'message': {
                        'entity_type': entity_type,
                        'id': entity.id,
                        'status': entity.status,
                        'description': description
                    }
                }
            )

    def form_valid(self, form):
        user = self.request.user
        try:
            with transaction.atomic():
                tankhah = form.save(commit=False)
                if tankhah.status == 'APPROVED':
                    if tankhah.start_date > timezone.now().date() or (tankhah.end_date and tankhah.end_date < timezone.now().date()):
                        messages.error(self.request, _("تنخواه در بازه زمانی مجاز نیست."))
                        return self.form_invalid(form)
                tankhah.save()
                logger.info(f"Tankhah {tankhah.number} status updated to {tankhah.status} by user {user.username}")

                # اعلان برای به‌روزرسانی تنخواه
                self.send_notifications(
                    entity=tankhah,
                    action='APPROVED' if tankhah.status == 'APPROVED' else 'UPDATED',
                    priority='MEDIUM',
                    description=f"تنخواه {tankhah.number} به وضعیت {tankhah.get_status_display()} به‌روزرسانی شد."
                )

                # بررسی فاکتورهای ردشده
                rejected_factors = tankhah.factors.filter(status='REJECTED')
                for factor in rejected_factors:
                    self.send_notifications(
                        entity=factor,
                        action='REJECTED',
                        priority='HIGH',
                        description=f"فاکتور {factor.number} رد شد. لطفاً در تنخواه جدید ثبت کنید. دلیل: {factor.rejected_reason or 'نامشخص'}"
                    )

                # ایجاد دستور پرداخت
                if tankhah.status == 'APPROVED' and tankhah.current_stage and tankhah.current_stage.triggers_payment_order:
                    payees = tankhah.factors.filter(payee__isnull=False, status='APPROVED').values_list('payee', flat=True).distinct()
                    if not payees:
                        messages.warning(self.request, _("هیچ فاکتور تأییدشده‌ای برای ایجاد دستور پرداخت وجود ندارد."))
                        return super().form_valid(form)
                    for payee_id in payees:
                        self.create_payment_order(tankhah, Payee.objects.get(pk=payee_id), user)

                return super().form_valid(form)

        except Exception as e:
            logger.error(f"Error in EnhancedTankhahUpdateStatusView: {e}", exc_info=True)
            messages.error(self.request, "خطایی در به‌روزرسانی تنخواه یا ایجاد دستور پرداخت رخ داد.")
            return self.form_invalid(form)

    def create_payment_order(self, tankhah, payee, user):
        # initial_po_stage = AccessRule.objects.filter(
        #     entity_type='PAYMENTORDER',
        #     order=1,
        #     is_active=True
        # ).first()
        from core.models import Status
        initial_po_stage = Status.objects.filter(code='PAYMENTORDER', is_initial=True).first()
        if not initial_po_stage:
            logger.error("No initial workflow stage for PAYMENTORDER")
            messages.error(self.request, _("مرحله اولیه گردش کار برای دستور پرداخت تعریف نشده است."))
            return

        user_post = user.userpost_set.filter(is_active=True).first()
        approved_factors = tankhah.factors.filter(payee=payee, status='APPROVED')
        if not approved_factors.exists():
            return

        payment_order = PaymentOrder(
            tankhah=tankhah,
            related_tankhah=tankhah,
            amount=approved_factors.aggregate(total=Sum('amount'))['total'] or 0,
            description=f"پرداخت خودکار برای تنخواه {tankhah.number} (گیرنده: {payee.name})",
            organization=tankhah.organization,
            project=tankhah.project,
            status='DRAFT',
            created_by=user,
            created_by_post=user_post.post if user_post else None,
            current_stage=initial_po_stage,
            issue_date=timezone.now().date(),
            payee=payee,
            min_signatures=initial_po_stage.min_signatures or 1
        )
        payment_order.save()
        payment_order.related_factors.set(approved_factors)

        approving_posts = StageApprover.objects.filter(stage=initial_po_stage, is_active=True).values_list('post', flat=True)
        for post in approving_posts:
            ApprovalLog.objects.create(action=payment_order, approver_post=Post.objects.get(pk=post))

        self.send_notifications(
            entity=payment_order,
            action='CREATED',
            priority='HIGH',
            description=f"دستور پرداخت {payment_order.order_number} برای تنخواه {tankhah.number} ایجاد شد."
        )
        messages.success(self.request, f"دستور پرداخت {payment_order.order_number} ایجاد شد.")