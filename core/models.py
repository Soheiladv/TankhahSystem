# Create your models here.
import logging
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db import models

import accounts.models
from accounts.models import CustomUser

from tankhah.constants import ACTION_TYPES, ENTITY_TYPES
from django.contrib.postgres.fields import ArrayField

logger = logging.getLogger(__name__)

class OrganizationType(models.Model):
    fname = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name=_('نام شعبه/مجتمع/اداره'))
    org_type = models.CharField(max_length=100, unique=True, null=True, blank=True,
                                verbose_name=_('نام شعبه/مجتمع/اداره'))
    is_budget_allocatable = models.BooleanField(default=False, verbose_name=_("قابل استفاده برای تخصیص بودجه"))
    is_active = models.BooleanField(default=True, verbose_name=_('فعال'))

    def __str__(self):
        return f"{self.fname} - {self.org_type} " or _("نامشخص")

    class Meta:
        verbose_name = _('عنوان مرکز/شعبه/اداره/سازمان')
        verbose_name_plural = _('عنوان مرکز/شعبه/اداره/سازمان')
        default_permissions = ()
        permissions = [
            ('OrganizationType_add', 'افزودن شعبه/اداره/مجتمع/سازمان'),
            ('OrganizationType_view', 'نمایش شعبه/اداره/مجتمع/سازمان'),
            ('OrganizationType_update', 'ویرایش شعبه/اداره/مجتمع/سازمان'),
            ('OrganizationType_delete', 'حــذف شعبه/اداره/مجتمع/سازمان'),
        ]
class Organization(models.Model):
    """مدل سازمان برای تعریف مجتمع‌ها و دفتر مرکزی"""
    code = models.CharField(max_length=10, unique=True, verbose_name=_("کد سازمان"))
    name = models.CharField(max_length=100, verbose_name=_("نام سازمان"))
    org_type = models.ForeignKey('OrganizationType', on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name=_("نوع سازمان"),
                                 related_name='organizations')  # اضافه کردن related_name برای وضوح

    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    is_core = models.BooleanField(default=False, verbose_name=_("دفتر مرکزی سازمان"))  # تغییر پیش‌فرض به False
    is_holding = models.BooleanField(default=False, verbose_name=_(" هلدینگ "))  # تغییر پیش‌فرض به False
    parent_organization = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='sub_organizations', verbose_name=_("سازمان والد"))
    is_independent = models.BooleanField(default=False, verbose_name=_("مستقل"))

    def clean(self):
        """اعتبارسنجی مدل برای اطمینان از منطق دفتر مرکزی"""
        from django.core.exceptions import ValidationError
        if self.is_core and self.parent_organization:
            raise ValidationError(_('دفتر مرکزی نمی‌تواند سازمان والد داشته باشد.'))
        if self.is_core:
            # بررسی وجود تنها یک دفتر مرکزی فعال
            existing_core = Organization.objects.filter(is_core=True, is_active=True).exclude(pk=self.pk)
            if existing_core.exists():
                raise ValidationError(_('فقط یک سازمان می‌تواند به‌عنوان دفتر مرکزی فعال باشد.'))

    def __str__(self):
        org_type_str = self.org_type.fname if self.org_type else _("نامشخص")
        return f"{self.code} - {self.name} ({org_type_str})"

    @property
    def org_type_code(self):
        return self.org_type.fname if self.org_type else None

    @property
    def budget_allocations(self):
        from budgets.models import BudgetAllocation
        return BudgetAllocation.objects.filter(organization=self)

    def save(self, *args, **kwargs):
        """اجرای clean قبل از ذخیره"""
        self.full_clean()  # اجرای اعتبارسنجی
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        # Assuming you have a URL pattern named 'organization_detail'
        # that takes organization's pk or code
        from django.urls import reverse
        return reverse('organization_detail', kwargs={'pk': self.pk})

    class Meta:
        verbose_name = _("سازمان")
        verbose_name_plural = _("سازمان‌ها")
        default_permissions = ()
        permissions = [
            ('Organization_add', 'افزودن سازمان برای تعریف مجتمع‌ها و دفتر مرکزی'),
            ('Organization_update', 'بروزرسانی سازمان برای تعریف مجتمع‌ها و دفتر مرکزی'),
            ('Organization_delete', 'حــذف سازمان برای تعریف مجتمع‌ها و دفتر مرکزی'),
            ('Organization_view', 'نمایش سازمان برای تعریف مجتمع‌ها و دفتر مرکزی'),
        ]
        indexes = [
            models.Index(fields=['code', 'org_type']),
        ]

