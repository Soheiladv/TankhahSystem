from django import forms
from django.utils.translation import gettext_lazy as _
from .models import  BudgetAllocation, BudgetTransaction, PaymentOrder, Payee, TransactionType

from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# تابع کمکی برای تبدیل اعداد فارسی به انگلیسی
def to_english_digits(text):
    """تبدیل اعداد انگلیسی به فارسی"""
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    translation_table = str.maketrans(persian_digits, english_digits)
    return text.translate(translation_table)
    # return ''.join(persian_digits[int(c)] if c.isdigit() else c for c in str(text))


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

# class PaymentOrderForm(forms.ModelForm):
#     issue_date = forms.CharField(
#         label=_('تاریخ صدور'),
#         widget=forms.TextInput(attrs={
#             'data-jdp': '',
#             'class': 'form-control',
#             'placeholder': _('تاریخ را انتخاب کنید (1404/01/17)')
#         })
#     )
#
#     class Meta:
#         model = PaymentOrder
#         fields = ['tankhah', 'amount', 'payee', 'description', 'related_factors', 'status', 'min_signatures']
#         widgets = {
#             'tankhah': forms.Select(attrs={'class': 'form-control'}),
#             'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('مبلغ')}),
#             'payee': forms.Select(attrs={'class': 'form-control'}),
#             'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
#             'related_factors': forms.SelectMultiple(attrs={'class': 'form-control'}),
#             'status': forms.Select(attrs={'class': 'form-control'}),
#             'min_signatures': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
#         }
#         labels = {
#             'tankhah': _('تنخواه'),
#             'amount': _('مبلغ'),
#             'payee': _('دریافت‌کننده'),
#             'description': _('شرح پرداخت'),
#             'related_factors': _('فاکتورهای مرتبط'),
#             'status': _('وضعیت'),
#             'min_signatures': _('حداقل تعداد امضا'),
#         }
#
#     def clean_issue_date(self):
#         date_str = self.cleaned_data.get('issue_date')
#         if not date_str:
#             raise forms.ValidationError(_('تاریخ صدور اجباری است.'))
#         try:
#             j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
#             gregorian_date = j_date.togregorian()
#             return timezone.make_aware(gregorian_date)
#         except ValueError:
#             raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))
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
#     def clean_min_signatures(self):
#         min_signatures = self.cleaned_data.get('min_signatures')
#         if min_signatures < 1:
#             raise forms.ValidationError(_('حداقل تعداد امضا باید ۱ یا بیشتر باشد.'))
#         return min_signatures


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
# budgets/forms.py
from core.models import Project, SubProject
