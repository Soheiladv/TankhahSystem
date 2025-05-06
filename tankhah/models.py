import os
from decimal import Decimal
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum, Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from accounts.models import CustomUser
from budgets.budget_calculations import get_subproject_remaining_budget, get_project_remaining_budget, \
    get_factor_remaining_budget, get_tankhah_remaining_budget
import logging

from budgets.models import TransactionType, BudgetTransaction, BudgetHistory, BudgetAllocation
from core.models import WorkflowStage, Post

logger = logging.getLogger(__name__)

NUMBER_SEPARATOR = getattr(settings, 'NUMBER_SEPARATOR', '-')

def get_default_workflow_stage():

    from core.models import WorkflowStage  # اگر در همان اپلیکیشن است
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
    # project = models.ForeignKey('core.Project', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('پروژه'))
    project = models.ForeignKey('core.Project', on_delete=models.SET_NULL, null=True, blank=True, related_name='tankhah_set', verbose_name=_('پروژه'))
    project_budget_allocation = models.ForeignKey('budgets.ProjectBudgetAllocation', on_delete=models.CASCADE,
                                                  related_name='tankhahs', verbose_name=_("تخصیص بودجه پروژه"),
                                                  null=True, blank=True)
    subproject = models.ForeignKey('core.SubProject', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("زیر مجموعه پروژه"))
    letter_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شماره نامه"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, related_name='tankhah_created', verbose_name=_("ایجادکننده"))
    approved_by = models.ManyToManyField('accounts.CustomUser', blank=True, verbose_name=_('تأییدکنندگان'))
    description = models.TextField(verbose_name=_("توضیحات"))
    current_stage = models.ForeignKey('core.WorkflowStage', on_delete=models.SET_NULL, null=True,
                                      default=get_default_workflow_stage, verbose_name="مرحله فعلی")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,  default='DRAFT', verbose_name=_("وضعیت"))
    hq_status = models.CharField(max_length=20, default='PENDING',
                                 choices=STATUS_CHOICES, null=True, blank=True,
                                 verbose_name=_("وضعیت در HQ"))
    last_stopped_post = models.ForeignKey('core.Post', null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("آخرین پست متوقف‌شده"))

    is_archived = models.BooleanField(default=False, verbose_name=_("آرشیو شده"))

    payment_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شماره پرداخت"))
    is_locked = models.BooleanField(default=False, verbose_name=_("قفل شده"))
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان آرشیو")
    canceled = models.BooleanField(default=False, verbose_name="لغو شده")
    remaining_budget = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_("بودجه باقیمانده"))

    budget_allocation = models.ForeignKey('budgets.BudgetAllocation', on_delete=models.SET_NULL, null=True,
                                          verbose_name=_("تخصیص بودجه"))
    is_emergency = models.BooleanField(default=False, verbose_name=_("اضطراری"))
    """توضیح: لینک به BudgetAllocation برای مصرف بودجه و اضافه شدن is_emergency."""
    request_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ درخواست"))

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

    def clean(self):
        """اعتبارسنجی تنخواه"""
        super().clean()

        if self.amount <= 0:
            raise ValidationError(_("مبلغ تنخواه باید مثبت باشد."))
        if self.subproject and self.subproject.project != self.project:
            raise ValidationError(_("زیرپروژه باید متعلق به پروژه انتخاب‌شده باشد."))

        remaining = self.get_remaining_budget()
        if self.amount > remaining:
            raise ValidationError(
                _(f"مبلغ تنخواه ({self.amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده ({remaining:,.0f} ریال) است.")
            )
            # حذف اعتبارسنجی سخت‌گیرانه budget_allocation اگر اختیاری است
        if not self.budget_allocation and not self.project_budget_allocation:
            logger.warning("Neither budget_allocation nor project_budget_allocation is set.")
            raise ValidationError({"budget_allocation": _("حداقل یکی از تخصیص‌های بودجه باید تنظیم شود.")})

        if self.subproject and self.subproject.project != self.project:
            raise ValidationError(_("زیرپروژه باید متعلق به پروژه انتخاب‌شده باشد."))

        if not self.budget_allocation:
            logger.warning("budget_allocation مقدار ندارد. این ممکن است باعث مشکلاتی در مراحل بعدی شود.")
            # اگر نمی‌خواهید این فیلد اجباری باشد، خطا اضافه نکنید
            # اگر اجباری است، خطا اضافه کنید:
            raise ValidationError({"budget_allocation": _("این فیلد نمی‌تواند خالی باشد.")})

    def get_remaining_budget(self):
            """محاسبه بودجه باقی‌مانده برای تنخواه"""
            if self.project_budget_allocation:
                return self.project_budget_allocation.get_remaining_amount()
            elif self.budget_allocation:
                return self.budget_allocation.get_remaining_amount()
            elif self.subproject:
                return get_subproject_remaining_budget(self.subproject)
            return Decimal('0')

    # def save(self, *args, **kwargs):
    #     with transaction.atomic():
    #         if not self.number:
    #             self.number = self.generate_number()
    #
    #         self.full_clean()
    #
    #     # ثبت تراکنش در صورت ایجاد یا تغییر وضعیت
    #     # اگه وضعیت COMPLETED یا PAID باشه، قفل کن
    #     if self.status in ['APPROVED', 'REJECTED', 'PAID'] and not self.is_locked:
    #         self.project_budget_allocation.budget_allocation.send_notification(
    #             self.status.lower(),
    #             f"تنخواه {self.number} به وضعیت {self.get_status_display()} تغییر کرد."
    #         )
    #         self.is_locked = True
    #     from budgets.models import ProjectBudgetAllocation
    #
    #     if not self.pk:  # فقط موقع ایجاد
    #         # پیدا کردن تخصیص بودجه پروژه/زیرپروژه
    #         if self.subproject:
    #             allocation = ProjectBudgetAllocation.objects.filter(
    #                 budget_allocation=self.budget_allocation,
    #                 subproject=self.subproject
    #             ).first()
    #             allocation = allocation.remaining_amount if allocation else self.subproject.get_remaining_budget()
    #         elif self.project:
    #             allocation = ProjectBudgetAllocation.objects.filter(
    #                 budget_allocation=self.budget_allocation,
    #                 project=self.project,
    #                 subproject__isnull=True
    #             ).first()
    #             allocation = allocation.remaining_amount if allocation else self.project.get_remaining_budget()
    #         else:
    #             raise ValueError("تنخواه باید به پروژه یا ساب‌پروژه وصل باشد.")
    #
    #         # ثبت تراکنش مصرف بودجه
    #         # allocation = self.project_budget_allocation
    #         # if not allocation:
    #         #     allocation = ProjectBudgetAllocation.objects.filter(
    #         #         budget_allocation=self.budget_allocation,
    #         #         project=self.project,
    #         #         subproject=self.subproject
    #         #     ).first()
    #         # if not allocation:
    #         #     raise ValidationError(_("تخصیص بودجه معتبر برای این پروژه/زیرپروژه یافت نشد."))
    #
    #         if self.amount > allocation.remaining_amount:
    #             raise ValidationError(
    #                 _(f"مبلغ تنخواه ({self.amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده تخصیص ({allocation.remaining_amount:,.0f} ریال) است.")
    #             )
    #
    #         # if not self.pk:  # ایجاد تنخواه جدید
    #         #     self.project_budget_allocation = allocation
    #         #     allocation.remaining_amount -= self.amount
    #         #     allocation.save()
    #         #
    #         #     BudgetTransaction.objects.create(
    #         #         allocation=self.budget_allocation,
    #         #         transaction_type='CONSUMPTION',
    #         #         amount=self.amount,
    #         #         related_tankhah=self,
    #         #         created_by=self.created_by,
    #         #         description=f"مصرف بودجه توسط تنخواه {self.number}",
    #         #         transaction_id=f"TX-TNK-{self.number}"
    #         #     )
    #
    #         # به‌روزرسانی بودجه در صورت تغییر وضعیت
    #         if self.status == 'PAID':
    #             self.is_locked = True
    #             self.budget_allocation.send_notification(
    #                 'paid',
    #                 f"تنخواه {self.number} پرداخت شد."
    #             )
    #         elif self.status == 'REJECTED' and self.is_locked:
    #             # بازگشت بودجه در صورت رد شدن
    #             allocation.remaining_amount += self.amount
    #             allocation.save()
    #             BudgetTransaction.objects.create(
    #                 allocation=self.budget_allocation,
    #                 transaction_type='RETURN',
    #                 amount=self.amount,
    #                 related_tankhah=self,
    #                 created_by=self.created_by,
    #                 description=f"بازگشت بودجه به دلیل رد تنخواه {self.number}",
    #                 transaction_id=f"TX-TNK-RET-{self.number}"
    #             )
    #             self.is_locked = False
    #
    #     super().save(*args, **kwargs)
    def save(self, *args, **kwargs):
        from budgets.models import ProjectBudgetAllocation
        with transaction.atomic():
            if not self.number:
                self.number = self.generate_number()
            self.full_clean()

            # دریافت تخصیص بودجه
            allocation = self.project_budget_allocation or ProjectBudgetAllocation.objects.filter(
                budget_allocation=self.budget_allocation,
                project=self.project,
                subproject=self.subproject
            ).first()
            if not allocation:
                raise ValidationError(_("تخصیص بودجه معتبر برای این پروژه/زیرپروژه یافت نشد."))


            # ثبت تراکنش در صورت ایجاد یا تغییر وضعیت
            if self.status in ['APPROVED', 'REJECTED', 'PAID'] and not self.is_locked:
                if self.budget_allocation:  # چک کردن وجود budget_allocation
                    print('  چک کردن وجود budget_allocation')
                    self.budget_allocation.send_notification(
                        self.status.lower(),
                        f"تنخواه {self.number} به وضعیت {self.get_status_display()} تغییر کرد."
                    )
                self.is_locked = True


            if not self.pk:  # فقط موقع ایجاد
                # پیدا کردن تخصیص بودجه پروژه/زیرپروژه
                if self.subproject:
                    allocation = ProjectBudgetAllocation.objects.filter(
                        budget_allocation=self.budget_allocation if self.budget_allocation else None,
                        subproject=self.subproject
                    ).first()
                    remaining = allocation.remaining_amount if allocation else self.subproject.get_remaining_budget()
                elif self.project:
                    allocation = ProjectBudgetAllocation.objects.filter(
                        budget_allocation=self.budget_allocation if self.budget_allocation else None,
                        project=self.project,
                        subproject__isnull=True
                    ).first()
                    remaining = allocation.remaining_amount if allocation else self.project.get_remaining_budget()
                else:
                    raise ValueError("تنخواه باید به پروژه یا ساب‌پروژه وصل باشد.")

                if self.amount > remaining:
                    raise ValidationError(
                        _(f"مبلغ تنخواه ({self.amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده تخصیص ({remaining:,.0f} ریال) است.")
                    )

            # به‌روزرسانی بودجه در صورت تغییر وضعیت
            if self.status == 'PAID':
                self.is_locked = True
                if self.budget_allocation:  # چک کردن وجود budget_allocation
                    self.budget_allocation.send_notification(
                        'paid',
                        f"تنخواه {self.number} پرداخت شد."
                    )
            elif self.status == 'REJECTED' and self.is_locked:
                # بازگشت بودجه در صورت رد شدن
                if allocation and self.budget_allocation:
                    allocation.remaining_amount += self.amount
                    allocation.save()
                    from budgets.models import BudgetTransaction
                    BudgetTransaction.objects.create(
                        allocation=self.budget_allocation,
                        transaction_type='RETURN',
                        amount=self.amount,
                        related_tankhah=self,
                        created_by=self.created_by,
                        description=f"بازگشت بودجه به دلیل رد تنخواه {self.number}",
                        transaction_id=f"TX-TNK-RET-{self.number}"
                    )
                self.is_locked = False

        super().save(*args, **kwargs)


    def __str__(self):
        project_str = self.project.name if self.project else 'بدون پروژه'
        subproject_str = f" ({self.subproject.name})" if self.subproject else ''
        return f"{self.number} - {project_str}{subproject_str} - {self.amount:,.0f} ({self.get_status_display()})"

    class Meta:
        verbose_name = _("تنخواه")
        verbose_name_plural = _("تنخواه‌ها")
        indexes = [
            models.Index(fields=['number', 'date', 'status' ,'organization'])]
        default_permissions =()
        permissions = [
            ('Tankhah_add', _(' + افزودن تنخواه')),
            ('Tankhah_view', _('نمایش تنخواه')),
            ('Tankhah_update', _('🆙بروزرسانی تنخواه')),
            ('Tankhah_delete', _('⛔حذف تنخواه')),
            ('Tankhah_approve', _('👍تأیید تنخواه')),
            ('Tankhah_reject', _('رد تنخواه👎')),

            ('Tankhah_part_approve', '👍تأیید رئیس قسمت'),

            ('Tankhah_hq_view', 'رصد دفتر مرکزی'),
            ('Tankhah_hq_approve', '👍تأیید رده بالا در دفتر مرکزی'),

            ('Tankhah_HQ_OPS_PENDING', _('در حال بررسی - بهره‌برداری')),
            ('Tankhah_HQ_OPS_APPROVED', _('👍تأییدشده - بهره‌برداری')),
            ('Tankhah_HQ_FIN_PENDING', _('در حال بررسی - مالی')),
            ('Tankhah_PAID', _('پرداخت‌شده')),

            ("FactorItem_approve", "👍تایید/رد ردیف فاکتور (تایید ردیف فاکتور*استفاده در مراحل تایید*)"),
            ('edit_full_tankhah','👍😊تغییرات کاربری در فاکتور /تایید یا رد ردیف ها '),

            ('Dashboard_Core_view', 'دسترسی به داشبورد Core پایه'),
            ('DashboardView_flows_view', 'دسترسی به روند تنخواه گردانی'),
            ('Dashboard__view', 'دسترسی به داشبورد اصلی 💻'),

            ('Dashboard_Stats_view', 'دسترسی به آمار کلی داشبورد💲'),
        ]
 #-------- فرمت نمایشی خاص
    def get_project_total_budget_display(self):
        return f"{self.project_total_budget:,.0f}" if hasattr(self,
                                                              'project_total_budget') and self.project_total_budget else '-'

    def get_project_remaining_budget_display(self):
        return f"{self.project_remaining_budget:,.0f}" if hasattr(self,
                                                                  'project_remaining_budget') and self.project_remaining_budget else '-'

    def get_branch_total_budget_display(self):
        return f"{self.branch_total_budget:,.0f}" if hasattr(self,
                                                             'branch_total_budget') and self.branch_total_budget else '-'

    def get_tankhah_used_budget_display(self):
        return f"{self.tankhah_used_budget:,.0f}" if hasattr(self,
                                                             'tankhah_used_budget') and self.tankhah_used_budget else '-'

    def get_factor_used_budget_display(self):
        return f"{self.factor_used_budget:,.0f}" if hasattr(self, 'factor_used_budget') and self.factor_used_budget else '-'
