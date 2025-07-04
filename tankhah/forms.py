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
class TankhahFormKKK(JalaliDateFormConvert):
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
    budget_allocation = forms.ModelChoiceField(
        queryset=BudgetAllocation.objects.all(),
        required=False,
        label=_('تخصیص بودجه'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    amount = forms.DecimalField(
        label=_('مبلغ'),
        required=True,
        min_value=Decimal('0.01'),
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'})
    )

    class Meta:
        model = Tankhah
        fields = ['date', 'organization', 'project', 'subproject', 'budget_allocation', 'letter_number',
                  'due_date', 'amount', 'description']
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
            'budget_allocation': _('تخصیص بودجه'),
            'letter_number': _('شماره نامه'),
            'due_date': _('مهلت زمانی'),
            'amount': _('مبلغ'),
            'description': _('توضیحات'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        from core.models import SubProject,Organization,Project

        if self.user:
            # تنظیم سازمان‌ها
            self.fields['organization'].queryset = Organization.objects.filter(
                org_type__is_budget_allocatable=True,
                is_active=True
            ).select_related('org_type').order_by('name')

            # تنظیم پروژه‌ها بر اساس سازمان انتخاب‌شده
            if 'organization' in self.data:
                try:
                    org_id = int(self.data.get('organization'))
                    logger.debug(f"Filtering projects for organization: {org_id}")
                    self.fields['project'].queryset = Project.objects.filter(
                        organizations__id=org_id,
                        is_active=True
                    ).distinct().order_by('name')
                except (ValueError, TypeError) as e:
                    logger.error(f"Error filtering projects: {str(e)}")
                    self.fields['project'].queryset = Project.objects.none()
            elif self.instance.pk and self.instance.organization:
                self.fields['project'].queryset = Project.objects.filter(
                    organizations=self.instance.organization,
                    is_active=True
                ).distinct().order_by('name')
            else:
                self.fields['project'].queryset = Project.objects.none()

            # تنظیم زیرپروژه‌ها و تخصیص بودجه
            if 'project' in self.data:
                try:
                    project_id = int(self.data.get('project'))
                    org_id = int(self.data.get('organization')) if 'organization' in self.data else None
                    subproject_id = int(self.data.get('subproject')) if 'subproject' in self.data else None

                    # زیرپروژه‌ها
                    self.fields['subproject'].queryset = SubProject.objects.filter(
                        project_id=project_id,
                        is_active=True
                    ).order_by('name')

                    # تخصیص بودجه
                    query = BudgetAllocation.objects.filter(
                        project_id=project_id,
                        is_active=True
                    )
                    if org_id:
                        query = query.filter(organization_id=org_id)
                    if subproject_id:
                        query = query.filter(subproject_id=subproject_id)
                    else:
                        query = query.filter(subproject__isnull=True)
                    self.fields['budget_allocation'].queryset = query.order_by('-allocation_date')
                except (ValueError, TypeError) as e:
                    logger.error(f"Error filtering subprojects or allocations: {str(e)}")
                    self.fields['subproject'].queryset = SubProject.objects.none()
                    self.fields['budget_allocation'].queryset = BudgetAllocation.objects.none()
            elif self.instance.pk and self.instance.project:
                self.fields['subproject'].queryset = SubProject.objects.filter(
                    project=self.instance.project,
                    is_active=True
                ).order_by('name')
                self.fields['budget_allocation'].queryset = BudgetAllocation.objects.filter(
                    project=self.instance.project,
                    organization=self.instance.organization,
                    is_active=True,
                    subproject=self.instance.subproject if self.instance.subproject else None
                ).order_by('-allocation_date')
            else:
                self.fields['subproject'].queryset = SubProject.objects.none()
                self.fields['budget_allocation'].queryset = BudgetAllocation.objects.none()

            # بررسی پرمیشن برای غیرفعال کردن فیلدها
            if self.instance.pk and not self.user.has_perm('tankhah.Tankhah_update'):
                for field_name in self.fields:
                    if field_name not in ['status', 'description']:
                        self.fields[field_name].disabled = True

        self.set_jalali_initial('date', 'date')
        self.set_jalali_initial('due_date', 'due_date')

    def clean_date(self):
        date = self.clean_jalali_date('date')
        if not date:
            raise forms.ValidationError(_('تاریخ تنخواه اجباری است.'))
        dt = datetime.combine(date, datetime.min.time())
        aware_dt = timezone.make_aware(dt)
        logger.debug(f"تاریخ پاک‌شده: {aware_dt}, آگاه از منطقه زمانی: {timezone.is_aware(aware_dt)}")
        return aware_dt

    def clean_due_date(self):
        date = self.clean_jalali_date('due_date')
        if date:
            dt = datetime.combine(date, datetime.min.time())
            aware_dt = timezone.make_aware(dt)
            logger.debug(f"مهلت پاک‌شده: {aware_dt}, آگاه از منطقه زمانی: {timezone.is_aware(aware_dt)}")
            return dt
        return None

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if not amount:
            raise forms.ValidationError("amount is required")
        if amount <= 0:
            raise forms.ValidationError("Amount must be positive")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get('project')
        subproject = cleaned_data.get('subproject')
        amount = cleaned_data.get('amount')
        organization = cleaned_data.get('organization')
        budget_allocation = cleaned_data.get('budget_allocation')

        from core.models import  Project
        if project:
            try:
                project = Project.objects.get(id=project.id)
                logger.debug(f"پروژه بارگذاری شد: {project.id} - {project}")
            except Project.DoesNotExist:
                self.add_error('project', _("پروژه یافت نشد یا معتبر نیست."))
                return cleaned_data

        if not project:
            self.add_error('project', _("پروژه اجباری است."))
            return cleaned_data

        if organization and not project.organizations.filter(id=organization.id).exists():
            self.add_error('project', _("پروژه انتخاب‌شده به سازمان شما تعلق ندارد."))
            return cleaned_data

        if subproject and subproject.project != project:
            self.add_error('subproject', _("زیرپروژه باید متعلق به پروژه انتخاب‌شده باشد."))
            return cleaned_data

        if budget_allocation:
            if budget_allocation.project != project:
                self.add_error('budget_allocation', _("تخصیص بودجه باید متعلق به پروژه انتخاب‌شده باشد."))
            if subproject and budget_allocation.subproject != subproject:
                self.add_error('budget_allocation', _("تخصیص بودجه باید متعلق به زیرپروژه انتخاب‌شده باشد."))
            if not subproject and budget_allocation.subproject:
                self.add_error('budget_allocation', _("تخصیص بودجه باید بدون زیرپروژه باشد."))
            if budget_allocation.organization != organization:
                self.add_error('budget_allocation', _("تخصیص بودجه باید متعلق به سازمان انتخاب‌شده باشد."))

        if project and amount:
            # پاک کردن کش
            cache_keys = [
                f"project_remaining_budget_{project.pk}_no_filters",
                f"project_total_budget_{project.pk}_no_filters",
            ]
            for key in cache_keys:
                try:
                    cache.delete(key)
                    logger.debug(f"کش پاک شد برای {key}")
                except Exception as e:
                    logger.warning(f"خطا در پاک کردن کش برای {key}: {str(e)}")

            # انتخاب تخصیص بودجه
            allocation = budget_allocation
            if not allocation and project:
                allocation = BudgetAllocation.objects.filter(
                    project=project,
                    organization=organization,
                    subproject__isnull=True,
                    is_active=True
                ).first()
            if not allocation and subproject:
                allocation = BudgetAllocation.objects.filter(
                    project=project,
                    organization=organization,
                    subproject=subproject,
                    is_active=True
                ).first()

            # محاسبه بودجه باقی‌مانده
            if subproject:
                remaining_budget = get_subproject_remaining_budget(subproject, force_refresh=True)
                budget_type = "زیرپروژه"
            elif allocation:
                remaining_budget = allocation.get_remaining_amount()
                budget_type = "تخصیص بودجه پروژه"
            else:
                remaining_budget = get_project_remaining_budget(project, force_refresh=True)
                budget_type = "پروژه"

            total_budget = get_project_total_budget(project, force_refresh=True)
            logger.debug(
                f"اعتبارسنجی بودجه {budget_type} برای پروژه {project.id}: "
                f"کل={total_budget}، باقی‌مانده={remaining_budget}، درخواست‌شده={amount}"
            )

            if not allocation and not subproject:
                logger.error(f"هیچ تخصیص بودجه فعالی برای پروژه {project.id} یافت نشد")
                self.add_error('project', _("هیچ تخصیص بودجه فعالی برای این پروژه یافت نشد."))
                return cleaned_data

            if remaining_budget is None or remaining_budget <= 0:
                self.add_error('amount', _(
                    f"هیچ بودجه‌ای برای {budget_type} باقی نمانده است."
                ))
            elif amount > remaining_budget:
                self.add_error('amount', _(
                    f"مبلغ واردشده ({amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) است."
                ))

        return cleaned_data

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

class old__FactorForm(forms.ModelForm):
    date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        })
    )

    class Meta:
        model = Factor
        fields = ['tankhah', 'date', 'amount', 'description']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'tankhah': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 1, 'placeholder': _('توضیحات فاکتور')}),
        }
        labels = {
            'tankhah': _('تنخواه'),
            'date': _('تاریخ'),
            'amount': _('مبلغ'),
            'description': _('توضیحات'),
        }

    def __init__(self, *args, **kwargs):
        from core.models import WorkflowStage, Project, SubProject
        self.user = kwargs.pop('user', None)
        self.tankhah = kwargs.pop('tankhah', None)
        super().__init__(*args, **kwargs)
        initial_stage_order = WorkflowStage.objects.order_by('order').first().order if WorkflowStage.objects.exists() else None

        if self.user:
            user_orgs = restrict_to_user_organization(self.user)
            if user_orgs is None:
                self.fields['tankhah'].queryset = Tankhah.objects.filter(
                    status__in=['DRAFT', 'PENDING'],
                    current_stage__order=initial_stage_order
                ).select_related('project', 'subproject')
                self.fields['tankhah'].required = True # فیلد تنخواه اجباری
            else:
                projects = Project.objects.filter(organizations__in=user_orgs)
                subprojects = SubProject.objects.filter(project__in=projects)
                from django.db.models import Q
                queryset = Tankhah.objects.filter(
                    status__in=['DRAFT', 'PENDING'],
                    current_stage__order=initial_stage_order
                ).filter(
                    Q(organization__in=user_orgs) |
                    Q(project__in=projects) |
                    Q(subproject__in=subprojects)
                ).distinct()
                self.fields['tankhah'].queryset = queryset
                logger.info(f"Tankhah queryset: {list(queryset.values('number', 'project__name', 'subproject__name'))}")

        if self.instance.pk:
            self.fields['tankhah'].queryset = Tankhah.objects.filter(id=self.instance.tankhah.id).select_related(
                'project')
            self.fields['tankhah'].initial = self.instance.tankhah
            if self.instance.date:
                j_date = jdatetime.date.fromgregorian(date=self.instance.date)
                jalali_date_str = j_date.strftime('%Y/%m/%d')
                self.fields['date'].initial = jalali_date_str
                self.initial['date'] = jalali_date_str

            amount = self.instance.amount
            if amount is not None:
                self.initial['amount'] = str(int(round(Decimal(amount))))
                logger.info(f'Initial amount set for widget: {self.initial["amount"]}')

        elif self.tankhah:
            self.fields['tankhah'].initial = self.tankhah

        if self.instance.pk and self.user and not self.user.has_perm('tankhah.Factor_full_edit'):
            for field_name in self.fields:
                self.fields[field_name].disabled = True

    def clean_date(self):
        date_str = self.cleaned_data.get('date')
        if not date_str:
            logger.error("خطا: تاریخ فاکتور وارد نشده است")
            raise forms.ValidationError(_('تاریخ فاکتور اجباری است.'))
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
            gregorian_date = j_date.togregorian()
            logger.info(f"تاریخ تبدیل‌شده: {gregorian_date}")
            return timezone.make_aware(gregorian_date)
        except ValueError:
            # logger.error(f"خطا در تبدیل تاریخ: {e}")
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError(_("وارد کردن مبلغ الزامی است."))
        if amount <= 0:
            raise forms.ValidationError(_("مبلغ باید بزرگتر از صفر باشد."))
        return amount

    def clean(self):
        cleaned_data = super().clean()
        logger.info(f"داده‌های اعتبارسنجی‌شده: {cleaned_data}")

        amount = cleaned_data.get('amount')
        tankhah = cleaned_data.get('tankhah')

        if not tankhah:
            logger.error("Validation error: Tankhah is required")
            raise forms.ValidationError(_('انتخاب تنخواه الزامی است.'))

        if amount is None or amount <= 0:
            logger.error("Validation error: Amount must be positive")
            raise forms.ValidationError(_('مبلغ فاکتور باید بزرگ‌تر از صفر باشد.'))
        if tankhah:
            remaining = get_tankhah_remaining_budget(tankhah)
            if amount > remaining:
                logger.error(f"Validation error: Amount ({amount}) exceeds tankhah remaining budget ({remaining})")
                raise forms.ValidationError(
                    _('مبلغ فاکتور از بودجه باقی‌مانده تنخواه ({}) بیشتر است.').format(remaining)
                )
        logger.info("FactorForm cleaned successfully")
        return cleaned_data

    def save(self, commit=True):
        logger.info(f"Starting save for factor by {self.user}, commit={commit}, data={self.cleaned_data}")
        instance = super().save(commit=False)
        if self.user:
            if self.instance.pk and self.has_changed():
                old_instance = Factor.objects.get(pk=self.instance.pk)
                for field in self.changed_data:
                    old_value = getattr(old_instance, field)
                    new_value = getattr(instance, field)
                    logger.info(
                        f"Change in factor (ID: {instance.pk}): {field} from {old_value} to {new_value} by {self.user}")
            else:
                logger.info(f"Creating new factor by {self.user}: {self.cleaned_data}")
        if commit:
            instance.save()
            logger.info(f"Factor saved: ID={instance.pk}, number={instance.number}")
        return instance

