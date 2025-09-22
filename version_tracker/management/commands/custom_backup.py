"""
دستور پشتیبان‌گیری سفارشی بدون نیاز به mysqldump
"""
from django.core.management.base import BaseCommand
from django.db import connections
from django.conf import settings
from django.utils import timezone
import os
import json
import logging
from datetime import datetime, date, time
from decimal import Decimal

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'پشتیبان‌گیری سفارشی از هر دو دیتابیس'

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

    def handle(self, *args, **options):
        database = options['database']
        format_type = options['format']
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        
        # ایجاد پوشه backups اگر وجود ندارد
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            if database in ['main', 'both']:
                self.backup_database('default', 'main', timestamp, backup_dir, format_type)
            
            if database in ['logs', 'both']:
                self.backup_database('tankhah_logs_db', 'logs', timestamp, backup_dir, format_type)
            
            self.stdout.write(self.style.SUCCESS("پشتیبان‌گیری سفارشی تکمیل شد!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"خطا در پشتیبان‌گیری: {str(e)}"))
            logger.error(f"خطا در پشتیبان‌گیری: {str(e)}", exc_info=True)

    def backup_database(self, db_alias, db_name, timestamp, backup_dir, format_type):
        """پشتیبان‌گیری از یک دیتابیس"""
        self.stdout.write(f"پشتیبان‌گیری از دیتابیس {db_name}...")
        
        connection = connections[db_alias]
        
        if format_type == 'json':
            self.backup_to_json(connection, db_name, timestamp, backup_dir)
        else:
            self.backup_to_sql(connection, db_name, timestamp, backup_dir)

    def backup_to_json(self, connection, db_name, timestamp, backup_dir):
        """پشتیبان‌گیری به فرمت JSON"""
        backup_data = {}
        
        with connection.cursor() as cursor:
            # دریافت لیست جداول
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
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
        
        # ذخیره فایل JSON
        backup_file = os.path.join(backup_dir, f"{db_name}_{timestamp}.json")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2, default=self.json_serializer)
        
        self.stdout.write(f"فایل پشتیبان ایجاد شد: {backup_file}")

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

    def backup_to_sql(self, connection, db_name, timestamp, backup_dir):
        """پشتیبان‌گیری به فرمت SQL"""
        sql_statements = []
        
        with connection.cursor() as cursor:
            # دریافت لیست جداول
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
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
        
        # ذخیره فایل SQL
        backup_file = os.path.join(backup_dir, f"{db_name}_{timestamp}.sql")
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sql_statements))
        
        self.stdout.write(f"فایل پشتیبان ایجاد شد: {backup_file}")
