"""
تنظیمات پنل مدیریت برای اپلیکیشن version_tracker
"""
import os
from datetime import timedelta

from django.apps import apps
from django.contrib import admin
from django.core.serializers import json
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Count
import logging

from .models import AppVersion, FinalVersion, FileHash, CodeChangeLog

# تنظیم لاگ‌گذاری برای دیباگ
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class VersionTypeFilter(admin.SimpleListFilter):
    title = _('نوع نسخه')
    parameter_name = 'version_type'
    def lookups(self, request, model_admin):
        return AppVersion.VERSION_TYPES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(version_type=self.value())
        return queryset

@admin.register(AppVersion)
class AppVersionAdmin(admin.ModelAdmin):
    """پنل مدیریت برای نسخه‌های اپلیکیشن‌ها"""
    list_display = ('get_app_name_fa', 'version_number', 'version_type', 'release_date', 'file_change_count', 'author', 'index_tag')
    list_filter = ('app_name', 'version_type', 'release_date')
    search_fields = ('app_name', 'version_number', 'code_hash')
    readonly_fields = ('code_hash', 'changed_files_display', 'system_info_display')
    list_per_page = 25
    actions = ['recalculate_hash', 'mark_as_major', 'update_versions', 'check_version_status']

    # change_list_template = 'versions/appversion_list.html'
    # context_object_name = 'app_versions'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['version_stats'] = {
            'total': AppVersion.objects.count(),
            'last_week': AppVersion.objects.filter(release_date__gte=timezone.now() - timedelta(days=7)).count()
        }
        return super().changelist_view(request, extra_context=extra_context)

    def update_versions(self, request, queryset):
        """به‌روزرسانی نسخه‌ها برای اپلیکیشن‌های انتخاب‌شده یا همه"""
        try:
            updates = AppVersion.check_and_update_versions()
            message = f"نسخه‌ها به‌روزرسانی شدند: {updates}" if updates else "هیچ تغییری یافت نشد."
            self.message_user(request, message)
            logger.info(message)
        except Exception as e:
            self.message_user(request, f"خطا در به‌روزرسانی: {str(e)}", level='error')
            logger.error(f"خطا در به‌روزرسانی نسخه‌ها: {str(e)}", exc_info=True)
    update_versions.short_description = "🔄 به‌روزرسانی نسخه‌ها"

    def check_version_status(self, request, queryset):
        """بررسی وضعیت نسخه‌ها"""
        latest_version = AppVersion.objects.latest('release_date')
        final_version = FinalVersion.objects.first()
        if final_version:
            final_version_number = final_version.version_number
        else:
            final_version_number = "تعریف نشده"
        message = (f"آخرین نسخه منتشر شده: {latest_version.version_number}\n"
                   f"نسخه نهایی: {final_version.version_number}")
        self.message_user(request, message)
    check_version_status.short_description = "🔍 بررسی وضعیت نسخه‌ها"

    def index_tag(self, obj):
        """اضافه کردن تگ برای نمایش نسخه نهایی"""
        final_version = FinalVersion.objects.first()
        if final_version and obj.version_number == final_version.version_number:
            return format_html('<span style="color:green; font-weight:bold;">✔ نهایی</span>')
        return format_html('<span style="color:red;">❌</span>')

    index_tag.short_description = _("📌 وضعیت نسخه")

    def get_queryset(self, request):
        """بهینه‌سازی کوئری‌ها"""
        return super().get_queryset(request).select_related('author').only(
            'app_name', 'version_number', 'version_type', 'release_date', 'changed_files', 'author__username'
        )

    def get_app_name_fa(self, obj):
        return obj.get_app_name_fa()
    get_app_name_fa.short_description = _("نام اپلیکیشن (فارسی)")

    def file_change_count(self, obj):
        """نمایش تعداد فایل‌های تغییر یافته"""
        return len(obj.changed_files)
    file_change_count.short_description = _("📁 تعداد تغییرات")

    def changed_files_display(self, obj):
        """نمایش فایل‌های تغییر یافته با قابلیت جستجو"""
        return format_html('<div class="scrollable-json"><pre>{}</pre></div>',
                           json.dumps(obj.changed_files, indent=2, ensure_ascii=False))
    changed_files_display.short_description = _("📂 فایل‌های تغییر یافته")

    def system_info_display(self, obj):
        """نمایش تعاملی اطلاعات سیستم"""
        return format_html(
            '<div class="system-info">'
            '<button class="toggle-info">نمایش جزئیات</button>'
            '<pre class="info-content" style="display:none">{}</pre>'
            '</div>',
            json.dumps(obj.system_info, indent=2, ensure_ascii=False)
        )
    system_info_display.short_description = _("🖥️ اطلاعات سیستم")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        """محدودیت حذف نسخه‌های قدیمی"""
        if obj and obj.version_number != FinalVersion.objects.first().version_number:
            return False
        return super().has_delete_permission(request, obj)

