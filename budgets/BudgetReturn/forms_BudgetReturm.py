import logging
from django import forms
from django.core.cache import cache
from budgets.budget_calculations import get_project_remaining_budget, check_budget_status
from budgets.models import (BudgetTransaction)

logger = logging.getLogger(__name__)

# budgets/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from decimal import Decimal

class old___BudgetReturnForm(forms.ModelForm):
    class Meta:
        model = BudgetTransaction
        fields = ['amount', 'description']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'مبلغ (ریال)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'توضیحات'}),
        }
        labels = {
            'amount': _('مبلغ برگشتی'),
            'description': _('توضیحات'),
        }

    def __init__(self, *args, **kwargs):
        self.allocation = kwargs.pop('allocation', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.allocation:
            self.instance.allocation = self.allocation.budget_allocation
        if self.user:
            self.instance.created_by = self.user
        self.instance.transaction_type = 'RETURN'

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if not amount:
            raise forms.ValidationError(_('مبلغ برگشتی الزامی است.'))
        if amount <= 0:
            raise forms.ValidationError(_('مبلغ برگشتی باید مثبت باشد.'))

        if self.allocation:
            # محاسبه مصرف خالص
            consumed = BudgetTransaction.objects.filter(
                allocation=self.allocation.budget_allocation,
                allocation__project=self.allocation.project,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            returned = BudgetTransaction.objects.filter(
                allocation=self.allocation.budget_allocation,
                allocation__project=self.allocation.project,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            total_consumed = consumed - returned

            # بررسی سقف بازگشت
            if amount > total_consumed:
                raise forms.ValidationError(
                    _(f"مبلغ برگشتی ({amount:,.0f} ریال) نمی‌تواند بیشتر از مصرف خالص ({total_consumed:,.0f} ریال) باشد.")
                )

            # بررسی بودجه باقی‌مانده پروژه
            remaining_budget = get_project_remaining_budget(self.allocation.project)
            if amount > remaining_budget:
                raise forms.ValidationError(
                    _(f"مبلغ برگشتی ({amount:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده پروژه ({remaining_budget:,.0f} ریال) باشد.")
                )

        return amount

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.transaction_type = 'RETURN'
        if commit:
            instance.save()
            # بررسی وضعیت بودجه و ارسال اعلان
            status, message = check_budget_status(instance.allocation.budget_period)
            if status in ('warning', 'locked', 'completed', 'stopped'):
                instance.allocation.send_notification(status, message)
            instance.allocation.send_notification(
                'return',
                f"مبلغ {instance.amount:,.0f} ریال از تخصیص {instance.allocation.id} برگشت داده شد."
            )
        return instance

class BudgetReturnForm(forms.ModelForm):
    class Meta:
        model = BudgetTransaction
        fields = ['amount', 'description']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.01',
                'step': '0.01',
                'placeholder': _('مبلغ (ریال)')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('توضیحات (اختیاری)')
            }),
        }
        labels = {
            'amount': _('مبلغ برگشتی'),
            'description': _('توضیحات'),
        }

    def __init__(self, *args, allocation=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.allocation = allocation
        self.user = user
        if allocation:
            self.instance.allocation = allocation.budget_allocation
        if user:
            self.instance.created_by = user
        self.instance.transaction_type = 'RETURN'

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if not amount:
            raise forms.ValidationError(_('مبلغ برگشتی الزامی است.'))
        if amount <= 0:
            raise forms.ValidationError(_('مبلغ برگشتی باید مثبت باشد.'))

        if not self.allocation:
            raise forms.ValidationError(_('تخصیص بودجه مشخص نشده است.'))

        # کش برای مصرف خالص
        cache_key = f"net_consumed_{self.allocation.pk}"
        net_consumed = cache.get(cache_key)
        if net_consumed is None:
            consumed = BudgetTransaction.objects.filter(
                allocation=self.allocation.budget_allocation,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            returned = BudgetTransaction.objects.filter(
                allocation=self.allocation.budget_allocation,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            net_consumed = consumed - returned
            cache.set(cache_key, net_consumed, timeout=300)

        # بررسی سقف بازگشت
        if amount > net_consumed:
            raise forms.ValidationError(
                _(
                    f"مبلغ برگشتی ({amount:,.0f} ریال) نمی‌تواند بیشتر از مصرف خالص "
                    f"({net_consumed:,.0f} ریال) باشد."
                )
            )

        # بررسی بودجه باقی‌مانده پروژه
        remaining_budget = get_project_remaining_budget(self.allocation.project)
        if amount > remaining_budget:
            raise forms.ValidationError(
                _(
                    f"مبلغ برگشتی ({amount:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده پروژه "
                    f"({remaining_budget:,.0f} ریال) باشد."
                )
            )

        return amount

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.transaction_type = 'RETURN'
        if commit:
            instance.save()
            # به‌روزرسانی مقادیر تخصیص
            self.allocation.returned_amount = (
                self.allocation.returned_amount or Decimal('0')
            ) + instance.amount
            self.allocation.allocated_amount -= instance.amount
            self.allocation.budget_allocation.returned_amount = (
                self.allocation.budget_allocation.returned_amount or Decimal('0')
            ) + instance.amount
            self.allocation.budget_allocation.allocated_amount -= instance.amount
            self.allocation.budget_allocation.budget_period.total_allocated -= instance.amount
            self.allocation.budget_allocation.budget_period.returned_amount = (
                self.allocation.budget_allocation.budget_period.returned_amount or Decimal('0')
            ) + instance.amount

            self.allocation.save(update_fields=['returned_amount', 'allocated_amount'])
            self.allocation.budget_allocation.save(update_fields=['returned_amount', 'allocated_amount'])
            self.allocation.budget_allocation.budget_period.save(
                update_fields=['total_allocated', 'returned_amount']
            )

            # ارسال اعلان‌ها
            from budgets.budget_calculations import check_budget_status
            status, message = check_budget_status(self.allocation.budget_allocation.budget_period)
            if status in ('warning', 'locked', 'completed', 'stopped'):
                self.allocation.budget_allocation.send_notification(status, message)
            self.allocation.budget_allocation.send_notification(
                'return',
                f"مبلغ {instance.amount:,.0f} ریال از تخصیص {self.allocation.id} برگشت داده شد."
            )
        return instance
