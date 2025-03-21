import datetime
import logging

from django.utils.timezone import now

logger = logging.getLogger(__name__)
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Permission, AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_jalali.db import models as jmodels
import hashlib

class Province(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("نام استان"))

    class Meta:
        verbose_name = _("استان")
        verbose_name_plural = _("استان‌ها")
        default_permissions = []  # جلوگیری از ایجاد permissions پیش‌فرض
        permissions = [
            ("Province_view_customuser", _("می‌تواند استان را مشاهده کند")),
            ("Province_add_customuser", _("می‌تواند استان  جدید اضافه کند")),
            ("Province_change_customuser", _("می‌تواند استان را تغییر دهد")),
            ("Province_delete_customuser", _("می‌تواند استان را حذف کند")),
        ]

    def __str__(self):
        return self.name

class City(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("نام شهر"))
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name="cities", verbose_name=_("استان"))

    class Meta:
        verbose_name = _("شهر")
        verbose_name_plural = _("شهرها")
        # unique_together = ('name', 'province')  # تعریف unique_together
        default_permissions = []  # جلوگیری از ایجاد permissions پیش‌فرض
        permissions = [
            ("City_view_customuser", _(" شهــر را مشاهده کند")),
            ("City_add_customuser", _(" شهــر  جدید اضافه کند")),
            ("City_change_customuser", _(" شهــر را تغییر دهد")),
            ("City_delete_customuser", _(" شهــر را حذف کند")),
        ]

    def __str__(self):
        return f"{self.name} - {self.province.name}"

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("ایمیل باید وارد شود"))
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('سوپرکاربر باید is_staff=True باشد.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('سوپرکاربر باید is_superuser=True باشد.'))

        return self.create_user(username, email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    roles = models.ManyToManyField('Role', related_name="custom_users", verbose_name=_("نقش‌ها"), blank=True)
    groups = models.ManyToManyField('MyGroup', through='CustomUserGroup', related_name='accounts_groups_set',
                                    verbose_name=_('عضویت در گروه'), blank=True)

    objects = CustomUserManager()

    username = models.CharField(max_length=150, unique=True, verbose_name=_('نام کاربری'))
    email = models.EmailField(unique=True, verbose_name=_('ایمیل کاربر'))

    first_name = models.CharField(max_length=30, blank=True, verbose_name=_('نام کوچک'))
    last_name = models.CharField(max_length=150, blank=True, verbose_name=_('فامیلی'))
    is_active = models.BooleanField(default=True, verbose_name=_('فعالیت'))
    is_staff = models.BooleanField(default=False, verbose_name=_('کارمندی؟'))

    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        related_name='accounts_user_set',  # تغییر این خطا
        help_text='مجوزهای خاص برای این کاربر.',
        related_query_name='user',
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = _("کاربر سفارشی")
        verbose_name_plural = _("کاربران سفارشی")
        # db_table = 'accounts_customuser_users'
        default_permissions = []  # جلوگیری از ایجاد permissions پیش‌فرض
        permissions = [
            ("users_view_customuser", _("می‌تواند کاربران سفارشی را مشاهده کند")),
            ("users_add_customuser", _("می‌تواند کاربر سفارشی جدید اضافه کند")),
            ("users_change_customuser", _("می‌تواند کاربر سفارشی را تغییر دهد")),
            ("users_delete_customuser", _("می‌تواند کاربر سفارشی را حذف کند")),
        ]

    def __str__(self):
        return self.username

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username
        # return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    def has_perm(self, perm, obj=None):
        if self.is_active and self.is_superuser:
            return True

        # بررسی مجوزها از طریق نقش‌های گروه‌های سفارشی
        for group in self.groups.all():
            for role in group.roles.all():
                if perm in role.permissions.values_list('codename', flat=True):
                    return True

        # بررسی مجوزهای مستقیم کاربر
        if perm in self.user_permissions.values_list('codename', flat=True):
            return True

        return False

    def get_all_permissions(self, obj=None):
        if not self.is_active or self.is_superuser:
            return set()

        perms = set()
        for group in self.groups.all():
            for role in group.roles.all():
                perms.update(role.permissions.values_list('codename', flat=True))
        perms.update(self.user_permissions.values_list('codename', flat=True))
        return perms

User = get_user_model()

class CustomProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile",
                                verbose_name=_("کاربر"))
    first_name = models.CharField(max_length=30, blank=True, verbose_name=_("نام"))
    last_name = models.CharField(max_length=30, blank=True, verbose_name=_("نام خانوادگی"))
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name="profiles",
                             verbose_name=_("شهر"))
    phone_number = models.CharField(max_length=15, blank=True, verbose_name=_("شماره تلفن"))
    # birth_date = models.DateField(null=True, blank=True, verbose_name=_("تاریخ تولد"))
    birth_date = jmodels.jDateField(null=True, blank=True, verbose_name="تاریخ تولد")
    address = models.TextField(blank=True, verbose_name=_("آدرس"))
    location = models.TextField(blank=True, verbose_name=_("موقعیت"))
    bio = models.TextField(blank=True, verbose_name=_("بیوگرافی"))
    zip_code = models.CharField(max_length=10, blank=True, verbose_name=_("کد پستی"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))

    class Meta:
        verbose_name = _("ساخت پروفایل سفارشی")
        verbose_name_plural = _("ساخت پروفایل سفارشی")

        default_permissions = []  # جلوگیری از ایجاد permissions پیش‌فرض
        permissions = [
            ("users_view_userprofile", _("می‌تواند پروفایل کاربران را مشاهده کند")),
            ("users_add_userprofile", _("می‌تواند پروفایل کاربری اضافه دهد")),
            ("users_update_userprofile", _("می‌تواند پروفایل کاربر را تغییر دهد")),
            ("users_delete_userprofile", _("می‌تواند پروفایل کاربر را غیرفعال کرد")),
            ("users_Search_userprofile", _("می‌تواند پروفایل کاربر را جستجو کند")),
        ]

    def __str__(self):
        return f'{self.user.username} {_("پروفایل کاربری")}'

