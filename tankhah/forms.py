import logging
import os
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _
from budgets.budget_calculations import get_subproject_remaining_budget, get_project_remaining_budget, \
    get_tankhah_remaining_budget, get_project_total_budget
from budgets.models import BudgetTransaction, BudgetAllocation
from core.models import Organization, Project , SubProject
from .utils import restrict_to_user_organization
import jdatetime
from django.utils import timezone
from Tanbakhsystem.utils import convert_to_farsi_numbers, to_english_digits
from Tanbakhsystem.base import JalaliDateForm
from tankhah.models import Factor, FactorItem, Tankhah  # وارد کردن مدل‌ها
from .models import ItemCategory
from datetime import datetime
from decimal import Decimal
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class FactorItemApprovalForm(forms.ModelForm):
    class Meta:
        model = FactorItem
        fields = ['status', 'description']

    status = forms.ChoiceField(
        choices=[
            ('', 'انتخاب کنید'),
            ('PENDING', _('در حال بررسی')),
            ('APPROVED', _('تأیید شده')),
            ('REJECTED', _('رد شده')),
        ],
        widget=forms.Select(attrs={'class': 'form-control form-select', 'style': 'max-width: 200px;'}),
        label=_("اقدام"),
        required=False,
        initial='PENDING'
    )

    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': _('توضیحات خود را اینجا وارد کنید...'),
            'style': 'max-width: 500px;'
        }),
        required=False,
        label=_("توضیحات")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.status:
            self.fields['status'].initial = self.instance.status

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        if status and status != 'NONE':
            cleaned_data['status'] = status
        return cleaned_data

