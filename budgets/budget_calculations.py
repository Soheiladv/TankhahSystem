# budget_calculations.py
import logging
from decimal import Decimal
from django.db.models import Sum, Q, Value
from django.core.cache import cache
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from Tanbakhsystem.utils import parse_jalali_date
logger = logging.getLogger('BudgetsCalculations')
"""
توضیحات فایل budget_calculations.py:
ساختار: توابع به دسته‌های سازمان، پروژه، زیرپروژه، تنخواه، و فاکتور تقسیم شده‌اند.
کش: استفاده از django.core.cache برای ذخیره نتایج محاسبات و بهبود عملکرد.
فیلترهای پویا: تابع apply_filters برای اعمال فیلترهای زمانی، دوره بودجه، و وضعیت.
مدیریت تراکنش‌ها: در نظر گرفتن تراکنش‌های CONSUMPTION و RETURN در محاسبات.
فاکتورها: توابع جدید برای محاسبه بودجه فاکتورها و آیتم‌های آن‌ها.
سازگاری: استفاده از مدل‌های موجود و ادغام توابع شما (مانند get_project_remaining_budget).
"""
# === محاسبات بودجه ===
def calculate_remaining_amount(allocation, amount_field='allocated_amount', model_name='BudgetAllocation'):
    """
    محاسبه بودجه باقی‌مانده تخصیص با در نظر گرفتن تراکنش‌های مصرف و بازگشت.

    Args:
        allocation (Model): نمونه مدل BudgetAllocation
        amount_field (str): نام فیلد مقدار اولیه (پیش‌فرض: 'allocated_amount')
        model_name (str): نام مدل برای لاگ‌گذاری (پیش‌فرض: 'BudgetAllocation')

    Returns:
        Decimal: بودجه باقی‌مانده (همیشه غیرمنفی)

    Example:
        >>> alloc = BudgetAllocation.objects.get(pk=1)
        >>> remaining = calculate_remaining_amount(alloc)
        Decimal('1000.00')
    """
    try:
        from budgets.models import BudgetAllocation,BudgetTransaction
        if not isinstance(allocation, BudgetAllocation):
            logger.error(f"ورودی allocation باید BudgetAllocation باشد، دریافت شده: {type(allocation)}")
            raise ValueError(f"ورودی allocation باید BudgetAllocation باشد، دریافت شده: {type(allocation)}")

        if not hasattr(allocation, 'pk') or allocation.pk is None:
            logger.debug(f"{model_name} هنوز ذخیره نشده، بازگشت مقدار اولیه")
            initial_amount = getattr(allocation, amount_field, Decimal('0.00')) or Decimal('0.00')
            return initial_amount

        # محاسبه تراکنش‌های مصرف و بازگشت در یک کوئری
        transactions = BudgetTransaction.objects.filter(allocation=allocation).aggregate(
            consumed=Coalesce(Sum('amount', filter=Q(transaction_type='CONSUMPTION')), Decimal('0.00')),
            returned=Coalesce(Sum('amount', filter=Q(transaction_type='RETURN')), Decimal('0.00'))
        )
        consumed = transactions['consumed']
        returned = transactions['returned']
        initial_amount = getattr(allocation, amount_field, Decimal('0.00')) or Decimal('0.00')

        remaining = initial_amount - consumed + returned
        logger.debug(
            f"{model_name} {allocation.pk}: مقدار اولیه={initial_amount}, مصرف={consumed}, بازگشت={returned}, باقی‌مانده={remaining}"
        )
        return max(remaining, Decimal('0.00'))
    except Exception as e:
        logger.error(f"خطا در محاسبه بودجه باقی‌مانده برای {model_name} {getattr(allocation, 'pk', 'Unknown')}: {str(e)}", exc_info=True)
        return Decimal('0.00')
def old__calculate_remaining_amount(allocation, amount_field='allocated_amount', model_name='Allocation'):
    """
    محاسبه بودجه باقی‌مانده تخصیص با در نظر گرفتن تراکنش‌های مصرف و بازگشت.

    Args:
        allocation (Model): نمونه مدل (مانند BudgetAllocation یا BudgetAllocation)
        amount_field (str): نام فیلد مقدار اولیه (پیش‌فرض: 'allocated_amount')
        model_name (str): نام مدل برای لاگ‌گذاری (پیش‌فرض: 'Allocation')

    Returns:
        Decimal: بودجه باقی‌مانده (همیشه غیرمنفی)

    Example:
        >>> alloc = BudgetAllocation.objects.get(pk=1)
        >>> remaining = calculate_remaining_amount(alloc)
        Decimal('1000.00')
    """
    from budgets.models import BudgetTransaction,BudgetAllocation,BudgetAllocation
    try:
        # چک کردن اینکه allocation ذخیره شده
        # اگر allocation ذخیره نشده باشد، مقدار اولیه را برگردان
        if not hasattr(allocation, 'pk') or allocation.pk is None:
            logger.debug(f"{model_name} هنوز ذخیره نشده، بازگشت مقدار اولیه")
            initial_amount = getattr(allocation, amount_field, Decimal('0.00')) or Decimal('0.00')
            return initial_amount

        # تبدیل allocation به BudgetAllocation اگر BudgetAllocation باشد
        budget_allocation = allocation
        if isinstance(allocation, BudgetAllocation):
            budget_allocation = allocation.budget_allocation
            logger.debug(
                f"تبدیل BudgetAllocation {allocation.pk} به BudgetAllocation {budget_allocation.pk}")
        elif not isinstance(allocation, BudgetAllocation):
            logger.error(
                f"ورودی allocation باید BudgetAllocation یا BudgetAllocation باشد، دریافت شده: {type(allocation)}")
            raise ValueError(
                f"ورودی allocation باید BudgetAllocation یا BudgetAllocation باشد، دریافت شده: {type(allocation)}")

        # محاسبه تراکنش‌های مصرف
        consumed_qs = BudgetTransaction.objects.filter(allocation=budget_allocation, transaction_type='CONSUMPTION')
        consumed = consumed_qs.aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
        # محاسبه تراکنش‌های بازگشت
        returned_qs = BudgetTransaction.objects.filter(allocation=budget_allocation, transaction_type='RETURN')
        returned = returned_qs.aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
        # دریافت مقدار اولیه
        initial_amount = getattr(allocation, amount_field) if getattr(allocation, amount_field) is not None else Decimal('0.00')
        # محاسبه بودجه باقی‌مانده
        remaining = initial_amount - consumed + returned

        logger.debug(
            f"{model_name} {budget_allocation.pk}: مقدار اولیه={initial_amount}, مصرف={consumed}, بازگشت={returned}, باقی‌مانده={remaining}"
        )
        return max(remaining, Decimal('0.00'))
    except Exception as e:
        logger.error(f"خطا در محاسبه بودجه باقی‌مانده برای {model_name} {getattr(allocation, 'pk', 'Unknown')}: {str(e)}", exc_info=True)
        return Decimal('0.00')
