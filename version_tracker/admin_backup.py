"""
رابط ادمین برای مدیریت پشتیبان‌گیری
"""
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
import os
import glob
import json
from datetime import datetime, timedelta
import logging
import psutil

logger = logging.getLogger(__name__)

def get_disk_usage():
    """محاسبه فضای دیسک"""
    try:
        # مسیر backup
        backup_dir = getattr(settings, 'DBBACKUP_STORAGE_OPTIONS', {}).get('location', 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # فضای کل دیسک
        disk_usage = psutil.disk_usage(backup_dir)
        total_space = disk_usage.total
        used_space = disk_usage.used
        free_space = disk_usage.free
        
        # فضای استفاده شده توسط backup ها
        backup_files = glob.glob(os.path.join(backup_dir, '*'))
        backup_size = sum(os.path.getsize(f) for f in backup_files if os.path.isfile(f))
        
        return {
            'total_space': total_space,
            'used_space': used_space,
            'free_space': free_space,
            'backup_size': backup_size,
            'backup_dir': backup_dir,
            'backup_count': len(backup_files)
        }
    except Exception as e:
        logger.error(f"خطا در محاسبه فضای دیسک: {str(e)}")
        return {
            'total_space': 0,
            'used_space': 0,
            'free_space': 0,
            'backup_size': 0,
            'backup_dir': 'backups',
            'backup_count': 0
        }

def format_bytes(bytes_value):
    """تبدیل بایت به فرمت خوانا"""
    if bytes_value == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while bytes_value >= 1024 and i < len(size_names) - 1:
        bytes_value /= 1024.0
        i += 1
    
    return f"{bytes_value:.2f} {size_names[i]}"

class BackupAdminSite(AdminSite):
    site_header = "مدیریت پشتیبان‌گیری"
    site_title = "پشتیبان‌گیری"
    index_title = "مدیریت فایل‌های پشتیبان"

backup_admin = BackupAdminSite(name='backup_admin')

class BackupFile:
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)
        self.file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
        self.file_type = self._get_file_type()
        
    def _get_file_type(self):
        if 'main' in self.file_name.lower():
            return 'دیتابیس اصلی'
        elif 'logs' in self.file_name.lower():
            return 'دیتابیس لاگ'
        else:
            return 'نامشخص'
    
    @property
    def size_mb(self):
        return self.file_size / (1024 * 1024)
    
    @property
    def formatted_date(self):
        return self.file_date.strftime('%Y-%m-%d %H:%M:%S')

