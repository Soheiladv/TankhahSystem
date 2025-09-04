import os
from decimal import Decimal

from Demos.win32ts_logoff_disconnected import username
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum, Max, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from accounts.models import CustomUser
# from core.models import   Post, SystemSettings, AccessRule, UserPost, PostAction, Organization
# from core.models import PostAction, SystemSettings, AccessRule, Organization
from django.contrib.contenttypes.models import ContentType
import logging
logger = logging.getLogger('Tankhah_Models')
# from tankhah.constants import ACTION_TYPES, FACTOR_STATUSES

NUMBER_SEPARATOR = getattr(settings, 'NUMBER_SEPARATOR', '-')
#-----------------------------------------------
def get_default_workflow_stage():

    from core.models import AccessRule  # اگر در همان اپلیکیشن است
    try:
        return AccessRule.objects.get(name='HQ_INITIAL').id
    except AccessRule.DoesNotExist:
        # اگه پیدا نشد، اولین مرحله رو برگردون یا None
        stage = AccessRule.objects.order_by('order').first()
        return stage.id if stage else None
def tankhah_document_path(instance, filename):
    # مسیر آپلود: documents/شماره_تنخواه/نام_فایل
    extension = os.path.splitext(filename)[1]  # مثل .pdf
    return f'documents/{instance.tankhah.number}/document{extension}/%Y/%m/%d/'
# --- تابع اصلاح شده ---

#-----------------------------------------------
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

# --- تابع کمکی برای گرفتن وضعیت پیش‌فرض ---
def get_default_factor_status():
    from core.models import Status
    from django.core.exceptions import ImproperlyConfigured
    try:
        actor_status = Status.objects.get(code='DRAFT', is_initial=True)
        logger.debug(f"Default factor status found: {actor_status}")
        return actor_status
    except Status.DoesNotExist:
        raise ImproperlyConfigured("وضعیت اولیه 'DRAFT' در سیستم تعریف نشده است. لطفاً یک وضعیت با کد 'DRAFT' و is_initial=True در پنل ادمین ایجاد کنید.")
    except Status.MultipleObjectsReturned:
        raise ImproperlyConfigured("بیش از یک وضعیت اولیه با کد 'DRAFT' در سیستم تعریف شده است. لطفاً اطمینان حاصل کنید که تنها یک وضعیت با کد 'DRAFT' و is_initial=True وجود دارد.")
