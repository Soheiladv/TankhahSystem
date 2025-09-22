from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import os
import logging

from accounts.models import CustomUser

logger = logging.getLogger(__name__)

class BackupLocation(models.Model):
    """مدل برای مدیریت مسیرهای پشتیبان‌گیری"""
    
    LOCATION_TYPES = [
        ('LOCAL', _('محلی')),
        ('NETWORK', _('شبکه')),
        ('CLOUD', _('ابر')),
        ('EXTERNAL', _('خارجی')),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', _('فعال')),
        ('INACTIVE', _('غیرفعال')),
        ('ERROR', _('خطا')),
        ('TESTING', _('در حال تست')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_("نام مسیر"))
    path = models.CharField(max_length=500, verbose_name=_("مسیر"))
    location_type = models.CharField(
        max_length=20, 
        choices=LOCATION_TYPES, 
        default='LOCAL',
        verbose_name=_("نوع مسیر")
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='ACTIVE',
        verbose_name=_("وضعیت")
    )
    is_default = models.BooleanField(default=False, verbose_name=_("پیش‌فرض"))
    is_encrypted = models.BooleanField(default=False, verbose_name=_("رمزگذاری شده"))
    max_size_gb = models.IntegerField(null=True, blank=True, verbose_name=_("حداکثر حجم (GB)"))
    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("ایجادکننده"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان ایجاد"))
    last_tested = models.DateTimeField(null=True, blank=True, verbose_name=_("آخرین تست"))
    last_error = models.TextField(blank=True, null=True, verbose_name=_("آخرین خطا"))
    
    class Meta:
        verbose_name = _("مسیر پشتیبان‌گیری")
        verbose_name_plural = _("مسیرهای پشتیبان‌گیری")
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"
    
    def save(self, *args, **kwargs):
        # اگر این مسیر به عنوان پیش‌فرض تنظیم شد، بقیه را غیرفعال کن
        if self.is_default:
            BackupLocation.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
    
    def test_connection(self):
        """تست اتصال به مسیر"""
        try:
            # بررسی وجود مسیر
            if not os.path.exists(self.path):
                # تلاش برای ایجاد مسیر
                os.makedirs(self.path, exist_ok=True)
            
            # تست نوشتن فایل
            test_file = os.path.join(self.path, 'test_connection.tmp')
            with open(test_file, 'w') as f:
                f.write('test')
            
            # حذف فایل تست
            os.remove(test_file)
            
            from django.utils import timezone
            self.status = 'ACTIVE'
            self.last_error = None
            self.last_tested = timezone.now()
            self.save(update_fields=['status', 'last_error', 'last_tested'])
            
            return True, "اتصال موفق"
            
        except Exception as e:
            error_msg = str(e)
            self.status = 'ERROR'
            self.last_error = error_msg
            self.save(update_fields=['status', 'last_error'])
            
            return False, error_msg
    
    def get_available_space(self):
        """محاسبه فضای خالی"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.path)
            return {
                'total': total,
                'used': used,
                'free': free,
                'free_gb': round(free / (1024**3), 2),
                'used_percent': round((used / total) * 100, 2)
            }
        except Exception as e:
            logger.error(f"خطا در محاسبه فضای دیسک برای {self.path}: {e}")
            return None
    
    def get_backup_files(self):
        """دریافت لیست فایل‌های پشتیبان در این مسیر"""
        try:
            if not os.path.exists(self.path):
                return []
            
            files = []
            for filename in os.listdir(self.path):
                if filename.endswith(('.sql', '.json', '.gz', '.encrypted')):
                    file_path = os.path.join(self.path, filename)
                    if os.path.isfile(file_path):
                        stat = os.stat(file_path)
                        files.append({
                            'name': filename,
                            'path': file_path,
                            'size': stat.st_size,
                            'modified': stat.st_mtime
                        })
            
            return sorted(files, key=lambda x: x['modified'], reverse=True)
            
        except Exception as e:
            logger.error(f"خطا در دریافت فایل‌های پشتیبان از {self.path}: {e}")
            return []
    
    @classmethod
    def get_default_location(cls):
        """دریافت مسیر پیش‌فرض"""
        try:
            return cls.objects.filter(is_default=True, status='ACTIVE').first()
        except:
            return None
    
    @classmethod
    def get_active_locations(cls):
        """دریافت مسیرهای فعال"""
        return cls.objects.filter(status='ACTIVE').order_by('-is_default', 'name')
    
    @classmethod
    def create_default_locations(cls, user):
        """ایجاد مسیرهای پیش‌فرض"""
        from django.conf import settings
        
        default_locations = [
            {
                'name': 'مسیر محلی',
                'path': settings.BACKUP_LOCATIONS['local'],
                'location_type': 'LOCAL',
                'is_default': True,
                'description': 'مسیر پیش‌فرض محلی'
            },
            {
                'name': 'دیسک شبکه',
                'path': settings.BACKUP_LOCATIONS['network'],
                'location_type': 'NETWORK',
                'description': 'مسیر دیسک شبکه'
            },
            {
                'name': 'مسیر ثانویه',
                'path': settings.BACKUP_LOCATIONS['secondary'],
                'location_type': 'LOCAL',
                'description': 'مسیر ثانویه محلی'
            }
        ]
        
        for location_data in default_locations:
            location_data['created_by'] = user
            location, created = cls.objects.get_or_create(
                path=location_data['path'],
                defaults=location_data
            )
            if created:
                logger.info(f"مسیر پشتیبان‌گیری ایجاد شد: {location.name}")
