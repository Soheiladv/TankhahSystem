from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from budgets.models import BudgetAllocation, BudgetTransaction, BudgetPeriod, PaymentOrder
from core.models import Post
from tankhah.models import Tankhah, Factor, ApprovalLog
from decimal import Decimal
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

@receiver([post_save, post_delete], sender=BudgetAllocation)
def update_total_allocated(sender, instance, **kwargs):
    if kwargs.get('raw', False):  # نادیده گرفتن در فیکسچرها
        return
    try:
        budget_period = instance.budget_period
        total_allocated = BudgetAllocation.objects.filter(budget_period=budget_period).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
        BudgetPeriod.objects.filter(pk=budget_period.pk).update(total_allocated=total_allocated)
        logger.debug(f"Updated total_allocated={total_allocated} for BudgetPeriod {budget_period.pk}")
    except Exception as e:
        logger.error(f"Error in update_total_allocated for BudgetAllocation {instance.pk}: {str(e)}", exc_info=True)

@receiver(post_save, sender=BudgetTransaction)
def update_remaining_amount(sender, instance, created, **kwargs):
    try:
        allocation = instance.allocation
        logger.debug(f"BudgetTransaction {instance.transaction_id} created. Invalidating cache for allocation {allocation.id}")
        cache.delete(f"allocation_remaining_{allocation.id}")
        if instance.related_tankhah:
            instance.related_tankhah.remaining_budget = instance.related_tankhah.get_remaining_budget()
            instance.related_tankhah.save(update_fields=['remaining_budget'])
            cache.delete(f"tankhah_remaining_{instance.related_tankhah.id}")
            logger.debug(f"Updated remaining_budget for Tankhah {instance.related_tankhah.id}")
    except Exception as e:
        logger.error(f"Error updating caches for BudgetTransaction {instance.id}: {str(e)}", exc_info=True)

@receiver([post_save, post_delete], sender=BudgetTransaction)
def invalidate_transaction_cache(sender, instance, **kwargs):
    cache_keys = set()
    try:
        allocation = instance.allocation
        cache_keys.add(f"free_budget_{allocation.pk}")
        if allocation.project:
            cache_keys.add(f"project_remaining_budget_{allocation.project.pk}")
        if allocation.subproject:
            cache_keys.add(f"subproject_remaining_budget_{allocation.subproject.pk}")
        cache_keys.add(f"budget_transfers_{allocation.budget_period.pk}_no_filters")
        cache_keys.add(f"returned_budgets_{allocation.budget_period.pk}_all_no_filters")
        for key in cache_keys:
            cache.delete(key)
        logger.debug(f"Invalidated cache keys after BudgetTransaction change: {cache_keys}")
    except Exception as e:
        logger.error(f"Error invalidating cache for BudgetTransaction {instance.pk}: {str(e)}", exc_info=True)

@receiver([post_save, post_delete], sender=BudgetAllocation)
def invalidate_allocation_cache(sender, instance, **kwargs):
    cache_keys = set()
    try:
        cache_keys.add(f"free_budget_{instance.pk}")
        if instance.project:
            cache_keys.add(f"project_remaining_budget_{instance.project.pk}")
        if instance.subproject:
            cache_keys.add(f"subproject_remaining_budget_{instance.subproject.pk}")
        cache_keys.add(f"budget_transfers_{instance.budget_period.pk}_no_filters")
        cache_keys.add(f"tankhah_report_{instance.budget_period.pk}_no_filters")
        for key in cache_keys:
            cache.delete(key)
        logger.debug(f"Invalidated cache keys after BudgetAllocation change: {cache_keys}")
    except Exception as e:
        logger.error(f"Error invalidating cache for BudgetAllocation {instance.pk}: {str(e)}", exc_info=True)

@receiver([post_save, post_delete], sender=Tankhah)
def invalidate_tankhah_cache(sender, instance, **kwargs):
    cache_keys = set()
    try:
        if instance.project_budget_allocation:
            cache_keys.add(f"tankhah_report_{instance.project_budget_allocation.budget_period.pk}_no_filters")
            cache_keys.add(f"free_budget_{instance.project_budget_allocation.pk}")
        for key in cache_keys:
            cache.delete(key)
        logger.debug(f"Invalidated cache keys after Tankhah change: {cache_keys}")
    except Exception as e:
        logger.error(f"Error invalidating cache for Tankhah {instance.pk}: {str(e)}", exc_info=True)

