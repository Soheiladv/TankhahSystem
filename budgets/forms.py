import re
from decimal import Decimal, InvalidOperation
import jdatetime
# budgets/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from Tanbakhsystem.utils import to_english_digits
from Tanbakhsystem.widgets import NumberToWordsWidget
from .models import BudgetPeriod, BudgetAllocation, ProjectBudgetAllocation, PaymentOrder, TransactionType, Payee
from core.models import Organization, Project, SubProject

class BudgetPeriodForm(forms.ModelForm):
    class Meta:
        model = BudgetPeriod
        fields = ['name', 'organization', 'total_amount', 'start_date', 'end_date', 'is_active', 'warning_threshold',
                  'locked_percentage']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and start_date > end_date:
            self.add_error('end_date', _("تاریخ پایان باید بعد از تاریخ شروع باشد"))
        return cleaned_data

#-------------#
class __a____BudgetAllocationForm(forms.ModelForm):
    allocation_type = forms.ChoiceField(
        label=_('نوع تخصیص'),
        choices=(('amount', _('مبلغ ثابت')), ('percent', _('درصد'))),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='amount'
    )

    allocated_amount = forms.CharField(
        label=_("مقدار تخصیص"),
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': _('مبلغ یا درصد را وارد کنید'),
            'class': 'form-control form-control-sm ltr-input',
            'inputmode': 'numeric',
            'pattern': '[۰-۹0-9,،.]*',
        })
    )

    budget_period = forms.ModelChoiceField(
        queryset=BudgetPeriod.objects.all(),
        label=_("دوره بودجه"),
        widget=forms.HiddenInput(),
    )

    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        label=_("شعبه دریافت‌کننده"),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )

    allocation_date = forms.CharField(
        label=_('تاریخ تخصیص'),
        required=True,
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control form-control-sm datepicker',
            'placeholder': _('مثال: 1403/02/21'),
            'autocomplete': 'off',
        })
    )

    class Meta:
        model = BudgetAllocation
        fields = ['budget_period', 'organization', 'allocation_type', 'allocated_amount', 'allocation_date',
                  'description', 'status']
        widgets = {
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('شرح تخصیص بودجه')
            }),
        }

    def __init__(self, *args, organizations=None, **kwargs):
        super().__init__(*args, **kwargs)

        if organizations is not None:
            self.fields['organization'].queryset = organizations

        # تنظیم مقدار اولیه تاریخ به فرمت جلالی در حالت ویرایش
        if self.instance and self.instance.pk and self.instance.allocation_date:
            j_date = jdatetime.date.fromgregorian(date=self.instance.allocation_date)
            self.fields['allocation_date'].initial = j_date.strftime('%Y/%m/%d')

    def clean_allocated_amount(self):
        amount_str = self.cleaned_data.get('allocated_amount', '')
        if not amount_str:
            raise ValidationError(_('وارد کردن مقدار تخصیص الزامی است.'))

        # تبدیل اعداد فارسی به انگلیسی و حذف کاماها
        amount_str = to_english_digits(amount_str).replace(',', '')

        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValidationError(_('مقدار باید بزرگ‌تر از صفر باشد.'))
            return amount
        except:
            raise ValidationError(_('لطفاً یک مقدار عددی معتبر وارد کنید.'))

    def clean_allocation_date(self):
        date_str = self.cleaned_data.get('allocation_date')
        if not date_str:
            raise ValidationError(_('تاریخ تخصیص اجباری است.'))

        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d').date()
            return j_date.togregorian()
        except ValueError:
            raise ValidationError(_('فرمت تاریخ نامعتبر. مثال صحیح: 1403/02/21'))

    def clean(self):
        cleaned_data = super().clean()
        allocation_type = cleaned_data.get('allocation_type')
        allocated_amount = cleaned_data.get('allocated_amount')
        budget_period = cleaned_data.get('budget_period')

        if not all([allocation_type, allocated_amount, budget_period]):
            return cleaned_data

        try:
            # محاسبه مبلغ نهایی بر اساس نوع تخصیص
            if allocation_type == 'percent':
                if allocated_amount > 100:
                    self.add_error('allocated_amount', _('درصد نمی‌تواند بیشتر از ۱۰۰ باشد.'))
                    return cleaned_data

                final_amount = (allocated_amount / Decimal('100')) * budget_period.total_amount
            else:
                final_amount = allocated_amount

            # بررسی باقی‌مانده بودجه
            remaining_amount = budget_period.get_remaining_amount()

            # اگر در حال ویرایش رکورد موجود هستیم، بودجه قبلی را به باقی‌مانده اضافه می‌کنیم
            if self.instance and self.instance.pk:
                remaining_amount += self.instance.allocated_amount

            if final_amount > remaining_amount:
                self.add_error(
                    'allocated_amount',
                    _('مبلغ تخصیص ({:,.0f} ریال) بیشتر از بودجه باقی‌مانده ({:,.0f} ریال) است.').format(
                        final_amount, remaining_amount
                    )
                )

            # ذخیره مبلغ نهایی
            cleaned_data['final_amount'] = final_amount

        except Exception as e:
            self.add_error(None, _('خطا در محاسبات بودجه. لطفاً اطلاعات را بررسی کنید.'))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # تنظیم مبلغ نهایی
        if 'final_amount' in self.cleaned_data:
            instance.allocated_amount = self.cleaned_data['final_amount']

        if commit:
            instance.save()
            self.save_m2m()

        return instance
