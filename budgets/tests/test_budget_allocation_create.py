from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import Organization, OrganizationType
from budgets.models import BudgetPeriod, BudgetItem, BudgetAllocation


class BudgetAllocationCreateViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='admin', email='admin@example.com', password='admin', is_superuser=True, is_staff=True)
        self.client.login(username='admin', password='admin')

        self.org_type = OrganizationType.objects.create(fname='Branch', org_type='BR', is_budget_allocatable=True)
        self.org = Organization.objects.create(code='B01', name='Branch 01', org_type=self.org_type, is_active=True)

        today = timezone.now().date()
        self.bp = BudgetPeriod.objects.create(
            name='مهر ماه 1404', organization=self.org, total_amount=Decimal('750000000'),
            start_date=today.replace(day=1), end_date=today.replace(day=min(28, today.day)), is_active=True
        )
        self.other_bp = BudgetPeriod.objects.create(
            name='آبان 1404', organization=self.org, total_amount=Decimal('500000000'),
            start_date=today.replace(day=1), end_date=today.replace(day=min(28, today.day)), is_active=True
        )

        self.item_bp = BudgetItem.objects.create(name='آیتم مهر', code='ITEM-MEH-001', organization=self.org, budget_period=self.bp, is_active=True)
        self.item_other = BudgetItem.objects.create(name='آیتم آبان', code='ITEM-ABN-001', organization=self.org, budget_period=self.other_bp, is_active=True)

    def test_get_form_limits_budget_items_to_period(self):
        url = reverse('budgetallocation_create') + f'?budget_period={self.bp.id}'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        ids = set(form.fields['budget_item'].queryset.values_list('id', flat=True))
        self.assertIn(self.item_bp.id, ids)
        self.assertNotIn(self.item_other.id, ids)

    def test_post_success_with_matching_period(self):
        url = reverse('budgetallocation_create') + f'?budget_period={self.bp.id}'
        payload = {
            'budget_period': str(self.bp.id),
            'budget_item': str(self.item_bp.id),
            'organization': str(self.org.id),
            'allocated_amount': '250000000',
            'allocation_type': 'amount',
            'allocation_date': '1404/07/02',
            'is_active': 'on',
            'is_stopped': '',
        }
        resp = self.client.post(url, data=payload, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(BudgetAllocation.objects.filter(budget_period=self.bp, budget_item=self.item_bp).exists())

    def test_post_error_on_mismatched_budget_item(self):
        url = reverse('budgetallocation_create') + f'?budget_period={self.bp.id}'
        payload = {
            'budget_period': str(self.bp.id),
            'budget_item': str(self.item_other.id),  # different period
            'organization': str(self.org.id),
            'allocated_amount': '100000000',
            'allocation_type': 'amount',
            'allocation_date': '1404/07/02',
            'is_active': 'on',
        }
        resp = self.client.post(url, data=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'ردیف بودجه باید متعلق به دوره بودجه انتخاب‌شده باشد', status_code=200)
        self.assertFalse(BudgetAllocation.objects.filter(budget_item=self.item_other).exists())

    def test_post_without_budget_period_is_invalid(self):
        url = reverse('budgetallocation_create')
        payload = {
            # missing budget_period
            'budget_item': str(self.item_bp.id),
            'organization': str(self.org.id),
            'allocated_amount': '100000000',
            'allocation_type': 'amount',
            'allocation_date': '1404/07/02',
            'is_active': 'on',
        }
        resp = self.client.post(url, data=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'دوره بودجه اجباری است', status_code=200)
        self.assertEqual(BudgetAllocation.objects.count(), 0)