#-----------------------------------------------
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
    number = models.CharField(max_length=150, unique=True, blank=True, verbose_name=_("شماره تنخواه"))
    amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ"))
    date = models.DateTimeField(default=timezone.now, verbose_name=_("تاریخ")) #start_date
    due_date = models.DateTimeField(null=True, blank=True, verbose_name=_('مهلت زمانی')) # end_date
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, verbose_name=_('مجموعه/شعبه'))
    project = models.ForeignKey('core.Project', on_delete=models.SET_NULL, null=True, blank=True,related_name='tankhah_set', verbose_name=_('پروژه'))
    project_budget_allocation = models.ForeignKey( 'budgets.BudgetAllocation', on_delete=models.CASCADE, related_name='tankhahs',verbose_name=_("تخصیص بودجه پروژه"), null=True, blank=True)
    subproject = models.ForeignKey('core.SubProject', on_delete=models.CASCADE, null=True, blank=True,verbose_name=_("زیر مجموعه پروژه"))
    letter_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شماره نامه"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, related_name='tankhah_created', verbose_name=_("ایجادکننده"))
    approved_by = models.ManyToManyField('accounts.CustomUser', blank=True, verbose_name=_('تأییدکنندگان'))
    description = models.TextField(verbose_name=_("توضیحات"))
    # current_stage = models.ForeignKey('core.WorkflowStage', on_delete=models.SET_NULL, null=True, default=None,  verbose_name="مرحله فعلی")
    # فیلد جدید برای جایگزینی current_stage
    # current_stage = models.IntegerField(default=1, verbose_name=_("ترتیب مرحله"))

    # status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', verbose_name=_("وضعیت"))
    status = models.ForeignKey('core.Status', on_delete=models.SET_NULL, null=True, related_name='status_tankhah_set')
    # status = models.ForeignKey('core.Status',on_delete=models.PROTECT,null=True,  # اجازه می‌دهیم در ابتدا خالی باشد
    #     blank=True,        verbose_name=_("وضعیت")    )
    # hq_status = models.ForeignKey('core.Status',on_delete=models.PROTECT,null=True,  # اجازه می‌دهیم در ابتدا خالی باشد
    #     blank=True, verbose_name=_("وضعیت در HQ"))
    last_stopped_post = models.ForeignKey('core.Post', null=True, blank=True, on_delete=models.SET_NULL,   verbose_name=_("آخرین پست متوقف‌شده"))
    is_archived = models.BooleanField(default=False, verbose_name=_("آرشیو شده"))
    payment_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شماره پرداخت"))
    is_locked = models.BooleanField(default=False, verbose_name=_("قفل شده"))
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان آرشیو")
    canceled = models.BooleanField(default=False, verbose_name="لغو شده")
    remaining_budget = models.DecimalField(max_digits=25, decimal_places=2, default=0,          verbose_name=_("بودجه باقیمانده"))
    is_emergency = models.BooleanField(default=False, verbose_name=_("اضطراری"))
    request_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ درخواست"))
    payment_ceiling = models.DecimalField(max_digits=25, decimal_places=2, null=True, blank=True, verbose_name=_("سقف پرداخت"))
    is_payment_ceiling_enabled = models.BooleanField(default=False, verbose_name=_("فعال بودن سقف پرداخت"))

    # current_stage = models.ForeignKey('core.AccessRule',on_delete=models.SET_NULL,null=True,blank=True,  # اجازه می‌دهیم در ابتدا خالی باشد
    #     verbose_name=_("مرحله فعلی گردش کار")    )
    current_stage = models.ForeignKey('core.Status', on_delete=models.SET_NULL, null=True, blank=True,
                                      verbose_name=_("وضعیت فعلی گردش کار"))

    # @property
    # def current_stage(self):
    #     # مثلاً از AccessRule یا منطقی دیگر برای تعیین مرحله فعلی
    #     return AccessRule.objects.filter(
    #         entity_type='TANKHAH',
    #         stage_order=1  # فرض: مرحله اول
    #     ).first()

    class Meta:
        verbose_name = _("تنخواه")
        verbose_name_plural = _("تنخواه‌ها")
        indexes = [
            models.Index(fields=['number', 'date', 'status',
                                 'organization','number',
                                 'project_id', 'organization_id',
                                 'status', 'created_at']),
        ]
        default_permissions = ()
        permissions = [
            ('Tankhah_add', _(' + افزودن تنخواه')),
            ('Tankhah_view', _('نمایش تنخواه')),
            ('Tankhah_detail', _('نمایش تنخواه')),
            ('Tankhah_update', _('🆙بروزرسانی تنخواه')),
            ('Tankhah_delete', _('⛔حذف تنخواه')),
            ('Tankhah_approve', _('👍تأیید تنخواه')),
            ('Tankhah_reject', _('رد تنخواه👎')),
            ('Tankhah_view_all', _('مجوز تمامی سطوح را دارد HQ Full- نمایش همه تنخواه‌ها (دفتر مرکزی)')),

            ('Tankhah_part_approve', '👍تأیید رئیس قسمت'),

            ('Tankhah_hq_view', 'رصد دفتر مرکزی'),
            ('Tankhah_hq_approve', '👍تأیید رده بالا در دفتر مرکزی'),

            ('Tankhah_HQ_OPS_PENDING', _('در حال بررسی - بهره‌برداری')),
            ('Tankhah_HQ_OPS_APPROVED', _('👍تأییدشده - بهره‌برداری')),
            ('Tankhah_HQ_FIN_PENDING', _('در حال بررسی - مالی')),
            ('Tankhah_PAID', _('پرداخت‌شده')),

            ("FactorItem_approve", "👍تایید/رد ردیف فاکتور (تایید ردیف فاکتور*استفاده در مراحل تایید*)"),
            ('edit_full_tankhah', '👍😊تغییرات کاربری در فاکتور /تایید یا رد ردیف ها '),

            ('Dashboard_Core_view', 'دسترسی به داشبورد Core پایه'),
            ('DashboardView_flows_view', 'دسترسی به روند تنخواه گردانی'),
            ('Dashboard__view', 'دسترسی به داشبورد اصلی 💻'),
            ('Dashboard_Stats_view', 'دسترسی به آمار کلی داشبورد💲'),
        ]


    def __str__(self):
        project_str = self.project.name if self.project else 'بدون پروژه'
        subproject_str = f" ({self.subproject.name})" if self.subproject else ''
        return f"{self.number} - {project_str}{subproject_str} - {self.amount:,.0f} "
    def get_remaining_budget(self):
        """محاسبه بودجه باقی‌مانده با در نظر گرفتن سقف پرداخت"""
        remaining = Decimal('0')
        from budgets.budget_calculations import get_subproject_remaining_budget,get_project_remaining_budget
        if self.project_budget_allocation:
            remaining = self.project_budget_allocation.get_remaining_amount()
        elif self.subproject:
            remaining = get_subproject_remaining_budget(self.subproject)
        elif self.project:
            remaining = get_project_remaining_budget(self.project)
        else:
            logger.warning(f"No budget source for Tankhah {self.number}")
            return remaining

        # اعمال سقف پرداخت
        from core.models import SystemSettings
        settings = SystemSettings.objects.first()
        if self.is_payment_ceiling_enabled and self.payment_ceiling is not None:
            remaining = min(remaining, self.payment_ceiling)
        elif settings and settings.tankhah_payment_ceiling_enabled_default and settings.tankhah_payment_ceiling_default is not None:
            remaining = min(remaining, settings.tankhah_payment_ceiling_default)

        return remaining

    def update_remaining_budget(self):
        """به‌روزرسانی فیلد remaining_budget بدون فراخوانی save"""
        self.remaining_budget = self.get_remaining_budget()
    def clean(self):
        """اعتبارسنجی تنخواه"""
        super().clean()

        if self.amount is None:
            raise ValidationError({"amount": _("مبلغ تنخواه اجباری است.")})

        if self.amount <= 0:
            raise ValidationError({"amount": _("مبلغ تنخواه باید مثبت باشد.")})

        if self.subproject and self.project and self.subproject.project != self.project:
            raise ValidationError({"subproject": _("زیرپروژه باید متعلق به پروژه انتخاب‌شده باشد.")})

        if self.project_budget_allocation and self.project and self.project_budget_allocation.project != self.project:
            raise ValidationError({"project_budget_allocation": _("تخصیص بودجه باید متعلق به پروژه انتخاب‌شده باشد.")})

        remaining = self.get_remaining_budget()

        if not self.pk:  # تنخواه جدید
            remaining_budget = self.get_remaining_budget()
            if self.amount > remaining_budget:
                raise ValidationError(
                    _(f"مبلغ تنخواه ({self.amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده ({remaining:,.0f} ریال) است.")
                )

    def save(self, *args, **kwargs):
        from budgets.budget_calculations import create_budget_transaction
        from budgets.models import BudgetAllocation
        with transaction.atomic():
            if not self.number:
                self.number = self.generate_number()

            # بررسی وجود و فعال بودن project_budget_allocation
            if self.project_budget_allocation:
                try:
                    allocation = BudgetAllocation.objects.get(id=self.project_budget_allocation.id,is_active=True)
                except BudgetAllocation.DoesNotExist:
                    raise ValidationError(_("تخصیص بودجه معتبر نیست یا غیرفعال است."))
            else:
                # اگر project_budget_allocation اجباری است، خطا بدهید
                raise ValidationError(_("تخصیص بودجه پروژه اجباری است."))

            self.update_remaining_budget()
            self.clean()
            #
            # if self.project_budget_allocation:
            #     remaining = self.project_budget_allocation.get_remaining_amount()
            #     if not self.pk is None:
            #         old_instance = Tankhah.objects.get(pk=self.pk)
            #         if old_instance.amount != self.amount:
            #             remaining = self.get_remaining_budget()
            #             if self.amount > remaining:
            #                 raise ValidationError(
            #                     _(f"مبلغ تنخواه ({self.amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده تخصیص ({remaining:,.0f} ریال) است.")
            #                 )
            #     else:
            #         remaining = self.get_remaining_budget()
            #         if  self.amount > remaining  :
            #             raise ValidationError(
            #                 _(f"مبلغ تنخواه ({self.amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده تخصیص ({remaining:,.0f} ریال) است.")
            #             )
            #     # if self.amount > remaining:
            #     #     raise ValidationError(
            #     #         _(f"مبلغ تنخواه ({self.amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده تخصیص ({remaining:,.0f} ریال) است.")
            #     #     )

            # تنظیم فلگ‌ها
            if self.status in ['APPROVED', 'PAID'] and not self.is_locked:
                if self.status == 'PAID':
                    create_budget_transaction(
                        allocation=self.project_budget_allocation,
                        transaction_type='CONSUMPTION',
                        amount=self.amount,
                        related_obj=self,
                        created_by=self.created_by,
                        description=f"Tankhah {self.number} for project {self.project.id}",
                        transaction_id=f"TX-TNK-CONS-{self.number}"
                    )
                    self.is_locked = True

            if self.status == 'REJECTED':
                # initial_stage = AccessRule.objects.order_by('order').first()
                from core.models import Status
                initial_stage = Status.objects.filter(is_initial=True).first()
                if self.current_stage == initial_stage:
                    factors = Factor.objects.filter(tankhah=self, is_finalized=True)
                    factors.update(is_finalized=False, locked=False)
                    target_allocation = BudgetAllocation.objects.filter(organization__is_core=True).first()
                    if target_allocation:
                        create_budget_transaction(
                            allocation=self.project_budget_allocation,
                            transaction_type='TRANSFER',
                            amount=self.amount,
                            related_obj=self,
                            created_by=self.created_by,
                            description=f"انتقال بودجه به دلیل رد تنخواه {self.number}",
                            transaction_id=f"TX-TNK-XFER-{self.number}",
                            target_allocation = target_allocation
                        )
                    else:
                        create_budget_transaction(
                            allocation=self.project_budget_allocation,
                            transaction_type='RETURN',
                            amount=self.amount,
                            related_obj=self,
                            created_by=self.created_by,
                            description=f"بازگشت بودجه به دلیل رد تنخواه {self.number}",
                            transaction_id=f"TX-TNK-RET-{self.number}"
                        )
                    self.is_locked = False

            # super().save(*args, **kwargs)
            # بررسی قفل تخصیص
            is_active = False if (
                    self.project_budget_allocation and (
                    self.project_budget_allocation.is_locked or
                    self.project_budget_allocation.budget_period.is_locked
            )
            ) else True
            self.is_active = is_active

            super().save(*args, **kwargs)
            logger.info(f"Tankhah saved 👍with ID: {self.pk}")

    def generate_number(self):
        sep = NUMBER_SEPARATOR
        import jdatetime
        jalali_date = jdatetime.datetime.fromgregorian(datetime=self.date).strftime('%Y%m%d')
        org_code = self.organization.code
        project_code = self.project.code if self.project else 'NOPRJ'

        with transaction.atomic():
            max_serial = Tankhah.objects.filter(
                organization=self.organization,
                date__date=self.date.date()
            ).aggregate(Max('number'))['number__max']
            serial = 1 if not max_serial else int(max_serial.split(sep)[-1]) + 1
            new_number = f"TNKH{sep}{jalali_date}{sep}{org_code}{sep}{project_code}{sep}{serial:03d}"
            while Tankhah.objects.filter(number=new_number).exists():
                serial += 1
                new_number = f"TNKH{sep}{jalali_date}{sep}{org_code}{sep}{project_code}{sep}{serial:03d}"
            return new_number

    def process_approved_factors(self, user):
        processed_count = 0
        with transaction.atomic():
            approved_factors = self.factors.filter(status__code='APPROVED')
            current_status = self.status  # تغییر از current_stage به status
            current_stage= current_status
            if not current_status or current_status.code not in ['APPROVED', 'PENDING_APPROVAL']:
                logger.warning(f"No payment order can be issued for Tankhah {self.number}: Invalid status")
                return

            for factor in approved_factors:
                # if not current_stage or not current_stage.triggers_payment_order:
                #     logger.warning(f"No payment order can be issued for Tankhah {self.number}: Invalid stage")
                #     continue

                factor.status = Status.objects.get(code='PAID')
                factor.save(current_user=user)

                from budgets.budget_calculations import create_budget_transaction
                create_budget_transaction(
                    allocation=self.project_budget_allocation,
                    transaction_type='CONSUMPTION',
                    amount=factor.amount,
                    related_obj=factor,
                    created_by=user,
                    description=f"مصرف بودجه توسط فاکتور پرداخت شده {factor.number}",
                    transaction_id=f"TX-FAC-{factor.number}"
                )

                user_post = user.userpost_set.filter(is_active=True).first()
                from core.models import PostAction,AccessRule
                if user_post and PostAction.objects.filter(
                    post=user_post.post,
                    stage=current_stage,
                    action_type__code='ISSUE_PAYMENT_ORDER',
                    entity_type='FACTOR',
                    is_active=True
                ).exists():
                    target_payee = factor.payee
                    if not target_payee:
                        logger.warning(f"No payee for Factor {factor.number}")
                        continue

                    # initial_po_stage = AccessRule.objects.filter(
                    #     entity_type='PAYMENTORDER',
                    #     order=1,
                    #     is_active=True
                    # ).first()
                    from core.models import Status
                    initial_po_stage = Status.objects.filter(code='PAYMENTORDER', is_initial=True).first()

                    if not initial_po_stage:
                        logger.error("No initial workflow stage for PAYMENTORDER")
                        continue

                    from budgets.models import PaymentOrder
                    payment_order = PaymentOrder(
                        tankhah=self,
                        related_tankhah=self,
                        amount=factor.amount,
                        description=f"پرداخت برای فاکتور {factor.number}",
                        organization=self.organization,
                        project=self.project if hasattr(self, 'project') else None,
                        status='DRAFT',
                        created_by=user,
                        created_by_post=user_post.post,
                        current_stage=initial_po_stage,
                        issue_date=timezone.now().date(),
                        payee=target_payee,
                        min_signatures=initial_po_stage.min_signatures or 1
                    )
                    payment_order.save()
                    payment_order.related_factors.add(factor)

                    approving_posts = StageApprover.objects.filter(
                        stage=initial_po_stage,
                        is_active=True
                    ).select_related('post')
                    for stage_approver in approving_posts:
                        ApprovalLog.objects.create(
                            action=payment_order,
                            approver_post=stage_approver.post
                        )

                    logger.info(f"PaymentOrder {payment_order.order_number} issued for Factor {factor.number} in Tankhah {self.number}")
                    processed_count += 1

                ApprovalLog.objects.create(
                    factor=factor,
                    action='SIGN_PAYMENT',
                    stage=current_stage,
                    user=user,
                    post=user_post.post if user_post else None,
                    content_type=ContentType.objects.get_for_model(factor),
                    object_id=factor.id,
                    comment=f"دستور پرداخت برای فاکتور {factor.number} صادر شد.",
                    changed_field='status'
                )

                if current_stage.auto_advance:
                    from core.models import  AccessRule
                    next_stage = AccessRule.objects.filter(order__gt=current_stage.order, is_active=True).order_by('order').first()
                    if next_stage:
                        self.current_stage = next_stage
                        self.save()
                        logger.info(f"Tankhah {self.number} advanced to stage {next_stage.name}")

        return processed_count

