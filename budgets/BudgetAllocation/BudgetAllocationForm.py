from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from decimal import Decimal
import jdatetime
import re

from budgets.models import BudgetAllocation
from core.models import Organization, Project
import logging
logger = logging.getLogger(__name__)

class BudgetAllocationForm(forms.ModelForm):
    project = forms.ModelChoiceField(
        queryset=Project.objects.filter(is_active=True),
        label=_("پروژه"),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )

    class Meta:
        model = BudgetAllocation
        fields = ['organization', 'project', 'allocated_amount', 'allocation_date', 'description', 'is_active']
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'allocated_amount': forms.NumberInput(attrs={
                'class': 'form-control numeric-input',
                'min': '0',
                'step': '1',
                'inputmode': 'numeric',
                'required': 'required'
            }),
            'allocation_date': forms.TextInput(attrs={
                'data-jdp': '',
                'class': 'form-control',
                'placeholder': '1404/01/17',
                'required': 'required'
            }),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.budget_period = kwargs.pop('budget_period', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['organization'].queryset = Organization.objects.filter(
            org_type__in=['COMPLEX', 'HQ'], is_active=True
        )
        if self.budget_period:
            self.fields['organization'].queryset = self.fields['organization'].queryset.filter(
                id__in=BudgetAllocation.objects.filter(
                    budget_period=self.budget_period
                ).values_list('organization_id', flat=True)
            )

    def clean_allocation_date(self):
        date_str = self.cleaned_data.get('allocation_date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ تخصیص اجباری است.'))
        date_str = re.sub(r'[-\.]', '/', date_str.strip())
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d').date()
            return j_date.togregorian()
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean(self):
        cleaned_data = super().clean()
        organization = cleaned_data.get('organization')
        project = cleaned_data.get('project')
        allocated_amount = cleaned_data.get('allocated_amount')
        allocation_date = cleaned_data.get('allocation_date')

        if not organization:
            self.add_error('organization', _('لطفاً یک سازمان انتخاب کنید.'))

        if not project:
            self.add_error('project', _('لطفاً یک پروژه انتخاب کنید.'))

        if allocated_amount is None or allocated_amount <= 0:
            self.add_error('allocated_amount', _('مبلغ تخصیص باید مثبت باشد.'))

        if organization and project:
            if not project.organizations.filter(id=organization.id).exists():
                self.add_error('project', _('پروژه انتخاب‌شده متعلق به این سازمان نیست.'))

        if self.budget_period and allocated_amount:
            used_budget = BudgetAllocation.objects.filter(
                budget_period=self.budget_period
            ).exclude(id=self.instance.id).aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')
            remaining_budget = self.budget_period.total_amount - used_budget
            if allocated_amount > remaining_budget:
                self.add_error('allocated_amount', _(
                    f'مبلغ تخصیص ({allocated_amount:,} ریال) بیشتر از بودجه باقی‌مانده ({remaining_budget:,} ریال) است.'
                ))

        if allocation_date and self.budget_period:
            if allocation_date < self.budget_period.start_date or (
                self.budget_period.end_date and allocation_date > self.budget_period.end_date
            ):
                self.add_error('allocation_date', _('تاریخ تخصیص باید در بازه دوره بودجه باشد.'))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.budget_period = self.budget_period
        instance.created_by = self.user
        if commit:
            instance.save()
        return instance