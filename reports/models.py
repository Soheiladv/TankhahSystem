from django.db import models

from tankhah.models import Tankhah
from django.utils.translation import gettext_lazy as _


# Create your models here.
class FinancialReport(models.Model):
    tankhah = models.OneToOneField(Tankhah, on_delete=models.CASCADE, verbose_name=_("تنخواه"))
    total_amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ کل"))
    approved_amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ تأییدشده"))
    rejected_amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ ردشده"))
    payment_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شماره پرداخت"))
    report_date = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ گزارش"))

    def generate_report(self):
        self.total_amount = self.tankhah.amount
        self.approved_amount = sum(f.amount for f in self.tankhah.factors.filter(status='APPROVED'))
        self.rejected_amount = sum(f.amount for f in self.tankhah.factors.filter(status='REJECTED'))
        self.payment_number = self.tankhah.payment_number
        self.save()

    def __str__(self):
        return f"گزارش مالی {self.tankhah.number}"