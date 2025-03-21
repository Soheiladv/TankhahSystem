from django.db.models.signals import pre_save
from django.dispatch import receiver

from core.models import Post, PostHistory


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