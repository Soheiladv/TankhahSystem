from pydoc import visiblename

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from Tanbakhsystem.utils import convert_to_farsi_numbers, parse_jalali_date, format_jalali_date
from Tanbakhsystem.widgets import NumberToWordsWidget
from core.models import Organization
from .models import BudgetPeriod, BudgetAllocation, BudgetTransaction, PaymentOrder, Payee, TransactionType, \
    ProjectBudgetAllocation, SystemSettings
import jdatetime
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# تابع کمکی برای تبدیل اعداد فارسی به انگلیسی
def to_english_digits(text):
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    translation_table = str.maketrans(persian_digits, english_digits)
    return text.translate(translation_table)

# budgets/forms.py

class BudgetPeriodForm(forms.ModelForm):
    """فرم دوره بودجه کلان با تاریخ شمسی و اعتبارسنجی‌های پیشرفته"""
    start_date = forms.CharField(
        label=_('تاریخ شروع'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('1404/01/17'),
            'autocomplete': 'off'
        })
    )
    end_date = forms.CharField(
        label=_('تاریخ پایان'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('1404/12/29'),
            'autocomplete': 'off'
        })
    )

    class Meta:
        model = BudgetPeriod
        fields = [
            'organization', 'name', 'start_date', 'end_date', 'total_amount',
            'is_active', 'is_archived', 'is_completed', 'lock_condition',
            'locked_percentage', 'warning_threshold', 'warning_action'
        ]
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام دوره (مثل بودجه ۱۴۰۴)')}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('مبلغ کل'), 'min': 1}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_archived': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lock_condition': forms.Select(attrs={'class': 'form-control'}),
            'locked_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 0.01}),
            'warning_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 0.01}),
            'warning_action': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'organization': _('دفتر مرکزی'),
            'name': _('نام دوره بودجه'),
            'total_amount': _('مبلغ کل (ریال)'),
            'is_active': _('فعال'),
            'is_archived': _('بایگانی شده'),
            'is_completed': _('تمام‌شده'),
            'lock_condition': _('شرط قفل'),
            'locked_percentage': _('درصد قفل‌شده'),
            'warning_threshold': _('آستانه اخطار'),
            'warning_action': _('اقدام هشدار'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تنظیم مقادیر اولیه تاریخ‌ها برای نمایش شمسی
        if self.instance and self.instance.pk:
            self.initial['start_date'] = format_jalali_date(self.instance.start_date)
            self.initial['end_date'] = format_jalali_date(self.instance.end_date)

    def clean_start_date(self):
        date_str = self.cleaned_data.get('start_date')
        return parse_jalali_date(date_str, field_name=_('تاریخ شروع'))

    def clean_end_date(self):
        date_str = self.cleaned_data.get('end_date')
        return parse_jalali_date(date_str, field_name=_('تاریخ پایان'))

    def clean_total_amount(self):
        amount = self.cleaned_data.get('total_amount')
        if amount is None or amount <= 0:
            raise forms.ValidationError(_('مبلغ کل باید بزرگ‌تر از صفر باشد.'))
        return amount

    def clean_locked_percentage(self):
        percentage = self.cleaned_data.get('locked_percentage')
        if percentage is None or not (0 <= percentage <= 100):
            raise forms.ValidationError(_('درصد قفل‌شده باید بین ۰ تا ۱۰۰ باشد.'))
        return percentage

    def clean_warning_threshold(self):
        threshold = self.cleaned_data.get('warning_threshold')
        if threshold is None or not (0 <= threshold <= 100):
            raise forms.ValidationError(_('آستانه اخطار باید بین ۰ تا ۱۰۰ باشد.'))
        locked_percentage = self.cleaned_data.get('locked_percentage')
        if locked_percentage is not None and threshold <= locked_percentage:
            raise forms.ValidationError(_('آستانه اخطار باید بزرگ‌تر از درصد قفل‌شده باشد.'))
        return threshold

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_completed = cleaned_data.get('is_completed')
        is_active = cleaned_data.get('is_active')
        if start_date and end_date:
            if end_date <= start_date:
                raise forms.ValidationError(_('تاریخ پایان باید بعد از تاریخ شروع باشد.'))
            if start_date < timezone.now().date():
                raise forms.ValidationError(_('تاریخ شروع نمی‌تواند در گذشته باشد.'))

        if is_completed and is_active:
            raise forms.ValidationError(_('دوره تمام‌شده نمی‌تواند فعال باشد.'))

        logger.info(cleaned_data,start_date,end_date,is_completed,is_active)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.created_by = self.initial.get('created_by', None)
        if commit:
            instance.save()
        return instance


class BudgetTransactionForm(forms.ModelForm):
    class Meta:
        model = BudgetTransaction
        fields = ['allocation', 'transaction_type', 'amount', 'related_tankhah', 'description']
        widgets = {
            'allocation': forms.Select(attrs={'class': 'form-control'}),
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('مبلغ')}),
            'related_tankhah': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'allocation': _('تخصیص بودجه'),
            'transaction_type': _('نوع تراکنش'),
            'amount': _('مبلغ'),
            'related_tankhah': _('تنخواه مرتبط'),
            'description': _('توضیحات'),
        }

    def clean_amount(self):
        amount_str = self.cleaned_data.get('amount', '')
        if amount_str is None or str(amount_str).strip() == '':
            raise forms.ValidationError(_("وارد کردن مبلغ الزامی است."))
        try:
            english_amount_str = to_english_digits(str(amount_str)).replace(',', '')
            amount_decimal = Decimal(english_amount_str)
            amount_int = int(round(amount_decimal))
            if amount_int <= 0:
                raise forms.ValidationError(_("مبلغ باید بزرگ‌تر از صفر باشد."))
            return amount_int
        except (ValueError, TypeError):
            raise forms.ValidationError(_("لطفاً یک عدد معتبر برای مبلغ وارد کنید."))

