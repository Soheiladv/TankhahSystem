from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from budgets.models import BudgetAllocation, BudgetTransaction, ProjectBudgetAllocation
from tankhah.models import Tankhah, Factor
from decimal import Decimal
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

@receiver([post_save, post_delete], sender=BudgetAllocation)
def update_total_allocated(sender, instance, **kwargs):
    # آپدیت مجموع تخصیص‌ها در دوره بودجه
    budget_period = instance.budget_period
    # دوره بودجه مرتبط
    total_allocated = BudgetAllocation.objects.filter(budget_period=budget_period).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
    # محاسبه مجموع تخصیص‌ها
    budget_period.total_allocated = total_allocated
    budget_period.save(update_fields=['total_allocated'])
    # ذخیره مجموع تخصیص‌ها

@receiver(post_save, sender=BudgetTransaction)
def update_remaining_amount(sender, instance, created, **kwargs):
    # آپدیت بودجه باقی‌مانده بعد از تراکنش
    allocation = instance.allocation
    # تخصیص مرتبط
    allocation.remaining_amount = allocation.get_remaining_amount()
    allocation.save(update_fields=['remaining_amount'])
    # آپدیت باقی‌مانده تخصیص
    if instance.related_tankhah:
        from budgets.budget_calculations import get_tankhah_remaining_budget
        instance.related_tankhah.remaining_budget = get_tankhah_remaining_budget(instance.related_tankhah)
        instance.related_tankhah.save(update_fields=['remaining_budget'])
        # آپدیت بودجه باقی‌مانده تنخواه

@receiver(post_save, sender=BudgetTransaction)
def update_budget_fields(sender, instance, **kwargs):
    # آپدیت فیلدهای بودجه بعد از تراکنش
    try:
        allocation = instance.allocation
        allocation.remaining_amount = allocation.get_remaining_amount()
        allocation.save(update_fields=['remaining_amount'])
        # آپدیت باقی‌مانده تخصیص
        project_allocation = ProjectBudgetAllocation.objects.filter(budget_allocation=allocation).first()
        if project_allocation:
            project_allocation.remaining_amount = project_allocation.get_remaining_amount()
            project_allocation.save(update_fields=['remaining_amount'])
            # آپدیت باقی‌مانده تخصیص پروژه
        if instance.related_tankhah:
            from budgets.budget_calculations import get_tankhah_remaining_budget
            instance.related_tankhah.remaining_budget = get_tankhah_remaining_budget(instance.related_tankhah)
            instance.related_tankhah.save(update_fields=['remaining_budget'])
            # آپدیت بودجه باقی‌مانده تنخواه
    except Exception as e:
        logger.error(f"Error updating budget fields for BudgetTransaction {instance.id}: {e}", exc_info=True)
        # لاگ خطا

@receiver([post_save, post_delete], sender=BudgetTransaction)
def invalidate_transaction_cache(sender, instance, **kwargs):
    # ابطال کش بعد از تغییر تراکنش
    cache_keys = set()
    try:
        project_allocations = instance.allocation.project_allocations.all()
        for alloc in project_allocations:
            cache_keys.add(f"free_budget_{alloc.pk}")
            if alloc.project:
                cache_keys.add(f"project_remaining_budget_{alloc.project.pk}")
            if alloc.subproject:
                cache_keys.add(f"subproject_remaining_budget_{alloc.subproject.pk}")
        cache_keys.add(f"budget_transfers_{instance.allocation.budget_period.pk}_no_filters")
        cache_keys.add(f"returned_budgets_{instance.allocation.budget_period.pk}_all_no_filters")
        for key in cache_keys:
            cache.delete(key)
        logger.debug(f"Invalidated cache keys after BudgetTransaction change: {cache_keys}")
    except Exception as e:
        logger.error(f"Error invalidating cache for BudgetTransaction {instance.pk}: {str(e)}", exc_info=True)
        # لاگ خطا

