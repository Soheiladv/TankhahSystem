from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from tankhah.models import Tankhah
from core.models import Post, PostHistory, AccessRule
from tankhah.models import Factor, ApprovalLog
import logging
logger = logging.getLogger(__name__)

# tankhah/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from tankhah.models import Tankhah
from budgets.models import BudgetTransaction,   PaymentOrder, BudgetAllocation
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import   WorkflowStage
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Post, WorkflowStage, PostAction
from django.contrib.contenttypes.models import ContentType
from tankhah.models import FactorItem, Factor, Tankhah


# @receiver(pre_save, sender=Post)
# def log_post_changes(sender, instance, **kwargs):
#     """عملکرد: این سیگنال قبل از ذخیره تغییرات در مدل Post اجرا می‌شود. اگر فیلدهای name, parent, یا branch تغییر کنند، این تغییرات در مدل PostHistory ثبت می‌شوند."""
#     if instance.pk:  # اگه پست قبلاً وجود داشته
#         old_instance = Post.objects.get(pk=instance.pk)
#         fields_to_check = ['name', 'parent', 'branch']  # فیلدهایی که می‌خواید چک بشن
#         for field in fields_to_check:
#             old_value = str(getattr(old_instance, field, None))
#             new_value = str(getattr(instance, field, None))
#             if old_value != new_value:
#                 PostHistory.objects.create(
#                     post=instance,
#                     changed_field=field,
#                     old_value=old_value,
#                     new_value=new_value,
#                     changed_by=instance._current_user if hasattr(instance, '_current_user') else None
#                 )
@receiver(post_save, sender=Tankhah)
def handle_tankhah_status_change(sender, instance, **kwargs):
    if instance.status == 'PAID' and instance.budget_allocation:
        project_allocation = BudgetAllocation.objects.filter(
            budget_allocation=instance.budget_allocation,
            project=instance.project,
            subproject=instance.subproject if instance.subproject else None
        ).first()
        if project_allocation:
            BudgetTransaction.objects.create(
                allocation=instance.budget_allocation,
                transaction_type='CONSUMPTION',
                amount=instance.amount,
                description=f"هزینه کرد برای تنخواه {instance.number}",
                created_by=instance.created_by
            )
            logger.info(f"Created CONSUMPTION transaction for tankhah {instance.number}, amount={instance.amount}")

"""این کد وقتی پست یا مرحله جدید ایجاد می‌شه، PostAction رو بر اساس قوانین مشخص پر می‌کنه:"""
@receiver(post_save, sender=Post)
def create_post_actions_for_post(sender, instance, created, **kwargs):
    if created or kwargs.get('update_fields') is None:
        stages = AccessRule.objects.filter(is_active=True)
        entity_types = {
            'FACTORITEM': ContentType.objects.get_for_model(FactorItem).model.upper(),
            'FACTOR': ContentType.objects.get_for_model(Factor).model.upper(),
            'TANKHAH': ContentType.objects.get_for_model(Tankhah).model.upper(),
            'PAYMENTORDER': ContentType.objects.get_for_model(PaymentOrder).model.upper(),
        }

        for stage in stages:
            for entity_type_key, entity_type in entity_types.items():
                rules = AccessRule.objects.filter(
                    organization=instance.organization,
                    stage=stage,
                    entity_type=entity_type,
                    is_active=True
                ).filter(
                    models.Q(branch=instance.branch.code if instance.branch else '', min_level__lte=instance.level) |
                    models.Q(is_payment_order_signer=True, entity_type='PAYMENTORDER')
                )

                for rule in rules:
                    if rule.is_payment_order_signer and not instance.is_payment_order_signer:
                        continue
                    PostAction.objects.get_or_create(
                        post=instance,
                        stage=stage,
                        action_type=rule.action_type,
                        entity_type=entity_type,
                        is_active=True
                    )

@receiver(post_save, sender=WorkflowStage)
def create_post_actions_for_stage(sender, instance, created, **kwargs):
    if created:
        posts = Post.objects.filter(is_active=True)
        entity_types = {
            'FACTORITEM': ContentType.objects.get_for_model(FactorItem).model.upper(),
            'FACTOR': ContentType.objects.get_for_model(Factor).model.upper(),
            'TANKHAH': ContentType.objects.get_for_model(Tankhah).model.upper(),
            'PAYMENTORDER': ContentType.objects.get_for_model(PaymentOrder).model.upper(),
        }

        for post in posts:
            for entity_type_key, entity_type in entity_types.items():
                rules = AccessRule.objects.filter(
                    organization=post.organization,
                    stage=instance,
                    entity_type=entity_type,
                    is_active=True
                ).filter(
                    models.Q(branch=post.branch, min_level__lte=post.level) |
                    models.Q(is_payment_order_signer=True, entity_type='PAYMENTORDER')
                )

                for rule in rules:
                    if rule.is_payment_order_signer and not post.is_payment_order_signer:
                        continue
                    PostAction.objects.get_or_create(
                        post=post,
                        stage=instance,
                        action_type=rule.action_type,
                        entity_type=entity_type,
                        is_active=True
                    )

