import pymysql
import configparser
import os
import json
import subprocess
from datetime import datetime

class MySQLBackupManager:
    def __init__(self, config_file='mysql_config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.backup_dir = 'mysql_backups'
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def connect_to_mysql(self):
        """اتصال به پایگاه داده MySQL"""
        try:
            connection = pymysql.connect(
                host=self.config['mysql']['host'],
                user=self.config['mysql']['user'],
                password=self.config['mysql']['password'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return connection
        except Exception as e:
            print(f"خطا در اتصال به MySQL: {str(e)}")
            return None

    def export_users_and_privileges(self):
        """خروجی کاربران و مجوزهای آنها"""
        try:
            with self.connect_to_mysql() as connection:
                with connection.cursor() as cursor:
                    # دریافت لیست کاربران
                    cursor.execute("SELECT user, host FROM mysql.user")
                    users = cursor.fetchall()
                    
                    # تولید اسکریپت ایجاد کاربران و مجوزها
                    backup_content = "-- MySQL Users and Privileges Backup\n"
                    backup_content += f"-- Generated at: {datetime.now()}\n\n"
                    
                    for user in users:
                        username = user['user']
                        host = user['host']
                        
                        # دریافت مجوزهای کاربر
                        cursor.execute(f"SHOW GRANTS FOR '{username}'@'{host}'")
                        grants = cursor.fetchall()
                        
                        for grant in grants:
                            backup_content += grant[f"Grants for {username}@{host}"] + ";\n"
                    
                    # ذخیره در فایل
                    filename = os.path.join(self.backup_dir, f"mysql_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(backup_content)
                    
                    print(f"خروجی کاربران و مجوزها در {filename} ذخیره شد.")
                    return filename
                    
        except Exception as e:
            print(f"خطا در تولید خروجی کاربران: {str(e)}")
            return None

    def export_database_structure(self, database_name):
        """خروجی ساختار پایگاه داده"""
        try:
            filename = os.path.join(self.backup_dir, f"{database_name}_structure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
            
            command = [
                "mysqldump",
                "--host=" + self.config['mysql']['host'],
                "--user=" + self.config['mysql']['user'],
                "--password=" + self.config['mysql']['password'],
                "--no-data",
                "--routines",
                "--triggers",
                "--events",
                database_name
            ]
            
            with open(filename, 'w', encoding='utf-8') as f:
                subprocess.run(command, stdout=f, check=True)
            
            print(f"خروجی ساختار پایگاه داده {database_name} در {filename} ذخیره شد.")
            return filename
            
        except Exception as e:
            print(f"خطا در تولید خروجی ساختار: {str(e)}")
            return None

    def export_full_database(self, database_name):
        """خروجی کامل پایگاه داده"""
        try:
            filename = os.path.join(self.backup_dir, f"{database_name}_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
            
            command = [
                "mysqldump",
                "--host=" + self.config['mysql']['host'],
                "--user=" + self.config['mysql']['user'],
                "--password=" + self.config['mysql']['password'],
                "--routines",
                "--triggers",
                "--events",
                "--single-transaction",
                database_name
            ]
            
            with open(filename, 'w', encoding='utf-8') as f:
                subprocess.run(command, stdout=f, check=True)
            
            print(f"خروجی کامل پایگاه داده {database_name} در {filename} ذخیره شد.")
            return filename
            
        except Exception as e:
            print(f"خطا در تولید خروجی کامل: {str(e)}")
            return None

    def export_configuration(self):
        """خروجی تنظیمات MySQL"""
        try:
            filename = os.path.join(self.backup_dir, f"mysql_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            config_data = {
                "timestamp": str(datetime.now()),
                "global_variables": {},
                "status_variables": {}
            }
            
            with self.connect_to_mysql() as connection:
                with connection.cursor() as cursor:
                    # دریافت متغیرهای جهانی
                    cursor.execute("SHOW GLOBAL VARIABLES")
                    config_data['global_variables'] = cursor.fetchall()
                    
                    # دریافت وضعیت سرور
                    cursor.execute("SHOW GLOBAL STATUS")
                    config_data['status_variables'] = cursor.fetchall()
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            
            print(f"خروجی تنظیمات MySQL در {filename} ذخیره شد.")
            return filename
            
        except Exception as e:
            print(f"خطا در تولید خروجی تنظیمات: {str(e)}")
            return None

    def create_restore_script(self):
        """تولید اسکریپت بازگردانی"""
        try:
            filename = os.path.join(self.backup_dir, "restore_mysql.sh")
            
            script_content = """#!/bin/bash
# اسکریپت بازگردانی MySQL
# تاریخ تولید: {date}

echo "بازگردانی کاربران و مجوزها..."
mysql --host={host} --user={user} --password={password} < mysql_users_*.sql

echo "بازگردانی ساختار پایگاه داده..."
mysql --host={host} --user={user} --password={password} < dbname_structure_*.sql

echo "بازگردانی داده‌ها..."
mysql --host={host} --user={user} --password={password} < dbname_full_*.sql

echo "تنظیمات سیستم..."
# دستورات تنظیمات خاص سیستم
# mysql --host={host} --user={user} --password={password} -e "SET GLOBAL max_connections=100;"

echo "بازگردانی با موفقیت انجام شد!"
""".format(
    date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    host=self.config['mysql']['host'],
    user=self.config['mysql']['user'],
    password=self.config['mysql']['password']
)

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # اجازه اجرا دادن به فایل
            os.chmod(filename, 0o755)
            
            print(f"اسکریپت بازگردانی در {filename} ایجاد شد.")
            return filename
            
        except Exception as e:
            print(f"خطا در تولید اسکریپت بازگردانی: {str(e)}")
            return None


if __name__ == "__main__":
    # فایل پیکربندی (mysql_config.ini)
    """
    [mysql]
    host = localhost
    user = root
    password = yourpassword
    """
    
    backup_manager = MySQLBackupManager()
    
    print("در حال تولید خروجی‌های پشتیبان...")
    
    # 1. خروجی کاربران و مجوزها
    backup_manager.export_users_and_privileges()
    
    # 2. خروجی ساختار پایگاه داده (نام پایگاه داده را تغییر دهید)
    backup_manager.export_database_structure("your_database_name")
    
    # 3. خروجی کامل پایگاه داده
    backup_manager.export_full_database("your_database_name")
    
    # 4. خروجی تنظیمات MySQL
    backup_manager.export_configuration()
    
    # 5. تولید اسکریپت بازگردانی
    backup_manager.create_restore_script()
    
    print("\nتمام عملیات با موفقیت انجام شد. فایل‌های پشتیبان در دایرکتوری mysql_backups ذخیره شدند.")