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
from Tanbakhsystem.utils import to_english_digits, format_jalali_date, parse_jalali_date

logger = logging.getLogger(__name__)
class __BudgetAllocationForm(forms.ModelForm):
    ALLOCATION_TYPE_CHOICES = [
        ('amount', _('مبلغ')),
        ('percent', _('درصد')),
    ]

    WARNING_ACTION_CHOICES_ = [
        ('email', _('ارسال ایمیل هشدار')),
        ('sms', _('ارسال پیامک هشدار')),
        ('notification', _('ارسال اعلان سیستم')),
    ]
    WARNING_ACTION_CHOICES = [
    ('NOTIFY', _("فقط اعلان")), ('LOCK', _("قفل کردن")), ('RESTRICT', _("محدود کردن ثبت")),]
    allocation_type = forms.ChoiceField(
        choices=ALLOCATION_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label=_('نوع تخصیص'),
        initial='amount'
    )

    warning_action = forms.ChoiceField(
        choices=WARNING_ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
        label=_('اقدام هشدار'),
        required=False
    )
    allocation_date = forms.CharField(
        label=_('تاریخ تخصیص بودجه'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control jalali-datepicker',
            'autocomplete': 'off'
        }),
        required=True
    )
    class Meta:
        model = BudgetAllocation
        fields = [
            'budget_period', 'organization', 'project', 'allocated_amount',
            'allocation_date', 'description', 'is_active', 'is_stopped',
            'allocation_type', 'locked_percentage', 'warning_threshold',
            'warning_action', 'allocation_number'
        ]
        widgets = {
            'organization': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'required': 'required',
                'data-control': 'select2',
                'data-placeholder': _('انتخاب سازمان')
            }),
            'project': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'required': 'required',
                'data-control': 'select2',
                'data-placeholder': _('انتخاب پروژه')
            }),
            'allocated_amount': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg numeric-input',
                'min': '0',
                'step': '1',
                'inputmode': 'numeric',
                'required': 'required',
                'placeholder': _('مبلغ را وارد کنید')
            }),
            'allocation_date': forms.TextInput(attrs={
                'data-jdp': '',
                'class': 'form-control form-control-lg',
                'placeholder': '1404/01/17',
                'required': 'required',
                'autocomplete': 'off'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control form-control-lg',
                'rows': 3,
                'placeholder': _('توضیحات تخصیص بودجه')
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
                'style': 'width: 2.5rem; height: 1.5rem;'
            }),
            'is_stopped': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
                'style': 'width: 2.5rem; height: 1.5rem;'
            }),
            'locked_percentage': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'min': '0',
                'max': '100',
                'step': '1',
                'inputmode': 'numeric',
                'placeholder': '0-100'
            }),
            'warning_threshold': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'min': '0',
                'max': '100',
                'step': '1',
                'inputmode': 'numeric',
                'placeholder': '0-100'
            }),
            'allocation_number': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'min': '0',
                'step': '1',
                'inputmode': 'numeric',
                'placeholder': _('شماره تخصیص')
            }),
            'budget_period': forms.HiddenInput(),
        }
        labels = {
            'organization': _('سازمان'),
            'project': _('پروژه'),
            'allocated_amount': _('مبلغ تخصیص'),
            'allocation_date': _('تاریخ تخصیص'),
            'description': _('شرح'),
            'is_active': _('فعال'),
            'is_stopped': _('متوقف شده'),
            'locked_percentage': _('درصد قفل شده'),
            'warning_threshold': _('آستانه اخطار'),
            'allocation_number': _('شماره تخصیص'),
        }
        help_texts = {
            'locked_percentage': _('درصدی از بودجه که پس از رسیدن به آن، تخصیص جدید غیرفعال می‌شود'),
            'warning_threshold': _('درصدی از بودجه که پس از رسیدن به آن، هشدار ارسال می‌شود'),
        }

    def __init__(self, *args, **kwargs):
        self.budget_period = kwargs.pop('budget_period', None)
        self.user = kwargs.pop('user', None)
        logger.debug(f"Initializing BudgetAllocationForm with budget_period={self.budget_period}, user={self.user}")

        super().__init__(*args, **kwargs)

        # تنظیم کوئری‌ست برای سازمان‌های قابل تخصیص بودجه
        allowed_org_types = OrganizationType.objects.filter(
            is_budget_allocatable=True
        ).values_list('id', flat=True)

        self.fields['organization'].queryset = Organization.objects.filter(
            org_type__in=allowed_org_types,
            is_active=True
        ).select_related('org_type')

        # تنظیم کوئری‌ست برای پروژه‌های فعال
        # self.fields['project'].queryset = Project.objects.filter(
        #     is_active=True
        # ).select_related('category')
        # تنظیم تاریخ‌های اولیه
        if self.instance and self.instance.pk:
            from Tanbakhsystem.utils import format_jalali_date
            self.initial['allocation_date'] = format_jalali_date(self.instance.allocation_date)

            logger.debug(
                f"Set initial dates: start_date={self.initial['allocation_date']}")
        else:
            current_jalali_year = jdatetime.date.today().year
            self.initial['allocation_date'] = f"{current_jalali_year}/01/01"
            logger.debug(
                f"Set default dates for new instance: start={self.initial['allocation_date']}")


        if self.budget_period:
            self.fields['budget_period'].initial = self.budget_period
            # فیلتر سازمان‌هایی که قبلاً برای این دوره بودجه تخصیص داده‌اند
            allocated_orgs = BudgetAllocation.objects.filter(
                budget_period=self.budget_period
            ).values_list('organization_id', flat=True)

            if allocated_orgs:
                self.fields['organization'].queryset = self.fields['organization'].queryset.filter(
                    id__in=allocated_orgs
                )

            logger.debug(
                f"Filtered organization queryset: {list(self.fields['organization'].queryset.values('id', 'fname'))}")

        # تبدیل تاریخ میلادی به شمسی برای نمایش
        if self.instance.pk and self.instance.allocation_date:
            j_date = jdatetime.date.fromgregorian(date=self.instance.allocation_date)
            self.initial['allocation_date'] = j_date.strftime('%Y/%m/%d')

    def clean_allocation_date(self):
        allocation_date = self.cleaned_data.get('allocation_date')
        logger.debug(f"Cleaning allocation_date: input={allocation_date}")
        if not allocation_date:
            logger.error("allocation_date is empty")
            raise forms.ValidationError(_('تاریخ شروع اجباری است.'))
        try:
            allocation_date = to_english_digits(allocation_date)
            from Tanbakhsystem.utils import parse_jalali_date
            parsed_date = parse_jalali_date(allocation_date, field_name=_('تاریخ شروع'))
            logger.debug(f"Parsed start_date: {parsed_date}")
            return parsed_date
        except Exception as e:
            logger.error(f"Error parsing start_date: {str(e)}")
            raise forms.ValidationError(_('فرمت تاریخ شروع نامعتبر است.'))


    # def clean_allocation_date(self):
    #     date_input = self.cleaned_data.get('allocation_date')
    #     logger.debug(f"Cleaning allocation_date: input={date_input}, type={type(date_input)}")
    #
    #     if not date_input:
    #         raise forms.ValidationError(_('تاریخ تخصیص اجباری است.'))
    #
    #     if isinstance(date_input, date):
    #         return date_input
    #
    #     try:
    #         date_str = to_english_digits(str(date_input).strip())
    #         date_str = re.sub(r'[-\.]', '/', date_str)
    #         # پشتیبانی از فرمت YYYY/MM/DD
    #         try:
    #             if re.match(r'^\d{4}/\d{2}/\d{2}$', date_str):
    #                 j_date = jdatetime.date.strptime(date_str, '%Y/%m/%d')
    #                 g_date = j_date.togregorian()
    #                 logger.debug(f"Parsed allocation_date: {g_date}")
    #                 return g_date
    #         except ValueError:
    #             pass
    #         # پشتیبانی از فرمت میلادی YYYY-MM-DD
    #         try:
    #             if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
    #                 g_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    #                 logger.debug(f"Parsed gregorian date: {g_date}")
    #                 return g_date
    #         except ValueError:
    #             pass
    #         raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17 یا 2025-04-01).'))
    #     except Exception as e:
    #         logger.error(f"Error parsing date: {str(e)}")
    #         raise forms.ValidationError(_('خطا در پردازش تاریخ.'))



    def clean(self):
        cleaned_data = super().clean()
        logger.debug(f"Running clean method: cleaned_data={cleaned_data}")

        organization = cleaned_data.get('organization')
        project = cleaned_data.get('project')
        allocated_amount = cleaned_data.get('allocated_amount')
        allocation_date = cleaned_data.get('allocation_date')
        budget_period = cleaned_data.get('budget_period')
        allocation_type = cleaned_data.get('allocation_type')
        locked_percentage = cleaned_data.get('locked_percentage')
        warning_threshold = cleaned_data.get('warning_threshold')

        # اعتبارسنجی دوره بودجه
        if not budget_period:
            logger.error("No budget_period selected")
            raise forms.ValidationError(_("دوره بودجه باید انتخاب شود."))

        # اعتبارسنجی سازمان
        if not organization:
            logger.error("No organization selected")
            raise forms.ValidationError(_('لطفاً یک سازمان انتخاب کنید.'))

        # اعتبارسنجی پروژه
        if not project:
            logger.error("No project selected")
            raise forms.ValidationError(_('لطفاً یک پروژه انتخاب کنید.'))

        # اعتبارسنجی مبلغ تخصیص
        if allocated_amount is None or allocated_amount <= 0:
            logger.error(f"Invalid allocated_amount: {allocated_amount}")
            raise forms.ValidationError(_('مبلغ تخصیص باید مثبت باشد.'))

        # اعتبارسنجی ارتباط سازمان و پروژه
        if organization and project:
            if not project.organizations.filter(id=organization.id).exists():
                logger.error(f"Project {project} does not belong to organization {organization}")
                raise forms.ValidationError(_('پروژه انتخاب‌شده متعلق به این سازمان نیست.'))

        # محاسبه بودجه باقیمانده
        if budget_period and allocated_amount:
            used_budget = BudgetAllocation.objects.filter(
                budget_period=budget_period
            ).exclude(id=self.instance.id).aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')

            remaining_budget = budget_period.total_amount - used_budget

            # اگر نوع تخصیص درصد باشد، محاسبه مبلغ معادل
            if allocation_type == 'percent':
                allocated_amount = (allocated_amount / 100) * budget_period.total_amount

            if allocated_amount > remaining_budget:
                logger.error(f"allocated_amount ({allocated_amount}) exceeds remaining_budget ({remaining_budget})")
                raise forms.ValidationError(_(
                    f'مبلغ تخصیص ({allocated_amount:,} ریال) بیشتر از بودجه باقی‌مانده ({remaining_budget:,} ریال) است.'
                ))

        # اعتبارسنجی تاریخ تخصیص
        if allocation_date and budget_period:
            start_date = budget_period.start_date
            end_date = budget_period.end_date

            if allocation_date < start_date or allocation_date > end_date:
                logger.error(f"allocation_date ({allocation_date}) outside budget_period range")
                raise forms.ValidationError(_('تاریخ تخصیص باید در بازه دوره بودجه باشد.'))

        # اعتبارسنجی درصدها
        if locked_percentage is not None and (locked_percentage < 0 or locked_percentage > 100):
            raise forms.ValidationError(_('درصد قفل‌شده باید بین ۰ تا ۱۰۰ باشد.'))

        if warning_threshold is not None and (warning_threshold < 0 or warning_threshold > 100):
            raise forms.ValidationError(_('آستانه اخطار باید بین ۰ تا ۱۰۰ باشد.'))

        if locked_percentage is not None and warning_threshold is not None:
            if locked_percentage >= warning_threshold:
                raise forms.ValidationError(_('آستانه اخطار باید بزرگتر از درصد قفل‌شده باشد.'))

        logger.debug("Clean method completed")
        return cleaned_data

    def save(self, commit=True):
        logger.debug("Saving BudgetAllocationForm")
        instance = super().save(commit=False)
        instance.budget_period = self.budget_period

        if self.user and self.user.is_authenticated:
            instance.created_by = self.user
            logger.debug(f"Set created_by: {self.user}")
        else:
            logger.error("No authenticated user provided for created_by")
            raise forms.ValidationError(_('کاربر معتبر برای ایجاد تخصیص بودجه لازم است.'))

        if commit:
            try:
                instance.save()
                logger.info(f"BudgetAllocation saved: {instance}")
            except Exception as e:
                logger.error(f"Error saving BudgetAllocation: {str(e)}")
                raise

        return instance

