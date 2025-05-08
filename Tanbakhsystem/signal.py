
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from notifications.signals import notify
from tankhah.models import Tankhah, Factor
from budgets.models import BudgetTransaction
from django.contrib.auth import get_user_model

User = get_user_model()

# 1. ثبت تنخواه
@receiver(post_save, sender=Tankhah)
def notify_tankhah_creation(sender, instance, created, **kwargs):
    if created:
        # فرض می‌کنیم شعبه (organization) تنخواه را ثبت کرده و باید به کاربران شعبه اطلاع داده شود
        organization = instance.organization
        users_in_org = User.objects.filter(userpost__post__organization=organization, userpost__is_active=True)
        for user in users_in_org:
            notify.send(
                sender=instance.created_by,  # کاربری که تنخواه را ایجاد کرده
                recipient=user,  # کاربران شعبه
                verb="created a new tankhah",  # فعل
                target=instance,  # تنخواه به‌عنوان هدف
                description=f"تنخواه {instance.number} در شعبه {organization.name} ثبت شد.",
                data={'tankhah_id': instance.id}
            )

# 2. ارجاع فاکتور
@receiver(post_save, sender=Factor)
def notify_factor_referral(sender, instance, created, **kwargs):
    if not created and instance.status == 'REFERRED':
        # فرض می‌کنیم فاکتور ارجاع داده شده و باید به کاربران مرتبط اطلاع داده شود
        users_to_notify = User.objects.filter(userpost__post__organization=instance.organization, userpost__is_active=True)
        for user in users_to_notify:
            notify.send(
                sender=instance.created_by,
                recipient=user,
                verb="referred a factor",
                target=instance,
                description=f"فاکتور {instance.number} ارجاع داده شد.",
                data={'factor_id': instance.id}
            )

# 3. رد/تأیید فاکتور
@receiver(post_save, sender=Factor)
def notify_factor_status_change(sender, instance, created, **kwargs):
    if not created and instance.status in ['APPROVED', 'REJECTED']:
        action = "تأیید" if instance.status == 'APPROVED' else "رد"
        users_to_notify = User.objects.filter(userpost__post__organization=instance.organization, userpost__is_active=True)
        for user in users_to_notify:
            notify.send(
                sender=instance.created_by,
                recipient=user,
                verb=f"{action} a factor",
                target=instance,
                description=f"فاکتور {instance.number} {action} شد.",
                data={'factor_id': instance.id, 'status': instance.status}
            )

# 4. ثبت یا برگشت بودجه
@receiver(post_save, sender=BudgetTransaction)
def notify_budget_transaction(sender, instance, created, **kwargs):
    if created:
        action = "مصرف" if instance.transaction_type == 'CONSUMPTION' else "برگشت"
        users_to_notify = User.objects.filter(userpost__post__organization=instance.allocation.budget_period.organization, userpost__is_active=True)
        for user in users_to_notify:
            notify.send(
                sender=instance.created_by,
                recipient=user,
                verb=f"performed a budget {action}",
                target=instance,
                description=f"تراکنش بودجه ({action}) به مبلغ {instance.amount} ثبت شد.",
                data={'budget_transaction_id': instance.id, 'type': instance.transaction_type}
            )


# ==ارسالب ایمیل ===
from notifications.models import Notification
from django.core.mail import send_mail

@receiver(post_save, sender=Notification)
def send_notification_email(sender, instance, created, **kwargs):
    if created and instance.recipient.email:
        subject = f"اعلان جدید: {instance.verb}"
        message = instance.description or f"{instance.actor} {instance.verb} {instance.target or ''}"
        send_mail(
            subject,
            message,
            'soheiladv@gmail.com',
            [instance.recipient.email],
            fail_silently=True,
        )