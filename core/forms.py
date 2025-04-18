import re
from django.db.models import Sum
from decimal import Decimal
from Tanbakhsystem.utils import convert_jalali_to_gregorian, convert_gregorian_to_jalali, convert_to_farsi_numbers
from Tanbakhsystem.widgets import NumberToWordsWidget
from accounts.models import TimeLockModel
from budgets.models import BudgetAllocation, ProjectBudgetAllocation
from core.models import Project, Organization, UserPost, Post, PostHistory, WorkflowStage, SubProject
from django import forms
from .models import Project, Organization
from django.utils.translation import gettext_lazy as _
from django_jalali.forms import jDateField
from django.core.exceptions import ValidationError
from jdatetime import datetime as jdatetime
import jdatetime

class TimeLockModelForm(forms.ModelForm):
    class Meta:
        model = TimeLockModel
        fields = ['lock_key', 'hash_value', 'salt', 'is_active', 'organization_name']
        widgets = {
            'lock_key': forms.TextInput(attrs={'class': 'form-control'}),
            'hash_value': forms.TextInput(attrs={'class': 'form-control'}),
            'salt': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'organization_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'lock_key': _('کلید قفل'),
            'hash_value': _('هش مقدار'),
            'salt': _('مقدار تصادفی'),
            'is_active': _('وضعیت فعال'),
            'organization_name': _('نام مجموعه'),
        }


