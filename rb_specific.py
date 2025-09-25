import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','BudgetsSystem.settings')
django.setup()
from django.utils import timezone
from datetime import datetime
from budgets.models import BudgetTransaction

# Target date from user snapshot
target = datetime.strptime('2025-09-24','%Y-%m-%d').date()
phrase = 'بازگشت مانده بودجه تنخواه منقضی'
qs = BudgetTransaction.objects.filter(transaction_type='RETURN', timestamp__date=target, description__icontains=phrase)
count = qs.count()
ids = list(qs.values_list('id', flat=True))
qs.delete()
print('Deleted RETURN tx on {}: {} (ids={})'.format(target, count, ids))