def calculate_threshold_amount(base_amount, percentage):
    """
    محاسبه مقدار بر اساس درصد (برای قفل یا هشدار).
    Args:
        base_amount: مقدار پایه (مانند total_amount یا allocated_amount)
        percentage: درصد (مانند locked_percentage یا warning_threshold)
    Returns:
        Decimal: مقدار محاسبه‌شده
    """
    # return (base_amount * percentage) / Decimal('100')
    try:
        base_amount = Decimal(str(base_amount)) if base_amount is not None else Decimal('0')
        percentage = Decimal(str(percentage)) if percentage is not None else Decimal('0')
        return (base_amount * percentage) / Decimal('100')
    except (TypeError, ValueError) as e:
        logger.error(f"خطا در محاسبه آستانه: base_amount={base_amount}, percentage={percentage}, خطا={str(e)}")
        return Decimal('0')
# === تابع ارسال نوت ===
def send_notification(target, status, message, recipients_queryset):
    """
    ارسال اعلان به کاربران.
    Args:
        target: نمونه مدل (مانند BudgetPeriod یا BudgetAllocation)
        status: وضعیت اعلان
        message: پیام اعلان
        recipients_queryset: کوئری‌ست گیرندگان
    """
    try:
        if not recipients_queryset.exists():
            logger.warning(f"No recipients found for notification: {message}")
            return
        for recipient in recipients_queryset:
            from notifications.models import Notification
            Notification.objects.bulk_create([
                Notification(
                    recipient=recipient,
                    actor=target.created_by or recipient,
                    verb=status,
                    description=message,
                    target=target,
                    level=status.lower()
                ) for recipient in recipients_queryset
            ])
        logger.info(f"Notification sent to {recipients_queryset.count()} users: {message}")
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}", exc_info=True)
# === توابع عمومی ===
def apply_filters(queryset, filters=None):
    """
    اعمال فیلترهای پویا روی کوئری‌ست
    """
    # if not isinstance(filters, dict):
    #     logger.error(f"apply_filters received non-dict filters: {filters}")
    #     raise TypeError("filters must be a dictionary")
    # if 'date_from' in filters:
    #     queryset = queryset.filter(budget_allocation__allocation_date__gte=filters['date_from'])
    # if 'date_to' in filters:
    #     queryset = queryset.filter(budget_allocation__allocation_date__lte=filters['date_to'])
    # if not filters:
    #     return queryset
    # if 'date_from' in filters:
    #     date_from = parse_jalali_date(filters['date_from']) if isinstance(filters['date_from'], str) else filters['date_from']
    #     queryset = queryset.filter(allocation_date__gte=date_from)
    # if 'date_to' in filters:
    #     date_to = parse_jalali_date(filters['date_to']) if isinstance(filters['date_to'], str) else filters['date_to']
    #     queryset = queryset.filter(allocation_date__lte=date_to)
    # if 'is_active' in filters:
    #     queryset = queryset.filter(is_active=filters['is_active'])
    # if 'budget_period' in filters:
    #     queryset = queryset.filter(budget_period=filters['budget_period'])
    # logger.debug(f"Applied filters {filters} to queryset, resulting count: {queryset.count()}")
    # return queryset
    if not filters:
        return queryset
    try:
        if 'date_from' in filters:
            date_from = parse_jalali_date(filters['date_from']) if isinstance(filters['date_from'], str) else filters[
                'date_from']
            queryset = queryset.filter(Q(allocation_date__gte=date_from) | Q(timestamp__date__gte=date_from))
        if 'date_to' in filters:
            date_to = parse_jalali_date(filters['date_to']) if isinstance(filters['date_to'], str) else filters[
                'date_to']
            queryset = queryset.filter(Q(allocation_date__lte=date_to) | Q(timestamp__date__lte=date_to))
        if 'is_active' in filters:
            queryset = queryset.filter(is_active=filters['is_active'])
        if 'budget_period' in filters:
            queryset = queryset.filter(budget_period=filters['budget_period'])
        logger.debug(f"فیلترهای اعمال‌شده: {filters}, تعداد نتایج: {queryset.count()}")
        return queryset
    except Exception as e:
        logger.error(f"خطا در اعمال فیلترها: {filters}, خطا={str(e)}")
        return queryset
    # === توابع بودجه سازمان ===
def get_organization_total_budget(organization, filters=None):
    """
       محاسبه بودجه کل تخصیص‌یافته به سازمان بر اساس دوره‌های بودجه فعال.
       Args:
           organization: نمونه مدل Organization
           filters (dict): دیکشنری فیلترهای اختیاری
       Returns:
           Decimal: بودجه کل
       """
    from budgets.models import BudgetPeriod
    try:
        queryset = BudgetPeriod.objects.filter(organization=organization, is_active=True, is_completed=False)
        if filters:
            queryset = apply_filters(queryset, filters)
        total_budget = queryset.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        logger.debug(f"get_organization_total_budget: organization={organization}, total={total_budget}")
        return total_budget
    except Exception as e:
        logger.error(f"خطا در محاسبه بودجه کل سازمان {organization}: {str(e)}")
        return Decimal('0')
def get_organization_budget(organization, filters=None):
    # """محاسبه بودجه کل سازمان بر اساس دوره‌های بودجه فعال.
    # """
    # from budgets.models import BudgetPeriod
    # total_budget = BudgetPeriod.objects.filter(organization=organization,is_active=True,is_completed=False).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    # return total_budget
    """
       محاسبه بودجه کل سازمان بر اساس دوره‌های بودجه فعال.
       Args:
           organization: نمونه مدل Organization
           filters (dict): دیکشنری فیلترهای اختیاری

       Returns:
           Decimal: بودجه کل
       """
    return get_organization_total_budget(organization, filters)
def get_organization_remaining_budget(organization, filters=None):
    """
       محاسبه بودجه باقی‌مانده سازمان.
       Args:
           organization: نمونه مدل Organization
           filters (dict): دیکشنری فیلترهای اختیاری
       Returns:
           Decimal: بودجه باقی‌مانده
       """
    from budgets.models import BudgetAllocation
    try:
        total_budget = get_organization_total_budget(organization, filters)
        allocated = BudgetAllocation.objects.filter(organization=organization)
        if filters:
            allocated = apply_filters(allocated, filters)
        total_allocated = allocated.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
        remaining = max(total_budget - total_allocated, Decimal('0'))
        logger.debug(f"get_organization_remaining_budget: organization={organization}, remaining={remaining}")
        return remaining
    except Exception as e:
        logger.error(f"خطا در محاسبه بودجه باقی‌مانده سازمان {organization}: {str(e)}")
        return Decimal('0')
# === توابع بودجه تنخواه ===
def get_tankhah_total_budget(tankhah, filters=None):
    """
    محاسبه بودجه کل تخصیص‌یافته به تنخواه.
    Args:
        tankhah: نمونه مدل Tankhah
        filters (dict): دیکشنری فیلترهای اختیاری
    Returns:
        Decimal: بودجه کل
    """
    try:
        total = tankhah.amount or Decimal('0')
        logger.debug(f"get_tankhah_total_budget: tankhah={tankhah.number}, total={total}")
        return total
    except Exception as e:
        logger.error(f"خطا در محاسبه بودجه کل تنخواه {tankhah.number}: {str(e)}")
        return Decimal('0')

