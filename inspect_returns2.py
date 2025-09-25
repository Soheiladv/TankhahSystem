import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','BudgetsSystem.settings')
django.setup()
from django.utils import timezone
from budgets.models import BudgetTransaction, BudgetAllocation, BudgetPeriod
from django.db.models import Sum
from decimal import Decimal

print('Recent RETURN transactions:')
qs = BudgetTransaction.objects.filter(transaction_type='RETURN').select_related('allocation','allocation__budget_period','related_tankhah').order_by('-timestamp')[:10]
for tx in qs:
    alloc = tx.allocation
    bp = alloc.budget_period if alloc else None
    print('- TX {} | amount={} | alloc_id={} | period={} | tankhah={}'.format(tx.transaction_id, tx.amount, alloc.id if alloc else None, bp.name if bp else None, tx.related_tankhah.number if tx.related_tankhah else None))

print('\nSample BudgetPeriod aggregates (top 5):')
for bp in BudgetPeriod.objects.all().order_by('-id')[:5]:
    total_returned = BudgetTransaction.objects.filter(allocation__budget_period=bp, transaction_type='RETURN').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    print('- {}: total_amount={} | total_allocated={} | returned_amount_field={} | returned_by_tx_agg={}'.format(bp.name, bp.total_amount, bp.total_allocated, bp.returned_amount, total_returned))

print('\nDesign note: RETURN reduces allocation and updates returned_amount; it does not create a new BudgetAllocation row automatically.')
