from .models import CustomProfile, TimeLockModel

###############################################################
from django.contrib.auth.forms import AdminPasswordChangeForm
from django_jalali.admin.filters import JDateFieldListFilter

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import Http404
from django.shortcuts import redirect, render
from django.contrib import admin
from .models import AuditLog

from accounts.models import CustomUser, Role, MyGroup, CustomUserGroup
from accounts.forms import   CustomUserCreationForm, CustomUserForm,MyGroupForm
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group
import django_filters
from django.contrib import admin
from django.contrib.auth.models import Permission

# ادمین پایه با تنظیمات مشترک
class BaseAdmin(admin.ModelAdmin):
    list_per_page = 20  # تعداد آیتم‌ها در هر صفحه
    ordering = ('-id',)  # ترتیب پیش‌فرض
    search_fields = ('name',)  # فیلد جستجوی پیش‌فرض

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'permissions_list')
    search_fields = ('name',)
    filter_horizontal = ('permissions',)

    def permissions_list(self, obj):
        return ", ".join([perm.name for perm in obj.permissions.all()])

    permissions_list.short_description = 'مجوزها'

class CustomUserGroupInline(admin.TabularInline):
    model = CustomUserGroup
    extra = 1
    verbose_name = 'کاربر'
    verbose_name_plural = 'کاربران'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "customuser":
            kwargs["queryset"] = CustomUser.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(MyGroup)
class GroupAdmin(admin.ModelAdmin):
    form = MyGroupForm
    list_display = ('name', 'role_list', 'user_count')  # اضافه کردن تعداد کاربران
    search_fields = ('name',)
    filter_horizontal = ('roles',)
    inlines = [CustomUserGroupInline, ]

    fieldsets = (
        (None, {
            'fields': ('name', 'roles', 'description')
        }),
    )

    def role_list(self, obj):
        return ", ".join([role.name for role in obj.roles.all()])
    role_list.short_description = 'نقش‌ها'

    def user_count(self, obj):
        return obj.accounts_groups_set.count()
    user_count.short_description = 'تعداد کاربران'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('roles', 'accounts_groups_set')
        return queryset

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = CustomUserForm
    add_form = CustomUserCreationForm
    change_password_form = AdminPasswordChangeForm
    inlines = [CustomUserGroupInline, ]  # مدیریت گروه‌ها از طریق مدل واسط

    list_display = ['username', 'email', 'get_groups']
    search_fields = ('username', 'email')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('اطلاعات شخصی', {'fields': ('first_name', 'last_name', 'email',)}),
        ('دسترسی‌ها', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions'),
        }),
        ('تاریخ‌های مهم', {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'email', 'password1', 'password2'),
        }),
        ('دسترسی‌ها', {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions')}),
    )

    # list_filter = ['groups']  # این خط را حذف کنید زیرا `groups` دیگر در fieldsets نیست
    filter_horizontal = ('user_permissions',)

    search_fields = ['username', 'email']

    def get_groups(self, obj):
        return ", ".join([g.name for g in obj.groups.all()])

    get_groups.short_description = 'گروه‌ها'

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'groups':
            kwargs['queryset'] = MyGroup.objects.all()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        return super().get_form(request, obj, **kwargs)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<id>/password/', self.admin_site.admin_view(self.change_password), name='customuser_change_password'),
        ]
        return custom_urls + urls

    def change_password(self, request, id):
        user = self.get_object(request, id)
        if not user:
            return Http404()
        if request.method == 'POST':
            form = AdminPasswordChangeForm(user, request.POST)
            if form.is_valid():
                form.save()
                return redirect('..')
        else:
            form = AdminPasswordChangeForm(user)
        context = {'form': form, 'title': 'تغییر رمز عبور'}
        return render(request, 'admin/auth/user/change_password.html', context)

@admin.register(CustomProfile)
class CustomProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'city', 'phone_number')
    search_fields = ('user__username', 'first_name', 'last_name', 'phone_number')
    list_filter = ('city',)
    fieldsets = (
        (None, {'fields': ('user',)}),
        ('اطلاعات شخصی', {'fields': ('first_name', 'last_name', 'birth_date')}),
        ('اطلاعات تماس', {'fields': ('phone_number', 'address', 'zip_code')}),
        ('سایر اطلاعات', {'fields': ('city', 'description', 'location', 'bio')}),
    )
    raw_id_fields = ('user', 'city')

admin.site.unregister(Group)
##########################  Auth Permission
class PermissionFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    codename = django_filters.CharFilter(lookup_expr='icontains')
    app_label = django_filters.CharFilter(field_name='content_type__app_label', lookup_expr='icontains')
    model = django_filters.CharFilter(field_name='content_type__model', lookup_expr='icontains')

    class Meta:
        model = Permission
        fields = ['name', 'codename', 'app_label', 'model']

class PermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'codename', 'content_type', 'app_label')
    search_fields = ['name', 'codename', 'content_type__app_label', 'content_type__model']
    list_filter = ('content_type__app_label', 'content_type__model')

    # تابع برای نمایش app_label
    def app_label(self, obj):
        return obj.content_type.app_label

    app_label.short_description = 'Application'

    def get_list_filter(self, request):
        # حذف تغییرات اعمال شده برای PermissionFilter
        return ['content_type__app_label', 'content_type__model']

    def get_queryset(self, request):
        # اعمال فیلترهای پیشرفته به queryset در اینجا
        qs = super().get_queryset(request)
        filter_instance = PermissionFilter(request.GET, queryset=qs)
        return filter_instance.qs

admin.site.register(Permission, PermissionAdmin)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'object_id', 'timestamp', 'ip_address', 'browser', 'status_code')
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('user__username', 'model_name', 'object_id')
    readonly_fields = ('user', 'action', 'model_name', 'object_id', 'timestamp', 'details', 'ip_address', 'browser', 'status_code')

# ادمین قفل سیستم
@admin.register(TimeLockModel)
class TimeLockModelAdmin(BaseAdmin):
    list_display = ('hash_value', 'created_at', 'is_active', 'decrypted_expiry', 'decrypted_max_users', 'decrypted_org')
    list_filter = (('created_at', JDateFieldListFilter), 'is_active')
    search_fields = ('hash_value', 'organization_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'lock_key', 'hash_value', 'salt', 'decrypted_expiry', 'decrypted_max_users', 'decrypted_org')
    fieldsets = (
        (None, {'fields': ('lock_key', 'hash_value', 'salt', 'is_active', 'organization_name')}),
        (_('اطلاعات رمزگشایی‌شده'), {'fields': ('decrypted_expiry', 'decrypted_max_users', 'decrypted_org'), 'classes': ('collapse',)}),
    )

    def decrypted_expiry(self, obj):
        return obj.get_decrypted_expiry_date()
    decrypted_expiry.short_description = _('تاریخ انقضا')

    def decrypted_max_users(self, obj):
        return obj.get_decrypted_max_users()
    decrypted_max_users.short_description = _('حداکثر کاربران')

    def decrypted_org(self, obj):
        return obj.get_decrypted_organization_name()
    decrypted_org.short_description = _('نام سازمان')

