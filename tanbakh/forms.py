from django.forms import inlineformset_factory

from Tanbakhsystem.utils import convert_to_farsi_numbers, convert_jalali_to_gregorian, convert_gregorian_to_jalali
from .models import Factor, Approval
from .models import FactorItem

FactorItemFormSet = inlineformset_factory(Factor, FactorItem, fields=['description', 'amount', 'quantity'], extra=1)

from django.forms import inlineformset_factory
from .models import Factor, FactorItem

from .models import Tanbakh
import jdatetime
from django import forms
from django.utils.translation import gettext_lazy as _

class TanbakhForm(forms.ModelForm):
    """فرم ایجاد و ویرایش تنخواه"""

    date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        })
    )

    class Meta:
        model = Tanbakh  # مدل مشخص شده
        fields = ['date', 'organization', 'project', 'status', 'hq_status',
                  'last_stopped_post', 'letter_number', 'number', 'amount', 'description',
                  'approved_by']
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-control'}),
            'letter_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('اختیاری')}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'hq_status': forms.Select(attrs={'class': 'form-control'}),
            'last_stopped_post': forms.Select(attrs={'class': 'form-control'}),
            'approved_by': forms.Select(attrs={'class': 'form-control'}),
            'number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره تنخواه'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'date': _('تاریخ'),
            'organization': _('مجتمع'),
            'project': _('پروژه'),
            'status': _('وضعیت'),
            'hq_status': _('وضعیت در HQ'),
            'last_stopped_post': _('آخرین پست متوقف‌شده'),
            'letter_number': _('شماره نامه'),
            'approved_by': _('تأییدکننده'),
            'number': _('شماره تنخواه'),
            'amount': _('مبلغ'),
            'description': _('توضیحات'),
        }

    def clean_date(self):
        """تبدیل تاریخ شمسی به میلادی هنگام اعتبارسنجی فرم"""
        date_str = self.cleaned_data.get('date')
        return convert_jalali_to_gregorian(date_str) if date_str else None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['date'].initial = convert_gregorian_to_jalali(self.instance.date)
            self.fields['number'].initial = convert_to_farsi_numbers(self.instance.number)
            self.fields['amount'].initial = convert_to_farsi_numbers(self.instance.amount)


class FactorForm(forms.ModelForm):
    """فرم ایجاد و ویرایش فاکتور"""
    date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        })
    )

    class Meta:
        model = Factor
        fields = ['tanbakh', 'date', 'amount', 'description', 'file']  # status حذف شده
        widgets = {
            'tanbakh': forms.Select(attrs={'class': 'form-control'}),
            # 'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('مبلغ را وارد کنید')}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('توضیحات فاکتور')}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'tanbakh': _('تنخواه'),
            'date': _('تاریخ'),
            'amount': _('مبلغ'),
            'description': _('توضیحات'),
            'file': _('فایل پیوست'),
        }

    def clean_date(self):
        """تبدیل تاریخ شمسی به میلادی هنگام اعتبارسنجی فرم"""
        date_str = self.cleaned_data.get('date')
        return convert_jalali_to_gregorian(date_str) if date_str else None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['date'].initial = convert_gregorian_to_jalali(self.instance.date)
            self.fields['amount'].initial = convert_to_farsi_numbers(self.instance.amount)


class FactorItemForm(forms.ModelForm):
    """فرم ایجاد و ویرایش اقلام فاکتور"""

    class Meta:
        model = FactorItem
        fields = ['description', 'amount', 'quantity']  # 'factor' توسط سیستم پر می‌شود
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('شرح ردیف را وارد کنید')
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('مبلغ ردیف'),
                'step': '0.01'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('تعداد'),
                'min': '1'
            }),
        }
        labels = {
            'description': _('شرح ردیف'),
            'amount': _('مبلغ'),
            'quantity': _('تعداد'),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError(_('مبلغ باید بزرگ‌تر از صفر باشد.'))
        return amount

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity < 1:
            raise forms.ValidationError(_('تعداد باید حداقل ۱ باشد.'))
        return quantity


class ApprovalForm(forms.ModelForm):
    """فرم ثبت تأیید یا رد"""

    class Meta:
        model = Approval
        fields = ['tanbakh', 'factor', 'comment', 'branch', 'is_approved']  # user و date توسط سیستم پر می‌شوند
        widgets = {
            'tanbakh': forms.Select(attrs={'class': 'form-control'}),
            'factor': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('توضیحات اختیاری')}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'tanbakh': _('تنخواه'),
            'factor': _('فاکتور'),
            'comment': _('توضیحات'),
            'branch': _('شاخه'),
            'is_approved': _('تأیید شده؟'),
        }


# فرم‌ست برای اقلام فاکتور
FactorItemFormSet = inlineformset_factory(
    Factor,  # مدل والد (فاکتور)
    FactorItem,  # مدل فرزند (اقلام فاکتور)
    form=FactorItemForm,  # فرم تعریف‌شده بالا
    fields=['description', 'amount', 'quantity'],
    extra=1,  # تعداد فرم‌های خالی پیش‌فرض
    can_delete=True  # امکان حذف ردیف‌ها
)
