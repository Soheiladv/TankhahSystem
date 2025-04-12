import logging

import jdatetime
from accounts.models import CustomUser
from budgets.budget_calculations import get_subproject_remaining_budget, get_project_remaining_budget
from core.models import Organization, Project, SubProject, WorkflowStage

logger = logging.getLogger(__name__)
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from jdatetime import datetime as jdatetime

# Create your models here.
 # -- New
# ------------------------------------
"""BudgetPeriod (دوره بودجه کلان):"""
class BudgetPeriod(models.Model):
    """
    بودجه کلان برای دفتر مرکزی (HQ).
    قابلیت‌ها: مدیریت قفل، هشدار، اتمام بودجه، و اعلانات.
    """
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        limit_choices_to={'org_type': 'HQ'},
        verbose_name=_("دفتر مرکزی"),
        related_name='budget_periods'
    )
    name = models.CharField(max_length=100, unique=True, verbose_name=_("نام دوره بودجه"))
    start_date = models.DateField(verbose_name=_("تاریخ شروع"))
    end_date = models.DateField(verbose_name=_("تاریخ پایان"))
    total_amount = models.DecimalField(max_digits=25, decimal_places=0, verbose_name=_("مبلغ کل"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    is_archived = models.BooleanField(default=False, verbose_name=_("بایگانی شده"))
    is_completed = models.BooleanField(default=False, verbose_name=_("تمام‌شده"))

    total_allocated = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_("مجموع تخصیص‌ها"))

    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='budget_periods_created',
        verbose_name=_("ایجادکننده")
    )
    locked_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_("درصد قفل‌شده"),
        help_text=_("درصد بودجه که قفل می‌شود (0-100)")
    )
    warning_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10,
        verbose_name=_("آستانه اخطار"),
        help_text=_("درصدی که هشدار نمایش داده می‌شود (0-100)")
    )
    lock_condition = models.CharField(
        max_length=50,
        choices=[
            ('AFTER_DATE', _("بعد از تاریخ پایان")),
            ('MANUAL', _("دستی")),
            ('ZERO_REMAINING', _("باقی‌مانده صفر")),
        ],
        default='AFTER_DATE',
        verbose_name=_("شرط قفل")
    )
    warning_action = models.CharField(
        max_length=50,
        choices=[
            ('NOTIFY', _("فقط اعلان")),
            ('LOCK', _("قفل کردن")),
            ('RESTRICT', _("محدود کردن ثبت")),
        ],
        default='NOTIFY',
        verbose_name=_("اقدام هشدار"),
        help_text=_("رفتار سیستم هنگام رسیدن به آستانه هشدار")
    )

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
        """اعتبارسنجی تاریخ‌ها و درصد‌ها"""
        if self.end_date <= self.start_date:
            raise ValidationError(_("تاریخ پایان باید بعد از تاریخ شروع باشد."))
        if not (0 <= self.locked_percentage <= 100):
            raise ValidationError(_("درصد قفل‌شده باید بین 0 تا 100 باشد."))
        if not (0 <= self.warning_threshold <= 100):
            raise ValidationError(_("آستانه هشدار باید بین 0 تا 100 باشد."))

    def get_remaining_amount(self):
        """محاسبه باقی‌مانده بودجه"""
        allocated = BudgetAllocation.objects.filter(budget_period=self).aggregate(
            total=Sum('allocated_amount')
        )['total'] or Decimal('0')
        return max(self.total_amount - allocated, Decimal('0'))

    def get_locked_amount(self):
        """محاسبه مقدار قفل‌شده"""
        return (self.total_amount * self.locked_percentage) / Decimal('100')

    def get_warning_amount(self):
        """محاسبه مقدار آستانه هشدار"""
        return (self.total_amount * self.warning_threshold) / Decimal('100')

    def check_budget_status(self):
        """چک کردن وضعیت بودجه"""
        remaining = self.get_remaining_amount()
        locked = self.get_locked_amount()
        warning = self.get_warning_amount()

        if not self.is_active:
            return 'inactive', _('دوره غیرفعال است.')
        if self.is_completed:
            return 'completed', _('بودجه تمام‌شده است.')
        if remaining <= 0 and self.lock_condition == 'ZERO_REMAINING':
            self.is_completed = True
            self.is_active = False
            self.save()
            return 'completed', _('بودجه به صفر رسیده و تمام‌شده است.')
        if self.lock_condition == 'AFTER_DATE' and self.end_date < timezone.now().date():
            self.is_active = False
            self.save()
            return 'locked', _('دوره به دلیل پایان تاریخ قفل شده است.')
        if self.lock_condition == 'MANUAL' and remaining <= locked:
            return 'locked', _('بودجه به حد قفل‌شده رسیده است.')
        if remaining <= warning:
            return 'warning', _('بودجه به آستانه هشدار رسیده است.')
        return 'normal', _('وضعیت عادی')

    def send_notification(self, status, message):
        """ارسال اعلان به کاربران مرتبط"""
        from tankhah.models import Notification
        recipients = CustomUser.objects.filter(
            models.Q(organization=self.organization) |
            models.Q(organization__parent=self.organization)
        ).distinct()
        level = {
            'warning': 'WARNING',
            'locked': 'ERROR',
            'completed': 'ERROR',
            'inactive': 'INFO',
            'normal': 'INFO'
        }.get(status, 'INFO')
        for recipient in recipients:
            Notification.objects.create(
                recipient=recipient,
                message=f"{self.name}: {message}",
                level=level
            )

    def save(self, *args, **kwargs):
        """مدیریت ذخیره و اعلانات"""
        self.clean()
        super().save(*args, **kwargs)
        status, message = self.check_budget_status()
        if status in ('warning', 'locked', 'completed'):
            self.send_notification(status, message)