class __BudgetAllocationForm(forms.ModelForm):
    allocation_type = forms.ChoiceField(
        label=_('نوع تخصیص'),
        choices=(('amount', _('مبلغ ثابت')), ('percent', _('درصد'))),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )
    allocated_amount = forms.CharField(
        label=_("مقدار/درصد تخصیص"),
        required=True,
        widget=NumberToWordsWidget(
            attrs={
                'placeholder': _('مقدار یا درصد را وارد کنید'),
                'class': 'form-control form-control-sm number-format ltr-input',
                'id': 'id_allocated_amount',
                'inputmode': 'numeric',
                'pattern': '[۰-۹0-9,،.]*',
            },
            word_label=_("به حروف:"),
            unit="",
        )
    )
    budget_period = forms.ModelChoiceField(
        queryset=BudgetPeriod.objects.all(),
        label=_("دوره بودجه"),
        widget=forms.HiddenInput(),
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        label=_("شعبه دریافت‌کننده"),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    allocation_date = forms.CharField(
        label=_('تاریخ تخصیص'),
        required=True,
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control form-control-sm datepicker',
            'placeholder': _('مثال: 1403/02/21'),
            'autocomplete': 'off',
        })
    )

    class Meta:
        model = BudgetAllocation
        fields = ['budget_period', 'organization', 'allocation_type', 'allocated_amount', 'allocation_date','description','status']
        widgets = {
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input' }),
            'description': forms.TextInput(attrs={'class': 'form-control','rows':1, 'placeholder': _('شرح ردیف')}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تنظیم مقدار اولیه تاریخ به فرمت جلالی در حالت ویرایش
        if self.instance and self.instance.pk and self.instance.allocation_date:
            j_date = jdatetime.date.fromgregorian(date=self.instance.allocation_date)
            jalali_date_str = j_date.strftime('%Y/%m/%d')
            self.fields['allocation_date'].initial = jalali_date_str
            self.initial['allocation_date'] = jalali_date_str

    def clean_allocation_date(self):
        date_str = self.cleaned_data.get('allocation_date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ تخصیص اجباری است.'))
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d').date()
            # تبدیل به تاریخ میلادی برای ذخیره در مدل (اگر DateField باشد)
            gregorian_date = j_date.togregorian()
            return gregorian_date
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1403/02/21).'))

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

            if amount > budget_period.get_remaining_amount():
                raise forms.ValidationError(_('مبلغ تخصیص بیشتر از باقی‌مانده بودجه است: %s') % budget_period.get_remaining_amount)
            return amount
        except (ValueError, TypeError):
            raise forms.ValidationError(_('لطفاً یک مقدار معتبر وارد کنید.'))

