from django import forms

from Tanbakhsystem.utils import convert_jalali_to_gregorian, convert_gregorian_to_jalali, convert_to_farsi_numbers
from .models import Project, Organization, TimeLockModel, UserPost, Post, PostHistory
from django.utils.translation import gettext_lazy as _

from django import forms
from .models import Project, Organization
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import datetime
import jdatetime

class ProjectForm(forms.ModelForm):
    """فرم ایجاد و ویرایش پروژه با فیلدهای اضافی و اعتبارسنجی"""
    budget = forms.DecimalField(
        max_digits=15, decimal_places=2,
        label=_("بودجه (ريال)"),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'مبلغ بودجه'}),
        required=False
    )
    priority = forms.ChoiceField(
        choices=[('LOW', _('کم')), ('MEDIUM', _('متوسط')), ('HIGH', _('زیاد'))],
        label=_("اولویت"),
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='MEDIUM'
    )
    is_active = forms.BooleanField(
        label=_("فعال"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False,
        initial=True
    )

    start_date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        })
    )
    end_date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        })
    )

    class Meta:
        model = Project
        fields = ['name', 'code', 'organizations', 'start_date', 'end_date', 'description', 'budget', 'priority', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام پروژه را وارد کنید'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'کد پروژه'}),
            'organizations': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            # 'organizations': forms.Select(attrs={'class': 'form-check-input'}),
            # 'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            # 'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'توضیحات پروژه'}),
        }
        labels = {
            'name': _('نام پروژه'),
            'code': _('کد پروژه'),
            'organizations': _('مجتمع‌های مرتبط'),
            'start_date': _('تاریخ شروع'),
            'end_date': _('تاریخ پایان'),
            'description': _('توضیحات'),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        budget = cleaned_data.get('budget')

        # اعتبارسنجی تاریخ‌ها
        if start_date and end_date and start_date > end_date:
            raise ValidationError(_("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد."))

        # اعتبارسنجی بودجه
        if budget and budget < 0:
            raise ValidationError(_("بودجه نمی‌تواند منفی باشد."))
        return cleaned_data



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # محدود کردن انتخاب سازمان‌ها به مجتمع‌ها
        self.fields['organizations'].queryset = Organization.objects.filter(org_type='COMPLEX')
        if self.instance.pk:
           self.fields['start_date'].initial = convert_gregorian_to_jalali(self.instance.start_date)
           self.fields['end_date'].initial = convert_gregorian_to_jalali(self.instance.end_date)



class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['code', 'name', 'org_type', 'description']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'org_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'code': _('کد سازمان'),
            'name': _('نام سازمان'),
            'org_type': _('نوع سازمان'),
            'description': _('توضیحات'),
        }

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['name', 'organization', 'parent', 'level', 'branch', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'level': forms.NumberInput(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'name': _('نام پست'),
            'organization': _('سازمان'),
            'parent': _('پست والد'),
            'level': _('سطح'),
            'branch': _('شاخه'),
            'description': _('توضیحات'),
        }
class UserPostForm(forms.ModelForm):
    class Meta:
        model = UserPost
        fields = ['user', 'post']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'post': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'user': _('کاربر'),
            'post': _('پست'),
        }
class PostHistoryForm(forms.ModelForm):
    class Meta:
        model = PostHistory
        fields = ['post', 'changed_field', 'old_value', 'new_value', 'changed_by']
        widgets = {
            'post': forms.Select(attrs={'class': 'form-control'}),
            'changed_field': forms.TextInput(attrs={'class': 'form-control'}),
            'old_value': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'new_value': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'changed_by': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'post': _('پست سازمانی'),
            'changed_field': _('فیلد تغییر یافته'),
            'old_value': _('مقدار قبلی'),
            'new_value': _('مقدار جدید'),
            'changed_by': _('تغییر دهنده'),
        }

class TimeLockModelForm(forms.ModelForm):
    class Meta:
        model = TimeLockModel
        fields = ['lock_key', 'hash_value', 'salt', 'is_active', 'organization_name']
        widgets = {
            'lock_key': forms.TextInput(attrs={'class': 'form-control'}),
            'hash_value': forms.TextInput(attrs={'class': 'form-control'}),
            'salt': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'organization_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'lock_key': _('کلید قفل'),
            'hash_value': _('هش مقدار'),
            'salt': _('مقدار تصادفی'),
            'is_active': _('وضعیت فعال'),
            'organization_name': _('نام مجموعه'),
        }