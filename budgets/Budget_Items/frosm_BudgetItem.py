from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from budgets.models import BudgetItem, BudgetPeriod
from core.models import Organization
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class BudgetItemForm(forms.ModelForm):
    class Meta:
        model = BudgetItem
        # fields = ['budget_period', 'organization', 'name', 'code',   'is_active']
        fields = ['budget_period', 'organization', 'name', 'code', 'is_active']
        widgets = {
            'budget_period': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required',
                'data-control': 'select2',
            }),
            'organization': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required',
                'data-control': 'select2',
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                'placeholder': _('نام ردیف بودجه'),
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                'placeholder': _('کد ردیف بودجه'),
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
            }),
        }
        labels = {
            'budget_period': _('دوره بودجه'),
            'organization': _('سازمان/شعبه'),
            'name': _('نام ردیف بودجه'),
            'code': _('کد ردیف بودجه'),
            'is_active': _('فعال'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['budget_period'].queryset = BudgetPeriod.objects.filter(is_active=True).select_related(
            'organization')
        self.fields['organization'].queryset = Organization.objects.filter(is_active=True).select_related('org_type')
        logger.debug("Initialized BudgetItemForm")

    def clean_code(self):
        code = self.cleaned_data.get('code')
        instance = self.instance
        if BudgetItem.objects.exclude(pk=instance.pk if instance else None).filter(code=code).exists():
            raise forms.ValidationError(_('این کد قبلاً استفاده شده است.'))
        return code
    #
    def clean_total_amount(self):
        amount = self.cleaned_data.get('total_amount')
        budget_period = self.cleaned_data.get('budget_period')
        if amount is None:
            raise forms.ValidationError(_('مبلغ کل نمی‌تواند خالی باشد.'))
        if amount <= 0:
            raise forms.ValidationError(_('مبلغ کل باید مثبت باشد.'))
        if budget_period:
            remaining = budget_period.get_remaining_amount()
            if amount > remaining:
                raise forms.ValidationError(
                    f"مبلغ ردیف ({amount:,.0f} ریال) بیشتر از باقی‌مانده دوره ({remaining:,.0f} ریال) است."
                )
        return amount

    def clean(self):
        cleaned_data = super().clean()
        budget_period = cleaned_data.get('budget_period')
        organization = cleaned_data.get('organization')
        if budget_period and organization and budget_period.organization != organization:
            raise forms.ValidationError(_('سازمان باید با دوره بودجه مطابقت داشته باشد.'))
        return cleaned_data
