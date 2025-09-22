"""
دستور مدیریت فایل‌های پشتیبان
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import glob
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'مدیریت فایل‌های پشتیبان'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='نمایش لیست فایل‌های پشتیبان'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='پاکسازی فایل‌های قدیمی'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='تعداد روزهای نگه‌داری فایل‌ها (پیش‌فرض: 7)'
        )
        parser.add_argument(
            '--size',
            action='store_true',
            help='نمایش حجم فایل‌ها'
        )

    def handle(self, *args, **options):
        list_files = options['list']
        cleanup = options['cleanup']
        days = options['days']
        show_size = options['size']
        
        backup_dir = settings.DBBACKUP_STORAGE_OPTIONS['location']
        
        if not os.path.exists(backup_dir):
            self.stdout.write(self.style.WARNING("پوشه پشتیبان‌گیری وجود ندارد"))
            return
        
        # دریافت فایل‌های پشتیبان
        backup_patterns = ['*.sql', '*.sql.gz', '*.sql.gpg', '*.json']
        backup_files = []
        
        for pattern in backup_patterns:
            backup_files.extend(glob.glob(os.path.join(backup_dir, pattern)))
        
        backup_files.sort(key=os.path.getmtime, reverse=True)
        
        if list_files or show_size:
            self.stdout.write(f"فایل‌های پشتیبان در {backup_dir}:")
            self.stdout.write("-" * 80)
            
            total_size = 0
            for file_path in backup_files:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # تشخیص نوع دیتابیس
                db_type = "نامشخص"
                if "logs" in file_name.lower():
                    db_type = "لاگ"
                elif "default" in file_name.lower():
                    db_type = "اصلی"
                
                size_mb = file_size / (1024 * 1024)
                total_size += file_size
                
                self.stdout.write(f"{file_name:<40} {db_type:<10} {size_mb:>8.2f} MB {file_date.strftime('%Y-%m-%d %H:%M')}")
            
            self.stdout.write("-" * 80)
            self.stdout.write(f"تعداد کل فایل‌ها: {len(backup_files)}")
            self.stdout.write(f"حجم کل: {total_size / (1024 * 1024):.2f} MB")
        
        if cleanup:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            deleted_size = 0
            
            self.stdout.write(f"\nپاکسازی فایل‌های قدیمی‌تر از {days} روز...")
            
            for file_path in backup_files:
                file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_date < cutoff_date:
                    file_size = os.path.getsize(file_path)
                    file_name = os.path.basename(file_path)
                    
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        deleted_size += file_size
                        self.stdout.write(f"حذف شد: {file_name}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"خطا در حذف {file_name}: {str(e)}"))
            
            self.stdout.write(self.style.SUCCESS(f"\nپاکسازی تکمیل شد:"))
            self.stdout.write(f"تعداد فایل‌های حذف شده: {deleted_count}")
            self.stdout.write(f"حجم آزاد شده: {deleted_size / (1024 * 1024):.2f} MB")
        
        if not list_files and not cleanup and not show_size:
            self.stdout.write("برای مشاهده کمک، از --help استفاده کنید")
