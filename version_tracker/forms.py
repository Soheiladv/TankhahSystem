from django import forms
from .models import AppVersion
from django_jalali.admin.widgets import AdminjDateWidget
from django.core.exceptions import ValidationError
import json

class AppVersionForm(forms.ModelForm):
    class Meta:
        model = AppVersion
        fields = '__all__'
        widgets = {
            'app_name': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100%; direction: rtl;',
                'placeholder': 'نام اپلیکیشن را وارد کنید',
            }),
            'version_number': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100%;',
                'placeholder': 'شماره نسخه (مثال: 1.0.0)',
            }),
            'version_type': forms.Select(attrs={
                'class': 'form-select',
                'style': 'width: 100%;',
            }),
            'release_date': AdminjDateWidget(attrs={
                'class': 'jalali_date-date form-control',
                'style': 'width: 100%;',
                'placeholder': 'تاریخ انتشار (مثال: 1402/01/01)',
            }),
            'code_hash': forms.TextInput(attrs={
                'class': 'form-control bg-light',
                'style': 'width: 100%;',
                'readonly': 'readonly',
            }),
            'changed_files': forms.Textarea(attrs={
                'class': 'form-control',
                'style': 'width: 100%; direction: ltr;',
                'rows': 4,
                'placeholder': 'فایل‌های تغییر یافته را به‌صورت JSON وارد کنید',
            }),
            'system_info': forms.Textarea(attrs={
                'class': 'form-control bg-light',
                'style': 'width: 100%; direction: ltr;',
                'rows': 4,
                'readonly': 'readonly',
            }),
            'major': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100%;',
                'placeholder': '0',
            }),
            'minor': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100%;',
                'placeholder': '0',
            }),
            'patch': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100%;',
                'placeholder': '0',
            }),
            'build': forms.NumberInput(attrs={
                'class': 'form-control',
                'style': 'width: 100%;',
                'placeholder': '0',
            }),
        }
        labels = {
            'app_name': 'نام اپلیکیشن',
            'version_number': 'شماره نسخه',
            'version_type': 'نوع نسخه',
            'release_date': 'تاریخ انتشار',
            'code_hash': 'هش کد',
            'changed_files': 'فایل‌های تغییر یافته',
            'system_info': 'اطلاعات سیستم',
            'major': 'نسخه اصلی',
            'minor': 'نسخه فرعی',
            'patch': 'وصله',
            'build': 'شماره ساخت',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code_hash'].disabled = True
        self.fields['system_info'].disabled = True
        if self.instance.pk:
            self.fields['changed_files'].initial = json.dumps(self.instance.changed_files, indent=2, ensure_ascii=False)
            self.fields['system_info'].initial = json.dumps(self.instance.system_info, indent=2, ensure_ascii=False)

    def clean_changed_files(self):
        data = self.cleaned_data['changed_files']
        try:
            if isinstance(data, str):
                return json.loads(data)
            return data
        except json.JSONDecodeError:
            raise ValidationError("فایل‌های تغییر یافته باید فرمت JSON معتبر داشته باشند.")

    def clean_system_info(self):
        data = self.cleaned_data['system_info']
        try:
            if isinstance(data, str):
                return json.loads(data)
            return data
        except json.JSONDecodeError:
            raise ValidationError("اطلاعات سیستم باید فرمت JSON معتبر داشته باشند.")