"""    محاسبه بودجه مصرف‌شده تنخواه (بر اساس فاکتورهای پرداخت‌شده)"""
""" محاسبه بودجه باقی‌مانده تنخواه  """
def ok_old_get_tankhah_remaining_budget(tankhah, filters=None):
    """ محاسبه بودجه باقی‌مانده تنخواه  """
    cache_key = f"tankhah_remaining_budget_{tankhah.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached tankhah_remaining_budget for {cache_key}: {cached_result}")
        return cached_result

    total_budget = get_tankhah_total_budget(tankhah, filters)
    used_budget = get_tankhah_used_budget(tankhah, filters)
    remaining = max(total_budget - used_budget, Decimal('0'))
    cache.set(cache_key, remaining, timeout=300)
    logger.debug(f"get_tankhah_remaining_budget: tankhah={tankhah.number}, remaining={remaining}")
    return remaining
def get_tankhah_remaining_budget(tankhah, filters=None):
    """
    محاسبه بودجه باقی‌مانده تنخواه با استفاده از فاکتورهای پرداخت‌شده.
    Args:
        tankhah: نمونه مدل Tankhah
        filters: دیکشنری فیلترهای اختیاری (مثل date_from، date_to)
    Returns:
        Decimal: بودجه باقی‌مانده
    """
    cache_key = f"tankhah_remaining_budget_{tankhah.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached tankhah_remaining_budget for {cache_key}: {cached_result}")
        return cached_result

    try:
        if not tankhah.project_budget_allocation:  # اصلاح شده
            logger.error(f"No project_budget_allocation for tankhah {tankhah.number}")
            return Decimal('0')

        total_budget = get_tankhah_total_budget(tankhah, filters)
        logger.debug(f"get_tankhah_remaining_budget({tankhah.number}): Initial Amount = {total_budget}")

        used_budget = get_tankhah_used_budget(tankhah, filters)
        logger.debug(f"get_tankhah_remaining_budget({tankhah.number}): Used Budget (Paid Factors) = {used_budget}")

        remaining = max(total_budget - used_budget, Decimal('0'))
        logger.info(f"get_tankhah_remaining_budget({tankhah.number}): Calculated Remaining = {remaining}")

        cache.set(cache_key, remaining, timeout=300)
        logger.debug(f"get_tankhah_remaining_budget: tankhah={tankhah.number}, remaining={remaining}")
        return remaining
    except Exception as e:
        logger.error(f"Error calculating tankhah_remaining_budget for {tankhah.number}: {str(e)}", exc_info=True)
        return Decimal('0')
# === توابع بودجه پروژه ===
def old__get_project_total_budget(project, force_refresh=False, filters=None):
    """
        محاسبه مجموع بودجه تخصیص‌یافته به پروژه.
        Args:
            project: نمونه مدل Project
            force_refresh (bool): حذف کش برای محاسبه مجدد
            filters (dict): دیکشنری فیلترهای اختیاری
        Returns:
            Decimal: بودجه کل
        """
    cache_key = f"project_total_budget_{project.pk}_no_filters"
    if force_refresh:
        cache.delete(cache_key)
        logger.debug(f"کش برای {cache_key} حذف شد")
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached project_total_budget for {cache_key}: {cached_result}")
        return cached_result

    from budgets.models import BudgetAllocation
    direct_allocations = BudgetAllocation.objects.filter(
        project=project,
        subproject__isnull=True,
        budget_allocation__is_active=True
    )
    # اعمال فیلترها فقط اگر filters ارائه شده باشد
    if filters:
        direct_allocations = apply_filters(direct_allocations, filters)
    direct_total = direct_allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')

    subproject_allocations = BudgetAllocation.objects.filter(
        project=project,
        subproject__isnull=False,
        budget_allocation__is_active=True
    )
    if filters:
        subproject_allocations = apply_filters(subproject_allocations, filters)
    subproject_total = subproject_allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')

    total = direct_total + subproject_total
    cache.set(cache_key, total, timeout=300)
    logger.debug(
        f"Project {project.id} total budget: {total}, direct: {direct_total}, "
        f"subproject: {subproject_total}, direct_count: {direct_allocations.count()}, "
        f"subproject_count: {subproject_allocations.count()}"
    )
    return total
def get_project_total_budget(project, force_refresh=False, filters=None):
    """
    محاسبه مجموع بودجه تخصیص‌یافته به پروژه (با ساختار مدل BudgetAllocation جدید).

    Args:
        project: نمونه مدل Project (core.Project)
        force_refresh (bool): حذف کش برای محاسبه مجدد (پیش‌فرض: False)
        filters (dict): دیکشنری فیلترهای اختیاری که باید روی BudgetAllocation اعمال شود (پیش‌فرض: None)

    Returns:
        Decimal: بودجه کل تخصیص‌یافته به پروژه (هم مستقیم و هم از طریق زیرپروژه‌ها)
    """
    # ساخت کلید کش شامل PK پروژه و یک هش از فیلترها (اگر وجود داشته باشند)
    # هش کردن فیلترها اطمینان می‌دهد که برای فیلترهای مختلف، کش‌های متفاوتی وجود دارد.
    filter_hash = hash(frozenset(filters.items())) if filters else 'no_filters'
    cache_key = f"project_total_budget_v2_{project.pk}_{filter_hash}"

    if force_refresh:
        cache.delete(cache_key)
        logger.debug(f"کش برای {cache_key} حذف شد (force_refresh=True)")

    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached project_total_budget for {cache_key}: {cached_result}")
        return cached_result

    try:
        # BudgetAllocation حالا مستقیماً به project و subproject لینک شده است.
        # بنابراین، می‌توانیم مستقیماً روی BudgetAllocation فیلتر کنیم.
        # شامل هم تخصیص‌های مستقیم به project و هم تخصیص‌های از طریق subproject.

        # کوئری اصلی: تخصیص‌های فعال مرتبط با این پروژه
        from budgets.models import BudgetAllocation
        allocations_qs = BudgetAllocation.objects.filter(
            project=project,
            is_active=True  # فقط تخصیص‌های بودجه فعال را در نظر می‌گیرد
        )

        # اعمال فیلترهای اختیاری، اگر تابع apply_filters وجود دارد.
        if filters:
            # تابع apply_filters باید QuerySet را برگرداند.
            allocations_qs = apply_filters(allocations_qs, filters)

        # جمع‌آوری allocated_amount از تمامی تخصیص‌های فیلترشده
        total_budget = allocations_qs.aggregate(
            total=Coalesce(Sum('allocated_amount'), Decimal('0'))
        )['total']

        # ذخیره نتیجه در کش
        cache.set(cache_key, total_budget, timeout=300)  # کش به مدت 5 دقیقه

        logger.debug(
            f"Calculated project_total_budget for Project {project.id}: {total_budget} "
            f"(Total Allocations: {allocations_qs.count()})"
        )
        return total_budget

    except Exception as e:
        logger.error(f"خطا در محاسبه بودجه کل پروژه {project.id}: {str(e)}", exc_info=True)
        return Decimal('0')
