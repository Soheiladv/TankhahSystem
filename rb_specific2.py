import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','BudgetsSystem.settings')
django.setup()
from django.utils import timezone
from datetime import datetime
from budgets.models import BudgetTransaction

# Fallback: remove any RETURN transactions for that date linked to a tankhah

target = datetime.strptime('2025-09-24','%Y-%m-%d').date()
qs = BudgetTransaction.objects.filter(transaction_type='RETURN', timestamp__date=target, related_tankhah__isnull=False)
count = qs.count()
ids = list(qs.values_list('id', flat=True))
qs.delete()
print('Deleted RETURN tx (linked to tankhahs) on {}: {} (ids={})'.format(target, count, ids))
