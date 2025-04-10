# Create your models here.
import datetime
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import CustomUser


class Organization(models.Model):
    """مدل سازمان برای تعریف مجتمع‌ها و دفتر مرکزی"""
    ORG_TYPES = (
        ('COMPLEX', _('مجتمع')),
        ('HOTEL', _('هتل')),
        ('PROVINCE', _('دفاتر استانی')),
        ('RENTAL', _('مجموعه‌های استیجاری')),
        ('HQ', _('دفتر مرکزی')),
    )
    code = models.CharField(max_length=10, unique=True, verbose_name=_("کد سازمان"))
    name = models.CharField(max_length=100, verbose_name=_("نام سازمان"))
    org_type = models.CharField(max_length=25, choices=ORG_TYPES, verbose_name=_("نوع سازمان"))
    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))

    def __str__(self):
        return f"{self.code} - {self.name} ({self.org_type})"

    class Meta:
        verbose_name = _("سازمان")
        verbose_name_plural = _("سازمان‌ها")

        default_permissions =()
        permissions = [
            ('Organization_add','افزودن سازمان برای تعریف مجتمع‌ها و دفتر مرکزی'),
            ('Organization_update','بروزرسانی سازمان برای تعریف مجتمع‌ها و دفتر مرکزی'),
            ('Organization_delete','حــذف سازمان برای تعریف مجتمع‌ها و دفتر مرکزی'),
            ('Organization_view','نمایش سازمان برای تعریف مجتمع‌ها و دفتر مرکزی'),
        ]
        indexes = [
            models.Index(fields=['code', 'org_type']),
        ]
class Project(models.Model):
    """مدل پروژه برای مدیریت پروژه‌های چندمجتمعی"""
    priority_CHOICES = (
        ('LOW', _('کم')), ('MEDIUM', _('متوسط')), ('HIGH', _('زیاد')),
    )
    name = models.CharField(max_length=100, verbose_name=_("نام پروژه"))
    code = models.CharField(max_length=80, unique=True, verbose_name=_("کد پروژه"))
    organizations = models.ManyToManyField(Organization, limit_choices_to={'org_type': 'COMPLEX'}, verbose_name=_("مجتمع‌های مرتبط"))
    start_date = models.DateField(verbose_name=_("تاریخ شروع"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("تاریخ پایان"))
    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    budget = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name=_("بودجه (ریال)"))
    is_active = models.BooleanField(default=True, verbose_name="وضعیت فعال")
    priority = models.CharField(max_length=10, choices=priority_CHOICES, null=True, blank=True, verbose_name=_("اولویت"))

    def __str__(self):
        status = "فعال" if self.is_active else "غیرفعال"
        return f"{self.code} - {self.name} ({status})"

    def save(self, *args, **kwargs):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("پروژه")
        verbose_name_plural = _("پروژه‌ها")
        default_permissions =()
        permissions = [
            ('Project_add','افزودن  پروژه برای مدیریت پروژه‌های چندمجتمعی'),
            ('Project_update','بروزرسانی  پروژه برای مدیریت پروژه‌های چندمجتمعی'),
            ('Project_view','نمایش  پروژه برای مدیریت پروژه‌های چندمجتمعی'),
            ('Project_delete','حــذف  پروژه برای مدیریت پروژه‌های چندمجتمعی'),
            ]

class SubProject(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='subprojects', verbose_name=_("پروژه اصلی"))
    name = models.CharField(max_length=200, verbose_name=_("نام ساب‌پروژه"))
    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))

    class Meta:
        verbose_name = _("ساب‌پروژه")
        verbose_name_plural = _("ساب‌پروژه‌ها")
        default_permissions =()
        permissions = [
            ('SubProject_add','افزودن زیر مجموعه پروژه'),
            ('SubProject_update','ویرایش زیر مجموعه پروژه'),
            ('SubProject_view','نمایش زیر مجموعه پروژه'),
            ('SubProject_delete','حــذف زیر مجموعه پروژه'),
        ]
    def __str__(self):
        return f"{self.project.name} - {self.name}"