def get_budget_info(request):
    project_id = request.GET.get('project_id')
    subproject_id = request.GET.get('subproject_id')
    response_data = {}

    if not project_id:
        logger.warning('project_id دریافت نشد')
        return JsonResponse({'total_budget': 0, 'remaining_budget': 0}, status=400)

    try:
        from core.models import Project, SubProject
        project_id = int(project_id)
        project = Project.objects.get(id=project_id)
        # from budgets.budget_calculations import get_project_total_budget, get_project_remaining_budget, get_subproject_total_budget, get_subproject_remaining_budget
        data = {
            'total_budget': float(get_project_total_budget(project, force_refresh=True)),
            'remaining_budget': float(get_project_remaining_budget(project, force_refresh=True))
        }
        logger.debug(f"Budget info for project {project_id}: {response_data}")

        if subproject_id:
            subproject_id = int(subproject_id)
            subproject = SubProject.objects.get(id=subproject_id)
            data['subproject_total_budget'] = float(get_subproject_total_budget(subproject))
            data['subproject_remaining_budget'] = float(get_subproject_remaining_budget(subproject))
        logger.info(f"Budget info for project {project_id}: {data}")
        return JsonResponse(data)
    except (Project.DoesNotExist, SubProject.DoesNotExist):
        logger.error(f'پروژه یا زیرپروژه یافت نشد: project_id={project_id}, subproject_id={subproject_id}')
        return JsonResponse({'total_budget': 0, 'remaining_budget': 0}, status=404)
    except Exception as e:
        logger.error(f'خطا در get_budget_info: {str(e)}')
        return JsonResponse({'total_budget': 0, 'remaining_budget': 0}, status=500)