# ------------------------------------
""" BudgetAllocation (تخصیص بودجه):"""
class BudgetAllocation(models.Model):
    """
    تخصیص بودجه به سازمان‌ها (شعبات یا ادارات) و پروژه‌ها.
    قابلیت‌ها: تخصیص چندباره، توقف بودجه، و ردیابی هزینه‌ها.
    """
    budget_period = models.ForeignKey(
        'BudgetPeriod',
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name=_("دوره بودجه")
    )
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='budget_allocations',
        verbose_name=_("سازمان دریافت‌کننده")
    )
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name=_("پروژه")
    )
    allocated_amount = models.DecimalField(
        max_digits=25,
        decimal_places=2,
        verbose_name=_("مبلغ تخصیص")
    )
    allocation_date = models.DateField(
        default=timezone.now,
        verbose_name=_("تاریخ تخصیص")
    )
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='budget_allocations_created',
        verbose_name=_("ایجادکننده")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("توضیحات")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("فعال")
    )
    is_stopped = models.BooleanField(
        default=False,
        verbose_name=_("متوقف‌شده")
    )
    ALLOCATION_TYPES = (
        ('amount', _("مبلغ ثابت")),
        ('percent', _("درصد")),
    )
    allocation_type = models.CharField(
        max_length=20,
        choices=ALLOCATION_TYPES,
        default='amount',
        verbose_name=_("نوع تخصیص")
    )
    locked_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_("درصد قفل‌شده"),
        help_text=_("درصد تخصیص که قفل می‌شود (0-100)")
    )
    warning_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10,
        verbose_name=_("آستانه اخطار"),
        help_text=_("درصدی که هشدار نمایش داده می‌شود (0-100)")
    )
    warning_action = models.CharField(
        max_length=50,
        choices=[
            ('NOTIFY', _("فقط اعلان")),
            ('LOCK', _("قفل کردن")),
            ('RESTRICT', _("محدود کردن ثبت")),
        ],
        default='NOTIFY',
        verbose_name=_("اقدام هشدار"),
        help_text=_("رفتار سیستم هنگام رسیدن به آستانه هشدار")
    )
    allocation_number = models.IntegerField(default=1, verbose_name=_("شماره تخصیص")) #برای ردیابی تخصیص‌های چندباره:

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
        ]

    def __str__(self):
        jalali_date = jdatetime.fromgregorian(date=self.allocation_date).strftime('%Y/%m/%d')
        return f"تخصیص {self.id} - {self.organization.name} - {self.project.name} - {self.allocated_amount:,} ({jalali_date})"

    def clean(self):
        """اعتبارسنجی تخصیص"""
        if self.allocated_amount <= 0:
            raise ValidationError(_("مبلغ تخصیص باید مثبت باشد."))
        if not (0 <= self.locked_percentage <= 100):
            raise ValidationError(_("درصد قفل‌شده باید بین 0 تا 100 باشد."))
        if not (0 <= self.warning_threshold <= 100):
            raise ValidationError(_("آستانه هشدار باید بین 0 تا 100 باشد."))
        if self.allocation_type == 'percent' and self.allocated_amount > 100:
            raise ValidationError(_("درصد تخصیص نمی‌تواند بیشتر از 100 باشد."))
        if self.budget_period and self.allocation_date:
            if not (self.budget_period.start_date <= self.allocation_date <= self.budget_period.end_date):
                raise ValidationError(_("تاریخ تخصیص باید در بازه دوره بودجه باشد."))

    def get_remaining_amount(self):
        """محاسبه باقی‌مانده تخصیص"""
        used = ProjectBudgetAllocation.objects.filter(budget_allocation=self).aggregate(
            total=Sum('allocated_amount')
        )['total'] or Decimal('0')
        return max(self.allocated_amount - used, Decimal('0'))

    def get_locked_amount(self):
        """محاسبه مقدار قفل‌شده"""
        return (self.allocated_amount * self.locked_percentage) / Decimal('100')

    def get_warning_amount(self):
        """محاسبه مقدار آستانه هشدار"""
        return (self.allocated_amount * self.warning_threshold) / Decimal('100')

    def check_allocation_status(self):
        """چک کردن وضعیت تخصیص"""
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
        """ارسال اعلان به کاربران مرتبط"""
        from tankhah.models import Notification
        recipients = CustomUser.objects.filter(
            models.Q(organization=self.organization) |
            models.Q(organization__parent=self.organization)
        ).distinct()
        level = {
            'warning': 'WARNING',
            'locked': 'ERROR',
            'completed': 'ERROR',
            'stopped': 'ERROR',
            'inactive': 'INFO',
            'normal': 'INFO'
        }.get(status, 'INFO')
        for recipient in recipients:
            Notification.objects.create(
                recipient=recipient,
                message=f"تخصیص {self.id} - {self.project.name}: {message}",
                level=level
            )

    def save(self, *args, **kwargs):
        """مدیریت ذخیره و اعلانات"""
        self.clean()
        if self.allocation_type == 'percent' and self.budget_period:
            self.allocated_amount = (self.budget_period.total_amount * self.allocated_amount) / Decimal('100')
        super().save(*args, **kwargs)
        status, message = self.check_allocation_status()
        if status in ('warning', 'locked', 'completed', 'stopped'):
            self.send_notification(status, message)

