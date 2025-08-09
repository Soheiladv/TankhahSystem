import logging
from decimal import Decimal
import jdatetime
from django import forms
from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError # Import ValidationError

# Assuming models are imported correctly
from budgets.models import BudgetAllocation, BudgetPeriod, BudgetItem
from core.models import Organization, OrganizationType, Project # Assuming core models
# Assuming utils are imported correctly
from Tanbakhsystem.utils import  parse_jalali_date

logger = logging.getLogger(__name__)

class OLD____BudgetAllocationForm(forms.ModelForm):
    ALLOCATION_TYPE_CHOICES = [
        ('amount', _('مبلغ')),
        ('percent', _('درصد')),
    ]
    # Assuming WARNING_ACTION_CHOICES are defined in the model now, use model's choices
    # WARNING_ACTION_CHOICES = BudgetAllocation.WARNING_ACTION_CHOICES # Get choices from model

    allocation_type = forms.ChoiceField(
        choices=ALLOCATION_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label=_('نوع تخصیص'),
        initial='amount',
        required=True
    )

    # Use CharField for date input to handle Jalali string
    allocation_date = forms.CharField(
        label=_('تاریخ تخصیص'), # Changed label slightly
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control form-control-lg jalali-datepicker', # Added jalali-datepicker class
            'autocomplete': 'off',
            'placeholder': _('مثال: 1404/01/26') # Updated placeholder
        }),
        required=True
    )

    class Meta:
        model = BudgetAllocation
        fields = [
            'budget_period','budget_item', 'organization', 'project', 'allocated_amount',
            'allocation_date', 'description', 'is_active', 'is_stopped',
            'allocation_type', 'locked_percentage', 'warning_threshold',
            'warning_action', 'allocation_number'
        ]
        widgets = {
            'budget_item': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'required': 'required',
                'data-control': 'select2',
                'data-placeholder': _('انتخاب ردیف بودجه'),
                'id': 'id_budget_item'
            }),
            'organization': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'required': 'required',
                'data-control': 'select2',
                'data-placeholder': _('انتخاب سازمان'),
                'id': 'id_organization'  # برای دسترسی آسان در جاوااسکریپت
            }),
            'project': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'data-control': 'select2',
                'data-placeholder': _('انتخاب پروژه'),
                'id': 'id_project'  # برای دسترسی آسان در جاوااسکریپت
            }),
            'allocated_amount': forms.TextInput(attrs={ # Use TextInput for flexibility with formatting JS
                'class': 'form-control form-control-lg numeric-input',
                'inputmode': 'decimal', # Use decimal for amounts potentially with fractions
                'required': 'required',
                'placeholder': _('مقدار مبلغ یا درصد') # Placeholder reflects type choice
            }),
            # allocation_date widget is defined above as CharField
            'description': forms.Textarea(attrs={
                'class': 'form-control form-control-lg',
                'rows': 3,
                'placeholder': _('توضیحات (اختیاری)')
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'is_stopped': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'locked_percentage': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg', 'min': '0', 'max': '100', 'step': '0.01'
            }),
            'warning_threshold': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg', 'min': '0', 'max': '100', 'step': '0.01'
            }),
            'warning_action': forms.Select(attrs={'class': 'form-select form-select-lg'}), # Use model choices
            'allocation_number': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg', 'min': '0', 'step': '1'
            }),
            'budget_period': forms.HiddenInput(),
        }
        labels = {
            # Labels are mostly defined by model verbose_name, override if needed
            'budget_item': _(' ردیف بودجه '),
            'organization': _('سازمان/شعبه'),
            'project': _('پروژه (اختیاری)'),
            'allocated_amount': _('مقدار (مبلغ/درصد)'),
            'allocation_date': _('تاریخ تخصیص'),
            'description': _('شرح'),
            'is_active': _('فعال'),
            'is_stopped': _('متوقف شده'),
            'locked_percentage': _('درصد قفل (%)'),
            'warning_threshold': _('آستانه هشدار (%)'),
            'warning_action': _('اقدام هشدار'),
            'allocation_number': _('شماره تخصیص (اختیاری)'),
        }
        help_texts = {
            'locked_percentage': _('درصدی از بودجه که تخصیص دیگر امکان‌پذیر نیست.'),
            'warning_threshold': _('درصدی از بودجه که باعث نمایش/ارسال هشدار می‌شود.'),
            'project': _('پروژه‌ای که این بودجه به آن مرتبط است (در صورت وجود).')
        }

    def __init__(self, *args, user=None, budget_period=None, **kwargs):
        # مقداردهی اولیه فرم
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # محدود کردن گزینه‌های budget_item به دوره بودجه انتخاب‌شده
        # budget_period_id = self.initial.get('budget_period') or self.data.get('budget_period')
        # if budget_period_id:
        #     self.fields['budget_item'].queryset = BudgetItem.objects.filter(budget_period_id=budget_period_id)
        # تنظیم required برای فیلدها
        self.fields['budget_item'].required = True
        self.fields['organization'].required = True
        self.fields['budget_period'].required = True
        self.fields['allocated_amount'].required = True
        self.fields['allocation_date'].required = True
        self.fields['allocation_type'].required = True

        self.user = user
        self.budget_period = budget_period

        # تنظیم budget_period
        if self.budget_period:
            # self.fields['budget_period'].queryset = BudgetPeriod.objects.filter(id=self.budget_period.id,
            #                                                                     is_active=True)
            # self.fields['budget_item'].queryset = BudgetItem.objects.filter(budget_period=self.budget_period,
            #                                                                 is_active=True)
            self.fields['budget_period'].queryset = BudgetPeriod.objects.filter(id=self.budget_period.id,
                                                                                is_active=True)
            # حذف فیلتر budget_period و is_active برای budget_item
            self.fields['budget_item'].queryset = BudgetItem.objects.all()
        else:
            # self.fields['budget_period'].queryset = BudgetPeriod.objects.filter(is_active=True)
            # self.fields['budget_item'].queryset = BudgetItem.objects.none()
            self.fields['budget_period'].queryset = BudgetPeriod.objects.filter(is_active=True)
            # در صورت عدم وجود budget_period، همچنان تمام budget_item‌ها نمایش داده شوند
            self.fields['budget_item'].queryset = BudgetItem.objects.all()

        # تنظیم کوئری‌ست‌ها
        self.fields['organization'].queryset = Organization.objects.filter(
            org_type__is_budget_allocatable=True, is_active=True
        ).select_related('org_type').order_by('name')
        self.fields['project'].queryset = Project.objects.filter(is_active=True).order_by('name')
        self.fields['project'].required = False
        self.fields['project'].empty_label = _("--------- (بدون پروژه)")

        # تنظیم تاریخ پیش‌فرض جلالی
        default_date = jdatetime.date.today().strftime('%Y/%m/%d')
        if self.instance.pk and self.instance.allocation_date:
            try:
                initial_date = jdatetime.date.fromgregorian(
                    date=self.instance.allocation_date
                ).strftime('%Y/%m/%d')
                self.initial['allocation_date'] = initial_date
                logger.debug(f"Set initial allocation_date from instance: {initial_date}")
            except Exception as e:
                logger.error(f"Error formatting existing allocation_date: {e}")
                self.initial['allocation_date'] = default_date
        else:
            self.initial['allocation_date'] = default_date
            logger.debug(f"Set default allocation_date: {default_date}")

        # تنظیم مقادیر اولیه
        if self.budget_period and not self.instance.pk:
            self.initial['locked_percentage'] = self.budget_period.locked_percentage
            self.initial['warning_threshold'] = self.budget_period.warning_threshold
            self.initial['warning_action'] = self.budget_period.warning_action

        # تنظیم کوئری‌ست سازمان‌ها
        try:
            allowed_org_types = OrganizationType.objects.filter(
                is_budget_allocatable=True
            ).values_list('id', flat=True)
            self.fields['organization'].queryset = Organization.objects.filter(
                org_type__in=allowed_org_types,
                is_active=True
            ).select_related('org_type').order_by('name')
            logger.debug("Organization queryset set for active, allocatable orgs.")
        except Exception as e:
            logger.error(f"Error setting organization queryset: {e}")
            self.fields['organization'].queryset = Organization.objects.none()

    def clean_organization(self):
        organization = self.cleaned_data.get('organization')
        if organization and not organization.is_active:
            raise ValidationError(_('سازمان انتخاب شده فعال نیست و نمی‌توان به آن بودجه تخصیص داد.'))
        if organization and not organization.org_type.is_budget_allocatable:
            raise ValidationError(_('این نوع سازمان قابلیت دریافت تخصیص بودجه ندارد.'))
        return organization

    def clean_allocation_date(self):
        date_str = self.cleaned_data.get('allocation_date')
        if not date_str:
            raise ValidationError(_('تاریخ تخصیص اجباری است.'))
        try:
            parsed_date = parse_jalali_date(str(date_str), field_name=_('تاریخ تخصیص'))
            return parsed_date
        except ValueError as e:
            logger.warning(f"Could not parse allocation_date '{date_str}': {e}")
            raise ValidationError(e)
        except Exception as e:
            logger.error(f"Unexpected error parsing allocation_date '{date_str}': {e}", exc_info=True)
            raise ValidationError(_('فرمت تاریخ تخصیص نامعتبر است.'))

    def clean_allocated_amount(self):
        amount_input = self.cleaned_data.get('allocated_amount')
        allocation_type = self.cleaned_data.get('allocation_type')
        budget_period = self.cleaned_data.get('budget_period') or self.budget_period

        if amount_input is None:
            raise ValidationError(_('مقدار تخصیص نمی‌تواند خالی باشد.'))

        try:
            amount_decimal = Decimal(str(amount_input))
        except Exception:
            raise ValidationError(_('مقدار وارد شده عدد معتبری نیست.'))

        if amount_decimal <= 0:
            raise ValidationError(_('مقدار تخصیص باید مثبت باشد.'))

        if allocation_type == 'percent' and not (0 <= amount_decimal <= 100):
            raise ValidationError(_('درصد تخصیص باید بین ۰ تا ۱۰۰ باشد.'))

        return amount_decimal

    def clean(self):
        cleaned_data = super().clean()
        budget_period = cleaned_data.get('budget_period')
        organization = cleaned_data.get('organization')
        budget_item = cleaned_data.get('budget_item')
        project = cleaned_data.get('project')
        allocated_amount = cleaned_data.get('allocated_amount')
        allocation_date = cleaned_data.get('allocation_date')
        allocation_type = cleaned_data.get('allocation_type')
        warning_threshold = cleaned_data.get('warning_threshold')

        # چک کردن فیلدهای اجباری
        if not budget_period:
            self.add_error('budget_period', _("دوره بودجه اجباری است."))
        if not organization:
            self.add_error('organization', _("سازمان دریافت‌کننده اجباری است."))
        if not budget_item:
            self.add_error('budget_item', _("ردیف بودجه اجباری است."))
        if allocated_amount is None:
            self.add_error('allocated_amount', _("مبلغ تخصیص اجباری است."))
        if not allocation_type:
            self.add_error('allocation_type', _("نوع تخصیص اجباری است."))

        # اعتبارسنجی تطابق budget_item با organization
        if budget_item and organization and budget_item.organization != organization:
            self.add_error('budget_item', _("ردیف بودجه باید متعلق به سازمان انتخاب‌شده باشد."))

        # اعتبارسنجی تطابق project با organization
        if project and organization and not project.organizations.filter(id=organization.id).exists():
            self.add_error('project', _("پروژه انتخاب‌شده به سازمان انتخاب‌شده تعلق ندارد."))

        # تبدیل درصد به مبلغ
        if budget_period and allocated_amount is not None and allocation_type == 'percent':
            total_amount = budget_period.total_amount
            allocated_amount = (Decimal(allocated_amount) / Decimal('100')) * total_amount
            cleaned_data['allocated_amount'] = allocated_amount
            logger.debug(f"Converted percent to amount: {allocated_amount}")

        # اعتبارسنجی بودجه باقی‌مانده
        if budget_period and allocated_amount is not None:
            used_budget = BudgetAllocation.objects.filter(budget_period=budget_period).aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')
            if self.instance.pk:
                current_allocation = BudgetAllocation.objects.filter(pk=self.instance.pk).aggregate(
                    total=Sum('allocated_amount')
                )['total'] or Decimal('0')
                used_budget -= current_allocation
            remaining_budget = budget_period.total_amount - used_budget
            if allocated_amount > remaining_budget:
                self.add_error('allocated_amount', _(
                    f"مبلغ تخصیص ({allocated_amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) است."
                ))

        # اعتبارسنجی تاریخ تخصیص
        if allocation_date and budget_period:
            if not (budget_period.start_date <= allocation_date <= budget_period.end_date):
                self.add_error('allocation_date', _(
                    f"تاریخ تخصیص باید در بازه {budget_period.start_date} تا {budget_period.end_date} باشد."
                ))

        # اعتبارسنجی warning_threshold
        if warning_threshold is not None and not (0 <= warning_threshold <= 100):
            self.add_error('warning_threshold', _("آستانه اخطار باید بین ۰ تا ۱۰۰ باشد."))

        # اعتبارسنجی مدل
        try:
            allocation = self.instance
            allocation.budget_period = budget_period
            allocation.organization = organization
            allocation.budget_item = budget_item
            allocation.allocated_amount = allocated_amount
            allocation.allocation_date = allocation_date
            allocation.allocation_type = allocation_type
            allocation.locked_percentage = cleaned_data.get('locked_percentage')
            allocation.warning_threshold = warning_threshold
            allocation.warning_action = cleaned_data.get('warning_action')
            allocation.project = project
            allocation.description = cleaned_data.get('description')
            allocation.allocation_number = cleaned_data.get('allocation_number')
            allocation.is_active = cleaned_data.get('is_active', True)
            allocation.is_stopped = cleaned_data.get('is_stopped', False)
            allocation.clean()
        except Exception as e:
            logger.error(f"Error in BudgetAllocationForm.clean: {str(e)}")
            self.add_error(None, _(f"خطا در اعتبارسنجی تخصیص: {str(e)}"))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not self.cleaned_data.get('budget_period') and self.budget_period:
            instance.budget_period = self.budget_period
        elif not instance.budget_period_id:
            raise ValidationError(_('دوره بودجه اجباری است.'))

        # instance.allocated_amount = self.cleaned_data['effective_amount']
        instance.allocated_amount = self.cleaned_data['allocated_amount']  # استفاده از allocated_amount
        if not instance.pk and self.user and self.user.is_authenticated:
            instance.created_by = self.user

        with transaction.atomic():
            instance = super().save(commit=commit)
            if commit and instance.budget_period_id:
                total_allocated = BudgetAllocation.objects.filter(
                    budget_period=instance.budget_period
                ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
                instance.budget_period.total_allocated = total_allocated
                instance.budget_period.save(update_fields=['total_allocated'])

        return instance


class BudgetAllocationForm(forms.ModelForm):
    ALLOCATION_TYPE_CHOICES = [
        ('amount', _('مبلغ')),
        ('percent', _('درصد')),
    ]

    allocation_type = forms.ChoiceField(
        choices=ALLOCATION_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label=_('نوع تخصیص'),
        initial='amount',
        required=True
    )

    allocation_date = forms.CharField(
        label=_('تاریخ تخصیص'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control form-control-lg jalali-datepicker',
            'autocomplete': 'off',
            'placeholder': _('مثال: 1404/01/26')
        }),
        required=True
    )

    class Meta:
        model = BudgetAllocation
        fields = [
            'budget_period', 'budget_item', 'organization', 'project', 'allocated_amount',
            'allocation_date', 'description', 'is_active', 'is_stopped',
            'allocation_type', 'locked_percentage', 'warning_threshold',
            'warning_action', 'allocation_number'
        ]
        widgets = {
            'budget_item': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'required': 'required',
                'data-control': 'select2',
                'data-placeholder': _('انتخاب ردیف بودجه'),
                'id': 'id_budget_item'
            }),
            'organization': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'required': 'required',
                'data-control': 'select2',
                'data-placeholder': _('انتخاب سازمان'),
                'id': 'id_organization'
            }),
            'project': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'data-control': 'select2',
                'data-placeholder': _('انتخاب پروژه'),
                'id': 'id_project'
            }),
            'allocated_amount': forms.TextInput(attrs={
                'class': 'form-control form-control-lg numeric-input',
                'inputmode': 'decimal',
                'required': 'required',
                'placeholder': _('مقدار مبلغ یا درصد')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control form-control-lg',
                'rows': 3,
                'placeholder': _('توضیحات (اختیاری)')
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'is_stopped': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'locked_percentage': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg', 'min': '0', 'max': '100', 'step': '0.01'
            }),
            'warning_threshold': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg', 'min': '0', 'max': '100', 'step': '0.01'
            }),
            'warning_action': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'allocation_number': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg', 'min': '0', 'step': '1'
            }),
            'budget_period': forms.HiddenInput(),
        }
        labels = {
            'budget_item': _('ردیف بودجه'),
            'organization': _('سازمان/شعبه'),
            'project': _('پروژه (اختیاری)'),
            'allocated_amount': _('مقدار (مبلغ/درصد)'),
            'allocation_date': _('تاریخ تخصیص'),
            'description': _('شرح'),
            'is_active': _('فعال'),
            'is_stopped': _('متوقف شده'),
            'locked_percentage': _('درصد قفل (%)'),
            'warning_threshold': _('آستانه هشدار (%)'),
            'warning_action': _('اقدام هشدار'),
            'allocation_number': _('شماره تخصیص (اختیاری)'),
        }
        help_texts = {
            'locked_percentage': _('درصدی از بودجه که تخصیص دیگر امکان‌پذیر نیست.'),
            'warning_threshold': _('درصدی از بودجه که باعث نمایش/ارسال هشدار می‌شود.'),
            'project': _('پروژه‌ای که این بودجه به آن مرتبط است (در صورت وجود).')
        }

    def __init__(self, *args, user=None, budget_period=None, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['budget_item'].required = True
        self.fields['organization'].required = True
        self.fields['budget_period'].required = True
        self.fields['allocated_amount'].required = True
        self.fields['allocation_date'].required = True
        self.fields['allocation_type'].required = True

        self.user = user
        self.budget_period = budget_period

        # تنظیم queryset برای budget_item بدون فیلتر اضافی
        self.fields['budget_item'].queryset = BudgetItem.objects.filter(is_active=True).order_by('name')

        # تنظیم queryset برای budget_period
        if self.budget_period:
            self.fields['budget_period'].queryset = BudgetPeriod.objects.filter(id=self.budget_period.id,
                                                                                is_active=True)
        else:
            self.fields['budget_period'].queryset = BudgetPeriod.objects.filter(is_active=True)

        # تنظیم queryset برای organization
        self.fields['organization'].queryset = Organization.objects.filter(
            org_type__is_budget_allocatable=True, is_active=True
        ).select_related('org_type').order_by('name')

        # تنظیم queryset برای project
        self.fields['project'].queryset = Project.objects.filter(is_active=True).order_by('name')
        self.fields['project'].required = False
        self.fields['project'].empty_label = _("--------- (بدون پروژه)")

        default_date = jdatetime.date.today().strftime('%Y/%m/%d')
        if self.instance.pk and self.instance.allocation_date:
            try:
                initial_date = jdatetime.date.fromgregorian(
                    date=self.instance.allocation_date
                ).strftime('%Y/%m/%d')
                self.initial['allocation_date'] = initial_date
                logger.debug(f"Set initial allocation_date from instance: {initial_date}")
            except Exception as e:
                logger.error(f"Error formatting existing allocation_date: {e}")
                self.initial['allocation_date'] = default_date
        else:
            self.initial['allocation_date'] = default_date
            logger.debug(f"Set default allocation_date: {default_date}")

        if self.budget_period and not self.instance.pk:
            self.initial['locked_percentage'] = self.budget_period.locked_percentage
            self.initial['warning_threshold'] = self.budget_period.warning_threshold
            self.initial['warning_action'] = self.budget_period.warning_action

        try:
            allowed_org_types = OrganizationType.objects.filter(
                is_budget_allocatable=True
            ).values_list('id', flat=True)
            self.fields['organization'].queryset = Organization.objects.filter(
                org_type__in=allowed_org_types, is_active=True
            ).select_related('org_type').order_by('name')
            logger.debug("Organization queryset set for active, allocatable orgs.")
        except Exception as e:
            logger.error(f"Error setting organization queryset: {e}")
            self.fields['organization'].queryset = Organization.objects.none()

    def clean_organization(self):
        organization = self.cleaned_data.get('organization')
        if organization and not organization.is_active:
            raise ValidationError(_('سازمان انتخاب شده فعال نیست و نمی‌توان به آن بودجه تخصیص داد.'))
        if organization and not organization.org_type.is_budget_allocatable:
            raise ValidationError(_('این نوع سازمان قابلیت دریافت تخصیص بودجه ندارد.'))
        return organization

    def clean_allocation_date(self):
        date_str = self.cleaned_data.get('allocation_date')
        try:
            return parse_jalali_date(date_str)
        except (ValueError, TypeError):
            raise forms.ValidationError(_('فرمت تاریخ نامعتبر است.'))
    def clean_allocated_amount(self):
        amount_input = self.cleaned_data.get('allocated_amount')
        allocation_type = self.cleaned_data.get('allocation_type')
        budget_period = self.cleaned_data.get('budget_period') or self.budget_period

        if amount_input is None:
            raise ValidationError(_('مقدار تخصیص نمی‌تواند خالی باشد.'))

        try:
            amount_decimal = Decimal(str(amount_input))
        except Exception:
            raise ValidationError(_('مقدار وارد شده عدد معتبری نیست.'))

        if amount_decimal <= 0:
            raise ValidationError(_('مقدار تخصیص باید مثبت باشد.'))

        if allocation_type == 'percent' and not (0 <= amount_decimal <= 100):
            raise ValidationError(_('درصد تخصیص باید بین ۰ تا ۱۰۰ باشد.'))

        return amount_decimal

    def clean(self):
        cleaned_data = super().clean()
        budget_period = cleaned_data.get('budget_period')
        organization = cleaned_data.get('organization')
        budget_item = cleaned_data.get('budget_item')
        project = cleaned_data.get('project')
        allocated_amount = cleaned_data.get('allocated_amount')
        allocation_date = cleaned_data.get('allocation_date')
        allocation_type = cleaned_data.get('allocation_type')
        warning_threshold = cleaned_data.get('warning_threshold')

        # چک کردن فیلدهای اجباری
        if not budget_period:
            self.add_error('budget_period', _("دوره بودجه اجباری است."))
        if not organization:
            self.add_error('organization', _("سازمان دریافت‌کننده اجباری است."))
        if not budget_item:
            self.add_error('budget_item', _("ردیف بودجه اجباری است."))
        if allocated_amount is None:
            self.add_error('allocated_amount', _("مبلغ تخصیص اجباری است."))
        if not allocation_type:
            self.add_error('allocation_type', _("نوع تخصیص اجباری است."))

        # # اعتبارسنجی تطابق budget_item با organization
        # if budget_item and organization and budget_item.organization != organization:
        #     self.add_error('budget_item', _("ردیف بودجه باید متعلق به سازمان انتخاب‌شده باشد."))

        # # اعتبارسنجی تطابق project با organization
        # if project and organization and not project.organizations.filter(id=organization.id).exists():
        #     self.add_error('project', _("پروژه انتخاب‌شده به سازمان انتخاب‌شده تعلق ندارد."))

        # تبدیل درصد به مبلغ
        if budget_period and allocated_amount is not None and allocation_type == 'percent':
            total_amount = budget_period.total_amount
            allocated_amount = (Decimal(allocated_amount) / Decimal('100')) * total_amount
            cleaned_data['allocated_amount'] = allocated_amount
            logger.debug(f"Converted percent to amount: {allocated_amount}")

        # اعتبارسنجی بودجه باقی‌مانده
        if budget_period and allocated_amount is not None:
            used_budget = BudgetAllocation.objects.filter(budget_period=budget_period).aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')
            if self.instance.pk:
                current_allocation = BudgetAllocation.objects.filter(pk=self.instance.pk).aggregate(
                    total=Sum('allocated_amount')
                )['total'] or Decimal('0')
                used_budget -= current_allocation
            remaining_budget = budget_period.total_amount - used_budget
            if allocated_amount > remaining_budget:
                self.add_error('allocated_amount', _(
                    f"مبلغ تخصیص ({allocated_amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) است."
                ))

        # # اعتبارسنجی تاریخ تخصیص
        # if allocation_date and budget_period:
        #     if not (budget_period.start_date <= allocation_date <= budget_period.end_date):
        #         self.add_error('allocation_date', _(
        #             f"تاریخ تخصیص باید در بازه {budget_period.start_date} تا {budget_period.end_date} باشد."
        #         ))

        # اعتبارسنجی warning_threshold
        if warning_threshold is not None and not (0 <= warning_threshold <= 100):
            self.add_error('warning_threshold', _("آستانه اخطار باید بین ۰ تا ۱۰۰ باشد."))

        # اعتبارسنجی مدل
        try:
            allocation = self.instance
            allocation.budget_period = budget_period
            allocation.organization = organization
            allocation.budget_item = budget_item
            allocation.allocated_amount = allocated_amount
            allocation.allocation_date = allocation_date
            allocation.allocation_type = allocation_type
            allocation.locked_percentage = cleaned_data.get('locked_percentage')
            allocation.warning_threshold = warning_threshold
            allocation.warning_action = cleaned_data.get('warning_action')
            allocation.project = project
            allocation.description = cleaned_data.get('description')
            allocation.allocation_number = cleaned_data.get('allocation_number')
            allocation.is_active = cleaned_data.get('is_active', True)
            allocation.is_stopped = cleaned_data.get('is_stopped', False)
            allocation.clean()
        except Exception as e:
            logger.error(f"Error in BudgetAllocationForm.clean: {str(e)}")
            self.add_error(None, _(f"خطا در اعتبارسنجی تخصیص: {str(e)}"))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not self.cleaned_data.get('budget_period') and self.budget_period:
            instance.budget_period = self.budget_period
        elif not instance.budget_period_id:
            raise ValidationError(_('دوره بودجه اجباری است.'))

        instance.allocated_amount = self.cleaned_data['allocated_amount']
        if not instance.pk and self.user and self.user.is_authenticated:
            instance.created_by = self.user

        with transaction.atomic():
            instance = super().save(commit=commit)
            if commit and instance.budget_period_id:
                total_allocated = BudgetAllocation.objects.filter(
                    budget_period=instance.budget_period
                ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
                instance.budget_period.total_allocated = total_allocated
                instance.budget_period.save(update_fields=['total_allocated'])

        return instance