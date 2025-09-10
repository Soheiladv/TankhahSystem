from django.contrib.postgres.fields import ArrayField
from django.db.models.functions import Coalesce
from django.db.models import Value, Q
import logging
from django.utils import timezone
from django.core.cache import cache

from core.models import Organization, Project, AccessRule, Post, UserPost
from tankhah.models import Factor, Tankhah, ApprovalLog, get_default_initial_status

logger = logging.getLogger(__name__)
from django.contrib.contenttypes.models import ContentType

from budgets.budget_calculations import check_budget_status, get_project_remaining_budget, calculate_remaining_amount, \
    calculate_threshold_amount, create_budget_transaction

from django.utils import timezone
from datetime import date, datetime as dt  # اصلاح وارد کردن datetime

import jdatetime
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from decimal import Decimal
from django.core.exceptions import ValidationError
from accounts.models import CustomUser


def get_current_date():
    return timezone.now().date()

""" مدل نوع بودجه """  # ------------------------------------
"""BudgetPeriod (دوره بودجه کلان):"""
class BudgetPeriod(models.Model):
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, verbose_name=_("دفتر مرکزی"),
                                     related_name='budget_periods')
    name = models.CharField(max_length=100, unique=True, verbose_name=_("نام دوره بودجه"))
    start_date = models.DateField(verbose_name=_("تاریخ شروع"))
    end_date = models.DateField(verbose_name=_("تاریخ پایان"))
    total_amount = models.DecimalField(max_digits=25, decimal_places=0, verbose_name=_("مبلغ کل"))
    total_allocated = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_("مجموع تخصیص‌ها"))
    returned_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0,
                                          verbose_name=_("مجموع بودجه برگشتی"))
    locked_percentage = models.IntegerField(default=0, verbose_name=_("درصد قفل‌شده"),
                                            help_text=_("درصد بودجه که قفل می‌شود (0-100)"))
    warning_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=10, verbose_name=_("آستانه اخطار"),
                                            help_text=_("درصدی که هشدار نمایش داده می‌شود (0-100)"))
    warning_action = models.CharField(max_length=50, choices=[('NOTIFY', _("فقط اعلان")), ('LOCK', _("قفل کردن")),
                                                              ('RESTRICT', _("محدود کردن ثبت"))], default='NOTIFY',
                                      verbose_name=_("اقدام هشدار"),
                                      help_text=_("رفتار سیستم هنگام رسیدن به آستانه هشدار"))
    allocation_phase = models.CharField(max_length=50, blank=True, verbose_name=_("فاز تخصیص"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))

    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,
                                   related_name='budget_periods_created', verbose_name=_("ایجادکننده"))

    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    is_archived = models.BooleanField(default=False, verbose_name=_("بایگانی شده"))
    is_completed = models.BooleanField(default=False, verbose_name=_("تمام‌شده"))
    lock_condition = models.CharField(max_length=50,
                                      choices=[('AFTER_DATE', _("بعد از تاریخ پایان")), ('MANUAL', _("دستی")),
                                               ('ZERO_REMAINING', _("باقی‌مانده صفر")), ], default='AFTER_DATE',
                                      verbose_name=_("شرط قفل"))

    @property
    def is_locked(self):
        """
        بررسی وضعیت قفل دوره بودجه.
        Returns:
            tuple: (bool, str) - وضعیت قفل و پیام مربوطه
        """
        try:
            if not self.is_active:
                return True, _("دوره بودجه غیرفعال است.")
            if self.is_completed:
                return True, _("دوره بودجه تمام‌شده است.")
            if self.lock_condition == 'AFTER_DATE' and self.end_date < timezone.now().date():
                return True, _("دوره بودجه به دلیل پایان تاریخ قفل شده است.")
            remaining = self.get_remaining_amount()
            locked_amount = (self.total_amount * self.locked_percentage) / Decimal('100')
            if self.lock_condition == 'MANUAL' and remaining <= locked_amount:
                return True, _("دوره بودجه به دلیل رسیدن به حد قفل، قفل شده است.")
            return False, _("دوره بودجه فعال است.")
        except Exception as e:
            logger.error(f"Error checking lock status for BudgetPeriod {self.pk}: {str(e)}", exc_info=True)
            return True, _("خطا در بررسی وضعیت قفل دوره بودجه.")

    class Meta:
        verbose_name = _("دوره بودجه")
        verbose_name_plural = _("دوره‌های بودجه")
        default_permissions = ()
        permissions = [
            ('budgetperiod_add', _("افزودن دوره بودجه")),
            ('budgetperiod_update', _("بروزرسانی دوره بودجه")),
            ('budgetperiod_view', _("نمایش دوره بودجه")),
            ('budgetperiod_delete', _("حذف دوره بودجه")),
            ('budgetperiod_archive', _("بایگانی دوره بودجه")),
        ]

    def __str__(self):
        return f"{self.name} ({self.organization.code})"

    def save(self, *args, **kwargs):
        from .models import BudgetHistory  # Import محلی

        with transaction.atomic():
            original_status = None
            if self.pk:
                try:
                    old_instance = BudgetPeriod.objects.get(pk=self.pk)
                    original_status_tuple = old_instance.check_budget_status_no_save()
                    original_status = original_status_tuple[0]  # e.g., 'normal'
                except BudgetPeriod.DoesNotExist:
                    pass

            super().save(*args, **kwargs)

            current_status, current_message = self.check_budget_status_no_save()

            if original_status and current_status != original_status:
                import uuid
                transaction_id = f"BPH-{self.pk}-{uuid.uuid4().hex[:10]}"

                BudgetHistory.objects.create(
                    content_object=self,
                    action='STATUS_CHANGE',  # یک اکشن مناسب
                    details=f"تغییر وضعیت از '{original_status}' به '{current_status}'. پیام: {current_message}",
                    created_by=self.created_by,  # ایده آل: کاربری که تغییر را ایجاد کرده
                    transaction_id=transaction_id  # <--- پاس دادن شناسه یکتا
                )
                logger.info(f"BudgetHistory created for BudgetPeriod {self.pk} due to status change.")

            self.update_lock_status()
            self.apply_warning_action()

    def check_budget_status_no_save(self, filters=None):
        filters = filters or {}
        cache_key = f"budget_status_{self.pk}_{hash(str(filters))}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Returning cached budget_status for {cache_key}: {cached_result}")
            return cached_result

        try:
            remaining = self.get_remaining_amount()
            locked = self.get_locked_amount()
            warning = self.get_warning_amount()

            if not self.is_active:
                result = 'inactive', _('دوره غیرفعال است.')
            elif self.is_completed:
                result = 'completed', _('بودجه تمام‌شده است.')
            elif remaining <= 0 and self.lock_condition == 'ZERO_REMAINING':
                result = 'completed', _('بودجه به صفر رسیده و تمام‌شده است.')
            elif self.lock_condition == 'AFTER_DATE' and self.end_date < timezone.now().date():
                result = 'locked', _('دوره به دلیل پایان تاریخ قفل شده است.')
            elif self.lock_condition == 'MANUAL' and remaining <= locked:
                result = 'locked', _('بودجه به حد قفل‌شده رسیده است.')
            elif remaining <= warning:
                result = 'warning', _('بودجه به آستانه هشدار رسیده است.')
            else:
                result = 'normal', _('وضعیت عادی')

            cache.set(cache_key, result, timeout=300)
            logger.debug(f"check_budget_status_no_save: obj={self}, result={result}")
            return result
        except Exception as e:
            logger.error(f"Error in check_budget_status_no_save for BudgetPeriod {self.pk}: {str(e)}")
            return 'unknown', _('وضعیت نامشخص')

    def update_lock_status(self):
        try:
            remaining = self.get_remaining_amount()
            locked = self.get_locked_amount()
            is_locked, lock_message = self.is_locked
            if is_locked:
                self.is_active = False
                if self.lock_condition == 'ZERO_REMAINING' and remaining <= 0:
                    self.is_completed = True
            else:
                self.is_active = True
                self.is_completed = False

            BudgetPeriod.objects.filter(pk=self.pk).update(is_active=self.is_active, is_completed=self.is_completed)
            logger.debug(
                f"Updated lock status for BudgetPeriod {self.pk}: is_active={self.is_active}, "
                f"is_completed={self.is_completed}")
        except Exception as e:
            logger.error(f"Error updating lock status for BudgetPeriod {self.pk}: {str(e)}")

    def get_remaining_amount(self):
        """
        محاسبه بودجه باقیمانده دوره بر اساس تراکنش‌ها.
        """
        allocations_in_period = self.allocations.all()

        if not allocations_in_period.exists():
            return self.total_amount

        transactions = BudgetTransaction.objects.filter(allocation__in=allocations_in_period).aggregate(
            total_consumed=Coalesce(Sum('amount', filter=Q(transaction_type='CONSUMPTION')), Value(Decimal('0'))),
            total_returned=Coalesce(Sum('amount', filter=Q(transaction_type='RETURN')), Value(Decimal('0')))
        )

        consumed = transactions['total_consumed']
        returned = transactions['total_returned']

        return self.total_amount - self.total_allocated + self.returned_amount

    def get_locked_amount(self):
        try:
            return calculate_threshold_amount(self.total_amount, self.locked_percentage)
        except Exception as e:
            logger.error(f"Error in get_locked_amount for BudgetPeriod {self.pk}: {str(e)}")
            return Decimal('0')

    def get_warning_amount(self):
        try:
            return calculate_threshold_amount(self.total_amount, self.warning_threshold)
        except Exception as e:
            logger.error(f"Error in get_warning_amount for BudgetPeriod {self.pk}: {str(e)}")
            return Decimal('0')

    def apply_warning_action(self):
        try:
            status, _ = self.check_budget_status_no_save()
            if status == 'warning' and self.warning_action == 'LOCK':
                self.is_locked = True
                BudgetPeriod.objects.filter(pk=self.pk).update(is_locked=True)
                logger.debug(f"Applied LOCK action for BudgetPeriod {self.pk}")
            elif status == 'warning' and self.warning_action == 'RESTRICT':
                logger.debug(f"Applied RESTRICT action for BudgetPeriod {self.pk}")
        except Exception as e:
            logger.error(f"Error applying warning action for BudgetPeriod {self.pk}: {str(e)}")