class BackupAdmin:
    def __init__(self):
        self.backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        self.encrypted_dir = os.path.join(settings.BASE_DIR, 'backups', 'encrypted')
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.encrypted_dir, exist_ok=True)
    
    def get_backup_files(self):
        """دریافت لیست فایل‌های پشتیبان"""
        backup_files = []
        
        # فایل‌های JSON
        json_files = glob.glob(os.path.join(self.backup_dir, '*.json'))
        for file_path in json_files:
            backup_files.append(BackupFile(file_path))
        
        # فایل‌های SQL
        sql_files = glob.glob(os.path.join(self.backup_dir, '*.sql'))
        for file_path in sql_files:
            backup_files.append(BackupFile(file_path))
        
        # فایل‌های رمزگذاری شده
        encrypted_files = glob.glob(os.path.join(self.encrypted_dir, '*'))
        for file_path in encrypted_files:
            backup_files.append(BackupFile(file_path))
        
        return sorted(backup_files, key=lambda x: x.file_date, reverse=True)
    
    def delete_backup_file(self, file_name):
        """حذف فایل پشتیبان"""
        try:
            # جستجو در پوشه اصلی
            file_path = os.path.join(self.backup_dir, file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True, "فایل حذف شد"
            
            # جستجو در پوشه رمزگذاری شده
            file_path = os.path.join(self.encrypted_dir, file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True, "فایل رمزگذاری شده حذف شد"
            
            return False, "فایل یافت نشد"
            
        except Exception as e:
            logger.error(f"خطا در حذف فایل {file_name}: {str(e)}")
            return False, f"خطا در حذف فایل: {str(e)}"
    
    def encrypt_backup_file(self, file_name, password):
        """رمزگذاری فایل پشتیبان"""
        try:
            import cryptography
            from cryptography.fernet import Fernet
            import base64
            
            # تولید کلید از رمز عبور
            key = base64.urlsafe_b64encode(password.encode()[:32].ljust(32, b'0'))
            fernet = Fernet(key)
            
            # خواندن فایل اصلی
            file_path = os.path.join(self.backup_dir, file_name)
            if not os.path.exists(file_path):
                return False, "فایل یافت نشد"
            
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # رمزگذاری
            encrypted_data = fernet.encrypt(file_data)
            
            # ذخیره فایل رمزگذاری شده
            encrypted_file = os.path.join(self.encrypted_dir, f"{file_name}.encrypted")
            with open(encrypted_file, 'wb') as f:
                f.write(encrypted_data)
            
            return True, f"فایل رمزگذاری شد: {encrypted_file}"
            
        except ImportError:
            return False, "کتابخانه cryptography نصب نشده است"
        except Exception as e:
            logger.error(f"خطا در رمزگذاری فایل {file_name}: {str(e)}")
            return False, f"خطا در رمزگذاری: {str(e)}"
    
    def get_backup_stats(self):
        """آمار فایل‌های پشتیبان"""
        files = self.get_backup_files()
        
        total_size = sum(f.file_size for f in files)
        main_files = [f for f in files if f.file_type == 'دیتابیس اصلی']
        logs_files = [f for f in files if f.file_type == 'دیتابیس لاگ']
        
        return {
            'total_files': len(files),
            'total_size_mb': total_size / (1024 * 1024),
            'main_files': len(main_files),
            'logs_files': len(logs_files),
            'oldest_file': min(files, key=lambda x: x.file_date).file_date if files else None,
            'newest_file': max(files, key=lambda x: x.file_date).file_date if files else None
        }

backup_admin_instance = BackupAdmin()

def backup_list_view(request):
    """نمایش لیست فایل‌های پشتیبان"""
    files = backup_admin_instance.get_backup_files()
    stats = backup_admin_instance.get_backup_stats()
    disk_info = get_disk_usage()
    
    # آمار اسکچول‌ها
    try:
        from notificationApp.models import BackupSchedule, BackupLog
        from django.utils import timezone
        
        now = timezone.now()
        schedule_stats = {
            'total_schedules': BackupSchedule.objects.count(),
            'active_schedules': BackupSchedule.objects.filter(is_active=True).count(),
            'pending_schedules': BackupSchedule.objects.filter(
                is_active=True,
                next_run__lte=now
            ).count(),
            'total_logs': BackupLog.objects.count(),
        }
    except Exception as e:
        logger.error(f"خطا در دریافت آمار اسکچول‌ها: {str(e)}")
        schedule_stats = {
            'total_schedules': 0,
            'active_schedules': 0,
            'pending_schedules': 0,
            'total_logs': 0,
        }
    
    context = {
        'files': files,
        'stats': stats,
        'backup_dir': backup_admin_instance.backup_dir,
        'encrypted_dir': backup_admin_instance.encrypted_dir,
        'disk_info': disk_info,
        'schedule_stats': schedule_stats,
    }
    
    return render(request, 'admin/backup_with_base.html', context)

def backup_delete_view(request, file_name):
    """حذف فایل پشتیبان"""
    if request.method == 'POST':
        success, message = backup_admin_instance.delete_backup_file(file_name)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
    
    return HttpResponseRedirect(reverse('backup_admin:backup_list'))

def backup_encrypt_view(request, file_name):
    """رمزگذاری فایل پشتیبان"""
    if request.method == 'POST':
        password = request.POST.get('password')
        if not password:
            messages.error(request, "رمز عبور الزامی است")
        else:
            success, message = backup_admin_instance.encrypt_backup_file(file_name, password)
            
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
    
    return HttpResponseRedirect(reverse('backup_admin:backup_list'))

def backup_create_view(request):
    """ایجاد پشتیبان‌گیری جدید"""
    if request.method == 'POST':
        database = request.POST.get('database', 'both')
        format_type = request.POST.get('format', 'json')
        encrypt = request.POST.get('encrypt') == 'on'
        password = request.POST.get('password', '')
        
        try:
            from django.core.management import call_command
            
            if database == 'both':
                # پشتیبان‌گیری از هر دو دیتابیس
                call_command('custom_backup', database='main', format=format_type)
                call_command('custom_backup', database='logs', format=format_type)
            else:
                call_command('custom_backup', database=database, format=format_type)
            
            if encrypt and password:
                # رمزگذاری فایل‌های جدید
                files = backup_admin_instance.get_backup_files()
                for file in files[:2]:  # دو فایل آخر
                    backup_admin_instance.encrypt_backup_file(file.file_name, password)
            
            messages.success(request, "پشتیبان‌گیری با موفقیت ایجاد شد")
            
        except Exception as e:
            logger.error(f"خطا در ایجاد پشتیبان‌گیری: {str(e)}")
            messages.error(request, f"خطا در ایجاد پشتیبان‌گیری: {str(e)}")
    
    return render(request, 'admin/backup_create.html', {
        'backup_admin': backup_admin_instance
    })

def backup_restore_view(request, file_name):
    """بازگردانی فایل پشتیبان"""
    if request.method == 'POST':
        confirm_text = request.POST.get('confirm_text', '')
        if confirm_text != 'بازگردانی':
            messages.error(request, "برای تأیید، باید کلمه 'بازگردانی' را تایپ کنید")
            return render(request, 'admin/backup_restore.html', {
                'file_name': file_name,
                'backup_admin': backup_admin_instance
            })
        
        try:
            from django.core.management import call_command
            call_command('dbrestore', '--database=default', f'--input-filename={file_name}')
            messages.success(request, f"فایل {file_name} با موفقیت بازگردانی شد")
        except Exception as e:
            logger.error(f"خطا در بازگردانی: {str(e)}")
            messages.error(request, f"خطا در بازگردانی: {str(e)}")
        return redirect('backup:list')
    
    return render(request, 'admin/backup_restore.html', {
        'file_name': file_name,
        'backup_admin': backup_admin_instance
    })

def backup_mysql_view(request):
    """ایجاد پشتیبان‌گیری MySQL استاندارد"""
    if request.method == 'POST':
        try:
            from django.core.management import call_command
            # ابتدا سعی کن از dbbackup استفاده کن
            call_command('dbbackup', '--database=default')
            call_command('dbbackup', '--database=logs')
            messages.success(request, "پشتیبان‌گیری MySQL استاندارد ایجاد شد")
        except Exception as e:
            logger.error(f"خطا در dbbackup: {str(e)}")
            # اگر dbbackup کار نکرد، از custom_backup استفاده کن
            try:
                call_command('custom_backup', '--database=main')
                call_command('custom_backup', '--database=logs')
                messages.success(request, "پشتیبان‌گیری MySQL با روش جایگزین ایجاد شد")
            except Exception as e2:
                logger.error(f"خطا در custom_backup: {str(e2)}")
                # اگر custom_backup هم کار نکرد، از secure_backup استفاده کن
                try:
                    call_command('secure_backup', '--database=main', '--format=json')
                    call_command('secure_backup', '--database=logs', '--format=json')
                    messages.success(request, "پشتیبان‌گیری MySQL با روش سوم (JSON) ایجاد شد")
                except Exception as e3:
                    logger.error(f"خطا در secure_backup: {str(e3)}")
                    messages.error(request, f"خطا در ایجاد پشتیبان‌گیری MySQL. لطفا MySQL client را نصب کنید یا از روش‌های دیگر استفاده کنید.")
        return redirect('backup:list')
    
    return render(request, 'admin/backup_mysql.html', {
        'backup_admin': backup_admin_instance
    })

# تنظیم URL ها
def get_backup_urls():
    return [
        path('', backup_list_view, name='backup_list'),
        path('create/', backup_create_view, name='backup_create'),
        path('delete/<str:file_name>/', backup_delete_view, name='backup_delete'),
        path('encrypt/<str:file_name>/', backup_encrypt_view, name='backup_encrypt'),
        path('restore/<str:file_name>/', backup_restore_view, name='backup_restore'),
        path('mysql/', backup_mysql_view, name='backup_mysql'),
    ]

backup_admin.get_urls = get_backup_urls
