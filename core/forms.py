import re

from accounts.models import TimeLockModel, CustomUser
from core.models import Project, Organization, UserPost, Post, PostHistory, SubProject, OrganizationType, \
    SystemSettings, Branch, PostAction, Status, FontSettings
from django.core.exceptions import ValidationError
from jdatetime import datetime as jdatetime
from django.utils.translation import gettext_lazy as _
from core.models import Organization, Project, SubProject
import jdatetime
import logging
logger = logging.getLogger(__name__)

from django import forms

class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = [
            'budget_locked_percentage_default',
            'budget_warning_threshold_default',
            'budget_warning_action_default',
            'allocation_locked_percentage_default',
            'tankhah_used_statuses',
            'tankhah_accessible_organizations',
            'tankhah_payment_ceiling_default',
            'tankhah_payment_ceiling_enabled_default',
            'enforce_strict_approval_order',
            'allow_bypass_org_chart',
            'allow_action_without_org_chart',
            'enforce_single_browser_session',
            'enforce_single_tab',
            'heartbeat_interval_ms',
            'heartbeat_stale_ms',
        ]
        widgets = {
            'budget_locked_percentage_default': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100', 'placeholder': _('مثلاً 10') }),
            'budget_warning_threshold_default': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100', 'placeholder': _('مثلاً 20') }),
            'budget_warning_action_default': forms.Select(attrs={'class': 'form-select'}),
            'allocation_locked_percentage_default': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'tankhah_used_statuses': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('["PAID","APPROVED"]') }),
            'tankhah_accessible_organizations': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('[1,2,3]') }),
            'tankhah_payment_ceiling_default': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'tankhah_payment_ceiling_enabled_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enforce_strict_approval_order': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_bypass_org_chart': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_action_without_org_chart': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enforce_single_browser_session': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enforce_single_tab': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'heartbeat_interval_ms': forms.NumberInput(attrs={'class': 'form-control', 'step': '100', 'min': '1000'}),
            'heartbeat_stale_ms': forms.NumberInput(attrs={'class': 'form-control', 'step': '100', 'min': '2000'}),
        }
        labels = {
            'budget_locked_percentage_default': _('درصد قفل پیش‌فرض بودجه'),
            'budget_warning_threshold_default': _('آستانه اخطار بودجه'),
            'enforce_single_browser_session': _('محدودیت به یک مرورگر (یک سشن)'),
            'enforce_single_tab': _('محدودیت به یک تب مرورگر'),
            'heartbeat_interval_ms': _('بازه ضربان تب (ms)'),
            'heartbeat_stale_ms': _('مهلت منقضی شدن تب (ms)'),
        }
        help_texts = {
            'budget_locked_percentage_default': _('وقتی درصد باقیمانده بودجه کمتر از این مقدار شود قفل می‌شود.'),
            'budget_warning_threshold_default': _('اگر درصد باقیمانده از این مقدار کمتر شود هشدار فعال می‌شود.'),
            'allocation_locked_percentage_default': _('حداقل درصد باقیمانده تخصیص برای قفل شدن تخصیص‌ها.'),
            'tankhah_payment_ceiling_default': _('حداکثر مبلغ مجاز هر پرداخت تنخواه (ریال).'),
            'tankhah_payment_ceiling_enabled_default': _('در صورت فعال بودن، سقف پرداخت تنخواه اعمال می‌شود.'),
            'tankhah_accessible_organizations': _('لیست ID سازمان‌های مجاز به‌صورت JSON مانند [1,2,3].'),
            'tankhah_used_statuses': _('لیست کد وضعیت‌های مصرف‌شده به‌صورت JSON مانند ["PAID","APPROVED"].'),
            'enforce_strict_approval_order': _('الزام رعایت ترتیب سلسله‌مراتب تأیید.'),
            'allow_bypass_org_chart': _('اجازه رد شدن از سلسله‌مراتب در شرایط خاص.'),
            'allow_action_without_org_chart': _('اجازه اقدام بدون داشتن پست سازمانی.'),
        }

    def clean_tankhah_used_statuses(self):
        # این متدها را به دلیل ماهیت JSONی آن‌ها نگه دارید.
        val = self.cleaned_data.get('tankhah_used_statuses')
        if not val: # چک کردن مقدار خالی بهتر از (None, '') است
            return []
        if isinstance(val, list):
            return val
        try:
            import json
            parsed = json.loads(val)
            if not isinstance(parsed, list):
                raise ValidationError(_('قالب وضعیت‌ها باید لیست JSON باشد.'))
            return parsed
        except Exception:
            raise ValidationError(_('قالب وضعیت‌ها باید لیست JSON معتبر باشد.'))

    def clean_tankhah_accessible_organizations(self):
        val = self.cleaned_data.get('tankhah_accessible_organizations')
        if not val: # چک کردن مقدار خالی بهتر از (None, '') است
            return []
        if isinstance(val, list):
            return val
        try:
            import json
            parsed = json.loads(val)
            if not isinstance(parsed, list):
                raise ValidationError(_('قالب سازمان‌های مجاز باید لیست JSON باشد.'))
            return parsed
        except Exception:
            raise ValidationError(_('قالب سازمان‌های مجاز باید لیست JSON معتبر باشد.'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Removed dynamic dashboard toggles; dashboard visibility is no longer managed via SystemSettings

    def save(self, commit=True):
        instance = super().save(commit)
        return instance

# ========================


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

class ProjectForm(forms.ModelForm):
    has_subproject = forms.BooleanField(
        label=_("آیا ساب‌پروژه دارد؟"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    subproject_name = forms.CharField(
        label=_("نام ساب‌پروژه"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    subproject_description = forms.CharField(
        label=_("توضیحات ساب‌پروژه"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        label=_("شعبه"),
        widget=forms.Select(attrs={'class': 'form-control', 'data-control': 'select2'})
    )
    start_date = forms.CharField(
        label=_('تاریخ شروع'),  # Changed label slightly
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control form-control-lg jalali-datepicker',  # Added jalali-datepicker class
            'autocomplete': 'off',
            'placeholder': _('مثال: 1404/01/26')  # Updated placeholder
        }),
        required=True
    )
    end_date = forms.CharField(
            label=_('تاریخ خاتمه'),  # Changed label slightly
            widget=forms.TextInput(attrs={
                'data-jdp': '',
                'class': 'form-control form-control-lg jalali-datepicker',  # Added jalali-datepicker class
                'autocomplete': 'off',
                'placeholder': _('مثال: 1404/01/26')  # Updated placeholder
            }),
            required=True
        )

    class Meta:
        model = Project
        fields = [
            'name', 'code', 'priority', 'organization',
            'is_active', 'description', 'has_subproject', 'subproject_name',
            'subproject_description','start_date', 'end_date',
        ]#
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام پروژه')}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('کد پروژه')}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': _('توضیحات')}),
            'start_date': forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control jalali-datepicker', 'placeholder': '1404/01/17'}),
            'end_date': forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control jalali-datepicker', 'placeholder': '1404/01/17'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # محدود کردن سازمان‌ها به شعب فعال و قابل تخصیص بودجه
        self.fields['organization'].queryset = Organization.objects.filter( org_type__is_budget_allocatable=True, is_active=True
        ).select_related('org_type').order_by('name')

        # تنظیم مقادیر اولیه برای ویرایش پروژه
        if self.instance.pk:
            try:
                if self.instance.end_date:
                    # jalali_start = jdatetime.date.fromgregorian(date=self.instance.start_date).strftime('%Y/%m/%d')
                    # self.fields['start_date'].initial = jalali_start
                    j_date = jdatetime.date.fromgregorian(date=self.instance.start_date)
                    self.initial['start_date'] = j_date.strftime('%Y/%m/%d')

                if self.instance.end_date:

                    j_date = jdatetime.date.fromgregorian(date=self.instance.end_date)
                    self.initial['end_date'] = j_date.strftime('%Y/%m/%d')

                self.fields['organization'].initial = self.instance.organizations.first()
                if self.instance.subprojects.exists():
                    subproject = self.instance.subprojects.first()
                    self.fields['has_subproject'].initial = True
                    self.fields['subproject_name'].initial = subproject.name
                    self.fields['subproject_description'].initial = subproject.description
            except Exception as e:
                logger.error(f"Error setting initial values: {str(e)}")


    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        logger.debug(f"Cleaning start_date: input='{start_date}'")
        if not start_date:
            # This might be redundant if field is required=True
            raise ValidationError(_('تاریخ تخصیص اجباری است.'))
        try:
            # استفاده از پارسر محلی که خروجی date می‌دهد
            parsed_date = parse_jalali_date(str(start_date), field_name=_('تاریخ شروع'))
            logger.debug(f"Parsed start_date: {parsed_date}")
            return parsed_date
        except ValueError as e:  # Catch specific parsing errors
            logger.warning(f"Could not parse start_date '{start_date}': {e}")
            raise ValidationError(e)  # Show the specific error from parse_jalali_date
        except Exception as e:  # Catch other unexpected errors
            logger.error(f"Unexpected error parsing start_date '{start_date}': {e}", exc_info=True)
            raise ValidationError(_('فرمت تاریخ شروع نامعتبر است.'))

    def clean_end_date(self):
        end_date = self.cleaned_data.get('end_date')
        logger.debug(f"Cleaning end_date: input='{end_date}'")
        if not end_date:
            # This might be redundant if field is required=True
            raise ValidationError(_('تاریخ خاتمه اجباری است.'))
        try:
            parsed_date = parse_jalali_date(str(end_date), field_name=_('تاریخ خاتمه'))
            logger.debug(f"Parsed end_date: {parsed_date}")
            return parsed_date
        except ValueError as e:  # Catch specific parsing errors
            logger.warning(f"Could not parse end_date '{end_date}': {e}")
            raise ValidationError(e)  # Show the specific error from parse_jalali_date
        except Exception as e:  # Catch other unexpected errors
            logger.error(f"Unexpected error parsing end_date '{end_date}': {e}", exc_info=True)
            raise ValidationError(_('فرمت تاریخ تخصیص نامعتبر است.'))




    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code:
            raise forms.ValidationError(_('کد پروژه اجباری است.'))
        if Project.objects.exclude(pk=self.instance.pk).filter(code=code).exists():
            raise forms.ValidationError(_('این کد پروژه قبلاً استفاده شده است.'))
        return code

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        has_subproject = cleaned_data.get('has_subproject')
        subproject_name = cleaned_data.get('subproject_name')

        # بررسی تاریخ‌ها
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError(_("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد."))

        # بررسی ساب‌پروژه
        if has_subproject and not subproject_name:
            self.add_error('subproject_name', _('نام ساب‌پروژه اجباری است.'))

        return cleaned_data

    def save(self, commit=True):
        from django.db import transaction
        instance = super().save(commit=False)
        has_subproject = self.cleaned_data.get('has_subproject')
        subproject_name = self.cleaned_data.get('subproject_name')
        subproject_description = self.cleaned_data.get('subproject_description')
        organization = self.cleaned_data.get('organization')

        with transaction.atomic():
            # توضیحات خودکار در صورت خالی بودن
            try:
                if not instance.description:
                    org_name = getattr(organization, 'name', '')
                    start_j = jdatetime.date.fromgregorian(date=instance.start_date).strftime('%Y/%m/%d') if instance.start_date else ''
                    end_j = jdatetime.date.fromgregorian(date=instance.end_date).strftime('%Y/%m/%d') if instance.end_date else ''
                    parts = [
                        _("پروژه"), f"{instance.name}",
                        _("با کد"), f"{instance.code}",
                    ]
                    if org_name:
                        parts += [_("در شعبه"), org_name]
                    if start_j:
                        parts += [_("از تاریخ"), start_j]
                    if end_j:
                        parts += [_("تا"), end_j]
                    instance.description = ' '.join([str(p) for p in parts if p])
            except Exception as e:
                logger.warning(f"Auto description generation failed: {e}")

            if commit:
                instance.save()
                instance.organizations.set([organization])
                self.save_m2m()

                if has_subproject and subproject_name:
                    SubProject.objects.create(
                        project=instance,
                        name=subproject_name,
                        description=subproject_description,
                        is_active=True
                    )

            return instance

class SubProjectForm(forms.ModelForm):

    allocated_budget = forms.DecimalField(label=_("بودجه ساب‌پروژه"), decimal_places=2, max_digits=25, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    class Meta:
        model = SubProject
        fields = ['project', 'name', 'description', 'allocated_budget', 'is_active']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام ساب‌پروژه')}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': _('توضیحات')}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            # 'allocated_budget': forms.NumberInput(attrs={'class': 'form-control', 'step': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Project.objects.filter(is_active=True)
        if self.instance.pk:  # ویرایش
            self.fields['allocated_budget'].initial = self.instance.allocated_budget
    #
    # def clean(self):
    #     cleaned_data = super().clean()
    #     project = cleaned_data.get('project')
    #     budget = cleaned_data.get('allocated_budget')
    #     if project and budget and budget > get_project_remaining_budget(project):
    #         raise ValidationError(
    #             _("بودجه ساب‌پروژه (%(budget)s) نمی‌تواند بیشتر از بودجه باقیمانده پروژه (%(remaining)s) باشد."),
    #             params={'budget': budget, 'remaining': get_project_remaining_budget(project)}
    #         )
    #     return cleaned_data

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get('project')
        allocated_budget = cleaned_data.get('allocated_budget')
        if project and allocated_budget:
            remaining_budget = project.get_remaining_budget()
            if allocated_budget > remaining_budget:
                self.add_error(
                    'allocated_budget',
                    _('بودجه تخصیص‌یافته نمی‌تواند بیشتر از بودجه باقی‌مانده پروژه باشد: %s') % remaining_budget
                )
        return cleaned_data

class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['code', 'name', 'org_type', 'description', 'parent_organization','is_core','is_holding' ,'is_independent']
        # budget = forms.DecimalField(
        #     widget=NumberToWordsWidget(attrs={'placeholder': '  ارقام بودجه سالانه را وارد کنید'}),
        #     label='بودجه سالانه'
        # )

        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'org_type': forms.Select(attrs={'class': 'form-control'}),
            'is_core': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_holding': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_independent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            # 'budget': forms.Select(attrs={'class': 'form-control'}),
            'parent_organization': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'code': _('کد سازمان'),
            'name': _('نام سازمان'),
            'org_type': _('نوع سازمان'),
            'is_core': _('شعبه اصلی سازمان(دفتر مرکزی)'),
            'is_independent': _('مستقل کار میکند؟'),
            'is_holding': _(' هلدینگ است ؟'),
            'parent_organization': _('نوع سازمان'),
            'description': _('توضیحات'),
        }

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = [
            'name', 'organization', 'parent', 'branch', 'description',
            'is_active', 'max_change_level', 'is_payment_order_signer',
            'can_final_approve_factor', 'can_final_approve_tankhah', 'can_final_approve_budget'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام پست'}),
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'max_change_level': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'حداکثر سطح تغییر'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        # فقط پست‌های فعال برای parent و branch
        self.fields['branch'].queryset = Branch.objects.filter(is_active=True)
        self.fields['parent'].queryset = Post.objects.filter(is_active=True).exclude(pk=self.instance.pk if self.instance.pk else None)

        # مراحل تایید: از جدول Transition/PostAction استفاده می‌کنیم
        self.fields['post_actions'] = forms.ModelMultipleChoiceField(
            queryset=PostAction.objects.filter(is_active=True),
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            required=False,
            label='مراحل تأیید',
            initial=PostAction.objects.filter(post=self.instance, is_active=True) if self.instance.pk else None
        )

    def save(self, commit=True):
        post = super().save(commit=False)
        if commit:
            # استفاده از _changed_by اگر تنظیم شده باشد، در غیر این صورت از self._user
            changed_by = getattr(post, '_changed_by', self._user)
            post.save(changed_by=changed_by)
            selected_actions = self.cleaned_data.get('post_actions', [])

            # حذف PostAction هایی که انتخاب نشده‌اند
            PostAction.objects.filter(post=post).exclude(id__in=[a.id for a in selected_actions]).delete()

            # ایجاد PostAction های جدید
            existing_ids = set(PostAction.objects.filter(post=post).values_list('id', flat=True))
            for action in selected_actions:
                if action.id not in existing_ids:
                    PostAction.objects.create(
                        post=post,
                        stage=action.stage,
                        action_type=action.action_type,
                        entity_type=action.entity_type,
                        is_active=True
                    )
        return post

#================================== parse_jalali_date ==========
def parse_jalali_date(date_str, field_name="تاریخ"):
    """
    تبدیل رشته تاریخ جلالی (مثل 1404/01/17) به تاریخ میلادی.
    - کاراکترهای فارسی و جداکننده‌های مختلف را پشتیبانی می‌کند.
    - شیء datetime.date را برمی‌گرداند.
    """
    if not date_str:
        return None

    # تبدیل اعداد فارسی و کاراکترهای مختلف
    date_str = date_str.strip()
    date_str = ''.join([chr(ord(c) - 1728) if '۰' <= c <= '۹' else c for c in date_str])
    date_str = re.sub(r'[-.]', '/', date_str)

    try:
        # اصلاح: استفاده از jdatetime.datetime.strptime به جای jdatetime.date.strptime
        j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
        g_date = j_date.togregorian()
        # در نهایت، فقط بخش تاریخ (date) را برگردانید
        return g_date.date()
    except ValueError:
        logger.warning(f"Invalid jalali date format for field '{field_name}': {date_str}")
        raise ValidationError(_(f'فرمت {field_name} نامعتبر است. از فرمت 1404/01/17 استفاده کنید.'))
#============================================
#============================================
class UserPostForm(forms.ModelForm):
    """
    فرم برای ایجاد یا به‌روزرسانی اتصال کاربر به پست.
    مسئولیت: اعتبارسنجی، فیلتر کردن کاربران و پست‌های مجاز، و ذخیره تاریخ‌ها.
    """
    start_date = forms.CharField(
        label=_('تاریخ شروع فعالیت'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('1404/01/17'),
        }),
        required=True
    )
    end_date = forms.CharField(
        label=_('تاریخ خاتمه فعالیت'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('1404/01/17'),
        }),
        required=False
    )

    class Meta:
        model = UserPost
        fields = ['user', 'post', 'start_date', 'end_date', 'is_active']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'post': forms.Select(attrs={'class': 'form-select select2-post'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        logger.debug(f"[UserPostForm] شروع مقداردهی اولیه برای کاربر '{self.request.user.username if self.request else 'Anonymous'}'")

        # فیلتر کاربران فعال و تنظیم نمایش نام کامل
        self.fields['user'].queryset = CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # تنظیم نمایش نام کامل در dropdown
        def get_user_display_name(user):
            full_name = user.get_full_name()
            if full_name and full_name != user.username:
                return f"{full_name} " #({user.username})
            return user.username
        
        # تنظیم label_from_instance برای نمایش نام کامل
        self.fields['user'].label_from_instance = get_user_display_name

        # فیلتر پست‌های فعال در سازمان‌های مجاز
        if self.request and not self.request.user.is_superuser:
            user_orgs = {up.post.organization for up in self.request.user.userpost_set.filter(is_active=True)
                         if up.post.organization and not up.post.organization.is_core and not up.post.organization.is_holding}
            if not user_orgs:
                logger.warning(f"[UserPostForm] کاربر '{self.request.user.username}' به هیچ سازمان شعبه‌ای دسترسی ندارد")
                self.fields['post'].queryset = Post.objects.none()
            else:
                self.fields['post'].queryset = Post.objects.filter(
                    is_active=True,
                    organization__in=user_orgs
                ).order_by('name')
                logger.debug(f"[UserPostForm] پست‌های فیلترشده برای سازمان‌ها: {[org.name for org in user_orgs]}")
        else:
            self.fields['post'].queryset = Post.objects.filter(is_active=True).order_by('name')

        # تنظیم مقدار اولیه تاریخ‌ها و is_active
        if self.instance.pk:
            if self.instance.start_date:
                self.initial['start_date'] = self.instance.start_date.strftime('%Y/%m/%d')
            if self.instance.end_date:
                self.initial['end_date'] = self.instance.end_date.strftime('%Y/%m/%d')
            self.initial['is_active'] = self.instance.is_active
            logger.debug(f"[UserPostForm] ویرایش اتصال با ID: {self.instance.pk}, تاریخ شروع: {self.initial['start_date']}")

        # ✅ اصلاح نمایش تاریخ‌ها در فرم
        from jalali_date import date2jalali
        if self.instance.pk:
            logger.debug(f"[UserPostForm] ویرایش اتصال با ID: {self.instance.pk}, کاربر فعلی: {self.instance.user}, پست فعلی: {self.instance.post}")
            if self.instance.start_date:
                self.initial['start_date'] = date2jalali(self.instance.start_date).strftime('%Y/%m/%d')
            if self.instance.end_date:
                self.initial['end_date'] = date2jalali(self.instance.end_date).strftime('%Y/%m/%d')
            self.initial['is_active'] = self.instance.is_active


    def clean_start_date(self):
        """اعتبارسنجی تاریخ جلالی برای شروع"""
        date_  = self.cleaned_data.get('start_date')
        try:
            return parse_jalali_date(date_)
        except (ValueError, TypeError) as e:
            logger.warning(f"[UserPostForm.clean_start_date] فرمت تاریخ نامعتبر: {date_}, خطا: {str(e)}")
            raise forms.ValidationError(_('فرمت تاریخ شروع نامعتبر است. از فرمت YYYY/MM/DD استفاده کنید.'))

    def clean_end_date(self):
        """اعتبارسنجی تاریخ جلالی برای پایان"""
        date_ = self.cleaned_data.get('end_date')
        if not date_:
            return None
        try:
            return parse_jalali_date(date_)
        except (ValueError, TypeError) as e:
            logger.warning(f"[UserPostForm.clean_end_date] فرمت تاریخ نامعتبر: {date_}, خطا: {str(e)}")
            raise forms.ValidationError(_('فرمت تاریخ پایان نامعتبر است. از فرمت YYYY/MM/DD استفاده کنید.'))

    def clean(self):
        """اعتبارسنجی فرم"""
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        post = cleaned_data.get('post')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_active = cleaned_data.get('is_active')

        if user and post:
            # Only check for duplicates if we're creating a new connection or changing user/post
            current_user = getattr(self.instance, 'user', None)
            current_post = getattr(self.instance, 'post', None)
            
            logger.debug(f"[UserPostForm.clean] بررسی تداخل - Instance PK: {self.instance.pk}, Current User: {current_user}, New User: {user}, Current Post: {current_post}, New Post: {post}")
            
            # If user or post is being changed, check for existing active connections
            if (not self.instance.pk or 
                (current_user and current_user != user) or 
                (current_post and current_post != post)):
                
                logger.debug(f"[UserPostForm.clean] بررسی تداخل لازم است - Instance PK: {self.instance.pk}")
                
                # Check for existing active connections with the same user and post
                existing_connections = UserPost.objects.filter(
                    user=user,
                    post=post,
                    is_active=True
                ).exclude(pk=self.instance.pk if self.instance.pk else None)
                
                logger.debug(f"[UserPostForm.clean] تعداد اتصالات موجود: {existing_connections.count()}")
                
                # Simplified validation: Only check if there are multiple active connections
                if existing_connections.exists():
                    logger.warning(f"[UserPostForm.clean] اتصال فعال دیگری برای کاربر '{user.username}' و پست '{post.name}' وجود دارد")
                    # Allow the update but warn about existing connections
                    # raise ValidationError(_('این کاربر قبلاً به این پست متصل است و اتصال فعال است.'))
                    logger.info(f"[UserPostForm.clean] اجازه به‌روزرسانی داده شد - اتصالات موجود: {existing_connections.count()}")
                else:
                    logger.debug(f"[UserPostForm.clean] هیچ اتصال فعالی برای این کاربر و پست وجود ندارد")
            else:
                logger.debug(f"[UserPostForm.clean] نیازی به بررسی تداخل نیست - کاربر و پست تغییر نکرده‌اند")

        # ✅ در اینجا تاریخ‌ها از قبل در clean_start_date و clean_end_date تبدیل شدن
        if end_date and start_date and end_date < start_date:
            logger.warning(f"[UserPostForm.clean] تاریخ پایان {end_date} قبل از تاریخ شروع {start_date} است")
            raise ValidationError({'end_date': _('تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.')})

        from django.utils import timezone
        if is_active and end_date and end_date < timezone.now().date():
            raise ValidationError({'end_date': _('اتصال فعال نمی‌تواند تاریخ پایانی منقضی‌شده داشته باشد.')})

        logger.debug("[UserPostForm.clean] اعتبارسنجی فرم با موفقیت انجام شد")
        return cleaned_data

    def save(self, commit=True):
        """ذخیره فرم با انتقال تاریخ‌ها و is_active به مدل"""
        instance = super().save(commit=False)
        instance.start_date = self.cleaned_data['start_date']
        instance.end_date = self.cleaned_data.get('end_date')
        instance.is_active = self.cleaned_data.get('is_active', True)

        if commit:
            instance.save()
            logger.info(f"[UserPostForm.save] اتصال کاربر '{instance.user.username}' به پست '{instance.post.name}' ذخیره شد")
        return instance

#==============================================
class PostHistoryForm(forms.ModelForm):
    # changed_at = jDateField(
    #     widget=forms.DateInput(attrs={'class': 'form-control', 'data-jdp': ''}),
    #     label='تاریخ تغییر'
    # )

    class Meta:
        model = PostHistory
        fields = ['post', 'changed_field', 'old_value', 'new_value', 'changed_by']
        widgets = {
            'post': forms.Select(attrs={'class': 'form-control'}),
            'changed_field': forms.TextInput(attrs={'class': 'form-control'}),
            'old_value': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'new_value': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'changed_by': forms.Select(attrs={'class': 'form-control'}),
        }

class StatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = [
            'name',
            'code',
            'is_initial',
            'is_final_approve',
            'is_final_reject',
            'is_active',
            'description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_initial': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_final_approve': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_final_reject': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': _('نام وضعیت'),
            'code': _('کد وضعیت'),
            'description': _('توضیحات'),
            'is_active': _('فعال باشد'),
            'is_initial': _('وضعیت اولیه'),
            'is_final_approve': _('وضعیت تأیید نهایی'),
            'is_final_reject': _('وضعیت رد نهایی'),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        instance = self.instance
        if Status.objects.exclude(pk=instance.pk if instance else None).filter(code=code).exists():
            raise forms.ValidationError(_("کدی که انتخاب کردید قبلاً استفاده شده است."))
        return code

class OrganizationTypeForm(forms.ModelForm):
    class Meta:
        model = OrganizationType
        fields = ['fname', 'org_type', 'is_budget_allocatable']
        labels = {
            'fname': _("نام اصلی/رایج نوع سازمان"),
            'org_type': _("نام جایگزین/کد نوع سازمان (اختیاری)"),
            'is_budget_allocatable': _("قابل تخصیص بودجه؟"),
        }
        help_texts = {
            'fname': _("مثلاً: مجتمع مسکونی، شعبه استانی، دفتر مرکزی."),
            'org_type': _("در صورت نیاز به یک نام یا کد دیگر برای این نوع سازمان استفاده شود."),
        }

class FontSettingsForm(forms.ModelForm):
    """فرم مدیریت فونت‌ها"""
    
    class Meta:
        model = FontSettings
        fields = [
            'name',
            'family_name', 
            'font_file',
            'font_format',
            'font_weight',
            'is_active',
            'is_default',
            'is_rtl_support',
            'description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('مثال: وزیرمتن بولد')
            }),
            'family_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('مثال: Vazirmatn')
            }),
            'font_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.ttf,.woff,.woff2,.eot,.otf'
            }),
            'font_format': forms.Select(attrs={'class': 'form-select'}),
            'font_weight': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_rtl_support': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('توضیحات اختیاری درباره فونت...')
            })
        }
        labels = {
            'name': _('نام فونت'),
            'family_name': _('نام خانواده فونت'),
            'font_file': _('فایل فونت'),
            'font_format': _('فرمت فونت'),
            'font_weight': _('وزن فونت'),
            'is_active': _('فعال'),
            'is_default': _('فونت پیش‌فرض سیستم'),
            'is_rtl_support': _('پشتیبانی از راست به چپ'),
            'description': _('توضیحات')
        }
        help_texts = {
            'family_name': _('نام CSS که در font-family استفاده می‌شود'),
            'font_file': _('فایل‌های مجاز: TTF, WOFF, WOFF2, EOT, OTF'),
            'font_format': _('فرمت فایل آپلود شده'),
            'font_weight': _('وزن فونت (ضخامت)'),
            'is_default': _('در صورت انتخاب، این فونت به عنوان فونت اصلی سیستم استفاده می‌شود'),
            'is_rtl_support': _('آیا این فونت از زبان‌های راست به چپ پشتیبانی می‌کند؟')
        }
    
    def clean_font_file(self):
        """اعتبارسنجی فایل فونت"""
        font_file = self.cleaned_data.get('font_file')
        
        if font_file:
            # بررسی حجم فایل (حداکثر 10 مگابایت)
            if font_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError(_('حجم فایل نباید بیشتر از 10 مگابایت باشد.'))
            
            # بررسی پسوند فایل
            allowed_extensions = ['.ttf', '.woff', '.woff2', '.eot', '.otf']
            file_extension = font_file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise forms.ValidationError(
                    _('فرمت فایل مجاز نیست. فرمت‌های مجاز: {}').format(', '.join(allowed_extensions))
                )
        
        return font_file
    
    def clean(self):
        """اعتبارسنجی کلی فرم"""
        cleaned_data = super().clean()
        font_format = cleaned_data.get('font_format')
        font_file = cleaned_data.get('font_file')
        
        # بررسی تطابق فرمت فایل با فرمت انتخاب شده
        if font_file and font_format:
            file_extension = font_file.name.lower().split('.')[-1]
            if file_extension != font_format:
                raise forms.ValidationError(
                    _('فرمت انتخاب شده با پسوند فایل مطابقت ندارد.')
                )
        
        return cleaned_data

