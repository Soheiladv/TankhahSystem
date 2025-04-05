from django import forms
from django.core.exceptions import ValidationError

from Tanbakhsystem.utils import convert_jalali_to_gregorian, convert_gregorian_to_jalali, convert_to_farsi_numbers
from accounts.models import TimeLockModel
from .models import Project, Organization, UserPost, Post, PostHistory, WorkflowStage, SubProject
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
from core.models import WorkflowStage
from tankhah.models import StageApprover

class ProjectForm(forms.ModelForm):
    budget = forms.IntegerField(  # تغییر به IntegerField برای هماهنگی با مدل
        label=_("بودجه (ريال)"),widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'مبلغ بودجه'}),required=False)
    priority = forms.ChoiceField(choices=[('LOW', _('کم')), ('MEDIUM', _('متوسط')), ('HIGH', _('زیاد'))],
        label=_("اولویت"),widget=forms.Select(attrs={'class': 'form-control'}),initial='MEDIUM')
    is_active = forms.BooleanField(label=_("فعال"),widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False,initial=True)

    start_date = forms.CharField(label=_('تاریخ شروع'),widget=forms.TextInput(attrs={
            'data-jdp': '','class': 'form-control','placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))}))
    end_date = forms.CharField(label=_('تاریخ پایان'),widget=forms.TextInput(attrs={
            'data-jdp': '','class': 'form-control','placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))}),required=False)
    workflow_stages = forms.ModelMultipleChoiceField(queryset=WorkflowStage.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),required=False,label=_('مراحل گردش کار مرتبط')    )
    has_subproject = forms.BooleanField(
        label=_("آیا زیرمجموعه پروژه دارد؟"), widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}), required=False
    )
    subproject_name = forms.CharField(
        label=_("نام زیرمجموعه پروژه"), widget=forms.TextInput(attrs={'class': 'form-control'}), required=False
    )
    subproject_description = forms.CharField(
        label=_("توضیحات زیرمجموعه پروژه"), widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=False
    )

    class Meta:
        model = Project
        fields = ['name', 'code', 'organizations', 'start_date', 'end_date', 'description', 'budget', 'priority', 'is_active', 'workflow_stages']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام پروژه (مثل پروژه توسعه نرم‌افزار)'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'کد پروژه (مثل 04-S-001)'}),
            'organizations': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'rows': 1, 'class': 'form-control', 'placeholder': 'توضیحات پروژه (اختیاری)'})
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
        # همه سازمان‌ها رو لود کن
        self.fields['organizations'].queryset = Organization.objects.all()
        if self.instance.pk:
            jalali_start = jdatetime.fromgregorian(date=self.instance.start_date).strftime('%Y/%m/%d')
            jalali_end = (
                jdatetime.fromgregorian(date=self.instance.end_date).strftime('%Y/%m/%d')
                if self.instance.end_date else ''
            )
            self.fields['start_date'].initial = jalali_start
            self.fields['end_date'].initial = jalali_end

            # چک کن اگه ساب‌پروژه داره
            if self.instance.subprojects.exists():
                subproject = self.instance.subprojects.first()
                self.fields['has_subproject'].initial = True
                self.fields['subproject_name'].initial = subproject.name
                self.fields['subproject_description'].initial = subproject.description

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
        has_subproject = cleaned_data.get('has_subproject')
        subproject_name = cleaned_data.get('subproject_name')
        if start_date and end_date and start_date > end_date:
            raise ValidationError(_("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد."))
        if has_subproject and not subproject_name:
            raise ValidationError(_("لطفاً نام ساب‌پروژه را وارد کنید."))
        return cleaned_data

    def save(self, commit=True):
        project = super().save(commit=False)
        if commit:
            project.save()
            self.save_m2m()  # ذخیره روابط ManyToMany مثل organizations
            # ایجاد ساب‌پروژه اگه تیک زده شده باشه
            if self.cleaned_data.get('has_subproject') and self.cleaned_data.get('subproject_name'):
                SubProject.objects.get_or_create(
                    project=project,
                    name=self.cleaned_data['subproject_name'],
                    defaults={'description': self.cleaned_data.get('subproject_description', ''), 'is_active': True},
                )
        return project



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
# -- new
# tanbakh/forms.py

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['workflow_stages'] = forms.ModelMultipleChoiceField(
                queryset=WorkflowStage.objects.all(),
                widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
                required=False,
                label=_('مراحل تأیید'),
                initial=WorkflowStage.objects.filter(stageapprover__post=self.instance)
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            if 'workflow_stages' in self.fields:
                StageApprover.objects.filter(post=instance).delete()
                for stage in self.cleaned_data['workflow_stages']:
                    StageApprover.objects.create(post=instance, stage=stage)
        return instance

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

class WorkflowStageForm(forms.ModelForm):
    # is_active = forms.BooleanField(
    #     label=_("فعال"),
    #     widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    #     required=False,
    #     initial=True
    # )
    # is_final_stage = forms.BooleanField(
    #     label=_("مرحله نهایی تایید تنخواه"),
    #     widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    #     required=False,
    #     initial=True
    # )
    class Meta:
        model = WorkflowStage
        fields = ['name', 'order', 'description','is_active','is_final_stage']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام مرحله'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ترتیب'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'توضیحات'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input',  'placeholder': 'فعال'}),
            'is_final_stage': forms.CheckboxInput(attrs={'class': 'form-check-input', 'rows': 3, 'placeholder': 'مرحله نهایی تایید تنخواه'}),
        }

class SubProjectForm(forms.ModelForm):
    class Meta:
        model = SubProject
        fields = ['project', 'name', 'description', 'is_active']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام ساب‌پروژه را وارد کنید')}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': _('توضیحات ساب‌پروژه')}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'project': _('پروژه اصلی'),
            'name': _('نام ساب‌پروژه'),
            'description': _('توضیحات'),
            'is_active': _('فعال'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # فقط پروژه‌های فعال رو نشون بده
        self.fields['project'].queryset = Project.objects.filter(is_active=True)


