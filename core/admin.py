from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django_jalali.admin.filters import JDateFieldListFilter
from .models import Organization, Project, Post, UserPost, PostHistory
from tankhah.models import WorkflowStage


# تابع کمکی برای کوتاه کردن متن
def truncate_text(text, max_length=50):
    return text[:max_length] + '...' if text and len(text) > max_length else text


# ادمین پایه با تنظیمات مشترک
class BaseAdmin(admin.ModelAdmin):
    list_per_page = 20  # تعداد آیتم‌ها در هر صفحه
    ordering = ('-id',)  # ترتیب پیش‌فرض
    search_fields = ('name',)  # فیلد جستجوی پیش‌فرض


# ادمین سازمان
@admin.register(Organization)
class OrganizationAdmin(BaseAdmin):
    list_display = ('code', 'name', 'org_type', 'description_short', 'parent_organization')
    list_filter = ('org_type',)
    search_fields = ('code', 'name', 'description')
    ordering = ('code',)
    fieldsets = (
        (None, {'fields': ('code', 'name', 'org_type' ,'parent_organization')}),
        (_('توضیحات'), {'fields': ('description',), 'classes': ('collapse',)}),
    )

    def description_short(self, obj):
        return truncate_text(obj.description)
    description_short.short_description = _('توضیحات کوتاه')


# ادمین پروژه
@admin.register(Project)
class ProjectAdmin(BaseAdmin):
    list_display = ('code', 'name', 'start_date', 'end_date',  'org_count')
    list_filter = (('start_date', JDateFieldListFilter), ('end_date', JDateFieldListFilter))
    search_fields = ('code', 'name', 'description')
    filter_horizontal = ('organizations',)
    ordering = ('-start_date',)
    fieldsets = (
        (None, {'fields': ('code',  'name', 'organizations', 'start_date', 'end_date')}),
        (_('توضیحات'), {'fields': ('description',), 'classes': ('collapse',)}),
    )

    def org_count(self, obj):
        return obj.organizations.count()
    org_count.short_description = _('تعداد مجتمع‌ها')


# ادمین پست سازمانی
@admin.register(Post)
class PostAdmin(BaseAdmin):
    list_display = ('name', 'organization', 'parent', 'level', 'branch')
    list_filter = ('organization', 'branch', 'level')
    search_fields = ('name', 'description')
    list_select_related = ('organization', 'parent')
    autocomplete_fields = ('parent',)
    ordering = ('organization', 'level', 'name')
    fieldsets = (
        (None, {'fields': ('name', 'organization', 'parent', 'level', 'branch')}),
        (_('توضیحات'), {'fields': ('description',), 'classes': ('collapse',)}),
    )


# ادمین اتصال کاربر به پست
@admin.register(UserPost)
class UserPostAdmin(BaseAdmin):
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
class PostHistoryAdmin(BaseAdmin):
    list_display = ('post', 'changed_field', 'old_value_short', 'new_value_short', 'changed_at', 'changed_by')
    list_filter = (('changed_at', JDateFieldListFilter), 'changed_field', 'post__organization')
    search_fields = ('post__name', 'changed_field', 'old_value', 'new_value', 'changed_by__username')
    ordering = ('-changed_at',)
    readonly_fields = ('changed_at',)
    autocomplete_fields = ('post', 'changed_by')

    def old_value_short(self, obj):
        return truncate_text(obj.old_value)
    old_value_short.short_description = _('مقدار قبلی (کوتاه)')

    def new_value_short(self, obj):
        return truncate_text(obj.new_value)
    new_value_short.short_description = _('مقدار جدید (کوتاه)')


# ادمین مراحل گردش کار
@admin.register(WorkflowStage)
class WorkflowStageAdmin(BaseAdmin):
    list_display = ('name', 'order', 'description_short')
    search_fields = ('name', 'description')
    ordering = ('order',)

    def description_short(self, obj):
        return truncate_text(obj.description)
    description_short.short_description = _('توضیحات کوتاه')