class TankhActionType(models.Model):
    action_type = models.CharField(max_length=25, verbose_name=_('انواع  اقدام'))
    class Meta:
        verbose_name=_('انواع اقدام')
        verbose_name_plural =  _('انواع اقدام ')
        default_permissions = ()
        permissions = [
            ('TankhActionType_add','افزودن نوع اقدام'),
            ('TankhActionType_view','نمایش نوع اقدام'),
            ('TankhActionType_update','ویرایش نوع اقدام'),
            ('TankhActionType_delete','حذف نوع اقدام'),
        ]
    def __str__(self):
        return self.action_type
class TankhahAction(models.Model):
    # ACTION_TYPES = (
    #     ('ISSUE_PAYMENT_ORDER', _('صدور دستور پرداخت')),
    #     ('FINALIZE', _('اتمام')),
    #     ('INSURANCE', _('ثبت بیمه')),
    #     ('CUSTOM', _('سفارشی')),
    # )

    tankhah = models.ForeignKey(Tankhah, on_delete=models.CASCADE, related_name='actions', verbose_name=_("تنخواه"))
    action_type = models.CharField(max_length=50, choices=TankhActionType, verbose_name=_("نوع اقدام"))
    amount = models.DecimalField(max_digits=25, decimal_places=2, null=True, blank=True, verbose_name=_("مبلغ (برای پرداخت)"))
    stage = models.ForeignKey( WorkflowStage , on_delete=models.PROTECT, verbose_name=_("مرحله"))
    post = models.ForeignKey(  Post , on_delete=models.SET_NULL, null=True, verbose_name=_("پست انجام‌دهنده"))
    user = models.ForeignKey( CustomUser , on_delete=models.SET_NULL, null=True, verbose_name=_("کاربر"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    reference_number = models.CharField(max_length=50, blank=True, verbose_name=_("شماره مرجع"))

    action_type = models.ForeignKey( TransactionType , on_delete=models.SET_NULL, null=True,
                                    verbose_name=_("نوع اقدام"))
    # جایگزینی ACTION_TYPES با TransactionType


    def save(self, *args, **kwargs):
        # چک کن که پست مجاز به این اقدام باشه
        from core.models import PostAction
        if not PostAction.objects.filter(
            post=self.post, stage=self.stage, action_type=self.action_type
        ).exists():
            raise ValueError(f"پست {self.post} مجاز به {self.action_type} در این مرحله نیست")
        # برای دستور پرداخت، چک کن بودجه
        if self.action_type == 'ISSUE_PAYMENT_ORDER' and self.amount:
            if self.amount > self.tankhah.remaining_budget:
                raise ValueError("مبلغ دستور پرداخت بیشتر از بودجه باقیمانده است")
            self.tankhah.remaining_budget -= self.amount
            self.tankhah.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.action_type} برای {self.tankhah} ({self.created_at})"

    class Meta:
        verbose_name = _("اقدام تنخواه")
        verbose_name_plural = _("اقدامات تنخواه")
        permissions = [
            ('TankhahAction_view', 'نمایش اقدامات تنخواه'),
            ('TankhahAction_add', 'افزودن اقدامات تنخواه'),
            ('TankhahAction_update', 'بروزرسانی اقدامات تنخواه'),
            ('TankhahAction_delete', 'حذف اقدامات تنخواه'),
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
    uploaded_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, verbose_name=_("آپلود شده توسط"))

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
    STATUS_CHOICES = (
        ('DRAFT', _('پیش‌نویس')),
        ('PENDING', _('در انتظار تأیید')),
        ('APPROVED', _('تأیید شده')),
        ('REJECTED', _('رد شده')),
        ('PAID', _('پرداخت شده')),
    )

    number = models.CharField(max_length=60, blank=True, verbose_name=_("شماره فاکتور"))
    tankhah = models.ForeignKey('Tankhah', on_delete=models.PROTECT, related_name='factors', verbose_name=_("تنخواه"))
    date = models.DateField(default=timezone.now, verbose_name=_("تاریخ"))
    amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_('مبلغ فاکتور'), default=0)
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))
    approved_by = models.ManyToManyField(CustomUser, blank=True, verbose_name=_("تأییدکنندگان"))
    is_finalized = models.BooleanField(default=False, verbose_name=_("نهایی شده"))
    locked = models.BooleanField(default=False, verbose_name="قفل شده")
    locked_by_stage = models.ForeignKey(WorkflowStage, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("قفل شده توسط مرحله"))
    budget = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name=_("بودجه تخصیصی"))
    remaining_budget = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name=_("بودجه باقیمانده"))
    created_by = models.ForeignKey('accounts.CustomUser',related_name='CustomUser_related', on_delete=models.SET_NULL, null=True, verbose_name=_("ایجادکننده"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    is_emergency = models.BooleanField(default=False, verbose_name=_("اضطراری"))
    category = models.ForeignKey('ItemCategory', on_delete=models.SET_NULL, null=True, blank=False, verbose_name=_("دسته‌بندی"))

    def get_remaining_budget(self):
        return get_factor_remaining_budget(self)

    def get_items_total(self):
        if self.pk:
            total = self.items.aggregate(total=Sum('amount'))['total'] or Decimal('0')
            return total
        return Decimal('0')

    def total_amount(self):
        if self.pk:
            return self.get_items_total()
        return Decimal('0')
    #
    # def generate_number(self):
    #     from jdatetime import date as jdate
    #     date_str = jdate.fromgregorian(date=self.date).strftime('%Y%m%d')
    #     serial = Factor.objects.filter(date=self.date).count() + 1
    #     return f"FAC-{self.tankhah.number}-{date_str}-{serial:03d}"
    def generate_number(self):
        """تولید شماره یکتا برای فاکتور با استفاده از تاریخ شمسی"""
        sep = '-'  # استفاده از جداکننده ثابت
        from jdatetime import date as jdate
        date_str = jdate.fromgregorian(date=self.date).strftime('%Y%m%d')
        org_code = self.tankhah.organization.code if self.tankhah and self.tankhah.organization else 'NOORG'
        tankhah_number = self.tankhah.number if self.tankhah else 'NOTNKH'

        with transaction.atomic():
            max_serial = Factor.objects.filter(
                tankhah__organization=self.tankhah.organization,
                date=self.date
            ).aggregate(models.Max('number'))['number__max']

            serial = 1
            if max_serial:
                last_number = max_serial.split(sep)[-1]
                try:
                    serial = int(last_number) + 1
                except ValueError:
                    pass

            new_number = f"FAC{sep}{tankhah_number}{sep}{date_str}{sep}{org_code}{sep}{serial:04d}"
            while Factor.objects.filter(number=new_number).exists():
                serial += 1
                new_number = f"FAC{sep}{tankhah_number}{sep}{date_str}{sep}{org_code}{sep}{serial:04d}"
            return new_number

    def clean(self):
        super().clean()
        if self.amount < 0:
            raise ValidationError(_("مبلغ فاکتور نمی‌تواند منفی باشد."))
        if not self.category:
            raise ValidationError(_("دسته‌بندی الزامی است."))
        if self.tankhah and (
                self.tankhah.status not in ['DRAFT', 'PENDING'] ): #or not self.tankhah.workflow_stage.is_initial
            raise ValidationError(_("تنخواه انتخاب‌شده در وضعیت یا مرحله مجاز نیست."))

        #
        # total = self.total_amount()
        # errors = {}
        # if self.pk and total <= 0:
        #     raise ValidationError(_("مبلغ فاکتور باید مثبت باشد."))
        #
        # if abs(self.amount - total) > 0.01:
        #     logger.warning(f"Factor {self.number}: amount ({self.amount}) != items total ({total})")
        #     raise ValidationError(_("مبلغ فاکتور با مجموع آیتم‌ها همخوانی ندارد."))
        #
        # if self.tankhah:
        #     tankhah_remaining = get_tankhah_remaining_budget(self.tankhah)
        #     if total > tankhah_remaining:
        #         raise ValidationError(
        #             _(f"مبلغ فاکتور ({total:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده تنخواه ({tankhah_remaining:,.0f} ریال) باشد.")
        #         )
        #
        # if not self.category:
        #     errors['category'] = ValidationError(_('دسته‌بندی الزامی است.'), code='category_required')
        # if errors:
        #     raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """ذخیره فاکتور با مدیریت تراکنش‌ها، اعلان‌ها و تاریخچه تغییرات"""
        from budgets.models import BudgetTransaction
        with transaction.atomic():
            if not self.number:
                self.number = self.generate_number()

            # فقط در صورت نیاز به اعتبارسنجی خاص مدل، clean را فراخوانی کنید
            original = None
            if self.pk:
                original = Factor.objects.get(pk=self.pk)

            # به‌روزرسانی بودجه و وضعیت قفل
            if original and self.status != original.status:
                if self.status == 'PAID' and not self.is_locked:
                    create_budget_transaction(
                        allocation=self.tankhah.budget_allocation,
                        transaction_type='CONSUMPTION',
                        amount=self.amount,  # استفاده از self.amount به جای total_amount()
                        related_obj=self,
                        created_by=self.created_by,
                        description=f"مصرف بودجه توسط فاکتور {self.number}",
                        transaction_id=f"TX-FAC-{self.number}"
                    )
                    self.is_locked = True
                    Notification.objects.create(
                        user=self.created_by,
                        message=f"فاکتور {self.number} پرداخت شد.",
                        tankhah=self.tankhah
                    )
                elif self.status == 'REJECTED' and original.status in ['APPROVED', 'PAID'] and self.is_locked:
                    create_budget_transaction(
                        allocation=self.tankhah.budget_allocation,
                        transaction_type='RETURN',
                        amount=self.amount,
                        related_obj=self,
                        created_by=self.created_by,
                        description=f"بازگشت بودجه به دلیل رد فاکتور {self.number}",
                        transaction_id=f"TX-FAC-RET-{self.number}"
                    )
                    self.is_locked = False
                    Notification.objects.create(
                        user=self.created_by,
                        message=f"فاکتور {self.number} رد شد.",
                        tankhah=self.tankhah
                    )

            super().save(*args, **kwargs)
            # ثبت لاگ تأیید/رد
            if original and self.status != original.status:
                ApprovalLog.objects.create(
                    factor=self,
                    action='APPROVE' if self.status in ['APPROVED', 'PAID'] else 'REJECT',
                    stage=self.locked_by_stage or self.tankhah.current_stage,
                    user=self.created_by,
                    comment=f"تغییر وضعیت فاکتور به {self.get_status_display()}",
                    content_type=ContentType.objects.get_for_model(self),
                    object_id=self.pk
                )

            # ثبت تاریخچه تغییرات
            if original:
                changed_fields = []
                for field in self._meta.fields:
                    field_name = field.name
                    if getattr(original, field_name) != getattr(self, field_name):
                        changed_fields.append(field_name)
                if changed_fields:
                    ApprovalLog.objects.create(
                        factor=self,
                        action='STAGE_CHANGE',
                        stage=self.locked_by_stage or self.tankhah.current_stage,
                        user=self.created_by,
                        comment=f"تغییر فیلدهای {', '.join(changed_fields)}",
                        content_type=ContentType.objects.get_for_model(self),
                        object_id=self.pk,
                        changed_field=', '.join(changed_fields)
                    )



    def __str__(self):
        # اصلاح متد __str__ برای مدیریت tankhah=None
        tankhah_number = self.tankhah.number if self.tankhah else "تنخواه ندارد"
        return f"{self.number} ({tankhah_number})"

    class Meta:
        verbose_name = _("فاکتور")
        verbose_name_plural = _("فاکتورها")
        indexes = [
            models.Index(fields=['number', 'date', 'status', 'tankhah']),
        ]
        default_permissions = ()
        permissions = [
            ('factor_add', _('افزودن فاکتور')),
            ('factor_view', _('نمایش فاکتور')),
            ('factor_update', _('بروزرسانی فاکتور')),
            ('factor_delete', _('حذف فاکتور')),
            ('factor_approve', _('تأیید فاکتور')),
            ('factor_reject', _('رد فاکتور')),
            ('Factor_full_edit', _('دسترسی کامل به فاکتور')),
        ]
# --- تابع اصلاح شده ---
def create_budget_transaction(allocation, transaction_type, amount, related_obj, created_by, description,
                             transaction_id):
    """
    ایجاد تراکنش بودجه با اعتبارسنجی مبلغ و بدون ارسال فیلدهای مربوط به فاکتور/آیتم.

    Args:
        allocation (BudgetAllocation): تخصیص بودجه مرتبط.
        transaction_type (str): نوع تراکنش ('CONSUMPTION', 'RETURN', ...).
        amount (Decimal): مبلغ تراکنش.
        related_obj: شیء مرتبط (Tankhah, Factor, FactorItem) برای تعیین related_tankhah.
        created_by (CustomUser): کاربر ایجادکننده.
        description (str): توضیحات تراکنش.
        transaction_id (str): شناسه منحصربه‌فرد تراکنش.

    Raises:
        ValidationError: اگر مبلغ مصرف بیشتر از باقیمانده باشد یا مبلغ برگشتی نامعتبر باشد.
        Exception: برای سایر خطاهای دیتابیس یا پیش‌بینی نشده.
    """
    # Import models needed within the function
    from budgets.models import BudgetTransaction, BudgetHistory  # Adjust import path
    from tankhah.models import Tankhah, Factor, FactorItem  # Adjust import path

    # Validate input types (optional but good practice)
    if not hasattr(allocation, 'get_remaining_amount'):
        msg = "شیء 'allocation' ارسال شده متد get_remaining_amount را ندارد."
        logger.error(msg)
        raise TypeError(msg)
    if not isinstance(amount, Decimal):
        try:
            amount = Decimal(amount)
        except Exception:
            msg = f"مقدار 'amount' ({amount}) قابل تبدیل به Decimal نیست."
            logger.error(msg)
            raise TypeError(msg)

    try:
        with transaction.atomic():
            # 1. تعیین related_tankhah بر اساس related_obj
            related_tankhah = None
            if isinstance(related_obj, Tankhah):
                related_tankhah = related_obj
            elif isinstance(related_obj, Factor):
                related_tankhah = related_obj.tankhah
            elif isinstance(related_obj, FactorItem):
                related_tankhah = related_obj.factor.tankhah
            else:
                logger.warning(
                    f"Invalid related_obj type '{type(related_obj)}' for BudgetTransaction. related_tankhah will be NULL.")
                # Decide if you want to raise an error here instead
                # raise ValidationError(_("نوع شیء مرتبط برای تراکنش بودجه نامعتبر است."))

            # 2. اعتبارسنجی مبلغ تراکنش
            remaining = allocation.get_remaining_amount()  # Call the method
            logger.debug(
                f"create_budget_transaction check: allocation={allocation.pk}, remaining={remaining}, amount={amount}, type={transaction_type}")

            if transaction_type == 'CONSUMPTION':
                if amount <= Decimal('0'):
                    raise ValidationError(_("مبلغ مصرف باید مثبت باشد."))
                if amount > remaining:
                    logger.error(
                        f"Consumption amount {amount} exceeds remaining allocation {remaining} for allocation {allocation.pk}")
                    raise ValidationError(
                        _("مبلغ مصرف ({:,}) بیشتر از بودجه باقی‌مانده تخصیص ({:,}) است.").format(amount, remaining))

            elif transaction_type == 'RETURN':
                if amount <= Decimal('0'):
                    raise ValidationError(_("مبلغ برگشتی باید مثبت باشد."))
                # Calculate net consumed to validate return amount ceiling
                if hasattr(allocation, 'get_consumed_amount') and hasattr(allocation, 'get_returned_amount'):
                    consumed = allocation.get_consumed_amount()
                    returned_so_far = allocation.get_returned_amount()
                    net_consumed = consumed - returned_so_far
                    if amount > net_consumed:
                        logger.error(
                            f"Return amount {amount} exceeds net consumed {net_consumed} for allocation {allocation.pk}")
                        raise ValidationError(
                            _("مبلغ برگشتی ({:,}) نمی‌تواند بیشتر از مبلغ خالص مصرف شده ({:,}) باشد.").format(amount,
                                                                                                              net_consumed))
                else:
                    logger.warning(
                        f"Cannot validate RETURN amount ceiling for allocation {allocation.pk} due to missing methods.")

            # بررسی بودجه باقی‌مانده
            remaining = allocation.get_remaining_amount()
            if transaction_type == 'CONSUMPTION' and amount > remaining:
                logger.error(f"Insufficient budget: Amount {amount} exceeds remaining {remaining}")
                raise ValueError(f"مبلغ {amount} بیشتر از بودجه باقی‌مانده {remaining} است.")

            # تولید transaction_id اگر ارائه نشده باشد
            if not transaction_id:
                timestamp_str = timezone.now().strftime('%Y%m%d%H%M%S%f')
                transaction_id = f"TX-FACTOR-NEW-{transaction_type[:3]}-{allocation.id}-{timestamp_str}"
                logger.debug(f"Generated transaction_id: {transaction_id}")


            # 3. ایجاد تراکنش بودجه (بدون فیلدهای related_factor/related_factor_item)
            budget_transaction = BudgetTransaction.objects.create(
                allocation=allocation,
                transaction_type=transaction_type,
                amount=amount,
                related_tankhah=related_tankhah,  # فقط فیلدی که در مدل BudgetTransaction وجود دارد
                created_by=created_by,
                description=description,
                transaction_id=transaction_id  # اطمینان از ارسال شناسه یکتا
            )
            logger.info(
                f"BudgetTransaction created successfully: ID={budget_transaction.pk}, TxID={transaction_id}, amount={amount}, type={transaction_type}, allocation={allocation.pk}")

            # 4. (اختیاری) ثبت تاریخچه بودجه
            try:
                # ثبت تاریخچه بودجه
                history_transaction_id = f"HIST-{transaction_id}"

                BudgetHistory.objects.create(
                    content_type=ContentType.objects.get_for_model(allocation),
                    object_id=allocation.id,
                    action=transaction_type,
                    amount=amount,
                    created_by=created_by,
                    details=f"{transaction_type} {amount:,.0f} for allocation {allocation.id}: {description}",
                    transaction_id=history_transaction_id
                )
                logger.info(f"BudgetHistory recorded for transaction: {transaction_id}")
            except NameError:
                logger.warning("BudgetHistory model not found or not imported, skipping history recording.")
            except Exception as hist_exc:
                logger.error(f"Error recording BudgetHistory for transaction {transaction_id}: {hist_exc}",
                             exc_info=True)

            # 5. (مهم - اختیاری) آپدیت کردن فیلد باقیمانده در خود Allocation؟
            # اگر مدل BudgetAllocation فیلدی مثل 'remaining_amount' برای ذخیره باقیمانده دارد،
            # باید آن را اینجا آپدیت کنید تا با get_remaining_amount() هماهنگ باشد.
            # allocation.remaining_amount = remaining - amount # یا + amount برای RETURN
            # allocation.save(update_fields=['remaining_amount'])
            # logger.info(f"Updated remaining_amount on BudgetAllocation {allocation.pk}")

            # Return the created transaction object
            return budget_transaction

    except ValidationError as ve:
        # Log validation errors clearly
        error_message = str(ve.message_dict) if hasattr(ve, 'message_dict') else str(ve)
        logger.error(
            f"Validation Error creating BudgetTransaction: {error_message} (Allocation: {allocation.pk}, Amount: {amount}, Type: {transaction_type})",
            exc_info=False)  # exc_info=False for cleaner logs
        raise  # Re-raise to be handled by the caller (e.g., the view)
    except Exception as e:
        # Log other unexpected errors
        logger.error(
            f"Unexpected Error creating BudgetTransaction: {str(e)} (Allocation: {allocation.pk}, Amount: {amount}, Type: {transaction_type})",
            exc_info=True)
        raise  # Re-raise unexpected errors
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
    amount = models.DecimalField(max_digits=25, default=0, decimal_places=2, verbose_name=_("مبلغ"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))
    quantity = models.DecimalField(max_digits=25, default=1, decimal_places=2, verbose_name=_("تعداد"))
    unit_price = models.DecimalField(max_digits=25, decimal_places=2, blank=True, null=True,verbose_name=_("قیمت واحد"))
    min_stage_order = models.IntegerField(default=1, verbose_name=_("حداقل ترتیب مرحله"),help_text=_("این نوع تراکنش فقط در این مرحله یا بالاتر مجاز است")  , editable=False)
    # Optional: Timestamps for tracking
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان ایجاد"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("زمان آخرین ویرایش"))


    def clean(self):
        """
        Basic model-level validation. Avoid complex calculations here that rely
        on related models or states that might not be fully set yet.
        Focus on individual field constraints.
        """
        super().clean() # Call parent clean method first

        errors = {}

        # 1. Validate Quantity
        if self.quantity is not None and self.quantity <= Decimal('0'):
            errors['quantity'] = ValidationError(
                _('تعداد/مقدار باید بزرگ‌تر از صفر باشد.'), code='quantity_not_positive'
            )

        # 2. Validate Unit Price (if provided)
        if self.unit_price is not None and self.unit_price < Decimal('0'):
            # Allow zero unit price? Maybe. Disallow negative.
            errors['unit_price'] = ValidationError(
                _('قیمت واحد نمی‌تواند منفی باشد.'), code='unit_price_negative'
            )
            # Note: We don't raise 'unit_price must be positive' here,
            # because the final 'amount' validation in save() is more robust.

        # 3. Validate Amount (basic check for negative, final check in save)
        if self.amount is not None and self.amount < Decimal('0'):
             errors['amount'] = ValidationError(
                 _('مبلغ کل ردیف نمی‌تواند منفی باشد.'), code='amount_negative'
             )

        # Raise all collected errors at once
        if errors:
            raise ValidationError(errors)

        # Note: Comparison between amount, unit_price, and quantity is *not* done here
        # because self.amount might still hold its default value (0) before save calculates it.


    def save(self, *args, **kwargs):
        """ذخیره آیتم با محاسبه مبلغ و اعتبارسنجی ساده"""
        logger.debug(f"Starting FactorItem save for pk={self.pk}. Qty={self.quantity}, UnitPrice={self.unit_price}, Amount={self.amount}")

        # محاسبه مبلغ
        if self.unit_price is not None and self.quantity is not None:
            self.amount = self.quantity * self.unit_price
            logger.info(f"Calculated amount for FactorItem pk={self.pk}: {self.amount}")
        elif self.amount is None:
            logger.warning(f"Amount not provided and cannot be calculated for FactorItem pk={self.pk}")
            self.amount = Decimal('0')
         # اعتبارسنجی
        self.clean()

        # ذخیره
        super().save(*args, **kwargs)
        logger.info(f"FactorItem saved successfully (pk={self.pk}). Amount={self.amount}, Status={self.status}")



    def __str__(self):
        """String representation of the FactorItem."""
        # Format amount with commas for readability
        try:
            # Ensure amount is a Decimal before formatting
            amount_str = f"{self.amount:,.2f}" if isinstance(self.amount, Decimal) else str(self.amount)
        except (TypeError, ValueError):
            amount_str = str(self.amount) # Fallback if formatting fails

        return f"{self.description or _('بدون شرح')} - {amount_str}"

    class Meta:
        verbose_name = _("ردیف فاکتور")
        verbose_name_plural = _("ردیف‌های فاکتور")
        ordering = ['factor', 'pk'] # Order by parent factor, then by creation order (pk)
        indexes = [
            models.Index(fields=['factor', 'status']), # Index for common filtering
        ]
        # Using standard Django permissions unless specific needs arise
        # default_permissions = ('add', 'change', 'delete', 'view')
        default_permissions = () # Disable default if using custom perms exclusively
        permissions = [
            ('FactorItem_add', _('افزودن ردیف فاکتور')),
            ('FactorItem_update', _('ویرایش ردیف فاکتور')),
            ('FactorItem_view', _('نمایش ردیف فاکتور')),
            ('FactorItem_delete', _('حذف ردیف فاکتور')),
            # Add specific permissions for status changes if needed
            ('FactorItem_approve', _('تأیید ردیف فاکتور')),
            ('FactorItem_reject', _('رد ردیف فاکتور')),
        ]
#--------------
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
    stage = models.ForeignKey('core.WorkflowStage', on_delete=models.PROTECT, verbose_name=_('مرحله'))
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, verbose_name=_("کاربر"))
    comment = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان"))
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    post = models.ForeignKey('core.Post', on_delete=models.SET_NULL, null=True, verbose_name=_("پست تأییدکننده"))
    changed_field = models.CharField(max_length=50, blank=True, null=True, verbose_name="فیلد تغییر یافته")

    seen_by_higher = models.BooleanField(default=False, verbose_name=_("دیده‌شده توسط رده بالاتر"))
    seen_at = models.DateTimeField(null=True, blank=True, verbose_name=_("زمان دیده شدن"))

    action_type = models.CharField(max_length=50, blank=True, verbose_name=_("نوع اقدام"))

    # پشتیبانی از چندین نوع موجودیت با استفاده از GenericForeignKey
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_("نوع موجودیت"))
    object_id = models.PositiveIntegerField(verbose_name=_("شناسه موجودیت"))
    content_object = GenericForeignKey('content_type', 'object_id')


    # -- برای بودجه
    def save(self, *args, **kwargs):
        # چک کن که پست کاربر مجاز به این اقدام تو این مرحله باشه
        user_post = self.user.userpost_set.filter(end_date__isnull=True).first()
        if not user_post:
            raise ValueError("کاربر هیچ پست فعالی ندارد.")
        from core.models import PostAction
        if user_post and not PostAction.objects.filter(
                post=user_post.post,
                stage=self.stage,
                action_type=self.action,
                entity_type=self.content_type.model.upper(),
                is_active=True
        ).exists():
            raise ValueError(
                f"پست {user_post.post} مجاز به {self.action} در این مرحله برای {self.content_type.model} نیست")
        super().save(*args, **kwargs)

        # old
        # if user_post and self.action_type:
        #     if not PostAction.objects.filter(
        #         post=user_post.post, stage=self.stage, action_type=self.action_type
        #     ).exists():
        #         raise ValueError(f"پست {user_post.post} مجاز به {self.action_type} در این مرحله نیست")
        # super().save(*args, **kwargs)



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
"""
توضیح:
این مدل مشخص می‌کند کدام پست‌ها در یک مرحله خاص می‌توانند به‌عنوان تأییدکننده برای تنخواه یا بودجه عمل کنند.
فیلد entity_type مشابه PostAction اضافه شده تا نوع موجودیت مشخص شود.
"""
class StageApprover(models.Model):
    stage = models.ForeignKey('core.WorkflowStage', on_delete=models.CASCADE, verbose_name=_('مرحله'))
    post = models.ForeignKey( 'core.Post', on_delete=models.CASCADE, verbose_name=_('پست مجاز'))  # فرض بر وجود مدل Post
    is_active = models.BooleanField(default=True, verbose_name="وضعیت فعال")
    entity_type = models.CharField(
        max_length=50,
        choices=(('TANKHAH', _('تنخواه')), ('BUDGET_ALLOCATION', _('تخصیص بودجه'))),
        default='TANKHAH',
        verbose_name=_("نوع موجودیت")
    )
    def __str__(self):
        return f"{self.post} - تأییدکننده برای {self.get_entity_type_display()} در {self.stage}"
        # return f"{self.stage} - {self.post}"

    class Meta:
        verbose_name = _('تأییدکننده مرحله')
        verbose_name_plural = _('تأییدکنندگان مرحله')
        unique_together = ('stage', 'post', 'entity_type')
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
class ItemCategory(models.Model):
    """مقداردهی بر اساس دسته‌بندی (category):"""
    name = models.CharField(max_length=100, verbose_name=_("نام دسته‌بندی"))
    min_stage_order = models.IntegerField(default=1, verbose_name=_("حداقل ترتیب مرحله"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    def __str__(self):
        return self.name
    class Meta:
        verbose_name= "دسته بندی نوع هزینه کرد"
        verbose_name_plural= "دسته بندی نوع هزینه کرد"
        permissions = [
            ('ItemCategory_add','افزودن دسته بندی نوع هزینه کرد'),
            ('ItemCategory_update','ویرایش دسته بندی نوع هزینه کرد'),
            ('ItemCategory_view','نمایش دسته بندی نوع هزینه کرد'),
            ('ItemCategory_delete','حــذف دسته بندی نوع هزینه کرد'),
        ]
class Notification(models.Model):
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, verbose_name="کاربر")
    message = models.TextField(verbose_name="پیام")
    tankhah = models.ForeignKey('Tankhah', on_delete=models.CASCADE, null=True, verbose_name="تنخواه")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده")

    class Meta:
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان‌ها"

    def __str__(self):
        return f"{self.user.username} - {self.message[:50]}"

#---------------------- End Models ----------------------------------##########
class DashboardView(TemplateView):
    template_name = 'tankhah/calc_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # تنخواه‌های در انتظار در هر مرحله
        from core.models import WorkflowStage
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
        print(context['total_approved_this_month'])
        # آخرین فعالیت‌ها
        context['recent_approvals'] = ApprovalLog.objects.order_by('-timestamp')[:5]

        return context

class Dashboard_Tankhah(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('Dashboard_Tankhah_view','دسترسی به داشبورد تنخواه گردان ')
        ]