class BudgetAllocationForm__(forms.ModelForm):
    allocation_type = forms.ChoiceField(
        label=_('نوع تخصیص'),
        choices=(('amount', _('مبلغ ثابت')), ('percent', _('درصد'))),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )
    allocated_amount = forms.CharField(
        label=_("مقدار/درصد تخصیص"),
        required=True,
        widget=NumberToWordsWidget(
            attrs={
                'placeholder': _('مقدار یا درصد را وارد کنید'),
                'class': 'form-control form-control-sm number-format ltr-input',
                'id': 'id_allocated_amount',
                'inputmode': 'numeric',
                'pattern': '[۰-۹0-9,،.]*',
            },
            word_label=_("به حروف:"),
            unit="",
        )
    )
    budget_period = forms.ModelChoiceField(
        queryset=BudgetPeriod.objects.all(),
        label=_("دوره بودجه"),
        widget=forms.HiddenInput(),
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        label=_("شعبه دریافت‌کننده"),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    allocation_date = forms.CharField(
        label=_('تاریخ تخصیص'),
        required=True,
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control form-control-sm datepicker',
            'placeholder': _('مثال: 1403/02/21'),
            'autocomplete': 'off',
        })
    )

    class Meta:
        model = BudgetAllocation
        fields = ['budget_period', 'organization', 'allocation_type', 'allocated_amount', 'allocation_date', 'description', 'status']
        widgets = {
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input' }),
            'description': forms.TextInput(attrs={'class': 'form-control','rows':1, 'placeholder': _('شرح ردیف')}),
        }

    def __init__(self, *args, organizations=None, **kwargs):
        super().__init__(*args, **kwargs)
        # تنظیم کوئری‌ست سازمان‌ها
        if organizations is not None:
            self.fields['organization'].queryset = organizations
        else:
            self.fields['organization'].queryset = Organization.objects.all()
        # تنظیم مقدار اولیه تاریخ به فرمت جلالی در حالت ویرایش
        if self.instance and self.instance.pk and self.instance.allocation_date:
            j_date = jdatetime.date.fromgregorian(date=self.instance.allocation_date)
            jalali_date_str = j_date.strftime('%Y/%m/%d')
            self.fields['allocation_date'].initial = jalali_date_str
            self.initial['allocation_date'] = jalali_date_str

    def clean(self):
        cleaned_data = super().clean()
        budget_period = cleaned_data.get('budget_period')
        allocated_amount = cleaned_data.get('allocated_amount')
        allocation_type = cleaned_data.get('allocation_type')

        if budget_period and allocated_amount is not None and allocation_type:
            try:
                # تمیز کردن مقدار ورودی (حذف کاما، تبدیل اعداد فارسی به انگلیسی)
                amount_str = re.sub(r'[^\d.]', '', str(allocated_amount))  # فقط اعداد و نقطه نگه می‌داریم
                amount = Decimal(amount_str)

                # اعتبارسنجی مقدار پایه
                if amount <= 0:
                    self.add_error('allocated_amount', _('مقدار تخصیص باید بزرگ‌تر از صفر باشد.'))

                # محاسبه مقدار نهایی بر اساس نوع تخصیص
                final_amount = amount
                if allocation_type == 'percent':
                    if amount > 100:
                        self.add_error('allocated_amount', _('درصد نمی‌تواند بیشتر از ۱۰۰ باشد.'))
                        return cleaned_data
                    final_amount = (amount / Decimal('100')) * budget_period.total_amount

                # گرفتن باقی‌مانده بودجه
                remaining_amount = budget_period.get_remaining_amount()
                if remaining_amount <= 0:
                    self.add_error('allocated_amount', _('هیچ بودجه‌ای برای تخصیص باقی نمانده است.'))
                    return cleaned_data

                # چک کردن اینکه مقدار تخصیص از باقی‌مانده بیشتر نباشه
                if final_amount > remaining_amount:
                    self.add_error(
                        'allocated_amount',
                        _('مبلغ تخصیص ({}) بیشتر از باقی‌مانده بودجه ({}) است.').format(
                            final_amount, remaining_amount
                        )
                    )
                # ذخیره مقدار نهایی در cleaned_data برای استفاده در مدل
                cleaned_data['allocated_amount'] = final_amount

            except (InvalidOperation, ValueError, TypeError):
                self.add_error('allocated_amount', _('مقدار تخصیص نامعتبر است.'))

        return cleaned_data

    def clean_allocation_date(self):
        date_str = self.cleaned_data.get('allocation_date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ تخصیص اجباری است.'))
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d').date()
            # تبدیل به تاریخ میلادی برای ذخیره در مدل (اگر DateField باشد)
            gregorian_date = j_date.togregorian()
            return gregorian_date
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1403/02/21).'))

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

            if amount > budget_period.get_remaining_amount():
                raise forms.ValidationError(_('مبلغ تخصیص بیشتر از باقی‌مانده بودجه است: %s') % budget_period.get_remaining_amount)
            return amount
        except (ValueError, TypeError):
            raise forms.ValidationError(_('لطفاً یک مقدار معتبر وارد کنید.'))

