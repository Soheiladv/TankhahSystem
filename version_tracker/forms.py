from django import forms
from django.utils.translation import gettext_lazy as _
from notificationApp.models import BackupSchedule
from accounts.models import CustomUser
from .models import AppVersion

class BackupScheduleForm(forms.ModelForm):
    """فرم اسکچول پشتیبان‌گیری"""
    
    class Meta:
        model = BackupSchedule
        fields = [
            'name', 'description', 'frequency', 'custom_cron', 'is_active',
            'database', 'format_type', 'encrypt', 'password',
            'notify_on_success', 'notify_on_failure', 'notify_recipients'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('نام اسکچول')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('توضیحات اسکچول')
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'custom_cron': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('مثال: 0 2 * * *')
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'database': forms.Select(attrs={
                'class': 'form-select'
            }),
            'format_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'encrypt': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': _('رمز عبور')
            }),
            'notify_on_success': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notify_on_failure': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notify_recipients': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 5
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تنظیم choices برای گیرندگان اعلان
        self.fields['notify_recipients'].queryset = CustomUser.objects.filter(
            is_active=True
        ).order_by('username')
        
        # تنظیم help text
        self.fields['name'].help_text = _('نام منحصر به فرد برای اسکچول')
        self.fields['description'].help_text = _('توضیحات اختیاری')
        self.fields['frequency'].help_text = _('فرکانس اجرای پشتیبان‌گیری')
        self.fields['custom_cron'].help_text = _('فرمت cron سفارشی (در صورت انتخاب "سفارشی")')
        self.fields['database'].help_text = _('دیتابیس مورد نظر برای پشتیبان‌گیری')
        self.fields['format_type'].help_text = _('فرمت فایل پشتیبان')
        self.fields['encrypt'].help_text = _('رمزگذاری فایل پشتیبان')
        self.fields['password'].help_text = _('رمز عبور برای رمزگذاری')
        self.fields['notify_on_success'].help_text = _('اعلان در صورت موفقیت')
        self.fields['notify_on_failure'].help_text = _('اعلان در صورت خطا')
        self.fields['notify_recipients'].help_text = _('کاربرانی که اعلان دریافت خواهند کرد')
    
    def clean(self):
        cleaned_data = super().clean()
        frequency = cleaned_data.get('frequency')
        custom_cron = cleaned_data.get('custom_cron')
        encrypt = cleaned_data.get('encrypt')
        password = cleaned_data.get('password')
        
        # بررسی cron سفارشی
        if frequency == 'CUSTOM' and not custom_cron:
            raise forms.ValidationError(_('در صورت انتخاب "سفارشی"، باید cron سفارشی را وارد کنید'))
        
        # بررسی رمز عبور
        if encrypt and not password:
            raise forms.ValidationError(_('در صورت فعال کردن رمزگذاری، باید رمز عبور را وارد کنید'))
        
        return cleaned_data
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # بررسی تکراری نبودن نام
            queryset = BackupSchedule.objects.filter(name=name)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError(_('اسکچولی با این نام قبلاً وجود دارد'))
        return name
    
    def clean_custom_cron(self):
        custom_cron = self.cleaned_data.get('custom_cron')
        if custom_cron:
            # بررسی فرمت cron (ساده)
            parts = custom_cron.strip().split()
            if len(parts) != 5:
                raise forms.ValidationError(_('فرمت cron باید شامل 5 بخش باشد (دقیقه ساعت روز ماه روز_هفته)'))
        return custom_cron

class AppVersionForm(forms.ModelForm):
    """فرم AppVersion"""
    
    class Meta:
        model = AppVersion
        fields = ['app_name', 'version_number', 'version_type']
        widgets = {
            'app_name': forms.TextInput(attrs={'class': 'form-control'}),
            'version_number': forms.TextInput(attrs={'class': 'form-control'}),
            'version_type': forms.Select(attrs={'class': 'form-select'}),
        }