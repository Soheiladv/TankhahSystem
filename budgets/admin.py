# Register your models here.
from django.contrib import admin
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum

from core.models import SubProject
from budgets.models import (
    BudgetPeriod, BudgetAllocation, BudgetTransaction,
    PaymentOrder, Payee, TransactionType ,BudgetHistory,BudgetItem
)

from django import forms

# ادمین BudgetPeriod
@admin.register(BudgetPeriod)
class BudgetPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'total_amount',
                    'start_date', 'end_date', 'is_active', 'is_archived')
    list_filter = ('organization', 'is_active', 'is_archived', 'start_date', 'end_date')
    search_fields = ('name', 'organization__name', 'organization__code')
    date_hierarchy = 'start_date'
    ordering = ('-start_date',)
    # readonly_fields = ( get_remaining_amount() ,)
    fieldsets = (
        (None, {
            'fields': ('organization', 'name', 'total_amount' )
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
                     'allocation_date','budget_item')
    list_filter = ('budget_period', 'organization', 'allocation_date')
    search_fields = ('budget_period__name', 'organization__name')
    date_hierarchy = 'allocation_date'
    ordering = ('-allocation_date',)
    readonly_fields = ('budget_period',)
    fieldsets = (
        (None, {
            'fields': ('budget_period', 'organization', 'allocated_amount', 'budget_item', )
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
    list_display = ('order_number', 'tankhah', 'amount', 'payee', 'status', 'issue_date', 'min_signatures', 'created_by')
    list_filter = ('status', 'issue_date', 'created_by_post')
    search_fields = ('order_number', 'tankhah__number', 'payee__name', 'description')  # tankhah__tankhah_number به tankhah__number تغییر کرد
    date_hierarchy = 'issue_date'
    ordering = ('-issue_date',)
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('tankhah', 'order_number', 'amount', 'payee', 'description', 'organization')
        }),
        (_('وضعیت و تاریخ'), {
            'fields': ('status', 'issue_date', 'payment_id', 'min_signatures', 'payment_date')
        }),
        (_('اطلاعات پرداخت'), {
            'fields': ('payee_account_number', 'payee_iban', 'payment_tracking_id'),
            'classes': ('collapse',)
        }),
        (_('فاکتورها و ایجادکننده'), {
            'fields': ('related_factors', 'related_tankhah', 'created_by_post', 'created_by', 'paid_by'),
            'classes': ('collapse',)
        }),
        (_('گردش کار و یادداشت'), {
            'fields': ('current_stage', 'is_locked', 'notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    filter_horizontal = ('related_factors',)
    actions = ['mark_as_issued', 'mark_as_paid']

    def mark_as_issued(self, request, queryset):
        with transaction.atomic():
            updated = queryset.update(status='ISSUED_TO_TREASURY')
            for obj in queryset:
                obj.save()  # برای اطمینان از اجرای منطق save
        self.message_user(request, f"{updated} دستور پرداخت به وضعیت 'ارسال به خزانه' تغییر یافت.")
    mark_as_issued.short_description = _("تغییر وضعیت به ارسال به خزانه")

    def mark_as_paid(self, request, queryset):
        with transaction.atomic():
            updated = queryset.update(status='PAID')
            for obj in queryset:
                obj.update_budget_impact()
                obj.save()
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

@admin.register(SubProject)
class SubProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'is_active')
    list_filter = ('project', 'is_active')
    search_fields = ('name', 'project__name')  # برای autocomplete لازم داریم
    ordering = ('name',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project')


#------------from django.contrib import admin

class ProjectBudgetAllocationAdminForm(forms.ModelForm):
    class Meta:
        model = BudgetAllocation
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        budget_allocation = cleaned_data.get('budget_allocation')
        allocated_amount = cleaned_data.get('allocated_amount')
        subproject = cleaned_data.get('subproject')
        project = cleaned_data.get('project')
        #
        # if budget_allocation and allocated_amount:
        #     remaining = budget_allocation.get_remaining_amount()
        #     if allocated_amount > remaining:
        #         raise forms.ValidationError(
        #             _("مبلغ تخصیص (%(amount)s) بیشتر از باقی‌مانده بودجه شعبه (%(remaining)s) است") % {
        #                 'amount': allocated_amount,
        #                 'remaining': remaining
        #             }
        #         )

        if subproject and subproject.project != project:
            raise forms.ValidationError(_("زیرپروژه باید به پروژه انتخاب‌شده تعلق داشته باشد"))

        return cleaned_data

# @admin.register(ProjectBudgetAllocation)
# class ProjectBudgetAllocationAdmin(admin.ModelAdmin):
#     form = ProjectBudgetAllocationAdminForm
#     list_display = (
#         'project_name',
#         'subproject_name',
#         'allocated_amount_formatted',
#         'remaining_amount_formatted',
#         'budget_period_name',
#         'allocation_date',
#         'created_by',
#     )
#     list_filter = (
#         'budget_allocation__budget_period',
#         'project',
#         'subproject',
#         'allocation_date',
#         ('created_by', admin.RelatedOnlyFieldListFilter),
#     )
#     search_fields = (
#         'project__name',
#         'subproject__name',
#         'budget_allocation__budget_period__name',
#         'description',
#         'created_by__username',
#     )
#     list_per_page = 20
#     ordering = ('-allocation_date',)
#     autocomplete_fields = ('project', 'subproject', 'budget_allocation', 'created_by')
#     # readonly_fields = ('remaining_amount',)
#     fieldsets = (
#         (None, {
#             'fields': (
#                 'budget_allocation',
#                 'project',
#                 'subproject',
#                 'allocated_amount',
#                 # 'remaining_amount',
#                 'allocation_date',
#                 'created_by',
#                 'description',
#             )
#         }),
#     )
#
#     # متدهای سفارشی برای نمایش
#     def project_name(self, obj):
#         return obj.project.name
#     project_name.short_description = _("پروژه")
#     project_name.admin_order_field = 'project__name'
#
#     def subproject_name(self, obj):
#         return obj.subproject.name if obj.subproject else "-"
#     subproject_name.short_description = _("زیرپروژه")
#
#     def allocated_amount_formatted(self, obj):
#         return f"{obj.allocated_amount:,.0f} {_('ریال')}"
#     allocated_amount_formatted.short_description = _("مبلغ تخصیص")
#
#     def remaining_amount_formatted(self, obj):
#         return f"{obj.remaining_amount:,.0f} {_('ریال')}"
#     remaining_amount_formatted.short_description = _("باقی‌مانده")
#
#     def budget_period_name(self, obj):
#         return obj.budget_allocation.budget_period.name
#     budget_period_name.short_description = _("دوره بودجه")
#     budget_period_name.admin_order_field = 'budget_allocation__budget_period__name'
#
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related(
#             'budget_allocation__budget_period',
#             'project',
#             'subproject',
#             'created_by'
#         )
#
#     @admin.action(description=_("محاسبه مجدد باقی‌مانده‌ها"))
#     def recalculate_remaining(self, request, queryset):
#         for allocation in queryset:
#             allocation.remaining_amount = allocation.allocated_amount - (
#                 ProjectBudgetAllocation.objects.filter(budget_allocation=allocation.budget_allocation)
#                 .exclude(id=allocation.id)
#                 .aggregate(total=Sum('allocated_amount'))['total'] or 0
#             )
#             allocation.save()
#         self.message_user(request, _("باقی‌مانده‌ها با موفقیت محاسبه شدند"))
#
#     actions = [recalculate_remaining]
#
#     def has_add_permission(self, request):
#         return request.user.has_perm('budgets.ProjectBudgetAllocation_add')
#
#     def has_delete_permission(self, request, obj=None):
#         return request.user.has_perm('budgets.ProjectBudgetAllocation_delete')
#
#     def has_view_permission(self, request, obj=None):
#         return request.user.has_perm('budgets.ProjectBudgetAllocation_view')
#
#     def get_form(self, request, obj=None, **kwargs):
#         form = super().get_form(request, obj, **kwargs)
#         if obj:
#             form.base_fields['budget_allocation'].queryset = BudgetAllocation.objects.filter(
#                 budget_period__organization=obj.budget_allocation.organization
#             )
#         return form

admin.site.register(BudgetHistory)
admin.site.register(BudgetItem)