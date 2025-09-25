from django.core.management.base import BaseCommand

from core.models import Organization, Post, Transition


class Command(BaseCommand):
    help = 'برای همه سازمان‌ها allowed_posts گذارها را بر اساس پرچم‌های پست پر می‌کند'

    def add_arguments(self, parser):
        parser.add_argument('--entity', default='ALL', help='محدودسازی به یک EntityType خاص (FACTOR/BUDGET/PAYMENTORDER)')

    def handle(self, *args, **options):
        entity = options['entity'].upper() if options['entity'] else 'ALL'
        total_updates = 0
        for org in Organization.objects.filter(is_active=True):
            posts = Post.objects.filter(organization=org, is_active=True)
            # نگاشت پرچم نهایی
            finals_by_entity = {
                'FACTOR': set(posts.filter(can_final_approve_factor=True).values_list('id', flat=True)),
                'BUDGET': set(posts.filter(can_final_approve_budget=True).values_list('id', flat=True)),
                'PAYMENTORDER': set(posts.filter(can_final_approve_factor=True).values_list('id', flat=True)),
            }
            all_post_ids = set(posts.values_list('id', flat=True))

            qs = Transition.objects.filter(organization=org, is_active=True)
            if entity != 'ALL':
                qs = qs.filter(entity_type__code=entity)

            for tr in qs.select_related('entity_type', 'from_status', 'to_status', 'action'):
                et = tr.entity_type.code
                # اگر اقدام FINAL_APPROVE است: فقط پست‌های نهایی همان ماهیت
                if tr.action.code == 'FINAL_APPROVE':
                    final_ids = finals_by_entity.get(et, set())
                    tr.allowed_posts.set(list(final_ids))
                    total_updates += 1
                else:
                    # سایر اقدامات: همه پست‌های فعال سازمان
                    tr.allowed_posts.set(list(all_post_ids))
                    total_updates += 1

        self.stdout.write(self.style.SUCCESS(f'به‌روزرسانی allowed_posts انجام شد: {total_updates} گذار'))