def get_tankhah_budget_info(request):
    from tankhah.models import Tankhah
    tankhah_id = request.GET.get('tankhah_id')
    if not tankhah_id:
        logger.error("No tankhah_id provided in get_tankhah_budget_info")
        return JsonResponse({'error': 'Tankhah ID is required'}, status=400)
    try:
        # دریافت تنخواه با روابط مرتبط
        tankhah = Tankhah.objects.select_related(
            'project', 'project_budget_allocation', 'organization'
        ).get(id=tankhah_id)
        project = tankhah.project
        allocation = tankhah.project_budget_allocation

        if not allocation:
            logger.error(f"No project_budget_allocation     for tankhah {tankhah.number}")
            return JsonResponse({'error': 'No budget allocation for this tankhah'}, status=400)

        # محاسبه اطلاعات بودجه
        from budgets.models import BudgetTransaction
        budget_info = {
            'project_name': project.name if project else '-',
            'project_budget': str(get_project_total_budget(project) or Decimal('0')),
            'project_consumed': str(get_project_used_budget(project) or Decimal('0')),
            'project_returned': str(
                BudgetTransaction.objects.filter(
                    allocation__project=project,  # اصلاح شده
                    transaction_type='RETURN'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            ),
            'project_remaining': str(get_project_remaining_budget(project) or Decimal('0')),
            'tankhah_budget': str(get_tankhah_total_budget(tankhah) or Decimal('0')),
            'tankhah_consumed': str(get_tankhah_used_budget(tankhah) or Decimal('0')),
            'tankhah_remaining': str(get_tankhah_remaining_budget(tankhah) or Decimal('0')),
        }
        logger.info(f"Budget info retrieved for tankhah {tankhah.number}: {budget_info}")
        return JsonResponse(budget_info)
    except Tankhah.DoesNotExist:
        logger.error(f"Tankhah with ID {tankhah_id} not found")
        return JsonResponse({'error': 'Tankhah not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in get_tankhah_budget_info: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

""" محاسبه بودجه *واقعی* باقی‌مانده پروژه."""
def get_actual_project_remaining_budget(project, filters=None):
    """
    محاسبه بودجه *واقعی* باقی‌مانده پروژه.
    این تابع مجموع کل تخصیص یافته به پروژه (از BudgetAllocation) را محاسبه کرده
    و مجموع تراکنش‌های مصرفی (CONSUMPTION) و برگشتی (RETURN) ثبت شده در BudgetTransaction
    که به تخصیص‌های بودجه (BudgetAllocation) مرتبط با این پروژه لینک هستند را از آن کم/زیاد می‌کند.
    """
    if not project:
        logger.warning("get_actual_project_remaining_budget called with None project.")
        return Decimal('0.0')

    # استفاده از کش برای جلوگیری از محاسبات تکراری (اختیاری اما مفید)
    # کلید کش باید شامل شناسه پروژه و فیلترها باشد
    cache_key = f"actual_project_remaining_budget_{project.pk}"
    # فیلترها ممکن است کش را پیچیده کنند، فعلا بدون فیلتر در کش
    # if filters: cache_key += f"_{hash(str(filters))}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached actual_project_remaining_budget for {cache_key}: {cached_result}")
        return cached_result

    # 1. مجموع کل بودجه تخصیص یافته مستقیم به این پروژه
    #    (از تابع موجود شما استفاده می‌کنیم)
    #    توجه: اگر فیلترها روی تخصیص‌ها هم اثر دارند، آن‌ها را پاس دهید
    total_allocated_to_project = get_project_total_budget(project, filters=filters)
    # لاگ کل تخصیص یافته به پروژه
    logger.debug(f"get_actual_project_remaining_budget({project.id}): Total Allocated = {total_allocated_to_project}")

    # 2. مجموع کل مصرف‌ها (CONSUMPTION) مرتبط با این پروژه
    #    تراکنش‌هایی که به BudgetAllocation هایی لینک هستند که آن BudgetAllocation ها
    #    در BudgetAllocation های این پروژه استفاده شده‌اند.
    from budgets.models import BudgetTransaction
    consumptions_qs = BudgetTransaction.objects.filter(
        allocation__project = project, # پیوند از طریق BudgetAllocation به BudgetAllocation
        transaction_type='CONSUMPTION'
    )
    # اعمال فیلترهای زمانی بر روی تراکنش‌ها (اگر لازم است)
    # if filters:
    #     if 'date_from' in filters: consumptions_qs = consumptions_qs.filter(timestamp__date__gte=filters['date_from'])
    #     if 'date_to' in filters: consumptions_qs = consumptions_qs.filter(timestamp__date__lte=filters['date_to'])

    from django.db.models import Value
    total_consumed = consumptions_qs.aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.0'))) # استفاده از Coalesce برای مدیریت None
    )['total']
    # لاگ کل مصرف شده از BudgetTransaction
    logger.debug(f"get_actual_project_remaining_budget({project.id}): Total Consumed (via BudgetTransaction) = {total_consumed}")

    # 3. مجموع کل برگشتی‌ها (RETURN) مرتبط با این پروژه
    returns_qs = BudgetTransaction.objects.filter(
        allocation__project=project,
        transaction_type='RETURN'
    )
    # اعمال فیلترهای زمانی بر روی تراکنش‌ها (اگر لازم است)
    # if filters:
    #     # ... اعمال فیلتر ...

    total_returned = returns_qs.aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.0')))
    )['total']
    # لاگ کل برگشتی از BudgetTransaction
    logger.debug(f"get_actual_project_remaining_budget({project.id}): Total Returned (via BudgetTransaction) = {total_returned}")

    # 4. محاسبه باقیمانده نهایی
    remaining = total_allocated_to_project - total_consumed + total_returned
    actual_remaining = max(remaining, Decimal('0.0')) # باقیمانده نمی‌تواند منفی باشد

    # ذخیره نتیجه در کش برای مدت کوتاه (مثلاً ۲ دقیقه)
    cache.set(cache_key, actual_remaining, timeout=120)

    logger.info(f"Calculated actual remaining budget for Project {project.id}: Allocated={total_allocated_to_project}, Consumed={total_consumed}, Returned={total_returned}, Remaining={actual_remaining}")

    return actual_remaining
# --- اطمینان حاصل کنید که تابع get_project_total_budget در همین فایل یا قابل import است ---
# تابع get_project_total_budget شما به نظر صحیح می آید و می تواند استفاده شود.
def get_project_used_budget(project, filters=None):
    """
    محاسبه بودجه مصرف‌شده پروژه (شامل تنخواه‌ها).
    Args:
        project: نمونه مدل Project
        filters (dict): دیکشنری فیلترهای اختیاری
    Returns:
        Decimal: بودجه مصرف‌شده
    """
    from budgets.models import BudgetTransaction
    cache_key = f"project_used_budget_{project.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        # logger.debug(f"Returning cached project_used_budget for {cache_key}: {cached_result}")
        return cached_result

    # مصرف از تنخواه‌های پرداخت‌شده
    tankhah_budget = project.tankhah_set.filter(status='PAID')
    from tankhah.models import Tankhah
    tankhah_budget = Tankhah.objects.filter(project=project, status='PAID')
    if filters:
        tankhah_budget = apply_filters(tankhah_budget, filters)
    tankhah_budget = tankhah_budget.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # مصرف از زیرپروژه‌ها
    from budgets.models import BudgetAllocation
    subproject_budget = BudgetAllocation.objects.filter(project=project, subproject__isnull=False)
    if filters:
        subproject_budget = apply_filters(subproject_budget, filters)
    subproject_budget = subproject_budget.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')

    # مصرف‌های ثبت‌شده در تراکنش‌ها
    consumptions = BudgetTransaction.objects.filter(
        # allocation__project_allocations__project=project,
        allocation__project=project,
        transaction_type='CONSUMPTION'
    ).select_related('allocation')

    if filters:
        consumptions = apply_filters(consumptions, filters)
    consumptions = consumptions.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    total = tankhah_budget + subproject_budget + consumptions
    cache.set(cache_key, total, timeout=300)
    # logger.debug(f"get_project_used_budget: project={project}, tankhah={tankhah_budget}, subproject={subproject_budget}, total={total}")
    # logger.debug(f"Project {project.id} used budget: {total}")
    return total
def get_project_remaining_budget(project, force_refresh=False, filters=None):
    cache_key = f"project_remaining_budget_{project.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    if force_refresh:
        cache.delete(cache_key)
        logger.debug(f"کش برای {cache_key} حذف شد")
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached project_remaining_budget for {cache_key}: {cached_result}")
        return cached_result

    try:
        total_allocated = get_project_total_budget(project, force_refresh, filters)
        from budgets.models import BudgetAllocation, BudgetTransaction
        # تخصیص‌های مربوط به پروژه (مستقیم یا از طریق زیرپروژه)
        allocations = BudgetAllocation.objects.filter(
            project=project,
            is_active=True
        )
        if filters:
            allocations = apply_filters(allocations, filters)
        logger.debug(
            f"Project {project.id} allocations: count={allocations.count()}, "
            f"amounts={[a.allocated_amount for a in allocations]}"
        )

        # تراکنش‌های مصرف و بازگشت
        consumptions = BudgetTransaction.objects.filter(
            allocation__project=project,
            transaction_type='CONSUMPTION'
        )
        if filters:
            consumptions = apply_filters(consumptions, filters)
        consumptions_total = consumptions.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        returns = BudgetTransaction.objects.filter(
            allocation__project=project,
            transaction_type='RETURN'
        )
        if filters:
            returns = apply_filters(returns, filters)
        returns_total = returns.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        remaining = max(total_allocated - consumptions_total + returns_total, Decimal('0'))
        cache.set(cache_key, remaining, timeout=300)
        logger.debug(
            f"get_project_remaining_budget: project={project.id}, total={total_allocated}, "
            f"consumptions={consumptions_total}, returns={returns_total}, remaining={remaining}, "
            f"consumptions_count={consumptions.count()}, returns_count={returns.count()}"
        )
        return remaining
    except Exception as e:
        logger.error(f"خطا در محاسبه بودجه باقی‌مانده پروژه {project.id}: {str(e)}", exc_info=True)
        return Decimal('0')
# === توابع بودجه زیرپروژه ===
def get_subproject_total_budget(subproject, force_refresh=False, filters=None):
    """
       محاسبه بودجه کل تخصیص‌یافته به زیرپروژه.
       Args:
           subproject: نمونه مدل SubProject
           force_refresh (bool): حذف کش برای محاسبه مجدد
           filters (dict): دیکشنری فیلترهای اختیاری
       Returns:
           Decimal: بودجه کل
       """
    cache_key = f"subproject_remaining_budget_{subproject.pk}_no_filters"
    if force_refresh:
        cache.delete(cache_key)
        logger.debug(f"کش برای {cache_key} حذف شد")

    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached subproject_remaining_budget for {cache_key}: {cached_result}")
        return cached_result

    total_allocated = get_subproject_total_budget(subproject, force_refresh, filters)
    from budgets.models import BudgetTransaction
    consumptions = BudgetTransaction.objects.filter(
        allocation__project_allocations__subproject=subproject,
        transaction_type='CONSUMPTION'
    )
    consumptions_total = consumptions.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    returns = BudgetTransaction.objects.filter(
        allocation__project_allocations__subproject=subproject,
        transaction_type='RETURN'
    )
    returns_total = returns.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    remaining = max(total_allocated - consumptions_total + returns_total, Decimal('0'))
    cache.set(cache_key, remaining, timeout=300)
    logger.debug(
        f"get_subproject_remaining_budget: subproject={subproject.id}, total={total_allocated}, "
        f"consumptions={consumptions_total}, returns={returns_total}, remaining={remaining}, "
        f"consumptions_count={consumptions.count()}, returns_count={returns.count()}"
    )
    return remaining
#****************
def get_subproject_used_budget(subproject, filters=None):
    """
        محاسبه بودجه مصرف‌شده زیرپروژه.
        Args:
            subproject: نمونه مدل SubProject
            filters (dict): دیکشنری فیلترهای اختیاری
        Returns:
            Decimal: بودجه مصرف‌شده
        """
    cache_key = f"subproject_used_budget_{subproject.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached subproject_used_budget for {cache_key}: {cached_result}")
        return cached_result

    total = subproject.tankhah_set.filter(status='PAID')
    if filters:
        total = apply_filters(total, filters)
    total = total.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    cache.set(cache_key, total, timeout=300)
    logger.debug(f"get_subproject_used_budget: subproject={subproject}, total={total}")
    return total
