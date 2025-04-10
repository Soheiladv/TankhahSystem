from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from Tanbakhsystem.widgets import NumberToWordsWidget
from core.models import Organization
from .models import BudgetPeriod, BudgetAllocation, BudgetTransaction, PaymentOrder, Payee, TransactionType
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

class BudgetPeriodForm(forms.ModelForm):
    start_date = forms.CharField(
        label=_('تاریخ شروع'),
        widget=forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control', 'placeholder': _('1404/01/17')})
    )
    end_date = forms.CharField(
        label=_('تاریخ پایان'),
        widget=forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control', 'placeholder': _('1404/01/17')})
    )

    class Meta:
        model = BudgetPeriod
        fields = ['organization', 'name', 'start_date', 'end_date', 'total_amount', 'is_active', 'is_archived', 'lock_condition', 'locked_percentage', 'warning_threshold']
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام دوره را وارد کنید')}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('مبلغ کل')}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_archived': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lock_condition': forms.Select(attrs={'class': 'form-control'}),
            'locked_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 0.01}),
            'warning_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 0.01}),
        }
        labels = {
            'organization': _('دفتر مرکزی'),
            'name': _('نام دوره بودجه'),
            'total_amount': _('مبلغ کل'),
            'is_active': _('فعال'),
            'is_archived': _('بایگانی شده'),
            'lock_condition': _('شرط قفل'),
            'locked_percentage': _('درصد قفل‌شده'),
            'warning_threshold': _('آستانه اخطار'),
        }

    def clean_start_date(self):
        date_str = self.cleaned_data.get('start_date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ شروع اجباری است.'))
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
            return timezone.make_aware(j_date.togregorian())
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean_end_date(self):
        date_str = self.cleaned_data.get('end_date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ پایان اجباری است.'))
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
            return timezone.make_aware(j_date.togregorian())
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean_total_amount(self):
        amount_str = self.cleaned_data.get('total_amount', '')
        if not amount_str:
            raise forms.ValidationError(_('وارد کردن مبلغ کل الزامی است.'))
        try:
            amount = int(to_english_digits(str(amount_str)).replace(',', ''))
            if amount <= 0:
                raise forms.ValidationError(_('مبلغ کل باید بزرگ‌تر از صفر باشد.'))
            return amount
        except (ValueError, TypeError):
            raise forms.ValidationError(_('لطفاً یک عدد معتبر برای مبلغ وارد کنید.'))

    def clean_locked_percentage(self):
        percentage = self.cleaned_data.get('locked_percentage')
        if percentage is None:
            raise forms.ValidationError(_('درصد قفل‌شده اجباری است.'))
        if percentage < 0 or percentage > 100:
            raise forms.ValidationError(_('درصد قفل‌شده باید بین ۰ تا ۱۰۰ باشد.'))
        return percentage

    def clean_warning_threshold(self):
        threshold = self.cleaned_data.get('warning_threshold')
        if threshold is None:
            raise forms.ValidationError(_('آستانه اخطار اجباری است.'))
        if threshold < 0 or threshold > 100:
            raise forms.ValidationError(_('آستانه اخطار باید بین ۰ تا ۱۰۰ باشد.'))
        locked_percentage = self.cleaned_data.get('locked_percentage')
        if locked_percentage and threshold <= locked_percentage:
            raise forms.ValidationError(_('آستانه اخطار باید بزرگ‌تر از درصد قفل‌شده باشد.'))
        return threshold

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError(_('تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.'))
        return cleaned_data
