from django.contrib.postgres.fields import ArrayField
from django.db.models.functions import Coalesce
from django.db.models import Value, Q
import logging
from django.utils import timezone
from django.core.cache import cache

from core.models import Organization, Project, WorkflowStage, Post, UserPost
from tankhah.models import Factor, Tankhah, ApprovalLog

logger = logging.getLogger(__name__)
from django.contrib.contenttypes.models import ContentType

from budgets.budget_calculations import check_budget_status, get_project_remaining_budget, calculate_remaining_amount, \
    calculate_threshold_amount, send_notification

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

""" مدل نوع بودجه """# ------------------------------------
"""BudgetPeriod (دوره بودجه کلان):"""

class BudgetPeriod(models.Model):
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, verbose_name=_("دفتر مرکزی"),related_name='budget_periods')
    name = models.CharField(max_length=100, unique=True, verbose_name=_("نام دوره بودجه"))
    start_date = models.DateField(verbose_name=_("تاریخ شروع"))
    end_date = models.DateField(verbose_name=_("تاریخ پایان"))
    total_amount = models.DecimalField(max_digits=25, decimal_places=0, verbose_name=_("مبلغ کل"))
    total_allocated = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_("مجموع تخصیص‌ها"))
    returned_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0,verbose_name=_("مجموع بودجه برگشتی"))
    locked_percentage = models.IntegerField(default=0, verbose_name=_("درصد قفل‌شده"),help_text=_("درصد بودجه که قفل می‌شود (0-100)"))
    warning_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=10, verbose_name=_("آستانه اخطار"),help_text=_("درصدی که هشدار نمایش داده می‌شود (0-100)"))
    warning_action = models.CharField(max_length=50,choices=[('NOTIFY', _("فقط اعلان")), ('LOCK', _("قفل کردن")),('RESTRICT', _("محدود کردن ثبت"))],default='NOTIFY',verbose_name=_("اقدام هشدار") ,
                                      help_text=_("رفتار سیستم هنگام رسیدن به آستانه هشدار"))
    allocation_phase = models.CharField(max_length=50, blank=True, verbose_name=_("فاز تخصیص"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))

    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,related_name='budget_periods_created', verbose_name=_("ایجادکننده"))

    is_active =    models.BooleanField(default=True, verbose_name=_("فعال"))
    is_archived =  models.BooleanField(default=False, verbose_name=_("بایگانی شده"))
    is_completed = models.BooleanField(default=False, verbose_name=_("تمام‌شده"))
    # is_locked =    models.BooleanField(default=False, verbose_name=_("قفل شده"))  # فیلد جدید
    lock_condition = models.CharField(max_length=50,choices=[('AFTER_DATE', _("بعد از تاریخ پایان")), ('MANUAL', _("دستی")),
                                               ('ZERO_REMAINING', _("باقی‌مانده صفر")), ], default='AFTER_DATE',verbose_name=_("شرط قفل"))


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
        logger.debug(f"Starting save for BudgetPeriod (pk={self.pk})")
        try:
            with transaction.atomic():
                self.full_clean()
                super().save(*args, **kwargs)
                logger.info(f"BudgetPeriod saved with ID: {self.pk}")
                self.apply_warning_action()
                self.update_lock_status()  # اصلاح: استفاده از update_lock_status
                status, message = self.check_budget_status_no_save()
                if status in ('warning', 'locked', 'completed'):
                    self.send_notification(status, message)
                    logger.info(f"Notification sent for status: {status}")
        except Exception as e:
            logger.error(f"Error saving BudgetPeriod: {str(e)}", exc_info=True)
            raise

    def check_budget_status_no_save(self, filters=None):
        """بررسی وضعیت بودجه بدون ذخیره‌سازی"""
        cache_key = f"budget_status_{self.pk}_{hash(str(filters)) if filters else 'no_filters'}"
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
        """به‌روزرسانی وضعیت قفل بدون ذخیره"""
        try:
            remaining = self.get_remaining_amount()
            locked = self.get_locked_amount()
            is_locked, lock_message = self.is_locked
            # به‌روزرسانی is_active و is_completed بر اساس شرایط قفل
            if is_locked:
                self.is_active = False
                if self.lock_condition == 'ZERO_REMAINING' and remaining <= 0:
                    self.is_completed = True
            else:
                self.is_active = True
                self.is_completed = False

            # if remaining <= locked:
            #     self.is_locked = True
            #     self.is_active = False
            # else:
            #     self.is_locked = False
            #     self.is_active = True
            # BudgetPeriod.objects.filter(pk=self.pk).update(is_locked=self.is_locked, is_active=self.is_active)
            BudgetPeriod.objects.filter(pk=self.pk).update(is_active=self.is_active, is_completed=self.is_completed)
            logger.debug(
                f"Updated lock status for BudgetPeriod {self.pk}: is_active={self.is_active}, "
                f"is_completed={self.is_completed}")
            # logger.debug(f"Updated lock status for BudgetPeriod {self.pk}: is_locked={self.is_locked}, "
            #              f"is_active={self.is_active}")
        except Exception as e:
            logger.error(f"Error updating lock status for BudgetPeriod {self.pk}: {str(e)}")

    def get_remaining_amount(self):
        """محاسبه بودجه باقی‌مانده دوره"""
        return self.total_amount - self.total_allocated

    def get_locked_amount(self):
        """محاسبه مقدار قفل‌شده دوره"""
        try:
            return calculate_threshold_amount(self.total_amount, self.locked_percentage)
        except Exception as e:
            logger.error(f"Error in get_locked_amount for BudgetPeriod {self.pk}: {str(e)}")
            return Decimal('0')

    def get_warning_amount(self):
        """محاسبه آستانه هشدار دوره"""
        try:
            return calculate_threshold_amount(self.total_amount, self.warning_threshold)
        except Exception as e:
            logger.error(f"Error in get_warning_amount for BudgetPeriod {self.pk}: {str(e)}")
            return Decimal('0')

    def apply_warning_action(self):
        """اعمال اقدام هشدار"""
        try:
            status, _ = self.check_budget_status_no_save()
            if status == 'warning' and self.warning_action == 'LOCK':
                self.is_locked = True
                BudgetPeriod.objects.filter(pk=self.pk).update(is_locked=True)
                logger.debug(f"Applied LOCK action for BudgetPeriod {self.pk}")
            elif status == 'warning' and self.warning_action == 'RESTRICT':
                logger.debug(f"Applied RESTRICT action for BudgetPeriod {self.pk}")
                # منطق محدود کردن ثبت تراکنش‌ها
        except Exception as e:
            logger.error(f"Error applying warning action for BudgetPeriod {self.pk}: {str(e)}")

    def send_notification(self, status, message):
        """ارسال اعلان"""
        try:
            from accounts.models import CustomUser
            recipients = CustomUser.objects.filter(is_active=True)
            send_notification(self, status, message, recipients)
            logger.info(f"Notification sent for BudgetPeriod {self.pk}: {status} - {message}")
        except Exception as e:
            logger.error(f"Error sending notification for BudgetPeriod {self.pk}: {str(e)}")