def get_subproject_remaining_budget(subproject, force_refresh=False, filters=None):
    """
       محاسبه بودجه باقی‌مانده زیرپروژه.
       Args:
           subproject: نمونه مدل SubProject
           force_refresh (bool): حذف کش برای محاسبه مجدد
           filters (dict): دیکشنری فیلترهای اختیاری
       Returns:
           Decimal: بودجه باقی‌مانده
       """
    cache_key = f"subproject_remaining_budget_{subproject.pk}_no_filters"
    if force_refresh:
        cache.delete(cache_key)
        logger.debug(f"کش برای {cache_key} حذف شد")
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached subproject_remaining_budget for {cache_key}: {cached_result}")
        return cached_result

    # total_allocated = get_subproject_total_budget(subproject, force_refresh, filters)
    # from budgets.models import BudgetTransaction
    # consumptions = BudgetTransaction.objects.filter(
    #     allocation__project_allocations__subproject=subproject,
    #     transaction_type='CONSUMPTION'
    # )
    # consumptions_total = consumptions.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    #
    # returns = BudgetTransaction.objects.filter(
    #     allocation__project_allocations__subproject=subproject,
    #     transaction_type='RETURN'
    # )
    # returns_total = returns.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    #
    # remaining = max(total_allocated - consumptions_total + returns_total, Decimal('0'))
    # cache.set(cache_key, remaining, timeout=300)
    # logger.debug(
    #     f"get_subproject_remaining_budget: subproject={subproject.id}, total={total_allocated}, "
    #     f"consumptions={consumptions_total}, returns={returns_total}, remaining={remaining}, "
    #     f"consumptions_count={consumptions.count()}, returns_count={returns.count()}"
    # )
    # return remaining
    try:
            from budgets.models import BudgetTransaction
            total_allocated = get_subproject_total_budget(subproject, force_refresh, filters)
            consumptions = BudgetTransaction.objects.filter(
                allocation__subproject=subproject,
                transaction_type='CONSUMPTION'
            )
            if filters:
                consumptions = apply_filters(consumptions, filters)
            consumptions_total = consumptions.aggregate(total=Sum('amount'))['total'] or Decimal('0')

            returns = BudgetTransaction.objects.filter(
                allocation__subproject=subproject,
                transaction_type='RETURN'
            )
            if filters:
                returns = apply_filters(returns, filters)
            returns_total = returns.aggregate(total=Sum('amount'))['total'] or Decimal('0')

            remaining = max(total_allocated - consumptions_total + returns_total, Decimal('0'))
            cache.set(cache_key, remaining, timeout=300)
            logger.debug(
                f"get_subproject_remaining_budget: subproject={subproject.id}, total={total_allocated}, "
                f"consumptions={consumptions_total}, returns={returns_total}, remaining={remaining}"
            )
            return remaining
    except Exception as e:
        logger.error(f"خطا در محاسبه بودجه باقی‌مانده زیرپروژه {subproject.id}: {str(e)}")
        return Decimal('0')
# === توابع بودجه تنخواه ===
def get_tankhah_used_budget(tankhah, filters=None):
    """
    محاسبه بودجه مصرف‌شده تنخواه بر اساس فاکتورهای پرداخت‌شده.
    Args:
        tankhah: نمونه مدل Tankhah
        filters: دیکشنری فیلترهای اختیاری
    Returns:
        Decimal: بودجه مصرف‌شده
    محاسبه بودجه کل تخصیص‌یافته به تنخواه
    محاسبه بودجه مصرف‌شده تنخواه (بر اساس فاکتورهای پرداخت‌شده)
    """
    from tankhah.models import Factor
    cache_key = f"tankhah_used_budget_{tankhah.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached tankhah_used_budget for {cache_key}: {cached_result}")
        return cached_result

    # **تغییر:** در نظر گرفتن وضعیت‌های بیشتر برای مصرف موقت
    try:
        statuses_considered_as_used = ['PAID', 'APPROVED', 'PENDING', 'DRAFT']
        # factors = Factor.objects.filter(tankhah=tankhah, status__in=statuses_considered_as_used)
        factors = Factor.objects.filter(tankhah=tankhah, status__in=statuses_considered_as_used).exclude(status='REJECTED')
        # factors = Factor.objects.filter(tankhah=tankhah, status='PAID')
        if filters:
            factors = apply_filters(factors, filters)
        total = factors.aggregate(total=Coalesce(Sum('amount'), Value(Decimal('0'))))['total'] or Decimal('0')
        cache.set(cache_key, total, timeout=300)
        logger.debug(f"get_tankhah_used_budget: tankhah={tankhah.number}, total={total}")
        return total if total is not None else Decimal('0')
    except Exception as e:
            logger.error(f"خطا در محاسبه بودجه مصرف‌شده تنخواه {tankhah.number}: {str(e)}")
            return Decimal('0')
#----
def check_tankhah_lock_status(tankhah):
    """
    بررسی و به‌روزرسانی وضعیت قفل تنخواه.
    Args:
        tankhah: نمونه مدل Tankhah
    Returns:
        tuple: (bool, str) - وضعیت قفل و پیام
    """
    try:
        if not tankhah.budget_allocation:
            logger.error(f"هیچ تخصیص بودجه‌ای برای تنخواه {tankhah.code} وجود ندارد")
            return True, _("تنخواه به دلیل عدم وجود تخصیص بودجه غیرفعال است.")
        if tankhah.budget_allocation.budget_period.is_locked or tankhah.budget_allocation.is_locked:
            tankhah.is_active = False
            tankhah.save(update_fields=['is_active'])
            return True, _("تنخواه به دلیل قفل شدن تخصیص یا دوره غیرفعال شد.")
        return False, _("تنخواه فعال است.")
    except Exception as e:
        logger.error(f"خطا در بررسی وضعیت قفل تنخواه {tankhah.code}: {str(e)}")
        return True, _("خطا در بررسی وضعیت قفل تنخواه.")

def old__check_tankhah_lock_status(self):
    """
    اگر BudgetPeriod, BudgetAllocation, یا BudgetAllocation قفل شوند (مثلاً به دلیل lock_condition یا warning_action):
        تنخواه‌های مرتبط نیز قفل می‌شوند (مثلاً با تنظیم is_active=False در Tankhah).
        تراکنش‌های جدید (مثل مصرف یا برگشت) در تنخواه محدود می‌شوند.
        متد پیشنهادی برای قفل کردن تنخواه
    """
    if self.allocation.budget_period.is_locked or self.allocation.is_locked:
        self.is_active = False
        self.save(update_fields=['is_active'])
        return True, _("تنخواه به دلیل قفل شدن تخصیص یا دوره غیرفعال شد.")
    return False, _("تنخواه فعال است.")