class Role(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name=_("عنوان نقش"))
    permissions = models.ManyToManyField(Permission, blank=True, verbose_name=_("مجوزها"), related_name='roles')
    description = models.TextField(max_length=400, blank=True, null=True, verbose_name=_("توضیحات نقش"))
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children',
                               verbose_name=_("نقش والدین"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال"))

    class Meta:
        verbose_name = _("نقش")
        verbose_name_plural = _("نقش‌ها")
        ordering = ["name"]
        default_permissions = []  # جلوگیری از ایجاد permissions پیش‌فرض
        permissions = [
            ('Role_create', _('می‌تواند نقش جدید ایجاد کند')),
            ('Role_view', _('می‌تواند نقش‌ها را مشاهده کند')),
            ('Role_modify', _('می‌تواند نقش را تغییر دهد')),
            ('Role_delete ', _('می‌تواند نقش را حذف کند')),
        ]

    def __str__(self):
        return self.name

class MyGroup(models.Model):  # استفاده از نام متفاوت به جای Group
    name = models.CharField(max_length=150, unique=True, verbose_name=_("نام گروه"))
    roles = models.ManyToManyField('Role', related_name='mygroups', blank=True, verbose_name=_("تعریف نقش"))
    # users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="accounts_groups", verbose_name=_("کاربران"),blank=True)
    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاریخ ویرایش"))

    class Meta:
        db_table = 'accounts_mygroups'
        default_permissions = []  # جلوگیری از ایجاد permissions پیش‌فرض
        permissions = [
            ("MyGroup_can_view_group", "می‌تواند گروه‌ها را مشاهده کند"),
            ("MyGroup_can_add_group", "می‌تواند گروه جدید اضافه کند"),
            ("MyGroup_can_edit_group", "می‌تواند گروه را ویرایش کند"),
            ("MyGroup_can_delete_group", "می‌تواند گروه را حذف کند"),
        ]

        verbose_name = _("گروه")
        verbose_name_plural = _("گروه‌ها")
        ordering = ["name"]

    def __str__(self):
        return self.name

class CustomUserGroup(models.Model):
    customuser = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    mygroup = models.ForeignKey('MyGroup', on_delete=models.CASCADE)

    class Meta:
        db_table = 'accounts_customuser_groups'
        verbose_name = 'افزودن کاربری'
        verbose_name_plural = 'افزودن کاربری'

class AuditLog(models.Model):
    """لاگ گیری سیستمی"""
    ACTION_CHOICES = [
        ('create', 'افزودن'),
        ('read', 'نمایش'),
        ('update', 'بروزرسانی'),
        ('delete', 'حــذف'),
    ]

    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('کاربر'))
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('کاربر'))
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name=_('عملیات کاربری'))
    view_name = models.CharField(max_length=255, verbose_name=_('نام ویو'))  # نام ویو
    path = models.CharField(max_length=255, verbose_name=_('مسیر درخواست'))  # مسیر درخواست
    method = models.CharField(max_length=10, verbose_name=_('متد HTTP'))  # متد HTTP (GET, POST, etc.)
    model_name = models.CharField(max_length=255, verbose_name=_('نام مدل'))
    object_id = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('ابجکت'))
    timestamp = models.DateTimeField(default=timezone.now, verbose_name=_('زمان رخداد'))
    details = models.TextField(blank=True, verbose_name=_('ریزمشخصات'))
    changes = models.JSONField(null=True, blank=True, verbose_name=_('تغییرات'))  # ذخیره تغییرات به‌صورت JSON
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('آدرس IP'))
    browser = models.CharField(max_length=255, blank=True, verbose_name=_('بروزر'))
    status_code = models.IntegerField(null=True, blank=True, verbose_name=_('وضعیت کد'))
    related_object = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('شیء مرتبط'))
    # aliname= models.CharField(max_length=30)
    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name} - {self.timestamp}"

    class Meta:
        db_table = 'accounts_audit_log'
        verbose_name = _("لاگ گیری از سیستم")
        verbose_name_plural = _("لاگ گیری از سیستم")
        ordering = ["-timestamp"]  # نمایش آخرین رکوردها ابتدا
        default_permissions = []  # جلوگیری از ایجاد permissions پیش‌فرض
        permissions = [
            ('AuditLog_view', _('می‌تواند لاگ‌ها را مشاهده کند')),
            ('AuditLog_add', _('می‌تواند لاگ‌ها را اضافه کند')),
            ('AuditLog_update', _('می‌تواند لاگ‌ها را بروزرسانی کند')),
            ('AuditLog_delete', _('می‌تواند لاگ‌ها را حذف کند')),
        ]
