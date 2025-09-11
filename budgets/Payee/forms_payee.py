from django import forms
from django.utils.translation import gettext_lazy as _
from budgets.models import Payee
import re

class PayeeForm(forms.ModelForm):
    class Meta:
        model = Payee
        fields = [
            'entity_type', 'name', 'family', 'legal_name', 'brand_name',
            'payee_type', 'national_id', 'account_number', 'iban',
            'address', 'phone', 'email', 'tax_id', 'is_active'
        ]
        widgets = {
            'entity_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'entity-type-select'
            }),
            'payee_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام دریافت‌کننده'
            }),
            'family': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام خانوادگی دریافت‌کننده'
            }),
            'legal_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام حقوقی شرکت/سازمان'
            }),
            'brand_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام تجاری (اختیاری)'
            }),
            'national_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'کد ملی (10 رقمی) یا شناسه حقوقی (11 رقمی)',
                'oninput': "this.value = this.value.replace(/[^0-9]/g, '')"
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره حساب (عددی)',
                'oninput': "this.value = this.value.replace(/[^0-9]/g, '')"
            }),
            'iban': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '24 رقم بعد از IR',
                'dir': 'ltr',
                'style': 'text-align: left;',
                'oninput': "this.value = this.value.replace(/[^0-9]/g, '').substring(0, 24)"
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'آدرس کامل'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '09xxxxxxxxx',
                'oninput': "this.value = this.value.replace(/[^0-9]/g, '').substring(0, 11)"
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@email.com'
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شناسه مالیاتی'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
        }
        labels = {
            'entity_type': _('نوع شخص'),
            'name': _('نام'),
            'family': _('نام خانوادگی'),
            'legal_name': _('نام حقوقی'),
            'brand_name': _('نام تجاری'),
            'payee_type': _('نوع دریافت‌کننده'),
            'national_id': _('کد ملی/شناسه حقوقی'),
            'account_number': _('شماره حساب'),
            'iban': _('شبا'),
            'address': _('آدرس'),
            'phone': _('تلفن'),
            'email': _('ایمیل'),
            'tax_id': _('شناسه مالیاتی'),
            'is_active': _('فعال'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'is_active' and 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'

    def clean_national_id(self):
        national_id = self.cleaned_data.get('national_id', '')
        entity_type = self.cleaned_data.get('entity_type')

        if national_id:
            national_id = ''.join(filter(str.isdigit, national_id))
            if entity_type == 'INDIVIDUAL':
                if len(national_id) != 10:
                    raise forms.ValidationError(_("کد ملی باید دقیقاً 10 رقم باشد."))
                if not self.validate_national_code(national_id):
                    raise forms.ValidationError(_("کد ملی معتبر نیست."))
            elif entity_type == 'LEGAL':
                if len(national_id) != 11:
                    raise forms.ValidationError(_("شناسه حقوقی باید دقیقاً 11 رقم باشد."))
                if not self.validate_legal_code(national_id):
                    raise forms.ValidationError(_("شناسه حقوقی معتبر نیست."))
        return national_id

    def validate_national_code(self, code):
        if len(code) != 10 or code == code[0] * 10:
            return False
        sum_digits = sum(int(code[i]) * (10 - i) for i in range(9))
        remainder = sum_digits % 11
        check_digit = int(code[9])
        return (remainder < 2 and check_digit == remainder) or (remainder >= 2 and check_digit == 11 - remainder)

    def validate_legal_code(self, code):
        if len(code) != 11:
            return False
        weights = [29, 27, 23, 19, 17, 29, 27, 23, 19, 17]
        sum_digits = sum(int(code[i]) * weights[i] for i in range(10))
        remainder = sum_digits % 11
        if remainder == 10:
            remainder = 0
        return remainder == int(code[10])

    def clean_account_number(self):
        account_number = self.cleaned_data.get('account_number', '')
        if account_number:
            account_number = ''.join(filter(str.isdigit, account_number))
            if len(account_number) < 5 or len(account_number) > 20:
                raise forms.ValidationError(_("شماره حساب باید بین 5 تا 20 رقم باشد."))
        return account_number

    def clean_iban(self):
        iban = self.cleaned_data.get('iban', '').strip().upper()
        if iban:
            # حذف فاصله‌ها و کاراکترهای غیرمجاز
            iban = ''.join(filter(str.isdigit, iban))
            if len(iban) != 24:
                raise forms.ValidationError(_("شماره شبا باید دقیقاً 24 رقم باشد (بدون احتساب IR)."))
            # اضافه کردن IR و فرمت‌بندی
            formatted_iban = 'IR' + ''.join([iban[i:i + 4] for i in range(0, 24, 4)])
            return formatted_iban
        return iban

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone:
            phone = ''.join(filter(str.isdigit, phone))
            if phone.startswith('98'):
                phone = '0' + phone[2:]
            elif phone.startswith('+98'):
                phone = '0' + phone[3:]
            if not self.validate_iranian_phone(phone):
                raise forms.ValidationError(_("شماره تلفن معتبر نیست. فرمت صحیح: 09xxxxxxxxx"))
            if len(phone) == 11 and phone.startswith('0'):
                formatted_phone = f"{phone[:4]} {phone[4:7]} {phone[7:9]} {phone[9:11]}"
                return formatted_phone
        return phone

    def validate_iranian_phone(self, phone):
        pattern = r'^0(9[0-9]{9})$'
        return re.match(pattern, phone) is not None

    def clean(self):
        cleaned_data = super().clean()
        entity_type = cleaned_data.get('entity_type')
        name = cleaned_data.get('name')
        family = cleaned_data.get('family')
        legal_name = cleaned_data.get('legal_name')

        if entity_type == 'INDIVIDUAL':
            if not name:
                self.add_error('name', _("نام برای اشخاص حقیقی الزامی است."))
            if not family:
                self.add_error('family', _("نام خانوادگی برای اشخاص حقیقی الزامی است."))
            if legal_name or cleaned_data.get('brand_name'):
                self.add_error('legal_name', _("نام حقوقی و نام تجاری فقط برای اشخاص حقوقی قابل استفاده است."))
        elif entity_type == 'LEGAL':
            if not legal_name:
                self.add_error('legal_name', _("نام حقوقی برای اشخاص حقوقی الزامی است."))
            if name or family:
                self.add_error('name', _("نام و نام خانوادگی فقط برای اشخاص حقیقی قابل استفاده است."))
        return cleaned_data