@receiver(post_save, sender=ApprovalLog)
def create_payment_order_on_approval(sender, instance, created, **kwargs):
    if created and instance.action == 'APPROVE':
        stage = instance.stage
        if stage.triggers_payment_order:
            content_type = instance.content_type
            if content_type.model == 'factor':
                factor = Factor.objects.get(id=instance.object_id)
                tankhah = factor.tankhah
                if factor.status == 'APPROVED':
                    amount = sum(item.amount for item in factor.items.filter(status='APPROVE'))
                    user_post = instance.user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
                    if user_post:
                        payment_order = PaymentOrder.objects.create(
                            tankhah=tankhah,
                            amount=amount,
                            payee=None,
                            description=f"دستور پرداخت برای فاکتور {factor.id}",
                            created_by=instance.user,
                            created_by_post=user_post.post,
                            status='DRAFT',
                            min_signatures=1
                        )
                        payment_order.related_factors.add(factor)
                        logger.info(f"Created PaymentOrder for Factor {factor.id}")

@receiver(post_save, sender=Post)
def create_post_actions_for_payment_order(sender, instance, created, **kwargs):
    if created and instance.is_payment_order_signer:
        from core.models import PostAction, WorkflowStage
        stages = WorkflowStage.objects.filter(is_active=True, triggers_payment_order=True)
        content_type = ContentType.objects.get_for_model(PaymentOrder)
        for stage in stages:
            PostAction.objects.get_or_create(
                post=instance,
                stage=stage,
                action_type='APPROVE',
                entity_type=content_type.model.upper(),
                is_active=True
            )
            PostAction.objects.get_or_create(
                post=instance,
                stage=stage,
                action_type='REJECT',
                entity_type=content_type.model.upper(),
                is_active=True
            )
            logger.debug(f"Created PostActions for Post {instance.pk} and stage {stage.pk}")

