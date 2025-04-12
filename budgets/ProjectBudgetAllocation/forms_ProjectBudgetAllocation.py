from django import forms

from budgets import BudgetAllocation
from budgets.models import ProjectBudgetAllocation
from core.models import Project,SubProject
from django.utils.translation import gettext_lazy as _


class ProjectBudgetAllocationForm(forms.ModelForm):
    class Meta:
        model = ProjectBudgetAllocation
        fields = ['budget_allocation', 'project', 'subproject', 'allocated_amount', 'description']
        widgets = {
            'budget_allocation': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': _('انتخاب تخصیص بودجه شعبه'),
            }),
            'project': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': _('انتخاب پروژه'),
            }),
            'subproject': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': _('انتخاب زیرپروژه (اختیاری)'),
            }),
            'allocated_amount': forms.NumberInput(attrs={
                'class': 'form-control numeric-input',
                'placeholder': _('مبلغ به ریال'),
                'dir': 'ltr',
                'min': '0',
                'step': '1000',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('توضیحات مربوط به تخصیص بودجه'),
            }),
        }
        labels = {
            'budget_allocation': _('تخصیص بودجه شعبه'),
            'project': _('پروژه'),
            'subproject': _('زیرپروژه (اختیاری)'),
            'allocated_amount': _('مبلغ تخصیص (ریال)'),
            'description': _('توضیحات'),
        }
        help_texts = {
            'allocated_amount': _('مبلغ باید کمتر از باقی‌مانده بودجه دوره باشد'),
            'subproject': _('در صورتی که بودجه به زیرپروژه خاصی تعلق دارد انتخاب کنید'),
        }


    def __init__(self, *args, organization_id=None, **kwargs):
        super().__init__(*args, **kwargs)

        if organization_id:
            self.fields['budget_allocation'].queryset = BudgetAllocation.objects.filter(
                budget_period__organization_id=organization_id,
                budget_period__is_active=True
            ).select_related('budget_period')

            self.fields['project'].queryset = Project.objects.filter(
                organizations__id=organization_id,
                is_active=True
            ).only('id', 'name')

            self.fields['subproject'].queryset = SubProject.objects.filter(
                project__organizations__id=organization_id,
                is_active=True
            ).select_related('project').only('id', 'name', 'project')
            self.fields['subproject'].required = False

        # بهینه‌سازی: اضافه کردن کلاس‌ها و ویژگی‌ها فقط اگه لازم باشه
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
            if field.required:
                field.widget.attrs['required'] = 'required'

    def clean(self):
        cleaned_data = super().clean()
        budget_allocation = cleaned_data.get('budget_allocation')
        allocated_amount = cleaned_data.get('allocated_amount')

        if budget_allocation and allocated_amount:
            budget_period = budget_allocation.budget_period
            remaining = budget_period.get_remaining_amount()
            locked_amount = budget_period.get_locked_amount()

            if allocated_amount > remaining:
                self.add_error('allocated_amount',
                               _("مبلغ تخصیص بیشتر از بودجه باقی‌مانده است: %(remaining)s") % {'remaining': remaining})
            if remaining - allocated_amount < locked_amount:
                self.add_error('allocated_amount',
                               _("نقض مقدار قفل‌شده بودجه: %(locked)s") % {'locked': locked_amount})

        return cleaned_data