class __ProjectForm(forms.ModelForm):
    has_subproject = forms.BooleanField(
        label=_("آیا ساب‌پروژه دارد؟"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    subproject_name = forms.CharField(
        label=_("نام ساب‌پروژه"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    subproject_description = forms.CharField(
        label=_("توضیحات ساب‌پروژه"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    subproject_budget = forms.DecimalField(
        label=_("بودجه ساب‌پروژه (ریال)"),
        required=False,
        decimal_places=2,
        max_digits=25,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
    )
    allocated_amount = forms.DecimalField(
        label=_("بودجه تخصیص‌یافته به پروژه (ریال)"),
        required=False,
        decimal_places=2,
        max_digits=25,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        label=_("شعبه"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        })
    )
    end_date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        })
    )
    class Meta:
        model = Project
        fields = [
            'name', 'code',  'priority', 'organization',
            'is_active', 'description', 'has_subproject', 'subproject_name',
            'subproject_description', 'allocated_amount'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام پروژه'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'کد پروژه'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'توضیحات'}),
            'start_date': forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control', 'placeholder': '1404/01/17'}),
            'end_date': forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control', 'placeholder': '1404/01/17'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organization'].queryset = Organization.objects.filter(org_type__in=['COMPLEX', 'HQ'])

        if self.instance.pk:
            # مقدار اولیه برای ویرایش پروژه
            jalali_start = jdatetime.date.fromgregorian(
                year=self.instance.start_date.year,
                month=self.instance.start_date.month,
                day=self.instance.start_date.day
            ).strftime('%Y/%m/%d')
            jalali_end = ''
            if self.instance.end_date:
                jalali_end = jdatetime.date.fromgregorian(
                    year=self.instance.end_date.year,
                    month=self.instance.end_date.month,
                    day=self.instance.end_date.day
                ).strftime('%Y/%m/%d')
            self.fields['start_date'].initial = jalali_start
            self.fields['end_date'].initial = jalali_end
            self.fields['organization'].initial = self.instance.organizations.first()
            allocated = BudgetAllocation.objects.filter(project=self.instance).aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')
            self.fields['allocated_amount'].initial = allocated
            if self.instance.subprojects.exists():
                subproject = self.instance.subprojects.first()
                self.fields['has_subproject'].initial = True
                self.fields['subproject_name'].initial = subproject.name
                self.fields['subproject_description'].initial = subproject.description
                self.fields['subproject_budget'].initial = subproject.allocated_budget

    def clean_start_date(self):
        date_str = self.cleaned_data.get('start_date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ شروع اجباری است.'))

        # نرمال‌سازی ورودی
        date_str = re.sub(r'[-\.]', '/', date_str.strip())
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d').date()
            return j_date.togregorian()
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1403/02/21).'))

    def clean_end_date(self):
        date_str = self.cleaned_data.get('end_date')
        if not date_str:
            return None

        # نرمال‌سازی ورودی
        date_str = re.sub(r'[-\.]', '/', date_str.strip())
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d').date()
            return j_date.togregorian()
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1403/02/21).'))

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        has_subproject = cleaned_data.get('has_subproject')
        subproject_name = cleaned_data.get('subproject_name')
        subproject_budget = cleaned_data.get('subproject_budget')
        allocated_amount = cleaned_data.get('allocated_amount')
        organization = cleaned_data.get('organization')

        # اعتبارسنجی تاریخ‌ها
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError(_("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد."))

        # اعتبارسنجی ساب‌پروژه
        if has_subproject:
            if not subproject_name:
                self.add_error('subproject_name', _('نام ساب‌پروژه اجباری است.'))
            if not subproject_budget:
                self.add_error('subproject_budget', _('بودجه ساب‌پروژه اجباری است.'))

        # اعتبارسنجی بودجه
        if organization:
            from budgets.budget_calculations import get_organization_budget
            org_budget = get_organization_budget(organization)
            if org_budget is None:
                self.add_error('organization', _('این شعبه بودجه تعریف‌شده‌ای ندارد.'))
                return cleaned_data

            used_budget = BudgetAllocation.objects.filter(organization=organization).exclude(
                project=self.instance if self.instance.pk else None
            ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
            remaining_budget = org_budget - used_budget

            total_requested = (allocated_amount or Decimal('0')) + (subproject_budget or Decimal('0'))
            if total_requested > remaining_budget:
                self.add_error('allocated_amount', _(
                    f"مجموع بودجه درخواستی ({total_requested:,} ریال) بیشتر از بودجه باقی‌مانده شعبه ({remaining_budget:,} ریال) است."
                ))
            if total_requested < 0:
                self.add_error('allocated_amount', _('مجموع بودجه نمی‌تواند منفی باشد.'))

        if allocated_amount and allocated_amount < 0:
            self.add_error('allocated_amount', _('بودجه پروژه نمی‌تواند منفی باشد.'))
        if subproject_budget and subproject_budget < 0:
            self.add_error('subproject_budget', _('بودجه ساب‌پروژه نمی‌تواند منفی باشد.'))

        return cleaned_data

    def save(self, commit=True):
        from budgets.models import BudgetAllocation, ProjectBudgetAllocation
        instance = super().save(commit=False)
        has_subproject = self.cleaned_data.get('has_subproject')
        subproject_name = self.cleaned_data.get('subproject_name')
        subproject_description = self.cleaned_data.get('subproject_description')
        subproject_budget = self.cleaned_data.get('subproject_budget')
        allocated_amount = self.cleaned_data.get('allocated_amount')
        organization = self.cleaned_data.get('organization')

        if commit:
            instance.save()
            instance.organizations.set([organization])
            self.save_m2m()

            # تخصیص بودجه به پروژه
            if allocated_amount:
                budget_allocation = BudgetAllocation.objects.create(
                    organization=organization,
                    allocated_amount=allocated_amount,
                    created_by=self.request.user,
                    project=instance
                )
                ProjectBudgetAllocation.objects.create(
                    budget_allocation=budget_allocation,
                    project=instance,
                    allocated_amount=allocated_amount,
                    created_by=self.request.user
                )

            # ایجاد ساب‌پروژه
            if has_subproject and subproject_name:
                subproject = SubProject.objects.create(
                    project=instance,
                    name=subproject_name,
                    description=subproject_description,
                    allocated_budget=subproject_budget or Decimal('0'),
                    is_active=True
                )
                if subproject_budget:
                    budget_allocation = BudgetAllocation.objects.create(
                        organization=organization,
                        allocated_amount=subproject_budget,
                        created_by=self.request.user,
                        project=instance
                    )
                    ProjectBudgetAllocation.objects.create(
                        budget_allocation=budget_allocation,
                        project=instance,
                        subproject=subproject,
                        allocated_amount=subproject_budget,
                        created_by=self.request.user
                    )

        return instance

from django import forms
from django.utils.translation import gettext_lazy as _
from core.models import Organization, Project, SubProject
from budgets.models import BudgetAllocation
import jdatetime
import re

class _ProjectForm(forms.ModelForm):
    has_subproject = forms.BooleanField(
        label=_("آیا ساب‌پروژه دارد؟"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    subproject_name = forms.CharField(
        label=_("نام ساب‌پروژه"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    subproject_description = forms.CharField(
        label=_("توضیحات ساب‌پروژه"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        label=_("شعبه"),
        widget=forms.Select(attrs={'class': 'form-control', 'data-control': 'select2'})
    )

    class Meta:
        model = Project
        fields = [
            'name', 'code', 'start_date', 'end_date', 'priority', 'organization',
            'is_active', 'description', 'has_subproject', 'subproject_name',
            'subproject_description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام پروژه')}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('کد پروژه')}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': _('توضیحات')}),
            'start_date': forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control jalali-datepicker', 'placeholder': '1404/01/17'}),
            'end_date': forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control jalali-datepicker', 'placeholder': '1404/01/17'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # محدود کردن سازمان‌ها به شعب فعال و قابل تخصیص بودجه
        self.fields['organization'].queryset = Organization.objects.filter(
            org_type__is_budget_allocatable=True, is_active=True
        ).select_related('org_type').order_by('name')

        # تنظیم مقادیر اولیه برای ویرایش پروژه
        if self.instance.pk:
            jalali_start = jdatetime.date.fromgregorian(
                date=self.instance.start_date
            ).strftime('%Y/%m/%d')
            jalali_end = ''
            if self.instance.end_date:
                jalali_end = jdatetime.date.fromgregorian(
                    date=self.instance.end_date
                ).strftime('%Y/%m/%d')
            self.fields['start_date'].initial = jalali_start
            self.fields['end_date'].initial = jalali_end
            self.fields['organization'].initial = self.instance.organizations.first()
            if self.instance.subprojects.exists():
                subproject = self.instance.subprojects.first()
                self.fields['has_subproject'].initial = True
                self.fields['subproject_name'].initial = subproject.name
                self.fields['subproject_description'].initial = subproject.description

    def clean_start_date(self):
        date_str = self.cleaned_data.get('start_date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ شروع اجباری است.'))
        date_str = re.sub(r'[-\.]', '/', date_str.strip())
        try:
            j_date = jdatetime.date.strptime(date_str, '%Y/%m/%d')
            return j_date.togregorian()
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1403/02/21).'))

    def clean_end_date(self):
        date_str = self.cleaned_data.get('end_date')
        if not date_str:
            return None
        date_str = re.sub(r'[-\.]', '/', date_str.strip())
        try:
            j_date = jdatetime.date.strptime(date_str, '%Y/%m/%d')
            return j_date.togregorian()
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1403/02/21).'))

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if Project.objects.exclude(pk=self.instance.pk).filter(code=code).exists():
            raise forms.ValidationError(_('این کد پروژه قبلاً استفاده شده است.'))
        return code

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        has_subproject = cleaned_data.get('has_subproject')
        subproject_name = cleaned_data.get('subproject_name')
        organization = cleaned_data.get('organization')

        # بررسی تاریخ‌ها
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError(_("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد."))

        # بررسی ساب‌پروژه
        if has_subproject and not subproject_name:
            self.add_error('subproject_name', _('نام ساب‌پروژه اجباری است.'))

        # بررسی وجود بودجه برای سازمان
        if organization:
            from budgets.budget_calculations import get_organization_budget
            org_budget = get_organization_budget(organization)
            if org_budget is None or org_budget <= 0:
                self.add_error('organization', _('این شعبه بودجه تعریف‌شده‌ای ندارد.'))

        return cleaned_data

    def save(self, commit=True):
        from django.db import transaction
        instance = super().save(commit=False)
        has_subproject = self.cleaned_data.get('has_subproject')
        subproject_name = self.cleaned_data.get('subproject_name')
        subproject_description = self.cleaned_data.get('subproject_description')
        organization = self.cleaned_data.get('organization')

        with transaction.atomic():
            if commit:
                instance.save()
                instance.organizations.set([organization])
                self.save_m2m()

                if has_subproject and subproject_name:
                    SubProject.objects.create(
                        project=instance,
                        name=subproject_name,
                        description=subproject_description,
                        is_active=True
                    )

            return instance
import logging
logger = logging.getLogger(__name__)
class ProjectForm(forms.ModelForm):
    has_subproject = forms.BooleanField(
        label=_("آیا ساب‌پروژه دارد؟"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    subproject_name = forms.CharField(
        label=_("نام ساب‌پروژه"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    subproject_description = forms.CharField(
        label=_("توضیحات ساب‌پروژه"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        label=_("شعبه"),
        widget=forms.Select(attrs={'class': 'form-control', 'data-control': 'select2'})
    )
    start_date = forms.CharField(
        label=_('تاریخ شروع'),  # Changed label slightly
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control form-control-lg jalali-datepicker',  # Added jalali-datepicker class
            'autocomplete': 'off',
            'placeholder': _('مثال: 1404/01/26')  # Updated placeholder
        }),
        required=True
    )
    end_date = forms.CharField(
            label=_('تاریخ خاتمه'),  # Changed label slightly
            widget=forms.TextInput(attrs={
                'data-jdp': '',
                'class': 'form-control form-control-lg jalali-datepicker',  # Added jalali-datepicker class
                'autocomplete': 'off',
                'placeholder': _('مثال: 1404/01/26')  # Updated placeholder
            }),
            required=True
        )

    class Meta:
        model = Project
        fields = [
            'name', 'code', 'priority', 'organization',
            'is_active', 'description', 'has_subproject', 'subproject_name',
            'subproject_description','start_date', 'end_date',
        ]#
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام پروژه')}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('کد پروژه')}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': _('توضیحات')}),
            'start_date': forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control jalali-datepicker', 'placeholder': '1404/01/17'}),
            'end_date': forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control jalali-datepicker', 'placeholder': '1404/01/17'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # محدود کردن سازمان‌ها به شعب فعال و قابل تخصیص بودجه
        self.fields['organization'].queryset = Organization.objects.filter( org_type__is_budget_allocatable=True, is_active=True
        ).select_related('org_type').order_by('name')

        # تنظیم مقادیر اولیه برای ویرایش پروژه
        if self.instance.pk:
            try:
                if self.instance.end_date:
                    # jalali_start = jdatetime.date.fromgregorian(date=self.instance.start_date).strftime('%Y/%m/%d')
                    # self.fields['start_date'].initial = jalali_start
                    j_date = jdatetime.date.fromgregorian(date=self.instance.start_date)
                    self.initial['start_date'] = j_date.strftime('%Y/%m/%d')

                if self.instance.end_date:

                    j_date = jdatetime.date.fromgregorian(date=self.instance.end_date)
                    self.initial['end_date'] = j_date.strftime('%Y/%m/%d')

                self.fields['organization'].initial = self.instance.organizations.first()
                if self.instance.subprojects.exists():
                    subproject = self.instance.subprojects.first()
                    self.fields['has_subproject'].initial = True
                    self.fields['subproject_name'].initial = subproject.name
                    self.fields['subproject_description'].initial = subproject.description
            except Exception as e:
                logger.error(f"Error setting initial values: {str(e)}")


    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        logger.debug(f"Cleaning start_date: input='{start_date}'")
        if not start_date:
            # This might be redundant if field is required=True
            raise ValidationError(_('تاریخ تخصیص اجباری است.'))
        try:
            # Use the utility function to parse
            from Tanbakhsystem.utils import parse_jalali_date
            parsed_date = parse_jalali_date(str(start_date), field_name=_('تاریخ شروع'))
            logger.debug(f"Parsed start_date: {parsed_date}")
            return parsed_date  # Return the Python date object
        except ValueError as e:  # Catch specific parsing errors
            logger.warning(f"Could not parse start_date '{start_date}': {e}")
            raise ValidationError(e)  # Show the specific error from parse_jalali_date
        except Exception as e:  # Catch other unexpected errors
            logger.error(f"Unexpected error parsing start_date '{start_date}': {e}", exc_info=True)
            raise ValidationError(_('فرمت تاریخ شروع نامعتبر است.'))

    def clean_end_date(self):
        end_date = self.cleaned_data.get('end_date')
        logger.debug(f"Cleaning end_date: input='{end_date}'")
        if not end_date:
            # This might be redundant if field is required=True
            raise ValidationError(_('تاریخ خاتمه اجباری است.'))
        try:
            # Use the utility function to parse
            from Tanbakhsystem.utils import parse_jalali_date
            parsed_date = parse_jalali_date(str(end_date), field_name=_('تاریخ خاتمه'))
            logger.debug(f"Parsed end_date: {parsed_date}")
            return parsed_date  # Return the Python date object
        except ValueError as e:  # Catch specific parsing errors
            logger.warning(f"Could not parse end_date '{end_date}': {e}")
            raise ValidationError(e)  # Show the specific error from parse_jalali_date
        except Exception as e:  # Catch other unexpected errors
            logger.error(f"Unexpected error parsing end_date '{end_date}': {e}", exc_info=True)
            raise ValidationError(_('فرمت تاریخ تخصیص نامعتبر است.'))




    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code:
            raise forms.ValidationError(_('کد پروژه اجباری است.'))
        if Project.objects.exclude(pk=self.instance.pk).filter(code=code).exists():
            raise forms.ValidationError(_('این کد پروژه قبلاً استفاده شده است.'))
        return code

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        has_subproject = cleaned_data.get('has_subproject')
        subproject_name = cleaned_data.get('subproject_name')

        # بررسی تاریخ‌ها
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError(_("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد."))

        # بررسی ساب‌پروژه
        if has_subproject and not subproject_name:
            self.add_error('subproject_name', _('نام ساب‌پروژه اجباری است.'))

        return cleaned_data

    def save(self, commit=True):
        from django.db import transaction
        instance = super().save(commit=False)
        has_subproject = self.cleaned_data.get('has_subproject')
        subproject_name = self.cleaned_data.get('subproject_name')
        subproject_description = self.cleaned_data.get('subproject_description')
        organization = self.cleaned_data.get('organization')

        with transaction.atomic():
            if commit:
                instance.save()
                instance.organizations.set([organization])
                self.save_m2m()

                if has_subproject and subproject_name:
                    SubProject.objects.create(
                        project=instance,
                        name=subproject_name,
                        description=subproject_description,
                        is_active=True
                    )

            return instance

class SubProjectForm(forms.ModelForm):

    allocated_budget = forms.DecimalField(label=_("بودجه ساب‌پروژه"), decimal_places=2, max_digits=25, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    class Meta:
        model = SubProject
        fields = ['project', 'name', 'description', 'allocated_budget', 'is_active']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام ساب‌پروژه')}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': _('توضیحات')}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            # 'allocated_budget': forms.NumberInput(attrs={'class': 'form-control', 'step': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Project.objects.filter(is_active=True)
        if self.instance.pk:  # ویرایش
            self.fields['allocated_budget'].initial = self.instance.allocated_budget
    #
    # def clean(self):
    #     cleaned_data = super().clean()
    #     project = cleaned_data.get('project')
    #     budget = cleaned_data.get('allocated_budget')
    #     if project and budget and budget > get_project_remaining_budget(project):
    #         raise ValidationError(
    #             _("بودجه ساب‌پروژه (%(budget)s) نمی‌تواند بیشتر از بودجه باقیمانده پروژه (%(remaining)s) باشد."),
    #             params={'budget': budget, 'remaining': get_project_remaining_budget(project)}
    #         )
    #     return cleaned_data

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get('project')
        allocated_budget = cleaned_data.get('allocated_budget')
        if project and allocated_budget:
            remaining_budget = project.get_remaining_budget()
            if allocated_budget > remaining_budget:
                self.add_error(
                    'allocated_budget',
                    _('بودجه تخصیص‌یافته نمی‌تواند بیشتر از بودجه باقی‌مانده پروژه باشد: %s') % remaining_budget
                )
        return cleaned_data

class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['code', 'name', 'org_type', 'description', 'parent_organization','is_core']
        # budget = forms.DecimalField(
        #     widget=NumberToWordsWidget(attrs={'placeholder': '  ارقام بودجه سالانه را وارد کنید'}),
        #     label='بودجه سالانه'
        # )

        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'org_type': forms.Select(attrs={'class': 'form-control'}),
            'is_core': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            # 'budget': forms.Select(attrs={'class': 'form-control'}),
            'parent_organization': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'code': _('کد سازمان'),
            'name': _('نام سازمان'),
            'org_type': _('نوع سازمان'),
            'is_core': _('شعبه اصلی سازمان(دفتر مرکزی)'),
            # 'budget': _('بودجه سالانه'),
            'parent_organization': _('نوع سازمان'),
            'description': _('توضیحات'),
        }
# -- new
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['name', 'organization', 'parent', 'level', 'branch', 'description','max_change_level','is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام پست'}),
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'level': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'max_change_level': forms.NumberInput(attrs={'class': 'form-control', 'min': 1,'max': 1, 'placeholder': 'حداکثر سطح تغییر(ارجاع به مرحله قبل تر)'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input' , 'placeholder': 'فعال'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['workflow_stages'] = forms.ModelMultipleChoiceField(
                queryset=WorkflowStage.objects.all(),
                widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
                required=False,
                label=_('مراحل تأیید'),
                initial=WorkflowStage.objects.filter(stageapprover__post=self.instance)
            )

    def save(self, commit=True):
        project = super().save(commit=False)
        if commit:
            project.save()
            self.save_m2m()
            if self.cleaned_data.get('has_subproject'):
                SubProject.objects.update_or_create(
                    project=project,
                    name=self.cleaned_data['subproject_name'],
                    defaults={'allocated_budget': self.cleaned_data['subproject_budget']}
                )
        return project

class UserPostForm(forms.ModelForm):
    class Meta:
        model = UserPost
        fields = ['user', 'post']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'post': forms.Select(attrs={'class': 'form-control'}),
        }

