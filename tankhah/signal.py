from decimal import Decimal

from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from tankhah.models import Tankhah, FactorItem, create_budget_transaction
import logging
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

