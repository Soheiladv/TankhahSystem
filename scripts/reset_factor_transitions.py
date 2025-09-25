#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
    import django
    django.setup()

    from core.models import Transition, EntityType

    scope = (sys.argv[1] if len(sys.argv) > 1 else '').strip()
    et = EntityType.objects.filter(code='FACTOR').first()
    if not et:
        print('❌ EntityType FACTOR not found')
        return

    qs = Transition.objects.filter(entity_type=et)
    if scope.isdigit():
        qs = qs.filter(organization_id=int(scope))
        print(f'⚠️ Scoped reset to organization_id={scope}')
    total = qs.count()
    qs.delete()
    print(f'✅ Deleted {total} Transition(s) for FACTOR')


if __name__ == '__main__':
    main()


