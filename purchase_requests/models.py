from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PurchaseRequest(models.Model):
    number = models.CharField(max_length=100, unique=True, blank=True, verbose_name=_("شماره درخواست"))
    organization = models.ForeignKey('core.Organization', on_delete=models.PROTECT, verbose_name=_('سازمان'))
    project = models.ForeignKey('core.Project', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('پروژه'))
    subproject = models.ForeignKey('core.SubProject', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('زیرپروژه'))
    date = models.DateField(default=timezone.now, verbose_name=_('تاریخ'))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, related_name='created_purchase_requests', verbose_name=_('ایجادکننده'))
    description = models.TextField(blank=True, verbose_name=_('توضیحات'))
    status = models.ForeignKey('core.Status', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('وضعیت'))
    # یکپارچه‌سازی خارجی
    source_system = models.CharField(max_length=100, blank=True, verbose_name=_('سامانه منبع'))
    external_id = models.CharField(max_length=150, blank=True, verbose_name=_('شناسه خارجی'))
    external_payload = models.JSONField(null=True, blank=True, verbose_name=_('داده خام دریافتی/ارسالی'))
    is_synced = models.BooleanField(default=False, verbose_name=_('همگام‌سازی شده'))
    synced_at = models.DateTimeField(null=True, blank=True, verbose_name=_('زمان آخرین همگام‌سازی'))

    class Meta:
        verbose_name = _('درخواست کالا')
        verbose_name_plural = _('درخواست‌های کالا')
        default_permissions = ()
        permissions = [
            ('purchase_request_add', 'افزودن درخواست کالا'),
            ('purchase_request_view', 'نمایش درخواست کالا'),
            ('purchase_request_update', 'ویرایش درخواست کالا'),
            ('purchase_request_delete', 'حذف درخواست کالا'),
            ('purchase_request_approve', 'تأیید درخواست کالا'),
        ]
        indexes = [
            models.Index(fields=['number']),
            models.Index(fields=['organization', 'date']),
            models.Index(fields=['source_system', 'external_id']),
        ]

    def __str__(self):
        return self.number or f"PR-{self.pk}"

    @property
    def total_amount(self) -> Decimal:
        return self.items.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')


class PurchaseRequestItem(models.Model):
    request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name='items', verbose_name=_('درخواست'))
    description = models.CharField(max_length=255, verbose_name=_('شرح'))
    quantity = models.DecimalField(max_digits=25, decimal_places=2, default=1, verbose_name=_('تعداد'))
    unit_price = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_('قیمت واحد'))
    amount = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_('مبلغ'))
    # آماده یکپارچه‌سازی
    sku = models.CharField(max_length=100, blank=True, verbose_name=_('شناسه کالا/کد فنی'))
    uom = models.CharField(max_length=50, blank=True, verbose_name=_('واحد'))
    external_item_id = models.CharField(max_length=150, blank=True, verbose_name=_('شناسه خارجی آیتم'))

    def save(self, *args, **kwargs):
        if self.quantity is not None and self.unit_price is not None:
            self.amount = (self.quantity or Decimal('0')) * (self.unit_price or Decimal('0'))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} - {self.amount}"

    class Meta: 
        verbose_name = _('ردیف درخواست کالا')
        verbose_name_plural = _('ردیف‌های درخواست کالا')
        default_permissions = ()
        permissions = [
            ('purchase_request_item_add', 'افزودن ردیف درخواست کالا'),
            ('purchase_request_item_view', 'نمایش ردیف درخواست کالا'),
            ('purchase_request_item_update', 'ویرایش ردیف درخواست کالا'),
            ('purchase_request_item_delete', 'حذف ردیف درخواست کالا'),
        ]
        indexes = [
            models.Index(fields=['request']),
            models.Index(fields=['sku']),
        ]


