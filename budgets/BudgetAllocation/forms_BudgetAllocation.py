import logging
from time import timezone

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
    ALLOCATION_TYPE_CHOICES = [
        ('amount', _('مبلغ')),
        ('percent', _('درصد')),
    ]

    WARNING_ACTION_CHOICES = [
        ('email', _('ارسال ایمیل هشدار')),
        ('sms', _('ارسال پیامک هشدار')),
        ('notification', _('ارسال اعلان سیستم')),
    ]

    allocation_type = forms.ChoiceField(
        choices=ALLOCATION_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label=_('نوع تخصیص'),
        initial='amount'
    )

    warning_action = forms.ChoiceField(
        choices=WARNING_ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
        label=_('اقدام هشدار'),
        required=False
    )
    allocation_date = forms.CharField(
        label=_('تاریخ تخصیص بودجه'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control jalali-datepicker',
            'autocomplete': 'off'
        }),
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
                'data-placeholder': _('انتخاب سازمان')
            }),
            'project': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'required': 'required',
                'data-control': 'select2',
                'data-placeholder': _('انتخاب پروژه')
            }),
            'allocated_amount': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg numeric-input',
                'min': '0',
                'step': '1',
                'inputmode': 'numeric',
                'required': 'required',
                'placeholder': _('مبلغ را وارد کنید')
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
                'placeholder': _('توضیحات تخصیص بودجه')
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
            'locked_percentage': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'min': '0',
                'max': '100',
                'step': '1',
                'inputmode': 'numeric',
                'placeholder': '0-100'
            }),
            'warning_threshold': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'min': '0',
                'max': '100',
                'step': '1',
                'inputmode': 'numeric',
                'placeholder': '0-100'
            }),
            'allocation_number': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'min': '0',
                'step': '1',
                'inputmode': 'numeric',
                'placeholder': _('شماره تخصیص')
            }),
            'budget_period': forms.HiddenInput(),
        }
        labels = {
            'organization': _('سازمان'),
            'project': _('پروژه'),
            'allocated_amount': _('مبلغ تخصیص'),
            'allocation_date': _('تاریخ تخصیص'),
            'description': _('شرح'),
            'is_active': _('فعال'),
            'is_stopped': _('متوقف شده'),
            'locked_percentage': _('درصد قفل شده'),
            'warning_threshold': _('آستانه اخطار'),
            'allocation_number': _('شماره تخصیص'),
        }
        help_texts = {
            'locked_percentage': _('درصدی از بودجه که پس از رسیدن به آن، تخصیص جدید غیرفعال می‌شود'),
            'warning_threshold': _('درصدی از بودجه که پس از رسیدن به آن، هشدار ارسال می‌شود'),
        }

    def __init__(self, *args, **kwargs):
        self.budget_period = kwargs.pop('budget_period', None)
        self.user = kwargs.pop('user', None)
        logger.debug(f"Initializing BudgetAllocationForm with budget_period={self.budget_period}, user={self.user}")

        super().__init__(*args, **kwargs)

        # تنظیم کوئری‌ست برای سازمان‌های قابل تخصیص بودجه
        allowed_org_types = OrganizationType.objects.filter(
            is_budget_allocatable=True
        ).values_list('id', flat=True)

        self.fields['organization'].queryset = Organization.objects.filter(
            org_type__in=allowed_org_types,
            is_active=True
        ).select_related('org_type')

        # تنظیم کوئری‌ست برای پروژه‌های فعال
        # self.fields['project'].queryset = Project.objects.filter(
        #     is_active=True
        # ).select_related('category')
        # تنظیم تاریخ‌های اولیه
        if self.instance and self.instance.pk:
            from Tanbakhsystem.utils import format_jalali_date
            self.initial['allocation_date'] = format_jalali_date(self.instance.allocation_date)

            logger.debug(
                f"Set initial dates: start_date={self.initial['allocation_date']}")
        else:
            current_jalali_year = jdatetime.date.today().year
            self.initial['allocation_date'] = f"{current_jalali_year}/01/01"
            logger.debug(
                f"Set default dates for new instance: start={self.initial['allocation_date']}")


        if self.budget_period:
            self.fields['budget_period'].initial = self.budget_period
            # فیلتر سازمان‌هایی که قبلاً برای این دوره بودجه تخصیص داده‌اند
            allocated_orgs = BudgetAllocation.objects.filter(
                budget_period=self.budget_period
            ).values_list('organization_id', flat=True)

            if allocated_orgs:
                self.fields['organization'].queryset = self.fields['organization'].queryset.filter(
                    id__in=allocated_orgs
                )

            logger.debug(
                f"Filtered organization queryset: {list(self.fields['organization'].queryset.values('id', 'name'))}")

        # تبدیل تاریخ میلادی به شمسی برای نمایش
        if self.instance.pk and self.instance.allocation_date:
            j_date = jdatetime.date.fromgregorian(date=self.instance.allocation_date)
            self.initial['allocation_date'] = j_date.strftime('%Y/%m/%d')

    def clean_allocation_date(self):
        date_input = self.cleaned_data.get('allocation_date')
        logger.debug(f"Cleaning allocation_date: input={date_input}, type={type(date_input)}")

        if not date_input:
            raise forms.ValidationError(_('تاریخ تخصیص اجباری است.'))

        if isinstance(date_input, date):
            return date_input

        try:
            date_str = to_english_digits(str(date_input).strip())
            date_str = re.sub(r'[-\.]', '/', date_str)
            # پشتیبانی از فرمت YYYY/MM/DD
            try:
                if re.match(r'^\d{4}/\d{2}/\d{2}$', date_str):
                    j_date = jdatetime.date.strptime(date_str, '%Y/%m/%d')
                    g_date = j_date.togregorian()
                    logger.debug(f"Parsed allocation_date: {g_date}")
                    return g_date
            except ValueError:
                pass
            # پشتیبانی از فرمت میلادی YYYY-MM-DD
            try:
                if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                    g_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    logger.debug(f"Parsed gregorian date: {g_date}")
                    return g_date
            except ValueError:
                pass
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17 یا 2025-04-01).'))
        except Exception as e:
            logger.error(f"Error parsing date: {str(e)}")
            raise forms.ValidationError(_('خطا در پردازش تاریخ.'))



    def clean(self):
        cleaned_data = super().clean()
        logger.debug(f"Running clean method: cleaned_data={cleaned_data}")

        organization = cleaned_data.get('organization')
        project = cleaned_data.get('project')
        allocated_amount = cleaned_data.get('allocated_amount')
        allocation_date = cleaned_data.get('allocation_date')
        budget_period = cleaned_data.get('budget_period')
        allocation_type = cleaned_data.get('allocation_type')
        locked_percentage = cleaned_data.get('locked_percentage')
        warning_threshold = cleaned_data.get('warning_threshold')

        # اعتبارسنجی دوره بودجه
        if not budget_period:
            logger.error("No budget_period selected")
            raise forms.ValidationError(_("دوره بودجه باید انتخاب شود."))

        # اعتبارسنجی سازمان
        if not organization:
            logger.error("No organization selected")
            raise forms.ValidationError(_('لطفاً یک سازمان انتخاب کنید.'))

        # اعتبارسنجی پروژه
        if not project:
            logger.error("No project selected")
            raise forms.ValidationError(_('لطفاً یک پروژه انتخاب کنید.'))

        # اعتبارسنجی مبلغ تخصیص
        if allocated_amount is None or allocated_amount <= 0:
            logger.error(f"Invalid allocated_amount: {allocated_amount}")
            raise forms.ValidationError(_('مبلغ تخصیص باید مثبت باشد.'))

        # اعتبارسنجی ارتباط سازمان و پروژه
        if organization and project:
            if not project.organizations.filter(id=organization.id).exists():
                logger.error(f"Project {project} does not belong to organization {organization}")
                raise forms.ValidationError(_('پروژه انتخاب‌شده متعلق به این سازمان نیست.'))

        # محاسبه بودجه باقیمانده
        if budget_period and allocated_amount:
            used_budget = BudgetAllocation.objects.filter(
                budget_period=budget_period
            ).exclude(id=self.instance.id).aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')

            remaining_budget = budget_period.total_amount - used_budget

            # اگر نوع تخصیص درصد باشد، محاسبه مبلغ معادل
            if allocation_type == 'percent':
                allocated_amount = (allocated_amount / 100) * budget_period.total_amount

            if allocated_amount > remaining_budget:
                logger.error(f"allocated_amount ({allocated_amount}) exceeds remaining_budget ({remaining_budget})")
                raise forms.ValidationError(_(
                    f'مبلغ تخصیص ({allocated_amount:,} ریال) بیشتر از بودجه باقی‌مانده ({remaining_budget:,} ریال) است.'
                ))

        # اعتبارسنجی تاریخ تخصیص
        if allocation_date and budget_period:
            start_date = budget_period.start_date
            end_date = budget_period.end_date

            if allocation_date < start_date or allocation_date > end_date:
                logger.error(f"allocation_date ({allocation_date}) outside budget_period range")
                raise forms.ValidationError(_('تاریخ تخصیص باید در بازه دوره بودجه باشد.'))

        # اعتبارسنجی درصدها
        if locked_percentage is not None and (locked_percentage < 0 or locked_percentage > 100):
            raise forms.ValidationError(_('درصد قفل‌شده باید بین ۰ تا ۱۰۰ باشد.'))

        if warning_threshold is not None and (warning_threshold < 0 or warning_threshold > 100):
            raise forms.ValidationError(_('آستانه اخطار باید بین ۰ تا ۱۰۰ باشد.'))

        if locked_percentage is not None and warning_threshold is not None:
            if locked_percentage >= warning_threshold:
                raise forms.ValidationError(_('آستانه اخطار باید بزرگتر از درصد قفل‌شده باشد.'))

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