# --------------------------------------
""" BudgetAllocation (تخصیص بودجه):"""
class BudgetAllocation(models.Model):
    """
    تخصیص بودجه به سازمان‌ها (شعبات یا ادارات) و پروژه‌ها.
    """
    budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE, related_name='allocations',
                                      verbose_name=_("دوره بودجه"))
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='budget_allocations',
                                     verbose_name=_("سازمان دریافت‌کننده"))
    budget_item = models.ForeignKey('BudgetItem', on_delete=models.PROTECT, related_name='allocations',
                                    verbose_name=_("ردیف بودجه"))
    project = models.ForeignKey('core.Project', on_delete=models.CASCADE, related_name='allocations',
                                verbose_name=_("پروژه"), null=True, blank=True)
    subproject = models.ForeignKey('core.SubProject', on_delete=models.CASCADE, null=True, blank=True,
                                   related_name='budget_allocations', verbose_name=_("زیرپروژه"))
    allocated_amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ تخصیص"))
    allocation_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ تخصیص"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    ALLOCATION_TYPES = (('amount', _("مبلغ ثابت")), ('percent', _("درصد")), ('returned', _("برگشتی")),)
    allocation_type = models.CharField(max_length=20, choices=ALLOCATION_TYPES, default='amount',
                                       verbose_name=_("نوع تخصیص"))
    locked_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_("درصد قفل‌شده"),
                                            help_text=_("درصد تخصیص که قفل می‌شود (0-100)"))
    warning_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=10, verbose_name=_("آستانه اخطار"),
                                            help_text=_("درصدی که هشدار نمایش داده می‌شود (0-100)"))
    warning_action = models.CharField(max_length=50, choices=[('NOTIFY', _("فقط اعلان")), ('LOCK', _("قفل کردن")),
                                                              ('RESTRICT', _("محدود کردن ثبت"))], default='NOTIFY',
                                      verbose_name=_("اقدام هشدار"),
                                      help_text=_("رفتار سیستم هنگام رسیدن به آستانه هشدار"))
    allocation_number = models.IntegerField(default=1, verbose_name=_("شماره تخصیص"))
    returned_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0,
                                          verbose_name=_("مجموع بودجه برگشتی"))

    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    is_locked = models.BooleanField(default=False, verbose_name=_("قفل‌شده"))
    is_stopped = models.BooleanField(default=False, verbose_name=_("متوقف‌شده"))

    created_at = models.DateTimeField(_('تاریخ ایجاد '), auto_now_add=True,
                                      help_text=_('تاریخ ایجاد بودجه . خودکار سیستم '))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,
                                   related_name='budget_allocations_created', verbose_name=_("ایجادکننده"))

    class Meta:
        db_table = 'budgets_budgetallocation'
        verbose_name = _("تخصیص بودجه")
        verbose_name_plural = _("تخصیص‌های بودجه")
        default_permissions = ()
        permissions = [
            ('budgetallocation_add', _("افزودن تخصیص بودجه")),
            ('budgetallocation_view', _("نمایش تخصیص بودجه")),
            ('budgetallocation_update', _("بروزرسانی تخصیص بودجه")),
            ('budgetallocation_delete', _("حذف تخصیص بودجه")),
            ('budgetallocation_adjust', _("تنظیم تخصیص بودجه (افزایش/کاهش)")),
            ('budgetallocation_stop', _("توقف تخصیص بودجه")),
            ('budgetallocation_return', _("برگشت تخصیص بودجه")),
            ('BudgetAllocation_approve', 'می‌تواند تخصیص بودجه را تأیید کند'),
            ('BudgetAllocation_reject', 'می‌تواند تخصیص بودجه را رد کند'),
        ]
        indexes = [
            models.Index(fields=['budget_period', 'allocation_date']),
            models.Index(fields=['organization', 'allocated_amount']),
            models.Index(fields=['project']),
            models.Index(fields=['subproject']),
        ]

    def __str__(self):
        try:
            jalali_date = jdatetime.date.fromgregorian(date=self.allocation_date).strftime('%Y/%m/%d')
            org_name = self.organization.name if self.organization else 'بدون سازمان'
            item_name = self.budget_item.name if self.budget_item else 'بدون ردیف'
            return f"{org_name} - {item_name} - {jalali_date} - {self.allocated_amount:,.0f} ریال"
        except (AttributeError, TypeError) as e:
            logger.error(f"Error in BudgetAllocation.__str__: {str(e)}")
            project_name = self.project.name if self.project else 'بدون پروژه'
            return f"تخصیص {self.pk or 'جدید'}: {self.allocated_amount:,.0f} ریال ({project_name})"

    def get_percentage(self):
        if self.budget_item.total_amount and self.budget_item.total_amount != 0:
            return (self.allocated_amount / self.budget_item.total_amount) * 100
        return Decimal('0')

    def clean(self):
        super().clean()
        logger.debug(
            f"Cleaning BudgetAllocation: allocated_amount={self.allocated_amount}, allocation_type={self.allocation_type}")

        if self.budget_item_id is None:
            raise ValidationError(_("ردیف بودجه اجباری است."))
        if self.organization_id is None:
            raise ValidationError(_("سازمان دریافت‌کننده اجباری است."))
        if self.allocated_amount is None:
            raise ValidationError(_("مبلغ تخصیص نمی‌تواند خالی باشد."))
        if self.allocated_amount <= 0:
            raise ValidationError(_("مبلغ تخصیص باید مثبت باشد."))

        if self.budget_period and self.budget_item:
            if self.budget_item.budget_period != self.budget_period:
                raise ValidationError(_("ردیف بودجه باید متعلق به دوره بودجه انتخاب‌شده باشد."))

        if self.budget_period and self.allocation_date:
            allocation_date = self.allocation_date
            if hasattr(allocation_date, "date"):
                allocation_date = allocation_date.date()
            if not (self.budget_period.start_date <= allocation_date <= self.budget_period.end_date):
                raise ValidationError(_("تاریخ تخصیص باید در بازه دوره بودجه باشد."))

        if self.warning_threshold is not None and not (0 <= self.warning_threshold <= 100):
            raise ValidationError(_("آستانه اخطار باید بین ۰ تا ۱۰۰ باشد."))

        remaining_budget = self.budget_period.get_remaining_amount()
        if self.pk:
            current_allocation = BudgetAllocation.objects.filter(pk=self.pk).aggregate(total=Sum('allocated_amount'))[
                                     'total'] or Decimal('0')
            remaining_budget += current_allocation
        if self.allocated_amount > remaining_budget:
            raise ValidationError(_(
                f"مبلغ تخصیص ({self.allocated_amount:,.0f} ریال) بیشتر از باقی‌مانده دوره بودجه ({remaining_budget:,.0f} ریال) است."
            ))

        locked_amount = self.budget_period.get_locked_amount()
        available_for_allocation = remaining_budget - locked_amount
        if self.allocated_amount > available_for_allocation:
            raise ValidationError(_(
                f"نمی‌توان تخصیص داد. مبلغ تخصیص ({self.allocated_amount:,.0f} ریال) بیشتر از مقدار مجاز ({available_for_allocation:,.0f} ریال) است."
                f"حداقل {self.budget_period.locked_percentage}% از بودجه باید قفل بماند."
            ))

        logger.debug("Clean validation passed (Model IS : BudgetsAllocations )")

    def get_remaining_amount(self):
        allocated = self.allocated_amount
        spent_amount = Tankhah.objects.filter(
            project_budget_allocation=self,
            status__code__in=['APPROVED', 'PAID']
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        pending_amount = Tankhah.objects.filter(
            project_budget_allocation=self,
            status__code__in=['DRAFT', 'PENDING']
        ).exclude(pk=self.pk).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        return allocated - (spent_amount + pending_amount)

    def get_total_allocated(self):
        return self.allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')

    def get_locked_amount(self):
        try:
            return calculate_threshold_amount(self.allocated_amount, self.locked_percentage)
        except Exception as e:
            logger.error(f"Error in get_locked_amount for BudgetAllocation {self.pk}: {str(e)}")
            return Decimal('0')

    def get_warning_amount(self):
        try:
            return calculate_threshold_amount(self.allocated_amount, self.warning_threshold)
        except Exception as e:
            logger.error(f"Error in get_warning_amount for BudgetAllocation {self.pk}: {str(e)}")
            return Decimal('0')

    def get_actual_remaining_amount(self):
        transactions_sum = self.transactions.aggregate(
            consumption=Sum('amount', filter=Q(transaction_type='CONSUMPTION')),
            adjustment_decrease=Sum('amount', filter=Q(transaction_type='ADJUSTMENT_DECREASE')),
            returns=Sum('amount', filter=Q(transaction_type='RETURN')),
            adjustment_increase=Sum('amount', filter=Q(transaction_type='ADJUSTMENT_INCREASE')),
        )
        consumed = (transactions_sum['consumption'] or Decimal('0')) + (
                transactions_sum['adjustment_decrease'] or Decimal('0'))
        added_back = (transactions_sum['returns'] or Decimal('0')) + (
                transactions_sum['adjustment_increase'] or Decimal('0'))
        return self.allocated_amount - consumed + added_back

    def check_allocation_status(self):
        remaining = self.get_remaining_amount()
        locked = self.get_locked_amount()
        warning = self.get_warning_amount()
        if not self.is_active:
            return 'inactive', _('تخصیص غیرفعال است.')
        if self.is_stopped:
            return 'stopped', _('تخصیص متوقف شده است.')
        if remaining <= 0:
            return 'completed', _('تخصیص تمام‌شده است.')
        if remaining <= locked:
            return 'locked', _('تخصیص به حد قفل‌شده رسیده است.')
        if remaining <= warning:
            return 'warning', _('تخصیص به آستانه هشدار رسیده است.')
        return 'normal', _('وضعیت عادی')

    def update_lock_status(self):
        try:
            remaining_amount = self.get_remaining_amount()
            locked_amount = self.get_locked_amount()
            if remaining_amount <= locked_amount:
                self.is_locked = True
                self.is_active = False
                Tankhah.objects.filter(project_budget_allocation=self).update(is_active=False)
                logger.debug(f"Disabled Tankhahs for BudgetAllocation {self.pk}")
            else:
                self.is_locked = False
                self.is_active = True
            return self.is_locked, self.is_active
        except Exception as e:
            logger.error(f"Error in update_lock_status for BudgetAllocation {self.pk or 'unsaved'}: {str(e)}")
            return self.is_locked, self.is_active

    def reallocate(self, target_allocation, amount):
        if amount > self.get_remaining_amount():
            raise ValidationError(_("بودجه کافی برای انتقال وجود ندارد."))
        BudgetReallocation.objects.create(
            source_allocation=self,
            target_allocation=target_allocation,
            amount=amount
        )
        logger.info(f"Reallocated {amount} from PK {self.pk} to PK {target_allocation.pk}")

    def save(self, *args, **kwargs):
        from .budget_calculations import create_budget_transaction  # Import محلی
        with transaction.atomic():
            is_new = self._state.adding
            old_amount = Decimal('0')
            if not is_new:
                old_instance = BudgetAllocation.objects.select_for_update().get(pk=self.pk)
                old_amount = old_instance.allocated_amount

            super().save(*args, **kwargs)

            if is_new:
                if self.allocated_amount > 0:
                    logger.info(f"Creating initial ALLOCATION transaction for new BudgetAllocation PK {self.pk}")
                    create_budget_transaction(
                        budget_source_obj=self,
                        transaction_type='ALLOCATION',
                        amount=self.allocated_amount,
                        created_by=self.created_by,
                        description=f"اعتبار اولیه تخصیص بودجه برای پروژه {self.project.name}"
                    )
            elif self.allocated_amount != old_amount:
                adjustment_amount = self.allocated_amount - old_amount
                transaction_type = 'INCREASE' if adjustment_amount > 0 else 'DECREASE'

                logger.info(f"Creating {transaction_type} transaction for updated BudgetAllocation PK {self.pk}")
                create_budget_transaction(
                    budget_source_obj=self,
                    transaction_type=transaction_type,
                    amount=abs(adjustment_amount),
                    created_by=self.created_by,  # ایده آل: کاربری که تغییر را اعمال کرده
                    description=f"اصلاح مبلغ تخصیص از {old_amount:,.0f} به {self.allocated_amount:,.0f}"
                )
            from django.core.cache import cache
            cache.delete(f"budget_allocation_balance_{self.pk}")
            cache.delete(f"project_total_budget_v2_{self.project.pk}_no_filters" if self.project else None)
            cache.delete(f"project_remaining_budget_{self.project.pk}_no_filters" if self.project else None)
# --------------------------------------
""" BudgetItem (نوع ردیف بودجه):"""
class BudgetItem(models.Model):
    budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE, related_name='budget_items',
                                      verbose_name=_("دوره بودجه"))
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='budget_items',
                                     verbose_name=_("شعبه"))
    name = models.CharField(max_length=100, verbose_name=_("نام ردیف بودجه"), null=True, blank=True)
    code = models.CharField(max_length=50, unique=True, verbose_name=_("کد ردیف"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    create_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاریخ ثبت '), null=True, blank=True)

    class Meta:
        verbose_name = _("ردیف بودجه")
        verbose_name_plural = _("ردیف‌های بودجه")
        unique_together = ('budget_period', 'organization', 'code')
        default_permissions =()
        permissions =  [
            ('BudgetItem_add','افزودن ردیف بودجه'),
            ('BudgetItem_update','ویرایش ردیف بودجه'),
            ('BudgetItem_view','نمایش ردیف بودجه'),
            ('BudgetItem_delete','حــذف ردیف بودجه'),
        ]

    def __str__(self):
        if self.budget_period.name:
            return f"{self.budget_period.name} - {self.name} - {self.organization.name}"
        else:
            return f"{self.name} - {self.organization.name}-بدون ردیف بودجه"

    def clean(self):
        super().clean()
        if not self.name:
            raise ValidationError(_("نام ردیف بودجه نمی‌تواند خالی باشد."))
# --------------------------------------
""" BudgetTransaction (تراکنش بودجه):"""
class BudgetTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('ALLOCATION', _('تخصیص اولیه')),
        ('CONSUMPTION', _('مصرف / هزینه')),
        ('ADJUSTMENT_INCREASE', _('افزایش تخصیص')),
        ('ADJUSTMENT_DECREASE', _('کاهش تخصیص')),
        ('RETURN', _('برگشت به بودجه')),
    )
    allocation = models.ForeignKey('BudgetAllocation', on_delete=models.CASCADE, related_name='transactions',
                                   verbose_name=_("تخصیص بودجه"), null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name=_("نوع تراکنش"))
    amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ"))
    related_tankhah = models.ForeignKey('tankhah.Tankhah', on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name=_("تنخواه مرتبط"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, verbose_name=_("کاربر"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    transaction_id = models.CharField(max_length=250, unique=True, verbose_name=_("شناسه تراکنش"))

    class Meta:
        verbose_name = _("تراکنش بودجه")
        verbose_name_plural = _("تراکنش‌های بودجه")
        default_permissions = ()
        permissions = [
            ('BudgetTransaction_add', 'افزودن تراکنش بودجه'),
            ('BudgetTransaction_update', 'بروزرسانی تراکنش بودجه'),
            ('BudgetTransaction_delete', 'حــذف تراکنش بودجه'),
            ('BudgetTransaction_view', _('نمایش تراکنش بودجه')),
            ('BudgetTransaction_return', _('برگشت تراکنش بودجه')),
        ]

    def validate_return(self):
        if self.transaction_type != 'RETURN':
            return True, None
        logger.debug(f"Validating RETURN transaction: amount={self.amount}, allocation ID={self.allocation.pk}")

        if self.amount is None:
            logger.error("Return amount is None")
            return False, _("مبلغ بازگشت نمی‌تواند خالی باشد.")

        if self.amount > self.allocation.allocated_amount:
            logger.error(
                f"Return amount {self.amount:,.0f} exceeds allocated_amount {self.allocation.allocated_amount:,.0f} "
                f"for allocation ID: {self.allocation.pk}"
            )
            return False, _(
                f"مبلغ بازگشت ({self.amount:,.0f} ریال) نمی‌تواند بیشتر از مبلغ تخصیص‌یافته ({self.allocation.allocated_amount:,.0f} ریال) باشد.")

        remaining_budget = self.allocation.get_remaining_amount()
        if self.amount > remaining_budget:
            logger.error(
                f"Return amount {self.amount:,.0f} exceeds remaining_budget {remaining_budget:,.0f} "
                f"for allocation ID: {self.allocation.pk}"
            )
            return False, _(
                f"مبلغ بازگشت ({self.amount:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) باشد.")

        return True, None

    def clean(self):
        allocation_id_for_log = self.allocation.pk if self.allocation else 'N/A'
        logger.debug(
            f"Cleaning BudgetTransaction: amount={self.amount}, "
            f"type={self.transaction_type}, allocation ID={allocation_id_for_log}"
        )

        if self.transaction_type == 'RETURN':
            is_valid, error_message = self.validate_return()
            if not is_valid:
                raise ValidationError(error_message)
            if self.amount <= 0:
                raise ValidationError(_("مبلغ بازگشت باید مثبت باشد."))

        logger.info(f"BudgetTransaction validated successfully for allocation ID: {allocation_id_for_log}")

    def save(self, *args, **kwargs):
        allocation_id_for_log = self.allocation.pk if self.allocation else 'N/A'
        logger.debug(
            f"Starting save for BudgetTransaction: "f"amount={self.amount}, type={self.transaction_type}, "f"allocation ID={allocation_id_for_log}")
        try:
            with transaction.atomic():
                if not self.transaction_id:
                    import uuid
                    source_pk = self.allocation.pk if self.allocation else (
                        self.related_tankhah.pk if self.related_tankhah else 'NA')
                    self.transaction_id = f"TX-{self.transaction_type}-{source_pk}-{uuid.uuid4().hex[:10]}"
                    logger.info(f"Generated transaction_id: {self.transaction_id}")

                self.clean()
                super().save(*args, **kwargs)
                logger.info(f"BudgetTransaction saved with ID: {self.pk}")

                if self.transaction_type == 'RETURN':
                    self.allocation.allocated_amount -= self.amount
                    self.allocation.returned_amount += self.amount
                    self.allocation.save(update_fields=['allocated_amount', 'returned_amount'])
                    logger.debug(
                        f"Updated BudgetAllocation {self.allocation.pk}: allocated_amount={self.allocation.allocated_amount}, returned_amount={self.allocation.returned_amount}")

                    budget_period = self.allocation.budget_period
                    budget_period.returned_amount = BudgetTransaction.objects.filter(
                        allocation__budget_period=budget_period,
                        transaction_type='RETURN'
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                    BudgetPeriod.objects.filter(pk=budget_period.pk).update(
                        returned_amount=budget_period.returned_amount)
                    logger.debug(
                        f"Updated BudgetPeriod {budget_period.pk}: returned_amount={budget_period.returned_amount}")

        except Exception as e:
            logger.error(f"Error saving BudgetTransaction: {str(e)}", exc_info=True)
            raise

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount:,.0f} - {self.timestamp.strftime('%Y/%m/%d')}"
# --------------------------------------
"""Payee (دریافت‌کننده):"""
class Payee(models.Model):
    """توضیح: اطلاعات دریافت‌کننده پرداخت با نوع مشخص (فروشنده، کارمند، دیگر)."""
    PAYEE_TYPES = (
        ('VENDOR', _('فروشنده')),
        ('EMPLOYEE', _('کارمند')),
        ('OTHER', _('دیگر')),
    )
    name = models.CharField(max_length=100, verbose_name=_("نام"))
    family = models.CharField(max_length=100, verbose_name=_("نام خانوادگی"))
    payee_type = models.CharField(max_length=20, choices=PAYEE_TYPES, verbose_name=_("نوع"))
    national_id = models.CharField(max_length=20, blank=True, null=True,
                                   verbose_name=_("کد ملی/اقتصادی"))
    account_number = models.CharField(max_length=50, blank=True, null=True,
                                      verbose_name=_("شماره حساب"))
    iban = models.CharField(max_length=34, blank=True, null=True, verbose_name=_("شبا"))
    address = models.TextField(blank=True, null=True, verbose_name=_("آدرس"))
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("تلفن"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,
                                   related_name='payees_created', verbose_name=_("ایجادکننده"))
    is_active = models.BooleanField(verbose_name=_('فعال'))

    def __str__(self):
        return f"{self.name} ({self.payee_type})"

    class Meta:
        verbose_name = _("دریافت‌کننده")
        verbose_name_plural = _("دریافت‌کنندگان")
        default_permissions = ()
        permissions = [
            ('Payee_add', _('افزودن دریافت‌کننده')),
            ('Payee_view', _('نمایش دریافت‌کننده')),
            ('Payee_update', _('بروزرسانی دریافت‌کننده')),
            ('Payee_delete', _('حذف دریافت‌کننده')),
        ]
# --------------------------------------
"""PaymentOrder (دستور پرداخت):"""
# --------------------------------------
class PaymentOrder(models.Model):
    tankhah = models.ForeignKey(Tankhah, on_delete=models.CASCADE, related_name='payment_orders',
                                verbose_name=_("تنخواه"))
    related_tankhah = models.ForeignKey(Tankhah, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='payment_orders_tankhah', verbose_name=_('تنخواه مرتبط'))
    order_number = models.CharField(_('شماره دستور پرداخت'), max_length=50, unique=True, default=None)
    issue_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ صدور"))
    amount = models.DecimalField(_('مبلغ (ریال)'), max_digits=25, decimal_places=2)
    payee = models.ForeignKey(Payee, on_delete=models.PROTECT, related_name='payment_orders',
                              verbose_name=_('دریافت‌کننده'))
    description = models.TextField(_('شرح پرداخت'), blank=True)
    payment_id = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شناسه پرداخت"))

    status = models.ForeignKey(
        'core.Status',
        on_delete=models.PROTECT,
        verbose_name=_("وضعیت"),
        default=get_default_initial_status,
        null=True,
        blank=True,
    )
    created_by_post = models.ForeignKey(Post, on_delete=models.SET_NULL, null=True, verbose_name=_("پست ایجادکننده"))
    min_signatures = models.IntegerField(default=1, verbose_name=_("حداقل تعداد امضا"))
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='created_payment_orders',
                                   verbose_name=_('ایجادکننده'))
    payment_date = models.DateField(null=True, blank=True, verbose_name=_("تاریخ پرداخت"))
    payee_account_number = models.IntegerField(_('شماره حساب'), blank=True, null=True)
    payee_iban = models.IntegerField(_('شبا'), blank=True, null=True)
    payment_tracking_id = models.CharField(_('شناسه پرداخت'), max_length=200, blank=True, null=True)
    paid_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='processed_payment_orders', verbose_name=_('پردازش توسط'))
    related_factors = models.ManyToManyField(Factor, blank=True, related_name='payment_orders',
                                             verbose_name=_('فاکتورهای مرتبط '))
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='payment_orders_organize',
                                     verbose_name=_('سازمان'))
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='payment_orders',
                                verbose_name=_('پروژه'))

    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    is_locked = models.BooleanField(_('0قفل شده'), default=False)
    notes = models.TextField(_('یادداشت‌ها'), blank=True, null=True)

    def generate_payment_order_number(self):
        sep = "-"
        date_str = jdatetime.date.fromgregorian(date=self.issue_date).strftime('%Y%m%d')
        serial = PaymentOrder.objects.filter(issue_date=self.issue_date).count() + 1
        return f"PO{sep}{date_str}{sep}{serial:03d}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_payment_order_number()

        if not self.organization:
            if self.tankhah and self.tankhah.organization:
                self.organization = self.tankhah.organization
            elif self.related_tankhah and self.related_tankhah.organization:
                self.organization = self.related_tankhah.organization
            elif self.related_factors.exists():
                factor = self.related_factors.first()
                if factor.tankhah and factor.tankhah.organization:
                    self.organization = factor.tankhah.organization
            else:
                if self.created_by and not self.created_by.is_superuser:
                    user_org = UserPost.objects.filter(
                        user=self.created_by, is_active=True, end_date__isnull=True
                    ).values_list('post__organization', flat=True).first()
                    if user_org:
                        self.organization = Organization.objects.get(pk=user_org)
                    else:
                        raise ValidationError(_('سازمان باید مشخص شود.'))
                else:
                    default_org = Organization.objects.filter(is_active=True).first()
                    if default_org:
                        self.organization = default_org
                    else:
                        raise ValidationError(_('هیچ سازمان فعالی یافت نشد.'))

        if self.payee:
            self.payee_account_number = self.payee_account_number or self.payee.account_number
            self.payee_iban = self.payee_iban or self.payee.iban
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} - {self.amount:,.0f}"

    class Meta:
        verbose_name = _("دستور پرداخت")
        verbose_name_plural = _("دستورهای پرداخت")
        ordering = ['-created_at']
        default_permissions = ()
        permissions = [
            ('PaymentOrder_add', 'افزودن دستور پرداخت'),
            ('PaymentOrder_view', 'نمایش دستور پرداخت'),
            ('PaymentOrder_update', 'بروزرسانی دستور پرداخت'),
            ('PaymentOrder_delete', 'حذف دستور پرداخت'),
            ('PaymentOrder_sign', 'امضای دستور پرداخت'),
            ('PaymentOrder_issue', 'صدور دستور پرداخت'),
        ]

    def update_budget_impact(self):
        """به‌روزرسانی بودجه پس از پرداخت"""
        if self.status == 'PAID' and not self.is_locked:
            with transaction.atomic():
                if self.tankhah:
                    self.tankhah.spent += self.amount
                    self.tankhah.save()
                if self.related_tankhah:
                    self.related_tankhah.spent += self.amount
                    self.related_tankhah.save()
                if self.project:
                    self.project.spent += self.amount
                    self.project.save()
                BudgetTransaction.objects.create(
                    allocation=self.tankhah.budget_allocation if self.tankhah else None,
                    transaction_type='CONSUMPTION',
                    amount=self.amount,
                    related_tankhah=self.tankhah or self.related_tankhah,
                    description=f"پرداخت دستور {self.order_number}",
                    created_by=self.paid_by or self.created_by
                )
                self.is_locked = True
                self.save()
