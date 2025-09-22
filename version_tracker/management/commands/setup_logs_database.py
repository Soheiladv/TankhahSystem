"""
دستور راه‌اندازی دیتابیس لاگ برای version_tracker
"""
from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'راه‌اندازی دیتابیس لاگ برای version_tracker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='اجرای اجباری حتی اگر جداول وجود داشته باشند'
        )

    def handle(self, *args, **options):
        force = options['force']
        
        self.stdout.write("شروع راه‌اندازی دیتابیس لاگ...")
        
        try:
            # بررسی اتصال به دیتابیس لاگ
            logs_db = connections['tankhah_logs_db']
            with logs_db.cursor() as cursor:
                cursor.execute("SELECT 1")
                self.stdout.write(self.style.SUCCESS("اتصال به دیتابیس لاگ برقرار است"))
            
            # بررسی وجود جداول
            with logs_db.cursor() as cursor:
                cursor.execute("SHOW TABLES LIKE 'version_tracker_%'")
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                if existing_tables and not force:
                    self.stdout.write(f"جداول version_tracker در دیتابیس لاگ وجود دارند: {existing_tables}")
                    self.stdout.write("برای حذف و ایجاد مجدد، از --force استفاده کنید")
                    return
                
                if existing_tables and force:
                    self.stdout.write("حذف جداول موجود...")
                    for table in existing_tables:
                        cursor.execute(f"DROP TABLE IF EXISTS {table}")
                        self.stdout.write(f"جدول {table} حذف شد")
            
            # ایجاد جداول با استفاده از Django
            self.stdout.write("ایجاد جداول version_tracker در دیتابیس لاگ...")
            
            # ابتدا migration ها را fake کنم
            call_command('migrate', 'version_tracker', '--database=tankhah_logs_db', '--fake', verbosity=0)
            
            # سپس جداول را ایجاد کنم
            call_command('migrate', 'version_tracker', '--database=tankhah_logs_db', '--run-syncdb', verbosity=0)
            
            self.stdout.write(self.style.SUCCESS("جداول version_tracker در دیتابیس لاگ ایجاد شدند!"))
            
            # نمایش آمار
            with logs_db.cursor() as cursor:
                cursor.execute("SHOW TABLES LIKE 'version_tracker_%'")
                tables = [row[0] for row in cursor.fetchall()]
                self.stdout.write(f"تعداد جداول ایجاد شده: {len(tables)}")
                for table in tables:
                    self.stdout.write(f"  - {table}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"خطا در راه‌اندازی دیتابیس لاگ: {str(e)}"))
            logger.error(f"خطا در راه‌اندازی دیتابیس لاگ: {str(e)}", exc_info=True)
