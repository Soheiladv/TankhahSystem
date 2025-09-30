from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Organization, Project
from budgets.models import BudgetPeriod, BudgetItem, BudgetAllocation, BudgetTransaction


class BudgetWarningsReportTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username='admin_test', email='admin@test.local', password='pass1234'
        )
        self.client.login(username='admin_test', password='pass1234')

        self.org = Organization.objects.create(name='Org A', code='ORGA', is_active=True)
        self.project = Project.objects.create(name='Proj A', organization=self.org, is_active=True)

        self.bp = BudgetPeriod.objects.create(
            organization=self.org,
            name='Period A',
            start_date='2025-01-01',
            end_date='2025-12-31',
            total_amount=Decimal('1000000'),
            created_by=self.admin,
        )

        self.item = BudgetItem.objects.create(
            budget_period=self.bp,
            organization=self.org,
            name='Item A',
            code='ITEM-A',
            is_active=True,
        )

    def _create_allocation(self, allocated_amount=Decimal('1000'), warning_threshold=Decimal('50.00')):
        return BudgetAllocation.objects.create(
            budget_period=self.bp,
            organization=self.org,
            budget_item=self.item,
            project=self.project,
            allocated_amount=Decimal(allocated_amount),
            warning_threshold=Decimal(warning_threshold),
        )

    def _add_tx(self, allocation: BudgetAllocation, tx_type: str, amount):
        BudgetTransaction.objects.create(
            allocation=allocation,
            transaction_type=tx_type,
            amount=Decimal(amount),
            created_by=self.admin,
            description=f"{tx_type} test",
            transaction_id=f"TX-{tx_type}-{allocation.pk}-{amount}"
        )

    def test_report_empty_when_no_warnings(self):
        self._create_allocation(allocated_amount=Decimal('1000'), warning_threshold=Decimal('10.00'))
        url = reverse('budget_warning_report')
        resp = self.client.get(url)
        assert resp.status_code == 200
        assert 'هیچ هشداری یافت نشد' in resp.content.decode('utf-8')

    def test_report_shows_near_threshold_warning(self):
        allocation = self._create_allocation(allocated_amount=Decimal('1000'), warning_threshold=Decimal('50.00'))
        # مصرف 600 -> باقی‌مانده 400، آستانه 500 => نزدیک آستانه هشدار
        self._add_tx(allocation, 'CONSUMPTION', Decimal('600'))

        url = reverse('budget_warning_report')
        resp = self.client.get(url)
        assert resp.status_code == 200
        html = resp.content.decode('utf-8')
        assert 'نزدیک آستانه هشدار' in html
        # ستون‌های جدید نیز باید نمایش داده شوند
        assert 'آستانه هشدار' in html and 'باقی‌مانده' in html

    def test_report_shows_over_consumption(self):
        allocation = self._create_allocation(allocated_amount=Decimal('1000'), warning_threshold=Decimal('10.00'))
        self._add_tx(allocation, 'CONSUMPTION', Decimal('1200'))

        url = reverse('budget_warning_report')
        resp = self.client.get(url)
        assert resp.status_code == 200
        html = resp.content.decode('utf-8')
        assert 'مصرف بیش از تخصیص' in html