class TankhActionType(models.Model):
    action_type = models.CharField(max_length=25, verbose_name=_('انواع  اقدام'))
    code = models.CharField(max_length=50, unique=True,verbose_name=_('تایپ'))
    name = models.CharField(max_length=100,verbose_name=_('عنوان'))
    description = models.TextField(blank=True,verbose_name=_('توضیحات'))

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
class TankhahAction(models.Model): #صدور دستور پرداخت
    # ACTION_TYPES = (
    #     ('ISSUE_PAYMENT_ORDER', _('صدور دستور پرداخت')),
    #     ('FINALIZE', _('اتمام')),
    #     ('INSURANCE', _('ثبت بیمه')),
    #     ('CUSTOM', _('سفارشی')),
    # )

    tankhah = models.ForeignKey(Tankhah, on_delete=models.CASCADE, related_name='actions', verbose_name=_("تنخواه"))
    # action_type = models.CharField(max_length=50, choices=TankhActionType, verbose_name=_("نوع اقدام"))
    amount = models.DecimalField(max_digits=25, decimal_places=2, null=True, blank=True, verbose_name=_("مبلغ (برای پرداخت)"))
    stage = models.ForeignKey( 'core.AccessRule' , on_delete=models.PROTECT, verbose_name=_("مرحله"))
    post = models.ForeignKey(  'core.Post' , on_delete=models.SET_NULL, null=True, verbose_name=_("پست انجام‌دهنده"))
    user = models.ForeignKey( CustomUser , on_delete=models.SET_NULL, null=True, verbose_name=_("کاربر"))
    # created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    reference_number = models.CharField(max_length=50, blank=True, verbose_name=_("شماره مرجع"))
    action_type = models.ForeignKey('budgets.TransactionType' , on_delete=models.SET_NULL, null=True,verbose_name=_("نوع اقدام"))
    is_active = models.BooleanField(default=True,verbose_name=_('فعال'))
    created_at = models.DateTimeField(auto_now_add=True,verbose_name=_('ایجاد شده توسط'))


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
    # --- فیلدهای اصلی و تمیز شده ---
    number = models.CharField(max_length=100, blank=True, verbose_name=_("شماره فاکتور"))
    tankhah = models.ForeignKey('Tankhah', on_delete=models.PROTECT, related_name='factors', verbose_name=_("تنخواه"))
    date = models.DateField(default=timezone.now, verbose_name=_("تاریخ"))
    amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_('مبلغ کل فاکتور'), default=0)
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    category = models.ForeignKey('ItemCategory', on_delete=models.PROTECT, verbose_name=_("دسته‌بندی"))
    created_by = models.ForeignKey('accounts.CustomUser', related_name='created_factors', on_delete=models.PROTECT,
                                   verbose_name=_("ایجادکننده"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))

    # **فیلد status نهایی و صحیح**
    status = models.ForeignKey(
        'core.Status',
        on_delete=models.PROTECT,
        verbose_name=_("وضعیت"),
        default=get_default_factor_status,
        null=True,  # null=True برای جلوگیری از خطا در صورتی که get_default_factor_status چیزی برنگرداند
        blank=True,
        # db_column='status'
    )

    # --- فیلدهای مدیریتی ---
    is_locked = models.BooleanField(default=False, verbose_name=_('قفل شده'))
    rejected_reason = models.TextField(blank=True, null=True, verbose_name=_("دلیل رد"))
    is_deleted = models.BooleanField(default=False, verbose_name=_("حذف شده"))
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey('accounts.CustomUser', null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='deleted_factors')

    locked_by_stage = models.ForeignKey('core.Status', null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name='factor_lock_by_stage_set', verbose_name=_("قفل شده توسط وضعیت"))

    budget = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name=_("بودجه تخصیصی"))
    remaining_budget = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name=_("بودجه باقیمانده"))
    is_emergency = models.BooleanField(default=False, verbose_name=_("اضطراری"))
    re_registered_in = models.ForeignKey('Tankhah', null=True, blank=True, on_delete=models.SET_NULL,related_name='re_registered_factors',verbose_name=_("تنخواه جدید"))

    #----------------------------------------
    def update_total_amount(self):
        """
        مبلغ کل فاکتور را بر اساس مجموع ردیف‌های آن محاسبه و آپدیت می‌کند.
        """
        total = self.items.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        if self.amount != total:
            self.amount = total
            self.save(update_fields=['amount'])
            logger.info(f"Factor {self.pk} amount updated to {total}.")
        return total
    #----------------------------------------
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
    #----------------------------------------
    def clean(self):
        """
        نسخه نهایی و ایمن متد clean.
        """
        super().clean()
        if not self.category:
            raise ValidationError(_("دسته‌بندی الزامی است."))
        # اعتبارسنجی وضعیت تنخواه
        if self.tankhah and self.tankhah.status:
            # فقط به تنخواه‌هایی که هنوز در جریان هستند اجازه ایجاد فاکتور می‌دهیم.
            if self.tankhah.status.is_final_approve or self.tankhah.status.is_final_reject:
                raise ValidationError(_("تنخواه انتخاب‌شده در وضعیت نهایی قرار دارد و نمی‌توان برای آن فاکتور جدید ثبت کرد."))

        if self.status:
            # **اصلاح کلیدی:** مقایسه بر اساس status.code
            if self.status.code == 'REJECT' and not self.rejected_reason:
                raise ValidationError({"rejected_reason": _("برای رد کردن فاکتور، نوشتن دلیل الزامی است.")})

        # اعتبارسنجی دلیل رد
        if self.status and self.status.is_final_reject and not self.rejected_reason:
            raise ValidationError({"rejected_reason": _("برای رد کردن فاکتور، نوشتن دلیل الزامی است.")})
    #----------------------------------------
    def save(self, *args, **kwargs):
        """
            متد save که منطق‌های کلیدی کسب و کار را در خود دارد.
            """
        user = kwargs.pop('current_user', None)
        is_new = self.pk is None
        # اگر شیء جدید است، شماره تولید کن و از full_clean رد شو
        if is_new:
            if not self.number:
                self.number = self.generate_number()
                logger.debug(f"شماره فاکتور جدید تولید شد: {self.number}")
            if not self.status:
                self.status = get_default_factor_status()
                from core.models import Status
                try:
                    self.status = Status.objects.get(code='DRAFT', is_initial=True)
                    logger.debug(f"Status set to DRAFT in save method for factor {self.number}")
                except Status.DoesNotExist:
                    raise ValidationError("وضعیت اولیه 'DRAFT' در سیستم تعریف نشده است.")
                except Status.MultipleObjectsReturned:
                    raise ValidationError("بیش از یک وضعیت اولیه 'DRAFT' در سیستم تعریف شده است.")

        with transaction.atomic():

            # full_clean را اینجا فراخوانی می‌کنیم تا قبل از هر منطقی، داده‌ها معتبر باشند
            self.full_clean()
            original = None
            if self.pk:
                original_status = Factor.objects.get(pk=self.pk).status
            super().save(*args, **kwargs)

            if self.status and self.status.code == 'PAID' and self.status != original_status:
                logger.info(
                    f"Factor {self.number} marked as PAID. Creating CONSUMPTION transaction and checking payment order.")
                self.is_locked = True
                from budgets.budget_calculations import create_budget_transaction
                create_budget_transaction(
                    allocation=self.tankhah.project_budget_allocation,
                    transaction_type='CONSUMPTION',
                    amount=self.amount,
                    related_obj=self,
                    created_by=username or self.created_by,
                    description=f"مصرف بودجه توسط فاکتور پرداخت شده {self.number}",
                    transaction_id=f"TX-FAC-{self.number}"
                )
                self.is_locked = True

            if original and self.status != original.status and username:
                user_post = username.userpost_set.filter(is_active=True).first() if username else None
                if user_post:
                    action = 'APPROVE' if self.status in ['APPROVED', 'PAID'] else 'REJECT'
                    ApprovalLog.objects.create(
                        factor=self,
                        action=action,
                        stage=self.tankhah.current_stage,
                        user=username,
                        post=user_post.post,
                        content_type=ContentType.objects.get_for_model(self),
                        object_id=self.id,
                        comment=f"تغییر وضعیت فاکتور به {Factor.status.name} توسط {username.get_full_name()}",
                        changed_field='status'
                    )

            super().save(update_fields=['is_locked'])

    #----------------------------------------
    def revert_to_pending(self, user):
        """بازگرداندن فاکتور ردشده به وضعیت در انتظار تأیید"""
        from core.models import Status
        if not self.status or self.status.code != 'REJECT':
            return
        with transaction.atomic():
            pending_status = Status.objects.get(code='PENDING_APPROVAL')
            self.status = pending_status
            self.is_locked = False
            self.save(update_fields=['status', 'is_locked'])
            ApprovalLog.objects.create(
                factor=self,
                action='STAGE_CHANGE',
                stage=self.tankhah.current_stage,
                user=user,
                post=user.userpost_set.filter(is_active=True).first().post,
                content_type=ContentType.objects.get_for_model(self),
                object_id=self.id,
                comment=f"فاکتور {self.number} به وضعیت در انتظار تأیید بازگشت.",
                changed_field='status'
            )
            FactorHistory.objects.create(
                factor=self,
                change_type=FactorHistory.ChangeType.STATUS_CHANGE,
                changed_by=user,
                old_data={'status': 'REJECTED'},
                new_data={'status': 'PENDING'},
                description=f"بازگشت فاکتور به وضعیت در انتظار تأیید"
            )
            logger.info(f"Factor {self.number} reverted to PENDING by {user.username}")
    #---------------------------------------
    def unlock(self, user):
        """باز کردن قفل فاکتور توسط کاربر مجاز (مثل BOARD)"""
        if not user.has_perm('tankhah.factor_unlock'):
            raise PermissionError(_("کاربر مجوز باز کردن فاکتور را ندارد."))
        if not self.is_locked:
            return
        from core.models import Status
        try:
            pending_status = Status.objects.get(code='PENDING_APPROVAL')
            self.is_locked = False
            self.status = pending_status
            self.save(update_fields=['is_locked', 'status'])
            ApprovalLog.objects.create(
                factor=self,
                action='APPROVE',
                stage=self.tankhah.current_stage,
                user=user,
                post=user.userpost_set.filter(is_active=True).first().post,
                content_type=ContentType.objects.get_for_model(self),
                object_id=self.id,
                comment=f"فاکتور {self.number} توسط {user.username} باز شد.",
                changed_field='is_locked'
            )
            logger.info(f"Factor {self.number} unlocked by {user.username}")
        except Status.DoesNotExist:
            logger.error("FATAL: Status with code 'PENDING_APPROVAL' not found in DB.")
    #----------------------------------------
    def get_items_total(self):
        """مبلغ کل فاکتور را بر اساس مجموع ردیف‌ها آپدیت می‌کند."""
        if self.pk:
            total = self.items.aggregate(total=Sum('amount'))['total'] or Decimal('0')
            if self.amount != total:
                self.amount = total
                self.save(update_fields=['amount'])
        return Decimal('0')
    #----------------------------------------
    def get_first_access_rule_stage(self):
        from core.models import Status
        first_stage = Status.objects.filter(is_initial=True).first()
        return first_stage if first_stage else None
    #----------------------------------------
    def get_remaining_budget(self):
        from budgets.budget_calculations import get_factor_remaining_budget
        return get_factor_remaining_budget(self)
    #----------------------------------------
    def total_amount(self):
        if self.pk:
            return self.get_items_total()
        return Decimal('0')
    #----------------------------------------
    def can_approve(self, user):
        pass
        # """
        # بررسی می‌کند که آیا کاربر می‌تواند این فاکتور را تأیید کند.
        # :param user: کاربر فعلی
        # :return: True اگر کاربر دسترسی دارد، False در غیر این صورت
        # """
        # # بررسی احراز هویت کاربر
        # if not user.is_authenticated:
        #     return False
        # # بررسی قفل بودن فاکتور یا تنخواه
        # if self.is_locked or self.tankhah.is_locked or self.tankhah.is_archived:
        #     return False
        # # استفاده از تابع can_edit_approval برای بررسی دسترسی
        # from tankhah.Factor.Approved.fun_can_edit_approval import can_edit_approval
        # return can_edit_approval(user, self.tankhah, self.tankhah.current_stage)
    #----------------------------------------

    #----------------------------------------
    def __str__(self):
        # اصلاح متد __str__ برای مدیریت tankhah=None
        tankhah_number = self.tankhah.number if self.tankhah else "تنخواه ندارد"
        return f"{self.number} ({tankhah_number})"
    #----------------------------------------
    class Meta:
        verbose_name = _("فاکتور")
        verbose_name_plural = _("فاکتورها")
        indexes = [
            models.Index(fields=['number', 'is_deleted','date', 'status', 'tankhah']),
        ]
        default_permissions = ()
        permissions = [
            ('factor_add', _('افزودن فاکتور')),
            ('factor_view', _('نمایش فاکتور')),
            ('factor_update', _('بروزرسانی فاکتور')),
            ('factor_delete', _('حذف فاکتور')),
            ('factor_approve', _(' 👍تایید/رد ردیف فاکتور (تایید ردیف فاکتور*استفاده در مراحل تایید*)')),
            ('factor_reject', _('رد فاکتور')),
            ('Factor_full_edit', _('دسترسی کامل به فاکتور')),
            ('factor_unlock', _('باز کردن فاکتور قفل‌شده')),
            ('factor_approval_path', _('بررسی مسیر تایید/رد فاکتور⛓️‍💥')),
        ]
    #----------------------------------------