# === توابع بودجه فاکتور ===
def get_factor_total_budget(factor, filters=None):
    """
     محاسبه بودجه کل فاکتور.
    Args:
        factor: نمونه مدل Factor
        filters (dict): دیکشنری فیلترهای اختیاری
    Returns:
        Decimal: بودجه کل
    محاسبه بودجه کل فاکتور (مجموع آیتم‌های فاکتور)
    """
    try:
        total = factor.total_amount() or Decimal('0')
        logger.debug(f"get_factor_total_budget: factor={factor.number}, total={total}")
        return total
    except Exception as e:
        logger.error(f"خطا در محاسبه بودجه کل فاکتور {factor.number}: {str(e)}")
        return Decimal('0')
def get_factor_used_budget(factor, filters=None):
    """
    محاسبه بودجه مصرف‌شده فاکتور (آیتم‌های تأییدشده یا پرداخت‌شده).
    Args:
        factor: نمونه مدل Factor
        filters (dict): دیکشنری فیلترهای اختیاری
    Returns:
        Decimal: بودجه مصرف‌شده
    """
    cache_key = f"factor_used_budget_{factor.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached factor_used_budget for {cache_key}: {cached_result}")
        return cached_result

    try:
        total = factor.items.filter(status__in=['APPROVED', 'PAID'])
        if filters:
            total = apply_filters(total, filters)
        total = total.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        cache.set(cache_key, total, timeout=300)
        logger.debug(f"get_factor_used_budget: factor={factor.number}, total={total}")
        return total
    except Exception as e:
        logger.error(f"خطا در محاسبه بودجه مصرف‌شده فاکتور {factor.number}: {str(e)}")
        return Decimal('0')
def get_factor_remaining_budget(factor, filters=None):
    """
    محاسبه بودجه باقی‌مانده فاکتور.
    Args:
        factor: نمونه مدل Factor
        filters (dict): دیکشنری فیلترهای اختیاری
    Returns:
        Decimal: بودجه باقی‌مانده
    """
    cache_key = f"factor_remaining_budget_{factor.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached factor_remaining_budget for {cache_key}: {cached_result}")
        return cached_result

    try:
        total_budget = get_factor_total_budget(factor, filters)
        used_budget = get_factor_used_budget(factor, filters)
        remaining = max(total_budget - used_budget, Decimal('0'))
        cache.set(cache_key, remaining, timeout=300)
        logger.debug(f"get_factor_remaining_budget: factor={factor.number}, remaining={remaining}")
        return remaining
    except Exception as e:
        logger.error(f"خطا در محاسبه بودجه باقی‌مانده فاکتور {factor.number}: {str(e)}")
        return Decimal('0')
# === توابع وضعیت بودجه ===
def check_budget_status(obj, filters=None):
    """
    بررسی وضعیت بودجه برای دوره‌های بودجه.

    Args:
        obj: نمونه مدل BudgetPeriod
        filters (dict): دیکشنری فیلترهای اختیاری

    Returns:
        tuple: (status, message)
    """
    from budgets.models import BudgetPeriod
    if not isinstance(obj, BudgetPeriod):
        logger.warning(f"Invalid object type for check_budget_status: {type(obj)}")
        return 'unknown', _('وضعیت نامشخص')

    cache_key = f"budget_status_{obj.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Returning cached budget_status for {cache_key}: {cached_result}")
        return cached_result

    try:
        remaining = obj.get_remaining_amount()  # جایگزین get_organization_remaining_budget
        locked = get_locked_amount(obj)
        warning = get_warning_amount(obj)

        if not obj.is_active:
            result = 'inactive', _('دوره غیرفعال است.')
        elif obj.is_completed:
            result = 'completed', _('بودجه تمام‌شده است.')
        elif remaining <= 0 and obj.lock_condition == 'ZERO_REMAINING':
            result = 'completed', _('بودجه به صفر رسیده و تمام‌شده است.')
        elif obj.lock_condition == 'AFTER_DATE' and obj.end_date < timezone.now().date():
            result = 'locked', _('دوره به دلیل پایان تاریخ قفل شده است.')
        elif obj.lock_condition == 'MANUAL' and remaining <= locked:
            result = 'locked', _('بودجه به حد قفل‌شده رسیده است.')
        elif remaining <= warning:
            result = 'warning', _('بودجه به آستانه هشدار رسیده است.')
        else:
            result = 'normal', _('وضعیت عادی')

        cache.set(cache_key, result, timeout=300)
        logger.debug(f"check_budget_status: obj={obj}, result={result}")
        return result
    except Exception as e:
        logger.error(f"خطا در بررسی وضعیت بودجه {obj}: {str(e)}")
        return 'unknown', _('وضعیت نامشخص')
def get_budget_status(entity, filters=None):
    """
    بررسی وضعیت بودجه برای موجودیت‌های مختلف (سازمان، پروژه، زیرپروژه).
    Args:
        entity: نمونه مدل (Organization, Project, SubProject, BudgetPeriod)
        filters (dict): دیکشنری فیلترهای اختیاری
    Returns:
        dict: {'status': str, 'message': str}
    """
    cache_key = f"budget_status_{type(entity).__name__}_{entity.pk}_{hash(str(filters)) if filters else 'no_filters'}"
    cached_result = cache.get(cache_key)
    from budgets.models import BudgetPeriod, BudgetAllocation
    from core.models import Organization, Project, SubProject
    if cached_result is not None:
        logger.debug(f"Returning cached budget_status for {cache_key}: {cached_result}")
        return cached_result

    try:
        if isinstance(entity, BudgetPeriod):
            status, message = check_budget_status(entity, filters)
        elif isinstance(entity, Organization):
            allocations = BudgetAllocation.objects.filter(organization=entity)
            if filters:
                allocations = apply_filters(allocations, filters)
            if not allocations.exists():
                status, message = 'no_budget', _('هیچ بودجه‌ای تخصیص نیافته است.')
            else:
                active_count = allocations.filter(budget_period__is_active=True).count()
                status = 'active' if active_count > 0 else 'inactive'
                message = _(f"{active_count} تخصیص فعال از {allocations.count()} کل")
        elif isinstance(entity, Project):
            allocations = BudgetAllocation.objects.filter(project=entity)
            if filters:
                allocations = apply_filters(allocations, filters)
            if not allocations.exists():
                status, message = 'no_budget', _('هیچ بودجه‌ای تخصیص نیافته است.')
            else:
                active_count = allocations.filter(budget_period__is_active=True).count()
                status = 'active' if active_count > 0 else 'inactive'
                message = _(f"{active_count} تخصیص فعال از {allocations.count()} کل")
        elif isinstance(entity, SubProject):
            allocations = BudgetAllocation.objects.filter(subproject=entity)
            if filters:
                allocations = apply_filters(allocations, filters)
            if not allocations.exists():
                status, message = 'no_budget', _('هیچ بودجه‌ای تخصیص نیافته است.')
            else:
                active_count = allocations.filter(budget_period__is_active=True).count()
                status = 'active' if active_count > 0 else 'inactive'
                message = _(f"{active_count} تخصیص فعال از {allocations.count()} کل")
        else:
            status, message = 'unknown', _('وضعیت نامشخص')

        result = {'status': status, 'message': message}
        cache.set(cache_key, result, timeout=300)
        logger.debug(f"get_budget_status: entity={entity}, result={result}")
        return result
    except Exception as e:
        logger.error(f"خطا در بررسی وضعیت بودجه برای {entity}: {str(e)}")
        return {'status': 'unknown', 'message': _('وضعیت نامشخص')}
