import os
import re
from typing import Dict, List, Set, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.models import Action, Status, EntityType, Transition


ACTION_PATTERN = re.compile(r"\b(SUBMIT|APPROVE|FINAL_APPROVE|REJECT|SIGN_PAYMENT|SEND|REGISTER)\b")
STATUS_PATTERN = re.compile(r"\b(DRAFT|PENDING_APPROVAL|SUBMITTED|IN_REVIEW|APPROVED_INTERMEDIATE|APPROVED_FINAL|APPROVED|REJECT|REJECTED|PAID)\b")
ENTITY_PATTERN = re.compile(r"\b(FACTOR|FACTORITEM|TANKHAH|BUDGET|PAYMENTORDER|REPORTS|GENERAL)\b")
CODE_FILE_EXTS = {'.py', '.html', '.txt', '.md', '.js', '.ts'}

# Alias normalization to canonical codes
STATUS_ALIASES: Dict[str, str] = {
    'SUBMITTED': 'PENDING_APPROVAL',
    'IN_REVIEW': 'PENDING_APPROVAL',
    'APPROVED_FINAL': 'APPROVED',
    'REJECT': 'REJECTED',
}


class Command(BaseCommand):
    help = 'اسکن سورس برای اکشن/وضعیت/ماهیت‌های هاردکد، گزارش اختلاف با دیتابیس و همگام‌سازی اختیاری'

    def add_arguments(self, parser):
        parser.add_argument('--root', default='.', help='ریشه اسکن سورس (پیش‌فرض: پروژه فعلی)')
        parser.add_argument('--apply', action='store_true', help='اعمال همگام‌سازی روی دیتابیس (حذف/ایجاد/نرمال‌سازی)')
        parser.add_argument('--dry-run', action='store_true', help='فقط گزارش بده')
        parser.add_argument('--list-files', action='store_true', help='نام فایل‌های اسکن‌شده را حین اجرا نمایش بده')

    def handle(self, *args, **options):
        root = options['root']
        do_apply = options['apply']
        dry_run = options['dry_run'] or not do_apply

        action_codes, status_codes, entity_codes = self.scan_source(root, list_files=options.get('list_files', False))
        status_codes = {STATUS_ALIASES.get(c, c) for c in status_codes}

        self.stdout.write(self.style.MIGRATE_HEADING('نتایج اسکن سورس'))
        self.stdout.write(f"Actions: {sorted(action_codes)}")
        self.stdout.write(f"Statuses: {sorted(status_codes)}")
        self.stdout.write(f"Entities: {sorted(entity_codes)}")

        db_actions = set(Action.objects.values_list('code', flat=True))
        db_statuses = set(Status.objects.values_list('code', flat=True))
        db_entities = set(EntityType.objects.values_list('code', flat=True))

        create_actions = action_codes - db_actions
        delete_actions = db_actions - action_codes
        create_statuses = status_codes - db_statuses
        delete_statuses = db_statuses - status_codes
        create_entities = entity_codes - db_entities
        delete_entities = db_entities - entity_codes

        self.stdout.write(self.style.MIGRATE_HEADING('گزارش اختلاف با دیتابیس'))
        self.stdout.write(f"ایجاد اکشن‌ها: {sorted(create_actions)}")
        self.stdout.write(f"حذف اکشن‌ها: {sorted(delete_actions)}")
        self.stdout.write(f"ایجاد وضعیت‌ها: {sorted(create_statuses)}")
        self.stdout.write(f"حذف وضعیت‌ها: {sorted(delete_statuses)}")
        self.stdout.write(f"ایجاد ماهیت‌ها: {sorted(create_entities)}")
        self.stdout.write(f"حذف ماهیت‌ها: {sorted(delete_entities)}")

        if dry_run:
            self.stdout.write(self.style.NOTICE('dry-run: فقط گزارش بالا اعمال شد.'))
            return

        # Prefer isolated operations to avoid broken transactions
        # Deletes/deactivations
        for code in sorted(delete_actions):
            try:
                if Transition.objects.filter(action__code=code).exists():
                    self.stdout.write(self.style.WARNING(f"رد حذف اکشن در استفاده: {code}"))
                    continue
                with transaction.atomic():
                    updated = Action.objects.filter(code=code, is_active=True).update(is_active=False)
                    if updated:
                        self.stdout.write(self.style.SUCCESS(f"غیرفعال‌سازی اکشن: {code}"))
                    else:
                        Action.objects.filter(code=code).delete()
                        self.stdout.write(self.style.SUCCESS(f"حذف اکشن: {code}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"ناتوان در حذف/غیرفعال‌سازی اکشن {code}: {e}"))

        for code in sorted(delete_statuses):
            try:
                if Transition.objects.filter(from_status__code=code).exists() or Transition.objects.filter(to_status__code=code).exists():
                    self.stdout.write(self.style.WARNING(f"رد حذف وضعیت در استفاده: {code}"))
                    continue
                with transaction.atomic():
                    updated = Status.objects.filter(code=code, is_active=True).update(is_active=False)
                    if updated:
                        self.stdout.write(self.style.SUCCESS(f"غیرفعال‌سازی وضعیت: {code}"))
                    else:
                        Status.objects.filter(code=code).delete()
                        self.stdout.write(self.style.SUCCESS(f"حذف وضعیت: {code}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"ناتوان در حذف/غیرفعال‌سازی وضعیت {code}: {e}"))

        for code in sorted(delete_entities):
            if Transition.objects.filter(entity_type__code=code).exists():
                self.stdout.write(self.style.WARNING(f"رد حذف ماهیت در استفاده: {code}"))
                continue
            try:
                with transaction.atomic():
                    EntityType.objects.filter(code=code).delete()
                    self.stdout.write(self.style.SUCCESS(f"حذف ماهیت: {code}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"ناتوان در حذف ماهیت {code}: {e}"))

        # Creates
        for code in sorted(create_entities):
            try:
                with transaction.atomic():
                    EntityType.objects.get_or_create(code=code, defaults={'name': code})
                    self.stdout.write(self.style.SUCCESS(f"ایجاد ماهیت: {code}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"ناتوان در ایجاد ماهیت {code}: {e}"))

        for code in sorted(create_statuses):
            try:
                with transaction.atomic():
                    Status.objects.get_or_create(code=code, defaults={'name': code, 'is_active': True, 'created_by_id': 1})
                    self.stdout.write(self.style.SUCCESS(f"ایجاد وضعیت: {code}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"ناتوان در ایجاد وضعیت {code}: {e}"))

        for code in sorted(create_actions):
            try:
                with transaction.atomic():
                    Action.objects.get_or_create(code=code, defaults={'name': code, 'is_active': True, 'created_by_id': 1})
                    self.stdout.write(self.style.SUCCESS(f"ایجاد اکشن: {code}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"ناتوان در ایجاد اکشن {code}: {e}"))

        self.stdout.write(self.style.SUCCESS('همگام‌سازی با سورس انجام شد.'))

    def scan_source(self, root: str, list_files: bool = False) -> Tuple[Set[str], Set[str], Set[str]]:
        actions: Set[str] = set()
        statuses: Set[str] = set()
        entities: Set[str] = set()

        for dirpath, dirnames, filenames in os.walk(root):
            # Skip virtualenvs, site-packages, caches, migrations, staticfiles
            if any(skip in dirpath for skip in (
                os.sep + 'venv', os.sep + '.venv', os.sep + 'site-packages', os.sep + '__pycache__', os.sep + 'migrations', os.sep + 'staticfiles'
            )):
                continue
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in CODE_FILE_EXTS:
                    continue
                path = os.path.join(dirpath, fn)
                if list_files:
                    try:
                        self.stdout.write(f"SCAN: {path}")
                    except Exception:
                        pass
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception:
                    continue
                actions.update(ACTION_PATTERN.findall(content))
                statuses.update(STATUS_PATTERN.findall(content))
                entities.update(ENTITY_PATTERN.findall(content))

        return actions, statuses, entities


