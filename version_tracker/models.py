from django.db.models import Max, Q
import sys
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import difflib
import platform
import getpass
from dataclasses import dataclass
from accounts.models import CustomUser
import logging
logger = logging.getLogger(__name__)
from django.utils.translation import gettext_lazy as _
import os
import hashlib
from django.db import models, transaction
from django.apps import apps
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache


# لیست اپهای کنترل شده برای نسخه
monitored_apps = {'tankhah', 'core', 'reports', 'budgets',   'accounts', 'version_tracker'}

@dataclass
class SystemInfo:
    os_name: str
    os_version: str
    machine: str
    processor: str
    username: str
    hostname: str

    @classmethod
    def get_current(cls) -> 'SystemInfo':
        return cls(
            os_name=platform.system(),
            os_version=platform.version(),
            machine=platform.machine(),
            processor=platform.processor(),
            username=getpass.getuser(),
            hostname=platform.node()
        )

    def to_json(self):
        return {
            'os_name': self.os_name,
            'os_version': self.os_version,
            'machine': self.machine,
            'processor': self.processor,
            'username': self.username,
            'hostname': self.hostname
        }

def get_default_author():
    user, _ = CustomUser.objects.get_or_create(username='default')
    return user

class AppVersion(models.Model):
    VERSION_TYPES = [
        ('major', 'Major'),
        ('minor', 'Minor'),
        ('patch', 'Patch'),
        ('build', 'Build'),
    ]

    app_name = models.CharField(max_length=100, db_index=True)
    version_number = models.CharField(max_length=20, db_index=True)
    version_type = models.CharField(max_length=10, choices=VERSION_TYPES)
    release_date = models.DateTimeField(default=timezone.now, db_index=True)
    code_hash = models.CharField(max_length=64)
    changed_files = models.JSONField(default=list)
    system_info = models.JSONField(default=dict)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=get_default_author)
    major = models.PositiveIntegerField(default=0)
    minor = models.PositiveIntegerField(default=0)
    patch = models.PositiveIntegerField(default=0)
    build = models.PositiveIntegerField(default=0)
    previous_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    is_final = models.BooleanField(default=False,verbose_name=_(' نسخه نهایی '))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-major', '-minor', '-patch', '-build']
        unique_together = ('app_name', 'major', 'minor', 'patch', 'build')
        verbose_name_plural = 'نسخه بندی نرم افزار'
        verbose_name = 'نسخه بندی نرم افزار'
        default_permissions = ()
        permissions = [
            ('ApplicationVersion_view','نمایش نسخه های نرم افزار'),
            ('ApplicationVersion_Update','بروزرسانی نسخه های نرم افزار'),
            ('ApplicationVersion_create','بروزرسانی نسخه های نرم افزار'),
            ('ApplicationVersion_delete','بروزرسانی نسخه های نرم افزار'),
        ]

    def __str__(self):
        return f"{self.get_app_name_fa()} v{self.version_number}"

    def get_app_name_fa(self):
        try:
            return apps.get_app_config(self.app_name).verbose_name
        except (LookupError, AttributeError):
            return self.app_name

    @classmethod
    def update_version(cls, app_path, app_name):
        """به‌روزرسانی نسخه اپلیکیشن با مدیریت کامل تغییرات"""
        current_hashes = cls.get_current_hashes(app_path)
        last_version = cls.objects.filter(app_name=app_name).order_by('-build').first()

        if not cls.has_changes(last_version, current_hashes):
            logger.info(f"No changes detected in {app_name}")
            return None

        changed_files, code_changes = cls.get_changed_files(last_version, current_hashes, app_name)
        if not changed_files:
            logger.info(f"No file changes detected for {app_name}")
            return None

        code_hash = cls.calculate_total_hash(current_hashes)
        if last_version and last_version.code_hash == code_hash:
            logger.info(f"No content changes detected for {app_name} (hash: {code_hash})")
            return None

        with transaction.atomic():
            new_version = cls(
                app_name=app_name,
                changed_files=changed_files,
                system_info=SystemInfo.get_current().to_json(),
                author=get_default_author(),
                code_hash=code_hash,
                previous_version=last_version,
            )
            new_version.save()  # ذخیره با محاسبه نسخه و نوع
            cls.create_file_hashes(new_version, current_hashes)
            cls.create_code_changes(new_version, code_changes)
            new_version.update_version_file()
            return new_version

    @classmethod
    def get_current_hashes(cls, app_path):
        """محاسبه هش فایل‌ها با کش"""
        app_name = os.path.basename(app_path)
        cache_key = f"file_hashes_{app_name}"
        cached_hashes = cache.get(cache_key)

        if cached_hashes:
            return cached_hashes

        hashes = {}
        valid_extensions = ('.py', '.html', '.js', '.css')
        excluded_dirs = ('__pycache__', 'migrations', 'static', 'staticfiles', 'venv', 'media')

        for root, _, files in os.walk(app_path):
            if any(excluded in root for excluded in excluded_dirs):
                continue
            for file in files:
                if file.endswith(valid_extensions):
                    path = os.path.join(root, file)
                    try:
                        hashes[path] = cls.calculate_hash(path)
                    except (IOError, OSError) as e:
                        logger.warning(f"Failed to hash file {path}: {str(e)}")

        if hashes:
            cache.set(cache_key, hashes, timeout=300)  # 5 دقیقه کش
        return hashes

    @staticmethod
    def calculate_hash(file_path):
        """محاسبه هش فایل"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    @staticmethod
    def calculate_total_hash(hashes):
        """محاسبه هش کل برای همه فایل‌ها"""
        combined = ''.join(sorted(hashes.values()))
        return hashlib.sha256(combined.encode()).hexdigest()

    @staticmethod
    def has_changes(last_version, current_hashes):
        """بررسی تغییرات با مقایسه هش‌ها"""
        if not last_version:
            return True
        previous_hashes = {fh.file_path: fh.hash_value for fh in last_version.filehash_set.all()}
        logger.debug(f"Previous hashes: {len(previous_hashes)}, Current hashes: {len(current_hashes)}")
        return previous_hashes != current_hashes

    @staticmethod
    def get_changed_files(last_version, current_hashes, app_name):
        """دریافت فایل‌های تغییرکرده و تغییرات کد"""
        changed_files = []
        code_changes = []

        if not last_version:
            app_path = apps.get_app_config(app_name).path
            for path in current_hashes:
                content = AppVersion._read_file_content(path)
                rel_path = os.path.relpath(path, app_path)
                changed_files.append(f"Added: {rel_path}")
                code_changes.append({
                    'file_name': rel_path,
                    'old_code': '',
                    'new_code': content
                })
            return changed_files, code_changes

        app_path = apps.get_app_config(last_version.app_name).path
        previous_hashes = {fh.file_path: fh.hash_value for fh in last_version.filehash_set.all()}

        for path in current_hashes:
            rel_path = os.path.relpath(path, app_path)
            content = AppVersion._read_file_content(path)
            if path not in previous_hashes:
                changed_files.append(f"Added: {rel_path}")
                code_changes.append({
                    'file_name': rel_path,
                    'old_code': '',
                    'new_code': content
                })
            elif current_hashes[path] != previous_hashes[path]:
                old_hash_obj = last_version.filehash_set.filter(file_path=path).first()
                old_code = old_hash_obj.content if old_hash_obj else ''
                changed_files.append(f"Modified: {rel_path}")
                code_changes.append({
                    'file_name': rel_path,
                    'old_code': old_code,
                    'new_code': content
                })

        for path in previous_hashes:
            if path not in current_hashes:
                rel_path = os.path.relpath(path, app_path)
                old_hash_obj = last_version.filehash_set.filter(file_path=path).first()
                old_code = old_hash_obj.content if old_hash_obj else ''
                changed_files.append(f"Deleted: {rel_path}")
                code_changes.append({
                    'file_name': rel_path,
                    'old_code': old_code,
                    'new_code': ''
                })

        return changed_files, code_changes

    @staticmethod
    def _read_file_content(file_path):
        """خواندن محتوای فایل با مدیریت خطا"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except (UnicodeDecodeError, IOError) as e:
            logger.warning(f"Failed to read file {file_path}: {str(e)}")
            return "[Unable to read file content]"

    def save(self, *args, **kwargs):
        """ذخیره نسخه با محاسبه نوع و شماره نسخه"""
        with transaction.atomic():
            if not self.system_info:
                self.system_info = SystemInfo.get_current().to_json()

            last_version = AppVersion.objects.filter(app_name=self.app_name).order_by('-build').first()
            if last_version and last_version.code_hash == self.code_hash:
                logger.info(f"No changes for {self.app_name} compared to {last_version.version_number}")
                return

            if last_version:
                self.version_type = self.determine_version_type(last_version, self.changed_files)
                if self.version_type == 'major':
                    self.major = last_version.major + 1
                    self.minor = 0
                    self.patch = 0
                    self.build = 0
                elif self.version_type == 'minor':
                    self.major = last_version.major
                    self.minor = last_version.minor + 1
                    self.patch = 0
                    self.build = 0
                elif self.version_type == 'patch':
                    self.major = last_version.major
                    self.minor = last_version.minor
                    self.patch = last_version.patch + 1
                    self.build = 0
                else:
                    self.major = last_version.major
                    self.minor = last_version.minor
                    self.patch = last_version.patch
                    self.build = last_version.build + 1
            else:
                self.version_type = 'major'
                self.major = 1
                self.minor = 0
                self.patch = 0
                self.build = 0

            self.version_number = f"{self.major}.{self.minor}.{self.patch}.{self.build}"
            while AppVersion.objects.filter(app_name=self.app_name, version_number=self.version_number).exists():
                self.build += 1
                self.version_number = f"{self.major}.{self.minor}.{self.patch}.{self.build}"

            super().save(*args, **kwargs)
            self.update_version_file()

    def update_version_file(self):
        """به‌روزرسانی فایل version.py"""
        app_path = apps.get_app_config(self.app_name).path
        version_file = os.path.join(app_path, 'version.py')
        content = f"VERSION = '{self.version_number}'\nVERBOSE_NAME = '{self.get_app_name_fa()}'\n"
        try:
            with open(version_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Updated version.py for {self.app_name}")
        except IOError as e:
            logger.error(f"Failed to update version.py for {self.app_name}: {str(e)}")

    @staticmethod
    def determine_version_type(last_version, changed_files):
        """تعیین نوع نسخه بر اساس تغییرات"""
        if not last_version or not changed_files:
            return 'major'
        from pathlib import Path
        file_paths = [Path(file.split(': ')[1]) for file in changed_files]
        for file_path in file_paths:
            if 'models.py' in file_path.name or 'migrations' in file_path.parts:
                return 'major'
            elif 'views.py' in file_path.name or 'forms.py' in file_path.name:
                return 'minor'
            elif file_path.suffix in ['.css', '.js', '.html']:
                return 'build'
        return 'build'

    @classmethod
    def create_file_hashes(cls, version, hashes):
        """ثبت هش‌های فایل‌ها"""
        if not version.pk:
            logger.error(f"Cannot create file hashes for unsaved version: {version}")
            return

        file_hashes = [
            FileHash(
                app_version=version,
                file_path=path,
                hash_value=hash_value,
                content=cls._read_file_content(path)
            )
            for path, hash_value in hashes.items()
        ]
        FileHash.objects.bulk_create(file_hashes, ignore_conflicts=True, batch_size=1000)

    @classmethod
    def create_code_changes(cls, version, code_changes):
        """ثبت تغییرات کد"""
        if not code_changes:
            logger.info(f"No code changes for {version}")
            return

        if not version.pk:
            logger.error(f"Cannot create code changes for unsaved version: {version}")
            return

        CodeChangeLog.objects.bulk_create([
            CodeChangeLog(
                version=version,
                file_name=change['file_name'],
                old_code=change['old_code'] or '',
                new_code=change['new_code'] or ''
            ) for change in code_changes
        ], batch_size=1000)
        logger.info(f"{len(code_changes)} code changes recorded for {version}")

    @classmethod
    def get_final_version(cls):
        return cls.objects.filter(is_final=True).order_by('-created_at').first()
#############################
class FileHash(models.Model):
    app_version = models.ForeignKey(AppVersion, on_delete=models.CASCADE)
    file_path = models.CharField(max_length=255)
    hash_value = models.CharField(max_length=64)
    content = models.TextField(blank=True, null=True)  # محتوای فایل
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('app_version', 'file_path')
        verbose_name='هش فایل'
        verbose_name_plural='هش فایل کدها'
        default_permissions = ()

    def __str__(self):
        return f"{self.file_path} - {self.hash_value}"

class CodeChangeLog(models.Model):
    version = models.ForeignKey(AppVersion, on_delete=models.CASCADE, related_name='change_logs', verbose_name='نسخه')
    file_name = models.CharField(max_length=255, verbose_name='نام فایل')
    old_code = models.TextField(verbose_name='کد قدیمی')
    new_code = models.TextField(verbose_name='کد جدید')
    change_date = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ تغییر')

    class Meta:
        unique_together = ('version', 'file_name')
        verbose_name = 'تغییر کد'
        verbose_name_plural = 'تغییرات کد'
        ordering = ['-change_date']  # مرتب‌سازی بر اساس تاریخ تغییر
        default_permissions = ()
        permissions = [
            ('CodeChangeLog_Add','افزودن تغییرات کد'),
            ('CodeChangeLog_View','نمایش تغییرات کد'),
            ('CodeChangeLog_Update','بروزرسانی تغییرات کد'),
            ('CodeChangeLog_delete','حــذف تغییرات کد'),
        ]

    def __str__(self):
        return f"{self.file_name} - {self.version.version_number}"

    def get_diff(self):
        return difflib.unified_diff(
            self.old_code.splitlines(),
            self.new_code.splitlines(),
            fromfile=f'old_{self.file_name}',
            tofile=f'new_{self.file_name}',
            lineterm=''
        )

class FinalVersion(models.Model):
    version_number = models.CharField(max_length=20, verbose_name=_("نسخه نهایی"))
    release_date = models.DateTimeField(default=timezone.now, db_index=True, verbose_name=_("تاریخ انتشار"))
    app_versions = models.ManyToManyField(AppVersion, related_name='final_versions')
    is_active = models.BooleanField(default=True)


    class Meta:
        verbose_name = _("نسخه نهایی")
        verbose_name_plural = _("نسخه‌های نهایی")
        default_permissions = ()

    def __str__(self):
        return f"{self.version_number} - {self.release_date.strftime('%Y-%m-%d')}"

    @classmethod
    def calculate_final_version(cls):
        try:
            # مرحله ۱: پیدا کردن بالاترین major
            max_major = AppVersion.objects.aggregate(max_major=Max('major'))['max_major']
            if max_major is None:
                return "0.0.0.0"
            # مرحله ۲: پیدا کردن بالاترین minor برای major یافت شده
            max_minor = AppVersion.objects.filter(major=max_major ).aggregate(max_minor=Max('minor'))['max_minor']
            # مرحله ۳: پیدا کردن بالاترین patch
            max_patch = AppVersion.objects.filter(major=max_major,minor=max_minor).aggregate(max_patch=Max('patch'))['max_patch']
            # مرحله ۴: پیدا کردن بالاترین build
            max_build = AppVersion.objects.filter(major=max_major,minor=max_minor,patch=max_patch).aggregate(max_build=Max('build'))['max_build']
            # ساخت نسخه نهایی
            version_number = f"{max_major}.{max_minor}.{max_patch}.{max_build or 0}"

            # ایجاد/به‌روزرسانی رکورد
            final_version, created = FinalVersion.objects.update_or_create(
                is_active=True,
                defaults={
                    'version_number': version_number,
                    'release_date': timezone.now()
                }
            )
            # به‌روزرسانی رابطه app_versions
            final_version.app_versions.set(
                AppVersion.objects.filter(version_number=version_number)
            )
            return version_number

        except Exception as e:
            logger.error(f"خطا در محاسبه نسخه نهایی: {str(e)}", exc_info=True)
            raise