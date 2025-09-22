"""
دستور پشتیبان‌گیری دوره‌ای
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone
import os
import json
import logging
from datetime import datetime, timedelta
import schedule
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'پشتیبان‌گیری دوره‌ای از دیتابیس‌ها'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schedule-type',
            type=str,
            choices=['daily', 'weekly', 'monthly'],
            default='daily',
            help='نوع برنامه‌ریزی پشتیبان‌گیری'
        )
        parser.add_argument(
            '--time',
            type=str,
            default='02:00',
            help='زمان اجرای پشتیبان‌گیری (HH:MM)'
        )
        parser.add_argument(
            '--encrypt',
            action='store_true',
            help='رمزگذاری فایل‌های پشتیبان'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='رمز عبور برای رمزگذاری'
        )
        parser.add_argument(
            '--cleanup-days',
            type=int,
            default=30,
            help='تعداد روزهای نگه‌داری فایل‌های قدیمی'
        )
        parser.add_argument(
            '--run-once',
            action='store_true',
            help='اجرای یکباره پشتیبان‌گیری'
        )

    def handle(self, *args, **options):
        schedule_type = options['schedule_type']
        backup_time = options['time']
        encrypt = options['encrypt']
        password = options['password']
        cleanup_days = options['cleanup_days']
        run_once = options['run_once']
        
        if run_once:
            self.run_backup(encrypt, password, cleanup_days)
            return
        
        # تنظیم برنامه‌ریزی
        if schedule_type == 'daily':
            schedule.every().day.at(backup_time).do(
                self.run_backup, encrypt, password, cleanup_days
            )
        elif schedule_type == 'weekly':
            schedule.every().monday.at(backup_time).do(
                self.run_backup, encrypt, password, cleanup_days
            )
        elif schedule_type == 'monthly':
            schedule.every().month.do(
                self.run_backup, encrypt, password, cleanup_days
            )
        
        self.stdout.write(f"پشتیبان‌گیری {schedule_type} در ساعت {backup_time} برنامه‌ریزی شد")
        self.stdout.write("برای توقف، Ctrl+C را فشار دهید")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # بررسی هر دقیقه
        except KeyboardInterrupt:
            self.stdout.write("پشتیبان‌گیری دوره‌ای متوقف شد")

    def run_backup(self, encrypt=False, password=None, cleanup_days=30):
        """اجرای پشتیبان‌گیری"""
        try:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            self.stdout.write(f"شروع پشتیبان‌گیری در {timestamp}")
            
            # پشتیبان‌گیری از دیتابیس اصلی
            call_command('custom_backup', database='main', format='json')
            self.stdout.write("پشتیبان‌گیری از دیتابیس اصلی تکمیل شد")
            
            # پشتیبان‌گیری از دیتابیس لاگ
            call_command('custom_backup', database='logs', format='json')
            self.stdout.write("پشتیبان‌گیری از دیتابیس لاگ تکمیل شد")
            
            # رمزگذاری در صورت درخواست
            if encrypt and password:
                self.encrypt_latest_backups(password)
            
            # پاکسازی فایل‌های قدیمی
            self.cleanup_old_backups(cleanup_days)
            
            # ثبت لاگ موفقیت
            self.log_backup_success(timestamp)
            
            self.stdout.write(self.style.SUCCESS("پشتیبان‌گیری دوره‌ای تکمیل شد"))
            
        except Exception as e:
            logger.error(f"خطا در پشتیبان‌گیری دوره‌ای: {str(e)}")
            self.stdout.write(self.style.ERROR(f"خطا در پشتیبان‌گیری: {str(e)}"))
            self.log_backup_error(str(e))

    def encrypt_latest_backups(self, password):
        """رمزگذاری آخرین فایل‌های پشتیبان"""
        try:
            from version_tracker.admin_backup import backup_admin_instance
            
            # دریافت آخرین فایل‌ها
            files = backup_admin_instance.get_backup_files()
            latest_files = files[:2]  # دو فایل آخر
            
            for file in latest_files:
                if not file.file_name.endswith('.encrypted'):
                    success, message = backup_admin_instance.encrypt_backup_file(
                        file.file_name, password
                    )
                    if success:
                        self.stdout.write(f"رمزگذاری {file.file_name}: {message}")
                    else:
                        self.stdout.write(self.style.WARNING(f"خطا در رمزگذاری {file.file_name}: {message}"))
                        
        except Exception as e:
            logger.error(f"خطا در رمزگذاری: {str(e)}")
            self.stdout.write(self.style.WARNING(f"خطا در رمزگذاری: {str(e)}"))

    def cleanup_old_backups(self, days):
        """پاکسازی فایل‌های قدیمی"""
        try:
            from version_tracker.admin_backup import backup_admin_instance
            
            files = backup_admin_instance.get_backup_files()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            deleted_count = 0
            for file in files:
                if file.file_date < cutoff_date:
                    success, message = backup_admin_instance.delete_backup_file(file.file_name)
                    if success:
                        deleted_count += 1
                        self.stdout.write(f"حذف فایل قدیمی: {file.file_name}")
            
            if deleted_count > 0:
                self.stdout.write(f"تعداد فایل‌های حذف شده: {deleted_count}")
            else:
                self.stdout.write("هیچ فایل قدیمی‌ای برای حذف یافت نشد")
                
        except Exception as e:
            logger.error(f"خطا در پاکسازی: {str(e)}")
            self.stdout.write(self.style.WARNING(f"خطا در پاکسازی: {str(e)}"))

    def log_backup_success(self, timestamp):
        """ثبت لاگ موفقیت پشتیبان‌گیری"""
        log_entry = {
            'timestamp': timestamp,
            'status': 'success',
            'message': 'پشتیبان‌گیری دوره‌ای با موفقیت انجام شد'
        }
        
        log_file = os.path.join(settings.BASE_DIR, 'backups', 'backup_log.json')
        self.append_to_log(log_file, log_entry)

    def log_backup_error(self, error_message):
        """ثبت لاگ خطای پشتیبان‌گیری"""
        log_entry = {
            'timestamp': timezone.now().strftime('%Y%m%d_%H%M%S'),
            'status': 'error',
            'message': f'خطا در پشتیبان‌گیری دوره‌ای: {error_message}'
        }
        
        log_file = os.path.join(settings.BASE_DIR, 'backups', 'backup_log.json')
        self.append_to_log(log_file, log_entry)

    def append_to_log(self, log_file, log_entry):
        """اضافه کردن ورودی به فایل لاگ"""
        try:
            logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            logs.append(log_entry)
            
            # نگه‌داری فقط 100 ورودی آخر
            if len(logs) > 100:
                logs = logs[-100:]
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"خطا در ثبت لاگ: {str(e)}")
