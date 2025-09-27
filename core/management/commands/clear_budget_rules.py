from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import PostRuleAssignment
from tankhah.models import StageApprover


class Command(BaseCommand):
    help = "حذف امن قوانین مرتبط با بودجه (BUDGET_ALLOCATION): StageApprover و PostRuleAssignment"

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='تأیید نهایی برای حذف بدون سوال')

    def handle(self, *args, **options):
        confirm = options.get('yes')

        total_stage = StageApprover.objects.filter(entity_type='BUDGET_ALLOCATION').count()
        total_rules = PostRuleAssignment.objects.filter(entity_type='BUDGET_ALLOCATION').count()

        if not confirm:
            self.stdout.write(self.style.WARNING(
                f"این عملیات موارد زیر را حذف می‌کند:\n"
                f"- StageApprover (BUDGET_ALLOCATION): {total_stage}\n"
                f"- PostRuleAssignment (BUDGET_ALLOCATION): {total_rules}\n"
                f"برای ادامه از سوئیچ --yes استفاده کنید."
            ))
            return

        with transaction.atomic():
            deleted_stage = StageApprover.objects.filter(entity_type='BUDGET_ALLOCATION').delete()[0]
            deleted_rules = PostRuleAssignment.objects.filter(entity_type='BUDGET_ALLOCATION').delete()[0]

        self.stdout.write(self.style.SUCCESS(
            f"حذف انجام شد. StageApprover: {deleted_stage}, PostRuleAssignment: {deleted_rules}"
        ))


