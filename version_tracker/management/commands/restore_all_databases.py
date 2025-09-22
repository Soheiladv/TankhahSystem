"""
دستور بازیابی هر دو دیتابیس (اصلی و لاگ)
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'بازیابی هر دو دیتابیس (اصلی و لاگ)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='نام فایل پشتیبان برای بازیابی'
        )
        parser.add_argument(
            '--database',
            type=str,
            choices=['main', 'logs', 'both'],
            default='both',
            help='دیتابیس مورد نظر برای بازیابی (main, logs, both)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='اجرای اجباری بدون تأیید'
        )

    def handle(self, *args, **options):
        backup_file = options['file']
        database = options['database']
        force = options['force']
        
        if not backup_file:
            self.stdout.write(self.style.ERROR("لطفاً نام فایل پشتیبان را مشخص کنید"))
            return
        
        # بررسی وجود فایل پشتیبان
        backup_dir = settings.DBBACKUP_STORAGE_OPTIONS['location']
        backup_path = os.path.join(backup_dir, backup_file)
        
        if not os.path.exists(backup_path):
            self.stdout.write(self.style.ERROR(f"فایل پشتیبان یافت نشد: {backup_path}"))
            return
        
        # تأیید از کاربر
        if not force:
            confirm = input(f"آیا مطمئن هستید که می‌خواهید دیتابیس{'ها' if database == 'both' else ''} را بازیابی کنید؟ (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write("عملیات لغو شد")
                return
        
        try:
            if database in ['main', 'both']:
                self.stdout.write("بازیابی دیتابیس اصلی...")
                call_command('dbrestore', '--file', backup_file)
                self.stdout.write(self.style.SUCCESS("بازیابی دیتابیس اصلی تکمیل شد"))
            
            if database in ['logs', 'both']:
                self.stdout.write("بازیابی دیتابیس لاگ...")
                call_command('dbrestore', '--file', backup_file, '--database=tankhah_logs_db')
                self.stdout.write(self.style.SUCCESS("بازیابی دیتابیس لاگ تکمیل شد"))
            
            self.stdout.write(self.style.SUCCESS("بازیابی کامل تکمیل شد!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"خطا در بازیابی: {str(e)}"))
            logger.error(f"خطا در بازیابی: {str(e)}", exc_info=True)