class BudgetAllocationForm____(forms.ModelForm):
    allocation_date = forms.CharField(
        label=_('تاریخ تخصیص'),
        widget=forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control', 'placeholder': _('1404/01/17')})
    )
    allocation_type = forms.ChoiceField(
        label=_('نوع تخصیص'),
        choices=(('amount', _('مبلغ ثابت')), ('percent', _('درصد'))),
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_allocation_type'}),
    )
    # allocated_amount = forms.CharField(
    #     label=_('مبلغ تخصیص / درصد'),
    #     widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_allocated_amount'}),
    # )

    # استفاده از ویجت سفارشی برای مبلغ
    allocated_amount = forms.CharField(  # CharField به خاطر numberFormatter و ویجت
        label=_("مقدار/درصد تخصیص"),
        required=True,
        widget=NumberToWordsWidget(
            attrs={
                'placeholder': _('مقدار یا درصد را وارد کنید'),
                'class': 'form-control form-control-sm number-format ltr-input',  # ! کلاس‌های لازم
                'id': 'id_allocated_amount'  # ! اضافه کردن ID برای JS
            },
            word_label=_("به حروف:"),
            unit=""  # واحد توسط JS تعیین می‌شود
        )
    )
    budget_period = forms.ModelChoiceField(
        queryset=BudgetPeriod.objects.all(), # یا فیلتر کنید بر اساس نیاز
        label=_("دوره بودجه"),
        widget=forms.HiddenInput() # چون از URL یا جای دیگر می‌آید و در فرم نمایش داده نمی‌شود
                                   # اگر کاربر باید انتخاب کند، از forms.Select استفاده کنید
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),  # یا فیلتر کنید بر اساس نیاز
        label=_("شعبه دریافت‌کننده"),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})  # ! کلاس بوت‌استرپ
    )


    allocation_date = forms.CharField(  # CharField به خاطر دیتاپیکر جلالی
        label=_('تاریخ تخصیص'),
        required=True,
        widget=forms.TextInput(attrs={
            'data-jdp': '',  # فعال کردن دیتاپیکر
            'class': 'form-control form-control-sm datepicker',  # ! کلاس‌های لازم
            'placeholder': _('مثال: 1403/02/21'),
            'autocomplete': 'off'  # جلوگیری از پیشنهاد مرورگر
        })
    )
    class Meta:
        model = BudgetAllocation
        fields = ['budget_period', 'organization', 'allocated_amount', 'allocation_date']
        widgets = {
            'budget_period': forms.Select(attrs={'class': 'form-control'}),
            'organization': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        # می‌توانید user یا budget_period اولیه را از kwargs بگیرید
        # self.user = kwargs.pop('user', None)
        initial_budget_period = kwargs.pop('budget_period_initial', None)
        super().__init__(*args, **kwargs)

        # مقداردهی اولیه budget_period اگر از ویو پاس داده شده
        if initial_budget_period:
            self.fields['budget_period'].initial = initial_budget_period
            # می‌توانید queryset سازمان را بر اساس دوره بودجه فیلتر کنید اگر لازم است
            # self.fields['organization'].queryset = ...

        # اگر فیلد budget_period توسط کاربر باید انتخاب شود و مخفی نیست:
        # self.fields['budget_period'].queryset = BudgetPeriod.objects.filter(is_active=True) # مثال
        # self.fields['budget_period'].widget.attrs.update({'class': 'form-select form-select-sm'})



    def clean_allocation_date(self):
        date_str = self.cleaned_data.get('allocation_date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ تخصیص اجباری است.'))
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
            return j_date.date()
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean_allocated_amount(self):
        amount_str = self.cleaned_data.get('allocated_amount', '')
        allocation_type = self.cleaned_data.get('allocation_type')
        budget_period = self.cleaned_data.get('budget_period')

        if not amount_str:
            raise forms.ValidationError(_('وارد کردن مقدار تخصیص الزامی است.'))

        english_amount_str = to_english_digits(str(amount_str)).replace(',', '')
        try:
            amount = Decimal(english_amount_str)
            if allocation_type == 'percent':
                if amount <= 0 or amount > 100:
                    raise forms.ValidationError(_('درصد باید بین ۱ تا ۱۰۰ باشد.'))
                total_amount = budget_period.total_amount
                amount = (amount / 100) * total_amount
            else:
                if amount <= 0:
                    raise forms.ValidationError(_('مبلغ باید بزرگ‌تر از صفر باشد.'))

            if amount > budget_period.remaining_amount:
                raise forms.ValidationError(_('مبلغ تخصیص بیشتر از باقی‌مانده بودجه است: %s') % budget_period.remaining_amount)
            return amount
        except (ValueError, TypeError):
            raise forms.ValidationError(_('لطفاً یک مقدار معتبر وارد کنید.'))

