# budgets/tests/test_budget_calculations.py
from django.db.models import Sum
from django.test import TestCase
from django.utils import timezone
from budgets.models import BudgetPeriod, BudgetAllocation, BudgetTransaction
from core.models import Organization, Project
from budgets.budget_calculations import (
    calculate_total_allocated,
    calculate_remaining_budget,
    get_budget_status,
    get_budget_details,
)
from decimal import Decimal
from datetime import date  # اضافه کردن datetime.date برای تاریخ‌ها


class BudgetCalculationsTestCase(TestCase):
    def setUp(self):
        # ایجاد داده‌های آزمایشی
        self.hq_org = Organization.objects.create(
            code="HQ001", name="دفتر مرکزی", org_type="HQ"
        )
        self.branch_org = Organization.objects.create(
            code="BR001", name="شعبه 1", org_type="COMPLEX"
        )

        self.budget_period = BudgetPeriod.objects.create(
            organization=self.hq_org,
            name="دوره 1404",
            start_date=date(2025, 1, 1),  # استفاده از شیء date
            end_date=date(2025, 12, 31),  # استفاده از شیء date
            total_amount=Decimal("100000000"),  # 100 میلیون
            locked_percentage=10,  # 10% قفل‌شده
            warning_threshold=20,  # 20% آستانه اخطار
            created_by=None
        )

        self.allocation1 = BudgetAllocation.objects.create(
            budget_period=self.budget_period,
            organization=self.branch_org,
            allocated_amount=Decimal("30000000"),  # 30 میلیون
            remaining_amount=Decimal("30000000"),
            allocation_date=date(2025, 4, 1),  # استفاده از شیء date
            created_by=None,
            status=True
        )

        self.allocation2 = BudgetAllocation.objects.create(
            budget_period=self.budget_period,
            organization=self.branch_org,
            allocated_amount=Decimal("20000000"),  # 20 میلیون
            remaining_amount=Decimal("20000000"),
            allocation_date=date(2025, 4, 2),  # استفاده از شیء date
            created_by=None,
            status=True
        )

        self.project = Project.objects.create(
            name="پروژه 1",
            code="PRJ001",
            start_date=date(2025, 1, 1),  # استفاده از شیء date
            is_active=True
        )
        self.project.organizations.add(self.branch_org)
        self.project.allocations.add(self.allocation1)

        # تراکنش برای کاهش مانده تخصیص
        BudgetTransaction.objects.create(
            allocation=self.allocation1,
            transaction_type="CONSUMPTION",
            amount=Decimal("10000000"),  # مصرف 10 میلیون
            timestamp=timezone.now(),
            created_by=None
        )

    def test_calculate_total_allocated(self):
        # تست برای کل سیستم
        total = calculate_total_allocated()
        self.assertEqual(total, Decimal("50000000"))  # 30M + 20M

        # تست برای سازمان خاص
        total_org = calculate_total_allocated(entity=self.branch_org)
        self.assertEqual(total_org, Decimal("50000000"))

        # تست برای پروژه
        total_proj = calculate_total_allocated(entity=self.project)
        self.assertEqual(total_proj, Decimal("30000000"))  # فقط allocation1

        # تست با فیلتر تاریخ
        filters = {"date_from": date(2025, 4, 2), "date_to": date(2025, 4, 2)}
        total_filtered = calculate_total_allocated(entity=self.branch_org, filters=filters)
        self.assertEqual(total_filtered, Decimal("20000000"))  # فقط allocation2

    def test_calculate_remaining_budget(self):
        # تست برای BudgetPeriod
        remaining = calculate_remaining_budget(entity=self.budget_period)
        self.assertEqual(remaining, Decimal("50000000"))  # 100M - (30M + 20M)

        # تست برای سازمان (مانده تخصیص‌ها)
        remaining_org = calculate_remaining_budget(entity=self.branch_org)
        self.assertEqual(remaining_org, Decimal("40000000"))  # 30M - 10M + 20M

        # تست برای پروژه
        remaining_proj = calculate_remaining_budget(entity=self.project)
        self.assertEqual(remaining_proj, Decimal("20000000"))  # 30M - 10M

        # تست برای کل سیستم
        remaining_system = calculate_remaining_budget()
        self.assertEqual(remaining_system, Decimal("50000000"))

    def test_get_budget_status(self):
        # تست برای BudgetPeriod
        status = get_budget_status(self.budget_period)
        self.assertEqual(status['status'], "normal")  # هنوز به اخطار نرسیده

        # تست برای سازمان
        status_org = get_budget_status(self.branch_org)
        self.assertEqual(status_org['status'], "active")
        self.assertEqual(status_org['message'], "2 تخصیص فعال از 2 کل")

        # تست برای پروژه
        status_proj = get_budget_status(self.project)
        self.assertEqual(status_proj['status'], "active")
        self.assertEqual(status_proj['message'], "1 تخصیص فعال از 1 کل")

    def get_budget_details(entity=None, filters=None):
        """
        دریافت جزئیات بودجه برای یک موجودیت یا کل سیستم.

        :param entity: Organization، Project، BudgetPeriod یا None
        :param filters: دیکشنری فیلترها
        :return: دیکشنری شامل تمام اطلاعات بودجه
        """
        if isinstance(entity, BudgetPeriod):
            total_budget = entity.total_amount
            total_allocated = calculate_total_allocated(filters={'budget_period': entity})
            remaining = entity.get_remaining_amount()

        elif isinstance(entity, Organization):
            total_budget = BudgetPeriod.objects.filter(
                allocations__organization=entity
            ).distinct().aggregate(total=Sum('total_amount'))['total'] or 0  # اضافه کردن distinct
            total_allocated = calculate_total_allocated(entity=entity, filters=filters)
            remaining = calculate_remaining_budget(entity=entity, filters=filters)

        elif isinstance(entity, Project):
            total_budget = entity.allocations.aggregate(
                total=Sum('budget_period__total_amount')
            )['total'] or 0
            total_allocated = calculate_total_allocated(entity=entity, filters=filters)
            remaining = calculate_remaining_budget(entity=entity, filters=filters)

        else:  # کل سیستم
            total_budget = BudgetPeriod.objects.aggregate(total=Sum('total_amount'))['total'] or 0
            total_allocated = calculate_total_allocated(filters=filters)
            remaining = calculate_remaining_budget(filters=filters)

        status = get_budget_status(entity, filters)
        return {
            'total_budget': total_budget,
            'total_allocated': total_allocated,
            'remaining_budget': remaining,
            'status': status['status'],
            'status_message': status['message']
        }
    def test_filters(self):
        # تست فیلتر تاریخ
        filters = {"date_from": date(2025, 4, 2)}
        total = calculate_total_allocated(self.branch_org, filters)
        self.assertEqual(total, Decimal("20000000"))

        # تست فیلتر وضعیت فعال
        self.budget_period.is_active = False
        self.budget_period.save()
        filters = {"is_active": True}
        total = calculate_total_allocated(self.branch_org, filters)
        self.assertEqual(total, Decimal("0"))