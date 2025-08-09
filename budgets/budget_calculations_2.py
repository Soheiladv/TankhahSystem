import logging
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum, Q, Value
from django.core.cache import cache
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from Tanbakhsystem.utils import parse_jalali_date
from core.models import Project, SubProject
from tankhah.models import Tankhah, Factor

logger = logging.getLogger('BudgetsCalculations2')

# --------------------------------------------------------------------------
# ۱. تابع هسته‌ای و اصلی برای محاسبه بودجه باقیمانده (بر اساس معماری شما)
# --------------------------------------------------------------------------
from budgets.models import BudgetAllocation, BudgetTransaction
def get_allocation_remaining_budget(allocation: BudgetAllocation) -> Decimal:
    """
    **تابع هسته‌ای جدید:** بودجه باقیمانده یک تخصیص بودجه را محاسبه می‌کند.
    این تابع منبع حقیقت برای موجودی هر تخصیص است.
    فرمول: مبلغ تخصیص یافته - (مجموع مصارف) + (مجموع بازگشت‌ها)
    """
    if not allocation or not allocation.pk:
        return Decimal('0')

    try:
        # گام اول: مبلغ اولیه تخصیص یافته را از خود آبجکت بخوان
        initial_amount = allocation.allocated_amount or Decimal('0')

        # گام دوم: تمام تراکنش‌های مصرف و بازگشت را در یک کوئری جمع بزن
        transactions_summary = BudgetTransaction.objects.filter(allocation=allocation).aggregate(
            total_consumed=Coalesce(Sum('amount', filter=Q(transaction_type='CONSUMPTION')), Value(Decimal('0'))),
            total_returned=Coalesce(Sum('amount', filter=Q(transaction_type='RETURN')), Value(Decimal('0')))
        )

        consumed = transactions_summary['total_consumed']
        returned = transactions_summary['total_returned']

        # گام سوم: محاسبه نهایی
        remaining_budget = initial_amount - consumed + returned

        logger.info(
            f"Calculated remaining budget for Allocation PK {allocation.pk}: "
            f"Initial({initial_amount}) - Consumed({consumed}) + Returned({returned}) = {remaining_budget}"
        )

        return max(remaining_budget, Decimal('0'))

    except Exception as e:
        logger.error(f"Error calculating remaining budget for Allocation PK {allocation.pk}: {e}", exc_info=True)
        return Decimal('0')


# --------------------------------------------------------------------------
# ۲. توابع عمومی و قابل استفاده (API های بودجه) - بازنویسی شده
# --------------------------------------------------------------------------

def get_tankhah_available_budget(tankhah: Tankhah) -> Decimal:
    """
    **تابع اصلی برای تنخواه:** بودجه در دسترس تنخواه را محاسبه می‌کند.
    موجودی تنخواه برابر است با مبلغ اولیه آن منهای فاکتورهای پرداخت شده.
    سپس تعهدات (فاکتورهای در انتظار) نیز از آن کسر می‌شود.
    """
    if not tankhah or not tankhah.pk:
        return Decimal('0')

    initial_amount = tankhah.amount or Decimal('0')

    # محاسبه هزینه‌های قطعی (فاکتورهای پرداخت شده)
    paid_factors_total = Factor.objects.filter(
        tankhah=tankhah,
        status__code='PAID'
    ).aggregate(total=Coalesce(Sum('amount'), Value(Decimal('0'))))['total']

    # محاسبه تعهدات (فاکتورهای در انتظار تایید یا تایید شده)
    committed_statuses = ['PENDING_APPROVAL', 'APPROVED']
    committed_factors_total = Factor.objects.filter(
        tankhah=tankhah,
        status__code__in=committed_statuses
    ).aggregate(total=Coalesce(Sum('amount'), Value(Decimal('0'))))['total']

    available_budget = initial_amount - paid_factors_total - committed_factors_total

    logger.info(
        f"Available budget for Tankhah PK {tankhah.pk}: "
        f"Initial({initial_amount}) - Paid({paid_factors_total}) - Committed({committed_factors_total}) = {available_budget}"
    )

    return max(available_budget, Decimal('0'))


# --- توابع پروژه و زیرپروژه (با استفاده از تابع هسته‌ای جدید) ---

def get_project_available_budget(project: Project) -> Decimal:
    """بودجه در دسترس کل یک پروژه را محاسبه می‌کند."""
    total_remaining_from_allocations = Decimal('0')

    # تمام تخصیص‌های فعال این پروژه را پیدا کن

    allocations = BudgetAllocation.objects.filter(project=project, is_active=True)

    # موجودی باقیمانده هر تخصیص را با هم جمع بزن
    for alloc in allocations:
        total_remaining_from_allocations += get_allocation_remaining_budget(alloc)

    return total_remaining_from_allocations


# می‌توانید تابع مشابهی برای SubProject هم بنویسید
def get_subproject_available_budget(subproject: SubProject) -> Decimal:
    total_remaining_from_allocations = Decimal('0')
    allocations = BudgetAllocation.objects.filter(subproject=subproject, is_active=True)
    for alloc in allocations:
        total_remaining_from_allocations += get_allocation_remaining_budget(alloc)
    return total_remaining_from_allocations

