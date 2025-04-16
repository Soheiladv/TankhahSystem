from django import forms
from django.utils.translation import gettext_lazy as _
from budgets.models import BudgetItem, BudgetPeriod
from core.models import Organization
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class BudgetItemForm(forms.ModelForm):
    class Meta:
        model = BudgetItem
        fields = ['budget_period', 'organization', 'name', 'code', 'total_amount', 'is_active']
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
            'total_amount': forms.TextInput(attrs={
                'class': 'form-control numeric-input',
                'required': 'required',
                'inputmode': 'decimal',
                'placeholder': _('مبلغ کل (ریال)'),
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
            'total_amount': _('مبلغ کل'),
            'is_active': _('فعال'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['budget_period'].queryset = BudgetPeriod.objects.filter(is_active=True)
        self.fields['organization'].queryset = Organization.objects.filter(is_active=True)
        logger.debug("Initialized BudgetItemForm")

    def clean_code(self):
        code = self.cleaned_data.get('code')
        instance = self.instance
        if BudgetItem.objects.exclude(pk=instance.pk if instance else None).filter(code=code).exists():
            raise forms.ValidationError(_('این کد قبلاً استفاده شده است.'))
        return code

    def clean_total_amount(self):
        amount = self.cleaned_data.get('total_amount')
        if amount is None:
            raise forms.ValidationError(_('مبلغ کل نمی‌تواند خالی باشد.'))
        if amount <= 0:
            raise forms.ValidationError(_('مبلغ کل باید مثبت باشد.'))
        return amount

    def clean(self):
        cleaned_data = super().clean()
        budget_period = cleaned_data.get('budget_period')
        organization = cleaned_data.get('organization')
        if budget_period and organization:
            logger.debug(f"Validating BudgetItem: budget_period={budget_period.id}, organization={organization.id}")
        return cleaned_data