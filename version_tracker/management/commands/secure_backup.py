"""
دستور پشتیبان‌گیری امن بدون نمایش خطاهای mysqldump
"""
from django.core.management.base import BaseCommand
from django.db import connections
from django.conf import settings
from django.utils import timezone
import os
import json
import logging
import subprocess
import tempfile
from datetime import datetime, date, time
from decimal import Decimal

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'پشتیبان‌گیری امن از دیتابیس‌ها بدون نمایش خطاهای mysqldump'

    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            type=str,
            choices=['main', 'logs', 'both'],
            default='both',
            help='دیتابیس مورد نظر برای پشتیبان‌گیری'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'sql'],
            default='json',
            help='فرمت فایل پشتیبان'
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
            '--output-dir',
            type=str,
            help='پوشه خروجی برای فایل‌های پشتیبان'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='حالت سکوت - عدم نمایش جزئیات'
        )

    def handle(self, *args, **options):
        database = options['database']
        format_type = options['format']
        encrypt = options['encrypt']
        password = options['password']
        output_dir = options['output_dir']
        quiet = options['quiet']
        
        # تنظیم پوشه خروجی
        if output_dir:
            backup_dir = output_dir
        else:
            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            if not quiet:
                self.stdout.write("شروع پشتیبان‌گیری امن...")
            
            if database in ['main', 'both']:
                self.backup_database_secure('default', 'main', timestamp, backup_dir, format_type, quiet)
            
            if database in ['logs', 'both']:
                self.backup_database_secure('tankhah_logs_db', 'logs', timestamp, backup_dir, format_type, quiet)
            
            # رمزگذاری در صورت درخواست
            if encrypt and password:
                self.encrypt_backups(backup_dir, password, quiet)
            
            if not quiet:
                self.stdout.write(self.style.SUCCESS("پشتیبان‌گیری امن تکمیل شد!"))
            
        except Exception as e:
            if not quiet:
                self.stdout.write(self.style.ERROR(f"خطا در پشتیبان‌گیری: {str(e)}"))
            logger.error(f"خطا در پشتیبان‌گیری امن: {str(e)}", exc_info=True)

    def backup_database_secure(self, db_alias, db_name, timestamp, backup_dir, format_type, quiet):
        """پشتیبان‌گیری امن از یک دیتابیس"""
        try:
            if not quiet:
                self.stdout.write(f"پشتیبان‌گیری از دیتابیس {db_name}...")
            
            connection = connections[db_alias]
            
            if format_type == 'json':
                self.backup_to_json_secure(connection, db_name, timestamp, backup_dir, quiet)
            else:
                self.backup_to_sql_secure(connection, db_name, timestamp, backup_dir, quiet)
                
        except Exception as e:
            if not quiet:
                self.stdout.write(self.style.ERROR(f"خطا در پشتیبان‌گیری {db_name}: {str(e)}"))
            logger.error(f"خطا در پشتیبان‌گیری {db_name}: {str(e)}", exc_info=True)

    def backup_to_json_secure(self, connection, db_name, timestamp, backup_dir, quiet):
        """پشتیبان‌گیری امن به فرمت JSON"""
        backup_data = {}
        
        try:
            with connection.cursor() as cursor:
                # دریافت لیست جداول
                cursor.execute("SHOW TABLES")
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    try:
                        # دریافت ساختار جدول
                        cursor.execute(f"DESCRIBE {table}")
                        columns = [row[0] for row in cursor.fetchall()]
                        
                        # دریافت داده‌های جدول
                        cursor.execute(f"SELECT * FROM {table}")
                        rows = cursor.fetchall()
                        
                        # تبدیل به فرمت JSON
                        table_data = {
                            'columns': columns,
                            'rows': [list(row) for row in rows]
                        }
                        backup_data[table] = table_data
                        
                    except Exception as e:
                        if not quiet:
                            self.stdout.write(self.style.WARNING(f"خطا در جدول {table}: {str(e)}"))
                        logger.warning(f"خطا در جدول {table}: {str(e)}")
                        continue
            
            # ذخیره فایل JSON
            backup_file = os.path.join(backup_dir, f"{db_name}_{timestamp}.json")
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2, default=self.json_serializer)
            
            if not quiet:
                self.stdout.write(f"فایل پشتیبان ایجاد شد: {backup_file}")
                
        except Exception as e:
            if not quiet:
                self.stdout.write(self.style.ERROR(f"خطا در پشتیبان‌گیری JSON: {str(e)}"))
            logger.error(f"خطا در پشتیبان‌گیری JSON: {str(e)}", exc_info=True)

    def backup_to_sql_secure(self, connection, db_name, timestamp, backup_dir, quiet):
        """پشتیبان‌گیری امن به فرمت SQL"""
        sql_statements = []
        
        try:
            with connection.cursor() as cursor:
                # دریافت لیست جداول
                cursor.execute("SHOW TABLES")
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    try:
                        # CREATE TABLE statement
                        cursor.execute(f"SHOW CREATE TABLE {table}")
                        create_statement = cursor.fetchone()[1]
                        sql_statements.append(f"-- Table: {table}")
                        sql_statements.append(create_statement + ";")
                        sql_statements.append("")
                        
                        # INSERT statements
                        cursor.execute(f"SELECT * FROM {table}")
                        rows = cursor.fetchall()
                        
                        if rows:
                            cursor.execute(f"DESCRIBE {table}")
                            columns = [row[0] for row in cursor.fetchall()]
                            
                            for row in rows:
                                values = []
                                for value in row:
                                    if value is None:
                                        values.append('NULL')
                                    elif isinstance(value, str):
                                        values.append(f"'{value.replace(chr(39), chr(39)+chr(39))}'")
                                    else:
                                        values.append(str(value))
                                
                                insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)});"
                                sql_statements.append(insert_sql)
                        
                        sql_statements.append("")
                        
                    except Exception as e:
                        if not quiet:
                            self.stdout.write(self.style.WARNING(f"خطا در جدول {table}: {str(e)}"))
                        logger.warning(f"خطا در جدول {table}: {str(e)}")
                        continue
            
            # ذخیره فایل SQL
            backup_file = os.path.join(backup_dir, f"{db_name}_{timestamp}.sql")
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(sql_statements))
            
            if not quiet:
                self.stdout.write(f"فایل پشتیبان ایجاد شد: {backup_file}")
                
        except Exception as e:
            if not quiet:
                self.stdout.write(self.style.ERROR(f"خطا در پشتیبان‌گیری SQL: {str(e)}"))
            logger.error(f"خطا در پشتیبان‌گیری SQL: {str(e)}", exc_info=True)

    def json_serializer(self, obj):
        """تابع serialization برای انواع داده‌های خاص"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, time):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)

    def encrypt_backups(self, backup_dir, password, quiet):
        """رمزگذاری فایل‌های پشتیبان"""
        try:
            import cryptography
            from cryptography.fernet import Fernet
            import base64
            
            # تولید کلید از رمز عبور
            key = base64.urlsafe_b64encode(password.encode()[:32].ljust(32, b'0'))
            fernet = Fernet(key)
            
            # رمزگذاری فایل‌های JSON و SQL
            for file_name in os.listdir(backup_dir):
                if file_name.endswith(('.json', '.sql')):
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
                    
                    if not quiet:
                        self.stdout.write(f"فایل رمزگذاری شد: {file_name}")
                        
        except ImportError:
            if not quiet:
                self.stdout.write(self.style.ERROR("کتابخانه cryptography نصب نشده است"))
        except Exception as e:
            if not quiet:
                self.stdout.write(self.style.ERROR(f"خطا در رمزگذاری: {str(e)}"))
            logger.error(f"خطا در رمزگذاری: {str(e)}", exc_info=True)
