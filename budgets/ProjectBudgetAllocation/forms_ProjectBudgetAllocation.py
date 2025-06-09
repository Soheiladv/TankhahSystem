from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
import jdatetime
import re
from django.utils.translation import gettext_lazy as _
from budgets.models import BudgetAllocation, BudgetAllocation
from core.models import Project, SubProject
import logging

logger = logging.getLogger(__name__)

def to_english_digits(text):
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    translation_table = str.maketrans(persian_digits, english_digits)
    return text.translate(translation_table)

class ProjectBudgetAllocationForm(forms.ModelForm):
    allocation_date = forms.CharField(
        label=_('تاریخ تخصیص'),  # Changed label slightly
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control form-control-lg jalali-datepicker',  # Added jalali-datepicker class
            'autocomplete': 'off',
            'placeholder': _('مثال: 1404/01/26')  # Updated placeholder
        }),
        required=True
    )
    class Meta:
        model = BudgetAllocation
        fields = [ 'project', 'subproject', 'allocated_amount', 'allocation_date', 'description'] #'budget_allocation',
        widgets = {
            # 'budget_allocation': forms.Select(attrs={
            #     'class': 'form-select select2',
            #     'data-placeholder': _('انتخاب تخصیص بودجه شعبه'),
            # }),
            'project': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': _('انتخاب پروژه'),
            }),
            'subproject': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': _('انتخاب زیرپروژه (اختیاری)'),
            }),
            'allocated_amount': forms.TextInput(attrs={  # تغییر به TextInput برای پشتیبانی از اعداد پارسی
                'class': 'form-control numeric-input',
                'placeholder': _('مبلغ به ریال یا درصد'),
                'dir': 'ltr',
                'inputmode': 'numeric',
            }),
            'allocation_date': forms.DateInput(attrs={
                'data-jdp': 'true',
                'class': 'form-control form-control-lg jalali-datepicker',
                'autocomplete': 'off',
                'placeholder': _('مثال: 1404/01/26'),
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('توضیحات مربوط به تخصیص بودجه'),
            }),

        }
        labels = {
            'budget_allocation': _('تخصیص بودجه شعبه'),
            'project': _('پروژه'),
            'subproject': _('زیرپروژه (اختیاری)'),
            'allocated_amount': _('مبلغ تخصیص'),
            'allocation_date': _('تاریخ تخصیص'),
            'is_active': _('فعال'),
            'description': _('توضیحات'),
        }
        help_texts = {
            'allocated_amount': _('مبلغ یا درصد را وارد کنید. مثال: 1,000,000 یا 10%'),
            'subproject': _('در صورتی که بودجه به زیرپروژه خاصی تعلق دارد انتخاب کنید'),
            'allocation_date': _('تاریخ را به فرمت 1404/01/17 وارد کنید'),
        }

    def __init__(self, *args, organization_id=None, user=None, **kwargs):
        self.user = user
        self.organization_id = organization_id
        super().__init__(*args, **kwargs)

        # اگر نمونه تخصیص وجود دارد
        if self.instance and self.instance.pk:
            if not self.instance.is_active:
                logger.warning(f"Editing inactive allocation {self.instance.id}")
                # اختیاری: غیرفعال کردن برخی فیلدها
                # self.fields['allocated_amount'].disabled = True
            if not self.instance.budget_allocation.budget_period.is_active:
                logger.warning(f"Editing allocation {self.instance.id} with inactive budget period")
                # اختیاری: نمایش پیام یا غیرفعال کردن فیلدها
                self.fields['allocated_amount'].disabled = True

        # فیلتر کردن تخصیص‌های بودجه
        if organization_id:
            budget_allocations = BudgetAllocation.objects.filter(
                organization_id=organization_id,
                is_active=True,
                budget_period__is_active=True
            )
            self.fields['budget_allocation'].queryset = budget_allocations

            self.fields['project'].queryset = Project.objects.filter(
                organizations__id=organization_id,
                is_active=True
            )
            self.fields['subproject'].queryset = SubProject.objects.filter(
                project__organizations__id=organization_id,
                is_active=True
            )

            if budget_allocations.exists() and not self.initial.get('budget_allocation'):
                self.initial['budget_allocation'] = budget_allocations.first().id
                logger.info(f"Set default budget_allocation to ID {self.initial['budget_allocation']}")

        # تنظیم تاریخ اولیه
        if not self.initial.get('allocation_date'):
            if self.instance and self.instance.pk and self.instance.allocation_date:
                try:
                    self.initial['allocation_date'] = jdatetime.date.fromgregorian(
                        date=self.instance.allocation_date
                    ).strftime('%Y/%m/%d')
                    logger.debug(f"Set initial allocation_date from instance: {self.initial['allocation_date']}")
                except Exception as e:
                    logger.error(f"Error formatting existing allocation date: {e}")
                    self.initial['allocation_date'] = jdatetime.date.today().strftime('%Y/%m/%d')
            else:
                self.initial['allocation_date'] = jdatetime.date.today().strftime('%Y/%m/%d')
                logger.debug(f"Set default allocation_date for new instance: {self.initial['allocation_date']}")


    def clean_allocated_amount(self):
        allocated_amount = self.cleaned_data.get('allocated_amount')
        input_mode = self.data.get('input_mode', 'amount')
        budget_allocation = self.cleaned_data.get('budget_allocation')

        if not allocated_amount:
            raise forms.ValidationError(_('مبلغ تخصیص اجباری است.'))

        # تبدیل مقدار ورودی به عدد
        try:
            if isinstance(allocated_amount, str):
                allocated_amount = allocated_amount.replace(',', '').replace('،', '')
                allocated_amount = float(allocated_amount)
            allocated_amount = Decimal(allocated_amount)
        except (ValueError, TypeError):
            raise forms.ValidationError(_('مقدار تخصیص نامعتبر است.'))

        if input_mode == 'percent':
            if allocated_amount < 0 or allocated_amount > 100:
                raise forms.ValidationError(_('درصد باید بین 0 تا 100 باشد.'))
            if budget_allocation:
                allocated_amount = (allocated_amount / 100) * budget_allocation.allocated_amount
                allocated_amount = allocated_amount.quantize(Decimal('1.'))  # گرد کردن به عدد صحیح

        if allocated_amount <= 0:
            raise forms.ValidationError(_('مبلغ تخصیص باید مثبت باشد.'))

        if budget_allocation:
            remaining = budget_allocation.get_remaining_amount()
            if allocated_amount > remaining:
                raise forms.ValidationError(
                    f'مبلغ تخصیص بیشتر از باقی‌مانده بودجه ({remaining:,} ریال) است.'
                )

        return allocated_amount

    # * def clean_allocation_date(self):
    #      date_input = self.cleaned_data.get('allocation_date')
    #      if not date_input:
    #          raise forms.ValidationError(_('تاریخ تخصیص اجباری است.'))
    #      if isinstance(date_input, jdatetime.date):
    #          return date_input.togregorian()
    #      raise forms.ValidationError(_('تاریخ نامعتبر است.'))


    def clean_allocation_date(self):
        """Parse Jalali date string to Python date object."""
        date_str = self.cleaned_data.get('allocation_date')
        logger.debug(f"Cleaning allocation_date: input='{date_str}'")
        if not date_str:
            # This might be redundant if field is required=True
            raise ValidationError(_('تاریخ تخصیص اجباری است.'))
        try:
            # Use the utility function to parse
            from Tanbakhsystem.utils import parse_jalali_date
            parsed_date = parse_jalali_date(str(date_str), field_name=_('تاریخ تخصیص'))
            logger.debug(f"Parsed allocation_date: {parsed_date}")
            return parsed_date  # Return the Python date object
        except ValueError as e:  # Catch specific parsing errors
            logger.warning(f"Could not parse allocation_date '{date_str}': {e}")
            raise ValidationError(e)  # Show the specific error from parse_jalali_date
        except Exception as e:  # Catch other unexpected errors
            logger.error(f"Unexpected error parsing allocation_date '{date_str}': {e}", exc_info=True)
            raise ValidationError(_('فرمت تاریخ تخصیص نامعتبر است.'))

    def clean(self):
        cleaned_data = super().clean()
        budget_allocation = cleaned_data.get('budget_allocation')
        project = cleaned_data.get('project')
        subproject = cleaned_data.get('subproject')
        allocation_date = cleaned_data.get('allocation_date')

        if not budget_allocation:
            raise forms.ValidationError(_('لطفاً یک تخصیص بودجه انتخاب کنید.'))
        if not project:
            raise forms.ValidationError(_('لطفاً یک پروژه انتخاب کنید.'))
        if subproject and subproject.project != project:
            raise forms.ValidationError(_('زیرپروژه باید متعلق به پروژه انتخاب‌شده باشد.'))

        if allocation_date and budget_allocation:
            start_date = budget_allocation.budget_period.start_date
            end_date = budget_allocation.budget_period.end_date
            if not (start_date <= allocation_date <= end_date):
                raise forms.ValidationError(_('تاریخ تخصیص باید در بازه دوره بودجه باشد.'))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and self.user.is_authenticated:
            instance.created_by = self.user
        else:
            raise forms.ValidationError(_('کاربر معتبر برای ایجاد تخصیص لازم است.'))
        if commit:
            try:
                instance.save()
                # instance.budget_allocation.remaining_amount = instance.budget_allocation.get_remaining_amount()
                # instance.budget_allocation.save(update_fields=['remaining_amount'])
            except Exception as e:
                logger.error(f"Error saving BudgetAllocation: {str(e)}")
                raise
        return instance
