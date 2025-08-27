import re
from django.db.models import Sum
from decimal import Decimal
from BudgetsSystem.utils import convert_jalali_to_gregorian, convert_gregorian_to_jalali, convert_to_farsi_numbers
from BudgetsSystem.widgets import NumberToWordsWidget
from accounts.models import TimeLockModel, CustomUser
from budgets.models import BudgetAllocation
from core.models import Project, Organization, UserPost, Post, PostHistory, WorkflowStage, SubProject, OrganizationType, \
    SystemSettings, AccessRule, Branch, PostAction
from django import forms
from .models import Project, Organization
from django.utils.translation import gettext_lazy as _
from django_jalali.forms import jDateField
from django.core.exceptions import ValidationError
from jdatetime import datetime as jdatetime
import jdatetime
from django import forms
from django.utils.translation import gettext_lazy as _
from core.models import Organization, Project, SubProject
from budgets.models import BudgetAllocation
import jdatetime
import re
import logging
logger = logging.getLogger(__name__)

from django import forms

class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = '__all__'

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
            # Use the utility function to parse
            from BudgetsSystem.utils import parse_jalali_date
            parsed_date = parse_jalali_date(str(start_date), field_name=_('تاریخ شروع'))
            logger.debug(f"Parsed start_date: {parsed_date}")
            return parsed_date  # Return the Python date object
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
            # Use the utility function to parse
            from BudgetsSystem.utils import parse_jalali_date
            parsed_date = parse_jalali_date(str(end_date), field_name=_('تاریخ خاتمه'))
            logger.debug(f"Parsed end_date: {parsed_date}")
            return parsed_date  # Return the Python date object
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
# -- new
from django import forms
from .models import Post, Branch, Organization
from core.models import AccessRule, PostAction

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['branch'].queryset = Branch.objects.filter(is_active=True)
        self.fields['parent'].queryset = Post.objects.filter(is_active=True).exclude(pk=self.instance.pk if self.instance.pk else None)
        self.fields['access_rules'] = forms.ModelMultipleChoiceField(
            queryset=AccessRule.objects.filter(is_active=True),
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            required=False,
            label=_('مراحل تأیید'),
            initial=AccessRule.objects.filter(postactions__post=self.instance, postactions__is_active=True) if self.instance.pk else None
        )

    def save(self, commit=True):
        post = super().save(commit=False)
        if commit:
            post.save(changed_by=self.instance.changed_by or self._user)
            selected_rules = self.cleaned_data.get('access_rules', [])
            current_actions = PostAction.objects.filter(post=post)
            current_rule_ids = set(current_actions.values_list('stage_id', flat=True))

            PostAction.objects.filter(
                post=post,
                stage__in=AccessRule.objects.exclude(id__in=[r.id for r in selected_rules])
            ).delete()

            for rule in selected_rules:
                if rule.id not in current_rule_ids:
                    PostAction.objects.create(
                        post=post,
                        stage=rule,
                        action_type=rule.action_type,
                        entity_type=rule.entity_type,
                        is_active=True
                    )

        return post

    def _get_user(self):
        """Helper to access user from the view."""
        return getattr(self, '_user', None)

    def __init__(self, *args, user=None, **kwargs):
        self._user = user  # Store user for use in save
        super().__init__(*args, **kwargs)

class UserPostForm_(forms.ModelForm):
    class Meta:
        model = UserPost
        fields = ['user', 'post']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'post': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # مثال: فقط کاربران فعال
        self.fields['user'].queryset = CustomUser.objects.filter(is_active=True)