class FactorApprovalForm(forms.ModelForm):
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label=_("توضیحات کلی")
    )

    class Meta:
        model = Factor  # استفاده از کلاس مدل واقعی
        fields = ['comment']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for item in self.instance.items.all():
            self.fields[f'action_{item.id}'] = forms.ChoiceField(
                choices=[
                    ('', _('-------')),
                    ('APPROVED', _('تأیید')),
                    ('REJECTED', _('رد')),
                ],
                label=f"وضعیت ردیف: {item.description}",
                widget=forms.Select(attrs={'class': 'form-control'}),
                required=False
            )
            self.fields[f'comment_{item.id}'] = forms.CharField(
                label=f"توضیحات برای {item.description}",
                widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
                required=False
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            for item in self.instance.items.all():
                action_field = f'action_{item.id}'
                comment_field = f'comment_{item.id}'
                if action_field in self.cleaned_data and self.cleaned_data[action_field]:
                    item.status = self.cleaned_data[action_field]
                    item.comment = self.cleaned_data[comment_field]
                    item.save()
        return instance
#===
class JalaliDateFormConvert(forms.ModelForm):
    def set_jalali_initial(self, field_name, instance_field):
        if self.instance and getattr(self.instance, instance_field):
            jalali_date = jdatetime.date.fromgregorian(date=getattr(self.instance, instance_field))
            self.initial[field_name] = jalali_date.strftime('%Y/%m/%d')
            logger.info(f"Set initial {field_name} to: {self.initial[field_name]}")
        else:
            self.initial[field_name] = ''

    def clean_jalali_date(self, field_name):
        date_str = self.cleaned_data.get(field_name)
        logger.info(f"Raw {field_name}: {date_str}")
        if date_str:
            try:
                j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d').date()
                g_date = j_date.togregorian()
                logger.info(f"Converted {field_name} to: {g_date}")
                return g_date
            except ValueError as e:
                logger.error(f"Error parsing {field_name}: {e}")
                raise forms.ValidationError(_("تاریخ را به فرمت درست وارد کنید (مثل 1404/01/17)"))
        return None
#========= Tankhah Forms
class TankhahForm(forms.ModelForm):
    date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('1404/01/17'),
        })
    )
    due_date = forms.CharField(
        label=_('مهلت زمانی'),
        required=False,
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('1404/01/17'),
        })
    )
    amount = forms.DecimalField(
        label=_('مبلغ'),
        required=True,
        min_value=Decimal('0.01'),
        decimal_places=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '1'})
    )

    class Meta:
        model = Tankhah
        fields = ['date', 'organization', 'project', 'subproject', 'letter_number', 'due_date', 'amount','project_budget_allocation' ,'description']
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-control'}),
            'subproject': forms.Select(attrs={'class': 'form-control'}),
            'letter_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('اختیاری')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'date': _('تاریخ'),
            'organization': _('سازمان'),
            'project': _('پروژه'),
            'subproject': _('زیرپروژه'),
            'letter_number': _('شماره نامه'),
            'due_date': _('مهلت زمانی'),
            'amount': _('مبلغ'),
            'description': _('توضیحات'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # # محدود کردن سازمان‌ها به سازمان‌های کاربر
        # if self.user:
        #     self.fields['organization'].queryset = Organization.objects.filter(
        #         id__in=self.user.organizations.values_list('id', flat=True),
        #         org_type__is_budget_allocatable=True,
        #         is_active=True
        #     ).order_by('name')
        # else:
        #     self.fields['organization'].queryset = Organization.objects.filter(
        #         org_type__is_budget_allocatable=True,
        #         is_active=True
        #     ).order_by('name')

        # تنظیم پروژه‌ها
        org_id = None
        if 'organization' in self.data:
            try:
                org_id = int(self.data.get('organization'))
                self.fields['project'].queryset = Project.objects.filter(
                    organizations__id=org_id,
                    is_active=True
                ).distinct().order_by('name')
            except (ValueError, TypeError):
                logger.debug(f"Invalid organization ID: {self.data.get('organization')}")
                self.fields['project'].queryset = Project.objects.none()
        elif self.instance.pk and self.instance.organization:
            org_id = self.instance.organization.id
            self.fields['project'].queryset = Project.objects.filter(
                organizations=self.instance.organization,
                is_active=True
            ).distinct().order_by('name')
        else:
            self.fields['project'].queryset = Project.objects.none()

        # تنظیم زیرپروژه‌ها
        project_id = None
        if 'project' in self.data:
            try:
                project_id = int(self.data.get('project'))
            except (ValueError, TypeError):
                logger.debug(f"Invalid project ID: {self.data.get('project')}")
        elif self.instance.pk and self.instance.project:
            project_id = self.instance.project.id

        self.fields['subproject'].queryset = SubProject.objects.filter(
            project_id=project_id,
            is_active=True
        ).order_by('name') if project_id else SubProject.objects.none()

        # تنظیم مقادیر اولیه تاریخ جلالی
        if self.instance.pk:
            if self.instance.date:
                jalali_date = jdatetime.datetime.fromgregorian(datetime=self.instance.date).strftime('%Y/%m/%d')
                self.fields['date'].initial = jalali_date
            if self.instance.due_date:
                jalali_due_date = jdatetime.datetime.fromgregorian(datetime=self.instance.due_date).strftime('%Y/%m/%d')
                self.fields['due_date'].initial = jalali_due_date
        else:
            today_jalali = jdatetime.date.today().strftime('%Y/%m/%d')
            self.fields['date'].initial = today_jalali

        # غیرفعال کردن فیلدها در صورت عدم پرمیشن
        if self.instance.pk and self.user and not self.user.has_perm('tankhah.change_tankhah'):
            for field_name in self.fields:
                if field_name not in ['amount', 'description']:
                    self.fields[field_name].disabled = True

    def clean_date(self):
        date_str = self.cleaned_data.get('date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ تنخواه اجباری است.'))
        try:
            year, month, day = map(int, date_str.split('/'))
            jalali_date = jdatetime.date(year, month, day)
            gregorian_date = jalali_date.togregorian()
            if gregorian_date > timezone.now().date():
                raise forms.ValidationError(_('تاریخ نمی‌تواند در آینده باشد.'))
            dt = datetime.combine(gregorian_date, datetime.min.time())
            return timezone.make_aware(dt)
        except (ValueError, TypeError):
            raise forms.ValidationError(_('فرمت تاریخ نامعتبر است (مثال: 1404/03/14).'))

    def clean_due_date(self):
        date_str = self.cleaned_data.get('due_date')
        if date_str:
            try:
                year, month, day = map(int, date_str.split('/'))
                jalali_date = jdatetime.date(year, month, day)
                gregorian_date = jalali_date.togregorian()
                if gregorian_date < timezone.now().date():
                    raise forms.ValidationError(_('مهلت زمانی نمی‌تواند در گذشته باشد.'))
                dt = datetime.combine(gregorian_date, datetime.min.time())
                return timezone.make_aware(dt)
            except (ValueError, TypeError):
                raise forms.ValidationError(_('فرمت تاریخ نامعتبر است (مثال: 1404/03/14).'))
        return None

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError(_('مبلغ اجباری است.'))
        if amount <= 0:
            raise forms.ValidationError(_('مبلغ باید مثبت باشد.'))
        return amount

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get('project')
        subproject = cleaned_data.get('subproject')
        organization = cleaned_data.get('organization')
        amount = cleaned_data.get('amount')

        if not project:
            self.add_error('project', _('پروژه اجباری است.'))
        if not organization:
            self.add_error('organization', _('سازمان اجباری است.'))
        if self.errors:
            return cleaned_data

        if not project.organizations.filter(id=organization.id).exists():
            self.add_error('project', _('پروژه به سازمان انتخاب‌شده تعلق ندارد.'))
            return cleaned_data

        if subproject and subproject.project != project:
            self.add_error('subproject', _('زیرپروژه باید متعلق به پروژه انتخاب‌شده باشد.'))
            return cleaned_data

        # پیدا کردن تخصیص بودجه
        if project and organization:
            allocation_query = BudgetAllocation.objects.filter(
                project=project,
                organization=organization,
                is_active=True,
                subproject=subproject if subproject else None
            )
            allocation = allocation_query.first()

            if not allocation:
                self.add_error(None, _(
                    f'تخصیص بودجه فعالی برای پروژه "{project.name}" و سازمان "{organization.name}" یافت نشد.'
                ))
                return cleaned_data

            # اعتبارسنجی اضافی برای تخصیص
            if allocation.project != project:
                self.add_error(None, _('تخصیص بودجه با پروژه انتخاب‌شده سازگار نیست.'))
                return cleaned_data
            if allocation.organization != organization:
                self.add_error(None, _('تخصیص بودجه با سازمان انتخاب‌شده سازگار نیست.'))
                return cleaned_data
            if subproject and allocation.subproject != subproject:
                self.add_error(None, _('تخصیص بودجه با زیرپروژه انتخاب‌شده سازگار نیست.'))
                return cleaned_data
            if not subproject and allocation.subproject:
                self.add_error(None, _('تخصیص بودجه باید بدون زیرپروژه باشد.'))
                return cleaned_data

            # ذخیره تخصیص برای ویو
            cleaned_data['project_budget_allocation'] = allocation

            # چک بودجه باقی‌مانده
            cache_keys = [
                f"project_remaining_budget_{project.pk}_no_filters",
                f"project_total_budget_{project.pk}_no_filters",
            ]
            for key in cache_keys:
                cache.delete(key)
                logger.debug(f"Cache cleared for {key}")

            if self.instance.pk:
                allocation._current_tankhah_pk = self.instance.pk
            remaining_budget = allocation.get_remaining_amount()
            if hasattr(allocation, '_current_tankhah_pk'):
                del allocation._current_tankhah_pk

            if remaining_budget is None or remaining_budget <= 0:
                self.add_error('amount', _('هیچ بودجه‌ای باقی نمانده است.'))
            elif amount > remaining_budget:
                self.add_error('amount', _(
                    f"مبلغ ({amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) است."
                ))

        return cleaned_data
