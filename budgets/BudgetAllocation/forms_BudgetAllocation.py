import logging
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from decimal import Decimal
import jdatetime
import re
from budgets.models import BudgetAllocation, BudgetPeriod
from core.models import Organization, Project, OrganizationType
from datetime import datetime, date

logger = logging.getLogger(__name__)

def to_english_digits(text):
    """تبدیل اعداد فارسی به انگلیسی"""
    farsi_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    return str(text).translate(farsi_to_english)

class BudgetAllocationForm(forms.ModelForm):
    project = forms.ModelChoiceField(
        queryset=Project.objects.filter(is_active=True),
        label=_("پروژه"),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )

    class Meta:
        model = BudgetAllocation
        fields = [
            'budget_period', 'organization', 'project', 'allocated_amount',
            'allocation_date', 'description', 'is_active', 'is_stopped',
            'allocation_type', 'locked_percentage', 'warning_threshold',
            'warning_action', 'allocation_number'
        ]
        widgets = {
            'organization': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'required': 'required',
                'data-control': 'select2',
                'data-placeholder': 'انتخاب سازمان'
            }),
            'project': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'required': 'required',
                'data-control': 'select2',
                'data-placeholder': 'انتخاب پروژه'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'required': 'required',
                'data-control': 'select2',
                'data-placeholder': 'وضعیت پروژه'
            }),

            'allocated_amount': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg numeric-input',
                'min': '0',
                'step': '1',
                'inputmode': 'numeric',
                'required': 'required',
                'placeholder': 'مبلغ را وارد کنید'
            }),
            'allocation_date': forms.TextInput(attrs={
                'data-jdp': '',
                'class': 'form-control form-control-lg',
                'placeholder': '1404/01/17',
                'required': 'required',
                'autocomplete': 'off'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control form-control-lg',
                'rows': 3,
                'placeholder': 'توضیحات تخصیص بودجه'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
                'style': 'width: 2.5rem; height: 1.5rem;'
            }),
            'is_stopped': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
                'style': 'width: 2.5rem; height: 1.5rem;'
            }),
            'allocation_type': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            }),
            'locked_percentage': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'min': '0',
                'max': '100',
                'step': '1',
                'inputmode': 'numeric',
                'required': 'required',
                'placeholder': '0-100'
            }),
            'warning_threshold': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'min': '0',
                'max': '100',
                'step': '1',
                'inputmode': 'numeric',
                'required': 'required',
                'placeholder': '0-100'
            }),
            'warning_action': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'data-control': 'select2',
                'data-placeholder': 'انتخاب اقدام'
            }),
            'allocation_number': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'min': '0',
                'step': '1',
                'inputmode': 'numeric',
                'required': 'required',
                'placeholder': 'شماره تخصیص'
            }),
            'budget_period': forms.HiddenInput(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.budget_period = kwargs.pop('budget_period', None)
        self.user = kwargs.pop('user', None)
        logger.debug(f"Initializing BudgetAllocationForm with budget_period={self.budget_period}, user={self.user}")
        super().__init__(*args, **kwargs)
        allowed_org_types = OrganizationType.objects.filter(
            is_budget_allocatable=True
        ).values_list('id', flat=True)
        self.fields['organization'].queryset = Organization.objects.filter(
            org_type__in=allowed_org_types,
            is_active=True
        )
        self.fields['project'].queryset = Project.objects.filter(is_active=True)
        if self.budget_period:
            self.fields['budget_period'].initial = self.budget_period
            allocated_orgs = BudgetAllocation.objects.filter(
                budget_period=self.budget_period
            ).values_list('organization_id', flat=True)
            if allocated_orgs:
                self.fields['organization'].queryset = self.fields['organization'].queryset.filter(
                    id__in=allocated_orgs
                )
            logger.debug(
                f"Filtered organization queryset: {list(self.fields['organization'].queryset.values('id', 'name'))}")
        else:
            logger.warning("No budget_period provided to form")
        if self.instance.pk and self.instance.allocation_date:
            j_date = jdatetime.date.fromgregorian(date=self.instance.allocation_date)
            self.initial['allocation_date'] = j_date.strftime('%Y/%m/%d')

    def clean_allocation_date(self):
        date_input = self.cleaned_data.get('allocation_date')
        logger.debug(f"Cleaning allocation_date: input={date_input}")
        if not date_input:
            logger.error("allocation_date is empty")
            raise forms.ValidationError(_('تاریخ تخصیص اجباری است.'))
        if isinstance(date_input, date):  # اگر قبلاً تبدیل شده بود
            return date_input
        try:
            date_str = to_english_digits(str(date_input).strip())
            date_str = re.sub(r'[-\.]', '/', date_str)
            j_date = jdatetime.date.strptime(date_str, '%Y/%m/%d')
            g_date = j_date.togregorian()
            if not isinstance(g_date, date):
                logger.error(f"Invalid allocation_date type: {type(g_date)}")
                raise forms.ValidationError(_('فرمت تاریخ نامعتبر است.'))
            logger.debug(f"Parsed allocation_date: {g_date}")
            return g_date
        except Exception as e:
            logger.error(f"Invalid allocation_date format: {date_input}, error: {e}")
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean(self):
        cleaned_data = super().clean()
        logger.debug(f"Running clean method: cleaned_data={cleaned_data}")
        organization = cleaned_data.get('organization')
        project = cleaned_data.get('project')
        allocated_amount = cleaned_data.get('allocated_amount')
        allocation_date = cleaned_data.get('allocation_date')
        budget_period = cleaned_data.get('budget_period')

        if not budget_period:
            logger.error("No budget_period selected")
            raise forms.ValidationError(_("دوره بودجه باید انتخاب شود."))

        if not organization:
            logger.error("No organization selected")
            raise forms.ValidationError(_('لطفاً یک سازمان انتخاب کنید.'))

        if not project:
            logger.error("No project selected")
            raise forms.ValidationError(_('لطفاً یک پروژه انتخاب کنید.'))

        if allocated_amount is None or allocated_amount <= 0:
            logger.error(f"Invalid allocated_amount: {allocated_amount}")
            raise forms.ValidationError(_('مبلغ تخصیص باید مثبت باشد.'))

        if organization and project:
            if not project.organizations.filter(id=organization.id).exists():
                logger.error(f"Project {project} does not belong to organization {organization}")
                raise forms.ValidationError(_('پروژه انتخاب‌شده متعلق به این سازمان نیست.'))

        if budget_period and allocated_amount:
            used_budget = BudgetAllocation.objects.filter(
                budget_period=budget_period
            ).exclude(id=self.instance.id).aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')
            remaining_budget = budget_period.total_amount - used_budget
            if allocated_amount > remaining_budget:
                logger.error(f"allocated_amount ({allocated_amount}) exceeds remaining_budget ({remaining_budget})")
                raise forms.ValidationError(_(
                    f'مبلغ تخصیص ({allocated_amount:,} ریال) بیشتر از بودجه باقی‌مانده ({remaining_budget:,} ریال) است.'
                ))

        if allocation_date and budget_period:
            start_date = budget_period.start_date
            end_date = budget_period.end_date
            if allocation_date < start_date or allocation_date > end_date:
                logger.error(f"allocation_date ({allocation_date}) outside budget_period range")
                raise forms.ValidationError(_('تاریخ تخصیص باید در بازه دوره بودجه باشد.'))

        logger.debug("Clean method completed")
        return cleaned_data

    def save(self, commit=True):
        logger.debug("Saving BudgetAllocationForm")
        instance = super().save(commit=False)
        instance.budget_period = self.budget_period
        if self.user and self.user.is_authenticated:
            instance.created_by = self.user
            logger.debug(f"Set created_by: {self.user}")
        else:
            logger.error("No authenticated user provided for created_by")
            raise forms.ValidationError(_('کاربر معتبر برای ایجاد تخصیص بودجه لازم است.'))
        if commit:
            try:
                instance.save()
                logger.info(f"BudgetAllocation saved: {instance}")
            except Exception as e:
                logger.error(f"Error saving BudgetAllocation: {str(e)}")
                raise
        return instance