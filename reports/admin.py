from django.contrib import admin
<<<<<<< HEAD
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from .models import FinancialReport, Tankhah_FinancialReport,send_to_accounting,print_financial_report


admin.site.register(Tankhah_FinancialReport)
admin.site.register(print_financial_report)
admin.site.register(send_to_accounting)
class StatusFilter(admin.SimpleListFilter):
    title = _('وضعیت گزارش')
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            ('approved', _('تأیید شده')),
            ('rejected', _('رد شده')),
            ('partial', _('تأیید جزئی')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'approved':
            return queryset.filter(approved_amount__gt=0, rejected_amount=0)
        if self.value() == 'rejected':
            return queryset.filter(rejected_amount__gt=0, approved_amount=0)
        if self.value() == 'partial':
            return queryset.filter(rejected_amount__gt=0, approved_amount__gt=0)

@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = (
        'report_id',
        'tankhah_link',
        'total_amount_formatted',
        'approved_amount_formatted',
        'rejected_amount_formatted',
        'payment_status',
        'report_date_formatted',
        'action_buttons',  # تغییر نام از actions به action_buttons
    )
    list_filter = (StatusFilter, 'report_date')
    search_fields = ('tankhah__number', 'payment_number')
    readonly_fields = (
        'total_amount', 'approved_amount', 'rejected_amount',
        'total_factors', 'approved_factors', 'rejected_factors',
        'report_date', 'last_status', 'financial_summary'
    )
    fieldsets = (
        (_('اطلاعات پایه'), {
            'fields': ('tankhah', 'payment_number', 'report_date')
        }),
        (_('جزئیات مالی'), {
            'fields': (
                'total_amount', 'approved_amount', 'rejected_amount',
                'total_factors', 'approved_factors', 'rejected_factors',
                'financial_summary'
            )
        }),
        (_('تاریخچه وضعیت'), {
            'fields': ('last_status',),
            'classes': ('collapse',)
        }),
    )
    actions = None  # صراحتاً مشخص می‌کنیم که اکشن گروهی نداریم

    def report_id(self, obj):
        return f"REP-{obj.id:05d}"
    report_id.short_description = _('شناسه گزارش')

    def tankhah_link(self, obj):
        url = reverse('admin:tankhah_tankhah_change', args=[obj.tankhah.id])
        return format_html('<a href="{}">{}</a>', url, obj.tankhah.number)
    tankhah_link.short_description = _('شماره تنخواه')

    def total_amount_formatted(self, obj):
        return f"{obj.total_amount:,} ريال"
    total_amount_formatted.short_description = _('مبلغ کل')

    def approved_amount_formatted(self, obj):
        return format_html('<span style="color: green;">{:,} ريال</span>', obj.approved_amount)
    approved_amount_formatted.short_description = _('مبلغ تأییدشده')

    def rejected_amount_formatted(self, obj):
        return format_html('<span style="color: red;">{:,} ريال</span>', obj.rejected_amount)
    rejected_amount_formatted.short_description = _('مبلغ ردشده')

    def payment_status(self, obj):
        if obj.payment_number:
            return format_html('<span class="badge bg-success">پرداخت شده</span>')
        return format_html('<span class="badge bg-warning text-dark">در انتظار پرداخت</span>')
    payment_status.short_description = _('وضعیت پرداخت')

    def report_date_formatted(self, obj):
        return obj.report_date.strftime('%Y-%m-%d %H:%M')
    report_date_formatted.short_description = _('تاریخ گزارش')

    def financial_summary(self, obj):
        approval_rate = (obj.approved_amount / obj.total_amount * 100) if obj.total_amount > 0 else 0
        return format_html("""
            <div style="direction: rtl;">
                <div class="progress mb-2">
                    <div class="progress-bar bg-success" role="progressbar" style="width: {}%"
                         aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100"></div>
                    <div class="progress-bar bg-danger" role="progressbar" style="width: {}%"
                         aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
                <small>
                    <span class="text-success">تأیید شده: {:,} ريال ({:.1f}%)</span> |
                    <span class="text-danger">رد شده: {:,} ريال ({:.1f}%)</span>
                </small>
            </div>
        """,
            approval_rate, approval_rate,
            100 - approval_rate, 100 - approval_rate,
            obj.approved_amount, approval_rate,
            obj.rejected_amount, 100 - approval_rate
        )
    financial_summary.short_description = _('خلاصه مالی')

    def action_buttons(self, obj):
        return format_html("""
            <div class="btn-group">
                <a href="{}" class="btn btn-sm btn-outline-primary" title="مشاهده">
                    <i class="fas fa-eye"></i>
                </a>
                <a href="{}" class="btn btn-sm btn-outline-secondary" title="چاپ گزارش">
                    <i class="fas fa-print"></i>
                </a>
                <a href="{}" class="btn btn-sm btn-outline-info" title="ارسال به حسابداری">
                    <i class="fas fa-paper-plane"></i>
                </a>
            </div>
        """,
            reverse('admin:reports_financialreport_change', args=[obj.id]),
            reverse('print-financial-report', args=[obj.id]),
            reverse('send-to-accounting', args=[obj.id])
        )
    action_buttons.short_description = _('اقدامات')
    action_buttons.allow_tags = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tankhah')

    class Media:
        css = {
            # 'all': ('https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',)
        }
        js = (
            # 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
        )
=======

# Register your models here.
>>>>>>> 171b55a74efe3adb976919af53d3bd582bb2266e