class BudgetAllocationForm(forms.ModelForm):
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
        super().__init__(*args, **kwargs)
        self.user = user
        self.budget_period = budget_period

        # تنظیم budget_period
        if self.budget_period:
            self.fields['budget_period'].initial = self.budget_period
            self.fields['budget_period'].widget.attrs['disabled'] = True
            budget_items = BudgetItem.objects.filter(
                budget_period=self.budget_period,
                is_active=True
            ).select_related('organization')
            if not budget_items.exists():
                logger.warning(f"No active BudgetItems found for budget_period ID={self.budget_period.id}")
                self.fields['budget_item'].queryset = BudgetItem.objects.none()
                self.fields['budget_item'].help_text = _("هیچ ردیف بودجه‌ای برای این دوره تعریف نشده است.")
            else:
                self.fields['budget_item'].queryset = budget_items
                self.fields['organization'].queryset = Organization.objects.filter(
                    budget_items__in=budget_items
                ).distinct()
        else:
            self.fields['budget_item'].queryset = BudgetItem.objects.none()
            self.fields['organization'].queryset = Organization.objects.none()

        logger.debug(f"Initialized BudgetAllocationForm with budget_period={budget_period}, user={user}")

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

        # تنظیم کوئری‌ست پروژه‌ها
        try:
            self.fields['project'].queryset = Project.objects.filter(is_active=True).order_by('name')
            self.fields['project'].empty_label = _("--------- (بدون پروژه)")
            self.fields['project'].required = False
            logger.debug("Initial project queryset set for all active projects.")
        except Exception as e:
            logger.error(f"Error setting project queryset: {e}")
            self.fields['project'].queryset = Project.objects.none()

        # تنظیم تاریخ اولیه
        if not self.initial.get('allocation_date'):
            if self.instance and self.instance.pk and self.instance.allocation_date:
                try:
                    self.initial['allocation_date'] = jdatetime.date.fromgregorian(
                        date=self.instance.allocation_date
                    ).strftime('%Y/%m/%d')
                    logger.debug(f"Set initial allocation_date from instance: {self.initial['allocation_date']}")
                except Exception as e:
                    logger.error(f"Error formatting existing allocation date: {e}")
                    self.initial['allocation_date'] = jdatetime.date.today().strftime('%Y/%m/%d')
            else:
                self.initial['allocation_date'] = jdatetime.date.today().strftime('%Y/%m/%d')
                logger.debug(f"Set default allocation_date for new instance: {self.initial['allocation_date']}")

        # تنظیم مقادیر اولیه برای هشدار و قفل
        if self.budget_period and not self.instance.pk:
            self.initial['locked_percentage'] = self.budget_period.locked_percentage
            self.initial['warning_threshold'] = self.budget_period.warning_threshold
            self.initial['warning_action'] = self.budget_period.warning_action
            logger.debug("Set initial warning/lock values from budget period.")


    def clean_organization(self):
        """Ensure the selected organization is active."""
        organization = self.cleaned_data.get('organization')
        if organization and not organization.is_active:
            logger.error(f"Selected organization '{organization.name}' (ID: {organization.id}) is not active.")
            raise ValidationError(_('سازمان انتخاب شده فعال نیست و نمی‌توان به آن بودجه تخصیص داد.'))
        # Also check if it's allocatable type (redundant if queryset is correct, but safe)
        if organization and not organization.org_type.is_budget_allocatable:
             logger.error(f"Selected organization '{organization.name}' type '{organization.org_type.name}' is not budget allocatable.")
             raise ValidationError(_('این نوع سازمان قابلیت دریافت تخصیص بودجه ندارد.'))
        return organization

    def clean_allocation_date(self):
        """Parse Jalali date string to Python date object."""
        date_str = self.cleaned_data.get('allocation_date')
        logger.debug(f"Cleaning allocation_date: input='{date_str}'")
        if not date_str:
            # This might be redundant if field is required=True
            raise ValidationError(_('تاریخ تخصیص اجباری است.'))
        try:
            # Use the utility function to parse
            parsed_date = parse_jalali_date(str(date_str), field_name=_('تاریخ تخصیص'))
            logger.debug(f"Parsed allocation_date: {parsed_date}")
            return parsed_date # Return the Python date object
        except ValueError as e: # Catch specific parsing errors
            logger.warning(f"Could not parse allocation_date '{date_str}': {e}")
            raise ValidationError(e) # Show the specific error from parse_jalali_date
        except Exception as e: # Catch other unexpected errors
            logger.error(f"Unexpected error parsing allocation_date '{date_str}': {e}", exc_info=True)
            raise ValidationError(_('فرمت تاریخ تخصیص نامعتبر است.'))

    def clean_allocated_amount(self):
        amount_input = self.cleaned_data.get('allocated_amount')
        allocation_type = self.cleaned_data.get('allocation_type')
        budget_item = self.cleaned_data.get('budget_item')
        logger.debug(f"Cleaning allocated_amount: input={amount_input}, allocation_type={allocation_type}")

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

        if allocation_type == 'percent' and budget_item:
            total_period_amount = budget_item.total_amount
            calculated_amount = (amount_decimal / Decimal('100')) * total_period_amount
        else:
            calculated_amount = amount_decimal

        if budget_item:
            remaining_budget = budget_item.get_remaining_amount()
            if self.instance.pk:
                current_allocation = BudgetAllocation.objects.filter(pk=self.instance.pk).aggregate(
                    total=Sum('allocated_amount')
                )['total'] or Decimal('0')
                remaining_budget += current_allocation
            if calculated_amount > remaining_budget:
                raise ValidationError(_(
                    f"مبلغ تخصیص ({calculated_amount:,.0f} ریال) بیشتر از باقی‌مانده ردیف بودجه ({remaining_budget:,.0f} ریال) است."
                ))

        logger.debug(f"Validated allocated_amount: {amount_decimal}")
        return amount_decimal

    def clean(self):
        cleaned_data = super().clean()
        logger.debug(f"Form clean: cleaned_data keys={list(cleaned_data.keys())}")
        organization = cleaned_data.get('organization')
        budget_item = cleaned_data.get('budget_item')
        project = cleaned_data.get('project')
        allocated_amount = cleaned_data.get('allocated_amount')
        allocation_date = cleaned_data.get('allocation_date')
        budget_period = cleaned_data.get('budget_period') or self.budget_period
        allocation_type = cleaned_data.get('allocation_type')

        if budget_item and organization:
            if budget_item.organization != organization:
                self.add_error('budget_item', _('ردیف بودجه باید متعلق به شعبه انتخاب‌شده باشد.'))

        if not budget_period:
            raise ValidationError(_('دوره بودجه مشخص نیست.'))

        if project and organization:
            if not project.organizations.filter(id=organization.id).exists():
                self.add_error('project', _('پروژه انتخاب‌شده به سازمان انتخاب‌شده تعلق ندارد.'))

        if allocation_type == 'percent' and allocated_amount is not None:
            effective_amount = (allocated_amount / Decimal('100')) * budget_period.total_amount
            logger.info(f"Calculated percent: {allocated_amount}% = {effective_amount} Riyals")
            cleaned_data['effective_amount'] = effective_amount
        elif allocated_amount is not None:
            cleaned_data['effective_amount'] = allocated_amount
            logger.debug(f"Effective amount: {allocated_amount} Riyals")

        if cleaned_data.get('effective_amount') and budget_period:
            used_budget = BudgetAllocation.objects.filter(budget_period=budget_period).aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')
            remaining_budget = budget_period.total_amount - used_budget
            logger.debug(f"Budget period {budget_period.id}: total={budget_period.total_amount}, used={used_budget}, remaining={remaining_budget}")
            if cleaned_data['effective_amount'] > remaining_budget:
                self.add_error('allocated_amount', _(
                    f'مبلغ تخصیص ({cleaned_data["effective_amount"]:,.0f} ریال) بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) است.'
                ))

        if allocation_date and budget_period:
            if not (budget_period.start_date <= allocation_date <= budget_period.end_date):
                self.add_error('allocation_date', _(
                    f'تاریخ تخصیص باید در بازه {budget_period.start_date} تا {budget_period.end_date} باشد.'
                ))

        if cleaned_data.get('warning_threshold') is not None and not (0 <= cleaned_data.get('warning_threshold') <= 100):
            self.add_error('warning_threshold', _('آستانه اخطار باید بین ۰ تا ۱۰۰ باشد.'))

        logger.debug("Form clean completed")
        return cleaned_data

    def save(self, commit=True):
        logger.debug(f"Saving BudgetAllocationForm (commit={commit}, user={self.user})")
        try:
            if not self.cleaned_data.get('budget_period') and self.budget_period:
                self.instance.budget_period = self.budget_period
                logger.debug(f"Set budget_period: {self.budget_period.id}")
            elif not self.instance.budget_period_id:
                logger.error("No budget_period provided")
                raise ValidationError("Budget period is required.")

            allocation_type = self.cleaned_data.get('allocation_type')
            allocated_amount = self.cleaned_data.get('allocated_amount')
            budget_item = self.cleaned_data.get('budget_item')

            if allocation_type == 'percent' and allocated_amount is not None:
                total_period_amount = self.instance.budget_period.total_amount
                calculated_amount = (allocated_amount / Decimal('100')) * total_period_amount
                self.instance.allocated_amount = calculated_amount
                logger.info(f"Set allocated_amount from percent: {allocated_amount}% = {calculated_amount} Riyals")
            else:
                self.instance.allocated_amount = allocated_amount
                logger.debug(f"Set allocated_amount: {allocated_amount} Riyals")

            if not self.instance.pk and self.user and self.user.is_authenticated:
                self.instance.created_by = self.user
                logger.debug(f"Set created_by: {self.user}")

            with transaction.atomic():
                instance = super().save(commit=commit)
                logger.info(f"Form saved BudgetAllocation with ID: {instance.pk}")
                if commit and instance.budget_period_id:
                    total_allocated = BudgetAllocation.objects.filter(
                        budget_period=instance.budget_period
                    ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
                    instance.budget_period.total_allocated = total_allocated
                    instance.budget_period.save(update_fields=['total_allocated'])
                    logger.info(f"Updated BudgetPeriod {instance.budget_period_id} with total_allocated={total_allocated}")

            return instance
        except Exception as e:
            logger.error(f"Error in BudgetAllocationForm.save: {str(e)}", exc_info=True)
            self.add_error(None, str(e))
            raise