@receiver([post_save, post_delete], sender=BudgetAllocation)
def invalidate_allocation_cache(sender, instance, **kwargs):
    # ابطال کش بعد از تغییر تخصیص
    cache_keys = set()
    try:
        cache_keys.add(f"organization_remaining_budget_{instance.organization.pk}")
        cache_keys.add(f"budget_transfers_{instance.budget_period.pk}_no_filters")
        cache_keys.add(f"tankhah_report_{instance.budget_period.pk}_no_filters")
        cache_keys.add(f"invoice_report_{instance.budget_period.pk}_no_filters")
        for key in cache_keys:
            cache.delete(key)
        logger.debug(f"Invalidated cache keys after BudgetAllocation change: {cache_keys}")
    except Exception as e:
        logger.error(f"Error invalidating cache for BudgetAllocation {instance.pk}: {str(e)}", exc_info=True)
        # لاگ خطا

@receiver([post_save, post_delete], sender=ProjectBudgetAllocation)
def invalidate_project_allocation_cache(sender, instance, **kwargs):
    # ابطال کش بعد از تغییر تخصیص پروژه
    cache_keys = set()
    try:
        cache_keys.add(f"free_budget_{instance.pk}")
        if instance.project:
            cache_keys.add(f"project_remaining_budget_{instance.project.pk}")
        if instance.subproject:
            cache_keys.add(f"subproject_remaining_budget_{instance.subproject.pk}")
        cache_keys.add(f"budget_transfers_{instance.budget_allocation.budget_period.pk}_no_filters")
        cache_keys.add(f"tankhah_report_{instance.budget_allocation.budget_period.pk}_no_filters")
        for key in cache_keys:
            cache.delete(key)
        logger.debug(f"Invalidated cache keys after ProjectBudgetAllocation change: {cache_keys}")
    except Exception as e:
        logger.error(f"Error invalidating cache for ProjectBudgetAllocation {instance.pk}: {str(e)}", exc_info=True)
        # لاگ خطا

@receiver([post_save, post_delete], sender=Tankhah)
def invalidate_tankhah_cache(sender, instance, **kwargs):
    # ابطال کش بعد از تغییر تنخواه
    cache_keys = set()
    try:
        cache_keys.add(f"tankhah_report_{instance.allocation.budget_period.pk}_no_filters")
        cache_keys.add(f"free_budget_{instance.project_allocation.pk}")
        for key in cache_keys:
            cache.delete(key)
        logger.debug(f"Invalidated cache keys after Tankhah change: {cache_keys}")
    except Exception as e:
        logger.error(f"Error invalidating cache for Tankhah {instance.pk}: {str(e)}", exc_info=True)
        # لاگ خطا

# @receiver([post_save, post_delete], sender=Factor)
# def invalidate_invoice_cache(sender, instance, **kwargs):
#     # ابطال کش بعد از تغییر فاکتور
#     cache_keys = set()
#     try:
#         cache_keys.add(f"invoice_report_{instance.transaction.allocation.budget_period.pk}_no_filters")
#         for key in cache_keys:
#             cache.delete(key)
#         logger.debug(f"Invalidated cache keys after Invoice change: {cache_keys}")
#     except Exception as e:
#         logger.error(f"Error invalidating cache for Invoice {instance.pk}: {str(e)}", exc_info=True)
#         # لاگ خطا

@receiver(post_save, sender=BudgetAllocation)
def update_allocation_lock_status(sender, instance, **kwargs):
    # آپدیت وضعیت قفل تخصیص بعد از ذخیره
    try:
        instance.check_and_update_lock()
        logger.info(f"Updated lock status for BudgetAllocation {instance.pk}")
    except Exception as e:
        logger.error(f"Error updating lock status for BudgetAllocation {instance.pk}: {str(e)}")
        # لاگ خطا

@receiver(post_save, sender=BudgetTransaction)
def update_allocation_lock_on_transaction(sender, instance, **kwargs):
    # آپدیت وضعیت قفل تخصیص بعد از تراکنش
    try:
        allocation = instance.allocation
        allocation.check_and_update_lock()
        logger.info(f"Updated lock status for BudgetAllocation {allocation.pk} after BudgetTransaction {instance.pk}")
    except Exception as e:
        logger.error(f"Error updating lock status for BudgetAllocation {instance.allocation.pk}: {str(e)}")
        # لاگ خطا