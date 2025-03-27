import os
from django.conf import settings
from django.db import models, transaction
from django.db.models import Sum, Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import Post  # بررسی کنید که مسیر درست است
from core.models import WorkflowStage  # اگر در همان اپلیکیشن است
from accounts.models import CustomUser
from core.models import Organization, Post, UserPost, Project, WorkflowStage
from django.views.generic import TemplateView

NUMBER_SEPARATOR = getattr(settings, 'NUMBER_SEPARATOR', '-')

def get_default_workflow_stage():
    return WorkflowStage.objects.get(name='HQ_INITIAL').id  # نام را با 'HQ_ITDC' جایگزین کنید اگر متفاوت است

def tanbakh_document_path(instance, filename):
    # مسیر آپلود: documents/شماره_تنخواه/نام_فایل
    extension = os.path.splitext(filename)[1]  # مثل .pdf
    return f'documents/{instance.tanbakh.number}/document{extension}'

class TankhahDocument(models.Model):
    tankhah  = models.ForeignKey('Tankhah', on_delete=models.CASCADE,verbose_name=_("تنخواه"), related_name='documents')
    document = models.FileField(upload_to=tanbakh_document_path,  verbose_name=_("سند"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ آپلود")
    file_size = models.IntegerField(null=True, blank=True, verbose_name=_("حجم فایل (بایت)"))

    def save(self, *args, **kwargs):
        if self.document:
            self.file_size = self.document.size
        super().save(*args, **kwargs)

    def __str__(self):
        return f"سند {self.tanbakh.number} - {self.uploaded_at}-{self.document.name}"


class Tankhah(models.Model):
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
    date = models.DateTimeField(default=timezone.now, verbose_name=_("تاریخ"))
    due_date = models.DateTimeField(null=True, blank=True, verbose_name=_('مهلت زمانی'))
    # due_date = models.DateTimeField(verbose_name=_('مهلت زمانی'))  # پشنهاد به کاربر
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد")) # اجبار در توقف
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, verbose_name=_('مجموعه/شعبه'))
    project = models.ForeignKey('core.Project', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('پروژه'))
    letter_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شماره نامه"))
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='tanbakh_created', verbose_name=_("ایجادکننده"))
    approved_by = models.ManyToManyField(CustomUser, blank=True, verbose_name=_('تأییدکنندگان'))
    description = models.TextField(verbose_name=_("توضیحات"))
    current_stage = models.ForeignKey(WorkflowStage, on_delete=models.SET_NULL, null=True,
                                      default=get_default_workflow_stage, verbose_name="مرحله فعلی")

    # current_stage = models.ForeignKey(WorkflowStage,
    #           on_delete=models.SET_NULL,null=True,default=1,#get_default_workflow_stage,  # پیش‌فرض: ثبت در دفتر مرکزی
    #     verbose_name="مرحله فعلی")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES,  default='DRAFT', verbose_name=_("وضعیت"))
    hq_status = models.CharField(max_length=20, default='PENDING',
                                 choices=STATUS_CHOICES, null=True, blank=True,
                                 verbose_name=_("وضعیت در HQ"))
    last_stopped_post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("آخرین پست متوقف‌شده"))

    is_archived = models.BooleanField(default=False, verbose_name=_("آرشیو شده"))

    archived_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان آرشیو")
    canceled = models.BooleanField(default=False, verbose_name="لغو شده")

    def generate_number(self):
        """تولید شماره یکتا برای تنخواه با تاریخ شمسی"""
        sep = NUMBER_SEPARATOR

        # تبدیل تاریخ میلادی به شمسی
        import jdatetime
        jalali_date = jdatetime.datetime.fromgregorian(datetime=self.date)
        date_str = jalali_date.strftime('%Y%m%d')  # فرمت YYYYMMDD شمسی

        org_code = self.organization.code
        project_code = self.project.code if self.project else 'NOPRJ'

        # پیدا کردن بالاترین شماره سریال برای این تاریخ و سازمان
        with transaction.atomic():
            max_serial = Tanbakh.objects.filter(
                organization=self.organization,
                date__date=self.date.date()  # همچنان از تاریخ میلادی برای فیلتر استفاده می‌کنیم
            ).aggregate(Max('number'))['number__max']

            if max_serial:
                # استخراج شماره سریال از آخرین شماره موجود
                last_number = max_serial.split(sep)[-1]
                serial = int(last_number) + 1
            else:
                serial = 1

            new_number = f"TNKH{sep}{date_str}{sep}{org_code}{sep}{project_code}{sep}{serial:03d}"
            # چک کردن یکتایی و افزایش سریال در صورت نیاز
            while Tanbakh.objects.filter(number=new_number).exists():
                serial += 1
                new_number = f"TNKH{sep}{date_str}{sep}{org_code}{sep}{project_code}{sep}{serial:03d}"
            return new_number

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

            ('Tanbakh_part_approve', '👍تأیید رئیس قسمت'),
            ('Tanbakh_approve', '👍تأیید مدیر مجموعه'),
            ('Tanbakh_hq_view', 'رصد دفتر مرکزی'),
            ('Tanbakh_hq_approve', '👍تأیید رده بالا در دفتر مرکزی'),

            ('Tanbakh_HQ_OPS_PENDING', _('در حال بررسی - بهره‌برداری')),
            ('Tanbakh_HQ_OPS_APPROVED', _('👍تأییدشده - بهره‌برداری')),
            ('Tanbakh_HQ_FIN_PENDING', _('در حال بررسی - مالی')),
            ('Tanbakh_PAID', _('پرداخت‌شده')),
            ('Tanbakh_REJECTED', _('ردشده')),
            ("FactorItem_approve", "👍تایید/رد ردیف فاکتور دفتر مرکزی "),
            ('edit_full_tanbakh','👍😊تغییرات کاربری در فاکتور /تایید یا رد ردیف ها '),

            ('Dashboard_Core_view', 'دسترسی به داشبورد Core پایه'),
            ('DashboardView_flows_view', 'دسترسی به روند تنخواه گردانی'),
            ('Dashboard__view', 'دسترسی به داشبورد اصلی 💻'),

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
        return f"سند برای فاکتور {self.factor.number} ({self.uploaded_at})"

    class Meta:
        verbose_name = _("سند فاکتور")
        verbose_name_plural = _("اسناد فاکتور")
        default_permissions = ()
        permissions = [
            ('FactorDocument_add','افزودن سند فاکتور'),
            ('FactorDocument_update','بروزرسانی سند فاکتور'),
            ('FactorDocument_view','نمایش سند فاکتور'),
            ('FactorDocument_delete','حــذف سند فاکتور'),
        ]

