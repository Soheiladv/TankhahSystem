import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','BudgetsSystem.settings')
django.setup()
from django.utils import timezone
from budgets.models import BudgetPeriod
from datetime import date

qs = BudgetPeriod.objects.filter(name__icontains='مهرماه 1404')
if not qs.exists():
    print('No BudgetPeriod matched')
else:
    target_date = date(2025,10,22)
    updated = qs.update(end_date=target_date, is_completed=False, is_active=True)
    for bp in qs:
        print(f'Restored: {bp.name} -> end_date={bp.end_date}, is_completed={bp.is_completed}, is_active={bp.is_active}')
print('DONE')
