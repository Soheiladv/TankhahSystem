# budgets/forms.py
from django import forms
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import jdatetime
import logging
from decimal import Decimal
from Tanbakhsystem.utils import parse_jalali_date
from budgets.models import BudgetAllocation, BudgetTransaction

logger = logging.getLogger(__name__)

class __Project_Budget_Allocation_Update_Form(forms.ModelForm):
    allocation_date = forms.CharField(
        label=_('تاریخ تخصیص'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control form-control-lg jalali-datepicker',
            'autocomplete': 'off',
            'placeholder': _('مثال: 1404/01/26')
        }),
        required=True
    )

    class Meta:
        model =  BudgetAllocation
        fields = ['project', 'subproject', 'allocated_amount', 'allocation_date', 'is_active', 'description']
        widgets = {
            'project': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': _('انتخاب پروژه'),
            }),
            'subproject': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': _('انتخاب زیرپروژه'),
            }),
            'allocated_amount': forms.TextInput(attrs={
                'class': 'form-control numeric-input',
                'placeholder': _('مبلغ به ریال'),
                'dir': 'ltr',
                'inputmode': 'numeric',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('توضیحات مربوط به تخصیص بودجه'),
            }),
        }
        labels = {
            'project': _('پروژه'),
            'subproject': _('زیرپروژه'),
            'allocated_amount': _('مبلغ تخصیص'),
            'allocation_date': _('تاریخ تخصیص'),
            'is_active': _('فعال'),
            'description': _('توضیحات'),
        }
        help_texts = {
            'allocated_amount': _('مبلغ را به ریال وارد کنید. مثال: 1,000,000'),
            'is_active': _('تخصیص را فعال یا غیرفعال کنید'),
            'allocation_date': _('تاریخ را به فرمت 1404/01/17 وارد کنید'),
        }

    def __init__(self, *args, organization_id=None, user=None, **kwargs):
        self.user = user
        self.organization_id = organization_id
        super().__init__(*args, **kwargs)

        if organization_id:
            # فیلتر پروژه‌ها بر اساس سازمان
            self.fields['project'].queryset = self.fields['project'].queryset.filter(
                organization_id=organization_id
            )
            # فیلتر زیرپروژه‌ها بر اساس پروژه انتخاب‌شده
            if self.instance and self.instance.project:
                self.fields['subproject'].queryset = self.fields['subproject'].queryset.filter(
                    project=self.instance.project
                )

        # غیرفعال کردن پروژه و زیرپروژه در ویرایش
        if self.instance and self.instance.pk:
            self.fields['project'].disabled = True
            self.fields['subproject'].disabled = True

        # تنظیم تاریخ اولیه
        if self.instance and self.instance.pk and self.instance.allocation_date:
            try:
                j_date = jdatetime.date.fromgregorian(date=self.instance.allocation_date)
                self.initial['allocation_date'] = j_date.strftime('%Y/%m/%d')
                logger.debug(f"Set initial allocation_date: {self.initial['allocation_date']}")
            except Exception as e:
                logger.error(f"Error formatting allocation_date: {e}")
                self.initial['allocation_date'] = jdatetime.date.today().strftime('%Y/%m/%d')
        else:
            self.initial['allocation_date'] = jdatetime.date.today().strftime('%Y/%m/%d')

    def clean_allocated_amount(self):
        allocated_amount = self.cleaned_data.get('allocated_amount')
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

        if allocated_amount <= 0:
            raise forms.ValidationError(_('مبلغ تخصیص باید مثبت باشد.'))

        # بررسی بودجه مصرف‌شده
        if self.instance and self.instance.pk:
            consumed = BudgetTransaction.objects.filter(
                allocation=self.instance.budget_allocation,
                project=self.instance.project,
                subproject=self.instance.subproject,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            returned = BudgetTransaction.objects.filter(
                allocation=self.instance.budget_allocation,
                project=self.instance.project,
                subproject=self.instance.subproject,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            net_consumed = consumed - returned
            if allocated_amount < net_consumed:
                raise forms.ValidationError(
                    f'مبلغ تخصیص نمی‌تواند کمتر از مبلغ مصرف‌شده ({net_consumed:,} ریال) باشد.'
                )

        # بررسی بودجه باقی‌مانده
        if self.instance and self.instance.budget_allocation:
            total_budget = self.instance.budget_allocation.allocated_amount
            other_allocations =  BudgetAllocation.objects.filter(
                budget_allocation=self.instance.budget_allocation,
                is_active=True
            ).exclude(id=self.instance.id).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
            consumed = BudgetTransaction.objects.filter(
                allocation=self.instance.budget_allocation,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            returned = BudgetTransaction.objects.filter(
                allocation=self.instance.budget_allocation,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            remaining_budget = total_budget - consumed + returned - other_allocations
            if allocated_amount > remaining_budget:
                raise forms.ValidationError(
                    f'مبلغ تخصیص نمی‌تواند بیشتر از بودجه باقی‌مانده ({remaining_budget:,} ریال) باشد.'
                )

        return allocated_amount

    def clean_allocation_date(self):
        date_str = self.cleaned_data.get('allocation_date')
        logger.debug(f"Cleaning allocation_date: input='{date_str}'")
        if not date_str:
            raise forms.ValidationError(_('تاریخ تخصیص اجباری است.'))
        try:
            parsed_date = parse_jalali_date(str(date_str), field_name=_('تاریخ تخصیص'))
            logger.debug(f"Parsed allocation_date: {parsed_date}")
            return parsed_date
        except ValueError as e:
            logger.warning(f"Could not parse allocation_date '{date_str}': {e}")
            raise forms.ValidationError(e)
        except Exception as e:
            logger.error(f"Unexpected error parsing allocation_date '{date_str}': {e}", exc_info=True)
            raise forms.ValidationError(_('فرمت تاریخ تخصیص نامعتبر است.'))

    def clean(self):
        cleaned_data = super().clean()
        allocation_date = cleaned_data.get('allocation_date')
        project = cleaned_data.get('project')

        if project and allocation_date and self.instance.budget_allocation:
            start_date = self.instance.budget_allocation.budget_period.start_date
            end_date = self.instance.budget_allocation.budget_period.end_date
            if not (start_date <= allocation_date <= end_date):
                raise forms.ValidationError(_('تاریخ تخصیص باید در بازه دوره بودجه باشد.'))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and self.user.is_authenticated:
            instance.modified_by = self.user
        else:
            raise forms.ValidationError(_('کاربر معتبر برای ویرایش تخصیص لازم است.'))
        if commit:
            try:
                instance.save()
                logger.info(f"ProjectBudgetAllocation {instance.pk} updated by {self.user}")
            except Exception as e:
                logger.error(f"Error saving ProjectBudgetAllocation: {str(e)}")
                raise
        return instance
#--------------

def parse_jalali_date(date_str, field_name=''):
    """تبدیل تاریخ جلالی به میلادی"""
    try:
        j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
        g_date = j_date.togregorian()
        logger.debug(f"Parsed jalali date {date_str} to gregorian {g_date.date()}")
        return g_date.date()
    except ValueError:
        logger.warning(f"Invalid jalali date format: {date_str}")
        raise forms.ValidationError(_(f'فرمت {field_name} نامعتبر است. از فرمت 1404/01/17 استفاده کنید.'))

class Project_Budget_Allocation_Update_Form(forms.ModelForm):
    # فیلد تاریخ تخصیص با ویجت تقویم جلالی
    allocation_date = forms.CharField(
        label=_('تاریخ تخصیص'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control form-control-lg jalali-datepicker',
            'autocomplete': 'off',
            'placeholder': _('مثال: 1404/01/26')
        }),
        required=True
    )

    class Meta:
        model =  BudgetAllocation
        fields = ['project', 'subproject', 'allocated_amount', 'allocation_date', 'is_active', 'description']
        widgets = {
            'project': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': _('انتخاب پروژه'),
            }),
            'subproject': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': _('انتخاب زیرپروژه'),
            }),
            'allocated_amount': forms.TextInput(attrs={
                'class': 'form-control numeric-input',
                'placeholder': _('مبلغ به ریال'),
                'dir': 'ltr',
                'inputmode': 'numeric',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('توضیحات مربوط به تخصیص بودجه'),
            }),
        }
        labels = {
            'project': _('پروژه'),
            'subproject': _('زیرپروژه'),
            'allocated_amount': _('مبلغ تخصیص'),
            'allocation_date': _('تاریخ تخصیص'),
            'is_active': _('فعال'),
            'description': _('توضیحات'),
        }
        help_texts = {
            'allocated_amount': _('مبلغ را به ریال وارد کنید. مثال: 1,000,000'),
            'is_active': _('تخصیص را فعال یا غیرفعال کنید'),
            'allocation_date': _('تاریخ را به فرمت 1404/01/17 وارد کنید'),
        }

    def __init__(self, *args, organization_id=None, user=None, **kwargs):
        """
        تنظیم اولیه فرم.
        - organization_id: برای فیلتر کردن پروژه‌ها.
        - user: برای ثبت کاربر ویرایش‌کننده.
        - غیرفعال کردن پروژه و زیرپروژه در ویرایش.
        - تنظیم تاریخ اولیه به فرمت جلالی.
        """
        self.user = user
        self.organization_id = organization_id
        super().__init__(*args, **kwargs)
        logger.debug(f"Initializing form with organization_id={organization_id}, user={user}")

        if organization_id:
            # فیلتر پروژه‌ها بر اساس سازمان
            self.fields['project'].queryset = self.fields['project'].queryset.filter(
                organization_id=organization_id
            )
            logger.debug(f"Filtered projects for organization_id={organization_id}")
            # فیلتر زیرپروژه‌ها بر اساس پروژه انتخاب‌شده
            if self.instance and self.instance.project:
                self.fields['subproject'].queryset = self.fields['subproject'].queryset.filter(
                    project=self.instance.project
                )
                logger.debug(f"Filtered subprojects for project={self.instance.project}")

        # غیرفعال کردن پروژه و زیرپروژه در ویرایش
        if self.instance and self.instance.pk:
            self.fields['project'].disabled = True
            self.fields['subproject'].disabled = True
            logger.debug("Disabled project and subproject fields for editing")

        # تنظیم تاریخ اولیه
        if self.instance and self.instance.pk and self.instance.allocation_date:
            try:
                j_date = jdatetime.date.fromgregorian(date=self.instance.allocation_date)
                self.initial['allocation_date'] = j_date.strftime('%Y/%m/%d')
                logger.debug(f"Set initial allocation_date: {self.initial['allocation_date']}")
            except Exception as e:
                logger.error(f"Error formatting allocation_date: {str(e)}")
                self.initial['allocation_date'] = jdatetime.date.today().strftime('%Y/%m/%d')
        else:
            self.initial['allocation_date'] = jdatetime.date.today().strftime('%Y/%m/%d')
            logger.debug(f"Set default allocation_date: {self.initial['allocation_date']}")

    def clean_allocated_amount(self):
        """
        اعتبارسنجی مبلغ تخصیص.
        - مطمئن می‌شه مبلغ معتبر و مثبت باشه.
        - چک می‌کنه که مبلغ از مصرف‌شده کمتر نباشه.
        - چک می‌کنه که مبلغ از بودجه باقی‌مانده بیشتر نباشه.
        """
        allocated_amount = self.cleaned_data.get('allocated_amount')
        logger.debug(f"Cleaning allocated_amount: {allocated_amount}")
        if not allocated_amount:
            logger.warning("Allocated amount is empty")
            raise forms.ValidationError(_('مبلغ تخصیص اجباری است.'))

        # تبدیل مقدار ورودی به عدد
        try:
            if isinstance(allocated_amount, str):
                allocated_amount = allocated_amount.replace(',', '').replace('،', '')
                allocated_amount = float(allocated_amount)
            allocated_amount = Decimal(allocated_amount)
            logger.debug(f"Converted allocated_amount to Decimal: {allocated_amount}")
        except (ValueError, TypeError):
            logger.warning(f"Invalid allocated_amount format: {allocated_amount}")
            raise forms.ValidationError(_('مقدار تخصیص نامعتبر است.'))

        if allocated_amount <= 0:
            logger.warning(f"Allocated amount is non-positive: {allocated_amount}")
            raise forms.ValidationError(_('مبلغ تخصیص باید مثبت باشد.'))

        # بررسی بودجه مصرف‌شده
        if self.instance and self.instance.pk:
            consumed = BudgetTransaction.objects.filter(
                allocation=self.instance.budget_allocation,
                project=self.instance.project,
                subproject=self.instance.subproject,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            returned = BudgetTransaction.objects.filter(
                allocation=self.instance.budget_allocation,
                project=self.instance.project,
                subproject=self.instance.subproject,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            net_consumed = consumed - returned
            logger.debug(f"Net consumed: {net_consumed}")
            if allocated_amount < net_consumed:
                logger.warning(f"Allocated amount {allocated_amount} is less than net consumed {net_consumed}")
                raise forms.ValidationError(
                    f'مبلغ تخصیص نمی‌تواند کمتر از مبلغ مصرف‌شده ({net_consumed:,} ریال) باشد.'
                )

        # بررسی بودجه باقی‌مانده
        if self.instance and self.instance.budget_allocation:
            total_budget = self.instance.budget_allocation.allocated_amount
            other_allocations =  BudgetAllocation.objects.filter(
                budget_allocation=self.instance.budget_allocation,
                is_active=True
            ).exclude(id=self.instance.id).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
            consumed = BudgetTransaction.objects.filter(
                allocation=self.instance.budget_allocation,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            returned = BudgetTransaction.objects.filter(
                allocation=self.instance.budget_allocation,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            remaining_budget = total_budget - consumed + returned - other_allocations
            logger.debug(f"Remaining budget: {remaining_budget}")
            if allocated_amount > remaining_budget:
                logger.warning(f"Allocated amount {allocated_amount} exceeds remaining budget {remaining_budget}")
                raise forms.ValidationError(
                    f'مبلغ تخصیص نمی‌تواند بیشتر از بودجه باقی‌مانده ({remaining_budget:,} ریال) باشد.'
                )

        return allocated_amount

    def clean_allocation_date(self):
        """
        اعتبارسنجی تاریخ تخصیص.
        - تاریخ جلالی رو به میلادی تبدیل می‌کنه.
        - مطمئن می‌شه تاریخ معتبر باشه.
        """
        date_str = self.cleaned_data.get('allocation_date')
        logger.debug(f"Cleaning allocation_date: input='{date_str}'")
        if not date_str:
            logger.warning("Allocation date is empty")
            raise forms.ValidationError(_('تاریخ تخصیص اجباری است.'))
        try:
            parsed_date = parse_jalali_date(str(date_str), field_name=_('تاریخ تخصیص'))
            logger.debug(f"Parsed allocation_date: {parsed_date}")
            return parsed_date
        except ValueError as e:
            logger.warning(f"Could not parse allocation_date '{date_str}': {str(e)}")
            raise forms.ValidationError(str(e))
        except Exception as e:
            logger.error(f"Unexpected error parsing allocation_date '{date_str}': {str(e)}", exc_info=True)
            raise forms.ValidationError(_('فرمت تاریخ تخصیص نامعتبر است.'))

    def clean(self):
        """
        اعتبارسنجی کلی فرم.
        - چک می‌کنه که تاریخ تخصیص در بازه دوره بودجه باشه.
        """
        cleaned_data = super().clean()
        allocation_date = cleaned_data.get('allocation_date')
        project = cleaned_data.get('project')
        logger.debug(f"Cleaning form, allocation_date={allocation_date}, project={project}")

        if project and allocation_date and self.instance.budget_allocation:
            start_date = self.instance.budget_allocation.budget_period.start_date
            end_date = self.instance.budget_allocation.budget_period.end_date
            logger.debug(f"Budget period: start={start_date}, end={end_date}")
            if not (start_date <= allocation_date <= end_date):
                logger.warning(f"Allocation date {allocation_date} is outside budget period {start_date} to {end_date}")
                raise forms.ValidationError(_('تاریخ تخصیص باید در بازه دوره بودجه باشد.'))

        return cleaned_data

    def save(self, commit=True):
        """
        ذخیره تخصیص.
        - کاربر ویرایش‌کننده رو ثبت می‌کنه.
        - تخصیص رو در دیتابیس ذخیره می‌کنه.
        """
        instance = super().save(commit=False)
        if self.user and self.user.is_authenticated:
            instance.modified_by = self.user
            logger.debug(f"Setting modified_by to user {self.user}")
        else:
            logger.error("No authenticated user provided for saving allocation")
            raise forms.ValidationError(_('کاربر معتبر برای ویرایش تخصیص لازم است.'))
        if commit:
            try:
                instance.save()
                logger.info(f"ProjectBudgetAllocation {instance.pk} updated by {self.user}")
            except Exception as e:
                logger.error(f"Error saving ProjectBudgetAllocation: {str(e)}", exc_info=True)
                raise
        return instance