#-----------------------------------------------
class FactorItem(models.Model):
    """  اقلام فاکتور """
    factor = models.ForeignKey(Factor, on_delete=models.CASCADE, related_name='items', verbose_name=_("فاکتور"))
    description = models.CharField(max_length=255, verbose_name=_("شرح ردیف"))
    amount = models.DecimalField(max_digits=25, default=0, decimal_places=2, verbose_name=_("مبلغ"))
    # status = models.CharField(max_length=40, choices=FACTOR_STATUSES, default='PENDING_APPROVAL', verbose_name=_("وضعیت"))
    status = models.ForeignKey(
        'core.Status',
        on_delete=models.PROTECT,
        verbose_name=_("وضعیت"),
        default=get_default_factor_status,
        null=True,
        blank=True,
        # db_column='status'  # اضافه کردن db_column
    )
    quantity = models.DecimalField(max_digits=25, default=1, decimal_places=2, verbose_name=_("تعداد"))
    unit_price = models.DecimalField(max_digits=25, decimal_places=2, blank=True, null=True,verbose_name=_("قیمت واحد"))
    min_stage_order = models.IntegerField(default=1, verbose_name=_("حداقل ترتیب مرحله"),help_text=_("این نوع تراکنش فقط در این مرحله یا بالاتر مجاز است")  , editable=False)
    # Optional: Timestamps for tracking
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان ایجاد"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("زمان آخرین ویرایش"))
    is_locked = models.BooleanField(default=False,verbose_name=_('قفل شود'))


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
# class ApprovalLog(models.Model):
#     # --- فیلدهای ارتباطی ---
#     # این فیلدها به صراحت مشخص می‌کنند که لاگ ممکن است به کدام اشیاء مرتبط باشد
#     tankhah = models.ForeignKey(Tankhah, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("تنخواه"))
#     factor = models.ForeignKey(Factor, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("فاکتور"))
#     factor_item = models.ForeignKey(FactorItem, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("ردیف فاکتور"))
#
#     # --- فیلدهای GenericForeignKey برای اتصال عمومی ---
#     # اینها منبع اصلی حقیقت برای "هدف" لاگ هستند
#     content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, verbose_name=_("نوع موجودیت"))
#     object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("شناسه موجودیت"))
#     content_object = GenericForeignKey('content_type', 'object_id')
#
#     # --- فیلدهای اصلی لاگ ---
#     # action = models.CharField(max_length=45, choices=ACTION_TYPES, verbose_name=_("نوع اقدام"))
#
#     from_status = models.ForeignKey('core.Status', on_delete=models.PROTECT, related_name='+',verbose_name= _('از وضعیت '))
#     to_status = models.ForeignKey('core.Status', on_delete=models.PROTECT, related_name='+',verbose_name=_("تغییر به"))
#     # action = models.ForeignKey('core.Action', on_delete=models.CASCADE, verbose_name=_("نوع اقدام گردش کار"))
#     action = models.ForeignKey('core.Action', on_delete=models.PROTECT, verbose_name=_("اقدام انجام شده"))
#
#     user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name=_("کاربر"))
#     post = models.ForeignKey('core.Post', on_delete=models.SET_NULL, null=True, verbose_name=_("پست تأییدکننده"))
#     comment = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
#     timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان"))
#
#
#     # --- فیلدهای تکمیلی و اطلاعاتی (که شما داشتید و مهم هستند) ---
#     is_final_approval = models.BooleanField(default=False, verbose_name=_("نهایی شده"))
#     changed_field = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("فیلد تغییر یافته"))
#     seen_by_higher = models.BooleanField(default=False, verbose_name=_("دیده‌شده توسط رده بالاتر"))
#     seen_at = models.DateTimeField(null=True, blank=True, verbose_name=_("زمان دیده شدن"))
#
#     # --- فیلدهای مربوط به گردش کار ---
#     is_temporary = models.BooleanField(default=False, verbose_name="موقت")  # اضافه شده
#     # stage = models.ForeignKey('core.AccessRule', on_delete=models.SET_NULL, null= True , default=None,related_name='approval_logs_access', verbose_name=_("مرحله"))
#     # stage_rule = models.ForeignKey('core.AccessRule', on_delete=models.SET_NULL, null=True, related_name='approval_logs',
#     #                            verbose_name=_("قانون/مرحله مرتبط"))
#     stage = models.ForeignKey('core.Status', on_delete=models.SET_NULL, null=True, default=None,
#                               related_name='approval_logs_access', verbose_name=_("وضعیت"))
#     stage_rule = models.ForeignKey('core.Status', on_delete=models.SET_NULL, null=True, related_name='approval_logs',
#                                    verbose_name=_("وضعیت مرتبط"))
#
#     date = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
#     action_type = models.CharField(max_length=50, blank=True, verbose_name=_("نوع اقدام"))
#     created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, related_name='approvalLog_created', verbose_name=_("ایجادکننده"))
#
# # --- پراپرتی‌های کمکی برای دسترسی آسان ---
#     @property
#     def stage_name(self):
#         """نام مرحله را از قانون مرتبط برمی‌گرداند."""
#         return self.stage_rule.name if self.stage_rule else _("وضعیت نامشخص")
#
#     @property
#     def stage_order(self):
#         """ترتیب مرحله را از قانون مرتبط برمی‌گرداند."""
#         return self.stage_rule.stage_order if self.stage_rule else None
#
#     # def save(self, *args, **kwargs):
#     #     from core.models import Organization
#     #     # if self.pk is None:
#     #     #     logger.info(
#     #     #         f"[ApprovalLog] Attempting to save new ApprovalLog for user {self.user.username}, action {self.action}")
#     #     #     # سناریو ۱: ویو، فیلد جدید (stage_rule) را پاس داده است (روش ترجیحی).
#     #     #     if self.stage_rule and not self.stage:
#     #     #         # فیلد قدیمی (stage) را با فیلد جدید همگام می‌کنیم.
#     #     #         self.stage = self.stage_rule
#     #     #         logger.debug(
#     #     #             f"[ApprovalLog SAVE] 'stage' field populated from 'stage_rule' (PK: {self.stage_rule.pk}).")
#     #     #
#     #     #     # سناریو ۲: کد قدیمی هنوز از فیلد stage استفاده می‌کند.
#     #     #     elif self.stage and not self.stage_rule:
#     #     #         # فیلد جدید (stage_rule) را با فیلد قدیمی همگام می‌کنیم.
#     #     #         self.stage_rule = self.stage
#     #     #         logger.debug(f"[ApprovalLog SAVE] 'stage_rule' field populated from 'stage' (PK: {self.stage.pk}).")
#     #     #
#     #     #     # سناریو ۳: هیچکدام پاس داده نشده‌اند. باید آن را استنتاج کنیم.
#     #     #     elif not self.stage and not self.stage_rule:
#     #     #         inferred_stage = None
#     #     #         source_object = self.factor or self.tankhah
#     #     #         if source_object and hasattr(source_object,
#     #     #                                      'tankhah') and source_object.tankhah and source_object.tankhah.current_stage:
#     #     #             inferred_stage = source_object.tankhah.current_stage
#     #     #
#     #     #         if inferred_stage:
#     #     #             self.stage = inferred_stage
#     #     #             self.stage_rule = inferred_stage
#     #     #             logger.debug(
#     #     #                 f"[ApprovalLog SAVE] Both 'stage' and 'stage_rule' were inferred from tankhah.current_stage: {inferred_stage.pk}")
#     #     #         else:
#     #     #             logger.error(
#     #     #                 "[ApprovalLog SAVE] FATAL: Cannot save log. No stage information was provided or could be inferred.")
#     #     #             raise ValueError("ApprovalLog requires a valid stage to be saved.")
#     #     #
#     #     #     # --- مرحله ۲: اطمینان از وجود پست (اختیاری اما مهم) ---
#     #     #     if self.user and not self.post:
#     #     #         user_post_instance = self.user.userpost_set.filter(is_active=True).first()
#     #     #         if user_post_instance:
#     #     #             self.post = user_post_instance.post
#     #     #
#     #     #     user_post = self.user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
#     #     #     if not user_post:
#     #     #         logger.error(f"[ApprovalLog] No active UserPost found for user {self.user.username}")
#     #     #         raise ValueError(f"کاربر {self.user.username} هیچ پست فعالی ندارد")
#     #     #
#     #     #     user_org_ids = set()
#     #     #     for up in self.user.userpost_set.filter(is_active=True):
#     #     #         org = up.post.organization
#     #     #         user_org_ids.add(org.id)
#     #     #         current_org = org
#     #     #         while current_org.parent_organization:
#     #     #             current_org = current_org.parent_organization
#     #     #             user_org_ids.add(current_org.id)
#     #     #     is_hq_user = any(Organization.objects.filter(id=org_id, is_core=True).exists() for org_id in user_org_ids)
#     #     #     logger.info(f"[ApprovalLog] User {self.user.username} is_hq_user: {is_hq_user}")
#     #     #
#     #     #     # تنظیم stage اگر وجود نداشته باشد
#     #     #     if not self.stage and self.factor:
#     #     #         logger.info(f"[ApprovalLog] Setting stage from factor.current_stage for user {self.user.username}")
#     #     #         self.stage = self.factor.current_stage
#     #     #     if not self.stage:
#     #     #         logger.error(f"[ApprovalLog] Stage is required for ApprovalLog, but none provided")
#     #     #         raise ValueError("Stage is required for ApprovalLog")
#     #     #
#     #     #     if self.user.is_superuser or is_hq_user or self.user.has_perm('tankhah.Tankhah_view_all'):
#     #     #         logger.info(f"[ApprovalLog] User {self.user.username} has full access, saving directly")
#     #     #         super().save(*args, **kwargs)
#     #     #         return
#     #     #
#     #     #     if self.factor_item:
#     #     #         entity_type = 'FACTORITEM'
#     #     #     elif self.factor:
#     #     #         entity_type = 'FACTOR'
#     #     #     elif self.content_type:
#     #     #         entity_type = self.content_type.model.upper()
#     #     #     else:
#     #     #         entity_type = 'GENERAL'
#     #     #
#     #     #     logger.info(f"[ApprovalLog] Entity type: {entity_type}")
#     #     #     branch_filter = Q(branch=user_post.post.branch) if user_post.post.branch else Q(branch__isnull=True)  # 💡 تغییر
#     #     #     from core.models import AccessRule
#     #     #     access_rule = AccessRule.objects.filter(
#     #     #         organization=user_post.post.organization,
#     #     #         stage=self.stage.stage,  # این خط ممکن است مشکل داشته باشد
#     #     #         action_type=self.action,
#     #     #         entity_type=entity_type,
#     #     #         min_level__lte=user_post.post.level,
#     #     #         branch=    branch_filter, # استفاده از Q object
#     #     #         is_active=True
#     #     #     ).first()
#     #     #
#     #     #     if not access_rule:
#     #     #         general_rule = AccessRule.objects.filter(
#     #     #             organization=user_post.post.organization,
#     #     #             stage=self.stage.stage,
#     #     #             action_type=self.action,
#     #     #             entity_type__in=['FACTOR', 'FACTORITEM'],
#     #     #             branch=branch_filter,  # استفاده از Q object
#     #     #             is_active=True
#     #     #         ).first()
#     #     #         if not general_rule:
#     #     #             logger.error(
#     #     #                 f"[ApprovalLog] No access rule found for user {self.user.username}, "
#     #     #                 f"action {self.action}, stage {self.stage.stage}, entity {entity_type}"
#     #     #             )
#     #     #             raise ValueError(
#     #     #                 f"پست {user_post.post} مجاز به {self.action} در مرحله {self.stage.stage} "
#     #     #                 f"برای {entity_type} نیست - قانون دسترسی یافت نشد"
#     #     #             )
#     #
#     #     if self.pk is None:
#     #         # **مرحله ۱: تنظیم خودکار GenericForeignKey (حل مشکل اصلی)**
#     #         # اولویت با factor_item، سپس factor، سپس tankhah است.
#     #         target_object = self.factor_item or self.factor or self.tankhah or self.content_object
#     #         if target_object and not (self.content_type and self.object_id):
#     #             self.content_type = ContentType.objects.get_for_model(target_object)
#     #             self.object_id = target_object.pk
#     #
#     #         # **مرحله ۲: اطمینان از وجود مرحله (Stage)**
#     #         if not self.stage_rule:
#     #             # تلاش برای استنتاج مرحله از تنخواه
#     #             source_tankhah = getattr(target_object, 'tankhah', self.tankhah)
#     #             if source_tankhah and source_tankhah.current_stage:
#     #                 self.stage_rule = source_tankhah.current_stage
#     #             else:
#     #
#     #                 logger.warning("ApprovalLog is being saved without a stage_rule.")
#     #
#     #         # **مرحله ۳: اطمینان از وجود پست کاربر**
#     #         if self.user and not self.post:
#     #             user_post_instance = self.user.userpost_set.filter(is_active=True).first()
#     #             if user_post_instance:
#     #                 self.post = user_post_instance.post
#     #
#     #     super().save(*args, **kwargs)
#     #     logger.info(f"[ApprovalLog] ApprovalLog saved successfully for user {self.user.username}")
#     def save(self, *args, **kwargs):
#         """
#         متد save بازنویسی شده برای اطمینان از صحت داده‌ها قبل از ذخیره در دیتابیس.
#         این متد از خطای IntegrityError جلوگیری کرده و خطاهای واضح‌تری تولید می‌کند.
#         """
#         # --- منطق زیر فقط برای رکوردهای جدید (قبل از اولین ذخیره) اجرا می‌شود ---
#         if self.pk is None:
#             # **مرحله ۱: تنظیم هوشمند GenericForeignKey با در نظر گرفتن اولویت**
#             # این بخش به نکته شما در مورد FactorItem توجه می‌کند.
#             target_object = self.factor_item or self.factor or self.tankhah or self.content_object
#             if target_object:
#                 if not self.content_type:
#                     self.content_type = ContentType.objects.get_for_model(target_object)
#                 if not self.object_id:
#                     self.object_id = target_object.pk
#
#             # **مرحله ۲: تنظیم پست فعال کاربر در صورت خالی بودن**
#             if self.user and not self.post:
#                 user_post_instance = self.user.userpost_set.filter(is_active=True).first()
#                 if user_post_instance:
#                     self.post = user_post_instance.post
#
#             # **مرحله ۳ (بسیار مهم): اعتبارسنجی فیلدهای کلیدی قبل از ذخیره**
#             # این بخش از خطای IntegrityError دیتابیس جلوگیری می‌کند.
#             if not self.user:
#                 raise ValidationError(_("لاگ تأیید باید یک کاربر مشخص داشته باشد."))
#             if not self.content_type or not self.object_id:
#                 raise ValidationError(_("لاگ تأیید باید به یک موجودیت مشخص (فاکتور، تنخواه و...) متصل باشد."))
#             if not self.from_status:
#                 raise ValidationError(_("فیلد 'از وضعیت' (from_status) نمی‌تواند خالی باشد."))
#             if not self.to_status:
#                 raise ValidationError(_("فیلد 'به وضعیت' (to_status) نمی‌تواند خالی باشد."))
#             if not self.action:
#                 # این همان خطایی است که با آن مواجه بودید.
#                 raise ValidationError(_("فیلد 'اقدام' (action) نمی‌تواند خالی باشد."))
#
#         # **مرحله نهایی: فراخوانی متد save اصلی برای ذخیره در دیتابیس**
#         super().save(*args, **kwargs)
#         logger.info(f"ApprovalLog PK={self.pk} for {self.content_type} ID={self.object_id} saved successfully.")
#
#     def __str__(self):
#         return f"{self.factor.number} - {self.get_action_display()}" #self.user.username} - {self.action} ({self.date}
#     class Meta:
#         verbose_name = _("لاگ‌های تأیید👍/رد👎")
#         verbose_name_plural = _("لاگ‌های تأیید👍/رد👎")
#         ordering = ['-timestamp']
#         default_permissions = ()
#         permissions = [
#             ('Approval_add', 'افزودن تأیید برای ثبت اقدامات تأیید یا رد'),
#             ('Approval_update', 'ویرایش تأیید برای ثبت اقدامات تأیید یا رد'),
#             ('Approval_delete', 'حــذف تأیید برای ثبت اقدامات تأیید یا رد'),
#             ('Approval_view', 'نمایش تأیید برای ثبت اقدامات تأیید یا رد'),
#             ('Stepchange', 'تغییر مرحله'),
#         ]
#         indexes = [models.Index(fields=['factor', 'tankhah', 'user', 'stage', 'action'])]

