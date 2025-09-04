#
# فایل: tankhah/signals.py (نسخه کامل و نهایی)
#
import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# --- Import های لازم ---
from accounts.middleware import get_current_user
from budgets.models import PaymentOrder, BudgetTransaction
from notificationApp.utils import send_notification
from .models import Tankhah, FactorItem, Factor, ApprovalLog, FactorHistory
from core.models import Status, Action, Transition, Post  # مدل‌های جدید گردش کار

logger = logging.getLogger('TankhahSignalsLogger')


# ==============================================================================
# سیگنال‌های مربوط به Factor و FactorItem
# ==============================================================================
# سیگنال‌های مربوط به Factor و FactorItem
# ==============================================================================

@receiver(post_save, sender=FactorItem)
def update_factor_total_amount_on_item_change(sender, instance, **kwargs):
    """
    پس از تغییر یک ردیف فاکتور، مبلغ کل فاکتور والد را مجدداً محاسبه می‌کند.
    """
    try:
        logger.debug(f"[SIGNAL] FactorItem {instance.pk} changed. Updating total amount for Factor {instance.factor.pk}.")
        instance.factor.update_total_amount()
    except Exception as e:
        logger.error(f"[SIGNAL_ERROR] update_factor_total_amount_on_item_change for item {instance.pk}: {e}", exc_info=True)


@receiver(post_save, sender=Factor)
def log_factor_creation_in_history(sender, instance, created, **kwargs):
    """
    فقط رویداد ایجاد فاکتور را در تاریخچه ثبت می‌کند.
    تغییرات وضعیت در ویو ثبت می‌شوند.
    """
    if created:
        try:
            user = getattr(instance, '_request_user', instance.created_by)
            FactorHistory.objects.create(
                factor=instance,
                change_type=FactorHistory.ChangeType.CREATION,
                changed_by=user,
                description=f"فاکتور #{instance.number} توسط {user.username} ایجاد شد."
            )
            logger.debug(f"[SIGNAL] Creation history logged for Factor {instance.pk}.")
        except Exception as e:
            logger.error(f"[SIGNAL_ERROR] log_factor_creation_in_history for factor {instance.pk}: {e}", exc_info=True)


# ==============================================================================
# سیگنال‌های مربوط به ApprovalLog
# ==============================================================================

@receiver(post_save, sender=ApprovalLog)
def notify_on_new_approval_log(sender, instance, created, **kwargs):
    """
    پس از ثبت یک ApprovalLog جدید، نوتیفیکیشن ارسال می‌کند.
    """
    if not created:
        return

    try:
        logger.debug(f"[SIGNAL] New ApprovalLog PK {instance.pk} created. Preparing notifications.")

        # پیدا کردن هدف اصلی (Factor یا Tankhah)
        target = instance.factor or instance.tankhah or instance.factor_item
        if not target:
            logger.warning(f"[SIGNAL] ApprovalLog {instance.pk} has no target. Cannot send notification.")
            return

        new_status = instance.to_status
        if not new_status:
            logger.warning(f"[SIGNAL] ApprovalLog {instance.pk} has no 'to_status'. Cannot determine next approvers.")
            return

        # پیدا کردن تمام گذارهای ممکن از وضعیت جدید
        possible_next_transitions = Transition.objects.filter(
            organization=getattr(target, 'organization', None) or getattr(target, 'tankhah__organization', None),
            entity_type__code=target.__class__.__name__.upper(),
            from_status=new_status,
            is_active=True
        ).prefetch_related('allowed_posts')

        next_approver_posts = {post for trans in possible_next_transitions for post in trans.allowed_posts.all()}

        if next_approver_posts:
            description = _(
                f"{target._meta.verbose_name} #{getattr(target, 'number', target.pk)} برای تأیید در وضعیت '{new_status.name}' ارسال شد."
            )
            send_notification(
                sender=instance.user,
                posts=list(next_approver_posts),
                verb="NEEDS_APPROVAL",
                target=target,
                description=description,
                entity_type=target.__class__.__name__.upper()
            )
            logger.info(f"[SIGNAL] Notification sent to {len(next_approver_posts)} posts for target {target.pk}.")
        else:
            logger.info(f"[SIGNAL] No next approvers found for status '{new_status.name}'.")

    except Exception as e:
        logger.error(f"[SIGNAL_ERROR] notify_on_new_approval_log for log {instance.pk}: {e}", exc_info=True)


# ==============================================================================
# سیگنال مربوط به ایجاد PaymentOrder بعد از تایید نهایی Factor
# ==============================================================================

@receiver(post_save, sender=Factor)
def create_payment_order_on_final_approval(sender, instance, **kwargs):
    """
    اگر وضعیت Factor به "تأیید نهایی" رسید، PaymentOrder ایجاد کند.
    """
    if not instance.status or not instance.status.is_final_approve:
        return

    if PaymentOrder.objects.filter(related_factors=instance).exists():
        logger.info(f"[SIGNAL] PaymentOrder already exists for Factor {instance.pk}. Skipping creation.")
        return

    try:
        with transaction.atomic():
            logger.info(f"[SIGNAL] Factor {instance.pk} reached final approval. Creating PaymentOrder.")

            initial_po_status = Status.objects.get(entity_type__code='PAYMENTORDER', is_initial=True)

            payment_order = PaymentOrder.objects.create(
                tankhah=instance.tankhah,
                amount=instance.amount,
                description=_(f"پرداخت خودکار برای فاکتور #{instance.number}"),
                organization=instance.tankhah.organization,
                project=instance.tankhah.project,
                status=initial_po_status,
                created_by=instance.created_by,
                payee=instance.created_by,
            )
            payment_order.related_factors.add(instance)
            logger.info(f"[SIGNAL] PaymentOrder {payment_order.pk} created for Factor {instance.pk}.")

    except Status.DoesNotExist:
        logger.error(f"[SIGNAL_ERROR] Initial status for PAYMENTORDER not found for Factor {instance.pk}.")
    except Exception as e:
        logger.error(f"[SIGNAL_ERROR] create_payment_order_on_final_approval for factor {instance.pk}: {e}", exc_info=True)
