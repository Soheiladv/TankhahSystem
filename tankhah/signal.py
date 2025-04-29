from django.db.models.signals import post_save
from django.dispatch import receiver

from tankhah.models import Tankhah, Notification


@receiver(post_save, sender=Tankhah)
def send_tankhah_notification(sender, instance, created, **kwargs):
    if instance.status == 'PAID':
        Notification.objects.create(
            user=instance.created_by,
            message=f"تنخواه {instance.number} پرداخت شد.",
            tankhah=instance
        )