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
                'data-placeholder': _('دوره بودجه را انتخاب کنید'),
            }),
            'organization': forms.Select(attrs={
                'class': 'form-select',
                'data-control': 'select2',
                'data-placeholder': _('سازمان/شعبه را انتخاب کنید (اختیاری)'),
            }),
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
        self.fields['organization'].required = False  # اختیاری کردن فیلد

        # محدود کردن دوره‌های بودجه به موارد فعال
        self.fields['budget_period'].queryset = BudgetPeriod.objects.filter(
            is_active=True
        ).select_related('organization')

        # محدود کردن سازمان‌ها بر اساس دسترسی کاربر
        try:
            if user and not user.is_superuser:
                user_orgs = [
                    up.post.organization
                    for up in user.userpost_set.filter(is_active=True, end_date__isnull=True)
                ]
                org_ids = [org.id for org in user_orgs if org]
                if not org_ids:
                    logger.warning(f"No organizations found for user {user.username}")
                    self.fields['organization'].queryset = Organization.objects.none()
                    self.fields['organization'].help_text = _(
                        'شما به هیچ سازمانی دسترسی ندارید. با مدیر سیستم تماس بگیرید.'
                    )
                else:
                    self.fields['organization'].queryset = Organization.objects.filter(
                        is_active=True, id__in=org_ids
                    ).select_related('org_type')
            else:
                self.fields['organization'].queryset = Organization.objects.filter(
                    is_active=True
                ).select_related('org_type')
            logger.debug(
                f"BudgetItemForm initialized with {self.fields['organization'].queryset.count()} organizations"
            )
        except Exception as e:
            logger.error(f"Error initializing BudgetItemForm organizations: {str(e)}", exc_info=True)
            self.fields['organization'].queryset = Organization.objects.none()
            self.add_error(None, _('خطایی در بارگذاری سازمان‌ها رخ داد.'))

    def clean_code(self):
        code = self.cleaned_data.get('code')
        budget_period = self.cleaned_data.get('budget_period')
        instance = self.instance
        if code and budget_period:
            if BudgetItem.objects.exclude(pk=instance.pk if instance else None).filter(
                code=code, budget_period=budget_period
            ).exists():
                raise forms.ValidationError(_('این کد برای این دوره بودجه قبلاً استفاده شده است.'))
        return code

    def clean(self):
        cleaned_data = super().clean()
        budget_period = cleaned_data.get('budget_period')
        organization = cleaned_data.get('organization')
        if budget_period and not organization:
            cleaned_data['organization'] = budget_period.organization
            logger.debug(f"Set default organization to {budget_period.organization}")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.organization and instance.budget_period:
            instance.organization = instance.budget_period.organization
            logger.debug(f"Saved BudgetItem with default organization {instance.organization}")
        if commit:
            instance.save()
        return instance