class PaymentOrderForm(forms.ModelForm):
    issue_date = forms.CharField(
        label=_('تاریخ صدور'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('تاریخ را انتخاب کنید (1404/01/17)')
        })
    )

    class Meta:
        model = PaymentOrder
        fields = ['tankhah', 'amount', 'payee', 'description', 'related_factors', 'status', 'min_signatures']
        widgets = {
            'tankhah': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('مبلغ')}),
            'payee': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'related_factors': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'min_signatures': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
        labels = {
            'tankhah': _('تنخواه'),
            'amount': _('مبلغ'),
            'payee': _('دریافت‌کننده'),
            'description': _('شرح پرداخت'),
            'related_factors': _('فاکتورهای مرتبط'),
            'status': _('وضعیت'),
            'min_signatures': _('حداقل تعداد امضا'),
        }

    def clean_issue_date(self):
        date_str = self.cleaned_data.get('issue_date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ صدور اجباری است.'))
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
            gregorian_date = j_date.togregorian()
            return timezone.make_aware(gregorian_date)
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean_amount(self):
        amount_str = self.cleaned_data.get('amount', '')
        if amount_str is None or str(amount_str).strip() == '':
            raise forms.ValidationError(_("وارد کردن مبلغ الزامی است."))
        try:
            english_amount_str = to_english_digits(str(amount_str)).replace(',', '')
            amount_decimal = Decimal(english_amount_str)
            amount_int = int(round(amount_decimal))
            if amount_int <= 0:
                raise forms.ValidationError(_("مبلغ باید بزرگ‌تر از صفر باشد."))
            return amount_int
        except (ValueError, TypeError):
            raise forms.ValidationError(_("لطفاً یک عدد معتبر برای مبلغ وارد کنید."))

    def clean_min_signatures(self):
        min_signatures = self.cleaned_data.get('min_signatures')
        if min_signatures < 1:
            raise forms.ValidationError(_('حداقل تعداد امضا باید ۱ یا بیشتر باشد.'))
        return min_signatures

class PayeeForm(forms.ModelForm):
    class Meta:
        model = Payee
        fields = ['name', 'family','payee_type', 'national_id', 'account_number', 'iban', 'address','phone','is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام')}),
            'family': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام')}),
            'payee_type': forms.Select(attrs={'class': 'form-control'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('کد ملی/اقتصادی')}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('شماره حساب')}),
            'iban': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('شبا')}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
            'phone': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('تلفن')}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'placeholder': _('فعال(نمایش در لیست)')}),
        }
        labels = {
            'name': _('نام'),
            'payee_type': _('نوع'),
            'national_id': _('کد ملی/اقتصادی'),
            'account_number': _('شماره حساب'),
            'iban': _('شبا'),
            'address': _('آدرس'),
            'phone': _('تلفن'),
        }

class TransactionTypeForm(forms.ModelForm):
    class Meta:
        model = TransactionType
        fields = ['name', 'description', 'requires_extra_approval']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'requires_extra_approval': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': _('نام'),
            'description': _('توضیحات'),
            'requires_extra_approval': _('نیاز به تأیید اضافی'),
        }

