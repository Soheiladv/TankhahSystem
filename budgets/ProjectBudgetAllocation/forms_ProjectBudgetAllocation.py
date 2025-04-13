import jdatetime
from django import forms

from budgets.models import ProjectBudgetAllocation, BudgetAllocation
from core.models import Project, SubProject, Organization
from django.utils.translation import gettext_lazy as _



import logging
logger = logging.getLogger(__name__)

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
        self.user = kwargs.pop('user', None)
        self.organization_id = kwargs.pop('organization_id', None)
        # logger.debug(f"Initializing ProjectBudgetAllocationForm with user={self.user}, organization_id={self.organization_id}")
        super().__init__(*args, **kwargs)

        # محدود کردن انتخاب‌ها بر اساس سازمان
        if self.organization_id:
            organization = Organization.objects.get(id=self.organization_id)
            self.fields['budget_allocation'].queryset = BudgetAllocation.objects.filter(
                organization=organization,
                is_active=True
            )
            self.fields['project'].queryset = Project.objects.filter(
                organizations=organization,
                is_active=True
            )
            self.fields['subproject'].queryset = SubProject.objects.filter(
                project__organizations=organization,
                is_active=True
            )
        else:
            # logger.warning("No organization_id provided to form")
            self.fields['budget_allocation'].queryset = BudgetAllocation.objects.none()
            self.fields['project'].queryset = Project.objects.none()
            self.fields['subproject'].queryset = SubProject.objects.none()

        # تنظیم تاریخ اولیه
        if self.instance.pk and self.instance.allocation_date:
            j_date = jdatetime.date.fromgregorian(date=self.instance.allocation_date)
            self.initial['allocation_date'] = j_date.strftime('%Y/%m/%d')

    def clean_allocation_date(self):
        date_str = self.cleaned_data.get('allocation_date')
        logger.debug(f"Cleaning allocation_date: input={date_str}")
        if not date_str:
            logger.error("allocation_date is empty")
            raise forms.ValidationError(_('تاریخ تخصیص اجباری است.'))
        from budgets.forms import to_english_digits
        date_str = to_english_digits(date_str.strip())
        import re
        date_str = re.sub(r'[-\.]', '/', date_str)
        try:
            j_date = jdatetime.date.strptime(date_str, '%Y/%m/%d')
            g_date = j_date.togregorian()
            from datetime import date
            if not isinstance(g_date, date):
                logger.error(f"Invalid allocation_date type: {type(g_date)}")
                raise forms.ValidationError(_('فرمت تاریخ نامعتبر است.'))
            logger.debug(f"Parsed allocation_date: {g_date}")
            return g_date
        except ValueError:
            logger.error(f"Invalid allocation_date format: {date_str}")
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean(self):
        cleaned_data = super().clean()
        budget_allocation = cleaned_data.get('budget_allocation')
        project = cleaned_data.get('project')
        subproject = cleaned_data.get('subproject')
        allocated_amount = cleaned_data.get('allocated_amount')
        allocation_date = cleaned_data.get('allocation_date')

        if not budget_allocation:
            logger.error("No budget_allocation selected")
            raise forms.ValidationError(_('لطفاً یک تخصیص بودجه انتخاب کنید.'))

        if not project:
            logger.error("No project selected")
            raise forms.ValidationError(_('لطفاً یک پروژه انتخاب کنید.'))

        if subproject and subproject.project != project:
            logger.error(f"Subproject {subproject} does not belong to project {project}")
            raise forms.ValidationError(_('زیرپروژه باید متعلق به پروژه انتخاب‌شده باشد.'))

        if allocated_amount is None or allocated_amount <= 0:
            logger.error(f"Invalid allocated_amount: {allocated_amount}")
            raise forms.ValidationError(_('مبلغ تخصیص باید مثبت باشد.'))

        if budget_allocation and allocated_amount:
            remaining = budget_allocation.get_remaining_amount()
            if allocated_amount > remaining:
                logger.error(f"allocated_amount ({allocated_amount}) exceeds remaining budget ({remaining})")
                raise forms.ValidationError(_(
                    f'مبلغ تخصیص ({allocated_amount:,} ریال) بیشتر از بودجه باقی‌مانده ({remaining:,} ریال) است.'
                ))

        if allocation_date and budget_allocation:
            start_date = budget_allocation.budget_period.start_date
            end_date = budget_allocation.budget_period.end_date
            if not (start_date <= allocation_date <= end_date):
                logger.error(f"allocation_date ({allocation_date}) outside budget period")
                raise forms.ValidationError(_('تاریخ تخصیص باید در بازه دوره بودجه باشد.'))

        logger.debug("Clean method completed")
        return cleaned_data

    def save(self, commit=True):
        logger.debug("Saving ProjectBudgetAllocationForm")
        instance = super().save(commit=False)
        if self.user and self.user.is_authenticated:
            instance.created_by = self.user
        else:
            logger.error("No authenticated user provided")
            raise forms.ValidationError(_('کاربر معتبر برای ایجاد تخصیص لازم است.'))
        if commit:
            try:
                instance.save()
                logger.info(f"ProjectBudgetAllocation saved: {instance}")
            except Exception as e:
                logger.error(f"Error saving ProjectBudgetAllocation: {str(e)}")
                raise
        return instance

