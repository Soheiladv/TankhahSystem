# Register your models here.
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from .models import (
    BudgetPeriod, BudgetAllocation, BudgetTransaction,
    PaymentOrder, Payee, TransactionType
)

# ادمین BudgetPeriod
@admin.register(BudgetPeriod)
class BudgetPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'total_amount', 'remaining_amount',
                    'start_date', 'end_date', 'is_active', 'is_archived')
    list_filter = ('organization', 'is_active', 'is_archived', 'start_date', 'end_date')
    search_fields = ('name', 'organization__name', 'organization__code')
    date_hierarchy = 'start_date'
    ordering = ('-start_date',)
    readonly_fields = ('remaining_amount',)
    fieldsets = (
        (None, {
            'fields': ('organization', 'name', 'total_amount', 'remaining_amount')
        }),
        (_('دوره زمانی'), {
            'fields': ('start_date', 'end_date')
        }),
        (_('وضعیت'), {
            'fields': ('is_active', 'is_archived', 'lock_condition')
        }),
        (_('ایجادکننده'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )
    actions = ['archive_periods']

    def archive_periods(self, request, queryset):
        updated = queryset.update(is_archived=True, is_active=False)
        self.message_user(request, f"{updated} دوره بودجه با موفقیت بایگانی شدند.")
    archive_periods.short_description = _("بایگانی دوره‌های انتخاب‌شده")

# ادمین BudgetAllocation
@admin.register(BudgetAllocation)
class BudgetAllocationAdmin(admin.ModelAdmin):
    list_display = ('budget_period', 'organization', 'allocated_amount',
                    'remaining_amount', 'allocation_date')
    list_filter = ('budget_period', 'organization', 'allocation_date')
    search_fields = ('budget_period__name', 'organization__name')
    date_hierarchy = 'allocation_date'
    ordering = ('-allocation_date',)
    readonly_fields = ('remaining_amount',)
    fieldsets = (
        (None, {
            'fields': ('budget_period', 'organization', 'allocated_amount', 'remaining_amount')
        }),
        (_('تاریخ'), {
            'fields': ('allocation_date',)
        }),
        (_('ایجادکننده'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )
    actions = ['recalculate_remaining']

    def recalculate_remaining(self, request, queryset):
        for allocation in queryset:
            total_consumed = allocation.transactions.filter(
                transaction_type__in=['CONSUMPTION', 'ADJUSTMENT_DECREASE']
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            total_added = allocation.transactions.filter(
                transaction_type__in=['ALLOCATION', 'ADJUSTMENT_INCREASE']
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            allocation.remaining_amount = total_added - total_consumed
            allocation.save()
        self.message_user(request, f"باقی‌مانده تخصیص‌ها با موفقیت بازمحاسبه شد.")
    recalculate_remaining.short_description = _("بازمحاسبه باقی‌مانده تخصیص‌ها")

# ادمین BudgetTransaction
@admin.register(BudgetTransaction)
class BudgetTransactionAdmin(admin.ModelAdmin):
    list_display = ('allocation', 'transaction_type', 'amount', 'related_tankhah',
                    'timestamp', 'created_by')
    list_filter = ('transaction_type', 'timestamp', 'created_by')
    search_fields = ('allocation__organization__name', 'related_tankhah__tankhah_number',
                     'created_by__username', 'description')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp',)
    fieldsets = (
        (None, {
            'fields': ('allocation', 'transaction_type', 'amount', 'related_tankhah')
        }),
        (_('جزئیات'), {
            'fields': ('timestamp', 'created_by', 'description')
        }),
    )

# ادمین PaymentOrder
@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'tankhah', 'amount', 'payee', 'status', 'issue_date',
                    'min_signatures', 'created_by')
    list_filter = ('status', 'issue_date', 'created_by_post')
    search_fields = ('order_number', 'tankhah__tankhah_number', 'payee__name', 'description')
    date_hierarchy = 'issue_date'
    ordering = ('-issue_date',)
    readonly_fields = ('order_number',)
    fieldsets = (
        (None, {
            'fields': ('tankhah', 'order_number', 'amount', 'payee', 'description')
        }),
        (_('وضعیت و تاریخ'), {
            'fields': ('status', 'issue_date', 'payment_id', 'min_signatures')
        }),
        (_('فاکتورها و ایجادکننده'), {
            'fields': ('related_factors', 'created_by_post', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    filter_horizontal = ('related_factors',)
    actions = ['mark_as_issued', 'mark_as_paid']

    def mark_as_issued(self, request, queryset):
        updated = queryset.update(status='ISSUED')
        self.message_user(request, f"{updated} دستور پرداخت به وضعیت 'صادر شده' تغییر یافت.")
    mark_as_issued.short_description = _("تغییر وضعیت به صادر شده")

    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status='PAID')
        self.message_user(request, f"{updated} دستور پرداخت به وضعیت 'پرداخت شده' تغییر یافت.")
    mark_as_paid.short_description = _("تغییر وضعیت به پرداخت شده")

# ادمین Payee
@admin.register(Payee)
class PayeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'payee_type', 'national_id', 'account_number', 'iban', 'phone')
    list_filter = ('payee_type',)
    search_fields = ('name', 'national_id', 'account_number', 'iban', 'phone')
    fieldsets = (
        (None, {
            'fields': ('name', 'payee_type')
        }),
        (_('اطلاعات شناسایی'), {
            'fields': ('national_id', 'account_number', 'iban')
        }),
        (_('تماس'), {
            'fields': ('address', 'phone')
        }),
        (_('ایجادکننده'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

# ادمین TransactionType
@admin.register(TransactionType)
class TransactionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'requires_extra_approval', 'description_short')
    list_filter = ('requires_extra_approval',)
    search_fields = ('name', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'requires_extra_approval', 'description')
        }),
        (_('ایجادکننده'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = _("توضیحات کوتاه")