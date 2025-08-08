from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django_jalali.admin.filters import JDateFieldListFilter

from tankhah.models import Tankhah, Factor, ApprovalLog, ItemCategory , StageApprover

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django_jalali.admin.filters import JDateFieldListFilter
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from tankhah.models import Tankhah, Factor, ApprovalLog

def register_permissions(apps, schema_editor):
    ct = ContentType.objects.get_for_model(Factor)
    Permission.objects.get_or_create(codename='Factor_view', name='Can view factor', content_type=ct)
    Permission.objects.get_or_create(codename='Factor_update', name='Can update factor', content_type=ct)

# ادمین تنخواه
@admin.register(Tankhah)
class TankhahAdmin(admin.ModelAdmin):
    list_display = (
        'number', 'date', 'organization', 'project', 'status',
        'created_by_short', 'approved_by_short', 'view_factors_count'
    )
    list_filter = (
        ('date', JDateFieldListFilter),
        'status',

        'organization',
        'project',
    )
    search_fields = (
        'number', 'letter_number', 'created_by__username',
        'approved_by__username', 'organization__name', 'project__name'
    )
    list_select_related = ('organization', 'project', 'created_by', 'approved_by', 'last_stopped_post')
    autocomplete_fields = ('organization', 'project', 'last_stopped_post', 'created_by', 'approved_by')
    ordering = ('-date', 'number')
    list_per_page = 50
    readonly_fields = ('number', 'status',   'last_stopped_post', 'created_by', 'approved_by')
    fieldsets = (
        (None, {
            'fields': ('number', 'date', 'organization', 'project', 'status',   'last_stopped_post')
        }),
        (_('اطلاعات تأیید'), {
            'fields': ('letter_number', 'created_by', 'approved_by'),
            'classes': ('collapse',)
        }),
    )

    # class FactorInline(admin.TabularInline):
    #     model = Factor
    #     extra = 0
    #     fields = ('number', 'date', 'amount', 'status', 'view_link')
    #     readonly_fields = ('number', 'date', 'amount', 'status', 'view_link')
    #
    #     def view_link(self, obj):
    #         if obj.pk:
    #             url = reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=[obj.pk])
    #             return format_html('<a href="{}" target="_blank">{}</a>', url, _('مشاهده'))
    #         return "-"
    #     view_link.short_description = _('جزئیات')

    # inlines = [FactorInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'organization', 'project', 'created_by', 'approved_by'
        ).prefetch_related('factors').annotate(factor_count=Count('factors'))

    def created_by_short(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username if obj.created_by else '-'
    created_by_short.short_description = _('ایجادکننده')
    created_by_short.admin_order_field = 'created_by__username'

    def approved_by_short(self, obj):
        return obj.approved_by.get_full_name() or obj.approved_by.username if obj.approved_by else '-'
    approved_by_short.short_description = _('تأییدکننده نهایی')
    approved_by_short.admin_order_field = 'approved_by__username'

    def view_factors_count(self, obj):
        count = obj.factor_count
        if count > 0:
            url = reverse('admin:tankhah_factor_changelist') + f'?tankhah__id={obj.id}'
            return format_html('<a href="{}">{} فاکتور</a>', url, count)
        return f'۰ {_("فاکتور")}'
    view_factors_count.short_description = _('فاکتورها')

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.created_by_id and request.user.is_authenticated:
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
    # autocomplete_fields = ('tankhah',)
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
    # autocomplete_fields = ('user',)


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
    # autocomplete_fields = ('tankhah', 'factor', 'user')
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

admin.site.register(ItemCategory)


from .models import ItemCategory
admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_stage_order')
    search_fields = ('name',)



from django.contrib import admin
from tankhah.models import StageApprover
from core.models import AccessRule

@admin.register(StageApprover)
class StageApproverAdmin(admin.ModelAdmin):
    list_display = ('stage', 'post', 'entity_type', 'action', 'is_active')
    list_filter = ('stage', 'entity_type', 'is_active')
    search_fields = ('post__name', 'stage__name')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # همزمان AccessRule را به‌روزرسانی کنید
        AccessRule.objects.get_or_create(
            post=obj.post,
            stage=obj.stage,
            action_type=obj.action,
            entity_type=obj.entity_type,
            defaults={'is_active': obj.is_active}
        )