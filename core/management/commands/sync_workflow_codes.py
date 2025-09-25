from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Status, Action
from core.services.workflow import wf


class Command(BaseCommand):
    help = "Normalize Status/Action codes to canonical DB-driven values (aliases -> canonical)."

    def handle(self, *args, **options):
        fixed_status = fixed_action = 0

        with transaction.atomic():
            for s in Status.objects.select_for_update().all():
                orig = s.code or ''
                normalized = wf._normalize(orig)
                if normalized != orig:
                    s.code = normalized
                    s.save(update_fields=['code', 'updated_at'])
                    fixed_status += 1

            for a in Action.objects.select_for_update().all():
                orig = a.code or ''
                normalized = (orig or '').upper()
                if normalized != orig:
                    a.code = normalized
                    a.save(update_fields=['code', 'updated_at'])
                    fixed_action += 1

        self.stdout.write(self.style.SUCCESS(f"Statuses fixed: {fixed_status} | Actions fixed: {fixed_action}"))