# from django.contrib.contenttypes.models import ContentType
# from django.db.models import Sum
# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from budgets.models import BudgetAllocation, BudgetTransaction, PaymentOrder, BudgetPeriod
# from core.models import Post
# from tankhah.models import Tankhah, Factor
# from decimal import Decimal
# from django.core.cache import cache
# import logging
#
# logger = logging.getLogger(__name__)
#
# @receiver([post_save, post_delete], sender=BudgetAllocation)
# def update_total_allocated(sender, instance, **kwargs):
#     if kwargs.get('raw', False):  # نادیده گرفتن در فیکسچرها
#         return
#     try:
#         budget_period = instance.budget_period
#         total_allocated = BudgetAllocation.objects.filter(budget_period=budget_period).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
#         BudgetPeriod.objects.filter(pk=budget_period.pk).update(total_allocated=total_allocated)
#         logger.debug(f"Updated total_allocated={total_allocated} for BudgetPeriod {budget_period.pk}")
#     except Exception as e:
#         logger.error(f"Error in update_total_allocated for BudgetAllocation {instance.pk}: {str(e)}", exc_info=True)
#
#
# @receiver(post_save, sender=BudgetTransaction)
# def update_remaining_amount(sender, instance, created, **kwargs):
#     try:
#         allocation = instance.allocation
#         logger.debug(f"BudgetTransaction {instance.transaction_id} created. Invalidating cache for allocation {allocation.id}")
#         cache.delete(f"allocation_remaining_{allocation.id}")
#         if instance.related_tankhah:
#             instance.related_tankhah.remaining_budget = instance.related_tankhah.get_remaining_budget()
#             instance.related_tankhah.save(update_fields=['remaining_budget'])
#             cache.delete(f"tankhah_remaining_{instance.related_tankhah.id}")
#             logger.debug(f"Updated remaining_budget for Tankhah {instance.related_tankhah.id}")
#     except Exception as e:
#         logger.error(f"Error updating caches for BudgetTransaction {instance.id}: {str(e)}", exc_info=True)
#
#
# @receiver(post_save, sender=BudgetTransaction)
# def update_budget_fields(sender, instance, **kwargs):
#     try:
#         allocation = instance.allocation
#         logger.debug(f"Invalidating cache for BudgetAllocation {allocation.id}")
#         cache.delete(f"allocation_remaining_{allocation.id}")
#
#         if instance.related_tankhah:
#             from budgets.budget_calculations import get_tankhah_remaining_budget
#             instance.related_tankhah.remaining_budget = get_tankhah_remaining_budget(instance.related_tankhah)
#             instance.related_tankhah.save(update_fields=['remaining_budget'])
#             cache.delete(f"tankhah_remaining_{instance.related_tankhah.id}")
#             logger.debug(f"Updated remaining_budget for Tankhah {instance.related_tankhah.id}")
#     except Exception as e:
#         logger.error(f"Error updating caches for BudgetTransaction {instance.id}: {e}", exc_info=True)
#
# @receiver([post_save, post_delete], sender=BudgetTransaction)
# def invalidate_transaction_cache(sender, instance, **kwargs):
#     cache_keys = set()
#     try:
#         allocation = instance.allocation
#         cache_keys.add(f"free_budget_{allocation.pk}")
#         if allocation.project:
#             cache_keys.add(f"project_remaining_budget_{allocation.project.pk}")
#         if allocation.subproject:
#             cache_keys.add(f"subproject_remaining_budget_{allocation.subproject.pk}")
#         cache_keys.add(f"budget_transfers_{allocation.budget_period.pk}_no_filters")
#         cache_keys.add(f"returned_budgets_{allocation.budget_period.pk}_all_no_filters")
#         for key in cache_keys:
#             cache.delete(key)
#         logger.debug(f"Invalidated cache keys after BudgetTransaction change: {cache_keys}")
#     except Exception as e:
#         logger.error(f"Error invalidating cache for BudgetTransaction {instance.pk}: {str(e)}", exc_info=True)
#
#
# @receiver([post_save, post_delete], sender=BudgetAllocation)
# def invalidate_allocation_cache(sender, instance, **kwargs):
#     cache_keys = set()
#     try:
#         cache_keys.add(f"free_budget_{instance.pk}")
#         if instance.project:
#             cache_keys.add(f"project_remaining_budget_{instance.project.pk}")
#         if instance.subproject:
#             cache_keys.add(f"subproject_remaining_budget_{instance.subproject.pk}")
#         cache_keys.add(f"budget_transfers_{instance.budget_period.pk}_no_filters")
#         cache_keys.add(f"tankhah_report_{instance.budget_period.pk}_no_filters")
#         for key in cache_keys:
#             cache.delete(key)
#         logger.debug(f"Invalidated cache keys after BudgetAllocation change: {cache_keys}")
#     except Exception as e:
#         logger.error(f"Error invalidating cache for BudgetAllocation {instance.pk}: {str(e)}", exc_info=True)
#
#
# @receiver([post_save, post_delete], sender=BudgetAllocation)
# def invalidate_project_allocation_cache(sender, instance, **kwargs):
#     cache_keys = set()
#     try:
#         cache_keys.add(f"free_budget_{instance.pk}")
#         if instance.project:
#             cache_keys.add(f"project_remaining_budget_{instance.project.pk}")
#         if instance.subproject:
#             cache_keys.add(f"subproject_remaining_budget_{instance.subproject.pk}")
#         cache_keys.add(f"budget_transfers_{instance.budget_allocation.budget_period.pk}_no_filters")
#         cache_keys.add(f"tankhah_report_{instance.budget_allocation.budget_period.pk}_no_filters")
#         for key in cache_keys:
#             cache.delete(key)
#         logger.debug(f"Invalidated cache keys after ProjectBudgetAllocation change: {cache_keys}")
#     except Exception as e:
#         logger.error(f"Error invalidating cache for ProjectBudgetAllocation {instance.pk}: {str(e)}", exc_info=True)
#
# @receiver([post_save, post_delete], sender=Tankhah)
# def invalidate_tankhah_cache(sender, instance, **kwargs):
#     cache_keys = set()
#     try:
#         if instance.project_budget_allocation:
#             cache_keys.add(f"tankhah_report_{instance.project_budget_allocation.budget_period.pk}_no_filters")
#             cache_keys.add(f"free_budget_{instance.project_budget_allocation.pk}")
#         for key in cache_keys:
#             cache.delete(key)
#         logger.debug(f"Invalidated cache keys after Tankhah change: {cache_keys}")
#     except Exception as e:
#         logger.error(f"Error invalidating cache for Tankhah {instance.pk}: {str(e)}", exc_info=True)
#
#
# @receiver(post_save, sender=BudgetAllocation)
# def update_allocation_lock_status(sender, instance, **kwargs):
#     # آپدیت وضعیت قفل تخصیص بعد از ذخیره
#     try:
#         instance.check_and_update_lock()
#         logger.info(f"Updated lock status for BudgetAllocation {instance.pk}")
#     except Exception as e:
#         logger.error(f"Error updating lock status for BudgetAllocation {instance.pk}: {str(e)}")
#         # لاگ خطا
#
# @receiver(post_save, sender=BudgetTransaction)
# def update_allocation_lock_on_transaction(sender, instance, **kwargs):
#     # آپدیت وضعیت قفل تخصیص بعد از تراکنش
#     try:
#         allocation = instance.allocation
#         allocation.check_and_update_lock()
#         logger.info(f"Updated lock status for BudgetAllocation {allocation.pk} after BudgetTransaction {instance.pk}")
#     except Exception as e:
#         logger.error(f"Error updating lock status for BudgetAllocation {instance.allocation.pk}: {str(e)}")
#         # لاگ خطا
#
# #==
# """وقتی یک ApprovalLog برای فاکتور یا تنخواه ثبت می‌شه و مرحله به یکی با triggers_payment_order=True می‌رسه، یک PaymentOrder ایجاد می‌شه:"""
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from tankhah.models import ApprovalLog,  Factor
# from decimal import Decimal
#
# @receiver(post_save, sender=ApprovalLog)
# def create_payment_order_on_approval(sender, instance, created, **kwargs):
#     if created and instance.action == 'APPROVE':
#         stage = instance.stage
#         if stage.triggers_payment_order:
#             content_type = instance.content_type
#             if content_type.model == 'factor':
#                 factor = Factor.objects.get(id=instance.object_id)
#                 tankhah = factor.tankhah
#                 if factor.status == 'APPROVED':
#                     amount = sum(item.amount for item in factor.items.filter(status='APPROVE'))
#                     user_post = instance.user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
#                     if user_post:
#                         payment_order = PaymentOrder.objects.create(
#                             tankhah=tankhah,
#                             amount=amount,
#                             payee=None,  # باید مشخص شود
#                             description=f"دستور پرداخت برای فاکتور {factor.id}",
#                             created_by=instance.user,
#                             created_by_post=user_post.post,
#                             status='DRAFT',
#                             min_signatures=1
#                         )
#                         payment_order.related_factors.add(factor)
#                         logger.info(f"Created PaymentOrder for Factor {factor.id}")
#
#
# """تعریف PostAction برای امضای دستور پرداخت
# برای اینکه پست‌های خاصی بتونن دستور پرداخت رو امضا کنن، باید PostAction رو برای موجودیت paymentorder تعریف کنیم:"""
# @receiver(post_save, sender=Post)
# def create_post_actions_for_payment_order(sender, instance, created, **kwargs):
#     """فقط پست‌هایی که is_payment_order_signer=True دارن، می‌تونن دستور پرداخت رو امضا کنن.
#         این برای مراحل با triggers_payment_order=True اعمال می‌شه."""
#     if created and instance.is_payment_order_signer:
#         from core.models import PostAction, WorkflowStage
#         stages = WorkflowStage.objects.filter(is_active=True, triggers_payment_order=True)
#         content_type = ContentType.objects.get_for_model(PaymentOrder)
#         for stage in stages:
#             PostAction.objects.get_or_create(
#                 post=instance,
#                 stage=stage,
#                 action_type='APPROVE',
#                 entity_type=content_type.model.upper(),
#                 is_active=True
#             )
#             PostAction.objects.get_or_create(
#                 post=instance,
#                 stage=stage,
#                 action_type='REJECT',
#                 entity_type=content_type.model.upper(),
#                 is_active=True
#             )
#             logger.debug(f"Created PostActions for Post {instance.pk} and stage {stage.pk}")