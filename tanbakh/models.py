from django.db import models
from accounts.models import CustomUser
from core.models import Organization, Post, UserPost, Project
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _

NUMBER_SEPARATOR = getattr(settings, 'NUMBER_SEPARATOR', '-')

class Tanbakh(models.Model):
    """مدل تنخواه برای ثبت و مدیریت درخواست‌های مالی"""
    STATUS_CHOICES = (
        ('DRAFT', _('پیش‌نویس')),
        ('PENDING', _('در حال بررسی')),
        ('APPROVED', _('تأییدشده')),
        ('SENT_TO_HQ', _('ارسال‌شده به HQ')),
        ('HQ_OPS_PENDING', _('در حال بررسی - بهره‌برداری')),
        ('HQ_OPS_APPROVED', _('تأییدشده - بهره‌برداری')),
        ('HQ_FIN_PENDING', _('در حال بررسی - مالی')),
        ('PAID', _('پرداخت‌شده')),
        ('REJECTED', _('ردشده')),
    )
    number = models.CharField(max_length=50, unique=True, blank=True, verbose_name=_("شماره تنخواه"))
    date = models.DateField(default=timezone.now, verbose_name=_("تاریخ"))
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, limit_choices_to={'org_type': 'COMPLEX'}, verbose_name=_("مجتمع"))
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("پروژه"))
    hq_status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True, verbose_name=_("وضعیت در HQ"))
    last_stopped_post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("آخرین پست متوقف‌شده"))
    letter_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شماره نامه"))
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='tanbakh_created', verbose_name=_("ایجادکننده"))
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='tanbakh_approved', verbose_name=_("تأییدکننده"))

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))

    current_stage = models.CharField(max_length=20, default='COMPLEX',
                                     choices=[('COMPLEX', 'مجموعه ها'), ('OPS', 'بهره‌برداری'), ('FIN', 'مالی')])


    def generate_number(self):
        """تولید شماره تنخواه با جداکننده قابل تنظیم"""
        sep = NUMBER_SEPARATOR
        date_str = self.date.strftime('%Y%m%d')
        org_code = self.organization.code
        project_code = self.project.code if self.project else 'NOPRJ'
        serial = Tanbakh.objects.filter(organization=self.organization, date=self.date).count() + 1
        return f"TNKH{sep}{date_str}{sep}{org_code}{sep}{project_code}{sep}{serial:03d}"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self.generate_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.number

    class Meta:
        verbose_name = _("تنخواه")
        verbose_name_plural = _("تنخواه‌ها")
        indexes = [
            models.Index(fields=['number', 'date', 'status']),
        ]
        default_permissions =()
        permissions = [
            ('Tanbakh_add','افزودن مدل تنخواه برای ثبت و مدیریت درخواست‌های مالی '),
            ('Tanbakh_update','ویرایش مدل تنخواه برای ثبت و مدیریت درخواست‌های مالی'),
            ('Tanbakh_delete','حــذف مدل تنخواه برای ثبت و مدیریت درخواست‌های مالی'),
            ('Tanbakh_view','نمایش مدل تنخواه برای ثبت و مدیریت درخواست‌های مالی'),
        ]

class Factor(models.Model):
    """مدل فاکتور برای جزئیات تنخواه"""
    STATUS_CHOICES = (
        ('PENDING', _('در حال بررسی')),
        ('APPROVED', _('تأییدشده')),
        ('REJECTED', _('ردشده')),
    )
    number = models.CharField(max_length=50, blank=True, verbose_name=_("شماره فاکتور"))
    tanbakh = models.ForeignKey(Tanbakh, on_delete=models.CASCADE, related_name='factors', verbose_name=_("تنخواه"))
    date = models.DateField(default=timezone.now, verbose_name=_("تاریخ"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("مبلغ"))
    description = models.TextField(verbose_name=_("توضیحات"))
    file = models.FileField(upload_to='factors/%Y/%m/%d/', blank=True, null=True, verbose_name=_("فایل پیوست"))
    file_size = models.IntegerField(null=True, blank=True, verbose_name=_("حجم فایل (بایت)"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))

    def generate_number(self):
        """تولید شماره فاکتور با جداکننده قابل تنظیم"""
        sep = NUMBER_SEPARATOR
        serial = self.tanbakh.factors.count() + 1
        return f"{self.tanbakh.number}{sep}F{serial}"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self.generate_number()
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.number} ({self.tanbakh.number})"

    class Meta:
        verbose_name = _("فاکتور")
        verbose_name_plural = _("فاکتورها")
        indexes = [
            models.Index(fields=['number', 'date', 'status']),
        ]
        default_permissions=()
        permissions = [
                    ('Factor_add','افزودن فاکتور برای جزئیات تنخواه '),
                    ('Factor_update','ویرایش فاکتور برای جزئیات تنخواه'),
                    ('Factor_delete','حــذف فاکتور برای جزئیات تنخواه'),
                    ('Factor_view','نمایش فاکتور برای جزئیات تنخواه'),
                ]

class FactorItem(models.Model):
    """  اقلام فاکتور """
    factor = models.ForeignKey(Factor, on_delete=models.CASCADE, related_name='items', verbose_name=_("فاکتور"))
    description = models.CharField(max_length=255, verbose_name=_("شرح ردیف"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("مبلغ"))
    quantity = models.IntegerField(default=1, verbose_name=_("تعداد"))

    STATUS_CHOICES = (
        ('PENDING', _('در حال بررسی')),
        ('APPROVED', _('تأییدشده')),
        ('REJECTED', _('ردشده')),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))

    def __str__(self):
        return f"{self.description} - {self.amount}"

    class Meta:
        verbose_name = _("ردیف فاکتور")
        verbose_name_plural = _("ردیف‌های فاکتور")
        default_permissions = ()
        permissions = [
            ('FactorItem_add','افزودن اقلام فاکتور'),
            ('FactorItem_update','ویرایش اقلام فاکتور'),
            ('FactorItem_view','نمایش اقلام فاکتور'),
            ('FactorItem_delete','حذف اقلام فاکتور'),
        ]
class Approval(models.Model):
    """مدل تأیید برای ثبت اقدامات تأیید یا رد"""
    BRANCH_CHOICES = (
        ('OPS', _('بهره‌برداری')),
        ('FIN', _('مالی و اداری')),
        ('COMPLEX', _('مجتمع')),
    )
    tanbakh = models.ForeignKey(Tanbakh, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("تنخواه"))
    factor = models.ForeignKey(Factor, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("فاکتور"))
    factor_item = models.ForeignKey(FactorItem, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("ردیف فاکتور"))
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name=_("کاربر"))
    date = models.DateTimeField(default=timezone.now, verbose_name=_("تاریخ"))
    comment = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    branch = models.CharField(max_length=10, choices=BRANCH_CHOICES, verbose_name=_("شاخه"))
    is_approved = models.BooleanField(default=False, verbose_name=_("تأیید شده؟"))

    def __str__(self):
        return f"{self.user.username} - {self.date}"

    class Meta:
        verbose_name = _("تأیید")
        verbose_name_plural = _("تأییدات")
        default_permissions=()
        permissions = [
                    ('Approval_add','افزودن تأیید برای ثبت اقدامات تأیید یا رد '),
                    ('Approval_update','ویرایش تأیید برای ثبت اقدامات تأیید یا رد'),
                    ('Approval_delete','حــذف تأیید برای ثبت اقدامات تأیید یا رد'),
                    ('Approval_view','نمایش تأیید برای ثبت اقدامات تأیید یا رد'),
                ]