import json
from typing import Dict

from django.core.management.base import BaseCommand
from django.db.models import Count

from core.models import Status, Action, EntityType, Transition


class Command(BaseCommand):
    help = 'گزارش خلاصه‌ای از وضعیت دیتابیس گردش‌کار و شمارش گذارها برای یک ماهیت مشخص'

    def add_arguments(self, parser):
        parser.add_argument('--entity', default='TANKHAH', help='کد ماهیت مثل TANKHAH/FACTOR/PAYMENTORDER/BUDGET')
        parser.add_argument('--organization', type=int, help='ID سازمان (اختیاری) برای محدودسازی گذارها')

    def handle(self, *args, **options):
        entity_code = (options['entity'] or 'TANKHAH').upper()
        org_id = options.get('organization')

        data: Dict[str, object] = {}
        data['counts'] = {
            'statuses': Status.objects.count(),
            'actions': Action.objects.count(),
            'entity_types': EntityType.objects.count(),
            'transitions': Transition.objects.count(),
        }

        try:
            et = EntityType.objects.get(code=entity_code)
        except EntityType.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'EntityType not found: {entity_code}'))
            et = None

        if et:
            qs = Transition.objects.filter(entity_type=et)
            if org_id:
                qs = qs.filter(organization_id=org_id)
            rollup = qs.values('from_status__code', 'action__code', 'to_status__code').annotate(n=Count('id')).order_by()
            data['transitions_rollup'] = list(rollup)

        self.stdout.write(json.dumps(data, ensure_ascii=False, indent=2))


