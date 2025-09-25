import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','BudgetsSystem.settings')
django.setup()
from django.utils import timezone
from budgets.models import BudgetPeriod
from tankhah.views_return_budget import ReturnExpiredTankhahBudgetView
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()
user = User.objects.first()
if not user:
    print('No user found'); raise SystemExit(1)

bp = BudgetPeriod.objects.filter(name__icontains='مهرماه 1404').first()
if not bp:
    print('BudgetPeriod مهرماه 1404 not found'); raise SystemExit(1)

current_date = timezone.now().date()
yesterday = current_date - timezone.timedelta(days=1)
changed = False
if bp.end_date >= yesterday:
    bp.end_date = yesterday
    bp.save(update_fields=['end_date'])
    changed = True
print(f'Period: {bp.name} | end_date: {bp.end_date} | changed: {changed}')

view = ReturnExpiredTankhahBudgetView()
expired = view._get_expired_tankhahs(user, current_date)
print(f'Expired tankhahs: {len(expired)}')
for t in expired:
    bp2 = t.project_budget_allocation.budget_period if (t.project_budget_allocation and t.project_budget_allocation.budget_period) else None
    is_exp = False
    if bp2:
        is_exp = (bp2.end_date < current_date) or bool(bp2.is_completed)
    target = 'org' if is_exp else 'project'
    rem = t.get_remaining_budget() or Decimal('0')
    print(f'- {t.number} | period_end={bp2.end_date if bp2 else None} | target={target} | remaining={rem:,.0f}')
print('Done')
