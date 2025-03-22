from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import CustomUser
from core.models import Organization, Post, UserPost, Project, WorkflowStage

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
    amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد  "))

    date = models.DateField(default=timezone.now, verbose_name=_("تاریخ"))
    due_date = models.DateField(verbose_name=_('مهلت زمانی'))
    # organization = models.ForeignKey(Organization, on_delete=models.CASCADE, limit_choices_to={'org_type': 'COMPLEX'}, verbose_name=_("مجتمع"))
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, verbose_name=_('سازمان'))
    # project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("پروژه"))
    project = models.ForeignKey('core.Project', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('پروژه'))
    hq_status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True, verbose_name=_("وضعیت در HQ"))
    last_stopped_post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("آخرین پست متوقف‌شده"))
    letter_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شماره نامه"))
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='tanbakh_created', verbose_name=_("ایجادکننده"))
    # approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='tanbakh_approved', verbose_name=_("تأییدکننده"))
    approved_by = models.ManyToManyField(CustomUser, blank=True, verbose_name=_('تأییدکنندگان'))
    description = models.TextField()

    # current_stage = models.CharField(max_length=20, default='COMPLEX',
    #                                  choices=[('COMPLEX', 'مجموعه ها'), ('OPS', 'بهره‌برداری'), ('FIN', 'مالی')])
    current_stage = models.ForeignKey(WorkflowStage, on_delete=models.PROTECT, verbose_name=_('مرحله فعلی'))
    # namemamma=models.CharField(max_length=3)

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

            ('Tanbakh_add', 'ثبت تنخواه'),
            ('Tanbakh_update', 'بروزرسانی تنخواه'),
            ('Tanbakh_view', 'نمایش تنخواه'),
            ('Tanbakh_delete', 'حذف تنخواه'),

            ('Tanbakh_part_approve', 'تأیید رئیس قسمت'),
            ('Tanbakh_approve', 'تأیید مدیر مجموعه'),
            ('Tanbakh_hq_view', 'رصد دفتر مرکزی'),
            ('Tanbakh_hq_approve', 'تأیید رده بالا در دفتر مرکزی'),

            ('Tanbakh_HQ_OPS_PENDING', _('در حال بررسی - بهره‌برداری')),
            ('Tanbakh_HQ_OPS_APPROVED', _('تأییدشده - بهره‌برداری')),
            ('Tanbakh_HQ_FIN_PENDING', _('در حال بررسی - مالی')),
            ('Tanbakh_PAID', _('پرداخت‌شده')),
            ('Tanbakh_REJECTED', _('ردشده')),


        ]