""" BudgetAllocation (تخصیص بودجه):"""
class BudgetAllocation(models.Model):
    """
    تخصیص بودجه به سازمان‌ها (شعبات یا ادارات) و پروژه‌ها.
    قابلیت‌ها: تخصیص چندباره، توقف بودجه، و ردیابی هزینه‌ها.
    """
    budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE, related_name='allocations', verbose_name=_("دوره بودجه"))
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='budget_allocations', verbose_name=_("سازمان دریافت‌کننده"))
    budget_item = models.ForeignKey('BudgetItem', on_delete=models.PROTECT, related_name='allocations', verbose_name=_("ردیف بودجه"))
    project = models.ForeignKey('core.Project', on_delete=models.CASCADE, related_name='allocations', verbose_name=_("پروژه"), null=True, blank=True)
    subproject = models.ForeignKey('core.SubProject', on_delete=models.CASCADE, null=True, blank=True, related_name='budget_allocations', verbose_name=_("زیرپروژه"))
    allocated_amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ تخصیص"))
    allocation_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ تخصیص"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    ALLOCATION_TYPES = (('amount', _("مبلغ ثابت")), ('percent', _("درصد")), ('returned', _("برگشتی")),)
    allocation_type = models.CharField(max_length=20, choices=ALLOCATION_TYPES, default='amount', verbose_name=_("نوع تخصیص"))
    locked_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_("درصد قفل‌شده"), help_text=_("درصد تخصیص که قفل می‌شود (0-100)"))
    warning_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=10, verbose_name=_("آستانه اخطار"), help_text=_("درصدی که هشدار نمایش داده می‌شود (0-100)"))
    warning_action = models.CharField(max_length=50, choices=[('NOTIFY', _("فقط اعلان")), ('LOCK', _("قفل کردن")), ('RESTRICT', _("محدود کردن ثبت"))], default='NOTIFY', verbose_name=_("اقدام هشدار"), help_text=_("رفتار سیستم هنگام رسیدن به آستانه هشدار"))
    allocation_number = models.IntegerField(default=1, verbose_name=_("شماره تخصیص"))
    returned_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_("مجموع بودجه برگشتی"))

    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    is_locked = models.BooleanField(default=False, verbose_name=_("قفل‌شده"))
    is_stopped = models.BooleanField(default=False, verbose_name=_("متوقف‌شده"))

    created_at = models.DateTimeField(_( 'تاریخ ایجاد ' ), auto_now_add=True,help_text=_('تاریخ ایجاد بودجه . خودکار سیستم '))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, related_name='budget_allocations_created', verbose_name=_("ایجادکننده"))

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
        logger.debug(f"Cleaning BudgetAllocation: allocated_amount={self.allocated_amount}, allocation_type={self.allocation_type}")

        # اعتبارسنجی فیلدهای اجباری
        if self.budget_item_id is None:
            raise ValidationError(_("ردیف بودجه اجباری است."))
        if self.organization_id is None:
            raise ValidationError(_("سازمان دریافت‌کننده اجباری است."))
        if self.allocated_amount is None:
            raise ValidationError(_("مبلغ تخصیص نمی‌تواند خالی باشد."))
        if self.allocated_amount <= 0:
            raise ValidationError(_("مبلغ تخصیص باید مثبت باشد."))

        # بررسی سازگاری ردیف بودجه و دوره بودجه
        if self.budget_period and self.budget_item:
            if self.budget_item.budget_period != self.budget_period:
                raise ValidationError(_("ردیف بودجه باید متعلق به دوره بودجه انتخاب‌شده باشد."))

        # بررسی تاریخ تخصیص
        if self.budget_period and self.allocation_date:
            allocation_date = self.allocation_date
            if hasattr(allocation_date, "date"):
                allocation_date = allocation_date.date()
            if not (self.budget_period.start_date <= allocation_date <= self.budget_period.end_date):
                raise ValidationError(_("تاریخ تخصیص باید در بازه دوره بودجه باشد."))

        # بررسی آستانه هشدار
        if self.warning_threshold is not None and not (0 <= self.warning_threshold <= 100):
            raise ValidationError(_("آستانه اخطار باید بین ۰ تا ۱۰۰ باشد."))

        # بررسی باقی‌مانده دوره بودجه
        remaining_budget = self.budget_period.get_remaining_amount()
        if self.pk:
            current_allocation = BudgetAllocation.objects.filter(pk=self.pk).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
            remaining_budget += current_allocation
        if self.allocated_amount > remaining_budget:
            raise ValidationError(_(
                f"مبلغ تخصیص ({self.allocated_amount:,.0f} ریال) بیشتر از باقی‌مانده دوره بودجه ({remaining_budget:,.0f} ریال) است."
            ))

        # اعتبارسنجی درصد قفل‌شده
        locked_amount = self.budget_period.get_locked_amount()
        available_for_allocation = remaining_budget - locked_amount
        if self.allocated_amount > available_for_allocation:
            raise ValidationError(_(
                f"نمی‌توان تخصیص داد. مبلغ تخصیص ({self.allocated_amount:,.0f} ریال) بیشتر از مقدار مجاز ({available_for_allocation:,.0f} ریال) است."
                f"حداقل {self.budget_period.locked_percentage}% از بودجه باید قفل بماند."
            ))

        logger.debug("Clean validation passed (Model IS : BudgetsAllocations )")

    def get_remaining_amount(self):
        """محاسبه بودجه باقی‌مانده تخصیص پروژه"""
        allocated = self.allocated_amount
        spent_amount = Tankhah.objects.filter(
            project_budget_allocation=self,  # تأیید شده
            status__in=['APPROVED', 'PAID']
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        pending_amount = Tankhah.objects.filter(
            project_budget_allocation=self,  # تأیید شده
            status__in=['DRAFT', 'PENDING']
        ).exclude(pk=self.pk).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        return allocated - (spent_amount + pending_amount)

    def get_locked_amount(self):
        """محاسبه مقدار قفل‌شده تخصیص"""
        try:
            return calculate_threshold_amount(self.allocated_amount, self.locked_percentage)
        except Exception as e:
            logger.error(f"Error in get_locked_amount for BudgetAllocation {self.pk}: {str(e)}")
            return Decimal('0')

    def get_warning_amount(self):
        """محاسبه آستانه هشدار تخصیص"""
        try:
            return calculate_threshold_amount(self.allocated_amount, self.warning_threshold)
        except Exception as e:
            logger.error(f"Error in get_warning_amount for BudgetAllocation {self.pk}: {str(e)}")
            return Decimal('0')

    def get_actual_remaining_amount(self):
        """محاسبه باقی‌مانده واقعی بر اساس تراکنش‌ها"""
        transactions_sum = self.transactions.aggregate(
            consumption=Sum('amount', filter=Q(transaction_type='CONSUMPTION')),
            adjustment_decrease=Sum('amount', filter=Q(transaction_type='ADJUSTMENT_DECREASE')),
            returns=Sum('amount', filter=Q(transaction_type='RETURN')),
            adjustment_increase=Sum('amount', filter=Q(transaction_type='ADJUSTMENT_INCREASE')),
        )
        consumed = (transactions_sum['consumption'] or Decimal('0')) + (transactions_sum['adjustment_decrease'] or Decimal('0'))
        added_back = (transactions_sum['returns'] or Decimal('0')) + (transactions_sum['adjustment_increase'] or Decimal('0'))
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
        """به‌روزرسانی وضعیت قفل تخصیص"""
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

    def save(self, *args, **kwargs):
        logger.debug(f"Starting save for BudgetAllocation (pk={self.pk}, allocated_amount={self.allocated_amount})")
        try:
            with transaction.atomic():
                self.clean()
                is_locked, is_active = self.update_lock_status()
                self.is_locked = is_locked
                self.is_active = is_active
                super().save(*args, **kwargs)
                logger.info(f"BudgetAllocation saved with ID: {self.pk}")
                status, message = self.check_allocation_status()
                logger.debug(f"Allocation status: {status}, message: {message}")
                if status in ('warning', 'completed', 'stopped'):
                    self.send_notification(status, message)
                    logger.info(f"Sent notification for status: {status}")
        except Exception as e:
            logger.error(f"Error saving BudgetAllocation: {str(e)}", exc_info=True)
            raise

    def send_notification(self, status, message):
        """ارسال اعلان به کاربران مرتبط"""
        from accounts.models import CustomUser
        from django.db.models import Q
        try:
            # فقط کاربران فعال مرتبط با سازمان تخصیص
            recipients = CustomUser.objects.filter(
                userpost__post__organization=self.organization,
                is_active=True
            ).distinct()
            # فرض می‌کنیم تابع send_notification در core.utils تعریف شده است
            send_notification(self, status, message, recipients)
            logger.info(f"Notification sent for BudgetAllocation {self.pk}: {status} - {message}")
        except Exception as e:
            logger.error(f"Error sending notification for BudgetAllocation {self.pk}: {str(e)}")
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

    def __str__(self):
        if self.budget_period.name:
            return f"{self.budget_period.name} - {self.name} - {self.organization.name}"
        else:
            return f"{self.name} - {self.organization.name}-بدون ردیف بودجه"

    def clean(self):
        super().clean()
        if not self.name:
            raise ValidationError(_("نام ردیف بودجه نمی‌تواند خالی باشد."))
""" BudgetTransaction (تراکنش بودجه):"""
class BudgetTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('ALLOCATION', _('تخصیص اولیه')),
        ('CONSUMPTION', _('مصرف')),
        ('ADJUSTMENT_INCREASE', _('افزایش تخصیص')),
        ('ADJUSTMENT_DECREASE', _('کاهش تخصیص')),
        ('RETURN', _('بازگشت')),
    )
    allocation = models.ForeignKey('BudgetAllocation', on_delete=models.CASCADE, related_name='transactions',
                                   verbose_name=_("تخصیص بودجه"))
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name=_("نوع تراکنش"))
    amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ"))
    related_tankhah = models.ForeignKey('tankhah.Tankhah', on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name=_("تنخواه مرتبط"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, verbose_name=_("کاربر"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    transaction_id = models.CharField(max_length=50, unique=True, verbose_name=_("شناسه تراکنش"))

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
        """اعتبارسنجی تراکنش بازگشت"""
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
            return False, _(f"مبلغ بازگشت ({self.amount:,.0f} ریال) نمی‌تواند بیشتر از مبلغ تخصیص‌یافته ({self.allocation.allocated_amount:,.0f} ریال) باشد.")

        remaining_budget = self.allocation.get_remaining_amount()
        if self.amount > remaining_budget:
            logger.error(
                f"Return amount {self.amount:,.0f} exceeds remaining_budget {remaining_budget:,.0f} "
                f"for allocation ID: {self.allocation.pk}"
            )
            return False, _(f"مبلغ بازگشت ({self.amount:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) باشد.")

        return True, None

    def clean(self):
        """اعتبارسنجی مدل"""
        logger.debug(f"Cleaning BudgetTransaction: amount={self.amount}, type={self.transaction_type}, allocation ID={self.allocation.pk}")
        if self.transaction_type == 'RETURN':
            is_valid, error_message = self.validate_return()
            if not is_valid:
                raise ValidationError(error_message)
            if self.amount <= 0:
                raise ValidationError(_("مبلغ بازگشت باید مثبت باشد."))
        logger.info(f"BudgetTransaction validated successfully for allocation ID: {self.allocation.pk}")

    def save(self, *args, **kwargs):
        """ذخیره تراکنش با به‌روزرسانی تخصیص و دوره بودجه"""
        logger.debug(f"Starting save for BudgetTransaction: amount={self.amount}, type={self.transaction_type}, allocation ID={self.allocation.pk}")
        try:
            with transaction.atomic():
                if not self.transaction_id:
                    import uuid
                    self.transaction_id = f"TX-{self.transaction_type}-{self.allocation.pk}-{uuid.uuid4().hex[:12]}"
                    logger.info(f"Generated transaction_id: {self.transaction_id}")

                self.clean()
                super().save(*args, **kwargs)
                logger.info(f"BudgetTransaction saved with ID: {self.pk}")

                # به‌روزرسانی تخصیص برای تراکنش بازگشت
                if self.transaction_type == 'RETURN':
                    # کاهش allocated_amount و افزایش returned_amount تخصیص
                    self.allocation.allocated_amount -= self.amount
                    self.allocation.returned_amount += self.amount
                    self.allocation.save(update_fields=['allocated_amount', 'returned_amount'])
                    logger.debug(f"Updated BudgetAllocation {self.allocation.pk}: allocated_amount={self.allocation.allocated_amount}, returned_amount={self.allocation.returned_amount}")

                    # به‌روزرسانی returned_amount دوره بودجه بدون فراخوانی save
                    budget_period = self.allocation.budget_period
                    budget_period.returned_amount = BudgetTransaction.objects.filter(
                        allocation__budget_period=budget_period,
                        transaction_type='RETURN'
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                    BudgetPeriod.objects.filter(pk=budget_period.pk).update(returned_amount=budget_period.returned_amount)
                    logger.debug(f"Updated BudgetPeriod {budget_period.pk}: returned_amount={budget_period.returned_amount}")

        except Exception as e:
            logger.error(f"Error saving BudgetTransaction: {str(e)}", exc_info=True)
            raise

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount:,.0f} - {self.timestamp.strftime('%Y/%m/%d')}"
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
    is_active= models.BooleanField(verbose_name=_('فعال'))
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
    # return f"PO-{timezone.now().strftime('%Y%m%d')}-{last_pk + 1:04d}"
#
"""PaymentOrder (دستور پرداخت):"""
#--------------------------------------
class PaymentOrder(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', _('پیش‌نویس')),
        ('PENDING_APPROVAL', _('در انتظار تأیید/امضا')),
        ('APPROVED', _('تأیید شده/آماده پرداخت')),
        ('ISSUED_TO_TREASURY', _('ارسال به خزانه')),
        ('PAID', _('پرداخت شده')),
        ('REJECTED', _('رد شده')),
        ('CANCELLED', _('لغو شده')),
    )

    tankhah = models.ForeignKey(Tankhah, on_delete=models.CASCADE, related_name='payment_orders',verbose_name=_("تنخواه"))
    related_tankhah = models.ForeignKey(Tankhah, on_delete=models.SET_NULL, null=True, blank=True,related_name='payment_orders_tankhah', verbose_name=_('تنخواه مرتبط')    )
    order_number = models.CharField(_('شماره دستور پرداخت'), max_length=50, unique=True, default=None)
    issue_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ صدور"))
    amount = models.DecimalField(_('مبلغ (ریال)'), max_digits=25, decimal_places=2)
    payee = models.ForeignKey(Payee, on_delete=models.PROTECT, related_name='payment_orders',verbose_name=_('دریافت‌کننده')    )
    description = models.TextField(_('شرح پرداخت'), blank=True)
    payment_id = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شناسه پرداخت"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', verbose_name=_("وضعیت"))
    created_by_post = models.ForeignKey(        Post, on_delete=models.SET_NULL, null=True, verbose_name=_("پست ایجادکننده")    )
    min_signatures = models.IntegerField(default=1, verbose_name=_("حداقل تعداد امضا"))
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='created_payment_orders',verbose_name=_('ایجادکننده')    )
    payment_date = models.DateField(null=True, blank=True, verbose_name=_("تاریخ پرداخت"))
    payee_account_number = models.IntegerField(_('شماره حساب') , blank=True, null=True)
    payee_iban = models.IntegerField(_('شبا'),  blank=True, null=True)
    payment_tracking_id = models.CharField(_('شناسه پرداخت'), max_length=200, blank=True, null=True)
    paid_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,related_name='processed_payment_orders', verbose_name=_('پردازش توسط')    )
    related_factors = models.ManyToManyField(Factor, blank=True, related_name='payment_orders', verbose_name= _('فاکتورهای مرتبط ') )
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='payment_orders_organize',verbose_name=_('سازمان'))
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True,related_name='payment_orders', verbose_name=_('پروژه'))
    current_stage = models.ForeignKey(WorkflowStage, on_delete=models.SET_NULL, null=True, blank=True,related_name='payment_orders', verbose_name=_('مرحله فعلی')    )
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
                # اگر کاربر superuser نیست، از سازمان کاربر استفاده کن
                if self.created_by and not self.created_by.is_superuser:
                    user_org = UserPost.objects.filter(
                        user=self.created_by, is_active=True, end_date__isnull=True
                    ).values_list('post__organization', flat=True).first()
                    if user_org:
                        self.organization = Organization.objects.get(pk=user_org)
                    else:
                        raise ValidationError(_('سازمان باید مشخص شود.'))
                else:
                    # برای superuser، سازمان پیش‌فرض یا خطا
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
#--------------------------------------
"""TransactionType (نوع تراکنش):"""
class TransactionType(models.Model):
    """توضیح: تعریف پویا نوع تراکنش‌ها (مثل بیمه، جریمه) با امکان نیاز به تأیید اضافی."""
    name = models.CharField(max_length=250, unique=True, verbose_name=_("نام"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    requires_extra_approval = models.BooleanField(default=False,
                                                  verbose_name=_("نیاز به تأیید اضافی"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,
                                   related_name='transaction_types_created', verbose_name=_("ایجادکننده"))
    category = models.CharField(max_length=50, blank=True, null=True,verbose_name=_('گروه بندی تراکنش‌ها '))
    TRANSACTION_FLOW_CHOICES = [
        ('INFLOW', _('ورودی (افزایش بودجه)')),
        ('OUTFLOW', _('خروجی (کاهش بودجه)')),
        ('CONSUMPTION', _('مصرف بودجه')),  # For expenses
        ('TRANSFER', _('انتقال بودجه')),
        ('RETURN', _('بازگشت بودجه')),
        ('ADJUSTMENT', _('تعدیل بودجه')),  # مثلاً برای اصلاحات
    ]
    transaction_flow = models.CharField(
        max_length=20,
        choices=TRANSACTION_FLOW_CHOICES,
        verbose_name=_("جریان تراکنش"),  # e.g., INFLOW, OUTFLOW, CONSUMPTION
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
"""مدل BudgetReallocation برای انتقال باقی‌مانده بودجه متوقف‌شده."""
class BudgetReallocation(models.Model):
    source_allocation = models.ForeignKey('BudgetAllocation', on_delete=models.CASCADE, related_name='reallocations_from')
    target_allocation = models.ForeignKey('BudgetAllocation', on_delete=models.CASCADE, null=True, related_name='reallocations_to')
    amount = models.DecimalField(max_digits=25, decimal_places=2)
    reallocation_date = models.DateField(default=timezone.now)
    reason = models.TextField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
"""یه جدول تنظیمات (BudgetSettings) برای مدیریت قفل و هشدار در سطوح مختلف:"""
class BudgetSettings(models.Model):
    level = models.CharField(max_length=50, choices=[('PERIOD', 'دوره بودجه'), ('ALLOCATION', 'تخصیص'), ('PROJECT', 'پروژه')])
    locked_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    warning_threshold = models.DecimalField(max_digits=5, decimal_places=2)
    warning_action = models.CharField(max_length=50, choices=[('NOTIFY', 'اعلان'), ('LOCK', 'قفل'), ('RESTRICT', 'محدود')])
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, null=True)
    budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE, null=True, verbose_name=_("دوره بودجه"))

    # ردیابی مدل
    # content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    # object_id = models.PositiveIntegerField()
    # content_object = GenericForeignKey('content_type', 'object_id')
"""مدل BudgetHistory برای لاگ کردن تغییرات بودجه و تخصیص‌ها:"""
# ------------------------------------
"""تاریخچه برای هر بودجه کلان"""
class BudgetHistory(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    # content_object = GenericForeignKey('content_type', 'object_id')
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
    transaction_type = models.CharField(max_length=20, choices=[('ALLOCATION', _('تخصیص')), ('CONSUMPTION', _('مصرف')), ('RETURN', _('برگشت'))],verbose_name=_("نوع تراکنش"))
    transaction_id = models.CharField(max_length=50, unique=True, verbose_name=_("شناسه تراکنش"))


    def __str__(self):
        return f"{self.action} - {self.amount:,} ({self.created_at})"

    class Meta:
        verbose_name = _("تاریخچه بودجه")
        verbose_name_plural = _("تاریخچه‌های بودجه")
        default_permissions = ()
        permissions = [
            ('BudgetHistory_add','افزودن تاریخچه برای هر بودجه کلان'),
            ('BudgetHistory_view',' نمایش تاریخچه هر بودجه کلان'),
            ('BudgetHistory_update','بروزرسانی تاریخچه برای هر بودجه کلان'),
            ('BudgetHistory_delete',' حــذف تاریخچه برای هر بودجه کلان'),
        ]
"""'دسترسی برای جابجایی و برگشت بودجه'"""
class BudgetTransferReturn(models.Model):
    class Meta:
        verbose_name='دسترسی برای جابجایی و برگشت بودجه'
        verbose_name_plural='دسترسی برای جابجایی و برگشت بودجه'
        default_permissions = ()
        permissions = [
            ('BudgetTransfer','دسترسی جابجایی بودجه'),
            ('BudgetReturn','دسترسی برگشت جابجایی بودجه'),
        ]

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

    class Meta:
        verbose_name = _("مرکز هزینه")
        verbose_name_plural = _("مراکز هزینه")

# class BudgetPeriod(models.Model):
#
#     organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, verbose_name=_("دفتر مرکزی"),related_name='budget_periods')
#     name = models.CharField(max_length=100, unique=True, verbose_name=_("نام دوره بودجه"))
#     start_date = models.DateField(verbose_name=_("تاریخ شروع"))
#     end_date = models.DateField(verbose_name=_("تاریخ پایان"))
#     total_amount = models.DecimalField(max_digits=25, decimal_places=0, verbose_name=_("مبلغ کل"))
#     total_allocated = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_("مجموع تخصیص‌ها"))
#     returned_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0,verbose_name=_("مجموع بودجه برگشتی"))
#     is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
#     is_archived = models.BooleanField(default=False, verbose_name=_("بایگانی شده"))
#     is_completed = models.BooleanField(default=False, verbose_name=_("تمام‌شده"))
#     created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,related_name='budget_periods_created', verbose_name=_("ایجادکننده"))
#     locked_percentage = models.IntegerField(default=0, verbose_name=_("درصد قفل‌شده"),help_text=_("درصد بودجه که قفل می‌شود (0-100)"))
#     warning_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=10, verbose_name=_("آستانه اخطار"),help_text=_("درصدی که هشدار نمایش داده می‌شود (0-100)"))
#     warning_action = models.CharField(max_length=50,choices=[('NOTIFY', _("فقط اعلان")), ('LOCK', _("قفل کردن")),('RESTRICT', _("محدود کردن ثبت"))],default='NOTIFY',verbose_name=_("اقدام هشدار") ,
#                                       help_text=_("رفتار سیستم هنگام رسیدن به آستانه هشدار"))
#     allocation_phase = models.CharField(max_length=50, blank=True, verbose_name=_("فاز تخصیص"))
#     description = models.TextField(blank=True, verbose_name=_("توضیحات"))
#
#     lock_condition = models.CharField(max_length=50,choices=[('AFTER_DATE', _("بعد از تاریخ پایان")), ('MANUAL', _("دستی")),
#                                                ('ZERO_REMAINING', _("باقی‌مانده صفر")), ], default='AFTER_DATE',verbose_name=_("شرط قفل"))
#
#     is_locked = models.BooleanField(default=False, verbose_name=_("قفل‌شده"))  # فیلد جدید
#
#     class Meta:
#         verbose_name = _("دوره بودجه")
#         verbose_name_plural = _("دوره‌های بودجه")
#         default_permissions = ()
#         permissions = [
#             ('budgetperiod_add', _("افزودن دوره بودجه")),
#             ('budgetperiod_update', _("بروزرسانی دوره بودجه")),
#             ('budgetperiod_view', _("نمایش دوره بودجه")),
#             ('budgetperiod_delete', _("حذف دوره بودجه")),
#             ('budgetperiod_archive', _("بایگانی دوره بودجه")),
#         ]
#     def __str__(self):
#         return f"{self.name} ({self.organization.code})"
#     def clean(self):
#         # super().clean()
#         # if self.total_allocated > self.total_amount:
#         #     raise ValidationError(_("مجموع تخصیص‌ها نمی‌تواند از مبلغ کل بیشتر باشد."))
#         if not self.start_date or not self.end_date:
#             raise ValidationError(_("تاریخ شروع و پایان نمی‌توانند خالی باشند."))
#         if self.end_date <= self.start_date:
#             raise ValidationError(_("تاریخ پایان باید بعد از تاریخ شروع باشد."))
#         if not (0 <= self.locked_percentage <= 100):
#             raise ValidationError(_("درصد قفل‌شده باید بین 0 تا 100 باشد."))
#         if not (0 <= self.warning_threshold <= 100):
#             raise ValidationError(_("آستانه هشدار باید بین 0 تا 100 باشد."))
#         if self.is_completed and self.is_active:
#             raise ValidationError(_("دوره تمام‌شده نمی‌تواند فعال باشد."))
#     def validate_allocation(self, allocation_amount):
#         """اعتبارسنجی تخصیص با در نظر گرفتن درصد قفل"""
#         remaining = self.get_remaining_amount()
#         locked_amount = self.get_locked_amount()
#         available_for_allocation = remaining - locked_amount
#
#         if allocation_amount > available_for_allocation:
#             raise ValidationError(
#                 _(
#                     f"نمی‌توان تخصیص داد. مبلغ تخصیص ({allocation_amount:,.0f} ریال) بیشتر از مقدار مجاز ({available_for_allocation:,.0f} ریال) است."
#                     f"حداقل {self.locked_percentage}% از بودجه باید قفل بماند."
#                 )
#             )
#     # def update_lock_status(self):
#     #     """به‌روزرسانی وضعیت قفل بر اساس میزان بودجه"""
#     #     remaining_amount = self.get_remaining_amount()
#     #     locked_amount = self.get_locked_amount()
#     #     now_date = timezone.now().date()
#     #
#     #     if self.lock_condition == 'ZERO_REMAINING' and remaining_amount <= locked_amount:
#     #         self.is_locked = True
#     #         self.is_active = False
#     #         # بررسی شرایط قفل
#     #     elif self.lock_condition == 'AFTER_DATE' and self.end_date < now_date:
#     #         self.is_locked = True
#     #         self.is_active = False
#     #     elif self.lock_condition == 'MANUAL':
#     #     # قفل دستی توسط کاربر اعمال می‌شود
#     #         pass
#     #     elif self.lock_condition == 'COMBINED':
#     #         # ترکیبی: اگر تاریخ گذشته یا باقی‌مانده صفر باشد
#     #         self.is_locked = (self.end_date < now_date) or (remaining_amount <= 0)
#     #     else:
#     #         self.is_locked = False
#     #
#     #     self.save(update_fields=['is_locked', 'is_active'])
#     #
#     #     # قفل کردن تنخواه‌ها و تخصیص‌ها
#     #     if self.is_locked:
#     #         self.allocations.update(is_locked=True, is_active=False)
#     #         Tankhah.objects.filter(allocation__budget_period=self).update(is_active=False)
#     def update_lock(self, status):
#         """Update lock status without triggering save."""
#         try:
#             locked = self.get_locked_amount()
#             remaining = self.get_remaining_amount()
#             if remaining <= locked:
#                 self.is_locked = True
#                 self.is_active = True
#                 logger.debug(f"Locked BudgetPeriod {self.pk}")
#             else:
#                 self.is_locked = False
#                 self.is_active = True
#             BudgetPeriod.objects.filter(pk=self.pk).update(is_locked=self.is_locked, is_active=self.is_active)
#         except Exception as e:
#             logger.error(f"Error updating lock status for BudgetPeriod {self.pk}: {str(e)}")
#
#     def get_lock_message(self):
#         """پیام مناسب برای وضعیت قفل"""
#         if self.lock_condition == 'AFTER_DATE' and self.is_locked:
#             return _("تاریخ دوره بودجه به پایان رسیده و قفل شده است.")
#         elif self.lock_condition == 'ZERO_REMAINING' and self.is_locked:
#             return _("بودجه باقیمانده دوره صفر یا کمتر است و دوره قفل شده است.")
#         elif self.lock_condition == 'COMBINED' and self.is_locked:
#             return _("دوره بودجه به دلیل پایان تاریخ یا اتمام بودجه قفل شده است.")
#         elif self.lock_condition == 'MANUAL' and self.is_locked:
#             return _("دوره بودجه به صورت دستی قفل شده است.")
#         return _("دوره بودجه فعال و باز است.")
#     def get_remaining_amount(self):
#         """محاسبه بودجه باقی‌مانده دوره"""
#         """منطق متفاوت است (بر اساس تخصیص‌ها و نه تراکنش‌ها محاسبه می‌شود)."""
#         from django.db.models import Sum
#         from decimal import Decimal
#         total_allocated = self.allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
#         return max(self.total_amount - total_allocated + self.returned_amount, Decimal('0'))
#     def send_notification(self, status, message):
#         recipients = CustomUser.objects.filter(
#             organizations=self.organization,
#             roles__name__in=['Financial Manager', 'Budget Manager']
#         ).distinct()
#         send_notification(self, status, message, recipients)
#     def get_locked_amount(self):
#         """    محاسبه مقدار بر اساس درصد (برای قفل یا هشدار)."""
#         try:
#             return calculate_threshold_amount(self.total_amount, self.locked_percentage)
#         except Exception as e:
#             logger.error(f"Error in get_locked_amount for BudgetPeriod {self.pk}: {str(e)}")
#             return Decimal('0')
#     # def check_warning_threshold(self):
#     #     """Checks if the remaining budget has reached the warning threshold."""
#     #     """محاسبه آستانه هشدار دوره"""
#     #     if self.warning_threshold <= 0 or self.total_amount <= 0: # No warning if threshold or total is zero
#     #         return False, None
#     #
#     #     remaining_percentage = (self.get_remaining_amount() / self.total_amount) * Decimal('100')
#     #     if remaining_percentage <= self.warning_threshold:
#     #         warning_message = _("هشدار: بودجه باقیمانده دوره به آستانه {}% رسیده است (باقیمانده: {:,}).").format(
#     #             self.warning_threshold, self.get_remaining_amount()
#     #         )
#     #         return True, warning_message
#     #     return False, None
#     def get_warning_amount(self):
#         """محاسبه آستانه هشدار دوره"""
#         try:
#             return calculate_threshold_amount(self.total_amount, self.warning_threshold)
#         except Exception as e:
#             logger.error(f"Error in get_warning_amount for BudgetPeriod {self.pk}: {str(e)}")
#             return Decimal('0')
#
#     @property # Use property for easy access like a field
#     def is_period_locked(self):
#         """Checks if the budget period is currently locked based on conditions."""
#         now_date = timezone.now().date()
#
#         # Condition 1: Manual Lock (Assuming you add an 'is_manually_locked' field)
#         # if self.is_manually_locked:
#         #    return True, _("دوره بودجه به صورت دستی قفل شده است.")
#
#         # Condition 2: After End Date
#         if self.lock_condition == 'AFTER_DATE' and self.end_date < now_date:
#             # Optionally update is_active here if not done elsewhere
#             # if self.is_active:
#             #     self.is_active = False
#             #     self.save(update_fields=['is_active'])
#             return True, _("تاریخ دوره بودجه به پایان رسیده و قفل شده است.")
#
#         # Condition 3: Zero Remaining (or below zero)
#         # We need the *actual* remaining amount here
#         if self.lock_condition == 'ZERO_REMAINING' and self.get_remaining_amount() <= 0:
#              # Optionally update is_completed/is_active here
#              # if not self.is_completed:
#              #    self.is_completed = True
#              #    self.is_active = False
#              #    self.save(update_fields=['is_completed', 'is_active'])
#             return True, _("بودجه باقیمانده دوره صفر یا کمتر است و دوره قفل شده است.")
#
#         # Condition 4: Locked Percentage (Based on *allocated* amount, not remaining)
#         # This interpretation means you cannot allocate more than (100 - locked_percentage)%
#         # It usually doesn't prevent spending the allocated amount.
#         # If the intention is to lock *spending* when remaining is below locked percentage:
#         # remaining = self.get_remaining_amount()
#         # locked_threshold_amount = (self.total_amount * self.locked_percentage) / Decimal('100')
#         # if remaining <= locked_threshold_amount:
#         #     return True, _("بودجه باقیمانده به حد درصد قفل شده ({}) رسیده است.").format(self.locked_percentage)
#
#         return False, _("دوره بودجه فعال و باز است.")
#     # def apply_warning_action(self):
#     #     """اجرای اقدام هشدار"""
#     #     is_warning, message = self.check_warning_threshold()
#     #     if not is_warning:
#     #         return
#     #     if self.warning_action == 'NOTIFY':
#     #         self.log_action("WARNING", message)
#     #     elif self.warning_action == 'LOCK':
#     #         self.is_locked = True
#     #         self.is_active = False
#     #         self.save(update_fields=['is_locked', 'is_active'])
#     #         self.log_action("LOCK", _("دوره بودجه به دلیل رسیدن به آستانه اخطار قفل شد."))
#     #         self.send_notification("locked", _("دوره بودجه به دلیل رسیدن به آستانه اخطار قفل شد."))
#     #     elif self.warning_action == 'RESTRICT':
#     #         self.is_active = False
#     #         self.save(update_fields=['is_active'])
#     #         self.log_action("RESTRICT", _("ثبت تراکنش‌های جدید برای این دوره بودجه محدود شد."))
#     #         self.send_notification("restricted", _("ثبت تراکنش‌های جدید برای این دوره بودجه محدود شد."))
#     def apply_warning_action(self):
#         """اعمال اقدام هشدار"""
#         try:
#             status, _ = self.check_budget_status_no_save()
#             if status == 'warning' and self.warning_action == 'LOCK':
#                 self.is_locked = True
#                 BudgetPeriod.objects.filter(pk=self.pk).update(is_locked=True)
#                 logger.debug(f"Applied LOCK action for BudgetPeriod {self.pk}")
#             elif status == 'warning' and self.warning_action == 'RESTRICT':
#                 logger.debug(f"Applied RESTRICT action for BudgetPeriod {self.pk}")
#                 # منطق محدود کردن ثبت تراکنش‌ها
#         except Exception as e:
#             logger.error(f"Error applying warning action for BudgetPeriod {self.pk}: {str(e)}")
#
#
#     def log_action(self, action, message):
#         BudgetHistory.objects.create(
#             content_type=ContentType.objects.get_for_model(self),
#             object_id=self.id,
#             action=action,
#             created_by=self.created_by,
#             details=message,
#             transaction_type='SYSTEM',
#             transaction_id=f"SYS-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"
#         )
#     # def check_budget_status_no_save(self):
#     #     """
#     #     نسخه بدون ذخیره‌سازی از check_budget_status برای جلوگیری از recursion.
#     #     """
#     #     cache_key = f"budget_status_{self.pk}_no_filters"
#     #     from django.core.cache import cache
#     #     cached_result = cache.get(cache_key)
#     #     if cached_result is not None:
#     #         logger.debug(f"Returning cached budget_status for {cache_key}: {cached_result}")
#     #         return cached_result
#     #
#     #     try:
#     #         remaining = self.get_remaining_amount()
#     #         locked = self.get_locked_amount()
#     #         warning = self.get_warning_amount()
#     #
#     #         if not self.is_active:
#     #             result = 'inactive', _('دوره غیرفعال است.')
#     #         elif self.is_completed:
#     #             result = 'completed', _('بودجه تمام‌شده است.')
#     #         elif remaining <= 0 and self.lock_condition == 'ZERO_REMAINING':
#     #             result = 'completed', _('بودجه به صفر رسیده و تمام‌شده است.')
#     #         elif self.lock_condition == 'AFTER_DATE' and self.end_date < timezone.now().date():
#     #             result = 'locked', _('دوره به دلیل پایان تاریخ قفل شده است.')
#     #         elif self.lock_condition == 'MANUAL' and remaining <= locked:
#     #             result = 'locked', _('بودجه به حد قفل‌شده رسیده است.')
#     #         elif remaining <= warning:
#     #             result = 'warning', _('بودجه به آستانه هشدار رسیده است.')
#     #         else:
#     #             result = 'normal', _('وضعیت عادی')
#     #
#     #         from django.core.cache import cache
#     #         cache.set(cache_key, result, timeout=300)
#     #         logger.debug(f"check_budget_status_no_save: obj={self}, result={result}")
#     #         return result
#     #     except Exception as e:
#     #         logger.error(f"Error in check_budget_status_no_save for BudgetPeriod {self.pk}: {str(e)}")
#     #         return 'unknown', _('وضعیت نامشخص')
#     def check_budget_status_no_save(self, filters=None):
#         """بررسی وضعیت بودجه بدون ذخیره‌سازی"""
#         cache_key = f"budget_status_{self.pk}_{hash(str(filters)) if filters else 'no_filters'}"
#         cached_result = cache.get(cache_key)
#         if cached_result is not None:
#             logger.debug(f"Returning cached budget_status for {cache_key}: {cached_result}")
#             return cached_result
#
#         try:
#             remaining = self.get_remaining_amount()
#             locked = self.get_locked_amount()
#             warning = self.get_warning_amount()
#
#             if not self.is_active:
#                 result = 'inactive', _('دوره غیرفعال است.')
#             elif self.is_completed:
#                 result = 'completed', _('بودجه تمام‌شده است.')
#             elif remaining <= 0 and self.lock_condition == 'ZERO_REMAINING':
#                 result = 'completed', _('بودجه به صفر رسیده و تمام‌شده است.')
#             elif self.lock_condition == 'AFTER_DATE' and self.end_date < timezone.now().date():
#                 result = 'locked', _('دوره به دلیل پایان تاریخ قفل شده است.')
#             elif self.lock_condition == 'MANUAL' and remaining <= locked:
#                 result = 'locked', _('بودجه به حد قفل‌شده رسیده است.')
#             elif remaining <= warning:
#                 result = 'warning', _('بودجه به آستانه هشدار رسیده است.')
#             else:
#                 result = 'normal', _('وضعیت عادی')
#             cache.set(cache_key, result, timeout=300)
#             logger.debug(f"check_budget_status_no_save: obj={self}, result={result}")
#             return result
#         except Exception as e:
#             logger.error(f"Error in check_budget_status_no_save for BudgetPeriod {self.pk}: {str(e)}")
#             return 'unknown', _('وضعیت نامشخص')
#     def update_lock_status(self):
#         """به‌روزرسانی وضعیت قفل بدون ذخیره"""
#         try:
#             remaining = self.get_remaining_amount()
#             locked = self.get_locked_amount()
#             if remaining <= locked:
#                 self.is_locked = True
#                 self.is_active = False
#             else:
#                 self.is_locked = False
#                 self.is_active = True
#             BudgetPeriod.objects.filter(pk=self.pk).update(is_locked=self.is_locked, is_active=self.is_active)
#             logger.debug(f"Updated lock status for BudgetPeriod {self.pk}: is_locked={self.is_locked}, is_active={self.is_active}")
#         except Exception as e:
#             logger.error(f"Error updating lock status for BudgetPeriod {self.pk}: {str(e)}")
#
#     def save(self, *args, **kwargs):
#         logger.debug(f"Starting save for BudgetPeriod (pk={self.pk})")
#         try:
#             with transaction.atomic():
#                 self.full_clean()
#                 super().save(*args, **kwargs)
#                 logger.info(f"BudgetPeriod saved with ID: {self.pk}")
#                 self.apply_warning_action()
#                 self.update_lock_status()  # اصلاح: استفاده از update_lock_status
#                 status, message = self.check_budget_status_no_save()
#                 if status in ('warning', 'locked', 'completed'):
#                     self.send_notification(status, message)
#                     logger.info(f"Notification sent for status: {status}")
#         except Exception as e:
#             logger.error(f"Error saving BudgetPeriod: {str(e)}", exc_info=True)
#             raise

# class BudgetTransaction(models.Model):
#     TRANSACTION_TYPES = (
#         ('ALLOCATION', _('تخصیص اولیه')),
#         ('CONSUMPTION', _('مصرف')),
#         ('ADJUSTMENT_INCREASE', _('افزایش تخصیص')),
#         ('ADJUSTMENT_DECREASE', _('کاهش تخصیص')),
#         ('RETURN', _('بازگشت')),
#     )
#     allocation = models.ForeignKey('BudgetAllocation', on_delete=models.CASCADE,related_name='transactions', verbose_name=_("تخصیص بودجه"))
#     transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES,verbose_name=_("نوع تراکنش"))
#     amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ"))
#     related_tankhah = models.ForeignKey('tankhah.Tankhah', on_delete=models.SET_NULL, null=True, blank=True,verbose_name=_("تنخواه مرتبط"))
#     timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان"))
#     created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,verbose_name=_("کاربر"))
#     description = models.TextField(blank=True, verbose_name=_("توضیحات"))
#     transaction_id = models.CharField(max_length=50, unique=True, verbose_name=_("شناسه تراکنش"))
#
#     class Meta:
#         verbose_name = _("تراکنش بودجه")
#         verbose_name_plural = _("تراکنش‌های بودجه")
#         default_permissions = ()
#         permissions = [
#             ('BudgetTransaction_add', 'افزودن تراکنش بودجه'),
#             ('BudgetTransaction_update', 'بروزرسانی تراکنش بودجه'),
#             ('BudgetTransaction_delete', 'حــذف تراکنش بودجه'),
#             ('BudgetTransaction_view', _('نمایش تراکنش بودجه')),
#             ('BudgetTransaction_return', _('برگشت تراکنش بودجه')),
#         ]
#
#     def validate_return(self):
#         """اعتبارسنجی تراکنش بازگشت"""
#         if self.transaction_type != 'RETURN':
#             return True, None
#         logger.debug(f"Validating RETURN transaction: amount={self.amount}, allocation ID={self.allocation.pk}")
#         consumed = BudgetTransaction.objects.filter(allocation=self.allocation,transaction_type='CONSUMPTION').aggregate(total=Sum('amount'))['total'] or Decimal('0')
#         returned = BudgetTransaction.objects.filter(allocation=self.allocation,transaction_type='RETURN').aggregate(total=Sum('amount'))['total'] or Decimal('0')
#         total_consumed = consumed - returned
#         if self.amount > total_consumed:
#             return False, _(f"مبلغ بازگشت ({self.amount:,.0f} ریال) نمی‌تواند بیشتر از مصرف خالص ({total_consumed:,.0f} ریال) باشد.")
#         remaining_budget = self.allocation.get_remaining_amount()
#         if self.amount > remaining_budget:
#             return False, _(f"مبلغ بازگشت ({self.amount:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) باشد.")
#         return True, None
#
#     def save(self, *args, **kwargs):
#         from django.core.exceptions import ValidationError
#         from django.contrib.contenttypes.models import ContentType
#         from django.db import transaction
#
#         # 1. Generate transaction ID if missing
#         if not self.transaction_id:
#             timestamp_str = timezone.now().strftime('%Y%m%d%H%M%S%f')
#             self.transaction_id = f"TX-{self.transaction_type[:3]}-{self.allocation_id}-{timestamp_str}"
#             logger.info(f"Generated transaction_id: {self.transaction_id}")
#
#         # 2. اعتبارسنجی تراکنش بازگشت
#         if self.transaction_type == 'RETURN':
#             is_valid, error_message = self.validate_return()
#             if not is_valid:
#                 logger.error(f"Validation failed for RETURN transaction: {error_message}")
#                 raise ValidationError(error_message)
#
#         # 3. بررسی بودجه برای تراکنش CONSUMPTION
#         if self.transaction_type == 'CONSUMPTION':
#             remaining = self.allocation.get_remaining_amount()
#             if self.amount > remaining:
#                 logger.error(f"CONSUMPTION transaction amount {self.amount} exceeds remaining {remaining}")
#                 raise ValidationError(_("مبلغ مصرف بیشتر از باقی‌مانده تخصیص است."))
#
#         try:
#             with transaction.atomic():
#                 # 4. به‌روزرسانی تخصیص برای تراکنش‌های RETURN
#                 if self.transaction_type == 'RETURN':
#                     if not self.allocation.budget_period.is_active:
#                         logger.error(f"Cannot return from inactive budget period: {self.allocation.budget_period.id}")
#                         raise ValidationError(_("نمی‌توان از دوره غیرفعال بودجه برگشت داد."))
#
#                     self.allocation.allocated_amount -= self.amount
#                     self.allocation.returned_amount += self.amount
#                     self.allocation.budget_period.total_allocated -= self.amount
#                     self.allocation.budget_period.returned_amount += self.amount
#
#                     self.allocation.save(update_fields=['allocated_amount', 'returned_amount'])
#                     self.allocation.budget_period.save(update_fields=['total_allocated', 'returned_amount'])
#
#                     BudgetHistory.objects.create(
#                         content_type=ContentType.objects.get_for_model(BudgetAllocation),
#                         object_id=self.allocation.id,
#                         action='RETURN',
#                         amount=self.amount,
#                         created_by=self.created_by,
#                         details=f"برگشت {self.amount:,} از تخصیص {self.allocation.id} به دوره بودجه {self.allocation.budget_period.name}",
#                         transaction_type='RETURN',
#                         transaction_id=f"RET-{self.transaction_id}"
#                     )
#
#                     self.allocation.send_notification(
#                         'return',
#                         f"مبلغ {self.amount:,.0f} ریال از تخصیص {self.allocation.id} برگشت داده شد."
#                     )
#
#                 # 5. ذخیره تراکنش
#                 super().save(*args, **kwargs)
#                 logger.debug(f"BudgetTransaction {self.pk} ({self.transaction_id}) saved.")
#
#                 # 6. به‌روزرسانی وضعیت و ارسال اعلان
#                 status, message = check_budget_status(self.allocation.budget_period)
#                 if status in ('warning', 'locked', 'completed', 'stopped'):
#                     self.allocation.send_notification(status, message)
#
#         except Exception as e:
#             logger.error(f"Error saving BudgetTransaction {self.transaction_id}: {str(e)}", exc_info=True)
#             raise
#
#     # def clean(self):
#     #     super().clean()
#     #     # اگر دوره بودجه محدود شده باشد، از ثبت تراکنش جلوگیری شود
#     #     if self.allocation.budget_period.warning_action == 'RESTRICT' and self.allocation.budget_period.is_active == False:
#     #         raise ValidationError(_("ثبت تراکنش جدید به دلیل محدودیت دوره بودجه ممکن نیست."))
#
#
#     def clean(self):
#         if self.transaction_type == 'RETURN':
#             consumed = BudgetTransaction.objects.filter(
#                 allocation=self.allocation,
#                 transaction_type='CONSUMPTION'
#             ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#             returned = BudgetTransaction.objects.filter(
#                 allocation=self.allocation,
#                 transaction_type='RETURN'
#             ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#             net_consumed = consumed - returned
#             if self.amount > net_consumed:
#                 raise ValidationError(
#                     _(
#                         f"مبلغ بازگشت ({self.amount:,.0f} ریال) نمی‌تواند بیشتر از مصرف خالص "
#                         f"({net_consumed:,.0f} ریال) باشد."
#                     )
#                 )
#
#
#
#     def __str__(self):
#         return f"{self.get_transaction_type_display()} - {self.amount:,.0f} - {self.timestamp.strftime('%Y/%m/%d')}"

# """تخصیص بودجه به پروژه و زیر پروژه """
# class ProjectBudgetAllocation(models.Model):
#     """
#     تخصیص بودجه از BudgetAllocation شعبه به پروژه یا زیرپروژه.
#     توضیح: این مدل بودجه شعبه رو به پروژه یا زیرپروژه وصل می‌کنه و تاریخچه تخصیص رو نگه می‌داره.
#     """
#     budget_allocation = models.ForeignKey('budgets.BudgetAllocation', on_delete=models.CASCADE, related_name='project_allocations', verbose_name=_("تخصیص بودجه شعبه"))
#     project = models.ForeignKey('core.Project', on_delete=models.CASCADE, related_name='budget_allocations', verbose_name=_("پروژه"))
#     subproject = models.ForeignKey('core.SubProject', on_delete=models.CASCADE, null=True, blank=True, related_name='budget_allocations', verbose_name=_("زیرپروژه"))
#     allocated_amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ تخصیص"))
#     allocation_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ تخصیص"))
#     returned_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_("مجموع بودجه برگشتی"))
#     created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, related_name='project_budget_allocations_created', verbose_name=_("ایجادکننده"))
#     description = models.TextField(blank=True, verbose_name=_("توضیحات"))
#     is_active = models.BooleanField(default=True, verbose_name=_('فعال'))
#     is_locked = models.BooleanField(default=False, verbose_name=_("قفل‌شده"))
#     locked_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_("درصد قفل‌شده"))
#
#     def __str__(self):
#         target = self.subproject.name if self.subproject else self.project.name
#         jalali_date = jdatetime.date.fromgregorian(date=self.allocation_date).strftime('%Y/%m/%d')
#         return f"{target} - {self.allocated_amount:,} ({jalali_date})"
#
#     class Meta:
#         verbose_name = _("تخصیص بودجه پروژه")
#         verbose_name_plural = _("تخصیص‌های بودجه پروژه")
#         default_permissions = ()
#         permissions = [
#             ('ProjectBudgetAllocation_add', _('افزودن تخصیص بودجه پروژه')),
#             ('ProjectBudgetAllocation_view', _('نمایش تخصیص بودجه پروژه')),
#             ('ProjectBudgetAllocation_update', _('بروزرسانی تخصیص بودجه پروژه')),
#             ('ProjectBudgetAllocation_delete', _('حذف تخصیص بودجه پروژه')),
#             ('ProjectBudgetAllocation_Head_Office', 'تخصیص بودجه مجموعه پروژه(دفتر مرکزی)🏠'),
#             ('ProjectBudgetAllocation_Branch', 'تخصیص بودجه مجموعه پروژه(شعبه)🏠'),
#         ]
#         indexes = [
#             models.Index(fields=['project']),
#             models.Index(fields=['subproject']),
#         ]
#
#     def get_remaining_amount(self):
#         """محاسبه بودجه باقی‌مانده تخصیص پروژه"""
#         return calculate_remaining_amount(self, amount_field='allocated_amount', model_name='BudgetAllocation')
#
#     def get_locked_amount(self):
#         """محاسبه مقدار قفل‌شده بر اساس درصد"""
#         return calculate_threshold_amount(self.allocated_amount, self.locked_percentage)
#
#     def update_lock_status(self):
#         """قفل شدن بر اساس بودجه باقی‌مانده"""
#         remaining_amount = self.get_remaining_amount()
#         locked_amount = self.get_locked_amount()
#         logger.debug(
#             f"Checking lock status for ProjectBudgetAllocation {self.pk}: remaining={remaining_amount}, locked={locked_amount}"
#         )
#         if remaining_amount <= locked_amount:
#             self.is_locked = True
#             self.is_active = False
#             if self.pk:  # فقط اگر شیء قبلاً ذخیره شده باشد، save را فراخوانی کن
#                 self.save(update_fields=['is_locked', 'is_active'], skip_lock_status_update=True)
#                 Tankhah.objects.filter(project_budget_allocation=self).update(is_archived=True)
#                 # Tankhah.objects.filter(project_allocation=self).update(is_active=False)
#             else:
#                 logger.debug(f"New object (pk=None), setting is_locked={self.is_locked}, is_active={self.is_active} without saving")
#
#     def clean(self):
#         remaining = self.budget_allocation.get_remaining_amount()
#         if self.allocated_amount > remaining:
#             raise ValidationError(_("مبلغ تخصیص بیشتر از بودجه باقی‌مانده شعبه است"))
#         if self.subproject and self.subproject.project != self.project:
#             raise ValidationError(_("زیرپروژه باید به پروژه انتخاب‌شده تعلق داشته باشد"))
#         if self.allocated_amount < 0:
#             raise ValidationError(_("مبلغ تخصیص نمی‌تواند منفی باشد"))
#         if self.budget_allocation and self.allocation_date:
#             start_date = self.budget_allocation.budget_period.start_date
#             end_date = self.budget_allocation.budget_period.end_date
#             logger.info(
#                 f"start_date: {start_date} ({type(start_date)}), end_date: {end_date} ({type(end_date)}), allocation_date: {self.allocation_date} ({type(self.allocation_date)})"
#             )
#             # از آنجا که allocation_date یک DateField است، باید همیشه datetime.date باشد
#             allocation_date = self.allocation_date
#             if not isinstance(allocation_date, date):
#                 raise ValidationError(_("تاریخ تخصیص باید یک تاریخ معتبر باشد"))
#             if not (start_date <= allocation_date <= end_date):
#                 raise ValidationError(_("تاریخ تخصیص باید در بازه دوره بودجه باشد"))
#
#     def save(self, *args, **kwargs):
#         self.clean()
#         # self.full_clean()
#         if not kwargs.get('skip_lock_status_update', False):
#             self.update_lock_status()
#         kwargs.pop('skip_lock_status_update', None)
#         super().save(*args, **kwargs)
#         if self.subproject:
#             self.subproject.save()  # به‌روزرسانی بودجه زیرپروژه
#         logger.info(f"ProjectBudgetAllocation {self.pk} saved successfully")
# class BudgetAllocation(models.Model):
#     """
#     تخصیص بودجه به سازمان‌ها (شعبات یا ادارات) و پروژه‌ها.
#     قابلیت‌ها: تخصیص چندباره، توقف بودجه، و ردیابی هزینه‌ها.
#     """
#     budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE, related_name='allocations',verbose_name=_("دوره بودجه"))
#     organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='budget_allocations',verbose_name=_("سازمان دریافت‌کننده"))
#     budget_item = models.ForeignKey('BudgetItem', on_delete=models.PROTECT, related_name='allocations',verbose_name=_("ردیف بودجه"))
#     project = models.ForeignKey('core.Project', on_delete=models.CASCADE, related_name='allocations', verbose_name=_("پروژه"), null=True, blank=True)  # اختیاری کردن پروژه
#     subproject = models.ForeignKey('core.SubProject', on_delete=models.CASCADE, null=True, blank=True, related_name='budget_allocations', verbose_name=_("زیرپروژه"))
#     allocated_amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ تخصیص"))
#     allocation_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ تخصیص"))
#     created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,related_name='budget_allocations_created', verbose_name=_("ایجادکننده"))
#     description = models.TextField(blank=True, verbose_name=_("توضیحات"))
#     is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
#     is_stopped = models.BooleanField(default=False, verbose_name=_("متوقف‌شده"))
#
#     ALLOCATION_TYPES = (('amount', _("مبلغ ثابت")), ('percent', _("درصد")), ('returned', _("برگشتی")),)
#     allocation_type = models.CharField(max_length=20, choices=ALLOCATION_TYPES, default='amount',verbose_name=_("نوع تخصیص"))
#     locked_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_("درصد قفل‌شده"),help_text=_("درصد تخصیص که قفل می‌شود (0-100)"))
#     warning_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=10, verbose_name=_("آستانه اخطار"),help_text=_("درصدی که هشدار نمایش داده می‌شود (0-100)"))
#     warning_action = models.CharField(max_length=50,choices=[('NOTIFY', _("فقط اعلان")), ('LOCK', _("قفل کردن")), ('RESTRICT', _("محدود کردن ثبت")), ],        default='NOTIFY',verbose_name=_("اقدام هشدار"),help_text=_("رفتار سیستم هنگام رسیدن به آستانه هشدار"))
#     allocation_number = models.IntegerField(default=1, verbose_name=_("شماره تخصیص"))
#
#     returned_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0,verbose_name=_("مجموع بودجه برگشتی"))
#     is_locked = models.BooleanField(default=False, verbose_name=_("قفل‌شده"))
#     created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
#
#     class Meta:
#         verbose_name = _("تخصیص بودجه")
#         verbose_name_plural = _("تخصیص‌های بودجه")
#         default_permissions = ()
#         permissions = [
#             ('budgetallocation_add', _("افزودن تخصیص بودجه")),
#             ('budgetallocation_view', _("نمایش تخصیص بودجه")),
#             ('budgetallocation_update', _("بروزرسانی تخصیص بودجه")),
#             ('budgetallocation_delete', _("حذف تخصیص بودجه")),
#             ('budgetallocation_adjust', _("تنظیم تخصیص بودجه (افزایش/کاهش)")),
#             ('budgetallocation_stop', _("توقف تخصیص بودجه")),
#             ('budgetallocation_return', _("برگشت تخصیص بودجه")),  # جدید
#             ('BudgetAllocation_approve', 'می‌تواند تخصیص بودجه را تأیید کند'),
#             ('BudgetAllocation_reject', 'می‌تواند تخصیص بودجه را رد کند'),
#
#         ]
#         indexes = [
#             models.Index(fields=['budget_period', 'allocation_date']),
#             models.Index(fields=['organization', 'allocated_amount']),
#             models.Index(fields=['project']),
#             models.Index(fields=['subproject']),
#         ]
#
#     def __str__(self):
#         try:
#             jalali_date = jdatetime.date.fromgregorian(date=self.allocation_date).strftime('%Y/%m/%d')
#             if jalali_date:
#                 org_name = self.organization.name if self.organization else 'بدون سازمان/بدون شعبه'
#                 item_name = self.budget_item.name if self.budget_item else 'بدون ردیف'
#                 return f"{org_name} - {item_name} - {jalali_date} - {self.allocated_amount:,.0f} ریال"
#             else:
#                  return f"{self.budget_period.name} - {self.allocated_amount:,} ریال ({jalali_date})"
#         except (AttributeError, TypeError) as e:
#                  logger.error(f"Error in BudgetAllocation.__str__: {str(e)}")
#                  # در صورت خطا، یه نمایش ساده و امن برگردون
#                  project_name = self.project.name if self.project else 'بدون پروژه'
#                  return f"تخصیص {self.pk or 'جدید'}: {self.allocated_amount:,.0f} ریال ({project_name})"
#
#     def get_percentage(self):
#         if self.budget_item.total_amount and self.budget_item.total_amount != 0:
#             return (self.allocated_amount / self.budget_item.total_amount) * 100
#         return Decimal('0')
#
#     # def clean(self):
#     #     super().clean()
#     #     logger.debug(f"Cleaning BudgetAllocation: allocated_amount={self.allocated_amount}, allocation_type={self.allocation_type}")
#     #
#     #     if not self.budget_item:
#     #         raise ValidationError(_("ردیف بودجه اجباری است."))
#     #
#     #     if self.allocated_amount is None:
#     #         raise ValidationError(_("مبلغ تخصیص نمی‌تواند خالی باشد."))
#     #     if self.allocated_amount <= 0:
#     #         raise ValidationError(_("مبلغ تخصیص باید مثبت باشد."))
#     #
#     #     # چک کردن باقی‌مانده دوره به‌جای ردیف بودجه
#     #     remaining_budget = self.budget_period.get_remaining_amount()
#     #     if self.pk:  # برای ویرایش، تخصیص فعلی رو حساب نکن
#     #         current_allocation = BudgetAllocation.objects.filter(pk=self.pk).aggregate(
#     #             total=Sum('allocated_amount')
#     #         )['total'] or Decimal('0')
#     #         remaining_budget += current_allocation
#     #     if self.allocated_amount > remaining_budget:
#     #         raise ValidationError(_(
#     #             f"مبلغ تخصیص ({self.allocated_amount:,.0f} ریال) بیشتر از باقی‌مانده دوره بودجه ({remaining_budget:,.0f} ریال) است."
#     #         ))
#     #
#     #     if self.budget_period and self.budget_item:
#     #         if self.budget_item.budget_period != self.budget_period:
#     #             raise ValidationError(_("ردیف بودجه باید متعلق به دوره بودجه انتخاب‌شده باشد."))
#     #
#     #     if self.budget_period and self.allocation_date:
#     #         allocation_date = self.allocation_date
#     #         if hasattr(allocation_date, "date"):
#     #             allocation_date = allocation_date.date()
#     #         if not (self.budget_period.start_date <= allocation_date <= self.budget_period.end_date):
#     #             raise ValidationError(_("تاریخ تخصیص باید در بازه دوره بودجه باشد."))
#     #
#     #     if self.warning_threshold is not None and not (0 <= self.warning_threshold <= 100):
#     #         raise ValidationError(_("آستانه اخطار باید بین ۰ تا ۱۰۰ باشد."))
#     #
#     #     logger.debug("Clean validation passed")
#     #
#     #     # اعتبارسنجی درصد قفل‌شده دوره بودجه
#     #     # # چک کردن درصد قفل‌شده دوره بودجه
#     #     # به جای فراخوانی validate_allocation، مستقیم محاسبه می‌کنیم
#     #     locked_amount = self.budget_period.get_locked_amount()
#     #     available_for_allocation = remaining_budget - locked_amount
#     #     if self.allocated_amount > available_for_allocation:
#     #         raise ValidationError(_(
#     #             f"نمی‌توان تخصیص داد. مبلغ تخصیص ({self.allocated_amount:,.0f} ریال) بیشتر از مقدار مجاز ({available_for_allocation:,.0f} ریال) است."
#     #             f"حداقل {self.budget_period.locked_percentage}% از بودجه باید قفل بماند."
#     #         ))
#     #     logger.debug("Clean validation passed (Model IS : BudgetsAllocations )")
#
#     def clean(self):
#         # اعتبارسنجی مدل قبل از ذخیره
#         super().clean()
#         logger.debug(f"Cleaning BudgetAllocation: allocated_amount={self.allocated_amount}, allocation_type={self.allocation_type}")
#         # چک کردن وجود budget_item
#         if self.budget_item_id is None:
#             raise ValidationError(_("ردیف بودجه اجباری است."))
#         # چک کردن وجود organization
#         if self.organization_id is None:
#             raise ValidationError(_("سازمان دریافت‌کننده اجباری است."))
#         # چک کردن مبلغ تخصیص
#         if self.allocated_amount is None:
#             raise ValidationError(_("مبلغ تخصیص نمی‌تواند خالی باشد."))
#         if self.allocated_amount <= 0:
#             raise ValidationError(_("مبلغ تخصیص باید مثبت باشد."))
#
#         # چک کردن باقی‌مانده دوره بودجه
#         remaining_budget = self.budget_period.get_remaining_amount()
#         if self.pk:  # برای ویرایش، تخصیص فعلی رو حساب نکن
#             current_allocation = BudgetAllocation.objects.filter(pk=self.pk).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
#             remaining_budget += current_allocation
#         if self.allocated_amount > remaining_budget:
#             raise ValidationError(_(
#                 f"مبلغ تخصیص ({self.allocated_amount:,.0f} ریال) بیشتر از باقی‌مانده دوره بودجه ({remaining_budget:,.0f} ریال) است."
#             ))
#         # چک کردن تاریخ تخصیص
#         if self.budget_period and self.allocation_date:
#             allocation_date = self.allocation_date
#             if hasattr(allocation_date, "date"):
#                 allocation_date = allocation_date.date()
#             if not (self.budget_period.start_date <= allocation_date <= self.budget_period.end_date):
#                 raise ValidationError(_("تاریخ تخصیص باید در بازه دوره بودجه باشد."))
#
#         # چک کردن آستانه هشدار
#         if self.warning_threshold is not None and not (0 <= self.warning_threshold <= 100):
#             raise ValidationError(_("آستانه اخطار باید بین ۰ تا ۱۰۰ باشد."))
#
#         # اعتبارسنجی درصد قفل‌شده دوره بودجه
#         locked_amount = self.budget_period.get_locked_amount()
#         available_for_allocation = remaining_budget - locked_amount
#         if self.allocated_amount > available_for_allocation:
#             raise ValidationError(_(
#                 f"نمی‌توان تخصیص داد. مبلغ تخصیص ({self.allocated_amount:,.0f} ریال) بیشتر از مقدار مجاز ({available_for_allocation:,.0f} ریال) است."
#                 f"حداقل {self.budget_period.locked_percentage}% از بودجه باید قفل بماند."
#             ))
#
#         logger.debug("Clean validation passed (Model IS : BudgetsAllocations )")
#     def get_remaining_amount(self):
#         """محاسبه بودجه باقی‌مانده تخصیص پروژه"""
#         return calculate_remaining_amount(self, amount_field='allocated_amount', model_name='BudgetAllocation')
#     def get_remaining_amount(self):
#         # مبلغ تخصیص داده شده به این تخصیص بودجه
#         allocated = self.allocated_amount
#
#         # محاسبه مجموع مبالغ تنخواه‌های "تأیید شده" و "پرداخت شده"
#         # فرض می‌کنیم مدل Tankhah یک فیلد 'status' و یک فیلد 'amount' دارد
#         # و یک ForeignKey به BudgetAllocation به نام 'project_budget_allocation'
#         from tankhah.models import Tankhah # Import در داخل متد برای جلوگیری از Circular Import
#
#         # مبالغی که واقعا هزینه شده‌اند
#         spent_amount = Tankhah.objects.filter(
#             project_budget_allocation=self,
#             status__in=['APPROVED', 'PAID'] # فقط وضعیت‌های نهایی
#         ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
#
#         # مبالغی که در حال حاضر در انتظار تأیید هستند (رزرو موقت)
#         # این کار برای جلوگیری از Over-allocation است.
#         # می‌توانید تصمیم بگیرید که فقط برای status='DRAFT' یا 'PENDING' این رزرو را انجام دهید.
#         pending_amount = Tankhah.objects.filter(
#             project_budget_allocation=self,
#             status__in=['DRAFT', 'PENDING'] # وضعیت‌های در حال بررسی
#         ).exclude(pk=self.pk).aggregate(Sum('amount'))['amount__sum'] or Decimal('0') # اگر در حال ویرایش تنخواه فعلی هستید، مبلغ آن را دو بار کم نکنید
#
#         # باقیمانده واقعی بودجه = مبلغ تخصیص داده شده - (هزینه شده + در انتظار)
#         return allocated - (spent_amount + pending_amount)
#
#     # def get_locked_amount(self):
#     #     """    محاسبه مقدار بر اساس درصد (برای قفل یا هشدار)."""
#     #     return calculate_threshold_amount(self.allocated_amount, self.locked_percentage)
#     def get_locked_amount(obj):
#         """
#         محاسبه مقدار قفل‌شده بودجه.
#         Args:
#             obj: نمونه مدل BudgetPeriod یا BudgetAllocation
#         Returns:
#             Decimal: مقدار قفل‌شده
#         """
#         try:
#             if isinstance(obj, BudgetPeriod):
#                 return calculate_threshold_amount(obj.total_amount, obj.locked_percentage)
#             elif isinstance(obj, BudgetAllocation):
#                 return calculate_threshold_amount(obj.allocated_amount, obj.locked_percentage)
#             logger.warning(f"Invalid object type for get_locked_amount: {type(obj)}")
#             return Decimal('0')
#         except Exception as e:
#             logger.error(f"خطا در محاسبه مقدار قفل‌شده برای {obj}: {str(e)}")
#             return Decimal('0')
#
#     def get_actual_remaining_amount(self):
#         # این متد باید همیشه از دیتابیس بخواند و نباید به فیلد ذخیره شده تکیه کند
#         # مگر اینکه فیلد ذخیره شده با دقت بسیار بالا آپدیت شود
#         transactions_sum = self.transactions.aggregate(
#             consumption=Sum('amount', filter=Q(transaction_type='CONSUMPTION')),
#             adjustment_decrease=Sum('amount', filter=Q(transaction_type='ADJUSTMENT_DECREASE')),
#             returns=Sum('amount', filter=Q(transaction_type='RETURN')),
#             adjustment_increase=Sum('amount', filter=Q(transaction_type='ADJUSTMENT_INCREASE')),
#             # ALLOCATION اولیه جزو allocated_amount است و نباید اینجا محاسبه شود
#         )
#         consumed = (transactions_sum['consumption'] or Decimal('0')) + \
#                    (transactions_sum['adjustment_decrease'] or Decimal('0'))
#         added_back = (transactions_sum['returns'] or Decimal('0')) + \
#                      (transactions_sum['adjustment_increase'] or Decimal('0'))
#
#         # remaining = self.allocated_amount - consumed + added_back
#         # **اصلاح مهم:** allocated_amount با برگشت کم می‌شود، پس مبنای محاسبه remaining
#         # باید allocated_amount فعلی باشد و فقط مصرف‌ها از آن کم شوند.
#         # یا: مبنا allocated_amount اولیه باشد و برگشت‌ها اضافه شوند.
#         # روش صحیح‌تر: تکیه بر فیلد remaining_amount که توسط تراکنش‌ها آپدیت می‌شود.
#         # بنابراین این متد بیشتر برای نمایش یا چک کردن است:
#         return self.remaining_amount  # تکیه بر فیلد آپدیت شده
#
#     # def get_warning_amount(self):
#     #     """    محاسبه مقدار بر اساس درصد (برای قفل یا هشدار)."""
#     #     return calculate_threshold_amount(self.allocated_amount, self.warning_threshold)
#     def get_warning_amount(obj):
#         """
#         محاسبه آستانه هشدار بودجه.
#         Args:
#             obj: نمونه مدل BudgetPeriod یا BudgetAllocation
#         Returns:
#             Decimal: مقدار آستانه هشدار
#         """
#         try:
#             if isinstance(obj, BudgetPeriod):
#                 return calculate_threshold_amount(obj.total_amount, obj.warning_threshold)
#             elif isinstance(obj, BudgetAllocation):
#                 return calculate_threshold_amount(obj.allocated_amount, obj.warning_threshold)
#             logger.warning(f"Invalid object type for get_warning_amount: {type(obj)}")
#             return Decimal('0')
#         except Exception as e:
#             logger.error(f"خطا در محاسبه آستانه هشدار برای {obj}: {str(e)}")
#             return Decimal('0')
#
#     def check_allocation_status(self):
#         remaining = self.get_remaining_amount()
#         locked = self.get_locked_amount()
#         warning = self.get_warning_amount()
#         if not self.is_active:
#             return 'inactive', _('تخصیص غیرفعال است.')
#         if self.is_stopped:
#             return 'stopped', _('تخصیص متوقف شده است.')
#         if remaining <= 0:
#             return 'completed', _('تخصیص تمام‌شده است.')
#         if remaining <= locked:
#             return 'locked', _('تخصیص به حد قفل‌شده رسیده است.')
#         if remaining <= warning:
#             return 'warning', _('تخصیص به آستانه هشدار رسیده است.')
#         return 'normal', _('وضعیت عادی')
#
#     def send_notification(self, status, message):
#         recipients = CustomUser.objects.filter(
#             Q(userpost__post__organization=self.organization) |
#             Q(userpost__post__organization__parent=self.organization),
#             is_active=True
#         ).distinct()
#         send_notification(self, status, message, recipients)
#
#     # @property
#     # def project_allocations(self):
#     #     return ProjectBudgetAllocation.objects.filter(budget_allocation=self)
#
#     # def update_lock_status(self):
#     #     """قفل شدن بر اساس بودجه باقی‌مانده و تنظیم فلگ‌ها"""
#     #     try:
#     #         remaining_amount = self.get_remaining_amount()
#     #         locked_amount = self.get_locked_amount()
#     #         if remaining_amount <= locked_amount:
#     #             self.is_locked = True
#     #             self.is_active = False
#     #             # اصلاح: استفاده از budget_allocation به جای allocation
#     #             Tankhah.objects.filter(budget_allocation=self).update(is_active=False)
#     #             logger.debug(f"Disabled Tankhahs for BudgetAllocation {self.pk}")
#     #         self.save(update_fields=['is_locked', 'is_active'])
#     #         return self.is_locked, self.is_active
#     #     except Exception as e:
#     #         logger.error(f"Error in update_lock_status for BudgetAllocation {self.pk or 'unsaved'}: {str(e)}")
#     #         return self.is_locked, self.is_active
#     # محاسبه مانده بودجه
#
#     def update_lock_status(self):
#         try:
#             remaining_amount = self.get_remaining_amount()
#             locked_amount = self.get_locked_amount()
#             if remaining_amount <= locked_amount:
#                 self.is_locked = True
#                 self.is_active = False
#                 Tankhah.objects.filter(project_budget_allocation=self).update(is_active=False)
#                 logger.debug(f"Disabled Tankhahs for BudgetAllocation {self.pk}")
#             else:
#                 self.is_locked = False
#                 self.is_active = True
#             return self.is_locked, self.is_active
#         except Exception as e:
#             logger.error(f"Error in update_lock_status for BudgetAllocation {self.pk or 'unsaved'}: {str(e)}")
#             return self.is_locked, self.is_active
#
#     def save(self, *args, **kwargs):
#         logger.debug(f"Starting save for BudgetAllocation (pk={self.pk}, allocated_amount={self.allocated_amount})")
#         try:
#             with transaction.atomic():
#                 self.clean()
#                 # به‌روزرسانی وضعیت قفل
#                 is_locked, is_active = self.update_lock_status()
#                 self.is_locked = is_locked
#                 self.is_active = is_active
#
#                 # ذخیره نمونه
#                 super().save(*args, **kwargs)
#                 logger.info(f"BudgetAllocation saved with ID: {self.pk}")
#
#                 # آپدیت total_allocated دوره بودجه بدون فراخوانی save
#                 total_allocated = BudgetAllocation.objects.filter(
#                     budget_period=self.budget_period
#                 ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
#                 logger.debug(f"Calculated total_allocated={total_allocated} for BudgetPeriod {self.budget_period.id}")
#                 BudgetPeriod.objects.filter(pk=self.budget_period.pk).update(total_allocated=total_allocated)
#
#                 status, message = self.check_allocation_status()
#                 logger.debug(f"Allocation status: {status}, message: {message}")
#                 if status in ('warning', 'completed', 'stopped'):
#                     self.send_notification(status, message)
#                     logger.info(f"Sent notification for status: {status}")
#         except Exception as e:
#             logger.error(f"Error saving BudgetAllocation: {str(e)}", exc_info=True)
#             raise