# --------------------------------------
"""TransactionType (نوع تراکنش):"""
class TransactionType(models.Model):
    """توضیح: تعریف پویا نوع تراکنش‌ها (مثل بیمه، جریمه) با امکان نیاز به تأیید اضافی."""
    name = models.CharField(max_length=250, unique=True, verbose_name=_("نام"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    requires_extra_approval = models.BooleanField(default=False,
                                                  verbose_name=_("نیاز به تأیید اضافی"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,
                                   related_name='transaction_types_created', verbose_name=_("ایجادکننده"))
    category = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('گروه بندی تراکنش‌ها '))
    TRANSACTION_FLOW_CHOICES = [
        ('INFLOW', _('ورودی (افزایش بودجه)')),
        ('OUTFLOW', _('خروجی (کاهش بودجه)')),
        ('CONSUMPTION', _('مصرف بودجه')),
        ('TRANSFER', _('انتقال بودجه')),
        ('RETURN', _('بازگشت بودجه')),
        ('ADJUSTMENT', _('تعدیل بودجه')),
    ]
    transaction_flow = models.CharField(
        max_length=20,
        choices=TRANSACTION_FLOW_CHOICES,
        verbose_name=_("جریان تراکنش"),
        help_text=_("جهت جریان مالی این نوع تراکنش (ورودی، خروجی، مصرف و غیره)")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("نوع تراکنش")
        verbose_name_plural = _("انواع تراکنش")
        default_permissions = ()
        permissions = [
            ('TransactionType_add', _('افزودن نوع تراکنش')),
            ('TransactionType_view', _('نمایش نوع تراکنش')),
            ('TransactionType_update', _('بروزرسانی نوع تراکنش')),
            ('TransactionType_delete', _('حذف نوع تراکنش')),
        ]
# --------------------------------------
"""مدل BudgetReallocation برای انتقال باقی‌مانده بودجه متوقف‌شده."""
class BudgetReallocation(models.Model):
    source_allocation = models.ForeignKey('BudgetAllocation', on_delete=models.CASCADE,
                                          related_name='reallocations_from')
    target_allocation = models.ForeignKey('BudgetAllocation', on_delete=models.CASCADE, null=True,
                                          related_name='reallocations_to')
    amount = models.DecimalField(max_digits=25, decimal_places=2)
    reallocation_date = models.DateField(default=timezone.now)
    reason = models.TextField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    def clean(self):
        super().clean()
        if self.amount <= 0:
            raise ValidationError(_("مبلغ انتقال باید مثبت باشد."))
        if self.source_allocation.get_remaining_amount() < self.amount:
            raise ValidationError(_("بودجه کافی در تخصیص منبع وجود ندارد."))
# --------------------------------------
"""یه جدول تنظیمات (BudgetSettings) برای مدیریت قفل و هشدار در سطوح مختلف:"""


class BudgetSettings(models.Model):
    level = models.CharField(max_length=50,
                             choices=[('PERIOD', 'دوره بودجه'), ('ALLOCATION', 'تخصیص'), ('PROJECT', 'پروژه')])
    locked_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    warning_threshold = models.DecimalField(max_digits=5, decimal_places=2)
    warning_action = models.CharField(max_length=50,
                                      choices=[('NOTIFY', 'اعلان'), ('LOCK', 'قفل'), ('RESTRICT', 'محدود')])
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, null=True)
    budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE, null=True, verbose_name=_("دوره بودجه"))


"""مدل BudgetHistory برای لاگ کردن تغییرات بودجه و تخصیص‌ها:"""
# ------------------------------------
"""تاریخچه برای هر بودجه کلان"""


class BudgetHistory(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    action = models.CharField(max_length=50, choices=[
        ('CREATE', _('ایجاد')),
        ('UPDATE', _('بروزرسانی')),
        ('STOP', _('توقف')),
        ('REALLOCATE', _('انتقال')),
        ('RETURN', _('برگشت'))  # جدید
    ])
    amount = models.DecimalField(max_digits=25, decimal_places=2, null=True, verbose_name=_('رقم عدد'))
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name=_('کاربر ثبت کننده'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('اکشن در تاریخ و ساعت'))
    details = models.TextField(blank=True, verbose_name=_('جزئیات'))
    transaction_type = models.CharField(max_length=20, choices=[('ALLOCATION', _('تخصیص')), ('CONSUMPTION', _('مصرف')),
                                                                ('RETURN', _('برگشت'))], verbose_name=_("نوع تراکنش"))
    transaction_id = models.CharField(max_length=250, unique=True, verbose_name=_("شناسه تراکنش"))

    @staticmethod
    def log_change(obj, action, amount, created_by, details, transaction_type, transaction_id):
        BudgetHistory.objects.create(
            content_type=ContentType.objects.get_for_model(obj),
            object_id=obj.pk,
            action=action,
            amount=amount,
            created_by=created_by,
            details=details,
            transaction_type=transaction_type,
            transaction_id=transaction_id
        )

    def __str__(self):
        return f"{self.action} - {self.amount:,} ({self.created_at})"

    class Meta:
        verbose_name = _("تاریخچه بودجه")
        verbose_name_plural = _("تاریخچه‌های بودجه")
        default_permissions = ()
        permissions = [
            ('BudgetHistory_add', 'افزودن تاریخچه برای هر بودجه کلان'),
            ('BudgetHistory_view', ' نمایش تاریخچه هر بودجه کلان'),
            ('BudgetHistory_update', 'بروزرسانی تاریخچه برای هر بودجه کلان'),
            ('BudgetHistory_delete', ' حــذف تاریخچه برای هر بودجه کلان'),
        ]


# --------------------------------------
"""'دسترسی برای جابجایی و برگشت بودجه'"""


class BudgetTransferReturn(models.Model):
    class Meta:
        verbose_name = 'دسترسی برای جابجایی و برگشت بودجه'
        verbose_name_plural = 'دسترسی برای جابجایی و برگشت بودجه'
        default_permissions = ()
        permissions = [
            ('BudgetTransfer', 'دسترسی جابجایی بودجه'),
            ('BudgetReturn', 'دسترسی برگشت جابجایی بودجه'),
        ]


# --------------------------------------
""" مدل پیشنهادی برای هزینه‌های متعارف"""


class CostCenter(models.Model):
    """ مدل پیشنهادی برای هزینه‌های متعارف"""
    name = models.CharField(max_length=200, verbose_name=_("نام مرکز هزینه"))
    code = models.CharField(max_length=50, unique=True, verbose_name=_("کد مرکز هزینه"))
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, verbose_name=_("سازمان"))
    budget_allocation = models.ForeignKey(BudgetAllocation, on_delete=models.CASCADE, verbose_name=_("تخصیص بودجه"))
    allocated_budget = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("بودجه تخصیص‌یافته"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))

    def get_remaining_budget(self):
        from tankhah.models import Tankhah
        consumed = Tankhah.objects.filter(cost_center=self).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        return max(self.allocated_budget - consumed, Decimal('0'))

    def apply_settings(self, obj):
        if self.level == 'PERIOD' and isinstance(obj, BudgetPeriod):
            obj.locked_percentage = self.locked_percentage
            obj.warning_threshold = self.warning_threshold
            obj.warning_action = self.warning_action
            obj.save(update_fields=['locked_percentage', 'warning_threshold', 'warning_action'])

    class Meta:
        verbose_name = _("مرکز هزینه")
        verbose_name_plural = _("مراکز هزینه")


""" مدل ثبت دستور پرداخت  """


def generate_payment_order_number(self):
    last_order = PaymentOrder.objects.order_by('pk').last()
    if not last_order:
        return f"PO-{timezone.now().strftime('%Y%m%d')}-0001"
    last_pk = last_order.pk or 0
    sep = "-"
    date_str = jdatetime.date.fromgregorian(date=self.issue_date).strftime('%Y%m%d')
    serial = PaymentOrder.objects.filter(issue_date=self.issue_date).count() + 1
    return f"PO{sep}{date_str}{sep}{serial:03d}"