#=========
class TanbakhApprovalForm(forms.ModelForm):
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False,
        label=_("توضیحات")
    )

    class Meta:
        model = Tankhah
        fields = []

class ApprovalForm(forms.ModelForm):
    action = forms.ChoiceField(choices=[
        ('APPROVE', 'تأیید'),
        ('REJECT', 'رد'),
        ('RETURN', 'بازگشت'),
        ('CANCEL', 'لغو')
    ])

    class Meta:
        from tankhah.models import ApprovalLog
        model = ApprovalLog
        fields = ['action', 'comment', 'tankhah', 'factor', 'factor_item']
        widgets = {
            'tankhah': forms.Select(attrs={'class': 'form-control'}),
            'factor': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('توضیحات اختیاری')}),
            'action': forms.Select(attrs={'class': 'form-control'}),
            'factor_item': forms.HiddenInput(),
        }
        labels = {
            'tankhah': _('تنخواه'),
            'factor': _('فاکتور'),
            'comment': _('توضیحات'),
            'action': _('شاخه'),
        }

class TankhahStatusForm(forms.ModelForm):
    class Meta:
        model = Tankhah
        fields = ['status', 'current_stage', 'due_date', 'approved_by']
        widgets = {
            'status': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'current_stage': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'approved_by': forms.SelectMultiple(attrs={'class': 'form-control', 'disabled': 'disabled'}),
        }
        labels = {
            'status': _('وضعیت'),
            'current_stage': _('مرحله فعلی'),
            'due_date': _('مهلت زمانی'),
            'approved_by': _('تأییدکنندگان'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.disabled = True

class FactorStatusForm(forms.ModelForm):
    class Meta:
        model = Factor
        fields = ['status']
        widgets = {
            'status': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }
        labels = {
            'status': _('وضعیت'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].disabled = True

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'multiple': True, 'class': 'form-control'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data if d is not None]
        else:
            result = single_file_clean(data, initial)
        return result

ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png']
ALLOWED_EXTENSIONS_STR = ", ".join(ALLOWED_EXTENSIONS)

class FactorDocumentForm(forms.Form):
    files = MultipleFileField(
        label=_("بارگذاری اسناد فاکتور (فقط {} مجاز است)".format(ALLOWED_EXTENSIONS_STR)),
        required=False,
        widget=MultipleFileInput(
            attrs={
                'multiple': True,
                'class': 'form-control form-control-sm',
                'accept': ",".join(ALLOWED_EXTENSIONS)
            }
        )
    )

    def clean_files(self):
        files = self.cleaned_data.get('files')
        if files:
            invalid_files = []
            for uploaded_file in files:
                if uploaded_file:
                    ext = os.path.splitext(uploaded_file.name)[1].lower()
                    if ext not in ALLOWED_EXTENSIONS:
                        invalid_files.append(uploaded_file.name)
                        logger.warning(f"Invalid file type uploaded for FactorDocument: {uploaded_file.name} (type: {ext})")

            if invalid_files:
                invalid_files_str = ", ".join(invalid_files)
                error_msg = _("فایل(های) زیر دارای فرمت غیرمجاز هستند: {files}. فرمت‌های مجاز: {allowed}").format(
                    files=invalid_files_str,
                    allowed=ALLOWED_EXTENSIONS_STR
                )
                raise ValidationError(error_msg)
        return files

class TankhahDocumentForm(forms.Form):
    documents = MultipleFileField(
        label=_("بارگذاری مدارک تنخواه (فقط {} مجاز است)".format(ALLOWED_EXTENSIONS_STR)),
        required=False,
        widget=MultipleFileInput(
            attrs={
                'multiple': True,
                'class': 'form-control form-control-sm',
                'accept': ",".join(ALLOWED_EXTENSIONS)
            }
        )
    )

    def clean_documents(self):
        files = self.cleaned_data.get('documents')
        if files:
            invalid_files = []
            for uploaded_file in files:
                if uploaded_file:
                    ext = os.path.splitext(uploaded_file.name)[1].lower()
                    if ext not in ALLOWED_EXTENSIONS:
                        invalid_files.append(uploaded_file.name)
                        logger.warning(f"Invalid file type uploaded for TankhahDocument: {uploaded_file.name} (type: {ext})")

            if invalid_files:
                invalid_files_str = ", ".join(invalid_files)
                error_msg = _("فایل(های) زیر دارای فرمت غیرمجاز هستند: {files}. فرمت‌های مجاز: {allowed}").format(
                    files=invalid_files_str,
                    allowed=ALLOWED_EXTENSIONS_STR
                )
                raise ValidationError(error_msg)
        return files

def get_factor_item_formset():
    from django.forms import inlineformset_factory
    from tankhah.Factor.forms_Factor import FactorItemForm
    return inlineformset_factory(
        Factor, FactorItem, form=FactorItemForm,
        fields=['description', 'amount', 'quantity'],
        # extra=1, can_delete=True, min_num=1, validate_min=True, max_num=100
        extra=1, can_delete=True, min_num=1, validate_min=True, max_num=100
    )

#---
class ItemCategoryForm(forms.ModelForm):
    class Meta:
        model = ItemCategory
        fields = ['name', 'min_stage_order']
        # اضافه کردن کلاس‌های Bootstrap برای فیلدها
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام دسته‌بندی'}),
            'min_stage_order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'عدد ترتیب'}),
        }
        labels = {
            'name': 'نام دسته‌بندی',
            'min_stage_order': 'حداقل ترتیب مرحله',
            'description': 'توضیحات',
        }
# class ItemCategoryForm(forms.ModelForm):
#     class Meta:
#         model = ItemCategory
#         fields = ['name', 'min_stage_order', 'description']
#         widgets = {
#             'description': forms.Textarea(attrs={'rows': 3}),
#         }
#         labels = {
#             'name': 'نام دسته‌بندی',
#             'min_stage_order': 'حداقل ترتیب مرحله',
#             'description': 'توضیحات',
#         }
