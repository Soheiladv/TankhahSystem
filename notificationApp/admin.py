from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import NotificationRule, Notification, BackupSchedule, BackupLog


@admin.register(NotificationRule)
class NotificationRuleAdmin(admin.ModelAdmin):
    list_display = ('entity_type_display', 'action_display', 'priority_display', 'channel_display', 'is_active')
    list_filter = ('entity_type', 'action', 'priority', 'channel', 'is_active')
    filter_horizontal = ('recipients',)
    search_fields = ('entity_type', 'action')

    fieldsets = (
        (_('اطلاعات پایه'), {
            'fields': ('entity_type', 'action', 'is_active')
        }),
        (_('تنظیمات ارسال'), {
            'fields': ('recipients', 'priority', 'channel')
        }),
    )

    def entity_type_display(self, obj):
        return obj.get_entity_type_display()

    entity_type_display.short_description = _('نوع موجودیت')

    def action_display(self, obj):
        return obj.get_action_display()

    action_display.short_description = _('اقدام')

    def priority_display(self, obj):
        return obj.get_priority_display()

    priority_display.short_description = _('اولویت')

    def channel_display(self, obj):
        return obj.get_channel_display()

    channel_display.short_description = _('کانال')

    class Media:
        css = {
            'all': ('css/admin-custom.css',)
        }

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'verb', 'entity_type_display', 'priority_display', 'unread', 'timestamp')
    list_filter = ('entity_type', 'priority', 'unread', 'deleted', 'timestamp')
    search_fields = ('recipient__username', 'verb', 'description')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        (_('اطلاعات اعلان'), {
            'fields': ('recipient', 'actor', 'verb', 'description', 'entity_type', 'priority')
        }),
        (_('وضعیت'), {
            'fields': ('unread', 'deleted', 'timestamp')
        }),
        (_('هدف'), {
            'fields': ('target_content_type', 'target_object_id'),
            'classes': ('collapse',)
        }),
    )
    
    def entity_type_display(self, obj):
        return obj.get_entity_type_display()
    entity_type_display.short_description = _('نوع موجودیت')
    
    def priority_display(self, obj):
        colors = {
            'LOW': 'green',
            'MEDIUM': 'orange',
            'HIGH': 'red',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'LOCKED': 'purple'
        }
        color = colors.get(obj.priority, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_display.short_description = _('اولویت')
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(deleted=False)

@admin.register(BackupSchedule)
class BackupScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'frequency_display', 'database_display', 'format_display', 'is_active', 'next_run', 'last_run')
    list_filter = ('frequency', 'database', 'format_type', 'is_active', 'encrypt')
    search_fields = ('name', 'description')
    filter_horizontal = ('notify_recipients',)
    
    fieldsets = (
        (_('اطلاعات پایه'), {
            'fields': ('name', 'description', 'created_by')
        }),
        (_('تنظیمات زمان‌بندی'), {
            'fields': ('frequency', 'custom_cron', 'is_active')
        }),
        (_('تنظیمات پشتیبان‌گیری'), {
            'fields': ('database', 'format_type', 'encrypt', 'password')
        }),
        (_('تنظیمات اعلان'), {
            'fields': ('notify_on_success', 'notify_on_failure', 'notify_recipients')
        }),
        (_('اطلاعات اجرا'), {
            'fields': ('last_run', 'next_run'),
            'classes': ('collapse',)
        }),
    )
    
    def frequency_display(self, obj):
        return obj.get_frequency_display()
    frequency_display.short_description = _('فرکانس')
    
    def database_display(self, obj):
        return obj.get_database_display()
    database_display.short_description = _('دیتابیس')
    
    def format_display(self, obj):
        return obj.get_format_type_display()
    format_display.short_description = _('فرمت')
    
    def save_model(self, request, obj, form, change):
        if not change:  # اگر جدید است
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        
        # بروزرسانی زمان اجرای بعدی
        if obj.is_active:
            obj.update_next_run()

@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'status_display', 'started_at', 'duration', 'file_size_display')
    list_filter = ('status', 'started_at', 'schedule')
    search_fields = ('schedule__name', 'error_message')
    readonly_fields = ('started_at', 'finished_at', 'duration')
    date_hierarchy = 'started_at'
    
    fieldsets = (
        (_('اطلاعات اجرا'), {
            'fields': ('schedule', 'status', 'started_at', 'finished_at', 'duration')
        }),
        (_('نتایج'), {
            'fields': ('file_path', 'file_size', 'error_message')
        }),
        (_('جزئیات'), {
            'fields': ('details',),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        colors = {
            'STARTED': 'blue',
            'COMPLETED': 'green',
            'FAILED': 'red',
            'CANCELLED': 'orange'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = _('وضعیت')
    
    def file_size_display(self, obj):
        if obj.file_size:
            size_names = ["B", "KB", "MB", "GB", "TB"]
            i = 0
            size = obj.file_size
            while size >= 1024 and i < len(size_names) - 1:
                size /= 1024.0
                i += 1
            return f"{size:.2f} {size_names[i]}"
        return "-"
    file_size_display.short_description = _('حجم فایل')