class BudgetAllocationForm(forms.ModelForm):
    allocation_date = forms.CharField(
        label=_('تاریخ تخصیص'),
        widget=forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control', 'placeholder': _('1404/01/17')})
    )
    allocation_type = forms.ChoiceField(
        label=_('نوع تخصیص'),
        choices=(('amount', _('مبلغ ثابت')), ('percent', _('درصد'))),
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_allocation_type'}),
    )
    allocated_amount = forms.CharField(
        label=_('مبلغ تخصیص / درصد'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_allocated_amount'}),
    )
    budget_period = forms.ModelChoiceField(
        queryset=BudgetPeriod.objects.all(), # یا فیلتر کنید بر اساس نیاز
        label=_("دوره بودجه"),
        widget=forms.HiddenInput() # چون از URL یا جای دیگر می‌آید و در فرم نمایش داده نمی‌شود
                                   # اگر کاربر باید انتخاب کند، از forms.Select استفاده کنید
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),  # یا فیلتر کنید بر اساس نیاز
        label=_("شعبه دریافت‌کننده"),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})  # ! کلاس بوت‌استرپ
    )

    # استفاده از ویجت سفارشی برای مبلغ
    allocated_amount = forms.CharField(  # CharField به خاطر numberFormatter و ویجت
        label=_("مقدار/درصد تخصیص"),
        required=True,
        widget=NumberToWordsWidget(
            attrs={
                'placeholder': _('مقدار یا درصد را وارد کنید'),
                'class': 'form-control form-control-sm number-format ltr-input',  # ! کلاس‌های لازم
                'id': 'id_allocated_amount'  # ! اضافه کردن ID برای JS
            },
            word_label=_("به حروف:"),
            unit=""  # واحد توسط JS تعیین می‌شود
        )
    )

    allocation_date = forms.CharField(  # CharField به خاطر دیتاپیکر جلالی
        label=_('تاریخ تخصیص'),
        required=True,
        widget=forms.TextInput(attrs={
            'data-jdp': '',  # فعال کردن دیتاپیکر
            'class': 'form-control form-control-sm datepicker',  # ! کلاس‌های لازم
            'placeholder': _('مثال: 1403/02/21'),
            'autocomplete': 'off'  # جلوگیری از پیشنهاد مرورگر
        })
    )
    class Meta:
        model = BudgetAllocation
        fields = ['budget_period', 'organization', 'allocated_amount', 'allocation_date']
        widgets = {
            'budget_period': forms.Select(attrs={'class': 'form-control'}),
            'organization': forms.Select(attrs={'class': 'form-control'}),
        }


    def clean_allocation_date(self):
        date_str = self.cleaned_data.get('allocation_date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ تخصیص اجباری است.'))
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
            return j_date.date()
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean_allocated_amount(self):
        amount_str = self.cleaned_data.get('allocated_amount', '')
        allocation_type = self.cleaned_data.get('allocation_type')
        budget_period = self.cleaned_data.get('budget_period')

        if not amount_str:
            raise forms.ValidationError(_('وارد کردن مقدار تخصیص الزامی است.'))

        english_amount_str = to_english_digits(str(amount_str)).replace(',', '')
        try:
            amount = Decimal(english_amount_str)
            if allocation_type == 'percent':
                if amount <= 0 or amount > 100:
                    raise forms.ValidationError(_('درصد باید بین ۱ تا ۱۰۰ باشد.'))
                total_amount = budget_period.total_amount
                amount = (amount / 100) * total_amount
            else:
                if amount <= 0:
                    raise forms.ValidationError(_('مبلغ باید بزرگ‌تر از صفر باشد.'))

            if amount > budget_period.remaining_amount:
                raise forms.ValidationError(_('مبلغ تخصیص بیشتر از باقی‌مانده بودجه است: %s') % budget_period.remaining_amount)
            return amount
        except (ValueError, TypeError):
            raise forms.ValidationError(_('لطفاً یک مقدار معتبر وارد کنید.'))

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