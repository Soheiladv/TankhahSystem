"""
دستور مدیریت برای پاکسازی مقادیر datetime نامعتبر
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from datetime import datetime


class Command(BaseCommand):
    help = 'پاکسازی مقادیر datetime نامعتبر در دیتابیس'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='فقط نمایش رکوردهای نامعتبر بدون اصلاح',
        )
        parser.add_argument(
            '--table',
            type=str,
            default='budgets_paymentorder',
            help='نام جدول برای پاکسازی (پیش‌فرض: budgets_paymentorder)',
        )

    def handle(self, *args, **options):
        table_name = options['table']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(f'شروع پاکسازی جدول {table_name}...')
        )
        
        with connection.cursor() as cursor:
            # بررسی مقادیر نامعتبر
            cursor.execute(f"""
                SELECT id, created_at, updated_at 
                FROM {table_name} 
                WHERE created_at IS NULL 
                   OR created_at = '0000-00-00 00:00:00'
                   OR created_at = '1970-01-01 00:00:00'
                   OR created_at < '2020-01-01 00:00:00'
                   OR updated_at IS NULL 
                   OR updated_at = '0000-00-00 00:00:00'
                   OR updated_at = '1970-01-01 00:00:00'
                   OR updated_at < '2020-01-01 00:00:00'
            """)
            
            invalid_records = cursor.fetchall()
            self.stdout.write(f'تعداد رکوردهای نامعتبر یافت شده: {len(invalid_records)}')
            
            if not invalid_records:
                self.stdout.write(
                    self.style.SUCCESS('هیچ رکورد نامعتبری یافت نشد.')
                )
                return
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('حالت dry-run فعال است. رکوردها اصلاح نخواهند شد.')
                )
                for record_id, created_at, updated_at in invalid_records:
                    self.stdout.write(f'ID: {record_id}, created_at: {created_at}, updated_at: {updated_at}')
                return
            
            # اصلاح مقادیر نامعتبر
            current_time = timezone.now()
            fixed_count = 0
            
            for record_id, created_at, updated_at in invalid_records:
                self.stdout.write(f'اصلاح رکورد ID: {record_id}')
                
                # تعیین مقادیر جدید
                new_created_at = current_time
                new_updated_at = current_time
                
                # اگر created_at معتبر است، از آن استفاده کن
                if created_at and created_at != '0000-00-00 00:00:00' and created_at != '1970-01-01 00:00:00':
                    try:
                        if isinstance(created_at, str):
                            new_created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                        else:
                            new_created_at = created_at
                    except:
                        new_created_at = current_time
                
                # اگر updated_at معتبر است، از آن استفاده کن
                if updated_at and updated_at != '0000-00-00 00:00:00' and updated_at != '1970-01-01 00:00:00':
                    try:
                        if isinstance(updated_at, str):
                            new_updated_at = datetime.strptime(updated_at, '%Y-%m-%d %H:%M:%S')
                        else:
                            new_updated_at = updated_at
                    except:
                        new_updated_at = current_time
                
                # به‌روزرسانی رکورد
                cursor.execute(f"""
                    UPDATE {table_name} 
                    SET created_at = %s, updated_at = %s 
                    WHERE id = %s
                """, [new_created_at, new_updated_at, record_id])
                
                fixed_count += 1
            
            self.stdout.write(f'تعداد رکوردهای اصلاح شده: {fixed_count}')
            
            # بررسی نهایی
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM {table_name} 
                WHERE created_at IS NULL 
                   OR created_at = '0000-00-00 00:00:00'
                   OR created_at = '1970-01-01 00:00:00'
                   OR updated_at IS NULL 
                   OR updated_at = '0000-00-00 00:00:00'
                   OR updated_at = '1970-01-01 00:00:00'
            """)
            
            remaining_invalid = cursor.fetchone()[0]
            
            if remaining_invalid == 0:
                self.stdout.write(
                    self.style.SUCCESS('✅ همه مقادیر datetime اصلاح شدند!')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ هنوز {remaining_invalid} مقدار نامعتبر وجود دارد.')
                )
