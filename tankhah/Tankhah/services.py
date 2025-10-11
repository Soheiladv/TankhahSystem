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
class TankhahCreationErrorـــ(Exception):
    """خطای سفارشی برای فرآیند ایجاد تنخواه."""
    pass


class TankhahCreationService____:
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




# ===== IMPORTS & DEPENDENCIES =====
from decimal import Decimal
import logging

from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from tankhah.models import Tankhah
from budgets.models import BudgetAllocation
from budgets.budget_calculations import create_budget_transaction, calculate_balance_from_transactions
from core.models import Status



# ===== EXCEPTIONS =====
class TankhahCreationError(Exception):
    """خطای سفارشی مربوط به فرآیند ایجاد تنخواه."""
    pass


# ===== CORE SERVICE =====
class TankhahCreationService:
    """
    سرویس مسئول ساخت امن یک تنخواه:
    - اعتبارسنجی ورودی
    - انتخاب تخصیص بودجه مناسب
    - ایجاد آبجکت تنخواه بدون تداخل اعتبارسنجی مدل (با فلگ _skip_validation)
    - ایجاد تراکنش‌های بودجه مرتبط
    - پاک‌سازی کش‌های مرتبط
    """
    def __init__(self, *, user, organization, project, amount, date, subproject=None, due_date=None,
                 letter_number="", description=""):
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

    # ===== Input validation =====
    def _validate_input(self):
        if not all([self.user, self.organization, self.project, self.amount, self.date]):
            raise TankhahCreationError(_("اطلاعات ضروری برای ایجاد تنخواه ناقص است (کاربر، سازمان، پروژه، مبلغ، تاریخ)."))
        if self.amount <= 0:
            raise TankhahCreationError(_("مبلغ تنخواه باید مثبت باشد."))

    # ===== Find budget allocation with enough remaining budget =====
    def _find_budget_allocation(self):
        allocations = BudgetAllocation.objects.filter(
            project=self.project,
            organization=self.organization,
            subproject=self.subproject,
            is_active=True
        ).order_by('id')  # اولویت دلخواه، می‌توانید بر اساس policy تغییر دهید

        for allocation in allocations:
            try:
                remaining_budget = calculate_balance_from_transactions(allocation)
            except Exception as e:
                logger.warning(f"محاسبه بودجه باقی‌مانده برای تخصیص {allocation.pk} با خطا مواجه شد: {e}")
                continue

            logger.info(f"Calculated balance for BudgetAllocation PK {allocation.pk}: {remaining_budget:,.2f}")
            if remaining_budget >= self.amount:
                self.allocation = allocation
                logger.info(f"Selected BudgetAllocation PK {allocation.pk} with remaining budget {remaining_budget:,.2f}")
                return

        raise TankhahCreationError(_("هیچ تخصیص بودجه فعالی با بودجه کافی یافت نشد."))

    # ===== Find initial status (DRAFT) =====
    def _find_initial_status(self):
        try:
            self.initial_status = Status.objects.get(is_initial=True, code='DRAFT')
        except Status.DoesNotExist:
            # سعی کن یک وضعیت اولیه‌ی دیگر پیدا کنی یا خطا ده
            self.initial_status = Status.objects.filter(is_initial=True).first()
            if not self.initial_status:
                raise TankhahCreationError(_("وضعیت اولیه 'DRAFT' یافت نشد."))
        except Status.MultipleObjectsReturned:
            # در صورت چند مقدار بودن، اولین را انتخاب کن
            self.initial_status = Status.objects.filter(is_initial=True).first()
            logger.warning("چند وضعیت اولیه 'DRAFT' یافت شد؛ اولین مورد انتخاب شد.")

    # ===== Execute service =====
    @transaction.atomic
    def execute(self):
        logger.info(f"شروع ایجاد تنخواه توسط کاربر {getattr(self.user, 'username', 'unknown')}")
        # 1) اعتبارسنجی ورودی
        self._validate_input()

        # 2) پیدا کردن تخصیص مناسب
        self._find_budget_allocation()

        # 3) پیدا کردن وضعیت اولیه
        self._find_initial_status()

        # 4) ساخت آبجکت تنخواه (اما هنوز validation مدل اجرا نخواهد شد به دلیل فلگ)
        try:
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

            # *** کلیدِ حل مشکل: جلوی اجرای clean() در save را می‌گیریم چون اعتبارسنجی کسب‌وکاری قبلاً انجام شده. ***
            new_tankhah._skip_validation = True

            # ذخیره آبجکت بدون تداخل با clean() که بودجه را دوباره حساب می‌کند
            new_tankhah.save()
            logger.info(f"تنخواه ایجاد شد: شماره={new_tankhah.number}, PK={new_tankhah.pk}")

            # 5) ایجاد تراکنش‌های بودجه (در همان تراکنش DB)
            # تراکنش مصرف از تخصیص
            create_budget_transaction(
                budget_source_obj=self.allocation,
                transaction_type='CONSUMPTION',
                amount=self.amount,
                created_by=self.user,
                description=f"تخصیص اعتبار به تنخواه شماره {new_tankhah.number}",
                trigger_obj=new_tankhah
            )

            # تراکنش تخصیص به خود تنخواه (مثلاً نگهداری مانده در حساب تنخواه)
            create_budget_transaction(
                budget_source_obj=new_tankhah,
                transaction_type='ALLOCATION',
                amount=self.amount,
                created_by=self.user,
                description=f"اعتبار اولیه تنخواه شماره {new_tankhah.number}",
                trigger_obj=self.allocation
            )

            # 6) پاک کردن کش‌های مرتبط (allocation & project)
            try:
                keys_to_delete = [
                    f"budget_allocation_balance_{self.allocation.pk}",
                    f"project_remaining_budget_{self.project.pk}_no_filters",
                    f"project_total_budget_v2_{self.project.pk}_no_filters",
                ]
                for k in keys_to_delete:
                    cache.delete(k)
                logger.info(f"کش‌های مرتبط با تخصیص {self.allocation.pk} و پروژه {self.project.pk} پاک شد.")
            except Exception as e:
                logger.warning(f"پاک‌سازی کش با خطا مواجه شد: {e}")

            # برگرداندن شیء ساخته‌شده
            return new_tankhah

        except ValidationError as ve:
            # تبدیل ValidationError دجانگو به ارور سرویس تا ویو آن را نمایش دهد
            logger.warning(f"خطای اعتبارسنجی در هنگام ساخت تنخواه: {ve}")
            raise TankhahCreationError(ve.messages if hasattr(ve, 'messages') else str(ve))

        except TankhahCreationError:
            # خطای کسب‌وکاری را دوباره پاس می‌دهیم
            raise

        except Exception as e:
            logger.error(f"خطای غیرمنتظره در TankhahCreationService: {e}", exc_info=True)
            raise TankhahCreationError(_("خطایی در ایجاد تنخواه رخ داد. لطفاً با پشتیبانی تماس بگیرید."))