class ApprovalLog(models.Model):
    # --- فیلدهای ارتباطی ---
    tankhah = models.ForeignKey(Tankhah, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs',
                                verbose_name=_("تنخواه"))
    factor = models.ForeignKey(Factor, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs',
                               verbose_name=_("فاکتور"))
    factor_item = models.ForeignKey(FactorItem, on_delete=models.CASCADE, null=True, blank=True,
                                    related_name='approval_logs', verbose_name=_("ردیف فاکتور"))

    # --- GenericForeignKey برای اتصال عمومی و مطمئن ---
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_("نوع موجودیت"))
    object_id = models.PositiveIntegerField(verbose_name=_("شناسه موجودیت"))
    content_object = GenericForeignKey('content_type', 'object_id')

    # --- فیلدهای اصلی گردش کار ---
    from_status = models.ForeignKey('core.Status', on_delete=models.PROTECT, related_name='logs_from',
                                    verbose_name=_('از وضعیت'))
    to_status = models.ForeignKey('core.Status', on_delete=models.PROTECT, related_name='logs_to', verbose_name=_("به وضعیت"))
    action = models.ForeignKey('core.Action', on_delete=models.PROTECT, verbose_name=_("اقدام انجام شده"))

    # --- اطلاعات کاربر و توضیحات ---
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name=_("کاربر"))
    post = models.ForeignKey('core.Post', on_delete=models.SET_NULL, null=True, verbose_name=_("پست سازمانی کاربر"))
    comment = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان ثبت"))
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='approvalLog_created',
                                   verbose_name=_("ایجادکننده"))

    # --- فیلدهای تکمیلی ---
    is_final_approval = models.BooleanField(default=False, verbose_name=_("تایید نهایی"))

    seen_by_higher = models.BooleanField(default=False, verbose_name=_("دیده‌شده توسط رده بالاتر"))

    # FIX: حذف فیلدهای تکراری و مبهم مانند stage و action_type
    # stage_rule = models.ForeignKey(Status, ...) # این فیلد تکراری و غیرضروری است

    def save(self, *args, **kwargs):
        """
        متد save بازنویسی شده برای اطمینان از صحت داده‌ها قبل از ذخیره در دیتابیس.
        این متد از خطای IntegrityError جلوگیری کرده و خطاهای واضح‌تری تولید می‌کند.
        """
        # --- منطق زیر فقط برای رکوردهای جدید (قبل از اولین ذخیره) اجرا می‌شود ---
        if self.pk is None:

            # **مرحله ۱: تنظیم هوشمند GenericForeignKey با در نظر گرفتن اولویت**
            # این بخش به نکته شما در مورد FactorItem توجه می‌کند.
            target_object = self.factor_item or self.factor or self.tankhah
            if target_object:
                self.content_type = ContentType.objects.get_for_model(target_object)
                self.object_id = target_object.pk

            # **مرحله ۲: تنظیم پست فعال کاربر در صورت خالی بودن**
            if self.user and not self.post:
                user_post_instance = self.user.userpost_set.filter(is_active=True).first()
                if user_post_instance:
                    self.post = user_post_instance.post

            # **مرحله ۳ (بسیار مهم): اعتبارسنجی فیلدهای کلیدی قبل از ذخیره**
            # این بخش از خطای IntegrityError دیتابیس جلوگیری می‌کند.
            if not self.user:
                raise ValidationError(_("لاگ تأیید باید یک کاربر مشخص داشته باشد."))
            if not self.content_type or not self.object_id:
                raise ValidationError(_("لاگ تأیید باید به یک موجودیت مشخص (فاکتور، تنخواه و...) متصل باشد."))
            if not self.from_status:
                raise ValidationError(_("فیلد 'از وضعیت' (from_status) نمی‌تواند خالی باشد."))
            if not self.to_status:
                raise ValidationError(_("فیلد 'به وضعیت' (to_status) نمی‌تواند خالی باشد."))
            if not self.action:
                # این همان خطایی است که با آن مواجه بودید.
                raise ValidationError(_("فیلد 'اقدام' (action) نمی‌تواند خالی باشد."))

        # **مرحله نهایی: فراخوانی متد save اصلی برای ذخیره در دیتابیس**
        super().save(*args, **kwargs)
        logger.info(f"ApprovalLog PK={self.pk} for {self.content_type} ID={self.object_id} saved successfully.")

    def __str__(self):
        # FIX: متد __str__ قوی‌تر شد تا با هر نوع آبجکتی کار کند
        action_name = self.action.name if self.action else "اقدام نامشخص"
        user_name = self.user.username if self.user else "کاربر سیستم"
        return f"لاگ برای {self.content_object} - اقدام: {action_name} توسط {user_name}"

    class Meta:
        verbose_name = _("لاگ گردش کار")
        verbose_name_plural = _("لاگ‌های گردش کار")
        ordering = ['-timestamp']
        default_permissions = ()
        permissions = [
            ('ApprovalLog_add', 'افزودن لاگ گردش کار'),
            ('ApprovalLog_view', 'نمایش لاگ گردش کار'),
        ]
        # FIX: ایندکس‌ها با فیلدهای صحیح و نهایی به‌روز شدند
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['user', 'action']),
        ]
    # --- پراپرتی‌های کمکی برای دسترسی آسان ---
    @property
    def stage_name(self):
        """نام مرحله را از قانون مرتبط برمی‌گرداند."""
        return self.stage_rule.name if self.stage_rule else _("وضعیت نامشخص")

    @property
    def stage_order(self):
        """ترتیب مرحله را از قانون مرتبط برمی‌گرداند."""
        return self.stage_rule.stage_order if self.stage_rule else None
