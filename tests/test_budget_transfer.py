import pytest
from django.urls import reverse

from budgets.models import BudgetPeriod, BudgetItem, BudgetAllocation, BudgetTransaction
from core.models import Organization
from accounts.models import CustomUser
from django.utils import timezone


@pytest.mark.django_db
def test_small_transfer_creates_two_transactions(client):
    org = Organization.objects.create(name='Org', code='ORG')
    user = CustomUser.objects.create_superuser(username='u1', email='u1@example.com', password='p')
    client.login(username='u1', password='p')

    bp = BudgetPeriod.objects.create(
        organization=org,
        name='BP1',
        start_date=timezone.now().date(),
        end_date=timezone.now().date(),
        total_amount=1000000,
        created_by=user,
    )
    bi = BudgetItem.objects.create(budget_period=bp, organization=org, name='Item', code='ITM')

    src = BudgetAllocation.objects.create(budget_period=bp, organization=org, budget_item=bi, allocated_amount=500000, created_by=user)
    dst = BudgetAllocation.objects.create(budget_period=bp, organization=org, budget_item=bi, allocated_amount=100000, created_by=user)

    url = reverse('budget_transfer:transfer_create')
    resp = client.post(url, data={
        'source_allocation': src.id,
        'target_allocation': dst.id,
        'amount': 1000,
        'description': 't1',
    }, follow=True)

    assert resp.status_code == 200
    inc = BudgetTransaction.objects.filter(allocation=dst, transaction_type='INCREASE').count()
    dec = BudgetTransaction.objects.filter(allocation=src, transaction_type='DECREASE').count()
    assert inc >= 1
    assert dec >= 1
