# ===== CORE BUSINESS LOGIC / SERVICES (tankhah/services.py) =====

from decimal import Decimal

from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from tankhah.models import Tankhah
from core.models import   Status, EntityType
from budgets.models import BudgetAllocation
from budgets.budget_calculations import create_budget_transaction, calculate_balance_from_transactions
import logging

logger = logging.getLogger('Tankhah_service')

from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from tankhah.models import Tankhah
from core.models import Status, EntityType
from budgets.models import BudgetAllocation
from budgets.budget_calculations import create_budget_transaction, calculate_balance_from_transactions
import logging
class TankhahCreationError(Exception):
    """خطای سفارشی برای فرآیند ایجاد تنخواه."""
    pass


class TankhahCreationService:
    def __init__(self, *, user, organization, project, amount, date, subproject=None, due_date=None, letter_number="", description=""):
        self.user = user
        self.organization = organization
        self.project = project
        self.subproject = subproject
        self.amount = Decimal(amount)
        self.date = date
        self.due_date = due_date
        self.letter_number = letter_number
        self.description = description
        self.allocation = None
        self.initial_status = None

    def _validate_input(self):
        if not all([self.user, self.organization, self.project, self.amount, self.date]):
            raise TankhahCreationError(_("اطلاعات ضروری برای ایجاد تنخواه (کاربر، سازمان، پروژه، مبلغ، تاریخ) ناقص است."))
        if self.amount <= 0:
            raise TankhahCreationError(_("مبلغ تنخواه باید مثبت باشد."))

    def _find_budget_allocation(self):
        allocations = BudgetAllocation.objects.filter(
            project=self.project,
            organization=self.organization,
            subproject=self.subproject,
            is_active=True
        )
        for allocation in allocations:
            remaining_budget = calculate_balance_from_transactions(allocation)
            if remaining_budget >= self.amount:
                self.allocation = allocation
                logger.info(f"Selected BudgetAllocation PK {allocation.pk} with remaining budget {remaining_budget}")
                return
        raise TankhahCreationError(_("هیچ تخصیص بودجه فعالی با بودجه کافی یافت نشد."))

    def _check_budget(self):
        remaining_budget = calculate_balance_from_transactions(self.allocation)
        if self.amount > remaining_budget:
            raise TankhahCreationError(
                _(f"مبلغ درخواستی ({self.amount:,.0f}) بیشتر از بودجه باقیمانده تخصیص ({remaining_budget:,.0f}) است."))

    def _find_initial_status(self):
        try:
            self.initial_status = Status.objects.get(is_initial=True, code='DRAFT')
        except Status.DoesNotExist:
            raise TankhahCreationError(_("وضعیت اولیه 'DRAFT' یافت نشد."))
        except Status.MultipleObjectsReturned:
            raise TankhahCreationError(_("چند وضعیت اولیه 'DRAFT' یافت شد."))

    @transaction.atomic
    def execute(self):
        logger.info(f"Starting Tankhah creation process for user {self.user.username}")
        # 1. اعتبارسنجی‌ها
        self._validate_input()
        self._find_budget_allocation()
        # متد _check_budget دیگر لازم نیست، چون این کار در فرم انجام می‌شود. می‌توان آن را حذف کرد.
        # self._check_budget()
        self._find_initial_status()

        # 2. ایجاد آبجکت تنخواه
        new_tankhah = Tankhah(
            created_by=self.user,
            organization=self.organization,
            project=self.project,
            subproject=self.subproject,
            project_budget_allocation=self.allocation,
            amount=self.amount,
            date=self.date,
            due_date=self.due_date,
            letter_number=self.letter_number,
            description=self.description,
            status=self.initial_status,
        )
        new_tankhah.save()
        logger.info(f"Tankhah {new_tankhah.number} created with PK {new_tankhah.pk}")

        # 3. ایجاد تراکنش‌های بودجه (با منطق صحیح)
        # **تراکنش اول: مصرف از بودجه تخصیص**
        # این تراکنش به allocation لینک می‌شود.
        create_budget_transaction(
            budget_source_obj=self.allocation,
            transaction_type='CONSUMPTION',
            amount=self.amount,
            created_by=self.user,
            description=f"تخصیص اعتبار به تنخواه شماره {new_tankhah.number}",
            trigger_obj=new_tankhah
        )

        # **تراکنش دوم: واریز به حساب تنخواه**
        # این تراکنش به خود تنخواه لینک می‌شود و allocation ندارد.
        create_budget_transaction(
            budget_source_obj=new_tankhah,
            transaction_type='ALLOCATION',
            amount=self.amount,
            created_by=self.user,
            description=f"اعتبار اولیه تنخواه شماره {new_tankhah.number}",
            trigger_obj=self.allocation
        )

        # پاک کردن کش‌های مرتبط (این کار در سیگنال‌ها هم انجام می‌شود ولی اینجا هم خوب است)

        logger.debug(f"Attempting to invalidate cache for budget_allocation_balance_{self.allocation.pk}")
        cache.delete(f"budget_allocation_balance_{self.allocation.pk}")
        logger.info(f"Successfully invalidated cache for budget_allocation_balance_{self.allocation.pk}")
        # --- پایان بخش اصلاح شده ---
        return new_tankhah