#==================================================================
class FactorHistory(models.Model):
    class ChangeType(models.TextChoices):
        CREATION = 'CREATION', _('ایجاد')
        UPDATE = 'UPDATE', _('ویرایش')
        STATUS_CHANGE = 'STATUS_CHANGE', _('تغییر وضعیت')
        DELETION = 'DELETION', _('حذف')

    factor = models.ForeignKey('Factor', on_delete=models.CASCADE, related_name='history', verbose_name=_('فاکتور'))
    change_type = models.CharField(max_length=20, choices=ChangeType.choices, verbose_name=_('نوع تغییر'))
    changed_by = models.ForeignKey( CustomUser, on_delete=models.SET_NULL, null=True, verbose_name=_('تغییر توسط'))
    change_timestamp = models.DateTimeField(default=timezone.now, verbose_name=_('زمان تغییر'))
    old_data = models.JSONField(null=True, blank=True, verbose_name=_('داده‌های قبلی'))
    new_data = models.JSONField(null=True, blank=True, verbose_name=_('داده‌های جدید'))
    description = models.TextField(blank=True, verbose_name=_('توضیحات'))

    class Meta:
        verbose_name = _('تاریخچه فاکتور')
        verbose_name_plural = _('تاریخچه‌های فاکتور')
        ordering = ['-change_timestamp']

    def __str__(self):
        return f"{self.get_change_type_display()} برای فاکتور {self.factor.number} در {self.change_timestamp}"

