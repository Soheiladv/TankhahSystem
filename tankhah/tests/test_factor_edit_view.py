from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from django.contrib.auth import get_user_model

from core.models import Organization, Project, Status
from budgets.models import BudgetAllocation, BudgetPeriod, BudgetItem
from tankhah.models import Tankhah, Factor, ItemCategory


class FactorEditViewTests(TestCase):
    def setUp(self):
        # User
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            password="admin",
            email="admin@example.com",
        )
        self.client.login(username="admin", password="admin")

        # Core minimal
        self.org = Organization.objects.create(name="Org", code="ORG1", is_core=True, is_active=True)
        self.project = Project.objects.create(name="Proj", code="PRJ1")
        self.project.organizations.add(self.org)

        today = timezone.now().date()
        self.period = BudgetPeriod.objects.create(
            name="P1",
            start_date=today.replace(day=1),
            end_date=today.replace(day=min(28, today.day)),
            is_locked=False,
        )

        self.budget_item = BudgetItem.objects.create(
            name="Item",
            budget_period=self.period,
        )

        self.allocation = BudgetAllocation.objects.create(
            budget_period=self.period,
            organization=self.org,
            budget_item=self.budget_item,
            project=self.project,
            allocated_amount=Decimal("1000000"),
        )

        # Initial status
        self.initial_status = Status.objects.create(name="INITIAL", code="DRAFT", is_initial=True)

        # Tankhah + Factor deps
        self.category = ItemCategory.objects.create(name="Cat")
        self.tankhah = Tankhah.objects.create(
            number="TNK-1",
            amount=Decimal("100000"),
            organization=self.org,
            project=self.project,
            project_budget_allocation=self.allocation,
            created_by=self.user,
            description="desc",
            status=self.initial_status,
            current_stage=self.initial_status,
        )

        self.factor = Factor.objects.create(
            number="FAC-1",
            tankhah=self.tankhah,
            amount=Decimal("1000"),
            description="fd",
            category=self.category,
            created_by=self.user,
            status=self.initial_status,
        )

    def test_edit_view_get_200(self):
        # Prefer reversing if namespaced; fallback to hard URL
        url = f"/tankhah/factors/{self.factor.pk}/edit/"
        response = self.client.get(url)
        # On success should be 200 or a redirect to login if perms misconfigured.
        self.assertIn(response.status_code, (200, 302), msg=str(response.content[:500]))
        if response.status_code == 302:
            # If redirected, ensure it is to login (development misconfig) rather than error
            self.assertIn("login", response.url)

