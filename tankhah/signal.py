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

@receiver(post_save, sender=FactorItem)
def update_factor_total_amount_on_item_change(sender, instance, **kwargs):
    """
    پس از هر تغییر در یک ردیف فاکتور (ایجاد، ویرایش، حذف)،
    مبلغ کل فاکتور والد را مجدداً محاسبه و به‌روزرسانی می‌کند.
    """
    try:
        logger.debug(
            f"[SIGNAL] FactorItem {instance.pk} changed. Updating total amount for Factor {instance.factor.pk}.")
        # از متد کمکی که در مدل Factor تعریف کردیم، استفاده می‌کنیم.
        instance.factor.update_total_amount()
    except Exception as e:
        logger.error(f"[SIGNAL_ERROR] in update_factor_total_amount_on_item_change for item {instance.pk}: {e}",
                     exc_info=True)


@receiver(post_save, sender=Factor)
def log_factor_creation_in_history(sender, instance, created, **kwargs):
    """
    فقط رویداد "ایجاد" فاکتور را در تاریخچه ثبت می‌کند.
    تغییرات وضعیت در ویوهای مربوطه ثبت می‌شوند تا دقیق‌تر باشند.
    """
    if created:
        try:
            # کاربر را از ریکوئست (اگر در ویو ست شده باشد) یا از خود فاکتور می‌گیریم
            user = getattr(instance, '_request_user', instance.created_by)
            FactorHistory.objects.create(
                factor=instance,
                change_type=FactorHistory.ChangeType.CREATION,
                changed_by=user,
                description=f"فاکتور به شماره {instance.number} توسط {user.username} ایجاد شد."
            )
            logger.debug(f"[SIGNAL] Creation history logged for Factor {instance.pk}.")
        except Exception as e:
            logger.error(f"[SIGNAL_ERROR] in log_factor_creation_in_history for factor {instance.pk}: {e}",
                         exc_info=True)


# ==============================================================================
# سیگنال‌های مربوط به ApprovalLog (برای ارسال نوتیفیکیشن)
# ==============================================================================

@receiver(post_save, sender=ApprovalLog)
def notify_on_new_approval_log(sender, instance, created, **kwargs):
    """
    پس از ثبت یک لاگ اقدام جدید، نوتیفیکیشن‌های لازم را ارسال می‌کند.
    """
    # فقط برای لاگ‌های جدید اجرا شود
    if not created:
        return

    try:
        logger.debug(f"[SIGNAL] New ApprovalLog PK {instance.pk} created. Preparing notifications.")

        # پیدا کردن هدف اصلی (فاکتور یا تنخواه)
        target = instance.factor or instance.tankhah
        if not target:
            logger.warning(
                f"[SIGNAL] ApprovalLog {instance.pk} has no target (Factor/Tankhah). Cannot send notification.")
            return

        # پیدا کردن وضعیت جدید
        new_status = instance.to_status
        if not new_status:
            logger.warning(f"[SIGNAL] ApprovalLog {instance.pk} has no 'to_status'. Cannot determine next approvers.")
            return

        # پیدا کردن تمام گذارهای ممکن از وضعیت جدید
        possible_next_transitions = Transition.objects.filter(
            organization=target.tankhah.organization if hasattr(target, 'tankhah') else target.organization,
            entity_type__code=target.__class__.__name__.upper(),  # FACTOR or TANKHAH
            from_status=new_status,
            is_active=True
        ).prefetch_related('allowed_posts')

        # جمع‌آوری تمام پست‌هایی که در مرحله بعد باید اقدام کنند
        next_approver_posts = {post for trans in possible_next_transitions for post in trans.allowed_posts.all()}

        if next_approver_posts:
            description = _(
                f"{target._meta.verbose_name} #{target.number} برای تأیید در وضعیت '{new_status.name}' برای شما ارسال شد.")

            send_notification(
                sender=instance.user,
                posts=list(next_approver_posts),
                verb="NEEDS_APPROVAL",
                target=target,
                description=description,
                entity_type=target.__class__.__name__.upper()
            )
            logger.info(
                f"[SIGNAL] Notification for new status '{new_status.name}' sent to {len(next_approver_posts)} posts for target {target.pk}.")
        else:
            logger.info(f"[SIGNAL] No next approvers found for status '{new_status.name}'. No notification sent.")

    except Exception as e:
        logger.error(f"[SIGNAL_ERROR] in notify_on_new_approval_log for log {instance.pk}: {e}", exc_info=True)


# ==============================================================================
# سیگنال‌های مربوط به PaymentOrder (دستور پرداخت)
# ==============================================================================

@receiver(post_save, sender=Factor)
def create_payment_order_on_final_approval(sender, instance, **kwargs):
    """
    اگر وضعیت یک فاکتور به "تأیید نهایی" تغییر کرد، به صورت خودکار یک دستور پرداخت ایجاد می‌کند.
    """
    # آیا وضعیت فاکتور معتبر است و آیا از نوع "تایید نهایی" است؟
    if not instance.status or not instance.status.is_final_approve:
        return

    # آیا این فاکتور قبلاً دستور پرداخت داشته؟ (برای جلوگیری از ایجاد تکراری)
    if PaymentOrder.objects.filter(related_factors=instance).exists():
        logger.info(f"[SIGNAL] PaymentOrder already exists for Factor {instance.pk}. Skipping creation.")
        return

    try:
        with transaction.atomic():
            logger.info(f"[SIGNAL] Factor {instance.pk} reached final approval. Attempting to create PaymentOrder.")

            # پیدا کردن وضعیت اولیه برای دستور پرداخت
            initial_po_status = Status.objects.get(entity_type__code='PAYMENTORDER', is_initial=True)

            # ایجاد دستور پرداخت
            payment_order = PaymentOrder.objects.create(
                tankhah=instance.tankhah,
                amount=instance.amount,
                description=_(f"پرداخت خودکار برای فاکتور #{instance.number}"),
                organization=instance.tankhah.organization,
                project=instance.tankhah.project,
                status=initial_po_status,
                created_by=instance.created_by,  # یا آخرین کاربر تایید کننده
                payee=instance.created_by,  # باید منطق پیدا کردن گیرنده وجه را مشخص کنید
            )
            payment_order.related_factors.add(instance)
            logger.info(f"[SIGNAL] PaymentOrder {payment_order.pk} created for Factor {instance.pk}.")

            # اینجا می‌توان سیگنالی برای خود PaymentOrder داشت که نوتیفیکیشن‌های آن را ارسال کند.
            # (مانند سیگنال notify_on_new_approval_log)

    except Status.DoesNotExist:
        logger.error(
            f"[SIGNAL_ERROR] Could not create PaymentOrder for Factor {instance.pk}: Initial status for PAYMENTORDER not found.")
    except Exception as e:
        logger.error(f"[SIGNAL_ERROR] in create_payment_order_on_final_approval for factor {instance.pk}: {e}",
                     exc_info=True)
