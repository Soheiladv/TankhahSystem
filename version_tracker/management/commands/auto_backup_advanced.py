"""
دستور پشتیبان‌گیری خودکار پیشرفته
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone
import os
import json
import logging
from datetime import datetime, timedelta
import threading
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'پشتیبان‌گیری خودکار پیشرفته'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=24,
            help='فاصله زمانی پشتیبان‌گیری (ساعت)'
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
            '--output-dir',
            type=str,
            help='پوشه خروجی برای فایل‌های پشتیبان'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='اجرای در پس‌زمینه'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        encrypt = options['encrypt']
        password = options['password']
        cleanup_days = options['cleanup_days']
        output_dir = options['output_dir']
        daemon = options['daemon']
        
        if daemon:
            self.run_daemon(interval, encrypt, password, cleanup_days, output_dir)
        else:
            self.run_backup_cycle(interval, encrypt, password, cleanup_days, output_dir)

    def run_daemon(self, interval, encrypt, password, cleanup_days, output_dir):
        """اجرای در پس‌زمینه"""
        self.stdout.write("شروع پشتیبان‌گیری خودکار در پس‌زمینه...")
        
        def backup_worker():
            while True:
                try:
                    self.run_single_backup(encrypt, password, cleanup_days, output_dir)
                    time.sleep(interval * 3600)  # تبدیل ساعت به ثانیه
                except Exception as e:
                    logger.error(f"خطا در پشتیبان‌گیری خودکار: {str(e)}")
                    time.sleep(300)  # 5 دقیقه انتظار در صورت خطا
        
        thread = threading.Thread(target=backup_worker, daemon=True)
        thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write("پشتیبان‌گیری خودکار متوقف شد")

    def run_backup_cycle(self, interval, encrypt, password, cleanup_days, output_dir):
        """اجرای چرخه پشتیبان‌گیری"""
        self.stdout.write(f"شروع چرخه پشتیبان‌گیری با فاصله {interval} ساعت")
        
        try:
            while True:
                self.run_single_backup(encrypt, password, cleanup_days, output_dir)
                
                self.stdout.write(f"انتظار {interval} ساعت تا پشتیبان‌گیری بعدی...")
                time.sleep(interval * 3600)
                
        except KeyboardInterrupt:
            self.stdout.write("چرخه پشتیبان‌گیری متوقف شد")

    def run_single_backup(self, encrypt, password, cleanup_days, output_dir):
        """اجرای یک پشتیبان‌گیری"""
        try:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            self.stdout.write(f"شروع پشتیبان‌گیری در {timestamp}")
            
            # تنظیم پوشه خروجی
            if output_dir:
                backup_dir = output_dir
            else:
                backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            
            os.makedirs(backup_dir, exist_ok=True)
            
            # پشتیبان‌گیری از دیتابیس اصلی
            call_command('secure_backup', 
                        database='main', 
                        format='json',
                        output_dir=backup_dir,
                        quiet=True)
            
            # پشتیبان‌گیری از دیتابیس لاگ
            call_command('secure_backup', 
                        database='logs', 
                        format='json',
                        output_dir=backup_dir,
                        quiet=True)
            
            # رمزگذاری در صورت درخواست
            if encrypt and password:
                self.encrypt_latest_backups(backup_dir, password)
            
            # پاکسازی فایل‌های قدیمی
            self.cleanup_old_backups(backup_dir, cleanup_days)
            
            # ثبت لاگ موفقیت
            self.log_backup_success(timestamp, backup_dir)
            
            self.stdout.write(self.style.SUCCESS("پشتیبان‌گیری خودکار تکمیل شد"))
            
        except Exception as e:
            logger.error(f"خطا در پشتیبان‌گیری خودکار: {str(e)}")
            self.stdout.write(self.style.ERROR(f"خطا در پشتیبان‌گیری: {str(e)}"))
            self.log_backup_error(str(e), backup_dir)

    def encrypt_latest_backups(self, backup_dir, password):
        """رمزگذاری آخرین فایل‌های پشتیبان"""
        try:
            import cryptography
            from cryptography.fernet import Fernet
            import base64
            
            # تولید کلید از رمز عبور
            key = base64.urlsafe_b64encode(password.encode()[:32].ljust(32, b'0'))
            fernet = Fernet(key)
            
            # رمزگذاری فایل‌های JSON
            for file_name in os.listdir(backup_dir):
                if file_name.endswith('.json') and not file_name.endswith('.encrypted'):
                    file_path = os.path.join(backup_dir, file_name)
                    
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                    
                    # رمزگذاری
                    encrypted_data = fernet.encrypt(file_data)
                    
                    # ذخیره فایل رمزگذاری شده
                    encrypted_file = os.path.join(backup_dir, f"{file_name}.encrypted")
                    with open(encrypted_file, 'wb') as f:
                        f.write(encrypted_data)
                    
                    # حذف فایل اصلی
                    os.remove(file_path)
                    
                    self.stdout.write(f"فایل رمزگذاری شد: {file_name}")
                    
        except ImportError:
            self.stdout.write(self.style.WARNING("کتابخانه cryptography نصب نشده است"))
        except Exception as e:
            logger.error(f"خطا در رمزگذاری: {str(e)}")
            self.stdout.write(self.style.WARNING(f"خطا در رمزگذاری: {str(e)}"))

    def cleanup_old_backups(self, backup_dir, days):
        """پاکسازی فایل‌های قدیمی"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            for file_name in os.listdir(backup_dir):
                file_path = os.path.join(backup_dir, file_name)
                
                if os.path.isfile(file_path):
                    file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_date < cutoff_date:
                        os.remove(file_path)
                        deleted_count += 1
                        self.stdout.write(f"حذف فایل قدیمی: {file_name}")
            
            if deleted_count > 0:
                self.stdout.write(f"تعداد فایل‌های حذف شده: {deleted_count}")
            else:
                self.stdout.write("هیچ فایل قدیمی‌ای برای حذف یافت نشد")
                
        except Exception as e:
            logger.error(f"خطا در پاکسازی: {str(e)}")
            self.stdout.write(self.style.WARNING(f"خطا در پاکسازی: {str(e)}"))

    def log_backup_success(self, timestamp, backup_dir):
        """ثبت لاگ موفقیت پشتیبان‌گیری"""
        log_entry = {
            'timestamp': timestamp,
            'status': 'success',
            'message': 'پشتیبان‌گیری خودکار با موفقیت انجام شد',
            'backup_dir': backup_dir
        }
        
        log_file = os.path.join(backup_dir, 'backup_log.json')
        self.append_to_log(log_file, log_entry)

    def log_backup_error(self, error_message, backup_dir):
        """ثبت لاگ خطای پشتیبان‌گیری"""
        log_entry = {
            'timestamp': timezone.now().strftime('%Y%m%d_%H%M%S'),
            'status': 'error',
            'message': f'خطا در پشتیبان‌گیری خودکار: {error_message}',
            'backup_dir': backup_dir
        }
        
        log_file = os.path.join(backup_dir, 'backup_log.json')
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
