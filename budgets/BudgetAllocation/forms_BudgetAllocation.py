# budgets/ProjectBudgetAllocation/forms_ProjectBudgetAllocation.py
import logging
from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from decimal import Decimal
import jdatetime
import re
from budgets.models import BudgetAllocation, BudgetPeriod
from core.models import Organization, Project, OrganizationType

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
        logger.debug(f"Initializing BudgetAllocationForm with budget_period={self.budget_period}, user={self.user}")
        super().__init__(*args, **kwargs)
        # دریافت idهای OrganizationType که برای تخصیص بودجه مجاز هستند
        allowed_org_types = OrganizationType.objects.filter(
            is_budget_allocatable=True
        ).values_list('id', flat=True)  # به جای 'org_type'، از 'id' استفاده می‌کنیم
        self.fields['organization'].queryset = Organization.objects.filter(
            org_type__in=allowed_org_types,  # مستقیماً به idهای OrganizationType اشاره می‌کنیم
            is_active=True
        )
        if self.budget_period:
            allocated_orgs = BudgetAllocation.objects.filter(
                budget_period=self.budget_period
            ).values_list('organization_id', flat=True)
            self.fields['organization'].queryset = self.fields['organization'].queryset.filter(
                id__in=allocated_orgs
            ) if allocated_orgs else self.fields['organization'].queryset
            logger.debug(
                f"Filtered organization queryset: {list(self.fields['organization'].queryset.values('id', 'name'))}")
        if self.instance.pk and self.instance.allocation_date:
            j_date = jdatetime.date.fromgregorian(date=self.instance.allocation_date)
            self.initial['allocation_date'] = j_date.strftime('%Y/%m/%d')
            logger.debug(f"Set initial allocation_date: {self.initial['allocation_date']}")

    def clean_allocation_date(self):
        date_str = self.cleaned_data.get('allocation_date')
        logger.debug(f"Cleaning allocation_date: input={date_str}")
        if not date_str:
            logger.error("allocation_date is empty")
            raise forms.ValidationError(_('تاریخ تخصیص اجباری است.'))
        date_str = to_english_digits(date_str.strip())
        date_str = re.sub(r'[-\.]', '/', date_str)
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d').date()
            g_date = j_date.togregorian()
            logger.debug(f"Parsed allocation_date: {g_date}")
            return g_date
        except ValueError:
            logger.error(f"Invalid allocation_date format: {date_str}")
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean(self):
        cleaned_data = super().clean()
        logger.debug(f"Running clean method: cleaned_data={cleaned_data}")
        organization = cleaned_data.get('organization')
        project = cleaned_data.get('project')
        allocated_amount = cleaned_data.get('allocated_amount')
        allocation_date = cleaned_data.get('allocation_date')

        if not organization:
            logger.error("No organization selected")
            self.add_error('organization', _('لطفاً یک سازمان انتخاب کنید.'))

        if not project:
            logger.error("No project selected")
            self.add_error('project', _('لطفاً یک پروژه انتخاب کنید.'))

        if allocated_amount is None or allocated_amount <= 0:
            logger.error(f"Invalid allocated_amount: {allocated_amount}")
            self.add_error('allocated_amount', _('مبلغ تخصیص باید مثبت باشد.'))

        if organization and project:
            if not project.organizations.filter(id=organization.id).exists():
                logger.error(f"Project {project} does not belong to organization {organization}")
                self.add_error('project', _('پروژه انتخاب‌شده متعلق به این سازمان نیست.'))

        if self.budget_period and allocated_amount:
            used_budget = BudgetAllocation.objects.filter(
                budget_period=self.budget_period
            ).exclude(id=self.instance.id).aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')
            remaining_budget = self.budget_period.total_amount - used_budget
            if allocated_amount > remaining_budget:
                logger.error(f"allocated_amount ({allocated_amount}) exceeds remaining_budget ({remaining_budget})")
                self.add_error('allocated_amount', _(
                    f'مبلغ تخصیص ({allocated_amount:,} ریال) بیشتر از بودجه باقی‌مانده ({remaining_budget:,} ریال) است.'
                ))

        if allocation_date and self.budget_period:
            if allocation_date < self.budget_period.start_date or (
                self.budget_period.end_date and allocation_date > self.budget_period.end_date
            ):
                logger.error(f"allocation_date ({allocation_date}) outside budget_period range")
                self.add_error('allocation_date', _('تاریخ تخصیص باید در بازه دوره بودجه باشد.'))

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