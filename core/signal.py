# core/signals.py
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from core.models import Post, PostHistory, PostAction
from tankhah.models import Factor, FactorItem, Tankhah
from budgets.models import BudgetTransaction, BudgetAllocation, PaymentOrder

logger = logging.getLogger(__name__)

# ----------------------------
# سیگنال برای ثبت تاریخچه تغییرات Post
# ----------------------------
@receiver(post_save, sender=Post)
def log_post_changes(sender, instance, created, **kwargs):
    """
    وقتی یک Post ساخته یا بروزرسانی می‌شود،
    تغییرات فیلدهای name, parent, branch را در PostHistory ثبت می‌کند.
    """
    user = getattr(instance, '_current_user', None)

    if not created:  # فقط زمانی که پست موجود است
        try:
            old_instance = Post.objects.get(pk=instance.pk)
        except Post.DoesNotExist:
            return

        fields_to_check = ['name', 'parent', 'branch']
        for field in fields_to_check:
            old_value = getattr(old_instance, field, None)
            new_value = getattr(instance, field, None)
            if old_value != new_value:
                PostHistory.objects.create(
                    post=instance,
                    changed_field=field,
                    old_value=str(old_value) if old_value else '',
                    new_value=str(new_value) if new_value else '',
                    changed_by=user
                )

# ----------------------------
# سیگنال برای مدیریت بودجه و تنخواه هنگام تغییر وضعیت Tankhah
# ----------------------------
@receiver(post_save, sender=Tankhah)
def handle_tankhah_status_change(sender, instance, **kwargs):
    """
    وقتی وضعیت Tankhah به 'PAID' تغییر کرد، تراکنش بودجه ایجاد می‌شود.
    """
    if instance.status == 'PAID' and instance.budget_allocation:
        allocation = BudgetAllocation.objects.filter(
            budget_allocation=instance.budget_allocation,
            project=instance.project,
            subproject=instance.subproject if instance.subproject else None
        ).first()

        if allocation:
            BudgetTransaction.objects.create(
                allocation=instance.budget_allocation,
                transaction_type='CONSUMPTION',
                amount=instance.amount,
                description=f"هزینه کرد برای تنخواه {instance.number}",
                created_by=instance.created_by
            )
            logger.info(f"Created CONSUMPTION transaction for Tankhah {instance.number}, amount={instance.amount}")

# ----------------------------
# سیگنال برای ایجاد PostAction هنگام ایجاد Post جدید
# ----------------------------
@receiver(post_save, sender=Post)
def create_post_actions_for_post(sender, instance, created, **kwargs):
    """
    وقتی یک Post جدید ایجاد می‌شود، PostActionهای مربوط به آن براساس پست و سطح آن پر می‌شوند.
    """
    if created or kwargs.get('update_fields') is None:
        # تمام entity typeها
        entity_types = {
            'FACTORITEM': ContentType.objects.get_for_model(FactorItem).model.upper(),
            'FACTOR': ContentType.objects.get_for_model(Factor).model.upper(),
            'TANKHAH': ContentType.objects.get_for_model(Tankhah).model.upper(),
            'PAYMENTORDER': ContentType.objects.get_for_model(PaymentOrder).model.upper(),
        }

        # برای هر entity type، یک PostAction فعال ایجاد می‌کنیم
        for entity_type_name, entity_type in entity_types.items():
            PostAction.objects.get_or_create(
                post=instance,
                entity_type=entity_type,
                action_type='DEFAULT',  # نوع عمل پیش‌فرض، بسته به سیستم می‌تواند تغییر کند
                is_active=True
            )

# ----------------------------
# سیگنال برای ایجاد PostAction هنگام ایجاد Facto/Stage جدید
# ----------------------------
@receiver(post_save, sender=Factor)
def create_post_actions_for_factor(sender, instance, created, **kwargs):
    """
    وقتی فاکتور جدید ایجاد می‌شود، PostActionهای مربوط به پست‌ها پر شوند.
    """
    if created:
        posts = Post.objects.filter(is_active=True)
        entity_type = ContentType.objects.get_for_model(Factor).model.upper()

        for post in posts:
            PostAction.objects.get_or_create(
                post=post,
                entity_type=entity_type,
                action_type='DEFAULT',
                is_active=True
            )
