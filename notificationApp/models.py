from django.db import models
from django.utils.translation import gettext_lazy as _

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
