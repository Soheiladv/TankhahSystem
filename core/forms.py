from django import forms
from django.core.exceptions import ValidationError

from Tanbakhsystem.utils import convert_jalali_to_gregorian, convert_gregorian_to_jalali, convert_to_farsi_numbers
from .models import Project, Organization, TimeLockModel, UserPost, Post, PostHistory
from django.utils.translation import gettext_lazy as _

from django import forms
from .models import Project, Organization
from django.utils.translation import gettext_lazy as _

from django_jalali.forms import jDateField

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

from django.core.exceptions import ValidationError
from jdatetime import datetime as jdatetime

class ProjectForm(forms.ModelForm):
    budget = forms.IntegerField(  # تغییر به IntegerField برای هماهنگی با مدل
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
        label=_('تاریخ شروع'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        })
    )
    end_date = forms.CharField(
        label=_('تاریخ پایان'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        }),
        required=False
    )

    class Meta:
        model = Project
        fields = ['name', 'code', 'organizations', 'start_date', 'end_date', 'description', 'budget', 'priority', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام پروژه را وارد کنید'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'کد پروژه'}),
            'organizations': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'توضیحات پروژه'}),
        }
        labels = {
            'name': _('نام پروژه'),
            'code': _('کد پروژه'),
            'organizations': _('مجتمع‌های مرتبط'),
            'start_date': _('تاریخ شروع'),
            'end_date': _('تاریخ پایان'),
            'description': _('توضیحات'),
            'budget': _('بودجه (ريال)'),
            'priority': _('اولویت'),
            'is_active': _('فعال'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organizations'].queryset = Organization.objects.filter(org_type='COMPLEX')
        if self.instance.pk:
            jalali_start = jdatetime.fromgregorian(date=self.instance.start_date).strftime('%Y/%m/%d')
            jalali_end = (
                jdatetime.fromgregorian(date=self.instance.end_date).strftime('%Y/%m/%d')
                if self.instance.end_date else ''
            )
            print(f"Gregorian Start: {self.instance.start_date}, Jalali Start: {jalali_start}")
            print(f"Gregorian End: {self.instance.end_date}, Jalali End: {jalali_end}")
            self.fields['start_date'].initial = jalali_start
            self.fields['end_date'].initial = jalali_end

    def clean_start_date(self):
        start_date_str = self.cleaned_data['start_date']
        try:
            j_date = jdatetime.strptime(start_date_str, '%Y/%m/%d')
            g_date = j_date.togregorian()
            return g_date.date()
        except ValueError:
            raise ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean_end_date(self):
        end_date_str = self.cleaned_data.get('end_date')
        if not end_date_str:
            return None
        try:
            j_date = jdatetime.strptime(end_date_str, '%Y/%m/%d')
            g_date = j_date.togregorian()
            return g_date.date()
        except ValueError:
            raise ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and start_date > end_date:
            raise ValidationError(_("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد."))
        return cleaned_data

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

# class PostForm(forms.ModelForm):
#     class Meta:
#         model = Post
#         fields = ['name', 'organization', 'parent', 'level', 'branch', 'description']
#         widgets = {
#             'name': forms.TextInput(attrs={'class': 'form-control'}),
#             'organization': forms.Select(attrs={'class': 'form-control'}),
#             'parent': forms.Select(attrs={'class': 'form-control'}),
#             'level': forms.NumberInput(attrs={'class': 'form-control'}),
#             'branch': forms.Select(attrs={'class': 'form-control'}),
#             'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
#         }
#         labels = {
#             'name': _('نام پست'),
#             'organization': _('سازمان'),
#             'parent': _('پست والد'),
#             'level': _('سطح'),
#             'branch': _('شاخه'),
#             'description': _('توضیحات'),
#         }
# class UserPostForm(forms.ModelForm):
#     class Meta:
#         model = UserPost
#         fields = ['user', 'post']
#         widgets = {
#             'user': forms.Select(attrs={'class': 'form-control'}),
#             'post': forms.Select(attrs={'class': 'form-control'}),
#         }
#         labels = {
#             'user': _('کاربر'),
#             'post': _('پست'),
#         }
# class PostHistoryForm(forms.ModelForm):
#     class Meta:
#         model = PostHistory
#         fields = ['post', 'changed_field', 'old_value', 'new_value', 'changed_by']
#         widgets = {
#             'post': forms.Select(attrs={'class': 'form-control'}),
#             'changed_field': forms.TextInput(attrs={'class': 'form-control'}),
#             'old_value': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
#             'new_value': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
#             'changed_by': forms.Select(attrs={'class': 'form-control'}),
#         }
#         labels = {
#             'post': _('پست سازمانی'),
#             'changed_field': _('فیلد تغییر یافته'),
#             'old_value': _('مقدار قبلی'),
#             'new_value': _('مقدار جدید'),
#             'changed_by': _('تغییر دهنده'),
#         }

# -- new
# tanbakh/forms.py
from django import forms
from .models import Post, UserPost, PostHistory
from django_jalali.forms import jDateField

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['name', 'organization', 'parent', 'level', 'branch', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام پست'}),
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'level': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class UserPostForm(forms.ModelForm):
    class Meta:
        model = UserPost
        fields = ['user', 'post']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'post': forms.Select(attrs={'class': 'form-control'}),
        }

class PostHistoryForm(forms.ModelForm):
    # changed_at = jDateField(
    #     widget=forms.DateInput(attrs={'class': 'form-control', 'data-jdp': ''}),
    #     label='تاریخ تغییر'
    # )

    class Meta:
        model = PostHistory
        fields = ['post', 'changed_field', 'old_value', 'new_value',   'changed_by']
        widgets = {
            'post': forms.Select(attrs={'class': 'form-control'}),
            'changed_field': forms.TextInput(attrs={'class': 'form-control'}),
            'old_value': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'new_value': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'changed_by': forms.Select(attrs={'class': 'form-control'}),
        }