class PostHistoryForm(forms.ModelForm):
    # changed_at = jDateField(
    #     widget=forms.DateInput(attrs={'class': 'form-control', 'data-jdp': ''}),
    #     label='تاریخ تغییر'
    # )

    class Meta:
        model = PostHistory
        fields = ['post', 'changed_field', 'old_value', 'new_value',   'changed_by']
        widgets = {
            'post': forms.Select(attrs={'class': 'form-control'}),
            'changed_field': forms.TextInput(attrs={'class': 'form-control'}),
            'old_value': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'new_value': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'changed_by': forms.Select(attrs={'class': 'form-control'}),
        }

class WorkflowStageForm(forms.ModelForm):
    # is_active = forms.BooleanField(
    #     label=_("فعال"),
    #     widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    #     required=False,
    #     initial=True
    # )
    # is_final_stage = forms.BooleanField(
    #     label=_("مرحله نهایی تایید تنخواه"),
    #     widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    #     required=False,
    #     initial=True
    # )
    class Meta:
        model = WorkflowStage
        fields = ['name', 'order', 'description','is_active','is_final_stage']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام مرحله'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ترتیب'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'توضیحات'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input',  'placeholder': 'فعال'}),
            'is_final_stage': forms.CheckboxInput(attrs={'class': 'form-check-input', 'rows': 3, 'placeholder': 'مرحله نهایی تایید تنخواه'}),
        }