class ProjectBudgetAllocationForm(forms.ModelForm):
    class Meta:
        model = ProjectBudgetAllocation
        fields = ['budget_allocation', 'project', 'subproject', 'allocated_amount', 'allocation_date', 'description']
        widgets = {
            'allocation_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, organization_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization_id:
            self.fields['budget_allocation'].queryset = BudgetAllocation.objects.filter(
                organization_id=organization_id
            )
            self.fields['project'].queryset = Project.objects.filter(
                organizations__id=organization_id, is_active=True
            )
            self.fields['subproject'].queryset = SubProject.objects.filter(
                project__organizations__id=organization_id, is_active=True
            )

    def clean(self):
        cleaned_data = super().clean()
        budget_allocation = cleaned_data.get('budget_allocation')
        allocated_amount = cleaned_data.get('allocated_amount')
        project = cleaned_data.get('project')
        subproject = cleaned_data.get('subproject')
        if budget_allocation and allocated_amount:
            remaining = budget_allocation.get_remaining_amount()
            if allocated_amount > remaining:
                self.add_error('allocated_amount', f"مبلغ تخصیص بیشتر از باقی‌مانده بودجه شعبه ({remaining}) است")
        if subproject and project and subproject.project != project:
            self.add_error('subproject', _("زیرپروژه باید به پروژه انتخاب‌شده تعلق داشته باشد"))
        return cleaned_data

# from pydoc import visiblename
#
# from django import forms
# from django.utils.translation import gettext_lazy as _
# from django.core.exceptions import ValidationError
#
# from Tanbakhsystem.utils import convert_to_farsi_numbers
# from Tanbakhsystem.widgets import NumberToWordsWidget
# from core.models import Organization
# from .models import BudgetPeriod, BudgetAllocation, BudgetTransaction, PaymentOrder, Payee, TransactionType, \
#     ProjectBudgetAllocation
# import jdatetime
# from django.utils import timezone
# from decimal import Decimal
# import logging
#
# logger = logging.getLogger(__name__)
#
# # تابع کمکی برای تبدیل اعداد فارسی به انگلیسی
# def to_english_digits(text):
#     persian_digits = '۰۱۲۳۴۵۶۷۸۹'
#     english_digits = '0123456789'
#     translation_table = str.maketrans(persian_digits, english_digits)
#     return text.translate(translation_table)
#
# class BudgetPeriodForm(forms.ModelForm):
#     """BudgetPeriod (دوره بودجه کلان):
#     توضیح: این مدل بودجه کل رو جدا از Organization نگه می‌داره. remaining_amount موقع تخصیص آپدیت می‌شه و lock_condition مشخص می‌کنه کی قفل بشه.
#     """
#     start_date = forms.CharField(
#         label=_('تاریخ شروع'),
#         widget=forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control', 'placeholder': _('1404/01/17')})
#     )
#     end_date = forms.CharField(
#         label=_('تاریخ پایان'),
#         widget=forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control', 'placeholder': _('1404/01/17')})
#     )
#
#     class Meta:
#         model = BudgetPeriod
#         fields = ['organization', 'name', 'start_date', 'end_date', 'total_amount', 'is_active', 'is_archived', 'lock_condition', 'locked_percentage', 'warning_threshold']
#         widgets = {
#             'organization': forms.Select(attrs={'class': 'form-control'}),
#             'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام دوره را وارد کنید')}),
#             'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('مبلغ کل')}),
#             'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#             'is_archived': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#             'lock_condition': forms.Select(attrs={'class': 'form-control'}),
#             'locked_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 0.01}),
#             'warning_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 0.01}),
#         }
#         labels = {
#             'organization': _('دفتر مرکزی'),
#             'name': _('نام دوره بودجه'),
#             'total_amount': _('مبلغ کل'),
#             'is_active': _('فعال'),
#             'is_archived': _('بایگانی شده'),
#             'lock_condition': _('شرط قفل'),
#             'locked_percentage': _('درصد قفل‌شده'),
#             'warning_threshold': _('آستانه اخطار'),
#         }
#
#     def clean_start_date(self):
#         date_str = self.cleaned_data.get('start_date')
#         if not date_str:
#             raise forms.ValidationError(_('تاریخ شروع اجباری است.'))
#         try:
#             j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
#             return timezone.make_aware(j_date.togregorian())
#         except ValueError:
#             raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))
#
#     def clean_end_date(self):
#         date_str = self.cleaned_data.get('end_date')
#         if not date_str:
#             raise forms.ValidationError(_('تاریخ پایان اجباری است.'))
#         try:
#             j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
#             return timezone.make_aware(j_date.togregorian())
#         except ValueError:
#             raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))
#
#     def clean_total_amount(self):
#         amount_str = self.cleaned_data.get('total_amount', '')
#         if not amount_str:
#             raise forms.ValidationError(_('وارد کردن مبلغ کل الزامی است.'))
#         try:
#             amount = int(to_english_digits(str(amount_str)).replace(',', ''))
#             if amount <= 0:
#                 raise forms.ValidationError(_('مبلغ کل باید بزرگ‌تر از صفر باشد.'))
#             return amount
#         except (ValueError, TypeError):
#             raise forms.ValidationError(_('لطفاً یک عدد معتبر برای مبلغ وارد کنید.'))
#
#     def clean_locked_percentage(self):
#         percentage = self.cleaned_data.get('locked_percentage')
#         if percentage is None:
#             raise forms.ValidationError(_('درصد قفل‌شده اجباری است.'))
#         if percentage < 0 or percentage > 100:
#             raise forms.ValidationError(_('درصد قفل‌شده باید بین ۰ تا ۱۰۰ باشد.'))
#         return percentage
#
#     def clean_warning_threshold(self):
#         threshold = self.cleaned_data.get('warning_threshold')
#         if threshold is None:
#             raise forms.ValidationError(_('آستانه اخطار اجباری است.'))
#         if threshold < 0 or threshold > 100:
#             raise forms.ValidationError(_('آستانه اخطار باید بین ۰ تا ۱۰۰ باشد.'))
#         locked_percentage = self.cleaned_data.get('locked_percentage')
#         if locked_percentage and threshold <= locked_percentage:
#             raise forms.ValidationError(_('آستانه اخطار باید بزرگ‌تر از درصد قفل‌شده باشد.'))
#         return threshold
#
#     def clean(self):
#         cleaned_data = super().clean()
#         start_date = cleaned_data.get('start_date')
#         end_date = cleaned_data.get('end_date')
#         if start_date and end_date and end_date < start_date:
#             raise forms.ValidationError(_('تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.'))
#         return cleaned_data
#

# class BudgetTransactionForm(forms.ModelForm):
#     class Meta:
#         model = BudgetTransaction
#         fields = ['allocation', 'transaction_type', 'amount', 'related_tankhah', 'description']
#         widgets = {
#             'allocation': forms.Select(attrs={'class': 'form-control'}),
#             'transaction_type': forms.Select(attrs={'class': 'form-control'}),
#             'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('مبلغ')}),
#             'related_tankhah': forms.Select(attrs={'class': 'form-control'}),
#             'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
#         }
#         labels = {
#             'allocation': _('تخصیص بودجه'),
#             'transaction_type': _('نوع تراکنش'),
#             'amount': _('مبلغ'),
#             'related_tankhah': _('تنخواه مرتبط'),
#             'description': _('توضیحات'),
#         }
#
#     def clean_amount(self):
#         amount_str = self.cleaned_data.get('amount', '')
#         if amount_str is None or str(amount_str).strip() == '':
#             raise forms.ValidationError(_("وارد کردن مبلغ الزامی است."))
#         try:
#             english_amount_str = to_english_digits(str(amount_str)).replace(',', '')
#             amount_decimal = Decimal(english_amount_str)
#             amount_int = int(round(amount_decimal))
#             if amount_int <= 0:
#                 raise forms.ValidationError(_("مبلغ باید بزرگ‌تر از صفر باشد."))
#             return amount_int
#         except (ValueError, TypeError):
#             raise forms.ValidationError(_("لطفاً یک عدد معتبر برای مبلغ وارد کنید."))
#
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


# class ProjectBudgetAllocationForm1(forms.ModelForm):
#     class Meta:
#         model = ProjectBudgetAllocation
#         fields = ['budget_allocation', 'project', 'subproject', 'allocated_amount', 'description']
#
#     def __init__(self, *args, organization_id=None, **kwargs):
#         super().__init__(*args, **kwargs)
#         if organization_id:
#             self.fields['budget_allocation'].queryset = BudgetAllocation.objects.filter(
#                 budget_period__organization_id=organization_id,
#                 budget_period__is_active=True
#             )
#             from core.models import Project,SubProject
#             self.fields['project'].queryset = Project.objects.filter(organizations__id=organization_id, is_active=True)
#             self.fields['subproject'].queryset = SubProject.objects.filter(project__organizations__id=organization_id, is_active=True)
#             self.fields['subproject'].required = False
#
#     def clean_allocated_amount(self):
#         amount = self.cleaned_data['allocated_amount']
#         budget_allocation = self.cleaned_data.get('budget_allocation')
#         if budget_allocation:
#             budget_period = budget_allocation.budget_period
#             remaining = budget_period.get_remaining_amount()
#             locked_amount = budget_period.get_locked_amount()
#             if amount > remaining:
#                 raise forms.ValidationError(_("مبلغ تخصیص بیشتر از بودجه باقی‌مانده است"))
#             if remaining - amount < locked_amount:
#                 raise forms.ValidationError(_("تخصیص این مبلغ باعث نقض مقدار قفل‌شده بودجه می‌شود"))
#         return amount
#
#
# # budgets/forms.py
# class ProjectBudgetAllocationForm(forms.ModelForm):
#     class Meta:
#         model = ProjectBudgetAllocation
#         fields = ['budget_allocation', 'project', 'subproject', 'allocated_amount', 'description']
#         widgets = {
#             'budget_allocation': forms.Select(attrs={
#                 'class': 'form-select select2',
#                 'data-placeholder': _('انتخاب تخصیص بودجه شعبه'),
#             }),
#             'project': forms.Select(attrs={
#                 'class': 'form-select select2',
#                 'data-placeholder': _('انتخاب پروژه'),
#             }),
#             'subproject': forms.Select(attrs={
#                 'class': 'form-select select2',
#                 'data-placeholder': _('انتخاب زیرپروژه (اختیاری)'),
#             }),
#             'allocated_amount': forms.NumberInput(attrs={
#                 'class': 'form-control numeric-input',
#                 'placeholder': _('مبلغ به ریال'),
#                 'dir': 'ltr',
#                 'min': '0',
#                 'step': '1000',
#             }),
#             'description': forms.Textarea(attrs={
#                 'class': 'form-control',
#                 'rows': 3,
#                 'placeholder': _('توضیحات مربوط به تخصیص بودجه'),
#             }),
#         }
#         labels = {
#             'budget_allocation': _('تخصیص بودجه شعبه'),
#             'project': _('پروژه'),
#             'subproject': _('زیرپروژه (اختیاری)'),
#             'allocated_amount': _('مبلغ تخصیص (ریال)'),
#             'description': _('توضیحات'),
#         }
#         help_texts = {
#             'allocated_amount': _('مبلغ باید کمتر از باقی‌مانده بودجه دوره باشد'),
#             'subproject': _('در صورتی که بودجه به زیرپروژه خاصی تعلق دارد انتخاب کنید'),
#         }
#
#
#     def __init__(self, *args, organization_id=None, **kwargs):
#         super().__init__(*args, **kwargs)
#         from core.models import Project, SubProject
#
#         if organization_id:
#             self.fields['budget_allocation'].queryset = BudgetAllocation.objects.filter(
#                 budget_period__organization_id=organization_id,
#                 budget_period__is_active=True
#             ).select_related('budget_period')
#
#             self.fields['project'].queryset = Project.objects.filter(
#                 organizations__id=organization_id,
#                 is_active=True
#             ).only('id', 'name')
#
#             self.fields['subproject'].queryset = SubProject.objects.filter(
#                 project__organizations__id=organization_id,
#                 is_active=True
#             ).select_related('project').only('id', 'name', 'project')
#             self.fields['subproject'].required = False
#
#         # بهینه‌سازی: اضافه کردن کلاس‌ها و ویژگی‌ها فقط اگه لازم باشه
#         for field_name, field in self.fields.items():
#             if 'class' not in field.widget.attrs:
#                 field.widget.attrs['class'] = 'form-control'
#             if field.required:
#                 field.widget.attrs['required'] = 'required'
#
#     def clean(self):
#         cleaned_data = super().clean()
#         budget_allocation = cleaned_data.get('budget_allocation')
#         allocated_amount = cleaned_data.get('allocated_amount')
#
#         if budget_allocation and allocated_amount:
#             budget_period = budget_allocation.budget_period
#             remaining = budget_period.get_remaining_amount()
#             locked_amount = budget_period.get_locked_amount()
#
#             if allocated_amount > remaining:
#                 self.add_error('allocated_amount',
#                                _("مبلغ تخصیص بیشتر از بودجه باقی‌مانده است: %(remaining)s") % {'remaining': remaining})
#             if remaining - allocated_amount < locked_amount:
#                 self.add_error('allocated_amount',
#                                _("نقض مقدار قفل‌شده بودجه: %(locked)s") % {'locked': locked_amount})
#
#         return cleaned_data
#

