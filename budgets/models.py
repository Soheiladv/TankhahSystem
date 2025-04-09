from django.db import models
import logging

from accounts.models import CustomUser
from core.models import Organization, Project, SubProject, WorkflowStage
from django.utils.translation import gettext_lazy as _
logger = logging.getLogger(__name__)


# Create your models here.
class PettyCash(models.Model):
    STATUS_CHOICES = (
        ('PENDING', _('در انتظار')),
        ('APPROVED', _('تأیید شده')),
        ('REJECTED', _('رد شده')),
        ('PAID', _('پرداخت شده')),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, verbose_name=_("سازمان"))
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("پروژه"))
    subproject = models.ForeignKey(SubProject, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("ساب‌پروژه"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("مبلغ (ریال)"))
    budget = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("بودجه تخصیصی (ریال)"))
    remaining_budget = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=_("بودجه باقیمانده"))
    current_stage = models.ForeignKey(WorkflowStage, on_delete=models.SET_NULL, null=True, verbose_name=_("مرحله فعلی"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_petty_cash', verbose_name=_("ایجاد کننده"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))

    def save(self, *args, **kwargs):
        # تنظیم بودجه اولیه
        if not self.pk:  # فقط موقع ایجاد
            self.remaining_budget = self.budget
        # چک کردن بودجه
        if self.amount > self.remaining_budget:
            raise ValueError("مبلغ تنخواه نمی‌تواند بیشتر از بودجه باقیمانده باشد")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"تنخواه {self.id} - {self.organization} ({self.amount} ریال)"

    class Meta:
        verbose_name = _("تنخواه")
        verbose_name_plural = _("تنخواه‌ها")
        permissions = [
            ('PettyCash_view', 'نمایش تنخواه'),
            ('PettyCash_add', 'افزودن تنخواه'),
            ('PettyCash_update', 'بروزرسانی تنخواه'),
            ('PettyCash_delete', 'حذف تنخواه'),
        ]