from django.db.models.functions import Coalesce
from django.db.models import Value
import logging
from django.utils import timezone

from core.models import Organization

logger = logging.getLogger(__name__)
from django.contrib.contenttypes.models import ContentType

from budgets.budget_calculations import check_budget_status, get_project_remaining_budget

import jdatetime
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from decimal import Decimal
from django.core.exceptions import ValidationError
from accounts.models import CustomUser
# from budgets.budget_calculations import get_subproject_remaining_budget, get_project_remaining_budget
# from core.models import Organization, Project, SubProject, WorkflowStage
 # -- New
""" مدل نوع بودجه """# ------------------------------------
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
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    is_archived = models.BooleanField(default=False, verbose_name=_("بایگانی شده"))
    is_completed = models.BooleanField(default=False, verbose_name=_("تمام‌شده"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,
                                   related_name='budget_periods_created', verbose_name=_("ایجادکننده"))
    locked_percentage = models.IntegerField(default=0, verbose_name=_("درصد قفل‌شده"),
                                            help_text=_("درصد بودجه که قفل می‌شود (0-100)"))
    warning_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=10, verbose_name=_("آستانه اخطار"),
                                            help_text=_("درصدی که هشدار نمایش داده می‌شود (0-100)"))
    lock_condition = models.CharField(max_length=50,
                                      choices=[('AFTER_DATE', _("بعد از تاریخ پایان")), ('MANUAL', _("دستی")),
                                               ('ZERO_REMAINING', _("باقی‌مانده صفر")), ], default='AFTER_DATE',
                                      verbose_name=_("شرط قفل"))
    warning_action = models.CharField(max_length=50, choices=[('NOTIFY', _("فقط اعلان")), ('LOCK', _("قفل کردن")),
                                                              ('RESTRICT', _("محدود کردن ثبت")), ], default='NOTIFY',
                                      verbose_name=_("اقدام هشدار"),
                                      help_text=_("رفتار سیستم هنگام رسیدن به آستانه هشدار"))
    allocation_phase = models.CharField(max_length=50, blank=True, verbose_name=_("فاز تخصیص"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))


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

    def clean(self):
        # super().clean()
        # if self.total_allocated > self.total_amount:
        #     raise ValidationError(_("مجموع تخصیص‌ها نمی‌تواند از مبلغ کل بیشتر باشد."))
        if not self.start_date or not self.end_date:
            raise ValidationError(_("تاریخ شروع و پایان نمی‌توانند خالی باشند."))
        if self.end_date <= self.start_date:
            raise ValidationError(_("تاریخ پایان باید بعد از تاریخ شروع باشد."))
        if not (0 <= self.locked_percentage <= 100):
            raise ValidationError(_("درصد قفل‌شده باید بین 0 تا 100 باشد."))
        if not (0 <= self.warning_threshold <= 100):
            raise ValidationError(_("آستانه هشدار باید بین 0 تا 100 باشد."))
        if self.is_completed and self.is_active:
            raise ValidationError(_("دوره تمام‌شده نمی‌تواند فعال باشد."))

    # def get_remaining_amount(self):
    #     from budgets.models import BudgetAllocation
    #     allocated = BudgetAllocation.objects.filter(budget_period=self).aggregate(
    #         total=Sum('allocated_amount')
    #     )['total'] or Decimal('0')
    #     return max(self.total_amount - allocated, Decimal('0'))

    def get_remaining_amount(self):
        allocated = self.allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
        return max(self.total_amount - allocated + self.returned_amount, Decimal('0'))

    def get_locked_amount(self):
        return (self.total_amount * self.locked_percentage) / Decimal('100')

    def get_warning_amount(self):
        return (self.total_amount * self.warning_threshold) / Decimal('100')

    def send_notification(self, status, message):
        """
        Send notification to relevant users (e.g., Financial Manager, Budget Manager).
        """
        try:
            # فرض می‌کنیم CustomUser از طریق رابطه organizations به سازمان متصل است
            recipients = CustomUser.objects.filter(
                organizations=self.organization,  # اصلاح فیلد به رابطه صحیح
                roles__name__in=['Financial Manager', 'Budget Manager']
            ).distinct()

            if not recipients.exists():
                logger.warning(f"No recipients found for notification: {message}")
                return

            for recipient in recipients:
                from tankhah.models import Notification
                Notification.objects.create(
                    recipient=recipient,
                    actor=recipient,  # یا کاربر دیگری مثل created_by
                    verb=status,
                    description=message,
                    target=self,
                    level=status.lower()
                )
            logger.info(f"Notification sent to {recipients.count()} users: {message}")
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}", exc_info=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        status, message = check_budget_status(self)

        # self.budget_period.total_allocated = BudgetAllocation.objects.filter(
        #     budget_period=self
        # ).aggregate(Sum('allocated_amount'))['allocated_amount__sum'] or Decimal('0')
        # self.budget_period.save(update_fields=['total_allocated'])

        if status in ('warning', 'locked', 'completed'):
            self.send_notification(status, message)
