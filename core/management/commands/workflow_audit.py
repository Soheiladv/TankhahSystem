from django.core.management.base import BaseCommand
from django.db.models import Count

from core.models import Transition


class Command(BaseCommand):
    help = 'گزارش گذارهای بدون allowed_posts و شمارش گذارها برای هر سازمان/ماهیت'

    def handle(self, *args, **options):
        total = Transition.objects.count()
        empty = (
            Transition.objects.annotate(num_posts=Count('allowed_posts'))
            .filter(num_posts=0)
            .count()
        )
        self.stdout.write(f"Transitions total: {total}")
        self.stdout.write(f"Transitions with empty allowed_posts: {empty}")

        self.stdout.write("جزئیات گذارهای بدون allowed_posts:")
        qs = (
            Transition.objects.annotate(num_posts=Count('allowed_posts'))
            .filter(num_posts=0)
            .select_related('organization', 'entity_type', 'from_status', 'action', 'to_status')
        )
        for tr in qs:
            self.stdout.write(
                f" - {tr.organization.code} {tr.entity_type.code}: {tr.from_status.code} --{tr.action.code}--> {tr.to_status.code}"
            )


