"""
دستور پشتیبان‌گیری از هر دو دیتابیس (اصلی و لاگ)
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone
import os
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'پشتیبان‌گیری از هر دو دیتابیس (اصلی و لاگ)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--compress',
            action='store_true',
            help='فشرده‌سازی فایل‌های پشتیبان'
        )
        parser.add_argument(
            '--encrypt',
            action='store_true',
            help='رمزگذاری فایل‌های پشتیبان'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='پاکسازی فایل‌های قدیمی'
        )

    def handle(self, *args, **options):
        compress = options['compress']
        encrypt = options['encrypt']
        cleanup = options['cleanup']
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        
        self.stdout.write("شروع پشتیبان‌گیری از هر دو دیتابیس...")
        
        try:
            # پشتیبان‌گیری از دیتابیس اصلی
            self.stdout.write("پشتیبان‌گیری از دیتابیس اصلی...")
            main_backup_args = ['dbbackup']
            if compress:
                main_backup_args.append('--compress')
            if encrypt:
                main_backup_args.append('--encrypt')
            
            call_command(*main_backup_args)
            self.stdout.write(self.style.SUCCESS("پشتیبان‌گیری از دیتابیس اصلی تکمیل شد"))
            
            # پشتیبان‌گیری از دیتابیس لاگ
            self.stdout.write("پشتیبان‌گیری از دیتابیس لاگ...")
            logs_backup_args = ['dbbackup', '--database=tankhah_logs_db']
            if compress:
                logs_backup_args.append('--compress')
            if encrypt:
                logs_backup_args.append('--encrypt')
            
            call_command(*logs_backup_args)
            self.stdout.write(self.style.SUCCESS("پشتیبان‌گیری از دیتابیس لاگ تکمیل شد"))
            
            # پاکسازی فایل‌های قدیمی
            if cleanup:
                self.stdout.write("پاکسازی فایل‌های قدیمی...")
                call_command('dbbackup', '--cleanup')
                self.stdout.write(self.style.SUCCESS("پاکسازی تکمیل شد"))
            
            # نمایش آمار فایل‌های پشتیبان
            backup_dir = settings.DBBACKUP_STORAGE_OPTIONS['location']
            if os.path.exists(backup_dir):
                backup_files = [f for f in os.listdir(backup_dir) if f.endswith(('.sql', '.gz', '.gpg'))]
                self.stdout.write(f"\nتعداد فایل‌های پشتیبان: {len(backup_files)}")
                for file in sorted(backup_files)[-5:]:  # نمایش 5 فایل آخر
                    file_path = os.path.join(backup_dir, file)
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    self.stdout.write(f"  - {file} ({file_size:.2f} MB)")
            
            self.stdout.write(self.style.SUCCESS("پشتیبان‌گیری کامل از هر دو دیتابیس تکمیل شد!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"خطا در پشتیبان‌گیری: {str(e)}"))
            logger.error(f"خطا در پشتیبان‌گیری: {str(e)}", exc_info=True)
