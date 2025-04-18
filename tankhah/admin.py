from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django_jalali.admin.filters import JDateFieldListFilter

from .models import Tankhah, Factor, ApprovalLog

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

def register_permissions(apps, schema_editor):
    ct = ContentType.objects.get_for_model(Factor)
    Permission.objects.get_or_create(codename='Factor_view', name='Can view factor', content_type=ct)
    Permission.objects.get_or_create(codename='Factor_update', name='Can update factor', content_type=ct)

# ادمین تنخواه
@admin.register(Tankhah)
class TankhahAdmin(admin.ModelAdmin):
    list_display = (
    'number', 'date', 'organization', 'project', 'status', 'hq_status', 'created_by_short', 'approved_by_short')
    list_filter = (
        ('date', JDateFieldListFilter),
        'status',
        'hq_status',
        'organization',
    )
    search_fields = ('number', 'letter_number', 'created_by__username', 'approved_by__username')
    list_select_related = ('organization', 'project', 'created_by', 'approved_by', 'last_stopped_post')
    autocomplete_fields = ('organization', 'project', 'last_stopped_post', 'created_by', 'approved_by')
    ordering = ('-date', 'number')
    fieldsets = (
        (None, {
            'fields': ('number', 'date', 'organization', 'project', 'status', 'hq_status', 'last_stopped_post')
        }),
        (_('اطلاعات تأیید'), {
            'fields': ('letter_number', 'created_by', 'approved_by'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('number',)  # شماره به صورت خودکار تولید می‌شه

    def created_by_short(self, obj):
        return obj.created_by.username if obj.created_by else '-'

    created_by_short.short_description = _('ایجادکننده')

    def approved_by_short(self, obj):
        return obj.approved_by.username if obj.approved_by else '-'

    approved_by_short.short_description = _('تأییدکننده')

    # نمایش فاکتورهای مرتبط به صورت اینلاین
    class FactorInline(admin.TabularInline):
        model = Factor
        extra = 1
        fields = ('number', 'date', 'amount', 'status', 'file')
        readonly_fields = ('number',)
        autocomplete_fields = ('tankhah',)

    inlines = [FactorInline]

    def save_model(self, request, obj, form, change):
        # ثبت کاربر فعلی به عنوان ایجادکننده اگه جدید باشه
        if not obj.pk and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ادمین فاکتور
@admin.register(Factor)
class FactorAdmin(admin.ModelAdmin):
    list_display = ('number', 'number', 'date', 'amount', 'status' )
    list_filter = (
        ('date', JDateFieldListFilter),
        'status',
        'tankhah__organization',
    )
    search_fields = ('number', 'tankhah__number', 'description')
    list_select_related = ('tankhah',)
    autocomplete_fields = ('tankhah',)
    ordering = ('-date', 'number')
    fieldsets = (
        (None, {
            'fields': ('number', 'tankhah', 'date', 'amount', 'status')
        }),
        (_('جزئیات'), {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('number' ,)  # شماره و حجم فایل خودکار ست می‌شن
    #
    # def tankhah_number(self, obj):
    #     return obj.Tankhah.number
    #
    # tankhah_number.short_description = _('شماره تنخواه')

    # def file_link(self, obj):
    #     if obj.file:
    #         return admin.utils.format_html('<a href="{}" target="_blank">{}</a>', obj.file.url, _('دانلود فایل'))
    #     return '-'
    #
    # file_link.short_description = _('فایل')

# نمایش تأییدات مرتبط به صورت اینلاین
class ApprovalInline(admin.TabularInline):
    model = ApprovalLog
    extra = 1
    fields = ('user', 'date', 'action', 'comment')
    autocomplete_fields = ('user',)

inlines = [ApprovalInline]


# ادمین تأیید
@admin.register(ApprovalLog)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ('tankhah', 'factor_number', 'user', 'date', 'action', 'comment_short')
    list_filter = (
        ('date', JDateFieldListFilter),
        'action',
        'tankhah__organization',
    )
    search_fields = ('tankhah', 'factor__number', 'user__username', 'comment')
    list_select_related = ('tankhah', 'factor', 'user')
    autocomplete_fields = ('tankhah', 'factor', 'user')
    ordering = ('-date',)
    fieldsets = (
        (None, {
            'fields': ('tankhah', 'factor', 'user', 'date',)
        }),
        (_('توضیحات'), {
            'fields': ('comment',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('date',)  # تاریخ به صورت خودکار ست می‌شه

    def tankhah_number(self, obj):
        return obj.Tankhah.number if obj.Tankhah else '-'

    tankhah_number.short_description = _('شماره تنخواه')

    def factor_number(self, obj):
        return obj.factor.number if obj.factor else '-'

    factor_number.short_description = _('شماره فاکتور')

    def comment_short(self, obj):
        return obj.comment[:50] + '...' if obj.comment and len(obj.comment) > 50 else obj.comment

    comment_short.short_description = _('توضیحات کوتاه')

    def save_model(self, request, obj, form, change):
        # ثبت کاربر فعلی به عنوان تأییدکننده اگه جدید باشه
        if not obj.pk and not obj.user:
            obj.user = request.user
        super().save_model(request, obj, form, change)
