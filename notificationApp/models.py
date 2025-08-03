from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from accounts.models import CustomUser
from core.models import Post, Organization
# Create your models here.
# مدل اعلان پویا
class NotificationRule(models.Model):
    entity_type = models.CharField(
        max_length=50,
        choices=[('FACTOR', _('فاکتور')), ('TANKHAH', _('تنخواه')), ('PAYMENTORDER', _('دستور پرداخت'))],
        verbose_name=_("نوع موجودیت")
    )
    action = models.CharField(
        max_length=50,
        choices=[('CREATED', _('ایجاد')), ('APPROVED', _('تأیید')), ('REJECTED', _('رد')), ('PAID', _('پرداخت'))],
        verbose_name=_("اقدام")
    )
    recipients = models.ManyToManyField('core.Post', verbose_name=_("گیرندگان"))
    priority = models.CharField(
        max_length=20,
        choices=[('LOW', _('کم')), ('MEDIUM', _('متوسط')), ('HIGH', _('زیاد'))],
        default='MEDIUM',
        verbose_name=_("اولویت")
    )
    channel = models.CharField(
        max_length=50,
        choices=[('IN_APP', _('درون‌برنامه')), ('EMAIL', _('ایمیل')), ('SMS', _('پیامک'))],
        default='IN_APP',
        verbose_name=_("کانال")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))

    class Meta:
        verbose_name = _("قانون اعلان")
        verbose_name_plural = _("قوانین اعلان")
        default_permissions = ()
        permissions =[
            ('NotificationRule_add','افزودن اعلان'),
            ('NotificationRule_update','بروزرسانی اعلان'),
            ('NotificationRule_view','نمایش اعلان'),
            ('NotificationRule_delete','حذف اعلان'),
        ]

    def __str__(self):
        return f"{self.get_entity_type_display()} - {self.get_action_display()} ({self.get_channel_display()})"

class Notification(models.Model):
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications', verbose_name=_("گیرنده"))
    actor = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='acted_notifications', verbose_name=_("عامل"))
    verb = models.CharField(max_length=100, verbose_name=_("فعل"))
    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    unread = models.BooleanField(default=True, verbose_name=_("خوانده‌نشده"))
    deleted = models.BooleanField(default=False, verbose_name=_("حذف‌شده"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان ایجاد"))
    priority = models.CharField(
        max_length=20,
        choices=[
            ('LOW', _('کم')),
            ('MEDIUM', _('متوسط')),
            ('HIGH', _('زیاد')),
            ('WARNING', _('هشدار')),
            ('ERROR', _('خطا')),
            ('LOCKED', _('قفل‌شده'))
          ],
        default='MEDIUM',
        verbose_name=_("اولویت")
    )
    entity_type = models.CharField(
        max_length=50,
        choices=[('FACTOR', _('فاکتور')), ('TANKHAH', _('تنخواه')), ('PAYMENTORDER', _('دستور پرداخت'))],
        verbose_name=_("نوع موجودیت")
    )
    # فیلدهای GenericForeignKey برای target
    target_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("نوع هدف"))
    target_object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("شناسه هدف"))
    target = GenericForeignKey('target_content_type', 'target_object_id')

    class Meta:
        verbose_name = _("اعلان")
        verbose_name_plural = _("اعلان‌ها")
        ordering = ['-timestamp']
        default_permissions = []
        permissions = [
            ('Notification_view', 'نمایش اعلان'),
            ('Notification_delete', 'حذف اعلان'),
        ]

    def __str__(self):
        return f"{self.recipient.username} - {self.verb} - {self.get_entity_type_display()}"

    def mark_as_read(self):
        if self.unread:
            self.unread = False
            self.save(update_fields=['unread'])

    def mark_as_deleted(self):
        if not self.deleted:
            self.deleted = True
            self.save(update_fields=['deleted'])

