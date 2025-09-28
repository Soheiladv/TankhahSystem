from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django_jalali.admin.filters import JDateFieldListFilter
from core.models import Organization, OrganizationType, Project, Post, UserPost, PostHistory, \
    SystemSettings, Branch, Transition, Action, EntityType, Status, PostAction, PostRuleAssignment, UserRuleOverride, DynamicConfiguration

# AccessRule و WorkflowStage حذف شده‌اند - از Transition, Action, EntityType, Status استفاده می‌شود

# تابع کمکی برای کوتاه کردن متن
def truncate_text(text, max_length=50):
    if text and len(text) > max_length:
        return text[:max_length] + "..."
    return text

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'org_type', 'is_active')
    list_filter = ('org_type', 'is_active', 'is_core', 'is_holding')
    search_fields = ('name', 'code')
    ordering = ('name',)

@admin.register(OrganizationType)
class OrganizationTypeAdmin(admin.ModelAdmin):
    list_display = ('fname', 'org_type', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('fname', 'org_type')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'level', 'is_active')
    list_filter = ('organization', 'level', 'is_active')
    search_fields = ('name', 'organization__name')
    ordering = ('organization', 'level', 'name')

@admin.register(UserPost)
class UserPostAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'start_date', 'end_date', 'is_active')
    list_filter = ('post__organization', 'is_active', 'start_date', 'end_date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'post__name')
    date_hierarchy = 'start_date'

@admin.register(PostHistory)
class PostHistoryAdmin(admin.ModelAdmin):
    list_display = ('post', 'changed_field', 'changed_at', 'changed_by')
    list_filter = ('post__organization', 'changed_field', 'changed_at')
    search_fields = ('post__name', 'changed_field', 'changed_by__username')

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')

@admin.register(Transition)
class TransitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'entity_type', 'from_status', 'action', 'to_status', 'organization', 'is_active', 'created_at')
    list_filter = ('entity_type', 'organization', 'is_active', 'action', 'from_status', 'to_status', 'created_at')
    search_fields = ('name', 'entity_type__name', 'action__name', 'organization__name')
    filter_horizontal = ('allowed_posts',)
    autocomplete_fields = ('from_status', 'to_status', 'action', 'entity_type', 'organization')
    
    fieldsets = (
        (_('اطلاعات اصلی'), {
            'fields': ('name', 'entity_type', 'from_status', 'action', 'to_status', 'organization', 'is_active')
        }),
        (_('پست‌های مجاز'), {
            'fields': ('allowed_posts',),
            'description': _('پست‌هایی که مجاز به انجام این انتقال هستند')
        }),
        (_('تاریخ‌ها'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'description', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'description')
    list_editable = ('is_active',)
    
    fieldsets = (
        (_('اطلاعات اصلی'), {
            'fields': ('name', 'code', 'description', 'is_active')
        }),
        (_('تاریخ‌ها'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

@admin.register(EntityType)
class EntityTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'entity_type', 'is_initial', 'is_final_approve', 'is_final_reject', 'is_pending', 'is_paid', 'is_rejected', 'is_active')
    list_filter = ('entity_type', 'is_initial', 'is_final_approve', 'is_final_reject', 'is_pending', 'is_paid', 'is_rejected', 'is_active')
    search_fields = ('name', 'code', 'description', 'entity_type')
    list_editable = ('is_initial', 'is_final_approve', 'is_final_reject', 'is_pending', 'is_paid', 'is_rejected', 'is_active')
    
    fieldsets = (
        (_('اطلاعات اصلی'), {
            'fields': ('name', 'code', 'entity_type', 'description')
        }),
        (_('ویژگی‌های وضعیت'), {
            'fields': ('is_initial', 'is_final_approve', 'is_final_reject', 'is_pending', 'is_paid', 'is_rejected', 'is_active')
        }),
    )

@admin.register(PostAction)
class PostActionAdmin(admin.ModelAdmin):
    list_display = ('post', 'stage', 'action_type', 'entity_type', 'is_active')
    list_filter = ('stage', 'action_type', 'entity_type', 'is_active', 'post__organization')
    search_fields = ('post__name', 'stage__name', 'action_type')
    autocomplete_fields = ('post', 'stage')
    ordering = ('post__organization', 'post__name', 'stage__name')

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('budget_locked_percentage_default', 'budget_warning_threshold_default', 'budget_warning_action_default')
    fieldsets = (
        (_('تنظیمات بودجه'), {
            'fields': ('budget_locked_percentage_default', 'budget_warning_threshold_default', 'budget_warning_action_default')
        }),
        (_('تنظیمات تخصیص'), {
            'fields': ('allocation_locked_percentage_default',)
        }),
        (_('تنظیمات تنخواه'), {
            'fields': ('tankhah_used_statuses', 'tankhah_accessible_organizations')
        }),
    )

# ثبت مدل‌ها - SystemSettings قبلاً با @admin.register ثبت شده است

@admin.register(PostRuleAssignment)
class PostRuleAssignmentAdmin(admin.ModelAdmin):
    list_display = ('post', 'action', 'organization', 'entity_type', 'is_active')
    list_filter = ('organization', 'entity_type', 'is_active', 'action')
    search_fields = ('post__name', 'organization__name', 'action__name')
    autocomplete_fields = ('post', 'action', 'organization')


@admin.register(UserRuleOverride)
class UserRuleOverrideAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'action', 'entity_type', 'post', 'is_enabled', 'updated_at')
    list_filter = ('organization', 'entity_type', 'is_enabled', 'action')
    search_fields = ('user__username', 'organization__name', 'action__code', 'entity_type__code', 'post__name')
    autocomplete_fields = ('user', 'organization', 'action', 'entity_type', 'post')


@admin.register(DynamicConfiguration)
class DynamicConfigurationAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'category', 'is_active', 'updated_at')
    list_filter = ('category', 'is_active', 'created_at', 'updated_at')
    search_fields = ('key', 'value', 'description', 'category')
    list_editable = ('value', 'is_active')
    ordering = ('category', 'key')
    
    fieldsets = (
        (_('اطلاعات اصلی'), {
            'fields': ('key', 'value', 'category', 'is_active')
        }),
        (_('توضیحات'), {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
        (_('تاریخ‌ها'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('category', 'key')