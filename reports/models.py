from django.db import models
from django.db.models import Sum

from tankhah.models import Tankhah
from django.utils.translation import gettext_lazy as _


# Create your models here.
class FinancialReport(models.Model):
    tankhah = models.OneToOneField(Tankhah, on_delete=models.CASCADE, verbose_name=_("تنخواه"))
    total_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_("مبلغ کل"))
    approved_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_("مبلغ تأییدشده"))
    rejected_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_("مبلغ ردشده"))
    payment_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شماره پرداخت"))
    report_date = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ گزارش"))
    last_status = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('ردیابی تغییرات وضعیت'))
    total_factors = models.IntegerField(default=0, verbose_name=_("تعداد کل فاکتورها"))
    approved_factors = models.IntegerField(default=0, verbose_name=_("تعداد فاکتورهای تأییدشده"))
    rejected_factors = models.IntegerField(default=0, verbose_name=_("تعداد فاکتورهای ردشده"))

    def generate_report(self):
        factors = self.tankhah.factors.all()
        self.total_amount = factors.aggregate(total=Sum('amount'))['total'] or 0
        self.approved_amount = factors.filter(status='APPROVED').aggregate(total=Sum('amount'))['total'] or 0
        self.rejected_amount = factors.filter(status='REJECTED').aggregate(total=Sum('amount'))['total'] or 0
        self.total_factors = factors.count()
        self.approved_factors = factors.filter(status='APPROVED').count()
        self.rejected_factors = factors.filter(status='REJECTED').count()
        self.save()

    def __str__(self):
        return f"گزارش مالی {self.tankhah.number}"

    class Meta:
        verbose_name = _("گزارش مالی")
        verbose_name_plural = _("گزارش‌های مالی")
        default_permissions = ()
        permissions = [
            ('FinancialReport_view', 'نمایش گزارشات جامع مالی ♻️'),
            ('FinancialReport_add', 'افزودن گزارشات جامع مالی ♻️'),
            ('FinancialReport_update', 'ویرایش گزارشات جامع مالی ♻️'),
            ('FinancialReport_delet', 'حــذف گزارشات جامع مالی ♻️'),
        ]

######## Setting permissions
class Tankhah_FinancialReport(models.Model):
    class Meta:
        verbose_name='گزارشات تنخواه نهایی شده'
        verbose_name_plural='گزارشات تنخواه نهایی شده'
        default_permissions = ()
        permissions = [
            ('Tankhah_FinancialReport_view','امکان نمایش گزارشات تنخواه نهایی شده')
        ]
class print_financial_report(models.Model):
    class Meta:
        verbose_name=_('امکان چاپ گزارش ')
        verbose_name_plural=_('امکان چاپ گزارش ')
        default_permissions = ()
        permissions = [
            ('print_financial_report_view',_('امکان چاپ گزارش '))
        ]
class send_to_accounting(models.Model):
    class Meta:
        verbose_name=_('گزارشات تنخواه نهایی شده')
        verbose_name_plural=_('گزارشات تنخواه نهایی شده')
        default_permissions = ()
        permissions = [
            ('send_to_accounting_report_view',_('امکان ارسال گزارش '))
        ]
class TankhahDetailView(models.Model):
    class Meta:
        verbose_name=_('گزارش جزئیات تنخواه‌ها')
        verbose_name_plural=_('گزارش جزئیات تنخواه‌ها')
        default_permissions = ()
        permissions = [
            ('TankhahDetailView_report_view',_('گزارش جزئیات تنخواه‌ها '))
        ]

# ===== مجوزهای جدید برای Reports =====
class ReportsDashboard(models.Model):
    """مدل برای تعریف مجوزهای داشبورد گزارشات"""
    class Meta:
        verbose_name = _('داشبورد گزارشات')
        verbose_name_plural = _('داشبورد گزارشات')
        default_permissions = ()
        permissions = [
            ('reports.view_dashboard', _('نمایش داشبورد گزارشات')),
            ('reports.view_analytics', _('نمایش تحلیل‌های پیشرفته')),
            ('reports.export_reports', _('صادرات گزارشات')),
            ('reports.view_executive_dashboard', _('نمایش داشبورد اجرایی')),
        ]

class ReportsAPIs(models.Model):
    """مدل برای تعریف مجوزهای API های گزارشات"""
    class Meta:
        verbose_name = _('API های گزارشات')
        verbose_name_plural = _('API های گزارشات')
        default_permissions = ()
        permissions = [
            ('reports.api_dashboard_data', _('دسترسی به API داده‌های داشبورد')),
            ('reports.api_organizations', _('دسترسی به API سازمان‌ها')),
            ('reports.api_projects', _('دسترسی به API پروژه‌ها')),
            ('reports.api_budget_periods', _('دسترسی به API دوره‌های بودجه')),
            ('reports.api_export_data', _('دسترسی به API صادرات داده')),
        ]