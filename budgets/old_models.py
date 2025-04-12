import logging

import jdatetime
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import CustomUser
from budgets.budget_calculations import get_subproject_remaining_budget, get_project_remaining_budget
from core.models import Organization, Project, SubProject, WorkflowStage

logger = logging.getLogger(__name__)
from decimal import Decimal

# Create your models here.
 # -- New
# ------------------------------------
"""BudgetPeriod (دوره بودجه کلان):"""
class BudgetPeriod(models.Model):
    """BudgetPeriod (دوره بودجه کلان):
    توضیح: این مدل بودجه کل رو جدا از Organization نگه می‌داره. remaining_amount موقع تخصیص آپدیت می‌شه و lock_condition مشخص می‌کنه کی قفل بشه.
    """
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE,
                                     limit_choices_to={'org_type': 'HQ'}, verbose_name=_("دفتر مرکزی"))
    name = models.CharField(max_length=100, unique=True, verbose_name=_("نام دوره بودجه"))
    start_date = models.DateField(verbose_name=_("تاریخ شروع"))
    end_date = models.DateField(verbose_name=_("تاریخ پایان"))
    total_amount = models.DecimalField(max_digits=25, decimal_places=0, verbose_name=_("مبلغ کل"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    is_archived = models.BooleanField(default=False, verbose_name=_("بایگانی شده"))

    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,
                                   related_name='budget_periods_created', verbose_name=_("ایجادکننده"))
    locked_percentage = models.DecimalField(_('درصد قفل‌شده'), max_digits=5, decimal_places=0,
                                            help_text=_('درصد بودجه که قفل می‌شود (۰-۱۰۰)'))
    warning_threshold = models.DecimalField(_('آستانه اخطار'), max_digits=5, decimal_places=0,
                                            help_text=_('درصدی که اخطار نمایش داده می‌شود (۰-۱۰۰)'))
    lock_condition = models.CharField(max_length=50, choices=[
        ('AFTER_DATE', _('بعد از تاریخ پایان')),
        ('MANUAL', _('دستی')),
    ], default='AFTER_DATE', verbose_name=_("شرط قفل"))

    def get_remaining_amount(self):
        """محاسبه باقی‌مانده بودجه به‌صورت دینامیک"""
        allocated = BudgetAllocation.objects.filter(budget_period=self).aggregate(total=Sum('allocated_amount'))[
                        'total'] or Decimal("0")
        return self.total_amount - allocated

    def get_locked_amount(self):
        """محاسبه مقدار قفل‌شده بودجه بر اساس درصد قفل‌شده"""
        return (self.total_amount * self.locked_percentage) / Decimal("100")

    def get_warning_amount(self):
        return (self.total_amount * self.warning_threshold) / Decimal("100")


    def check_budget_status(self):
        remaining = self.get_remaining_amount()
        locked = self.get_locked_amount()
        warning = self.get_warning_amount()
        if not self.is_active:
            return 'inactive', 'دوره غیرفعال است.'
        if remaining <= locked:
            return 'locked', 'بودجه به حد قفل‌شده رسیده است.'
        if remaining <= warning:
            return 'warning', 'بودجه به آستانه هشدار رسیده است.'
        return 'normal', 'وضعیت عادی'


    def send_notification(self, status, message):
        # پیدا کردن کاربران مرتبط (مثلاً مدیران سازمان و زیرمجموعه‌ها)
        recipients = CustomUser.objects.filter(
            models.Q(organization=self.organization) |  # مدیران سازمان
            models.Q(organization__parent=self.organization)  # زیرمجموعه‌ها
        ).distinct()
        from tankhah.models import Notification
        for recipient in recipients:
            Notification.objects.create(
                recipient=recipient,
                message=f"{self.name}: {message}",
                level='WARNING' if status == 'warning' else 'ERROR' if status == 'locked' else 'INFO'
            )

    # def save(self, *args, **kwargs):
    #     if self.end_date < self.start_date:
    #         raise ValueError("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد")
    #     if self.lock_condition == 'AFTER_DATE' and self.end_date < timezone.now().date():
    #         self.is_active = False
    #     super().save(*args, **kwargs)
    #     # بعد از ذخیره، وضعیت رو چک کن و اعلان بفرست
    #     self.check_budget_status()

    def __str__(self):
        return f"{self.name} ({self.organization.code})"

    class Meta:
        verbose_name = _("دوره بودجه")
        verbose_name_plural = _("دوره‌های بودجه")
        default_permissions = ()
        permissions = [
            ('BudgetPeriod_add', _('افزودن دوره بودجه')),
            ('BudgetPeriod_update', _('بروزرسانی دوره بودجه')),
            ('BudgetPeriod_view', _('نمایش دوره بودجه')),
            ('BudgetPeriod_delete', _('حذف دوره بودجه')),
            ('BudgetPeriod_archive', _('بایگانی دوره بودجه')),
        ]

# ------------------------------------
""" BudgetAllocation (تخصیص بودجه):"""
class BudgetAllocation(models.Model):
    """
    توضیح: تخصیص بودجه به هر سطح از Organization (شعبه یا اداره داخلی). موقع ذخیره، بودجه کل رو چک و آپدیت می‌کنه.
    """
    project = models.ForeignKey('core.Project', on_delete=models.CASCADE, related_name='allocations', verbose_name=_("پروژه"))
    budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE,related_name='allocations', verbose_name=_("دوره بودجه"))
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE,verbose_name=_("سازمان دریافت‌کننده"))
    allocated_amount = models.DecimalField(max_digits=25, decimal_places=2,verbose_name=_("مبلغ تخصیص"))
    # remaining_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0,verbose_name=_("باقی‌مانده تخصیص"))
    allocation_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ تخصیص"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,related_name='budget_allocations_created', verbose_name=_("ایجادکننده"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    status = models.BooleanField(default=True,verbose_name=_('فعال'))
    ALLOCATION_TYPES = (('amount', _('مبلغ ثابت')),('percent', _('درصد')),)
    allocation_type = models.CharField(max_length=20, choices=ALLOCATION_TYPES, default='amount', verbose_name=_("نوع تخصیص"))
    is_active= models.BooleanField(verbose_name=_('فعال'))

    def get_remaining_amount(self):
        used = ProjectBudgetAllocation.objects.filter(budget_allocation=self).aggregate(total=Sum('allocated_amount'))[
                   'total'] or Decimal("0")
        return self.allocated_amount - used

    def save(self, *args, **kwargs):
        self.clean()
        if not self.pk:
            self.remaining_amount = self.allocated_amount
        super().save(*args, **kwargs)
        self.remaining_amount = self.get_remaining_amount()
        super().save(update_fields=['remaining_amount'])

    def __str__(self):
        # نمایش بهتر با تاریخ جلالی و اطلاعات سازمان و دوره
        from jdatetime import datetime as jdatetime
        jalali_date = jdatetime.fromgregorian(date=self.allocation_date).strftime('%Y/%m/%d')
        return f"ردیف بودجه{self.id}-{self.organization.name} - {self.budget_period.name} - {self.allocated_amount:,} ({jalali_date})"

    class Meta:
        verbose_name = _("تخصیص بودجه")
        verbose_name_plural = _("تخصیص‌های بودجه")
        default_permissions = ()
        permissions = [
            ('BudgetAllocation_add', _('افزودن تخصیص بودجه')),
            ('BudgetAllocation_view', _('نمایش تخصیص بودجه')),
            ('BudgetAllocation_update', _('بروزرسانی تخصیص بودجه')),
            ('BudgetAllocation_delete', _('حذف تخصیص بودجه')),
            ('budgetallocation_adjust', _('تنظیم تخصیص بودجه (افزایش/کاهش)')),
        ]
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
class SignatureLog(models.Model):
    """تکمیل برای log"""
    pass

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
    remaining_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0,
                                           verbose_name=_("باقی‌مانده تخصیص"))
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