####
class ActiveUser(models.Model):
    """
        مدل برای ردیابی کاربران فعال در سیستم
        این مدل اطلاعات ورود، فعالیت و محدودیت‌های کاربران را مدیریت می‌کند.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='active_sessions',
        related_query_name='active_session',
        verbose_name=_("کاربر"),
        help_text=_("کاربری که این سشن به او تعلق دارد"),
    )
    session_key = models.CharField(
        max_length=40,
        unique=False,
        blank=False,
        null=False,
        verbose_name=_("کلید سشن"),
        help_text=_("شناسه یکتا برای سشن کاربر"),
        db_index=True,  # ایندکس برای جستجوی سریع‌تر
    )
    login_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("زمان ورود"),
        help_text=_("زمان ورود کاربر به سیستم"),
        db_index=True,
    )
    hashed_count = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name=_("هش تعداد کاربران"),
        help_text=_("هش تعداد کاربران فعال برای امنیت بیشتر"),
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name=_("آخرین فعالیت"),
        help_text=_("آخرین زمان فعالیت کاربر"),
        db_index=True,
    )
    user_ip = models.GenericIPAddressField(
        protocol='both',  # پشتیبانی از IPv4 و IPv6
        unpack_ipv4=False,
        verbose_name=_("آی‌پی کاربر"),
        blank=True,
        null=True,
        help_text=_("آدرس IP کاربر در زمان ورود"),
    )
    user_agent = models.TextField(
        verbose_name=_("مرورگر/دستگاه کاربر"),
        blank=True,
        null=True,
        help_text=_("اطلاعات مرورگر یا دستگاه کاربر"),
        default='',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("فعال"),
        help_text=_("آیا این سشن هنوز فعال است؟"),
    )
    logout_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("زمان خروج"),
        help_text=_("زمان خروج کاربر از سیستم، در صورت ثبت"),
    )

    # ثابت‌های مدل (Constants)
    # MAX_ACTIVE_USERS = 5  # حداکثر تعداد کاربران مجاز (قابل تنظیم)
    MAX_ACTIVE_USERS = getattr(settings, 'MAX_ACTIVE_USERS', 2)  # از تنظیمات می‌خونه یا پیش‌فرض 5

    class Meta:
        # نام‌های نمایشی
        verbose_name = _("کاربر فعال")
        verbose_name_plural = _("کاربران فعال")
        # مجوزها
        default_permissions = []  # غیرفعال کردن مجوزهای پیش‌فرض
        permissions = [
            ('activeuser_view', _('نمایش تعداد کاربر دارای مجوز برای کار در سیستم')),
            ('activeuser_add', _('افزودن تعداد کاربر دارای مجوز برای کار در سیستم')),
            ('activeuser_update', _('آپدیت تعداد کاربر دارای مجوز برای کار در سیستم')),
            ('activeuser_delete', _('حذف تعداد کاربر دارای مجوز برای کار در سیستم')),
        ]
        # ایندکس‌ها
        indexes = [
            models.Index(fields=['user', 'session_key'], name='idx_user_session'),
            models.Index(fields=['last_activity'], name='idx_last_activity'),
        ]

        # محدودیت‌ها (Constraints)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'session_key'],
                name='unique_user_session',
                violation_error_message=_("هر کاربر تنها می‌تواند یک سشن با کلید مشخص داشته باشد.")
            ),
            models.CheckConstraint(
                check=models.Q(login_time__lte=models.F('last_activity')),
                name='check_login_before_activity',
                violation_error_message=_("زمان ورود باید قبل از آخرین فعالیت باشد.")
            ),
        ]

        # تنظیمات مرتب‌سازی
        ordering = ['-last_activity', 'user']

        # تنظیمات دیتابیس
        # db_table = 'active_users'  # نام جدول در دیتابیس
        # db_tablespace = 'active_users_space'  # فضای جدول (در صورت استفاده از دیتابیس خاص)
        managed = True  # آیا جنگو جدول را مدیریت کند؟
        app_label = 'accounts'  # نام اپلیکیشن (در صورت نیاز به تعیین دستی)

        # سایر تنظیمات متا
        get_latest_by = 'last_activity'  # برای متد latest()
        abstract = False  # مدل انتزاعی نیست
        swappable = False  # مدل قابل تعویض نیست

    @classmethod
    def remove_inactive_users(cls):
        """پاکسازی کاربران غیرفعال و حذف سشن‌های قدیمی"""
        inactivity_threshold = now() - datetime.timedelta(minutes=30)  # ۳۰ دقیقه
        inactive_users = cls.objects.filter(last_activity__lt=inactivity_threshold)
        if inactive_users.exists():
            for user in inactive_users:
                # logger.warning(f"حذف کاربر غیرفعال: {user.user.username} (آی‌پی: {user.user_ip})")
                from django.contrib.sessions.models import Session
                Session.objects.filter(session_key=user.session_key).delete()
                user.delete()
        # else:
        #     logger.info("هیچ کاربر غیرفعالی برای حذف یافت نشد.")


    @classmethod
    def delete_expired_sessions(cls):
        """حذف سشن‌های منقضی شده از دیتابیس"""
        from django.contrib.sessions.models import Session
        expired_sessions = Session.objects.filter(expire_date__lt=now())
        for session in expired_sessions:
            cls.objects.filter(session_key=session.session_key).delete()
            session.delete()



    def save(self, *args, **kwargs):
        """هش کردن تعداد کاربران فعال"""
        active_count = ActiveUser.objects.count()
        self.last_activity = now()  # همیشه آخرین فعالیت را به‌روزرسانی کن
        self.hashed_count = hashlib.sha256(str(active_count).encode()).hexdigest()
        super().save(*args, **kwargs)

    @classmethod
    def can_login(cls, session_key):
        """بررسی اینکه آیا کاربر جدید می‌تونه وارد بشه"""
        current_count = cls.objects.count()
        return current_count < cls.MAX_ACTIVE_USERS

    def __str__(self):
        return f"{self.user.username} - {self.session_key} - {self.login_time}"
############# Security Lock