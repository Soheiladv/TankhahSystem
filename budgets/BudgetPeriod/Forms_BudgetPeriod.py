import logging

import jdatetime
from django import forms
from django.utils.translation import gettext_lazy as _

from Tanbakhsystem.utils import format_jalali_date, parse_jalali_date
from budgets.models import BudgetPeriod, SystemSettings
from core.templatetags.rcms_custom_filters import number_to_farsi_words

logger = logging.getLogger(__name__)


def to_english_digits(text):
    """تبدیل اعداد فارسی به انگلیسی"""
    farsi_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    return str(text).translate(farsi_to_english)

class BudgetPeriodForm(forms.ModelForm):
    start_date = forms.CharField(
        label=_('تاریخ شروع'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control jalali-datepicker',
            'autocomplete': 'off'
        }),
        required=True
    )
    end_date = forms.CharField(
        label=_('تاریخ پایان'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control jalali-datepicker',
            'autocomplete': 'off'
        }),
        required=True
    )

    class Meta:
        model = BudgetPeriod
        fields = [
            'organization', 'name', 'start_date', 'end_date', 'total_amount', 'is_active',
            'is_archived', 'is_completed', 'lock_condition', 'locked_percentage',
            'warning_threshold', 'warning_action', 'description',
            # 'total_allocated', 'returned_amount', 'allocation_phase'  <-- حذف شدند
        ]
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-select', 'required': True}),
            # استفاده از form-select برای سازگاری با بوت استرپ 5+
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام دوره (مثل بودجه ۱۴۰۴)')}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_archived': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lock_condition': forms.Select(attrs={'class': 'form-select'}),  # استفاده از form-select
            'locked_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 0.01}),
            'warning_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 0.01}),
            'warning_action': forms.Select(attrs={'class': 'form-select'}),  # استفاده از form-select
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            # تغییر rows به 2 برای فضای بیشتر
        }
        labels = {
            'organization': _('دفتر مرکزی'),
            'name': _('نام دوره بودجه'),
            'total_amount': _('مبلغ کل (ریال)'),
            'is_active': _('فعال'),
            'is_archived': _('بایگانی شده'),
            'is_completed': _('تمام‌شده'),
            'lock_condition': _('شرط قفل'),
            'locked_percentage': _('درصد قفل (%)'),  # اضافه کردن واحد
            'warning_threshold': _('آستانه اخطار (%)'),  # اضافه کردن واحد
            'warning_action': _('اقدام هشدار'),
            'description': _('توضیحات'),  # اضافه کردن لیبل برای توضیحات
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        logger.debug("Initializing BudgetPeriodForm")
        # محدود کردن سازمان‌ها به دفاتر مرکزی فعال
        from core.models import Organization
        self.fields['organization'].queryset = Organization.objects.filter(is_core=True, is_active=True)
        # تنظیم مقادیر پیش‌فرض از SystemSettings
        system_settings = SystemSettings.objects.first()
        if system_settings:
            self.fields['locked_percentage'].initial = system_settings.budget_locked_percentage_default
            self.fields['warning_threshold'].initial = system_settings.budget_warning_threshold_default
            self.fields['warning_action'].initial = system_settings.budget_warning_action_default
        # تنظیم تاریخ‌های اولیه
        if self.instance and self.instance.pk:
            self.initial['start_date'] = format_jalali_date(self.instance.start_date)
            self.initial['end_date'] = format_jalali_date(self.instance.end_date)
            logger.debug(f"Set initial dates: start_date={self.initial['start_date']}, end_date={self.initial['end_date']}")
        else:
            current_jalali_year = jdatetime.date.today().year
            self.initial['start_date'] = f"{current_jalali_year}/01/01"
            self.initial['end_date'] = f"{current_jalali_year}/12/29"
            logger.debug(f"Set default dates for new instance: start={self.initial['start_date']}, end={self.initial['end_date']}")

        # مقدار حروف برای total_amount
        self.total_amount_words = ""
        if self.instance and self.instance.total_amount:
            self.total_amount_words = number_to_farsi_words(self.instance.total_amount)
            logger.info(f' self.total_amount_words  IS {self.total_amount_words}')

    def clean_start_date(self):
        date_str = self.cleaned_data.get('start_date')
        logger.debug(f"Cleaning start_date: input={date_str}")
        if not date_str:
            logger.error("start_date is empty")
            raise forms.ValidationError(_('تاریخ شروع اجباری است.'))
        try:
            date_str = to_english_digits(date_str)
            parsed_date = parse_jalali_date(date_str, field_name=_('تاریخ شروع'))
            logger.debug(f"Parsed start_date: {parsed_date}")
            return parsed_date
        except Exception as e:
            logger.error(f"Error parsing start_date: {str(e)}")
            raise forms.ValidationError(_('فرمت تاریخ شروع نامعتبر است.'))

    def clean_end_date(self):
        date_str = self.cleaned_data.get('end_date')
        logger.debug(f"Cleaning end_date: input={date_str}")
        if not date_str:
            logger.error("end_date is empty")
            raise forms.ValidationError(_('تاریخ پایان اجباری است.'))
        try:
            date_str = to_english_digits(date_str)
            parsed_date = parse_jalali_date(date_str, field_name=_('تاریخ پایان'))
            logger.debug(f"Parsed end_date: {parsed_date}")
            return parsed_date
        except Exception as e:
            logger.error(f"Error parsing end_date: {str(e)}")
            raise forms.ValidationError(_('فرمت تاریخ پایان نامعتبر است.'))

    def clean_total_amount(self):
        amount = self.cleaned_data.get('total_amount')
        logger.debug(f"Cleaning total_amount: input={amount}")
        if amount is None:
            logger.error("total_amount is None")
            raise forms.ValidationError(_('مبلغ کل نمی‌تواند خالی باشد.'))
        if amount <= 0:
            logger.error(f"Invalid total_amount: {amount} (must be positive)")
            raise forms.ValidationError(_('مبلغ کل باید بزرگ‌تر از صفر باشد.'))
        # به‌روزرسانی مقدار حروف
        self.total_amount_words = number_to_farsi_words(amount)
        logger.debug(f"Validated total_amount: {amount}, words: {self.total_amount_words}")
        return amount

    def clean_locked_percentage(self):
        percentage = self.cleaned_data.get('locked_percentage')
        logger.debug(f"Cleaning locked_percentage: input={percentage}")
        if percentage is None:
            logger.error("locked_percentage is None")
            raise forms.ValidationError(_('درصد قفل‌شده نمی‌تواند خالی باشد.'))
        if not (0 <= percentage <= 100):
            logger.error(f"Invalid locked_percentage: {percentage} (must be 0-100)")
            raise forms.ValidationError(_('درصد قفل‌شده باید بین ۰ تا ۱۰۰ باشد.'))
        logger.debug(f"Validated locked_percentage: {percentage}")
        return percentage

    def clean_warning_threshold(self):
        threshold = self.cleaned_data.get('warning_threshold')
        logger.debug(f"Cleaning warning_threshold: input={threshold}")
        if threshold is None:
            logger.error("warning_threshold is None")
            raise forms.ValidationError(_('آستانه اخطار نمی‌تواند خالی باشد.'))
        if not (0 <= threshold <= 100):
            logger.error(f"Invalid warning_threshold: {threshold} (must be 0-100)")
            raise forms.ValidationError(_('آستانه اخطار باید بین ۰ تا ۱۰۰ باشد.'))
        locked_percentage = self.cleaned_data.get('locked_percentage')
        if locked_percentage is not None and threshold <= locked_percentage:
            logger.error(f"warning_threshold ({threshold}) <= locked_percentage ({locked_percentage})")
            raise forms.ValidationError(_('آستانه اخطار باید بزرگ‌تر از درصد قفل‌شده باشد.'))
        logger.debug(f"Validated warning_threshold: {threshold}")
        return threshold

    def clean_organization(self):
        organization = self.cleaned_data.get('organization')
        logger.debug(f"Cleaning organization: input={organization}")
        if organization and not organization.is_core:
            logger.error(f"Selected organization {organization} is not core")
            raise forms.ValidationError(_('فقط دفاتر مرکزی می‌توانند برای بودجه کلان انتخاب شوند.'))
        return organization

    def clean(self):
        cleaned_data = super().clean()
        logger.debug(f"Running clean method: cleaned_data={cleaned_data}")
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_completed = cleaned_data.get('is_completed')
        is_active = cleaned_data.get('is_active')
        organization = cleaned_data.get('organization')
        name = cleaned_data.get('name')

        if start_date and end_date:
            if end_date <= start_date:
                logger.error(f"end_date ({end_date}) <= start_date ({start_date})")
                raise forms.ValidationError(_('تاریخ پایان باید بعد از تاریخ شروع باشد.'))
            overlapping_periods = BudgetPeriod.objects.filter(
                organization=organization,
                start_date__lte=end_date,
                end_date__gte=start_date
            ).exclude(pk=self.instance.pk)
            if overlapping_periods.exists():
                logger.error("Overlapping budget period detected")
                # raise forms.ValidationError(_('دوره بودجه با تاریخ‌های متداخل در این سازمان وجود دارد.'))
                # from django.contrib import messages
                # messages.success(self.request, _('دوره بودجه با موفقیت ایجاد شد.👍') + _(
                #     '💸دوره بودجه با تاریخ‌های متداخل در این سازمان وجود دارد.'))

            logger.debug("Validated date comparison")
        else:
            logger.warning(f"Missing dates: start_date={start_date}, end_date={end_date}")

        if is_completed and is_active:
            logger.error("is_completed and is_active both True")
            raise forms.ValidationError(_('دوره تمام‌شده نمی‌تواند فعال باشد.'))

        if organization and name:
            if BudgetPeriod.objects.filter(organization=organization, name=name).exclude(pk=self.instance.pk).exists():
                logger.error(f"Duplicate name '{name}' for organization {organization}")
                raise forms.ValidationError(_('نام دوره در این سازمان قبلاً استفاده شده است.'))
            logger.debug("Validated name uniqueness")

        logger.debug("Clean method completed successfully")
        return cleaned_data

    def save(self, commit=True):
        logger.debug("Saving BudgetPeriodForm")
        instance = super().save(commit=False)
        if not self.user or not self.user.is_authenticated:
            logger.error("No authenticated user provided")
            raise forms.ValidationError(_('کاربر معتبر برای ایجاد دوره بودجه لازم است.'))
        instance.created_by = self.user
        logger.debug(f"Set created_by: {instance.created_by}")
        if commit:
            try:
                instance.save()
                logger.info(f"BudgetPeriod saved: {instance}")
            except Exception as e:
                logger.error(f"Error saving BudgetPeriod: {str(e)}")
                raise
        return instance