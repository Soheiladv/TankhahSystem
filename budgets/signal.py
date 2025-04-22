from decimal import Decimal
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from budgets.models import BudgetAllocation
from django.db.models.signals import post_save
from django.dispatch import receiver
from budgets.models import ProjectBudgetAllocation, BudgetTransaction
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)



@receiver([post_save, post_delete], sender=BudgetAllocation)
def update_total_allocated(sender, instance, **kwargs):
    """به‌روزرسانی total_allocated در BudgetPeriod"""
    budget_period = instance.budget_period
    total_allocated = BudgetAllocation.objects.filter(
        budget_period=budget_period
    ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
    budget_period.total_allocated = total_allocated
    budget_period.save(update_fields=['total_allocated'])



@receiver(post_save, sender=ProjectBudgetAllocation)
def create_budget_transaction(sender, instance, created, **kwargs):
    """ایجاد تراکنش مصرف بودجه هنگام ذخیره تخصیص پروژه"""
    if created:  # فقط برای تخصیص‌های جدید
        try:
            BudgetTransaction.objects.create(
                allocation=instance.budget_allocation,
                transaction_type='CONSUMPTION',
                amount=instance.allocated_amount,
                created_by=instance.created_by,
                description=f"تخصیص بودجه پروژه {instance.pk} برای {instance.project.name}",
                transaction_id=f"TX-PBA-{instance.pk}"
            )
            logger.info(f"BudgetTransaction created for ProjectBudgetAllocation {instance.pk}")
        except Exception as e:
            logger.error(f"Error creating BudgetTransaction for ProjectBudgetAllocation {instance.pk}: {str(e)}")
            raise