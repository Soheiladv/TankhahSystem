import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','BudgetsSystem.settings')
django.setup()
from django.utils import timezone
from django.db import transaction
from budgets.models import BudgetTransaction, BudgetPeriod
from decimal import Decimal
from django.db.models import Sum
from tankhah.models import Tankhah

now = timezone.now()
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

desc_marker = 'بازگشت مانده بودجه تنخواه منقضی'
qs = BudgetTransaction.objects.filter(transaction_type='RETURN', timestamp__gte=today_start, description__icontains=desc_marker)
count = qs.count()
print(f'Found {count} RETURN transactions to rollback')
rolled = 0
with transaction.atomic():
    for tx in qs.select_related('allocation','related_tankhah','allocation__budget_period'):
        alloc = tx.allocation
        amt = tx.amount or Decimal('0')
        if not alloc:
            continue
        # restore allocation fields
        alloc.allocated_amount = (alloc.allocated_amount or Decimal('0')) + amt
        alloc.returned_amount = max((alloc.returned_amount or Decimal('0')) - amt, Decimal('0'))
        alloc.save(update_fields=['allocated_amount','returned_amount'])

        # recompute period returned_amount
        bp = alloc.budget_period
        if bp:
            total_returned = BudgetTransaction.objects.filter(allocation__budget_period=bp, transaction_type='RETURN').exclude(pk=tx.pk).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            BudgetPeriod.objects.filter(pk=bp.pk).update(returned_amount=total_returned)

        # clean tankhah description line if present
        th = tx.related_tankhah
        if th and th.description:
            lines = [ln for ln in th.description.split('\n') if desc_marker not in ln]
            th.description = '\n'.join(lines).strip()
            th.save(update_fields=['description'])

        # delete transaction
        tx.delete()
        rolled += 1
print(f'Rolled back: {rolled}')
print('DONE')