"""مشخص کردن کاربران یا نقش‌های مجاز برای هر مرحله"""
"""
توضیح:
این مدل مشخص می‌کند کدام پست‌ها در یک مرحله خاص می‌توانند به‌عنوان تأییدکننده برای تنخواه یا بودجه عمل کنند.
فیلد entity_type مشابه PostAction اضافه شده تا نوع موجودیت مشخص شود.
"""
class StageApprover(models.Model):
    stage = models.ForeignKey('core.AccessRule', on_delete=models.CASCADE, verbose_name=_('مرحله'))
    post = models.ForeignKey( 'core.Post', on_delete=models.CASCADE, verbose_name=_('پست مجاز'))  # فرض بر وجود مدل Post
    is_active = models.BooleanField(default=True, verbose_name="وضعیت فعال")
    entity_type = models.CharField(
        max_length=50,
        choices=(('TANKHAH', _('تنخواه')), ('BUDGET_ALLOCATION', _('تخصیص بودجه')) ,
                     ('FACTOR', _('فاکتور'))),

        default='TANKHAH',
        verbose_name=_("نوع موجودیت")
    )
    action = models.CharField(
        max_length=20,
        choices=[('APPROVE', 'تأیید'), ('REJECT', 'رد'), ('PARTIAL', 'نیمه‌تأیید')],
        blank=True,
        null=True
    )

    # entity_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)

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
# -------------------------------------------------------
# class DashboardView(TemplateView):
#     template_name = 'tankhah/calc_dashboard.html'
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         user = self.request.user
#
#         # تنخواه‌های در انتظار در هر مرحله
#         from core.models import AccessRule
#         stages = AccessRule.objects.all()
#         for stage in stages:
#             context[f'tankhah_pending_{stage.name}'] = Tankhah.objects.filter(
#                 current_stage=stage, status='PENDING'
#             ).count()
#
#         # تنخواه‌های نزدیک به مهلت
#         context['tankhah_due_soon'] = Tankhah.objects.filter(
#             due_date__lte=timezone.now() + timezone.timedelta(days=7),
#             status='PENDING'
#         ).count()
#
#         # مجموع مبلغ تأییدشده در ماه جاری
#         current_month = timezone.now().month
#         context['total_approved_this_month'] = Tankhah.objects.filter(
#             status='APPROVED', date__month=current_month
#         ).aggregate(total=Sum('amount'))['total'] or 0
#         print(context['total_approved_this_month'])
#         # آخرین فعالیت‌ها
#         context['recent_approvals'] = ApprovalLog.objects.order_by('-timestamp')[:5]
#
#         return context
class Dashboard_Tankhah(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('Dashboard_Tankhah_view','دسترسی به داشبورد تنخواه گردان ')
        ]

