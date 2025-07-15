from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import NotificationRule


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