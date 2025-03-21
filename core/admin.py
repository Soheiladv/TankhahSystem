from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django_jalali.admin.filters import JDateFieldListFilter
from .models import Organization, Project, Post, UserPost, PostHistory, TimeLockModel
from accounts.models import CustomUser


# ادمین سازمان
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'org_type', 'description_short')
    list_filter = ('org_type',)
    search_fields = ('code', 'name', 'description')
    ordering = ('code',)
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'org_type')
        }),
        (_('توضیحات'), {
            'fields': ('description',),
            'classes': ('collapse',)  # قابل جمع شدن
        }),
    )

    def description_short(self, obj):
        return obj.description[:50] + '...' if obj.description and len(obj.description) > 50 else obj.description
    description_short.short_description = _('توضیحات کوتاه')


# ادمین پروژه
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'start_date', 'end_date', 'org_count')
    list_filter = (('start_date', JDateFieldListFilter), ('end_date', JDateFieldListFilter))
    search_fields = ('code', 'name', 'description')
    filter_horizontal = ('organizations',)  # ویجت برای انتخاب چندگانه
    ordering = ('-start_date',)
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'organizations', 'start_date', 'end_date')
        }),
        (_('توضیحات'), {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
    )

    def org_count(self, obj):
        return obj.organizations.count()
    org_count.short_description = _('تعداد مجتمع‌ها')


# ادمین پست سازمانی
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'parent', 'level', 'branch')
    list_filter = ('organization', 'branch', 'level')
    search_fields = ('name', 'description')
    list_select_related = ('organization', 'parent')  # بهینه‌سازی کوئری‌ها
    autocomplete_fields = ('parent',)  # جستجوی خودکار برای والد
    ordering = ('organization', 'level', 'name')
    fieldsets = (
        (None, {
            'fields': ('name', 'organization', 'parent', 'level', 'branch')
        }),
        (_('توضیحات'), {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
    )


# ادمین اتصال کاربر به پست
@admin.register(UserPost)
class UserPostAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'user_fullname')
    list_filter = ('post__organization', 'post__branch')
    search_fields = ('user__username', 'post__name')
    autocomplete_fields = ('user', 'post')
    ordering = ('user__username',)

    def user_fullname(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_fullname.short_description = _('نام کامل کاربر')


# ادمین تاریخچه پست
@admin.register(PostHistory)
class PostHistoryAdmin(admin.ModelAdmin):
    list_display = ('post', 'changed_field', 'old_value_short', 'new_value_short', 'changed_at', 'changed_by')
    list_filter = (('changed_at', JDateFieldListFilter), 'changed_field', 'post__organization')
    search_fields = ('post__name', 'changed_field', 'old_value', 'new_value', 'changed_by__username')
    ordering = ('-changed_at',)
    readonly_fields = ('changed_at',)  # فقط خواندنی
    autocomplete_fields = ('post', 'changed_by')

    def old_value_short(self, obj):
        return obj.old_value[:50] + '...' if obj.old_value and len(obj.old_value) > 50 else obj.old_value
    old_value_short.short_description = _('مقدار قبلی (کوتاه)')

    def new_value_short(self, obj):
        return obj.new_value[:50] + '...' if obj.new_value and len(obj.new_value) > 50 else obj.new_value
    new_value_short.short_description = _('مقدار جدید (کوتاه)')


# ادمین قفل سیستم
@admin.register(TimeLockModel)
class TimeLockModelAdmin(admin.ModelAdmin):
    list_display = ('hash_value', 'created_at', 'is_active', 'decrypted_expiry', 'decrypted_max_users', 'decrypted_org')
    list_filter = (('created_at', JDateFieldListFilter), 'is_active')
    search_fields = ('hash_value', 'organization_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'lock_key', 'hash_value', 'salt', 'decrypted_expiry', 'decrypted_max_users', 'decrypted_org')
    fieldsets = (
        (None, {
            'fields': ('lock_key', 'hash_value', 'salt', 'is_active', 'organization_name')
        }),
        (_('اطلاعات رمزگشایی‌شده'), {
            'fields': ('decrypted_expiry', 'decrypted_max_users', 'decrypted_org'),
            'classes': ('collapse',)
        }),
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