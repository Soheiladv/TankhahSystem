"""
ایجاد مستقیم جداول version_tracker در دیتابیس لاگ
"""
from django.core.management.base import BaseCommand
from django.db import connections
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'ایجاد مستقیم جداول version_tracker در دیتابیس لاگ'

    def handle(self, *args, **options):
        logs_db = connections['tankhah_logs_db']
        
        # SQL برای ایجاد جداول
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS version_tracker_appversion (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                app_name VARCHAR(100) NOT NULL,
                version_number VARCHAR(20) NOT NULL,
                version_type VARCHAR(10) NOT NULL,
                release_date DATETIME(6) NOT NULL,
                code_hash VARCHAR(64) NOT NULL,
                changed_files JSON NOT NULL,
                system_info JSON NOT NULL,
                author_id BIGINT NOT NULL,
                major INT UNSIGNED NOT NULL DEFAULT 0,
                minor INT UNSIGNED NOT NULL DEFAULT 0,
                patch INT UNSIGNED NOT NULL DEFAULT 0,
                build INT UNSIGNED NOT NULL DEFAULT 0,
                previous_version_id BIGINT NULL,
                is_final BOOLEAN NOT NULL DEFAULT FALSE,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                INDEX idx_app_name (app_name),
                INDEX idx_version_number (version_number),
                INDEX idx_release_date (release_date),
                UNIQUE KEY unique_version (app_name, major, minor, patch, build)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS version_tracker_filehash (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                app_version_id BIGINT NOT NULL,
                file_path VARCHAR(255) NOT NULL,
                hash_value VARCHAR(64) NOT NULL,
                timestamp DATETIME(6) NOT NULL,
                INDEX idx_app_version (app_version_id),
                INDEX idx_timestamp (timestamp),
                UNIQUE KEY unique_file_version (app_version_id, file_path)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS version_tracker_codechangelog (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                version_id BIGINT NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                change_type VARCHAR(20) NOT NULL,
                change_date DATETIME(6) NOT NULL,
                INDEX idx_version (version_id),
                INDEX idx_change_date (change_date),
                UNIQUE KEY unique_version_file (version_id, file_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS version_tracker_finalversion (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                version_number VARCHAR(20) NOT NULL,
                release_date DATETIME(6) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                INDEX idx_release_date (release_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS version_tracker_finalversion_app_versions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                finalversion_id BIGINT NOT NULL,
                appversion_id BIGINT NOT NULL,
                UNIQUE KEY unique_final_app (finalversion_id, appversion_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS django_migrations (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                app VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                applied DATETIME(6) NOT NULL,
                UNIQUE KEY unique_app_name (app, name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        ]
        
        try:
            with logs_db.cursor() as cursor:
                for sql in sql_statements:
                    cursor.execute(sql)
                    self.stdout.write(self.style.SUCCESS("جدول ایجاد شد"))
                
                # درج migration records
                migration_records = [
                    "INSERT IGNORE INTO django_migrations (app, name, applied) VALUES ('version_tracker', '0001_initial', NOW())",
                    "INSERT IGNORE INTO django_migrations (app, name, applied) VALUES ('version_tracker', '0002_remove_codechangelog_new_code_and_more', NOW())"
                ]
                
                for sql in migration_records:
                    cursor.execute(sql)
                
                self.stdout.write(self.style.SUCCESS("جداول version_tracker در دیتابیس لاگ ایجاد شدند!"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"خطا در ایجاد جداول: {str(e)}"))
            logger.error(f"خطا در ایجاد جداول: {str(e)}", exc_info=True)
