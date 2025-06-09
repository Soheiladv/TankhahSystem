from decimal import Decimal

from django.test import TestCase

from accounts.models import CustomUser
from budgets.BudgetReturn.froms_BudgetTransferForm import BudgetTransferForm
from budgets.models import BudgetPeriod,BudgetAllocation,ProjectBudgetAllocation
from core.models import Organization,Project


# Create your tests here.
class BudgetTransferFormTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='testuser', password='testpass')
        self.org = Organization.objects.create(name='Test Org')
        self.project = Project.objects.create(name='Test Project', organization=self.org)
        self.budget_period = BudgetPeriod.objects.create(
            organization=self.org, name='Test 2025', start_date='2025-01-01',
            end_date='2025-12-31', total_amount=Decimal('1000000000'), created_by=self.user
        )
        self.budget_allocation = BudgetAllocation.objects.create(
            budget_period=self.budget_period, organization=self.org,
            allocated_amount=Decimal('50000000'), created_by=self.user
        )
        self.allocation = ProjectBudgetAllocation.objects.create(
            budget_allocation=self.budget_allocation, project=self.project,
            allocated_amount=Decimal('30000000'), created_by=self.user
        )

    def test_get_free_budget(self):
        form = BudgetTransferForm(user=self.user)
        free_budget = form._get_free_budget(self.allocation)
        self.assertEqual(free_budget, self.allocation.allocated_amount)

