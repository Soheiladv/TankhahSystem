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
        choices=[
            ('FACTOR', _('فاکتور')), 
            ('TANKHAH', _('تنخواه')), 
            ('PAYMENTORDER', _('دستور پرداخت')),
            ('BACKUP', _('پشتیبان\u200cگیری')),
            ('SYSTEM', _('سیستم')),
            ('SECURITY', _('امنیت')),
            ('MAINTENANCE', _('نگهداری'))
        ],
        verbose_name=_("نوع موجودیت")
    )
    action = models.CharField(
        max_length=50,
        choices=[
            ('CREATED', _('ایجاد')), 
            ('APPROVED', _('تأیید')), 
            ('REJECTED', _('رد')), 
            ('PAID', _('پرداخت')),
            ('COMPLETED', _('تکمیل')),
            ('FAILED', _('ناموفق')),
            ('SCHEDULED', _('زمان\u200cبندی شده')),
            ('STARTED', _('شروع شده')),
            ('FINISHED', _('پایان یافته'))
        ],
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
        choices=[
            ('FACTOR', _('فاکتور')), 
            ('TANKHAH', _('تنخواه')), 
            ('PAYMENTORDER', _('دستور پرداخت')),
            ('BACKUP', _('پشتیبان\u200cگیری')),
            ('SYSTEM', _('سیستم')),
            ('SECURITY', _('امنیت')),
            ('MAINTENANCE', _('نگهداری'))
        ],
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

# مدل اسکچول پشتیبان‌گیری
class BackupSchedule(models.Model):
    FREQUENCY_CHOICES = [
        ('DAILY', _('روزانه')),
        ('WEEKLY', _('هفتگی')),
        ('MONTHLY', _('ماهانه')),
        ('CUSTOM', _('سفارشی')),
    ]
    
    DATABASE_CHOICES = [
        ('BOTH', _('هر دو دیتابیس')),
        ('MAIN', _('دیتابیس اصلی')),
        ('LOGS', _('دیتابیس لاگ')),
    ]
    
    FORMAT_CHOICES = [
        ('JSON', _('JSON')),
        ('SQL', _('SQL')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_("نام اسکچول"))
    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, verbose_name=_("فرکانس"))
    custom_cron = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Cron سفارشی"))
    database = models.CharField(max_length=10, choices=DATABASE_CHOICES, default='BOTH', verbose_name=_("دیتابیس"))
    format_type = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='JSON', verbose_name=_("فرمت"))
    encrypt = models.BooleanField(default=False, verbose_name=_("رمزگذاری"))
    password = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("رمز عبور"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("ایجادکننده"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان ایجاد"))
    last_run = models.DateTimeField(null=True, blank=True, verbose_name=_("آخرین اجرا"))
    next_run = models.DateTimeField(null=True, blank=True, verbose_name=_("اجرای بعدی"))
    
    # تنظیمات اعلان
    notify_on_success = models.BooleanField(default=True, verbose_name=_("اعلان در صورت موفقیت"))
    notify_on_failure = models.BooleanField(default=True, verbose_name=_("اعلان در صورت خطا"))
    notify_recipients = models.ManyToManyField(CustomUser, related_name='backup_schedules', verbose_name=_("گیرندگان اعلان"))
    
    class Meta:
        verbose_name = _("اسکچول پشتیبان‌گیری")
        verbose_name_plural = _("اسکچول‌های پشتیبان‌گیری")
        ordering = ['-created_at']
        default_permissions=()
        permissions = [
            ('BackupSchedule_admin','مدیریت پشتیبان گیری'),
            ('BackupSchedule_view','نمایش پشتیبان ها '),
            ('BackupSchedule_delete','نمایش پشتیبان ها '),
            ('BackupSchedule_create','نمایش پشتیبان ها '),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"
    
    def get_next_run_time(self):
        """محاسبه زمان اجرای بعدی"""
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        now = timezone.now()
        
        if self.frequency == 'DAILY':
            return now + timedelta(days=1)
        elif self.frequency == 'WEEKLY':
            return now + timedelta(weeks=1)
        elif self.frequency == 'MONTHLY':
            return now + timedelta(days=30)
        elif self.frequency == 'CUSTOM' and self.custom_cron:
            # برای cron سفارشی، نیاز به کتابخانه croniter است
            try:
                from croniter import croniter
                cron = croniter(self.custom_cron, now)
                return cron.get_next(datetime)
            except ImportError:
                return now + timedelta(hours=1)
        
        return now + timedelta(hours=1)
    
    def update_next_run(self):
        """بروزرسانی زمان اجرای بعدی"""
        self.next_run = self.get_next_run_time()
        self.save(update_fields=['next_run'])

# مدل لاگ اجرای پشتیبان‌گیری
class BackupLog(models.Model):
    STATUS_CHOICES = [
        ('STARTED', _('شروع شده')),
        ('COMPLETED', _('تکمیل شده')),
        ('FAILED', _('ناموفق')),
        ('CANCELLED', _('لغو شده')),
    ]
    
    schedule = models.ForeignKey(BackupSchedule, on_delete=models.CASCADE, related_name='logs', verbose_name=_("اسکچول"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name=_("وضعیت"))
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان شروع"))
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name=_("زمان پایان"))
    duration = models.DurationField(null=True, blank=True, verbose_name=_("مدت زمان"))
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name=_("حجم فایل"))
    file_path = models.CharField(max_length=500, blank=True, null=True, verbose_name=_("مسیر فایل"))
    error_message = models.TextField(blank=True, null=True, verbose_name=_("پیام خطا"))
    details = models.JSONField(default=dict, blank=True, verbose_name=_("جزئیات"))
    
    class Meta:
        verbose_name = _("لاگ پشتیبان‌گیری")
        verbose_name_plural = _("لاگ‌های پشتیبان‌گیری")
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.schedule.name} - {self.get_status_display()} - {self.started_at}"
    
    def mark_completed(self, file_path=None, file_size=None):
        """علامت‌گذاری به عنوان تکمیل شده"""
        from django.utils import timezone
        
        self.status = 'COMPLETED'
        self.finished_at = timezone.now()
        self.duration = self.finished_at - self.started_at
        self.file_path = file_path
        self.file_size = file_size
        self.save()
    
    def mark_failed(self, error_message):
        """علامت‌گذاری به عنوان ناموفق"""
        from django.utils import timezone
        
        self.status = 'FAILED'
        self.finished_at = timezone.now()
        self.duration = self.finished_at - self.started_at
        self.error_message = error_message
        self.save()