class Branch(models.Model):
    code = models.CharField(max_length=10, unique=True, verbose_name=_("کد شاخه"))
    name = models.CharField(max_length=250, verbose_name=_("نام شاخه"))
    is_active = models.BooleanField(default=True, verbose_name=_("وضعیت فعال"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان ایجاد"))

    def __str__(self):
        return f'{self.name} - {self.name} - {self.is_active}'

    class Meta:
        verbose_name = _("شاخه سازمانی")
        verbose_name_plural = _("شاخه‌های سازمانی")
        default_permissions = ()
        permissions = [
            ('Branch_add', 'افزودن شاخه سازمانی'),
            ('Branch_edit', 'ویرایش شاخه سازمانی'),
            ('Branch_view', 'نمایش شاخه سازمانی'),
            ('Branch_delete', 'حــذف شاخه سازمانی'),
        ]
class Post(models.Model):
    """مدل پست سازمانی برای تعریف سلسله مراتب"""
    # BRANCH_CHOICES = (
    #     ('OPS', _('مدیرعامل')),
    #     ('FIN', _('مالی و اداری')),
    #     ('OPS', _('سرمایه گذاری')),
    #     ('OPS', _('هتلها')),
    #     ('OPS', _('دیگر واحدهای ستادی')),
    #     (None, _('بدون شاخه')),
    # )
    # BRANCH_CHOICES = (
    #     ('CEO', _('مدیرعامل')),
    #     ('FIN', _('مالی و اداری')),
    #     ('INV', _('سرمایه‌گذاری')),
    #     ('HOT', _('هتل‌ها')),
    #     ('STF', _('دیگر واحدهای ستادی')),
    #     (None, _('بدون شاخه')),
    # )
    name = models.CharField(max_length=100, verbose_name=_("نام پست"))
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, verbose_name=_("سازمان"))
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("پست والد"))
    level = models.IntegerField(default=1, verbose_name=_("سطح"))
    # branch = models.CharField(max_length=3, choices=BRANCH_CHOICES, null=True, blank=True, verbose_name=_("شاخه"))
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("شاخه"))
    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    is_active = models.BooleanField(default=True, verbose_name=_("وضعیت فعال"))
    max_change_level = models.IntegerField(default=1, verbose_name=_("حداکثر سطح تغییر(ارجاع به مرحله قبل تر)"), help_text=_("حداکثر مرحله‌ای که این پست می‌تواند تغییر دهد"))
    is_payment_order_signer = models.BooleanField(default=False,verbose_name=_("مجاز به امضای دستور پرداخت"))
    can_final_approve_factor = models.BooleanField(default=False, verbose_name=_("مجاز به تأیید نهایی فاکتور"))
    can_final_approve_tankhah = models.BooleanField(default=False, verbose_name=_("مجاز به تأیید نهایی تنخواه"))
    can_final_approve_budget = models.BooleanField(default=False, verbose_name=_("مجاز به تأیید نهایی بودجه"))

    def __str__(self):
        branch = self.branch or "بدون شاخه"
        branch_name = self.branch.name if self.branch else _('بدون شاخه')
        return f"{self.name} ({self.organization.code}) - {branch_name}"

    def get_absolute_url(self):
        return reverse('post_detail', kwargs={'pk': self.pk})

    def save(self, *args, changed_by=None, **kwargs):
        old_level = self.level if self.pk else None
        # محاسبه خودکار سطح بر اساس والد
        if self.parent:
            self.level = self.parent.level + 1
        else:
            self.level = 1
        # اطمینان از اینکه max_change_level کمتر از level نباشد
        if self.max_change_level < self.level:
            self.max_change_level = self.level
        super().save(*args, **kwargs)
        # ثبت تاریخچه تغییرات سطح
        if old_level != self.level:
            PostHistory.objects.create(
                post=self,
                changed_field='level',
                old_value=str(old_level),
                new_value=str(self.level),
                changed_by=changed_by
            )
        # به‌روزرسانی سطح فرزندان به‌صورت بازگشتی
        self._update_children_levels(changed_by=changed_by)

    def _update_children_levels(self, changed_by=None):
        """Recursively update levels of child posts."""
        children = Post.objects.filter(parent=self, is_active=True)
        for child in children:
            old_child_level = child.level
            child.level = self.level + 1
            if child.max_change_level < child.level:
                child.max_change_level = child.level
            child.save(changed_by=changed_by, update_fields=['level', 'max_change_level'])

    class Meta:
        verbose_name = _("پست سازمانی")
        verbose_name_plural = _("پست‌های سازمانی")
        default_permissions = ()
        permissions = [
            ('Post_add', 'افزودن  پست سازمانی برای تعریف سلسله مراتب'),
            ('Post_update', 'بروزرسانی پست سازمانی برای تعریف سلسله مراتب'),
            ('Post_view', 'نمایش  پست سازمانی برای تعریف سلسله مراتب'),
            ('Post_delete', 'حــذف  پست سازمانی برای تعریف سلسله مراتب'),
        ]