#--
class ProjectBudgetAllocationForm1(forms.ModelForm):
    class Meta:
        model = ProjectBudgetAllocation
        fields = ['budget_allocation', 'project', 'subproject', 'allocated_amount', 'description']

    def __init__(self, *args, organization_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization_id:
            self.fields['budget_allocation'].queryset = BudgetAllocation.objects.filter(
                budget_period__organization_id=organization_id,
                budget_period__is_active=True
            )
            from core.models import Project,SubProject
            self.fields['project'].queryset = Project.objects.filter(organizations__id=organization_id, is_active=True)
            self.fields['subproject'].queryset = SubProject.objects.filter(project__organizations__id=organization_id, is_active=True)
            self.fields['subproject'].required = False

    def clean_allocated_amount(self):
        amount = self.cleaned_data['allocated_amount']
        budget_allocation = self.cleaned_data.get('budget_allocation')
        if budget_allocation:
            budget_period = budget_allocation.budget_period
            remaining = budget_period.get_remaining_amount()
            locked_amount = budget_period.get_locked_amount()
            if amount > remaining:
                raise forms.ValidationError(_("مبلغ تخصیص بیشتر از بودجه باقی‌مانده است"))
            if remaining - amount < locked_amount:
                raise forms.ValidationError(_("تخصیص این مبلغ باعث نقض مقدار قفل‌شده بودجه می‌شود"))
        return amount
# budgets/forms.py
from core.models import Project, SubProject

class ProjectBudgetAllocationForm(forms.ModelForm):
    class Meta:
        model = ProjectBudgetAllocation
        fields = ['budget_allocation', 'project', 'subproject', 'allocated_amount', 'description']
        widgets = {
            'budget_allocation': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': _('انتخاب تخصیص بودجه شعبه'),
            }),
            'project': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': _('انتخاب پروژه'),
            }),
            'subproject': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': _('انتخاب زیرپروژه (اختیاری)'),
            }),
            'allocated_amount': forms.NumberInput(attrs={
                'class': 'form-control numeric-input',
                'placeholder': _('مبلغ به ریال'),
                'dir': 'ltr',
                'min': '0',
                'step': '1000',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('توضیحات مربوط به تخصیص بودجه'),
            }),
        }
        labels = {
            'budget_allocation': _('تخصیص بودجه شعبه'),
            'project': _('پروژه'),
            'subproject': _('زیرپروژه (اختیاری)'),
            'allocated_amount': _('مبلغ تخصیص (ریال)'),
            'description': _('توضیحات'),
        }
        help_texts = {
            'allocated_amount': _('مبلغ باید کمتر از باقی‌مانده بودجه دوره باشد'),
            'subproject': _('در صورتی که بودجه به زیرپروژه خاصی تعلق دارد انتخاب کنید'),
        }


    def __init__(self, *args, organization_id=None, **kwargs):
        super().__init__(*args, **kwargs)

        if organization_id:
            self.fields['budget_allocation'].queryset = BudgetAllocation.objects.filter(
                budget_period__organization_id=organization_id,
                budget_period__is_active=True
            ).select_related('budget_period')

            self.fields['project'].queryset = Project.objects.filter(
                organizations__id=organization_id,
                is_active=True
            ).only('id', 'name')

            self.fields['subproject'].queryset = SubProject.objects.filter(
                project__organizations__id=organization_id,
                is_active=True
            ).select_related('project').only('id', 'name', 'project')
            self.fields['subproject'].required = False

        # بهینه‌سازی: اضافه کردن کلاس‌ها و ویژگی‌ها فقط اگه لازم باشه
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
            if field.required:
                field.widget.attrs['required'] = 'required'

    def clean(self):
        cleaned_data = super().clean()
        budget_allocation = cleaned_data.get('budget_allocation')
        allocated_amount = cleaned_data.get('allocated_amount')

        if budget_allocation and allocated_amount:
            budget_period = budget_allocation.budget_period
            remaining = budget_period.get_remaining_amount()
            locked_amount = budget_period.get_locked_amount()

            if allocated_amount > remaining:
                self.add_error('allocated_amount',
                               _("مبلغ تخصیص بیشتر از بودجه باقی‌مانده است: %(remaining)s") % {'remaining': remaining})
            if remaining - allocated_amount < locked_amount:
                self.add_error('allocated_amount',
                               _("نقض مقدار قفل‌شده بودجه: %(locked)s") % {'locked': locked_amount})

        return cleaned_data

class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = '__all__'