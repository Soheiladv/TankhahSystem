from django import forms
from django.utils.translation import gettext_lazy as _
from budgets.models import Payee
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
                'oninput': 'this.value = this.value.replace(/[^0-9]/g, \'\')'
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره حساب (عددی)',
                'oninput': 'this.value = this.value.replace(/[^0-9]/g, \'\')'
            }),
            'iban': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'IR',
                'dir': 'ltr',
                'style': 'text-align: left;'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'آدرس کامل'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '09xxxxxxxxx',
                'oninput': 'this.value = this.value.replace(/[^0-9]/g, \'\')'
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
        # اضافه کردن کلاس form-control به همه فیلدها
        for field_name, field in self.fields.items():
            if field_name != 'is_active' and 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'

    def clean_national_id(self):
        national_id = self.cleaned_data.get('national_id', '')
        entity_type = self.cleaned_data.get('entity_type')

        if national_id:
            # حذف همه کاراکترهای غیرعددی
            national_id = ''.join(filter(str.isdigit, national_id))

            if entity_type == 'INDIVIDUAL':
                if len(national_id) != 10:
                    raise forms.ValidationError(_("کد ملی باید 10 رقمی باشد."))

                # اعتبارسنجی چک‌سام کد ملی
                if not self.validate_national_code(national_id):
                    raise forms.ValidationError(_("کد ملی معتبر نیست."))

            elif entity_type == 'LEGAL':
                if len(national_id) != 11:
                    raise forms.ValidationError(_("شناسه حقوقی باید 11 رقمی باشد."))

                # اعتبارسنجی چک‌سام شناسه حقوقی
                if not self.validate_legal_code(national_id):
                    raise forms.ValidationError(_("شناسه حقوقی معتبر نیست."))

        return national_id

    def validate_national_code(self, code):
        """اعتبارسنجی کد ملی ایران"""
        if len(code) != 10:
            return False

        # بررسی اینکه همه ارقام یکسان نباشند
        if code == code[0] * 10:
            return False

        sum = 0
        for i in range(9):
            sum += int(code[i]) * (10 - i)

        remainder = sum % 11
        check_digit = int(code[9])

        return (remainder < 2 and check_digit == remainder) or (remainder >= 2 and check_digit == 11 - remainder)

    def validate_legal_code(self, code):
        """اعتبارسنجی شناسه حقوقی ایران"""
        if len(code) != 11:
            return False

        # الگوریتم اعتبارسنجی شناسه حقوقی
        sum = 0
        weights = [29, 27, 23, 19, 17, 29, 27, 23, 19, 17]

        for i in range(10):
            sum += int(code[i]) * weights[i]

        remainder = sum % 11
        if remainder == 10:
            remainder = 0

        return remainder == int(code[10])

    def clean_account_number(self):
        account_number = self.cleaned_data.get('account_number', '')

        if account_number:
            # حذف همه کاراکترهای غیرعددی
            account_number = ''.join(filter(str.isdigit, account_number))

            # اعتبارسنجی طول شماره حساب
            if len(account_number) < 5 or len(account_number) > 20:
                raise forms.ValidationError(_("شماره حساب باید بین 5 تا 20 رقم باشد."))

        return account_number

    def clean_iban(self):
        iban = self.cleaned_data.get('iban', '').strip().upper()

        if iban:
            # حذف فاصله‌ها و خط تیره
            iban = iban.replace(' ', '').replace('-', '')

            # بررسی شروع با IR
            if not iban.startswith('IR'):
                raise forms.ValidationError(_("شماره شبا باید با IR شروع شود."))

            # بررسی طول
            if len(iban) != 26:
                raise forms.ValidationError(_("شماره شبا باید 26 کاراکتر باشد (IR + 24 رقم)."))

            # بررسی اعداد بعد از IR
            if not iban[2:].isdigit():
                raise forms.ValidationError(_("بعد از IR، فقط اعداد مجاز هستند."))

        return iban

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')

        if phone:
            # حذف همه کاراکترهای غیرعددی
            phone = ''.join(filter(str.isdigit, phone))

            # حذف پیش‌شماره بین‌المللی اگر وجود دارد
            if phone.startswith('98'):
                phone = '0' + phone[2:]
            elif phone.startswith('+98'):
                phone = '0' + phone[3:]

            # اعتبارسنجی شماره تلفن ایران
            if not self.validate_iranian_phone(phone):
                raise forms.ValidationError(_("شماره تلفن معتبر نیست. فرمت صحیح: 09xxxxxxxxx"))

            # فرمت کردن شماره تلفن
            if len(phone) == 11 and phone.startswith('0'):
                formatted_phone = f"{phone[0:4]} {phone[4:7]} {phone[7:9]} {phone[9:11]}"
                return formatted_phone

        return phone

    def validate_iranian_phone(self, phone):
        """اعتبارسنجی شماره تلفن ایران"""
        pattern = r'^0(9[0-9]{9})$'
        return re.match(pattern, phone) is not None

    def clean(self):
        cleaned_data = super().clean()
        entity_type = cleaned_data.get('entity_type')
        name = cleaned_data.get('name')
        family = cleaned_data.get('family')
        legal_name = cleaned_data.get('legal_name')

        # اعتبارسنجی نوع شخص
        if entity_type == 'INDIVIDUAL':
            if not name:
                self.add_error('name', _("نام برای اشخاص حقیقی الزامی است."))
            if not family:
                self.add_error('family', _("نام خانوادگی برای اشخاص حقیزی الزامی است."))
            if legal_name:
                self.add_error('legal_name', _("نام حقوقی فقط برای اشخاص حقوقی قابل استفاده است."))

        elif entity_type == 'LEGAL':
            if not legal_name:
                self.add_error('legal_name', _("نام حقوقی برای اشخاص حقوقی الزامی است."))
            if name or family:
                self.add_error('name', _("نام و نام خانوادگی فقط برای اشخاص حقیقی قابل استفاده است."))

        return cleaned_data