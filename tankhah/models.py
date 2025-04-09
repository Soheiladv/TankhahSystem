import logging
import os

from django.conf import settings
from django.db import models, transaction
from django.db.models import Sum, Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from accounts.models import CustomUser
from core.models import Organization, Post, UserPost, Project, WorkflowStage
from core.models import Post, SubProject  # بررسی کنید که مسیر درست است
from core.models import WorkflowStage  # اگر در همان اپلیکیشن است

NUMBER_SEPARATOR = getattr(settings, 'NUMBER_SEPARATOR', '-')

def get_default_workflow_stage():
    try:
        return WorkflowStage.objects.get(name='HQ_INITIAL').id
    except WorkflowStage.DoesNotExist:
        # اگه پیدا نشد، اولین مرحله رو برگردون یا None
        stage = WorkflowStage.objects.order_by('order').first()
        return stage.id if stage else None

def tankhah_document_path(instance, filename):
    # مسیر آپلود: documents/شماره_تنخواه/نام_فایل
    extension = os.path.splitext(filename)[1]  # مثل .pdf
    return f'documents/{instance.tankhah.number}/document{extension}/%Y/%m/%d/'

class TankhahDocument(models.Model):
    tankhah  = models.ForeignKey('Tankhah', on_delete=models.CASCADE,verbose_name=_("تنخواه"), related_name='documents')
    document = models.FileField(upload_to=tankhah_document_path,  verbose_name=_("سند"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ آپلود")
    file_size = models.IntegerField(null=True, blank=True, verbose_name=_("حجم فایل (بایت)"))

    def save(self, *args, **kwargs):
        if self.document:
            self.file_size = self.document.size
        super().save(*args, **kwargs)

    def __str__(self):
        return f"سند {self.tankhah.number} - {self.uploaded_at}-{self.document.name}"
    class Meta:
        default_permissions = ()
        permissions = [
            ('TankhahDocument_view','نمایش اسناد فاکتور منتهی به تنخواه'),
            ('TankhahDocument_add','افزودن اسناد فاکتور منتهی به تنخواه'),
            ('TankhahDocument_update','بروزرسانی اسناد فاکتور منتهی به تنخواه'),
            ('TankhahDocument_delete','حــذف اسناد فاکتور منتهی به تنخواه'),
        ]

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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد")) # اجبار در توقف
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, verbose_name=_('مجموعه/شعبه'))
    project = models.ForeignKey('core.Project', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('پروژه'))
    subproject = models.ForeignKey(SubProject, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("زیر مجموعه پروژه"))
    letter_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شماره نامه"))
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='tankhah_created', verbose_name=_("ایجادکننده"))
    approved_by = models.ManyToManyField(CustomUser, blank=True, verbose_name=_('تأییدکنندگان'))
    description = models.TextField(verbose_name=_("توضیحات"))
    current_stage = models.ForeignKey(WorkflowStage, on_delete=models.SET_NULL, null=True,
                                      default=get_default_workflow_stage, verbose_name="مرحله فعلی")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,  default='DRAFT', verbose_name=_("وضعیت"))
    hq_status = models.CharField(max_length=20, default='PENDING',
                                 choices=STATUS_CHOICES, null=True, blank=True,
                                 verbose_name=_("وضعیت در HQ"))
    last_stopped_post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("آخرین پست متوقف‌شده"))

    is_archived = models.BooleanField(default=False, verbose_name=_("آرشیو شده"))

    payment_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شماره پرداخت"))
    is_locked = models.BooleanField(default=False, verbose_name=_("قفل شده"))
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان آرشیو")
    canceled = models.BooleanField(default=False, verbose_name="لغو شده")
    budget = models.DecimalField(budgets, decimal_places=2, verbose_name=_("بودجه تخصیصی"))
    remaining_budget = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_("بودجه باقیمانده"))

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
            max_serial = Tankhah.objects.filter(
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
            while Tankhah.objects.filter(number=new_number).exists():
                serial += 1
                new_number = f"TNKH{sep}{date_str}{sep}{org_code}{sep}{project_code}{sep}{serial:03d}"
            return new_number

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self.generate_number()
            # اگه وضعیت COMPLETED یا PAID باشه، قفل کن
        if self.status in ['COMPLETED', 'PAID'] and not self.is_locked:
            self.is_locked = True

            self.remaining_budget = self.budget
        if self.amount > self.budget:
            raise ValueError("مبلغ تنخواه نمی‌تواند بیشتر از بودجه تخصیصی باشد")

        super().save(*args, **kwargs)

    def __str__(self):
        project_str = self.project.name if self.project else 'بدون پروژه'
        subproject_str = f" ({self.subproject.name})" if self.subproject else ''
        return f"{self.number} - {project_str}{subproject_str}"

    class Meta:
        verbose_name = _("تنخواه")
        verbose_name_plural = _("تنخواه‌ها")
        indexes = [
            models.Index(fields=['number', 'date', 'status' ,'organization'])]
        default_permissions =()
        permissions = [

            ('Tankhah_add', 'ثبت تنخواه'),
            ('Tankhah_update', 'بروزرسانی تنخواه'),
            ('Tankhah_view', 'نمایش تنخواه'),
            ('Tankhah_delete', 'حذف تنخواه'),

            ('Tankhah_part_approve', '👍تأیید رئیس قسمت'),
            ('Tankhah_approve', '👍تأیید مدیر مجموعه'),
            ('Tankhah_hq_view', 'رصد دفتر مرکزی'),
            ('Tankhah_hq_approve', '👍تأیید رده بالا در دفتر مرکزی'),

            ('Tankhah_HQ_OPS_PENDING', _('در حال بررسی - بهره‌برداری')),
            ('Tankhah_HQ_OPS_APPROVED', _('👍تأییدشده - بهره‌برداری')),
            ('Tankhah_HQ_FIN_PENDING', _('در حال بررسی - مالی')),
            ('Tankhah_PAID', _('پرداخت‌شده')),
            ('Tankhah_REJECTED', _('ردشده')),
            ("FactorItem_approve", "👍تایید/رد ردیف فاکتور (تایید ردیف فاکتور*استفاده در مراحل تایید*)"),
            ('edit_full_tankhah','👍😊تغییرات کاربری در فاکتور /تایید یا رد ردیف ها '),

            ('Dashboard_Core_view', 'دسترسی به داشبورد Core پایه'),
            ('DashboardView_flows_view', 'دسترسی به روند تنخواه گردانی'),
            ('Dashboard__view', 'دسترسی به داشبورد اصلی 💻'),

            ('Dashboard_Stats_view', 'دسترسی به آمار کلی داشبورد💲'),

        ]

def factor_document_upload_path(instance, filename):
    """
    مسیر آپلود فایل برای FactorDocument را بر اساس شماره تنخواه و ID فاکتور تعیین می‌کند.
    مسیر نهایی: factors/[شماره_تنخواه]/[ID_فاکتور]/[نام_فایل_اصلی]
    """
    # instance در اینجا یک شیء FactorDocument است
    factor = instance.factor
    if factor and factor.tankhah:
        tankhah_number = factor.tankhah.number
        factor_id = factor.id
        # برای جلوگیری از ذخیره شدن همه فایل‌ها با نام یکسان اگر چند فایل همزمان آپلود شوند،
        # بهتر است نام فایل اصلی را نگه داریم یا یک نام یکتا بسازیم.
        # filename = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}" # مثال: ساخت نام یکتا
        return f'factors/{tankhah_number}/{factor_id}/{filename}'
    else:
        # یک مسیر پیش‌فرض در صورتی که فاکتور یا تنخواه هنوز ذخیره نشده باشند (که نباید اتفاق بیفتد)
        # یا فاکتور به تنخواه لینک نباشد
        return f'factors/orphaned/{filename}'

class FactorDocument(models.Model):
    factor = models.ForeignKey('Factor', on_delete=models.CASCADE, related_name='documents', verbose_name=_("فاکتور"))
    # file = models.FileField(upload_to='factors/documents/%Y/%m/%d/', verbose_name=_("فایل پیوست"))
    file = models.FileField(upload_to=factor_document_upload_path, verbose_name=_("فایل پیوست"))
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
    tankhah = models.ForeignKey(Tankhah, on_delete=models.PROTECT, related_name='factors', verbose_name=_("تنخواه"))
    date = models.DateField(default=timezone.now, verbose_name=_("تاریخ"))
    amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_('مبلغ فاکتور'), default=0)  # فرض بر وجود فیلد مبلغ
    description = models.TextField(verbose_name=_("توضیحات"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))
    approved_by = models.ManyToManyField(CustomUser, blank=True, verbose_name=_("تأییدکنندگان"))

    is_finalized = models.BooleanField(default=False, verbose_name=_("نهایی شده"))
    locked = models.BooleanField(default=False, verbose_name="قفل شده")
    locked_by_stage = models.ForeignKey(WorkflowStage, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("قفل شده توسط مرحله"))


    def generate_number(self):
        """تولید شماره فاکتور با جداکننده قابل تنظیم"""
        sep = NUMBER_SEPARATOR
        serial = self.tankhah.factors.count() + 1
        return f"{self.tankhah.number}{sep}F{serial}"

    def save(self, *args, **kwargs):
        if not self.number:
            sep = "-"
            serial = self.tankhah.factors.count() + 1
            # self.number = f"{self.tanbakh.number}{sep}F{serial}"
            self.number = self.generate_number()
        super().save(*args, **kwargs)

    def total_amount(self):
        sum_Factor=sum(item.amount for item in self.items.all()) if self.items.exists() else 0
        logging.info(f'sum_factor is {sum_Factor}')
        return sum_Factor

    def __str__(self):
        return f"{self.number} ({self.tankhah.number})"

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
        ('PAID', 'پرداخت شده'),
    )
    factor = models.ForeignKey(Factor, on_delete=models.CASCADE, related_name='items', verbose_name=_("فاکتور"))
    description = models.CharField(max_length=255, verbose_name=_("شرح ردیف"))
    amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ") )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))
    quantity = models.DecimalField(max_digits=25, default=1,decimal_places=2, verbose_name=_("تعداد"))
    # quantity = models.IntegerField(default=1, verbose_name=_("تعداد"))
    unit_price = models.DecimalField(max_digits=25,default=1, decimal_places=1, verbose_name=_("قیمت واحد"))
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("دسته‌بندی"))


    def save(self, *args, **kwargs):
        if not self.amount:  # اگه amount وارد نشده باشه، محاسبه کن
            self.amount = self.unit_price * self.quantity
        # self.amount = self.unit_price * self.quantity
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
    ACTION_CHOICES = [
        ('APPROVE', 'تأیید'),
        ('REJECT', 'رد'),
        ('STAGE_CHANGE', 'تغییر مرحله'),
        ('NONE', 'هیچکدام'),
    ]
    tankhah  = models.ForeignKey(Tankhah, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("تنخواه"))
    factor = models.ForeignKey(Factor, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("فاکتور"))
    factor_item = models.ForeignKey(FactorItem, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("ردیف فاکتور"))
    action = models.CharField(max_length=25, choices=ACTION_CHOICES, verbose_name=_("اقدام"))
    stage = models.ForeignKey(WorkflowStage, on_delete=models.PROTECT, verbose_name=_('مرحله'))
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name=_("کاربر"))
    comment = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان"))
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    post = models.ForeignKey(Post, on_delete=models.SET_NULL, null=True, verbose_name=_("پست تأییدکننده"))
    changed_field = models.CharField(max_length=50, blank=True, null=True, verbose_name="فیلد تغییر یافته")

    seen_by_higher = models.BooleanField(default=False, verbose_name=_("دیده‌شده توسط رده بالاتر"))
    seen_at = models.DateTimeField(null=True, blank=True, verbose_name=_("زمان دیده شدن"))


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
        unique_together = ('post', 'stage')
        default_permissions=()
        permissions = [
            ('stageapprover__view','نمایش تأییدکننده مرحله'),
            ('stageapprover__add','افزودن تأییدکننده مرحله'),
            ('stageapprover__Update','بروزرسانی تأییدکننده مرحله'),
            ('stageapprover__delete','حــذف تأییدکننده مرحله'),
        ]

class TankhahFinalApproval(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('TankhahFinalApproval_view','دسترسی تایید یا رد تنخواه گردان ')
        ]

class DashboardView(TemplateView):
    template_name = 'tankhah/calc_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # تنخواه‌های در انتظار در هر مرحله
        stages = WorkflowStage.objects.all()
        for stage in stages:
            context[f'tankhah_pending_{stage.name}'] = Tankhah.objects.filter(
                current_stage=stage, status='PENDING'
            ).count()

        # تنخواه‌های نزدیک به مهلت
        context['tankhah_due_soon'] = Tankhah.objects.filter(
            due_date__lte=timezone.now() + timezone.timedelta(days=7),
            status='PENDING'
        ).count()

        # مجموع مبلغ تأییدشده در ماه جاری
        current_month = timezone.now().month
        context['total_approved_this_month'] = Tankhah.objects.filter(
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

class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="کاربر")
    message = models.TextField(verbose_name="پیام")
    tankhah = models.ForeignKey('Tankhah', on_delete=models.CASCADE, null=True, verbose_name="تنخواه")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده")

    class Meta:
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان‌ها"

    def __str__(self):
        return f"{self.user.username} - {self.message[:50]}"