class UserPost(models.Model):
    """مدل اتصال کاربر به پست"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("کاربر"))
    post = models.ForeignKey(Post, on_delete=models.CASCADE, verbose_name=_("پست"))
    # ردیابی تاریخ
    start_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ شروع"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("تاریخ پایان"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))

    class Meta:
        unique_together = ('user', 'post')
        verbose_name = _("اتصال کاربر به پست")
        verbose_name_plural = _("اتصالات کاربر به پست‌ها")

        default_permissions = ()
        permissions = [
            ('UserPost_add', 'افزودن  اتصال کاربر به پست'),
            ('UserPost_update', 'بروزرسانی  اتصال کاربر به پست'),
            ('UserPost_view', 'نمایش   اتصال کاربر به پست'),
            ('UserPost_delete', 'حــذف  اتصال کاربر به پست'),
        ]

    def save(self, *args, **kwargs):
        """ذخیره اتصال کاربر به پست با مدیریت خطای Redis"""
        self.full_clean()  # اجرای اعتبارسنجی
        super().save(*args, **kwargs)
        try:
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            if channel_layer:
                from asgiref.sync import async_to_sync
                async_to_sync(channel_layer.group_send)(
                    'chart_updates',
                    {
                        'type': 'chart_update',
                        'message': f'UserPost updated for user {self.user.username}, post {self.post.name}',
                    }
                )
                logger.debug(f"[UserPost.save] پیام به‌روزرسانی چارت برای کاربر '{self.user.username}' ارسال شد")
            else:
                logger.warning("[UserPost.save] Channel layer در دسترس نیست. پیام به‌روزرسانی چارت ارسال نشد.")
        except Exception as e:
            logger.error(f"[UserPost.save] خطا در ارسال پیام به channel layer: {str(e)}", exc_info=True)
            # ادامه اجرای ذخیره بدون کرش، چون Redis برای ذخیره ضروری نیست
        logger.info(f"[UserPost.save] اتصال کاربر '{self.user.username}' به پست '{self.post.name}' با موفقیت ذخیره شد")

    def clean(self):
        """اعتبارسنجی مدل"""
        super().clean()
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(_('تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.'))
        if self.is_active and self.end_date and self.end_date < timezone.now().date():
            raise ValidationError(_('اتصال فعال نمی‌تواند تاریخ پایانی منقضی‌شده داشته باشد.'))

    def __str__(self):
        return f"{self.user.username} - {self.post.name} (از {self.start_date})"

#=================================================
class PostHistory(models.Model):
    """
    مدل تاریخچه تغییرات پست‌های سازمانی
    برای ثبت تغییرات اعمال‌شده روی پست‌ها (مثل تغییر نام، والد یا شاخه)
    """
    post = models.ForeignKey(Post,on_delete=models.CASCADE,verbose_name=_("پست سازمانی"),help_text=_("پستی که تغییر کرده است")    )
    changed_field = models.CharField(max_length=50,verbose_name=_("فیلد تغییر یافته"),help_text=_("نام فیلدی که تغییر کرده (مثل name یا parent)")    )
    old_value = models.TextField(null=True,blank=True,verbose_name=_("مقدار قبلی"),help_text=_("مقدار قبلی فیلد قبل از تغییر")    )
    new_value = models.TextField(null=True,blank=True,verbose_name=_("مقدار جدید"),help_text=_("مقدار جدید فیلد بعد از تغییر")    )
    changed_at = models.DateTimeField(        auto_now_add=True,        verbose_name=_("تاریخ و زمان تغییر"),        help_text=_("زمان ثبت تغییر به صورت خودکار")    )
    changed_by = models.ForeignKey(        CustomUser,        on_delete=models.SET_NULL,        null=True,        verbose_name=_("تغییر دهنده"),        help_text=_("کاربری که این تغییر را اعمال کرده")    )

    # غیرفعال کردن مجوزهای پیش‌فرض (add, change, delete, view)
    default_permissions = ()
    # تعریف مجوزهای سفارشی
    permissions = [
        ("view_posthistory", _("می‌تواند تاریخچه پست‌ها را مشاهده کند")),
        ("add_posthistory", _("می‌تواند تاریخچه پست‌ها را اضافه کند")),
        ("delete_posthistory", _("می‌تواند تاریخچه پست‌ها را حذف کند")),
    ]

    def __str__(self):
        return f"{self.post} - {self.changed_field} ({self.changed_at})"

    class Meta:
        verbose_name = _("تاریخچه پست")
        verbose_name_plural = _("تاریخچه پست‌ها")
        # مرتب‌سازی بر اساس زمان تغییر (جدیدترین اول)
        ordering = ['-changed_at']
        # ایندکس برای بهینه‌سازی جستجو
        permissions = [
            ("posthistory_view", _("می‌تواند تاریخچه پست‌ها را مشاهده کند")),
            ("posthistory_add", _("می‌تواند تاریخچه پست‌ها را اضافه کند")),
            ("posthistory_update", _("می‌تواند تاریخچه پست‌ها را ویرایش کند")),
            ("posthistory_delete", _("می‌تواند تاریخچه پست‌ها را حذف کند")),
        ]

        indexes = [
            models.Index(fields=['post', 'changed_at']),
        ]
#-----
class Project(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("نام پروژه"))
    code = models.CharField(max_length=80, unique=True, verbose_name=_("کد پروژه"))
    # organizations = models.ManyToManyField(Organization, limit_choices_to={'org_type': 'COMPLEX'}, verbose_name=_("مجتمع‌های مرتبط"))
    organizations = models.ManyToManyField(Organization, limit_choices_to={'org_type__is_budget_allocatable': True},
                                           # سازمان‌هایی که می‌توانند بودجه دریافت کنند
                                           verbose_name=_("سازمان‌های مرتبط"))
    # allocations = models.ManyToManyField('budgets.BudgetAllocation', blank=True, verbose_name=_("تخصیص‌های بودجه مرتبط"))
    start_date = models.DateField(verbose_name=_("تاریخ شروع"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("تاریخ پایان"))
    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    is_active = models.BooleanField(default=True, verbose_name="وضعیت فعال")
    PRIORITY_CHOICES = (('LOW', _('کم')), ('MEDIUM', _('متوسط')), ('HIGH', _('زیاد')),)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM', verbose_name=_("اولویت"))

    # total_budget = models.DecimalField(max_digits=25, decimal_places=2, default=0, verbose_name=_("بودجه کل تخصیص‌یافته"))  # فیلد جدید

    def get_total_budget(self):
        from budgets.budget_calculations import get_project_total_budget, get_project_remaining_budget, \
    get_subproject_remaining_budget
        """محاسبه کل بودجه تخصیص‌یافته به پروژه"""
        return get_project_total_budget(self)

    def get_remaining_budget(self):
        from budgets.budget_calculations import get_project_total_budget, get_project_remaining_budget, \
            get_subproject_remaining_budget
        return get_project_remaining_budget(self)

    def __str__(self):
        status = "فعال" if self.is_active else "غیرفعال"
        return f"{self.code} - {self.name} ({status})"

    class Meta:
        verbose_name = _("پروژه")
        verbose_name_plural = _("پروژه")
        default_permissions = ()
        permissions = [
            ('Project_add', 'افزودن  مجموعه پروژه'),
            ('Project_update', 'ویرایش مجموعه پروژه'),
            ('Project_view', 'نمایش مجموعه پروژه'),
            ('Project_delete', 'حــذف مجموعه پروژه'),
            # ('Project_Budget_allocation_Head_Office', 'تخصیص بودجه مجموعه پروژه(دفتر مرکزی)'),
            # ('Project_Budget_allocation_Branch', 'تخصیص بودجه مجموعه پروژه(شعبه)'),
        ]
class SubProject(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='subprojects',
                                verbose_name=_("پروژه اصلی"))
    name = models.CharField(max_length=200, verbose_name=_("نام ساب‌پروژه"))
    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    allocated_budget = models.DecimalField(max_digits=25, decimal_places=2, default=0,
                                           verbose_name=_("بودجه تخصیص‌یافته"))
    # allocations = models.ManyToManyField('budgets.ProjectBudgetAllocation',
    #                                     related_name='budget_allocations_set' ,blank=True, verbose_name=_("تخصیص‌های بودجه مرتبط"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))

    def get_remaining_budget(self):
        from budgets.budget_calculations import get_project_total_budget, get_project_remaining_budget, \
            get_subproject_remaining_budget
        return get_subproject_remaining_budget(self)

    # def get_remaining_budget(self):
    #     total_allocated = self.budget_allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
    #     consumed = BudgetTransaction.objects.filter(
    #         allocation__in=self.budget_allocations.all(),
    #         transaction_type='CONSUMPTION'
    #     ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    #     returned = BudgetTransaction.objects.filter(
    #         allocation__in=self.budget_allocations.all(),
    #         transaction_type='RETURN'
    #     ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    #     return total_allocated - consumed + returned
    #
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # به‌روزرسانی بودجه تخصیص‌یافته
        total_allocated = self.budget_allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
        self.allocated_budget = total_allocated
        super().save(update_fields=['allocated_budget'])
        if not self.pk:
            total_allocated = sum([alloc.amount for alloc in self.allocations.all()])
            if total_allocated > self.project.get_remaining_budget():
                raise ValueError("بودجه تخصیص‌یافته بیشتر از بودجه باقی‌مانده پروژه است.")

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    class Meta:
        verbose_name = _("ساب‌پروژه")
        verbose_name_plural = _("ساب‌پروژه‌ها")
        default_permissions = ()
        permissions = [
            ('SubProject_add', 'افزودن زیر مجموعه پروژه'),
            ('SubProject_update', 'ویرایش زیر مجموعه پروژه'),
            ('SubProject_view', 'نمایش زیر مجموعه پروژه'),
            ('SubProject_delete', 'حــذف زیر مجموعه پروژه'),
            ('SubProject_Head_Office', 'تخصیص زیر مجموعه پروژه(دفتر مرکزی)🏠'),
            ('SubProject_Branch', 'تخصیص  زیر مجموعه پروژه(شعبه)🏠'),
        ]

class PostAction(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='postactions',verbose_name=_("پست"))
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES, verbose_name=_("نوع اقدام"))
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPES, default='TANKHAH',verbose_name=_("نوع موجودیت"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))
    min_level = models.IntegerField(null=True, blank=True)  # حداقل سطح دسترسی (اختیاری)
    triggers_payment_order = models.BooleanField(default=False,  verbose_name=_("فعال‌سازی دستور پرداخت"))  # مشخصه دستور پرداخت کاریر
    allowed_actions = ArrayField(models.CharField(max_length=25, choices=[
        ('APPROVE', 'تأیید'),
        ('REJECT', 'رد'),
        ('STAGE_CHANGE', 'تغییر مرحله'),
        ('SIGN_PAYMENT', 'امضای دستور پرداخت')
    ]), default=list, verbose_name=_("اقدامات مجاز"))
    stage = models.ForeignKey('Status', on_delete=models.CASCADE, related_name='postactions', verbose_name=_("مرحله"))


    def __str__(self):
        # return f"{self.post} - {self.action_type} برای {self.get_entity_type_display()} در {self.stage}"
        return f"{self.post} → {self.stage} :: {self.action_type}  برای {self.get_entity_type_display()}({'✅' if self.allowed_actions else '❌'})"
        # return f"{self.post} - {self.action_type} در {self.stage}"

    class Meta:
        verbose_name = _("اقدام مجاز پست")
        verbose_name_plural = _("اقدامات مجاز پست‌ها")
        # unique_together = ('post', 'stage', 'action_type', 'entity_type')  # اضافه کردن entity_type به unique_together
        permissions = [
            ('PostAction_view', 'نمایش اقدامات مجاز پست'),
            ('PostAction_add', 'افزودن اقدامات مجاز پست'),
            ('PostAction_update', 'بروزرسانی اقدامات مجاز پست'),
            ('PostAction_delete', 'حذف اقدامات مجاز پست'),
        ]
###################### NEW Config Status For ACTIONS TYPE ENTITY TYPES #######################################
# یک کلاس پایه برای فیلدهای مشترک (ایجادکننده، تاریخ، وضعیت فعالیت)
# مدل‌ها برای پشتیبانی از تاریخچه و بازنشستگی
#
class EntityType(models.Model):
    """
    تعریف انواع موجودیت‌های اصلی در سیستم که می‌توانند گردش کار داشته باشند.
    مثال: فاکتور، تنخواه، دستور پرداخت.
    """
    name = models.CharField(max_length=100, verbose_name=_("نام موجودیت"))
    code = models.CharField(max_length=50, unique=True, help_text=_("کد منحصر به فرد انگلیسی، مانند FACTORITEM"))
    # این به ما اجازه می‌دهد تا این مدل را به مدل‌های واقعی جنگو متصل کنیم
    content_type = models.OneToOneField('contenttypes.ContentType',on_delete=models.CASCADE,null=True, blank=True, # در ابتدا می‌تواند خالی باشد
        verbose_name=_("نوع محتوای مرتبط")    )
    def __str__(self):
        return self.name
    class Meta:
        verbose_name = _("نوع موجودیت گردش کار")
        verbose_name_plural = _("۰. انواع موجودیت‌های گردش کار")
        default_permissions = ()
        permissions = [
            ('EntityType_add','افزودن نوع موجودیت گردش کار '),
            ('EntityType_update','ویرایش نوع موجودیت گردش کار '),
            ('EntityType_view','نمایش نوع موجودیت گردش کار '),
            ('EntityType_delete','حــذف نوع موجودیت گردش کار '),
        ]
class Status(models.Model):
    """
    تعریف وضعیت‌های ممکن برای موجودیت‌های مختلف در سیستم.
    مثال: پیش‌نویس، در انتظار تایید، تایید نهایی، رد شده.
    """
    name = models.CharField(max_length=100, verbose_name=_("نام وضعیت"))
    code = models.CharField(max_length=50, unique=True, help_text=_("کد منحصر به فرد انگلیسی، مانند DRAFT"))
    is_initial = models.BooleanField(default=False, verbose_name=_("آیا این وضعیت اولیه (شروع) است؟"))
    is_final_approve = models.BooleanField(default=False, verbose_name=_("وضعیت تأیید نهایی؟"))
    is_final_reject = models.BooleanField(default=False, verbose_name=_("وضعیت رد نهایی؟"))
    is_active = models.BooleanField(default=True, db_index=True, verbose_name=_("فعال"))

    # فیلدهای مشترک به صورت مستقیم اضافه شده‌اند
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT, verbose_name=_("ایجادکننده"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))

    def __str__(self):
            return self.name

    class Meta:
        verbose_name = _("وضعیت گردش کار")
        verbose_name_plural = _("۱. وضعیت‌های گردش کار")
        default_permissions = ()
        permissions = [
            ('Status_add','افزودن وضعیت'),
            ('Status_update ','ویرایش وضعیت'),
            ('Status_view ','نمایش وضعیت'),
            ('Status_delete ','حــذف وضعیت'),
        ]
class Action(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("نام اقدام"))
    code = models.CharField(max_length=50, unique=True, help_text=_("کد منحصر به فرد انگلیسی، مانند SUBMIT"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))

    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT, verbose_name=_("ایجادکننده"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    is_active = models.BooleanField(default=True, db_index=True, verbose_name=_("فعال"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("اقدام گردش کار")
        verbose_name_plural = _("۲. اقدامات گردش کار")
        default_permissions = ()
        permissions = [
            ('Action_add','افزودن اقدام گردش کار '),
            ('Action_update','ویرایش اقدام گردش کار '),
            ('Action_view','نمایش اقدام گردش کار '),
            ('Action_delete','حــذف اقدام گردش کار '),
        ]
class Transition(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("نام/شرح گذار"))
    entity_type = models.ForeignKey(EntityType, on_delete=models.PROTECT, verbose_name=_("برای نوع موجودیت"))
    from_status = models.ForeignKey(Status, on_delete=models.PROTECT, related_name='transitions_from',
                                    verbose_name=_("از وضعیت"))
    action = models.ForeignKey(Action, on_delete=models.PROTECT, verbose_name=_("با اقدام"))
    to_status = models.ForeignKey(Status, on_delete=models.PROTECT, related_name='transitions_to',
                                  verbose_name=_("به وضعیت"))
    # فیلد سازمان به اینجا منتقل می‌شود تا هر گذار مختص یک سازمان باشد
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, verbose_name=_("سازمان"))
    allowed_posts = models.ManyToManyField(
        Post,
        verbose_name=_("پست‌های مجاز"),
        help_text=_("پست‌هایی که اجازه دارند این اقدام را در این وضعیت انجام دهند.")
    )
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT, verbose_name=_("ایجادکننده"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    is_active = models.BooleanField(default=True, db_index=True, verbose_name=_("فعال"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("گذار گردش کار")
        verbose_name_plural = _("۳. گذارهای گردش کار")
        unique_together = ('organization', 'entity_type', 'from_status', 'action')
        default_permissions = ()
        permissions = [
            ('Transition_add','افزودن گذار گردش کار '),
            ('Transition_update','ویرایش گذار گردش کار '),
            ('Transition_view','نمایش گذار گردش کار '),
            ('Transition_delete','حــذف گذار گردش کار '),
        ]

##################################################### ##########################################
class SystemSettings(models.Model):
    budget_locked_percentage_default = models.DecimalField(        max_digits=5, decimal_places=2, default=0, verbose_name=_("درصد قفل‌شده پیش‌فرض بودجه"))
    budget_warning_threshold_default = models.DecimalField(max_digits=5, decimal_places=2, default=10, verbose_name=_("آستانه هشدار پیش‌فرض بودجه"))
    budget_warning_action_default = models.CharField(
        max_length=50, choices=[('NOTIFY', 'اعلان'), ('LOCK', 'قفل'), ('RESTRICT', 'محدود')],
        default='NOTIFY', verbose_name=_("اقدام هشدار پیش‌فرض بودجه"))
    allocation_locked_percentage_default = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name=_("درصد قفل‌شده پیش‌فرض تخصیص"))
    tankhah_used_statuses = models.JSONField( default=list, blank=True, verbose_name=_("وضعیت‌های مصرف‌شده تنخواه"))
    tankhah_accessible_organizations = models.JSONField(
        default=list, blank=True, verbose_name=_("سازمان‌های مجاز برای ثبت تنخواه"),
        help_text=_("لیست ID سازمان‌هایی که همه کاربران می‌توانند برای آن‌ها تنخواه ثبت کنند (مثل دفتر مرکزی)"))

    tankhah_payment_ceiling_default = models.DecimalField(max_digits=25, decimal_places=2, null=True, blank=True,
                                                          verbose_name=_("سقف پرداخت پیش‌فرض تنخواه"))
    tankhah_payment_ceiling_enabled_default = models.BooleanField(default=False,
                                                                  verbose_name=_("فعال بودن پیش‌فرض سقف پرداخت تنخواه"))

    def save(self, *args, **kwargs):
        # اطمینان از وجود تنها یک نمونه
        if not self.pk and SystemSettings.objects.exists():
            raise ValidationError(_("فقط یک نمونه از تنظیمات سیستم مجاز است."))
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("تنظیمات سیستم")
        verbose_name_plural = _("تنظیمات سیستم")

    def __str__(self):
        ceiling = f"{self.tankhah_payment_ceiling_default:,.0f}" if self.tankhah_payment_ceiling_default else "غیرفعال"
        return f"تنظیمات سیستم - سقف تنخواه: {ceiling}"

    # def __str__(self):
    #     return "تنظیمات سیستم بودجه"
############################################################# End Off models
class Dashboard_Core(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('Dashboard_Core_view', 'دسترسی به داشبورد Core پایه')
        ]
class DashboardView_flows(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('DashboardView_flows_view', 'دسترسی به روند تنخواه گردانی ')
        ]
class DashboardView(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('Dashboard__view', 'دسترسی به داشبورد اصلی 💻')
        ]
class OrganizationChartAPIView(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('OrganizationChartAPIView_view', 'دسترسی به داشبورد چارت سازمانی 💻'),

        ]
class OrganizationChartView(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('OrganizationChartView_view', '   دسترسی به گرافیک داشبورد چارت سازمانی 💻'),

        ]

class WorkflowStage(models.Model):
    ENTITY_TYPE_CHOICES = (
        ('TANKHAH', _('تنخواه')),
        ('FACTOR', _('فاکتور')),
        ('PAYMENTORDER', _('دستور پرداخت')),
    )

    name = models.CharField(max_length=100, verbose_name=_('نام مرحله'))
    order = models.PositiveIntegerField(verbose_name=_('ترتیب'), unique=True)
    description = models.TextField(blank=True, verbose_name=_('توضیحات'))
    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPE_CHOICES,
        verbose_name=_('نوع موجودیت'),
        db_index=True  # اضافه کردن ایندکس
    )
    is_active = models.BooleanField(default=True, verbose_name=_('فعال'))
    min_signatures = models.PositiveIntegerField(default=1, verbose_name=_('حداقل امضاها'))
    is_final_stage = models.BooleanField(
        default=False,
        help_text=_("آیا این مرحله نهایی برای تکمیل تنخواه است؟"),
        verbose_name=_("مرحله نهایی")
    )
    auto_advance = models.BooleanField(
        default=True,
        verbose_name=_("پیش‌رفت خودکار"),
        help_text=_("اگر فعال باشد، پس از تأیید یک مرحله، فاکتور به مرحله بعدی می‌رود.")
    )
    triggers_payment_order = models.BooleanField(
        default=False,
        verbose_name=_("فعال‌سازی دستور پرداخت"),
        help_text=_("آیا این مرحله باعث ایجاد خودکار دستور پرداخت می‌شود؟ (برای تنخواه/فاکتور)")
    )

    # def get_next_stage(self):
    #     """
    #     مرحله بعدی را بر اساس ترتیب (order) پیدا می‌کند.
    #     اگر مرحله بعدی وجود نداشته باشد، None برمی‌گرداند.
    #     """
    #     try:
    #         # مرحله با order بزرگتر از order فعلی را پیدا می‌کند
    #         # و مطمئن می‌شود که ترتیب (order) آن حداقل یک واحد بیشتر باشد
    #         return WorkflowStage.objects.get(order=self.order + 1)
    #     except WorkflowStage.DoesNotExist:
    #         return None
    #
    # def save(self, *args, **kwargs):
    #     if not self.pk and WorkflowStage.objects.filter(order=self.order).exists():
    #         raise ValueError(_("ترتیب مرحله نمی‌تواند تکراری باشد"))
    #     super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_entity_type_display()}, ترتیب: {self.order})"

    class Meta:
        verbose_name = _('مرحله گردش کار')
        verbose_name_plural = _('مراحل گردش کار')
        ordering = ['order']
        indexes = [
            models.Index(fields=['entity_type', 'is_active']),
        ]
        default_permissions = ()
        permissions = [
            ('WorkflowStage_view', 'نمایش مرحله گردش کار'),
            ('WorkflowStage_add', 'افزودن مرحله گردش کار'),
            ('WorkflowStage_update', 'بروزرسانی مرحله گردش کار'),
            ('WorkflowStage_delete', 'حذف مرحله گردش کار'),
            ('WorkflowStage_triggers_payment_order', 'فعال‌سازی دستور پرداخت - مرحله گردش کار'),
        ]