# ------------------------------------
# ------------------------------------
""" BudgetAllocation (تخصیص بودجه):"""
class BudgetAllocation(models.Model):
    """
    تخصیص بودجه به سازمان‌ها (شعبات یا ادارات) و پروژه‌ها.
    قابلیت‌ها: تخصیص چندباره، توقف بودجه، و ردیابی هزینه‌ها.
    """
    budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE, related_name='allocations',
                                      verbose_name=_("دوره بودجه"))
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='budget_allocations',
                                     verbose_name=_("سازمان دریافت‌کننده"))
    budget_item = models.ForeignKey('BudgetItem', on_delete=models.PROTECT, related_name='allocations',
                                    verbose_name=_("ردیف بودجه"))
    project = models.ForeignKey('core.Project', on_delete=models.CASCADE, related_name='allocations',
                                verbose_name=_("پروژه"), null=True, blank=True)  # اختیاری کردن پروژه
    allocated_amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ تخصیص"))
    remaining_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0,
                                           verbose_name=_("باقی‌مانده تخصیص"))
    allocation_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ تخصیص"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,
                                   related_name='budget_allocations_created', verbose_name=_("ایجادکننده"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    is_stopped = models.BooleanField(default=False, verbose_name=_("متوقف‌شده"))

    ALLOCATION_TYPES = (('amount', _("مبلغ ثابت")), ('percent', _("درصد")), ('returned', _("برگشتی")),)
    allocation_type = models.CharField(max_length=20, choices=ALLOCATION_TYPES, default='amount',
                                       verbose_name=_("نوع تخصیص"))
    locked_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_("درصد قفل‌شده"),
                                            help_text=_("درصد تخصیص که قفل می‌شود (0-100)"))
    warning_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=10, verbose_name=_("آستانه اخطار"),
                                            help_text=_("درصدی که هشدار نمایش داده می‌شود (0-100)"))
    warning_action = models.CharField(
        max_length=50,
        choices=[('NOTIFY', _("فقط اعلان")), ('LOCK', _("قفل کردن")), ('RESTRICT', _("محدود کردن ثبت")), ],
        default='NOTIFY',
        verbose_name=_("اقدام هشدار"),
        help_text=_("رفتار سیستم هنگام رسیدن به آستانه هشدار")
    )
    allocation_number = models.IntegerField(default=1, verbose_name=_("شماره تخصیص"))
    returned_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0,verbose_name=_("مجموع بودجه برگشتی"))

    class Meta:
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
            ('budgetallocation_return', _("برگشت تخصیص بودجه")),  # جدید

            ('BudgetAllocation_approve', 'می‌تواند تخصیص بودجه را تأیید کند'),
            ('BudgetAllocation_reject', 'می‌تواند تخصیص بودجه را رد کند'),

        ]
        indexes = [
            models.Index(fields=['budget_period', 'allocation_date']),
            models.Index(fields=['organization', 'allocated_amount']),
        ]

    def __str__(self):
        try:
            jalali_date = jdatetime.date.fromgregorian(date=self.allocation_date).strftime('%Y/%m/%d')
            if jalali_date:
                org_name = self.organization.name if self.organization else 'بدون سازمان/بدون شعبه'
                item_name = self.budget_item.name if self.budget_item else 'بدون ردیف'
                return f"{org_name} - {item_name} - {jalali_date} - {self.allocated_amount:,.0f} ریال"
            else:
                 return f"{self.budget_period.name} - {self.allocated_amount:,} ریال ({jalali_date})"
        except (AttributeError, TypeError) as e:
            logger.error(f"Error in BudgetAllocation.__str__: {str(e)}")
            return f"تخصیص {self.organization.name}:{self.allocated_amount}{self.project.name} "

    def get_percentage(self):
        if self.budget_item.total_amount and self.budget_item.total_amount != 0:
            return (self.allocated_amount / self.budget_item.total_amount) * 100
        return Decimal('0')

    def clean(self):
        super().clean()
        logger.debug(f"Cleaning BudgetAllocation: allocated_amount={self.allocated_amount}, allocation_type={self.allocation_type}")

        if not self.budget_item:
            raise ValidationError(_("ردیف بودجه اجباری است."))

        if self.allocated_amount is None:
            raise ValidationError(_("مبلغ تخصیص نمی‌تواند خالی باشد."))
        if self.allocated_amount <= 0:
            raise ValidationError(_("مبلغ تخصیص باید مثبت باشد."))

        # چک کردن باقی‌مانده دوره به‌جای ردیف بودجه
        remaining_budget = self.budget_period.get_remaining_amount()
        if self.pk:  # برای ویرایش، تخصیص فعلی رو حساب نکن
            current_allocation = BudgetAllocation.objects.filter(pk=self.pk).aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')
            remaining_budget += current_allocation
        if self.allocated_amount > remaining_budget:
            raise ValidationError(_(
                f"مبلغ تخصیص ({self.allocated_amount:,.0f} ریال) بیشتر از باقی‌مانده دوره بودجه ({remaining_budget:,.0f} ریال) است."
            ))

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

        logger.debug("Clean validation passed")
    #
    # def get_remaining_amount(self):
    #     return max(self.allocated_amount -
    #                self.transactions.filter(transaction_type='CONSUMPTION').aggregate(total=Sum('amount'))['total'] or Decimal('0') +
    #                self.returned_amount, Decimal('0'))


    def __get_remaining_amount(self):

        consumption_total = self.transactions.filter(transaction_type='CONSUMPTION').aggregate(
            total=Coalesce(Sum('amount'), Value(Decimal('0')))
        )['total']
        return_total = self.transactions.filter(transaction_type='RETURN').aggregate(
            total=Coalesce(Sum('amount'), Value(Decimal('0')))
        )['total']

        return max(
            self.allocated_amount - consumption_total + return_total,
            Decimal('0')
        )

    def get_remaining_amount(self):
        consumption_total = BudgetTransaction.objects.filter(allocation=self, transaction_type='CONSUMPTION' ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        return_total = BudgetTransaction.objects.filter(allocation=self, transaction_type='RETURN' ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        project_consumed = ProjectBudgetAllocation.objects.filter( budget_allocation=self ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
        return self.allocated_amount - consumption_total - project_consumed + return_total


    def get_locked_amount(self):
        return (self.allocated_amount * self.locked_percentage) / Decimal('100')

    def get_warning_amount(self):
        return (self.allocated_amount * self.warning_threshold) / Decimal('100')

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

    def send_notification(self, status, message):
        """
        Send notification to users with roles 'Financial Manager' or 'Budget Manager'
        who are associated with the organization or its parent organization.
        """
        try:
            # انتخاب کاربرانی که از طریق پست‌های سازمانی به سازمان یا سازمان والد مرتبط هستند
            from django.db.models import Q
            recipients = CustomUser.objects.filter(
                Q(userpost__post__organization=self.organization) |
                Q(userpost__post__organization__parent=self.organization),
                # Q(roles__name__in=['Financial Manager', 'Budget Manager']) |
                # Q(groups__roles__name__in=['Financial Manager', 'Budget Manager']),
                is_active=True
            ).distinct()

            if not recipients.exists():
                logger.warning(f"No recipients found for notification: {message} (organization_id={self.organization_id})")
                return

            for recipient in recipients:
                # from tankhah.models import Notification
                from notifications.models import Notification
                Notification.objects.create(
                    recipient=recipient,
                    actor=self.created_by or recipient,  # استفاده از created_by اگر وجود داشته باشد
                    verb=status,
                    description=message,
                    target=self,
                    level=status.lower()
                )
            logger.info(f"Notification sent to {recipients.count()} users for BudgetAllocation {self.id}: {message}")
        except Exception as e:
            logger.error(f"Error sending notification for BudgetAllocation {self.id}: {str(e)}", exc_info=True)
            # جلوگیری از خرابی تراکنش در صورت خطا
            return

    def save(self, *args, **kwargs):
        logger.debug(f"Starting save for BudgetAllocation (pk={self.pk}, allocated_amount={self.allocated_amount})")
        try:
            with transaction.atomic():
                self.clean()
                if not self.pk:
                    self.remaining_amount = self.allocated_amount
                    logger.debug(f"New instance, set remaining_amount={self.remaining_amount}")

                super().save(*args, **kwargs)
                logger.info(f"BudgetAllocation saved with ID: {self.pk}")

                total_allocated = BudgetAllocation.objects.filter(
                    budget_period=self.budget_period
                ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
                logger.debug(f"Calculated total_allocated={total_allocated} for BudgetPeriod {self.budget_period.id}")

                self.budget_period.total_allocated = total_allocated
                self.budget_period.save(update_fields=['total_allocated'])
                logger.info(f"Updated BudgetPeriod {self.budget_period.id} with total_allocated={total_allocated}")

                status, message = self.check_allocation_status()
                logger.debug(f"Allocation status: {status}, message: {message}")
                if status in ('warning', 'completed', 'stopped'):
                    self.send_notification(status, message)
                    logger.info(f"Sent notification for status: {status}")

        except Exception as e:
            logger.error(f"Error saving BudgetAllocation: {str(e)}", exc_info=True)
            raise

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
        return f"{self.name} - {self.organization.name}"  # - {self.budget_period.name}"

    def clean(self):
        super().clean()
        if not self.name:
            raise ValidationError(_("نام ردیف بودجه نمی‌تواند خالی باشد."))

""" BudgetTransaction (تراکنش بودجه):"""
class BudgetTransaction(models.Model):
    """توضیح: هر تغییر در بودجه (مثل مصرف توسط تنخواه) رو ثبت می‌کنه و remaining_amount تخصیص رو آپدیت می‌کنه."""
    TRANSACTION_TYPES = (
        ('ALLOCATION', _('تخصیص اولیه')),
        ('CONSUMPTION', _('مصرف')),
        ('ADJUSTMENT_INCREASE', _('افزایش تخصیص')),
        ('ADJUSTMENT_DECREASE', _('کاهش تخصیص')),
    )
    allocation = models.ForeignKey(BudgetAllocation, on_delete=models.CASCADE,
                                   related_name='transactions', verbose_name=_("تخصیص بودجه"))
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES,
                                        verbose_name=_("نوع تراکنش"))
    amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ"))
    related_tankhah = models.ForeignKey('tankhah.Tankhah', on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name=_("تنخواه مرتبط"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان"))
    created_by  = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,
                             verbose_name=_("کاربر"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))

    transaction_id = models.CharField(max_length=50, unique=True, verbose_name=_("شناسه تراکنش"))#یک شناسه منحصربه‌فرد برای هر تراکنش:

    def validate_return(self):
        """اعتبارسنجی تراکنش بازگشت"""
        if self.transaction_type != 'RETURN':
            return True, None
        consumed = BudgetTransaction.objects.filter(
            allocation=self.allocation,
            allocation__project=self.allocation.project_allocations.first().project,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        returned = BudgetTransaction.objects.filter(
            allocation=self.allocation,
            allocation__project=self.allocation.project_allocations.first().project,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_consumed = consumed - returned
        if self.amount > total_consumed:
            return False, _(f"مبلغ بازگشت ({self.amount:,.0f} ریال) نمی‌تواند بیشتر از مصرف خالص ({total_consumed:,.0f} ریال) باشد.")
        remaining_budget = get_project_remaining_budget(self.allocation.project_allocations.first().project)
        if self.amount > remaining_budget:
            return False, _(f"مبلغ بازگشت ({self.amount:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) باشد.")
        return True, None

    def save(self, *args, **kwargs):
        if self.transaction_type == 'RETURN':
            is_valid, error_message = self.validate_return()
            if not is_valid:
                raise ValidationError(error_message)
        super().save(*args, **kwargs)
        # به‌روزرسانی وضعیت و اعلان
        status, message = check_budget_status(self.allocation.budget_period)
        if status in ('warning', 'locked', 'completed', 'stopped'):
            self.allocation.send_notification(status, message)
        if self.transaction_type == 'RETURN':
            self.allocation.send_notification(
                'return',
                f"مبلغ {self.amount:,.0f} ریال از تخصیص {self.allocation.id} برگشت داده شد."
            )


    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        from django.contrib.contenttypes.models import ContentType

        if not self.transaction_id:
            self.transaction_id = f"TX-{self.allocation.id}-{timezone.now().timestamp()}"

        if self.transaction_type == 'CONSUMPTION':
            if self.amount > self.allocation.remaining_amount:
                raise ValidationError(_("مبلغ مصرف بیشتر از باقی‌مانده تخصیص است."))
        elif self.transaction_type == 'RETURN':
            if self.amount > self.allocation.allocated_amount:
                raise ValidationError(_("مبلغ برگشتی نمی‌تواند بیشتر از مبلغ تخصیص‌یافته باشد."))
            if not self.allocation.budget_period.is_active:
                raise ValidationError(_("نمی‌توان از دوره غیرفعال بودجه برگشت داد."))

            self.allocation.remaining_amount += self.amount  # remaining_amount تخصیص افزایش یابد.
            self.allocation.allocated_amount -= self.amount  # کاهش مبلغ تخصیص
            self.allocation.returned_amount += self.amount

            self.allocation.budget_period.total_allocated -= self.amount
            self.allocation.budget_period.returned_amount += self.amount

            self.allocation.save(update_fields=['remaining_amount', 'allocated_amount', 'returned_amount'])
            self.allocation.budget_period.save(update_fields=['total_allocated', 'returned_amount'])

            # self.allocation.budget_period.save(update_fields=['total_allocated'])
            # ثبت در BudgetHistory
            BudgetHistory.objects.create(
                content_type=ContentType.objects.get_for_model(BudgetAllocation),
                object_id=self.allocation.id,
                action='RETURN',
                amount=self.amount,
                created_by=self.created_by,
                details=f"برگشت {self.amount:,} از تخصیص {self.allocation.id} به دوره بودجه {self.allocation.budget_period.name}",
                transaction_type='RETURN',
                transaction_id=f"RET-{self.transaction_id}"
            )

        elif self.transaction_type in ['CONSUMPTION', 'ADJUSTMENT_DECREASE']:
            self.allocation.remaining_amount -= self.amount
        elif self.transaction_type in ['ALLOCATION', 'ADJUSTMENT_INCREASE']:
            self.allocation.remaining_amount += self.amount

        self.allocation.save(update_fields=['remaining_amount', 'allocated_amount'])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount:,} ({self.timestamp})"

    class Meta:
        verbose_name = _("تراکنش بودجه")
        verbose_name_plural = _("تراکنش‌های بودجه")
        default_permissions = ()

        permissions = [
            ('BudgetTransaction_add', 'افزودن تراکنش بودجه'),
            ('BudgetTransaction_update', 'بروزرسانی تراکنش بودجه'),
            ('BudgetTransaction_delete', 'حــذف تراکنش بودجه'),
            ('BudgetTransaction_view', _('نمایش تراکنش بودجه')),
            ('BudgetTransaction_return', _('برگشت تراکنش بودجه')),  # جدید
            # add/update/delete معمولاً توسط سیستم انجام می‌شه، نه کاربر
        ]

def get_current_date():
    return timezone.now().date()

"""تخصیص بودجه به پروژه و زیر پروژه """
class ProjectBudgetAllocation(models.Model):
    """
    تخصیص بودجه از BudgetAllocation شعبه به پروژه یا زیرپروژه.
    توضیح: این مدل بودجه شعبه رو به پروژه یا زیرپروژه وصل می‌کنه و تاریخچه تخصیص رو نگه می‌داره.
    """
    budget_allocation = models.ForeignKey('budgets.BudgetAllocation', on_delete=models.CASCADE, related_name='project_allocations', verbose_name=_("تخصیص بودجه شعبه"))
    project = models.ForeignKey('core.Project', on_delete=models.CASCADE, related_name='budget_allocations', verbose_name=_("پروژه"))
    subproject = models.ForeignKey('core.SubProject', on_delete=models.CASCADE, null=True, blank=True,  related_name='budget_allocations', verbose_name=_("زیرپروژه"))
    allocated_amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ تخصیص"))
    allocation_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ تخصیص"))
    # allocation_date = models.DateField( verbose_name=_("تاریخ تخصیص"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, related_name='project_budget_allocations_created', verbose_name=_("ایجادکننده"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    is_active= models.BooleanField(default=True,verbose_name=_('فعال'))
    def get_remaining_amount(self):
        from budgets.budget_calculations import get_subproject_remaining_budget
        if self.subproject:
            return get_subproject_remaining_budget(self.subproject)
        from budgets.budget_calculations import get_project_remaining_budget
        return get_project_remaining_budget(self.project)

    def clean(self):
        remaining = self.budget_allocation.get_remaining_amount()
        if self.allocated_amount > remaining:
            raise ValidationError(_("مبلغ تخصیص بیشتر از بودجه باقی‌مانده شعبه است"))
        if self.subproject and self.subproject.project != self.project:
            raise ValidationError(_("زیرپروژه باید به پروژه انتخاب‌شده تعلق داشته باشد"))
        if self.allocated_amount < 0:
            raise ValidationError(_("مبلغ تخصیص نمی‌تواند منفی باشد"))
        from datetime import datetime
        if self.budget_allocation and self.allocation_date:
            start_date = self.budget_allocation.budget_period.start_date
            end_date = self.budget_allocation.budget_period.end_date
            # تبدیل allocation_date به datetime.date اگر datetime.datetime باشد
            logger.info( f"start_date: {start_date} ({type(start_date)}), end_date: {end_date} ({type(end_date)}), allocation_date: {self.allocation_date} ({type(self.allocation_date)})")

            allocation_date = self.allocation_date.date() if isinstance(self.allocation_date,
                                                                        datetime) else self.allocation_date
            if not (start_date <= allocation_date <= end_date):
                raise ValidationError(_("تاریخ تخصیص باید در بازه دوره بودجه باشد"))

    def save(self, *args, **kwargs):
        self.clean()
        # if not self.pk:
        #     self.remaining_amount = self.allocated_amount
        super().save(*args, **kwargs)
        # self.budget_allocation.remaining_amount = self.budget_allocation.get_remaining_amount()
        # self.budget_allocation.save(update_fields=['remaining_amount'])
        # self.remaining_amount = self.get_remaining_amount()
        # super().save(update_fields=['remaining_amount'])

    @property
    def remaining_amount(self):
        """
        محاسبه مقدار باقی‌مانده با کسر مجموع تراکنش‌های مصرفی از مبلغ تخصیص‌شده
        """
        consumed = BudgetTransaction.objects.filter(
            allocation=self.budget_allocation,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or 0

        returned = BudgetTransaction.objects.filter(
            allocation=self.budget_allocation,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or 0

        return self.allocated_amount - consumed + returned


    def __str__(self):
        target = self.subproject.name if self.subproject else self.project.name
        jalali_date = jdatetime.date.fromgregorian(date=self.allocation_date).strftime('%Y/%m/%d')
        return f"{target} - {self.allocated_amount:,} ({jalali_date})"

    class Meta:
        verbose_name = _("تخصیص بودجه پروژه")
        verbose_name_plural = _("تخصیص‌های بودجه پروژه")
        default_permissions = ()
        permissions = [
            ('ProjectBudgetAllocation_add', _('افزودن تخصیص بودجه پروژه')),
            ('ProjectBudgetAllocation_view', _('نمایش تخصیص بودجه پروژه')),
            ('ProjectBudgetAllocation_update', _('بروزرسانی تخصیص بودجه پروژه')),
            ('ProjectBudgetAllocation_delete', _('حذف تخصیص بودجه پروژه')),
            ('ProjectBudgetAllocation_Head_Office', 'تخصیص بودجه مجموعه پروژه(دفتر مرکزی)🏠'),
            ('ProjectBudgetAllocation_Branch', 'تخصیص بودجه مجموعه پروژه(شعبه)🏠'),
        ]

"""PaymentOrder (دستور پرداخت):"""
class PaymentOrder(models.Model):
    """توضیح: مدل جدا برای دستور پرداخت با لینک به تنخواه و فاکتورها. min_signatures برای کنترل تعداد امضا و شماره‌گذاری پویا با تاریخ شمسی."""
    STATUS_CHOICES = (
        ('DRAFT', _('پیش‌نویس')),
        ('PENDING_SIGNATURES', _('در انتظار امضا')),
        ('ISSUED', _('صادر شده')),
        ('PAID', _('پرداخت شده')),
        ('CANCELED', _('لغو شده')),
    )
    tankhah = models.ForeignKey('tankhah.Tankhah', on_delete=models.CASCADE,
                                related_name='payment_orders', verbose_name=_("تنخواه"))
    order_number = models.CharField(max_length=50, unique=True, blank=True,
                                    verbose_name=_("شماره دستور پرداخت"))
    issue_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ صدور"))
    amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ"))
    payee = models.ForeignKey('Payee', on_delete=models.SET_NULL, null=True,
                              verbose_name=_("دریافت‌کننده"))
    description = models.TextField(verbose_name=_("شرح پرداخت"))
    related_factors = models.ManyToManyField('tankhah.Factor', blank=True,
                                             verbose_name=_("فاکتورهای مرتبط"))
    payment_id = models.CharField(max_length=50, blank=True, null=True,
                                  verbose_name=_("شناسه پرداخت"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT',
                              verbose_name=_("وضعیت"))
    created_by_post = models.ForeignKey('core.Post', on_delete=models.SET_NULL, null=True,
                                        verbose_name=_("پست ایجادکننده"))
    min_signatures = models.IntegerField(default=1, verbose_name=_("حداقل تعداد امضا"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,
                                   related_name='payment_orders_created', verbose_name=_("ایجادکننده"))

    payment_date = models.DateField(null=True, blank=True, verbose_name=_("تاریخ پرداخت"))
    def generate_order_number(self):
        sep = "-"
        date_str = jdatetime.date.fromgregorian(date=self.issue_date).strftime('%Y%m%d')
        serial = PaymentOrder.objects.filter(issue_date=self.issue_date).count() + 1
        return f"PO{sep}{date_str}{sep}{serial:03d}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} - {self.amount}"

    class Meta:
        verbose_name = _("دستور پرداخت")
        verbose_name_plural = _("دستورهای پرداخت")
        default_permissions = ()
        permissions = [
            ('PaymentOrder_add', _('افزودن دستور پرداخت')),
            ('PaymentOrder_view', _('نمایش دستور پرداخت')),
            ('PaymentOrder_update', _('بروزرسانی دستور پرداخت')),
            ('PaymentOrder_delete', _('حذف دستور پرداخت')),
            ('PaymentOrder_sign', _('امضای دستور پرداخت')),
            ('PaymentOrder_issue', _('صدور دستور پرداخت')),
        ]

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

class SystemSettings(models.Model):
    """تنظیمات سیستم بودجه"""
    budget_locked_percentage_default = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name=_("درصد قفل‌شده پیش‌فرض بودجه")
    )
    budget_warning_threshold_default = models.DecimalField(
        max_digits=5, decimal_places=2, default=10, verbose_name=_("آستانه هشدار پیش‌فرض بودجه")
    )
    budget_warning_action_default = models.CharField(
        max_length=50, choices=[('NOTIFY', 'اعلان'), ('LOCK', 'قفل'), ('RESTRICT', 'محدود')],
        default='NOTIFY', verbose_name=_("اقدام هشدار پیش‌فرض بودجه")
    )
    allocation_locked_percentage_default = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name=_("درصد قفل‌شده پیش‌فرض تخصیص")
    )


    class Meta:
        verbose_name = _("تنظیمات سیستم")
        verbose_name_plural = _("تنظیمات سیستم")

    def __str__(self):
        return "تنظیمات سیستم بودجه"

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