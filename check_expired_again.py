import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','BudgetsSystem.settings')
django.setup()
from django.utils import timezone
from decimal import Decimal
from budgets.models import BudgetTransaction
from tankhah.models import Tankhah

now = timezone.now()
today = now.date()
print('Now:', now)

# Count today's RETURNs
rtoday = BudgetTransaction.objects.filter(transaction_type='RETURN', timestamp__date=today).count()
print('RETURN tx today:', rtoday)

# Find expired tankhahs with remaining > 0
eligible = []
for t in Tankhah.objects.filter(is_archived=False, project_budget_allocation__isnull=False).select_related('project_budget_allocation__budget_period','organization','project'):
    bp = t.project_budget_allocation.budget_period if t.project_budget_allocation and t.project_budget_allocation.budget_period else None
    if not bp:
        continue
    if (bp.end_date and bp.end_date < today) or getattr(bp,'is_completed', False):
        remaining = t.get_remaining_budget() or Decimal('0')
        if remaining > 0:
            eligible.append((t.id, t.number, float(remaining), bp.name))

print('Eligible expired tankhahs:', len(eligible))
for tid, num, rem, bpname in eligible[:20]:
    print('- #{} {} | remaining={} | period={}'.format(tid, num, rem, bpname))