@admin.register(FinalVersion)
class FinalVersionAdmin(admin.ModelAdmin):
    """پنل مدیریت برای نسخه نهایی پروژه"""
    list_display = ('version_number', 'release_date', 'app_count')
    list_filter = ('release_date',)
    search_fields = ('version_number',)
    readonly_fields = ('version_number', 'release_date')
    actions = ['recalculate_final_version']

    def app_count(self, obj):
        return AppVersion.objects.filter(version_number=obj.version_number).count()
    app_count.short_description = _("تعداد اپلیکیشن‌ها")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('app_versions')

    def app_count(self, obj):
        return obj.app_versions.count()
    app_count.short_description = _("تعداد اپلیکیشن‌ها")

    app_count.admin_order_field = 'app_count'

    def version_breakdown(self, obj):
        return format_html(
            '''
            <div class="version-breakdown">
                <span class="major">Major: {} </span>
                <span class="minor">Minor: {} </span>
                <span class="patch">Patch: {} </span>
            </div>
            ''',
            obj.major_count, obj.minor_count, obj.patch_count
        )

    version_breakdown.short_description = _("توزیع نسخه‌ها")

    @admin.action(description=_("محاسبه مجدد نسخه نهایی"))
    def recalculate_final_version(self, request, queryset):
        FinalVersion.calculate_final_version()
        self.message_user(request, "نسخه نهایی با موفقیت محاسبه شد.")

    def has_add_permission(self, request):
        return False


@admin.register(FileHash)
class FileHashAdmin(admin.ModelAdmin):
    """پنل مدیریت برای هش فایل‌ها"""
    list_display = ('app_version', 'file_path_short', 'hash_value_short', 'timestamp')
    list_filter = ('app_version__app_name', 'timestamp')
    search_fields = ('file_path', 'hash_value')
    readonly_fields = ('hash_value', 'timestamp')
    list_per_page = 50

    def file_path_short(self, obj):
        return os.path.basename(obj.file_path) if obj.file_path else ''
    file_path_short.short_description = _("نام فایل")

    def hash_value_short(self, obj):
        return obj.hash_value[:10] + '...' if obj.hash_value else ''
    hash_value_short.short_description = _("هش فایل")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'app_version'
        ).only(
            'app_version__version_number',
            'file_path',
            'hash_value',
            'timestamp'
        )
@admin.register(CodeChangeLog)
class CodeChangeLogAdmin(admin.ModelAdmin):
    """پنل مدیریت برای لاگ تغییرات کد"""
    list_display = ('version', 'file_name_short', 'change_date', 'diff_preview')
    list_filter = ('version__app_name', 'change_date')
    search_fields = ('file_name', 'version__app_name')
    readonly_fields = ('old_code', 'new_code', 'diff_display')
    list_per_page = 30

    def file_name_short(self, obj):
        return os.path.basename(obj.file_name) if obj.file_name else ''
    file_name_short.short_description = _("نام فایل")

    def diff_preview(self, obj):
        diff = list(obj.get_diff())[:5]
        return format_html('<pre>{}</pre>', '\n'.join(diff))
    diff_preview.short_description = _("پیش‌نمایش تفاوت")

    def diff_display(self, obj):
        diff = list(obj.get_diff())[:100]
        return format_html('<pre>{}</pre>', '\n'.join(diff))
    diff_display.short_description = _("تفاوت کامل")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False