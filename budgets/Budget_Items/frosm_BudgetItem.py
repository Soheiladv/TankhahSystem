import logging
from django import forms
from django.utils.translation import gettext_lazy as _

from budgets.models import BudgetItem, BudgetPeriod
from core.models import Organization

logger = logging.getLogger(__name__)

class BudgetItemForm(forms.ModelForm):
    class Meta:
        model = BudgetItem
        fields = ['budget_period', 'organization', 'name', 'code', 'is_active']
        widgets = {
            'budget_period': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required',
                'data-control': 'select2',
            }),
            'organization': forms.Select(attrs={
                'class': 'form-select',
                'data-control': 'select2',
            }),  # حذف required
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                'placeholder': _('نام ردیف بودجه'),
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                'placeholder': _('کد ردیف بودجه'),
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
            }),
        }
        labels = {
            'budget_period': _('دوره بودجه'),
            'organization': _('سازمان/شعبه (اختیاری)'),
            'name': _('نام ردیف بودجه'),
            'code': _('کد ردیف بودجه'),
            'is_active': _('فعال'),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # اختیاری کردن فیلد organization
        self.fields['organization'].required = False
        # محدود کردن گزینه‌ها به دوره‌های بودجه فعال
        self.fields['budget_period'].queryset = BudgetPeriod.objects.filter(is_active=True).select_related('organization')
        # اگر کاربر لاگین کرده، سازمان‌ها رو به سازمان‌های مجازش محدود کن
        if user:
            user_orgs = [up.post.organization for up in user.userpost_set.filter(is_active=True, end_date__isnull=True)]
            self.fields['organization'].queryset = Organization.objects.filter(
                is_active=True, id__in=[org.id for org in user_orgs]
            ).select_related('org_type')
        else:
            self.fields['organization'].queryset = Organization.objects.filter(is_active=True).select_related('org_type')
        logger.debug("Initialized BudgetItemForm")

    def clean_code(self):
        code = self.cleaned_data.get('code')
        budget_period = self.cleaned_data.get('budget_period')
        instance = self.instance
        if BudgetItem.objects.exclude(pk=instance.pk if instance else None).filter(
            code=code, budget_period=budget_period
        ).exists():
            raise forms.ValidationError(_('این کد برای این دوره بودجه قبلاً استفاده شده است.'))
        return code

    def clean(self):
        cleaned_data = super().clean()
        budget_period = cleaned_data.get('budget_period')
        organization = cleaned_data.get('organization')
        # اگر organization خالیه، بعداً در save مقدار پیش‌فرض می‌ذاریم
        if not organization and budget_period:
            # می‌تونیم organization رو به budget_period.organization تنظیم کنیم
            cleaned_data['organization'] = budget_period.organization
        # حذف اعتبارسنجی تطبیق سازمان و دوره بودجه
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # اگر organization خالیه، از budget_period.organization استفاده کن
        if not instance.organization and instance.budget_period:
            instance.organization = instance.budget_period.organization
        if commit:
            instance.save()
        return instance