# ------------------------------------
"""تاریخچه برای هر بودجه کلان"""

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

    def save(self, *args, **kwargs):
        if self.transaction_type == 'CONSUMPTION' and self.amount > self.allocation.remaining_amount:
            raise ValueError("مبلغ مصرف بیشتر از باقی‌مانده تخصیص است")
        if self.transaction_type in ['CONSUMPTION', 'ADJUSTMENT_DECREASE']:
            self.allocation.remaining_amount -= self.amount
        elif self.transaction_type in ['ALLOCATION', 'ADJUSTMENT_INCREASE']:
            self.allocation.remaining_amount += self.amount
        self.allocation.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.timestamp})"

    class Meta:
        verbose_name = _("تراکنش بودجه")
        verbose_name_plural = _("تراکنش‌های بودجه")
        default_permissions = ()

        permissions = [
            # ('BudgetTransaction_add', 'افزودن تراکنش بودجه'),
            # ('BudgetTransaction_update', 'بروزرسانی تراکنش بودجه'),
            # ('BudgetTransaction_delete', 'حــذف تراکنش بودجه'),
            ('BudgetTransaction_view', _('نمایش تراکنش بودجه')),
            # add/update/delete معمولاً توسط سیستم انجام می‌شه، نه کاربر
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

"""تخصیص بودجه به پروژه و زیر پروژه """
class ProjectBudgetAllocation(models.Model):
    """
    تخصیص بودجه از BudgetAllocation شعبه به پروژه یا زیرپروژه.
    توضیح: این مدل بودجه شعبه رو به پروژه یا زیرپروژه وصل می‌کنه و تاریخچه تخصیص رو نگه می‌داره.
    """
    budget_allocation = models.ForeignKey(
        'budgets.BudgetAllocation', on_delete=models.CASCADE, related_name='project_allocations',
        verbose_name=_("تخصیص بودجه شعبه"))
    project = models.ForeignKey('core.Project', on_delete=models.CASCADE, related_name='budget_allocations',
                                verbose_name=_("پروژه"))
    subproject = models.ForeignKey('core.SubProject', on_delete=models.CASCADE, null=True, blank=True,
                                   related_name='budget_allocations', verbose_name=_("زیرپروژه"))
    allocated_amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ تخصیص"))
    allocation_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ تخصیص"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,
                                   related_name='project_budget_allocations_created', verbose_name=_("ایجادکننده"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))

    def get_remaining_amount(self):
        if self.subproject:
            return get_subproject_remaining_budget(self.subproject)
        return get_project_remaining_budget(self.project)

    def clean(self):
        remaining = self.budget_allocation.get_remaining_amount()
        if self.allocated_amount > remaining:
            raise ValidationError(_("مبلغ تخصیص بیشتر از بودجه باقی‌مانده شعبه است"))
        if self.subproject and self.subproject.project != self.project:
            raise ValidationError(_("زیرپروژه باید به پروژه انتخاب‌شده تعلق داشته باشد"))
        if self.allocated_amount < 0:
            raise ValidationError(_("مبلغ تخصیص نمی‌تواند منفی باشد"))

    def save(self, *args, **kwargs):
        self.clean()
        if not self.pk:
            self.remaining_amount = self.allocated_amount
        super().save(*args, **kwargs)
        self.budget_allocation.remaining_amount = self.budget_allocation.get_remaining_amount()
        self.budget_allocation.save(update_fields=['remaining_amount'])
        self.remaining_amount = self.get_remaining_amount()
        super().save(update_fields=['remaining_amount'])


    def __str__(self):
        target = self.subproject.name if self.subproject else self.project.name
        return f"{target} - {self.allocated_amount:,} ({self.allocation_date})"

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

"""مدل BudgetHistory برای لاگ کردن تغییرات بودجه و تخصیص‌ها:"""
class BudgetHistory(models.Model):
    # content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    # content_object = GenericForeignKey('content_type', 'object_id')
    action = models.CharField(max_length=50, choices=[('CREATE', 'ایجاد'), ('UPDATE', 'بروزرسانی'), ('STOP', 'توقف'), ('REALLOCATE', 'انتقال')])
    amount = models.DecimalField(max_digits=25, decimal_places=2, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)
    transaction_type = models.CharField(max_length=20, choices=[('ALLOCATION', 'تخصیص'), ('CONSUMPTION', 'مصرف')],
                                        verbose_name=_("نوع تراکنش"))

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