# ===== CORE BUSINESS LOGIC =====
class UserPostForm(forms.ModelForm):
    """
    فرم برای ایجاد یا به‌روزرسانی اتصال کاربر به پست.
    مسئولیت: اعتبارسنجی و فیلتر کردن کاربران و پست‌های مجاز.
    """
    start_date = forms.CharField(
        label=_('تاریخ شروع فعالیت '),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('1404/01/17'),
        })
    )
    end_date = forms.CharField(
        label=_('تاریخ خاتمه فعالیت'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('1404/01/17'),
        })
    )
    class Meta:
        model = UserPost
        fields = ['user', 'post', 'is_active']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'post': forms.Select(attrs={'class': 'form-control'}),
            # 'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            # 'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    def clean_start_date(self):
        """اعتبارسنجی تاریخ جلالی"""
        date_str = self.cleaned_data.get('start_date')
        try:
            from tankhah.Factor.NF.form_Nfactor import parse_jalali_date
            return parse_jalali_date(date_str)
        except (ValueError, TypeError):
            logger.warning(f"[FactorForm.clean_date] فرمت تاریخ نامعتبر: {date_str}")
            raise forms.ValidationError(_('فرمت تاریخ نامعتبر است.'))

    def clean_end_date(self):
        """اعتبارسنجی تاریخ جلالی"""
        date_str = self.cleaned_data.get('end_date')
        try:
            from tankhah.Factor.NF.form_Nfactor import parse_jalali_date
            return parse_jalali_date(date_str)
        except (ValueError, TypeError):
            logger.warning(f"[FactorForm.clean_date] فرمت تاریخ نامعتبر: {date_str}")
            raise forms.ValidationError(_('فرمت تاریخ نامعتبر است.'))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        logger.debug(f"[UserPostForm] شروع مقداردهی اولیه برای کاربر '{self.request.user.username if self.request else 'Anonymous'}'")

        # فیلتر کاربران فعال
        self.fields['user'].queryset = CustomUser.objects.filter(is_active=True).order_by('username')
        # فیلتر پست‌های فعال در سازمان‌های مجاز
        if self.request and not self.request.user.is_superuser:
            user_orgs = {up.post.organization for up in self.request.user.userpost_set.filter(is_active=True)
                         if up.post.organization and not up.post.organization.is_core and not up.post.organization.is_holding}
            self.fields['post'].queryset = Post.objects.filter(
                is_active=True,
                organization__in=user_orgs
            ).order_by('name')
        else:
            self.fields['post'].queryset = Post.objects.filter(is_active=True).order_by('name')

        if self.instance.pk:
            logger.debug(f"[UserPostForm] ویرایش اتصال با ID: {self.instance.pk}")

    def clean(self):
        """اعتبارسنجی فرم"""
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        post = cleaned_data.get('post')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_active = cleaned_data.get('is_active')

        if user and post:
            # بررسی عدم وجود اتصال فعال مشابه
            existing = UserPost.objects.filter(
                user=user,
                post=post,
                is_active=True
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
            if existing.exists():
                logger.warning(f"[UserPostForm.clean] اتصال فعال برای کاربر '{user.username}' و پست '{post.name}' وجود دارد")
                raise ValidationError(_('این کاربر قبلاً به این پست متصل است و اتصال فعال است.'))

        if end_date and start_date and end_date < start_date:
            logger.warning(f"[UserPostForm.clean] تاریخ پایان {end_date} قبل از تاریخ شروع {start_date} است")
            raise ValidationError(_('تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.'))

        from django.utils import timezone
        if is_active and end_date and end_date < timezone.now().date():
            logger.warning(f"[UserPostForm.clean] اتصال فعال با تاریخ پایان منقضی‌شده: {end_date}")
            raise ValidationError(_('اتصال فعال نمی‌تواند تاریخ پایانی منقضی‌شده داشته باشد.'))

        logger.debug("[UserPostForm.clean] اعتبارسنجی فرم با موفقیت انجام شد")
        return cleaned_data

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
    class Meta:
        model = WorkflowStage
        fields = [
            'name',
            'order',
            'description',
            'entity_type',
            'is_active',
            'is_final_stage',
            'auto_advance',
            'triggers_payment_order'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'entity_type': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_final_stage': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_advance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'triggers_payment_order': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': _('نام مرحله'),
            'order': _('ترتیب نمایش'),
            'description': _('توضیحات'),
            'entity_type': _('نوع موجودیت'),
            'is_active': _('فعال باشد'),
            'is_final_stage': _('مرحله نهایی تأیید تنخواه است'),
            'auto_advance': _('پیش‌رفت خودکار به مرحله بعد'),
            'triggers_payment_order': _('باعث ایجاد دستور پرداخت خودکار شود'),
        }

    def clean_order(self):
        order = self.cleaned_data.get('order')
        instance = self.instance
        if WorkflowStage.objects.exclude(pk=instance.pk if instance else None).filter(order=order).exists():
            raise forms.ValidationError(_("ترتیبی که انتخاب کردید قبلاً استفاده شده است."))
        return order

    def clean_entity_type(self):
        entity_type = self.cleaned_data.get('entity_type')
        valid_choices = [choice[0] for choice in WorkflowStage.ENTITY_TYPE_CHOICES]
        if entity_type not in valid_choices:
            raise forms.ValidationError(_("نوع موجودیت انتخاب‌شده معتبر نیست."))
        return entity_type

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