def check_and_update_lock(allocation):
    """
    چک و به‌روزرسانی وضعیت قفل برای تخصیص.
    Args:
        allocation: نمونه مدل BudgetAllocation
    """
    try:
        from budgets.models import BudgetAllocation
        from tankhah.models import Tankhah
        if not isinstance(allocation, BudgetAllocation):
            logger.error(f"ورودی allocation باید BudgetAllocation باشد، دریافت شده: {type(allocation)}")
            raise ValueError(f"ورودی allocation باید BudgetAllocation باشد")

        if allocation.budget_period.is_locked:
            allocation.is_locked = True
            allocation.is_active = False
        else:
            remaining = allocation.get_remaining_amount()
            locked_amount = allocation.get_locked_amount()
            allocation.is_locked = remaining <= locked_amount
            allocation.is_active = not allocation.is_locked

        allocation.save(update_fields=['is_locked', 'is_active'])
        if allocation.is_locked:
            Tankhah.objects.filter(budget_allocation=allocation).update(is_active=False)
        logger.debug(f"Updated lock status for BudgetAllocation {allocation.pk}: is_locked={allocation.is_locked}")
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی قفل برای BudgetAllocation {allocation.pk}: {str(e)}")
# === توابع کمکی ===
def get_locked_amount(obj):
    """
    محاسبه مقدار قفل‌شده بودجه
    """
    from budgets.models import BudgetPeriod
    if isinstance(obj, BudgetPeriod):
        return (obj.total_amount * obj.locked_percentage) / Decimal('100')
    return Decimal('0')
def get_warning_amount(obj):
    """
    محاسبه آستانه هشدار بودجه
    """
    from budgets.models import BudgetPeriod
    if isinstance(obj, BudgetPeriod):
        return (obj.total_amount * obj.warning_threshold) / Decimal('100')
    return Decimal('0')
# def calculate_allocation_percentages(allocations):
#     """
#     محاسبه درصد تخصیص بودجه
#     """
#     total_percentage = Decimal("0")
#     for allocation in allocations:
#         allocation.percentage = (
#             (allocation.allocated_amount / allocation.budget_period.total_amount * Decimal("100"))
#             if allocation.budget_period.total_amount else Decimal("0")
#         )
#         total_percentage += allocation.percentage
#     logger.debug(f"calculate_allocation_percentages: total_percentage={total_percentage}, count={len(allocations)}")
#     return total_percentage
def calculate_allocation_percentages(allocations):
    """
    محاسبه درصد تخصیص بودجه.
    Args:
        allocations: QuerySet از BudgetAllocation
    Returns:
        Decimal: مجموع درصدهای تخصیص
    """
    try:
        total_percentage = Decimal('0')
        for allocation in allocations:
            if allocation.budget_period.total_amount:
                allocation.percentage = (allocation.allocated_amount / allocation.budget_period.total_amount) * Decimal('100')
            else:
                allocation.percentage = Decimal('0')
            total_percentage += allocation.percentage
        logger.debug(f"calculate_allocation_percentages: total_percentage={total_percentage}, count={allocations.count()}")
        return total_percentage
    except Exception as e:
        logger.error(f"خطا در محاسبه درصدهای تخصیص: {str(e)}")
        return Decimal('0')
def can_delete_budget(entity):
    """
    بررسی امکان حذف بودجه.

    Args:
        entity: نمونه مدل Project یا SubProject

    Returns:
        bool: امکان حذف
    """
    try:
        from core.models import Project, SubProject
        from tankhah.models import Tankhah
        if isinstance(entity, Project):
            can_delete = not Tankhah.objects.filter(project=entity).exists() and not SubProject.objects.filter(project=entity).exists()
        elif isinstance(entity, SubProject):
            can_delete = not Tankhah.objects.filter(subproject=entity).exists()
        else:
            can_delete = False
        logger.debug(f"can_delete_budget: entity={entity}, can_delete={can_delete}")
        return can_delete
    except Exception as e:
        logger.error(f"خطا در بررسی امکان حذف بودجه برای {entity}: {str(e)}")
        return False
# def can_delete_budget(entity):
#     """
#     بررسی امکان حذف بودجه
#     """
#     from core.models import Project, SubProject
#     if isinstance(entity, Project):
#         can_delete = not entity.tankhah_set.exists() and not entity.subprojects.exists()
#     elif isinstance(entity, SubProject):
#         can_delete = not entity.tankhah_set.exists()
#     else:
#         can_delete = False
#     logger.debug(f"can_delete_budget: entity={entity}, can_delete={can_delete}")
#     return can_delete

# == تابع بازگشت بودجه
def get_returned_budgets(budget_period, entity_type='all'):
    """
    گزارش بودجه‌های برگشتی برای یک دوره بودجه.
    Args:
        budget_period: نمونه BudgetPeriod
        entity_type (str): نوع موجودیت ('all', 'BudgetAllocation')
    Returns:
        QuerySet: اطلاعات بودجه‌های برگشتی
    """
    cache_key = f"returned_budgets_{budget_period.pk}_{entity_type}"
    cached_result = cache.get(cache_key)
    from django.contrib.contenttypes.models import ContentType
    from budgets.models import BudgetHistory, BudgetAllocation
    if cached_result is not None:
        logger.debug(f"Returning cached returned budgets: {cache_key}")
        return cached_result

    try:
        content_types = []
        if entity_type == 'all':
            content_types = [ContentType.objects.get_for_model(BudgetAllocation)]
        elif entity_type == 'BudgetAllocation':
            content_types = [ContentType.objects.get_for_model(BudgetAllocation)]
        else:
            logger.warning(f"Invalid entity_type: {entity_type}")
            return BudgetHistory.objects.none()

        queryset = BudgetHistory.objects.filter(
            content_type__in=content_types,
            action='RETURN',
            content_object__budget_period=budget_period
        ).values(
            'amount',
            'details',
            'created_at',
            'created_by__username',
            'content_type__model'
        )

        cache.set(cache_key, queryset, timeout=1200)
        logger.debug(f"Cached returned budgets: {cache_key}, count={queryset.count()}")
        return queryset
    except Exception as e:
        logger.error(f"خطا در دریافت بودجه‌های برگشتی برای {budget_period}: {str(e)}")
        return BudgetHistory.objects.none()
#------------------
