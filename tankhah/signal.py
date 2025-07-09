import logging
from decimal import Decimal

from django.db.models import Sum
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from tankhah.models import Tankhah, FactorItem, create_budget_transaction, Factor, ApprovalLog

logger = logging.getLogger(__name__)


@receiver(post_save, sender=FactorItem)
def handle_factor_item_budget_transaction(sender, instance, created, **kwargs):
    if created and instance.status not in ['APPROVED', 'PAID']:
        return  # برای آیتم‌های جدید با وضعیت غیرتأیید، تراکنش ثبت نمی‌شود
    try:
        original_status = None
        if not created:
            original_status = FactorItem.objects.get(pk=instance.pk).status
        if instance.status != original_status:
            logger.info(f"FactorItem {instance.pk} status changed from {original_status} to {instance.status}")
            allocation = instance.factor.tankhah.budget_allocation
            if instance.status in ['APPROVED', 'PAID']:
                create_budget_transaction(
                    allocation=allocation,
                    transaction_type='CONSUMPTION',
                    amount=instance.amount,
                    related_obj=instance,
                    created_by=instance.factor.created_by,
                    description=f"مصرف بودجه برای ردیف فاکتور {instance.factor.number} (pk:{instance.pk})",
                    transaction_id=f"TX-FAC-ITEM-{instance.factor.number}-{instance.pk}-{timezone.now().timestamp()}"
                )
            elif instance.status == 'REJECTED' and original_status in ['APPROVED', 'PAID']:
                create_budget_transaction(
                    allocation=allocation,
                    transaction_type='RETURN',
                    amount=instance.amount,
                    related_obj=instance,
                    created_by=instance.factor.created_by,
                    description=f"بازگشت بودجه به دلیل رد ردیف فاکتور {instance.factor.number} (pk:{instance.pk})",
                    transaction_id=f"TX-FAC-ITEM-RET-{instance.factor.number}-{instance.pk}-{timezone.now().timestamp()}"
                )
    except Exception as e:
        logger.error(f"Error in FactorItem budget transaction signal: {e}", exc_info=True)


"""به جای به‌روزرسانی در FactorItem.save، از سیگنال یا متد ویو استفاده کنید:"""
from django.db.models.signals import post_save, post_delete
@receiver([post_save, post_delete], sender=FactorItem)
def update_factor_and_tankhah(sender, instance, **kwargs):
    try:
        factor = instance.factor
        factor.amount = factor.items.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        factor.save(update_fields=['amount'])
        tankhah = factor.tankhah
        from budgets.budget_calculations import get_tankhah_remaining_budget
        tankhah.remaining_budget = get_tankhah_remaining_budget(tankhah)
        tankhah.save(update_fields=['remaining_budget'])
    except Exception as e:
        logger.error(f"Error updating factor/tankhah for FactorItem (Signal Tankhah) {instance.pk}: {e}", exc_info=True)


@receiver(post_save, sender=Factor)
def log_factor_changes(sender, instance, created, **kwargs):
    """عملکرد: این سیگنال پس از ذخیره یا ایجاد فاکتور (Factor) اجرا می‌شود. اگر فاکتور جدید باشد، ایجاد آن لاگ می‌شود. اگر فاکتور موجود ویرایش شود، تغییرات فیلدها در لاگ ثبت می‌شوند.
    تأثیر: اگر در فرآیند ثبت تنخواه فاکتوری ایجاد یا ویرایش شود، این سیگنال آن را لاگ می‌کند. اما در TankhahCreateView هیچ اشاره‌ای به ایجاد یا ویرایش فاکتور نیست، بنابراین این سیگنال احتمالاً در مرحله ثبت اولیه تنخواه اجرا نمی‌شود.
    """
    user = getattr(instance, '_changed_by', None)  # کاربر تغییر دهنده
    if created:
        logger.info(f"فاکتور جدید ایجاد شد: {instance.number} توسط {user or 'ناشناس'}")
    else:
        changes = instance._meta.fields  # تغییرات را بررسی کنید
        for field in changes:
            field_name = field.name
            old_value = getattr(instance, f'_old_{field_name}', None)
            new_value = getattr(instance, field_name)
            if old_value != new_value:
                logger.info(
                    f"تغییر در فاکتور {instance.number}: {field_name} از {old_value} به {new_value} توسط {user or 'ناشناس'}")


@receiver(post_save, sender=ApprovalLog)
def lock_factor_after_approval(sender, instance, **kwargs):
    """
    عملکرد: این سیگنال پس از ثبت یک ApprovalLog اجرا می‌شود. اگر اقدام (action) تأیید (APPROVE) باشد و فاکتور (factor) وجود داشته باشد، فاکتور قفل می‌شود (locked = True).
    """
    if instance.action == 'APPROVE' and instance.factor:
        instance.factor.locked = True
        instance.factor.save()


@receiver(pre_save, sender=Tankhah)
def log_tanbakh_changes(sender, instance, **kwargs):
    """
    عملکرد: این سیگنال قبل از ذخیره تنخواه اجرا می‌شود. اگر وضعیت (status) تنخواه تغییر کند (مثلاً از DRAFT به PAID)، یک رکورد در ApprovalLog ثبت می‌شود که تغییر وضعیت را با کاربر تغییردهنده و توضیحات ثبت می‌کند.
    ارتباط با تنخواه: این سیگنال مستقیماً به تنخواه مربوط است و تغییرات وضعیت آن را رصد می‌کند.
    تأثیر: در TankhahCreateView، تنخواه ابتدا با وضعیت PAID تنظیم می‌شود و سپس به DRAFT تغییر می‌کند. چون تنخواه جدید است (instance.pk وجود ندارد)، این سیگنال در مرحله ثبت اولیه اجرا نمی‌شود. اما اگر بعداً وضعیت تنخواه تغییر کند (مثلاً در جریان کاری تأیید به PAID برسد)، این سیگنال یک ApprovalLog ایجاد می‌کند.
    """
    if instance.pk:
        old_instance = Tankhah.objects.get(pk=instance.pk)
        if old_instance.status != instance.status:
            ApprovalLog.objects.create(
                tanbakh=instance,
                action='STATUS_CHANGE',
                user=instance._changed_by,
                comment=f"تغییر وضعیت از {old_instance.status} به {instance.status}"
            )



# فعال‌سازی سیگنال برای تأیید چندامضایی
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Tankhah, TankhahAction
from core.models import AccessRule, Post

@receiver(post_save, sender=TankhahAction)
def start_approval_process(sender, instance, created, **kwargs):
    if created and instance.action_type == 'ISSUE_PAYMENT_ORDER':
        logger.info(f"Starting approval process for TankhahAction {instance.id}")
        required_posts = AccessRule.objects.filter(
            organization=instance.tankhah.organization,
            stage=instance.stage,
            action_type='SIGN_PAYMENT',
            entity_type='PAYMENTORDER',
            is_active=True
        ).select_related('post')

        if not required_posts.exists():
            logger.warning(f"No approval rules found for TankhahAction {instance.id}")
            return

        for rule in required_posts:
            ActionApproval.objects.create(
                action=instance,
                approver_post=rule.post
            )
            logger.info(f"Created ActionApproval for post {rule.post.name} on TankhahAction {instance.id}")
            # اینجا می‌تونی نوتیفیکیشن به کاربران دارای پست مربوطه بفرستی
            # send_notification_to_post_users(rule.post, instance)