# --
class AccessRule(models.Model):
    """این مدل مشخص می‌کنه که پست‌های یک سازمان، با branch و min_level خاص، چه اقداماتی می‌تونن توی چه مراحلی برای چه موجودیت‌هایی انجام بدن."""

    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, verbose_name=_("سازمان"))
    # stage = models.ForeignKey(WorkflowStage, on_delete=models.CASCADE, verbose_name=_('مرحله'))
    stage = models.CharField(max_length=200, verbose_name=_('نام مرحله'))
    # stage_order = models.PositiveIntegerField(verbose_name=_('ترتیب مرحله'))
    stage_order = models.PositiveIntegerField(verbose_name=_('ترتیب مرحله'), null=True, blank=True)
    post = models.ForeignKey('core.Post', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('پست'),
                             help_text=_('پست مرتبط با این قانون. اگر خالی باشد، بر اساس min_level اعمال می‌شود.'))
    action_type = models.CharField(max_length=25, choices=ACTION_TYPES, verbose_name=_('نوع اقدام'))
    entity_type = models.CharField(max_length=100, choices=ENTITY_TYPES, verbose_name=_('نوع موجودیت'))
    min_level = models.IntegerField(default=1, verbose_name=_("حداقل سطح"))

    # branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True,default=None, verbose_name="شاخه")
    branch = models.ForeignKey('core.Branch', on_delete=models.SET_NULL, null=True, blank=True, default=None, verbose_name="شاخه")

    is_active = models.BooleanField(default=True, verbose_name=_('فعال'))
    min_signatures = models.PositiveIntegerField(default=1, verbose_name=_("حداقل تعداد امضا"))

    auto_advance = models.BooleanField(default=True, verbose_name=_("پیش‌رفت خودکار"))
    triggers_payment_order = models.BooleanField(default=False, verbose_name=_("فعال‌سازی دستور پرداخت"))
    is_payment_order_signer = models.BooleanField(default=False, verbose_name=_("امضاکننده دستور پرداخت"))
    is_final_stage = models.BooleanField(default=False, verbose_name=_("مرحله نهایی"))
    created_by = models.ForeignKey('accounts.CustomUser',related_name='access_rules', on_delete=models.SET_NULL, null=True, verbose_name=_("ایجادکننده"))

    class Meta:
        verbose_name = _("قانون دسترسی")
        verbose_name_plural = _("قوانین دسترسی")
        # unique_together = ('organization', 'branch', 'min_level', 'stage', 'action_type', 'entity_type')
        unique_together = ('organization', 'entity_type', 'stage_order' , 'post', 'action_type')

        default_permissions = ()
        permissions = [
            ('AccessRule_add', 'افزودن قانون دسترسی'),
            ('AccessRule_view', 'نمایش قانون دسترسی'),
            ('AccessRule_update', 'ویرایش قانون دسترسی'),
            ('AccessRule_delete', 'حــذف قانون دسترسی'),
        ]
    #
    # def save(self, *args, **kwargs):
    #     if self.stage_order and self.is_active:
    #         if AccessRule.objects.filter(
    #             organization=self.organization,
    #             entity_type=self.entity_type,
    #             stage_order=self.stage_order,
    #             is_active=True
    #         ).exclude(pk=self.pk).exists():
    #             raise ValueError(_immediate("ترتیب مرحله {stage_order} برای سازمان {org} و موجودیت {entity} قبلاً استفاده شده است.").format(
    #                 stage_order=self.stage_order,
    #                 org=self.organization,
    #                 entity=self.entity_type
    #             ))
    #     super().save(*args, **kwargs)

    # def __str__(self):
    #     return f"{self.organization} - {self.branch} - {self.action_type} - {self.entity_type}"

    # def save(self, *args, **kwargs):
    #     # بررسی یکتایی stage_order در سطح مدل، که قبلا داشتید و بسیار خوب است.
    #     # این باعث می‌شود حتی اگر از جاهای دیگر هم AccessRule ایجاد شود، تداخل پیش نیاید.
    #     if self.stage_order and self.is_active:
    #         if AccessRule.objects.filter(
    #             organization=self.organization,
    #             entity_type=self.entity_type,
    #             stage_order=self.stage_order,
    #             is_active=True
    #         ).exclude(pk=self.pk).exists():
    #             raise ValueError(_immediate("ترتیب مرحله {stage_order} برای سازمان {org} و موجودیت {entity} قبلاً استفاده شده است.").format(
    #                 stage_order=self.stage_order,
    #                 org=self.organization.name, # استفاده از .name برای نمایش بهتر
    #                 entity=self.entity_type
    #             ))
    #     super().save(*args, **kwargs)

    def __str__(self):
            return f"{self.organization} - {self.post} - {self.stage} (ترتیب: {self.stage_order}) - {self.action_type}"