class FactorDocument(models.Model):
    factor = models.ForeignKey('Factor', on_delete=models.CASCADE, related_name='documents', verbose_name=_("فاکتور"))
    file = models.FileField(upload_to='factors/documents/%Y/%m/%d/', verbose_name=_("فایل پیوست"))
    file_size = models.IntegerField(null=True, blank=True, verbose_name=_("حجم فایل (بایت)"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ بارگذاری"))

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return f"سند {self.id} برای فاکتور {self.factor.number}"

    class Meta:
        verbose_name = _("سند فاکتور")
        verbose_name_plural = _("اسناد فاکتور")

class Factor(models.Model):
    """مدل فاکتور برای جزئیات تنخواه"""
    STATUS_CHOICES = (
        ('PENDING', _('در حال بررسی')),
        ('APPROVED', _('تأییدشده')),
        ('REJECTED', _('ردشده')),
    )
    number = models.CharField(max_length=20, blank=True, verbose_name=_("شماره فاکتور"))
    tanbakh = models.ForeignKey(Tanbakh, on_delete=models.CASCADE, related_name='factors', verbose_name=_("تنخواه"))
    date = models.DateField(default=timezone.now, verbose_name=_("تاریخ"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_('مبلغ'), default=0)  # فرض بر وجود فیلد مبلغ
    description = models.TextField(verbose_name=_("توضیحات"))
    # file = models.FileField(upload_to='factors/%Y/%m/%d/', blank=True, null=True, verbose_name=_("فایل پیوست"))
    # file_size = models.IntegerField(null=True, blank=True, verbose_name=_("حجم فایل (بایت)"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("تأییدکننده"))

    def generate_number(self):
        """تولید شماره فاکتور با جداکننده قابل تنظیم"""
        sep = NUMBER_SEPARATOR
        serial = self.tanbakh.factors.count() + 1
        return f"{self.tanbakh.number}{sep}F{serial}"

    def save(self, *args, **kwargs):
        if not self.number:
            sep = "-"
            serial = self.tanbakh.factors.count() + 1
            self.number = f"{self.tanbakh.number}{sep}F{serial}"
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
    STATUS_CHOICES = (
        ('PENDING', _('در حال بررسی')),
        ('APPROVED', _('تأیید شده')),
        ('REJECTED', _('رد شده')),
    )
    factor = models.ForeignKey(Factor, on_delete=models.CASCADE, related_name='items', verbose_name=_("فاکتور"))
    description = models.CharField(max_length=255, verbose_name=_("شرح ردیف"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("مبلغ"))
    quantity = models.IntegerField(default=1, verbose_name=_("تعداد"))
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

class ApprovalLog(models.Model):
    ACTION_CHOICES = (
        ('APPROVE', _('تأیید')),
        ('REJECT', _('رد')),
        ('EDIT', _('ویرایش')),
    )
    tanbakh = models.ForeignKey(Tanbakh, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("تنخواه"))
    factor = models.ForeignKey(Factor, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("فاکتور"))
    factor_item = models.ForeignKey(FactorItem, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("ردیف فاکتور"))
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name=_("اقدام"))
    stage = models.ForeignKey(WorkflowStage, on_delete=models.PROTECT, verbose_name=_('مرحله'))
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name=_("کاربر"))
    comment = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان"))
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    post = models.ForeignKey(Post, on_delete=models.SET_NULL, null=True, verbose_name=_("پست تأییدکننده"))

    def __str__(self):
        return f"{self.user.username} - {self.date}"

    class Meta:
        verbose_name = _("تأیید")
        verbose_name_plural = _("تأییدات👍")
        default_permissions=()
        permissions = [
                    ('Approval_add','افزودن تأیید برای ثبت اقدامات تأیید یا رد '),
                    ('Approval_update','ویرایش تأیید برای ثبت اقدامات تأیید یا رد'),
                    ('Approval_delete','حــذف تأیید برای ثبت اقدامات تأیید یا رد'),
                    ('Approval_view','نمایش تأیید برای ثبت اقدامات تأیید یا رد'),
                ]

"""مشخص کردن کاربران یا نقش‌های مجاز برای هر مرحله"""
class StageApprover(models.Model):
    stage = models.ForeignKey(WorkflowStage, on_delete=models.CASCADE, verbose_name=_('مرحله'))
    post = models.ForeignKey('core.Post', on_delete=models.CASCADE, verbose_name=_('پست مجاز'))  # فرض بر وجود مدل Post

    def __str__(self):
        return f"{self.stage} - {self.post}"

    class Meta:
        verbose_name = _('تأییدکننده مرحله')
        verbose_name_plural = _('تأییدکنندگان مرحله')
        default_permissions=()
        permissions = [
            ('StageApprover_view','نمایش تأییدکننده مرحله'),
            ('StageApprover_add','افزودن تأییدکننده مرحله'),
            ('StageApprover_Update','بروزرسانی تأییدکننده مرحله'),
            ('StageApprover_delete','حــذف تأییدکننده مرحله'),
        ]

from django.views.generic import TemplateView
from django.utils import timezone
from django.db.models import Count, Sum
from .models import Tanbakh, ApprovalLog, WorkflowStage

class DashboardView(TemplateView):
    template_name = 'tanbakh/calc_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # تنخواه‌های در انتظار در هر مرحله
        stages = WorkflowStage.objects.all()
        for stage in stages:
            context[f'tanbakh_pending_{stage.name}'] = Tanbakh.objects.filter(
                current_stage=stage, status='PENDING'
            ).count()

        # تنخواه‌های نزدیک به مهلت
        context['tanbakh_due_soon'] = Tanbakh.objects.filter(
            due_date__lte=timezone.now() + timezone.timedelta(days=7),
            status='PENDING'
        ).count()

        # مجموع مبلغ تأییدشده در ماه جاری
        current_month = timezone.now().month
        context['total_approved_this_month'] = Tanbakh.objects.filter(
            status='APPROVED', date__month=current_month
        ).aggregate(total=Sum('amount'))['total'] or 0

        # آخرین فعالیت‌ها
        context['recent_approvals'] = ApprovalLog.objects.order_by('-timestamp')[:5]

        return context

class Dashboard_Tankhah(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('Dashboard_Tankhah_view','دسترسی به داشبورد تنخواه گردان ')
        ]