class Post(models.Model):
    """مدل پست سازمانی برای تعریف سلسله مراتب"""
    BRANCH_CHOICES = (
        ('OPS', _('بهره‌برداری')),
        ('FIN', _('مالی و اداری')),
        (None, _('بدون شاخه')),
    )
    name = models.CharField(max_length=100, verbose_name=_("نام پست"))
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, verbose_name=_("سازمان"))
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("پست والد"))
    level = models.IntegerField(default=1, verbose_name=_("سطح"))
    branch = models.CharField(max_length=3, choices=BRANCH_CHOICES, null=True, blank=True, verbose_name=_("شاخه"))
    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    is_active = models.BooleanField(default=True, verbose_name=_("وضعیت فعال"))
    max_change_level = models.IntegerField(default=1, verbose_name=_("حداکثر سطح تغییر(ارجاع به مرحله قبل تر)"), help_text=_("حداکثر مرحله‌ای که این پست می‌تواند تغییر دهد"))

    def __str__(self):
        branch = self.branch or "بدون شاخه"
        return f"{self.name} ({self.organization.code}) - {branch}"

    def save(self, *args, **kwargs):
        if self.parent:
            self.level = self.parent.level + 1
        else:
            self.level = 1
        # مطمئن می‌شیم max_change_level از level کمتر نباشه
        if self.max_change_level < self.level:
            self.max_change_level = self.level
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("پست سازمانی")
        verbose_name_plural = _("پست‌های سازمانی")
        default_permissions =()
        permissions = [
            ('Post_add','افزودن  پست سازمانی برای تعریف سلسله مراتب'),
            ('Post_update','بروزرسانی پست سازمانی برای تعریف سلسله مراتب'),
            ('Post_view','نمایش  پست سازمانی برای تعریف سلسله مراتب'),
            ('Post_delete','حــذف  پست سازمانی برای تعریف سلسله مراتب'),
            ]

class UserPost(models.Model):
    """مدل اتصال کاربر به پست"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("کاربر"))
    post = models.ForeignKey(Post, on_delete=models.CASCADE, verbose_name=_("پست"))
    # ردیابی تاریخ
    start_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ شروع"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("تاریخ پایان"))

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

    def __str__(self):
        return f"{self.user.username} - {self.post.name} (از {self.start_date})"
class PostHistory(models.Model):
    """
    مدل تاریخچه تغییرات پست‌های سازمانی
    برای ثبت تغییرات اعمال‌شده روی پست‌ها (مثل تغییر نام، والد یا شاخه)
    """
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        verbose_name=_("پست سازمانی"),
        help_text=_("پستی که تغییر کرده است")
    )
    changed_field = models.CharField(
        max_length=50,
        verbose_name=_("فیلد تغییر یافته"),
        help_text=_("نام فیلدی که تغییر کرده (مثل name یا parent)")
    )
    old_value = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("مقدار قبلی"),
        help_text=_("مقدار قبلی فیلد قبل از تغییر")
    )
    new_value = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("مقدار جدید"),
        help_text=_("مقدار جدید فیلد بعد از تغییر")
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاریخ و زمان تغییر"),
        help_text=_("زمان ثبت تغییر به صورت خودکار")
    )
    changed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("تغییر دهنده"),
        help_text=_("کاربری که این تغییر را اعمال کرده")
    )

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
#--
class WorkflowStage(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('نام مرحله'))
    order = models.IntegerField(verbose_name=_('ترتیب'))
    description = models.TextField(blank=True, verbose_name=_('توضیحات'))
    is_active = models.BooleanField(default=True, verbose_name=_("وضعیت فعال"))
    is_final_stage = models.BooleanField(default=False, help_text="آیا این مرحله نهایی برای تکمیل تنخواه است؟", verbose_name=_("تعیین مرحله آخر"))

    def save(self, *args, **kwargs):
        if WorkflowStage.objects.exclude(pk=self.pk).filter(order=self.order).exists():
            raise ValueError("ترتیب مرحله نمی‌تواند تکراری باشد")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (مرحله {self.order})"

    class Meta:
        verbose_name = _('مرحله گردش کار')
        verbose_name_plural = _('مراحل گردش کار')
        ordering = ['order']
        default_permissions = ()
        permissions = [
            ('WorkflowStage_view','نمایش مرحله گردش کار'),
            ('WorkflowStage_add','افزودن مرحله گردش کار'),
            ('WorkflowStage_update','بروزرسانی مرحله گردش کار'),
            ('WorkflowStage_delete','حــذف مرحله گردش کار'),
        ]

# lock -------
import logging
logger = logging.getLogger(__name__)
############################################################# End Off models
class Dashboard_Core(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('Dashboard_Core_view','دسترسی به داشبورد Core پایه')
        ]

class DashboardView_flows(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('DashboardView_flows_view','دسترسی به روند تنخواه گردانی ')
        ]

class DashboardView(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('Dashboard__view','دسترسی به داشبورد اصلی 💻')
        ]
