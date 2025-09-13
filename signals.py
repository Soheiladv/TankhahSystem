from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import CustomUser
from budgets.models import BudgetAllocation, BudgetTransaction, PaymentOrder, Payee
from core.models import Post, AccessRule
from tankhah.models import Tankhah, Factor, ApprovalLog
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
    # آپدیت کش‌های مرتبط بعد از تراکنش
    allocation = instance.allocation
    logger.debug(f"BudgetTransaction {instance.transaction_id} created. Invalidating cache for allocation {allocation.id}")
    # پاک کردن کش‌های مرتبط
    cache.delete(f"allocation_remaining_{allocation.id}")
    if instance.related_tankhah:
        from budgets.budget_calculations import get_tankhah_remaining_budget
        instance.related_tankhah.remaining_budget = get_tankhah_remaining_budget(instance.related_tankhah)
        instance.related_tankhah.save(update_fields=['remaining_budget'])
        cache.delete(f"tankhah_remaining_{instance.related_tankhah.id}")
        logger.debug(f"Updated remaining_budget for Tankhah {instance.related_tankhah.id}")

@receiver(post_save, sender=BudgetTransaction)
def update_budget_fields(sender, instance, **kwargs):
    # آپدیت کش‌های مرتبط بعد از تراکنش
    try:
        allocation = instance.allocation
        logger.debug(f"Invalidating cache for BudgetAllocation {allocation.id}")
        cache.delete(f"allocation_remaining_{allocation.id}")

        project_allocation = BudgetAllocation.objects.filter(budget_allocation=allocation).first()
        if project_allocation:
            logger.debug(f"Invalidating cache for ProjectBudgetAllocation {project_allocation.id}")
            cache.delete(f"project_allocation_remaining_{project_allocation.id}")

        if instance.related_tankhah:
            from budgets.budget_calculations import get_tankhah_remaining_budget
            instance.related_tankhah.remaining_budget = get_tankhah_remaining_budget(instance.related_tankhah)
            instance.related_tankhah.save(update_fields=['remaining_budget'])
            cache.delete(f"tankhah_remaining_{instance.related_tankhah.id}")
            logger.debug(f"Updated remaining_budget for Tankhah {instance.related_tankhah.id}")
    except Exception as e:
        logger.error(f"Error updating caches for BudgetTransaction {instance.id}: {e}", exc_info=True)

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

@receiver([post_save, post_delete], sender=BudgetAllocation)
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

#==
"""وقتی یک ApprovalLog برای فاکتور یا تنخواه ثبت می‌شه و مرحله به یکی با triggers_payment_order=True می‌رسه، یک PaymentOrder ایجاد می‌شه:"""
@receiver(post_save, sender=ApprovalLog)
def create_payment_order_on_approval(sender, instance, created, **kwargs):
    if created and instance.action == 'APPROVED':
        try:
            logger.info(f"[create_payment_order_on_approval] Processing ApprovalLog {instance.id}")
            
            content_type = instance.content_type
            if content_type.model != 'factor':
                logger.debug(f"[create_payment_order_on_approval] Content type is {content_type.model}, skipping")
                return

            factor = Factor.objects.get(id=instance.object_id)
            tankhah = factor.tankhah
            
            # بررسی اینکه فاکتور تایید نهایی شده باشد
            if not factor.status or not factor.status.is_final_approve:
                logger.debug(f"[create_payment_order_on_approval] Factor {factor.id} is not final approved, skipping")
                return

            # بررسی اینکه قبلاً دستور پرداخت ایجاد نشده باشد
            if PaymentOrder.objects.filter(related_factors=factor).exists():
                logger.info(f"[create_payment_order_on_approval] PaymentOrder already exists for Factor {factor.id}")
                return

            amount = factor.amount
            user_post = instance.user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
            if not user_post:
                logger.warning(f"[create_payment_order_on_approval] No active user post found for user {instance.user.username}")
                return

            from core.models import Status
            initial_po_status = Status.objects.filter(
                entity_type__code='PAYMENTORDER', 
                is_initial=True
            ).first()

            if not initial_po_status:
                logger.error(f"[create_payment_order_on_approval] No initial status found for PAYMENTORDER")
                return

            # ایجاد دستور پرداخت
            payment_order = PaymentOrder.objects.create(
                tankhah=tankhah,
                related_tankhah=tankhah,
                amount=amount,
                payee=None,  # باید بعداً تنظیم شود
                description=f"دستور پرداخت برای فاکتور {factor.number} (تنخواه: {tankhah.number})",
                organization=tankhah.organization,
                project=tankhah.project,
                status=initial_po_status,
                created_by=instance.user,
                created_by_post=user_post.post,
                issue_date=timezone.now().date(),
                min_signatures=1
            )
            payment_order.related_factors.add(factor)
            logger.info(f"[create_payment_order_on_approval] Created PaymentOrder {payment_order.order_number} for Factor {factor.id}")

            # ارسال اعلان
            from notificationApp.utils import send_notification
            send_notification(
                sender=instance.user,
                users=[factor.created_by],
                verb='PAYMENTORDER_CREATED',
                description=f"دستور پرداخت {payment_order.order_number} برای فاکتور {factor.number} ایجاد شد.",
                target=payment_order,
                entity_type='PAYMENTORDER',
                priority='HIGH'
            )
        except Exception as e:
            logger.error(f"[create_payment_order_on_approval] Error for ApprovalLog {instance.id}: {str(e)}", exc_info=True)

"""تعریف PostAction برای امضای دستور پرداخت
برای اینکه پست‌های خاصی بتونن دستور پرداخت رو امضا کنن، باید PostAction رو برای موجودیت paymentorder تعریف کنیم:"""
@receiver(post_save, sender=Post)
def create_post_actions_for_payment_order(sender, instance, created, **kwargs):
    """فقط پست‌هایی که is_payment_order_signer=True دارن، می‌تونن دستور پرداخت رو امضا کنن.
        این برای مراحل با triggers_payment_order=True اعمال می‌شه."""
    if created and instance.is_payment_order_signer:
        from core.models import PostAction,WorkflowStage
        stages = WorkflowStage.objects.filter(is_active=True, triggers_payment_order=True)
        content_type = ContentType.objects.get_for_model(PaymentOrder)
        for stage in stages:
            PostAction.objects.get_or_create(
                post=instance,
                stage=stage,
                action_type='APPROVE',  # برای امضا
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