class Factor(models.Model):
    """مدل فاکتور برای جزئیات تنخواه"""
    STATUS_CHOICES = (
        ('PENDING', _('در حال بررسی')),
        ('APPROVED', _('تأییدشده')),
        ('REJECTED', _('ردشده')),
    )
    number = models.CharField(max_length=60, blank=True, verbose_name=_("شماره فاکتور"))
    tankhah = models.ForeignKey(Tankhah, on_delete=models.CASCADE, related_name='factors', verbose_name=_("تنخواه"))
    date = models.DateField(default=timezone.now, verbose_name=_("تاریخ"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_('مبلغ'), default=0)  # فرض بر وجود فیلد مبلغ
    description = models.TextField(verbose_name=_("توضیحات"))
    # file = models.FileField(upload_to='factors/%Y/%m/%d/', blank=True, null=True, verbose_name=_("فایل پیوست"))
    # file_size = models.IntegerField(null=True, blank=True, verbose_name=_("حجم فایل (بایت)"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))
    # approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("تأییدکننده"))
    approved_by = models.ManyToManyField(CustomUser, blank=True, verbose_name=_("تأییدکنندگان"))

    is_finalized = models.BooleanField(default=False, verbose_name=_("نهایی شده"))

    locked = models.BooleanField(default=False, verbose_name="قفل شده")

    def generate_number(self):
        """تولید شماره فاکتور با جداکننده قابل تنظیم"""
        sep = NUMBER_SEPARATOR
        serial = self.tanbakh.factors.count() + 1
        return f"{self.tanbakh.number}{sep}F{serial}"

    def save(self, *args, **kwargs):
        if not self.number:
            sep = "-"
            serial = self.tanbakh.factors.count() + 1
            # self.number = f"{self.tanbakh.number}{sep}F{serial}"
            self.number = self.generate_number()
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
                    ('a_factor_add','افزودن فاکتور برای جزئیات تنخواه '),
                    ('a_factor_update','ویرایش فاکتور برای جزئیات تنخواه'),
                    ('a_factor_delete','حــذف فاکتور برای جزئیات تنخواه'),
                    ('a_factor_view','نمایش فاکتور برای جزئیات تنخواه'),
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
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("مبلغ") )
    # amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("مبلغ"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))
    quantity = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("تعداد"))
    # quantity = models.IntegerField(default=1, verbose_name=_("تعداد"))
    unit_price = models.DecimalField(max_digits=25,default=1, decimal_places=1, verbose_name=_("قیمت واحد"))

    def save(self, *args, **kwargs):
        self.amount = self.unit_price * self.quantity
        super().save(*args, **kwargs)

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
        ('RETURN', _('بازگشت')),
        ('CANCEL', _('لغو'))
    )
    tankhah  = models.ForeignKey(Tankhah, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("تنخواه"))
    factor = models.ForeignKey(Factor, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("فاکتور"))
    factor_item = models.ForeignKey(FactorItem, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("ردیف فاکتور"))
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name=_("اقدام"))
    stage = models.ForeignKey(WorkflowStage, on_delete=models.PROTECT, verbose_name=_('مرحله'))
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name=_("کاربر"))
    comment = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان"))
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    post = models.ForeignKey(Post, on_delete=models.SET_NULL, null=True, verbose_name=_("پست تأییدکننده"))
    changed_field = models.CharField(max_length=50, blank=True, null=True, verbose_name="فیلد تغییر یافته")
    def __str__(self):
        return f"{self.user.username} - {self.action} ({self.date})"


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
    post = models.ForeignKey( 'core.Post', on_delete=models.CASCADE, verbose_name=_('پست مجاز'))  # فرض بر وجود مدل Post
    is_active = models.BooleanField(default=True, verbose_name="وضعیت فعال")

    def __str__(self):
        return f"{self.stage} - {self.post}"

    class Meta:
        verbose_name = _('تأییدکننده مرحله')
        verbose_name_plural = _('تأییدکنندگان مرحله')
        default_permissions=()
        permissions = [
            ('stageapprover__view','نمایش تأییدکننده مرحله'),
            ('stageapprover__add','افزودن تأییدکننده مرحله'),
            ('stageapprover__Update','بروزرسانی تأییدکننده مرحله'),
            ('stageapprover__delete','حــذف تأییدکننده مرحله'),
        ]

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

class TanbakhFinalApproval(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('TanbakhFinalApproval_view','دسترسی تایید یا رد تنخواه گردان ')
        ]
# class IndexView(models.Model):
#     class Meta:
#         default_permissions = ()
#         permissions = [
#             ('IndexView_dashboard_view','دسترسی به داشبورد تنخواه گردان IndexView_dashboard')
#         ]
