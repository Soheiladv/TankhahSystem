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
from core.models import Organization, Project, SubProject, AccessRule
from .utils import restrict_to_user_organization
import jdatetime
from django.utils import timezone
from BudgetsSystem.utils import convert_to_farsi_numbers, to_english_digits
from BudgetsSystem.base import JalaliDateForm
from tankhah.models import Factor, FactorItem, Tankhah  # وارد کردن مدل‌ها
from .models import ItemCategory
from datetime import datetime
from decimal import Decimal
from django.core.cache import cache
import logging

logger = logging.getLogger('FactorItemApprovalForm')
from tankhah.constants import ACTION_TYPES


# ===
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




# =========
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
        fields = ['status', 'due_date', 'approved_by']  # 'current_stage',
        widgets = {
            'status': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            # 'current_stage': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
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
                        logger.warning(
                            f"Invalid file type uploaded for FactorDocument: {uploaded_file.name} (type: {ext})")

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
                        logger.warning(
                            f"Invalid file type uploaded for TankhahDocument: {uploaded_file.name} (type: {ext})")

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


# ---
class ItemCategoryForm(forms.ModelForm):
    class Meta:
        model = ItemCategory
        fields = ['name', 'min_stage_order','description']
        # اضافه کردن کلاس‌های Bootstrap برای فیلدها
        # widgets = {
        #     'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام دسته‌بندی'}),
        #     'min_stage_order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'عدد ترتیب'}),
        # }
        labels = {
            'name': 'نام دسته‌بندی',
            'min_stage_order': 'حداقل ترتیب مرحله',
            'description': 'توضیحات',
        }

