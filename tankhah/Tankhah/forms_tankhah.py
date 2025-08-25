from django import forms
from django.utils.translation import gettext_lazy as _

from BudgetsSystem.utils import parse_jalali_date
from budgets.models import BudgetAllocation
from core.models import   Project, SubProject, AccessRule
import jdatetime
from django.utils import timezone
from tankhah.models import  Tankhah
from datetime import datetime
from decimal import Decimal
from django.core.cache import cache
import logging

logger = logging.getLogger('FactorItemApprovalForm')


# ========= Tankhah Forms
class TankhahForm_(forms.ModelForm):
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

    def clean_current_stage(self):
        current_stage = self.cleaned_data.get('current_stage')
        if current_stage < 1:
            raise forms.ValidationError(_("ترتیب مرحله باید حداقل 1 باشد."))
        # بررسی هماهنگی با AccessRule.stage_order
        if not AccessRule.objects.filter(stage_order=current_stage, entity_type='TANKHAH', is_active=True).exists():
            raise forms.ValidationError(_("مرحله انتخاب‌شده معتبر نیست."))
        return current_stage

    class Meta:
        model = Tankhah
        fields = ['date', 'organization', 'project', 'subproject', 'letter_number', 'due_date', 'amount',
                  'project_budget_allocation', 'description']
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
# -------------------------------------------------
class TankhahForm(forms.ModelForm):
    date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control', 'placeholder': _('1404/01/17')})
    )
    due_date = forms.CharField(
        label=_('مهلت زمانی'),
        required=False,
        widget=forms.TextInput(attrs={'data-jdp': '', 'class': 'form-control', 'placeholder': '1404/06/20'})
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
        fields = [
            'organization', 'project', 'subproject',
            'date', 'due_date', 'amount',
            'letter_number', 'description'
        ]
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-select'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'subproject': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'letter_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if 'organization' in self.data:
            try:
                org_id = int(self.data.get('organization'))
                self.fields['project'].queryset = Project.objects.filter(
                    organizations__id=org_id, is_active=True
                ).distinct().order_by('name')
            except (ValueError, TypeError):
                self.fields['project'].queryset = Project.objects.none()
        elif self.instance.pk and self.instance.organization:
            self.fields['project'].queryset = Project.objects.filter(
                organizations=self.instance.organization, is_active=True
            ).distinct().order_by('name')
        else:
            self.fields['project'].queryset = Project.objects.none()

        if 'project' in self.data:
            try:
                project_id = int(self.data.get('project'))
                self.fields['subproject'].queryset = SubProject.objects.filter(
                    project_id=project_id, is_active=True
                ).order_by('name')
            except (ValueError, TypeError):
                self.fields['subproject'].queryset = SubProject.objects.none()
        elif self.instance.pk and self.instance.project:
            self.fields['subproject'].queryset = SubProject.objects.filter(
                project=self.instance.project, is_active=True
            ).order_by('name')
        else:
            self.fields['subproject'].queryset = SubProject.objects.none()

    def clean_date(self):
        date_str = self.cleaned_data.get('date')
        try:
            return parse_jalali_date(date_str)
        except (ValueError, TypeError):
            raise forms.ValidationError(_('فرمت تاریخ نامعتبر است.'))

    def clean_due_date(self):
        date_str = self.cleaned_data.get('due_date')
        if date_str:
            try:
                return parse_jalali_date(date_str)
            except (ValueError, TypeError):
                raise forms.ValidationError(_('فرمت تاریخ نامعتبر است.'))
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
        organization = cleaned_data.get('organization')
        subproject = cleaned_data.get('subproject')
        amount = cleaned_data.get('amount')

        if subproject and project and subproject.project != project:
            self.add_error('subproject', _('زیرپروژه انتخاب شده به این پروژه تعلق ندارد.'))

        if project and organization and amount:
            allocation = BudgetAllocation.objects.filter(
                project=project,
                organization=organization,
                subproject=subproject,
                is_active=True
            ).first()
            if not allocation:
                self.add_error('project', _('هیچ تخصیص بودجه فعالی برای این پروژه و سازمان یافت نشد.'))
            else:
                # حالا تخصیص پیدا شده، محاسبه رو انجام بده
                from budgets.budget_calculations import calculate_balance_from_transactions
                remaining = calculate_balance_from_transactions(allocation)
                logger.info(f'calculate_balance_from_transactions(allocation) {remaining} - amount {amount}')
                if amount > remaining:
                    self.add_error('amount', _('مبلغ درخواستی بیشتر از بودجه باقیمانده تخصیص است.'))

        return cleaned_data
# -------------------------------------------------