class old__FactorItemForm(forms.ModelForm):
    class Meta:
        model = FactorItem
        # fields = ['description', 'amount', 'quantity']
        # fields = ['description', 'unit_price', 'quantity']
        fields = ['description', 'quantity', 'unit_price']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('شرح ردیف')}),
             'unit_price': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm ltr-input unit-price-field', 'step': '1', 'min': '0', 'placeholder': 'مبلغ واحد'}),
            'quantity': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm ltr-input quantity-field', 'placeholder': _('تعداد'), 'min': '1'}),
        }
        labels = {
            'description': _('شرح'),
            'unit_price': _('مبلغ واحد'),
            'quantity': _('تعداد'),
        }

    def clean(self):
        cleaned_data = super().clean()
        description = cleaned_data.get('description')
        unit_price = cleaned_data.get('unit_price')
        quantity = cleaned_data.get('quantity')
        logger.debug(f"Cleaning FactorItemForm: description={description}, unit_price={unit_price}, quantity={quantity}")

        # بررسی فرم خالی یا در حال حذف
        is_potentially_empty = not description and (unit_price is None or unit_price == 0) and (quantity is None or quantity == 1)
        is_marked_for_deletion = cleaned_data.get('DELETE', False)

        if is_potentially_empty or is_marked_for_deletion:
            cleaned_data['DELETE'] = True
            logger.info("Empty or marked for deletion FactorItemForm. Skipping validation.")
            return cleaned_data

        errors_found = False
        # اعتبارسنجی‌های پایه‌ای فرم
        if not description:
            logger.error("FactorItemForm Validation error: Description is required")
            self.add_error('description', _('شرح ردیف الزامی است.'))
            errors_found = True
        if unit_price is None or not isinstance(unit_price, Decimal) or unit_price <= Decimal('0'):
            logger.error(f"FactorItemForm Validation error: Unit price invalid. Value={repr(unit_price)}")
            self.add_error('unit_price', _('مبلغ واحد باید بزرگ‌تر از صفر باشد.'))
            errors_found = True
        if quantity is None or not isinstance(quantity, Decimal) or quantity <= Decimal('0'): # بررسی quantity هم مهم است
            logger.error(f"FactorItemForm Validation error: Quantity invalid. Value={repr(quantity)}")
            self.add_error('quantity', _('تعداد باید بزرگ‌تر از صفر باشد.'))
            errors_found = True


        # اگر خطاهای پایه‌ای وجود نداشت، مبلغ را محاسبه کن
        if not errors_found:
            try:
                calculated_amount = unit_price * quantity
                if calculated_amount <= 0:
                     logger.error(f"FactorItemForm Validation error: Calculated amount is not positive. Amount={calculated_amount}")
                     # خطای کلی فرم، چون نتیجه محاسبه است
                     self.add_error(None, _('مبلغ محاسبه شده ردیف (قیمت * تعداد) باید بزرگ‌تر از صفر باشد.'))
                     errors_found = True
                else:
                     # مبلغ محاسبه شده را در cleaned_data ذخیره کن
                     cleaned_data['amount'] = calculated_amount
                     logger.info(f"FactorItemForm: Calculated and stored amount in cleaned_data: {calculated_amount}")
            except TypeError:
                 logger.error("FactorItemForm Validation error: Cannot calculate amount due to invalid types for unit_price or quantity.")
                 self.add_error(None, _('خطا در محاسبه مبلغ ردیف. مقادیر قیمت و تعداد را بررسی کنید.'))
                 errors_found = True
        else:
             # اگر خطای پایه‌ای بود، amount را در cleaned_data نگذار
             logger.warning("FactorItemForm: Skipping amount calculation due to base validation errors.")


        if not self.errors: # بررسی کنید آیا خطایی توسط add_error اضافه شده است
            logger.info("FactorItemForm cleaned successfully (No errors added)")
        else:
            logger.warning(f"FactorItemForm cleaned with errors: {self.errors}")

        return cleaned_data


    # def clean(self):
    #     cleaned_data = super().clean()
    #     description = cleaned_data.get('description')
    #     unit_price = cleaned_data.get('unit_price')
    #     quantity = cleaned_data.get('quantity')
    #     logger.debug(f"Cleaning FactorItemForm: description={description}, unit_price={unit_price}, quantity={quantity}")
    #
    #     # نادیده گرفتن فرم‌های خالی
    #     if not description and (unit_price is None or unit_price == 0) and (quantity is None or quantity == 1):
    #         cleaned_data['DELETE'] = True
    #         logger.info("Empty form marked for deletion")
    #         return cleaned_data
    #
    #     # اعتبارسنجی برای فرم‌های پرشده
    #     if not description:
    #         raise forms.ValidationError(_('شرح ردیف الزامی است.'))
    #     if unit_price is None or unit_price <= 0:
    #         raise forms.ValidationError(_('مبلغ واحد باید بزرگ‌تر از صفر باشد.'))
    #     if quantity is None or quantity <= 0:
    #         raise forms.ValidationError(_('تعداد باید بزرگ‌تر از صفر باشد.'))
    #
    #     # محاسبه amount
    #     amount = unit_price * quantity
    #     if amount <= 0:
    #         raise forms.ValidationError(_('مبلغ ردیف باید بزرگ‌تر از صفر باشد.'))
    #     cleaned_data['amount'] = amount
    #
    #     logger.info("FactorItemForm cleaned successfully")
    #     return cleaned_data

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
