from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from core.models import Post, PostHistory
from tanbakh.models import Factor, ApprovalLog, Tanbakh
import logging
logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Post)
def log_post_changes(sender, instance, **kwargs):
    if instance.pk:  # اگه پست قبلاً وجود داشته
        old_instance = Post.objects.get(pk=instance.pk)
        fields_to_check = ['name', 'parent', 'branch']  # فیلدهایی که می‌خواید چک بشن
        for field in fields_to_check:
            old_value = str(getattr(old_instance, field, None))
            new_value = str(getattr(instance, field, None))
            if old_value != new_value:
                PostHistory.objects.create(
                    post=instance,
                    changed_field=field,
                    old_value=old_value,
                    new_value=new_value,
                    changed_by=instance._current_user if hasattr(instance, '_current_user') else None
                )



@receiver(post_save, sender=Factor)
def log_factor_changes(sender, instance, created, **kwargs):
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
                logger.info(f"تغییر در فاکتور {instance.number}: {field_name} از {old_value} به {new_value} توسط {user or 'ناشناس'}")


@receiver(post_save, sender=ApprovalLog)
def lock_factor_after_approval(sender, instance, **kwargs):
    if instance.action == 'APPROVE' and instance.factor:
        instance.factor.locked = True
        instance.factor.save()

@receiver(pre_save, sender=Tanbakh)
def log_tanbakh_changes(sender, instance, **kwargs):
    if instance.pk:
        old_instance = Tanbakh.objects.get(pk=instance.pk)
        if old_instance.status != instance.status:
            ApprovalLog.objects.create(
                tanbakh=instance,
                action='STATUS_CHANGE',
                user=instance._changed_by,
                comment=f"تغییر وضعیت از {old_instance.status} به {instance.status}"
            )