import logging
from decimal import Decimal

import jdatetime  # Assuming jdatetime is installed
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from Tanbakhsystem.utils import format_jalali_date, to_english_digits, parse_jalali_date
from accounts.AccessRule.check_user_access import check_user_factor_access
from accounts.middleware import get_current_user
from budgets.models import BudgetAllocation
# Assuming models are in the same app or imported correctly
# from tankhah.models import Factor, FactorItem, FactorDocument, Tankhah, ItemCategory, TankhahDocument
# Assuming utility functions/models exist
from core.models import   Project, SubProject, AccessRule, Organization, Post  # Example paths
# Assuming budget functions exist
from tankhah.models import ItemCategory, Tankhah, Factor, FactorItem
from tankhah.utils import restrict_to_user_organization, get_factor_current_stage

logger = logging.getLogger(__name__)

# Helper function to convert date (can be moved to utils)
def convert_to_farsi_numbers(text):
    """Converts English digits in a string to Farsi digits."""
    mapping = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
    return str(text).translate(mapping)

from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Max
from budgets.budget_calculations import get_tankhah_remaining_budget

# ====
# --- Form for Factor Documents (Multiple Upload) ---
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
                    import os
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
# --- Form for Tankhah Documents (Multiple Upload) ---
class TankhahDocumentForm(forms.Form):
    documents = MultipleFileField(
        label=_("پیوست‌های تنخواه - بارگذاری مدارک تنخواه (فقط {} مجاز است)".format(ALLOWED_EXTENSIONS_STR)),
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
                    import os
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
#-----------------------------------------------------------------------------------------------------------
class FactorForm(forms.ModelForm):
    date = forms.CharField(
        label=_('تاریخ فاکتور'),
        required=True,
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control form-control-sm',
            'placeholder': _('مثال: 1403/01/17')
        })
    )
    category = forms.ModelChoiceField(
        queryset=ItemCategory.objects.all(),
        label=_("دسته‌بندی هزینه"),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        empty_label=None
    )

    class Meta:
        model = Factor
        fields = ['tankhah', 'category', 'date', 'amount', 'description']
        widgets = {
            'tankhah': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm ltr-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
        }
        labels = {
            'tankhah': _('تنخواه مرتبط'),
            'date': _('تاریخ فاکتور'),
            'amount': _('مبلغ کل فاکتور (ریال)'),
            'description': _('شرح کلی فاکتور'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.tankhah_instance = kwargs.pop('tankhah', None)
        super().__init__(*args, **kwargs)

        # فیلتر کردن تنخواه‌ها بر اساس دسترسی کاربر
        tankhah_queryset = Tankhah.objects.filter(
            is_archived=False,
            status__in=['DRAFT', 'PENDING'],
            due_date__gte=timezone.now()
        ).order_by('-due_date')

        if self.user and not self.user.is_superuser:
            user_orgs = restrict_to_user_organization(self.user)
            if user_orgs:
                tankhah_queryset = tankhah_queryset.filter(
                    Q(organization__id__in=user_orgs) |
                    Q(project__organizations__id__in=user_orgs) |
                    Q(subproject__project__organizations__id__in=user_orgs)
                ).distinct()

        self.fields['tankhah'].queryset = tankhah_queryset.select_related('organization', 'project', 'project_budget_allocation')

        if self.tankhah_instance and tankhah_queryset.filter(pk=self.tankhah_instance.pk).exists():
            self.initial['tankhah'] = self.tankhah_instance
            self.fields['tankhah'].disabled = True

        if not self.initial.get('date'):
            self.initial['date'] = jdatetime.date.today().strftime('%Y/%m/%d')

        if self.instance and self.instance.pk and self.instance.date:
            try:
                self.initial['date'] = jdatetime.date.fromgregorian(date=self.instance.date).strftime('%Y/%m/%d')
            except Exception as e:
                logger.error(f"Error setting initial Jalali date for Factor {self.instance.pk}: {e}")

    def clean_date(self):
        date_str = self.cleaned_data.get('date')
        if not date_str:
            raise forms.ValidationError(_('وارد کردن تاریخ الزامی است.'))
        try:
            parsed_date = parse_jalali_date(date_str)
            return parsed_date
        except ValueError as e:
            logger.error(f"Error parsing date {date_str}: {e}")
            raise forms.ValidationError(_('فرمت تاریخ نامعتبر است. (مثال: 1403/01/17)'))

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError(_('وارد کردن مبلغ کل فاکتور الزامی است.'))
        if amount <= Decimal('0'):
            raise forms.ValidationError(_('مبلغ کل فاکتور باید بزرگتر از صفر باشد.'))
        return amount

    def clean(self):
        cleaned_data = super().clean()
        tankhah = cleaned_data.get('tankhah')
        amount = cleaned_data.get('amount')

        if not tankhah or not amount:
            return cleaned_data

        user = self.user
        if not user or not user.is_authenticated:
            raise forms.ValidationError(_('کاربر معتبر یافت نشد.'))

        # بررسی دسترسی کاربر با استفاده از تابع عمومی
        current_stage_order = get_factor_current_stage(self.instance if self.instance.pk else None) if self.instance.pk else 1
        access_info = check_user_factor_access(
            user.username,
            tankhah=tankhah,
            action_type='EDIT',
            entity_type='FACTOR',
            default_stage_order=current_stage_order
        )
        if not access_info['has_access']:
            logger.warning(
                f"کاربر {user.username} اجازه ثبت فاکتور برای تنخواه {tankhah.number} را ندارد. دلیل: {access_info.get('error', 'بدون دسترسی')}"
            )
            raise forms.ValidationError(_('شما اجازه ثبت فاکتور برای این تنخواه را ندارید.'))

        # اعتبارسنجی وضعیت تنخواه
        if tankhah.status not in ['DRAFT', 'PENDING']:
            raise forms.ValidationError(
                _('فقط برای تنخواه‌های در وضعیت پیش‌نویس یا در انتظار می‌توانید فاکتور ثبت کنید.'))

        # اعتبارسنجی انقضای تنخواه
        if tankhah.due_date and tankhah.due_date < timezone.now():
            raise forms.ValidationError(_('تنخواه منقضی شده است. لطفاً فاکتور را در تنخواه جدید ثبت کنید.'))

        # اعتبارسنجی بودجه
        try:
            budget_allocation = tankhah.project_budget_allocation
            if not budget_allocation or not budget_allocation.is_active:
                raise forms.ValidationError(_('تخصیص بودجه معتبر یا فعال برای این تنخواه یافت نشد.'))
            is_locked, lock_reason = budget_allocation.budget_period.is_locked  # استفاده از پراپرتی is_locked
            if is_locked:
                raise forms.ValidationError(lock_reason)
            remaining_budget = get_tankhah_remaining_budget(tankhah)
            if amount > remaining_budget:
                raise forms.ValidationError(
                    _('مبلغ فاکتور ({:,.0f} ریال) از بودجه باقی‌مانده تنخواه ({:,.0f} ریال) بیشتر است.').format(
                        amount, remaining_budget
                    ))
        except Exception as e:
            logger.error(f"Error validating budget for tankhah {tankhah.number}: {e}")
            raise forms.ValidationError(_('خطا در بررسی بودجه تنخواه: {}').format(str(e)))

        if not cleaned_data.get('category'):
            raise forms.ValidationError(_('دسته‌بندی الزامی است.'))

        return cleaned_data
#--------------------------------------------------------------
# ====
class Update_FactorForm(forms.ModelForm):
    date = forms.CharField(
        label='تاریخ فاکتور',
        required=True,
        widget=forms.TextInput(attrs={
            'data-jdp': '',  # برای فعال‌سازی Jalali date picker
            'class': 'form-control form-control-sm',
            'placeholder': 'مثال: 1403/01/17'
        })
    )
    category = forms.ModelChoiceField(
        queryset=ItemCategory.objects.all(),
        label="دسته‌بندی هزینه",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        empty_label=None
    )

    class Meta:
        model = Factor
        fields = ['tankhah', 'category', 'date', 'amount', 'description']
        widgets = {
            'tankhah': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm ltr-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
        }
        labels = {
            'tankhah': 'تنخواه مرتبط',
            'date': 'تاریخ فاکتور',
            'amount': 'مبلغ کل فاکتور (ریال)',
            'description': 'شرح کلی فاکتور',
            'category': 'دسته‌بندی اصلی هزینه',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.tankhah_instance = kwargs.pop('tankhah', None)
        super().__init__(*args, **kwargs)

        # غیرفعال کردن فیلد تنخواه در حالت ویرایش
        if self.instance and self.instance.pk:
            if 'tankhah' in self.fields:
                self.fields['tankhah'].disabled = True
                self.fields['tankhah'].widget.attrs['readonly'] = True
                self.fields['tankhah'].help_text = 'تنخواه قابل ویرایش نیست.'

        # تنظیم تاریخ جلالی برای حالت ویرایش
        # if self.instance.date and not self.initial.get('date'):
            try:
                self.initial['date'] = format_jalali_date(self.instance.date)
                logger.debug(f"Set initial date for Factor {self.instance.pk}: {self.initial['date']}")
            except Exception as e:
                logger.error(f"Error setting initial date for Factor {self.instance.pk}: {e}")
                self.initial['date'] = ''

        # فیلتر کردن تنخواه‌ها
        try:
            initial_stage = AccessRule.objects.order_by('order').first()
            initial_stage_order = initial_stage.order if initial_stage else 0
        except Exception as e:
            logger.error(f"Error getting initial workflow stage: {e}")
            initial_stage_order = 0

        tankhah_queryset = Tankhah.objects.none()
        if self.user:
            user_orgs = restrict_to_user_organization(self.user)
            base_filter = models.Q(
                status__in=['DRAFT', 'PENDING'],
                current_stage__order=initial_stage_order
            )
            if user_orgs is None:
                tankhah_queryset = Tankhah.objects.filter(base_filter)
            else:
                projects = Project.objects.filter(organizations__id__in=user_orgs)
                subprojects = SubProject.objects.filter(project__in=projects)
                org_filter = models.Q(organization__id__in=user_orgs)
                project_filter = models.Q(project__in=projects)
                subproject_filter = models.Q(subproject__in=subprojects)
                tankhah_queryset = Tankhah.objects.filter(
                    base_filter & (org_filter | project_filter | subproject_filter)
                ).distinct()

            tankhah_queryset = tankhah_queryset.select_related('organization', 'project', 'subproject', 'current_stage')
            self.fields['tankhah'].queryset = tankhah_queryset
            logger.info(f"User {self.user.username}: Tankhah queryset count = {tankhah_queryset.count()}")

        # تنظیم مقدار اولیه تنخواه
        if self.tankhah_instance:
            if tankhah_queryset.filter(pk=self.tankhah_instance.pk).exists():
                self.initial['tankhah'] = self.tankhah_instance
            else:
                logger.warning(
                    f"Passed tankhah instance (pk={self.tankhah_instance.pk}) is not in the valid queryset for user {self.user.username}")

        # تنظیم تاریخ پیش‌فرض به امروز (جلالی) اگر مقدار اولیه وجود نداشته باشد
        if not self.initial.get('date'):
            try:
                today_jalali = jdatetime.date.today().strftime('%Y/%m/%d')
                self.initial['date'] = today_jalali
                logger.debug(f"Set default date to today: {today_jalali}")
            except Exception as e:
                logger.error(f"Error setting default Jalali date: {e}")

    def clean_date(self):
        """تبدیل تاریخ جلالی به میلادی."""
        date_str = self.cleaned_data.get('date')
        if not date_str:
            logger.error("Date is empty")
            raise forms.ValidationError('وارد کردن تاریخ الزامی است.')
        try:
            date_str = to_english_digits(date_str)
            parsed_date = parse_jalali_date(date_str, field_name='تاریخ')
            logger.debug(f"Parsed date: Jalali='{date_str}', Gregorian='{parsed_date}'")
            return parsed_date
        except Exception as e:
            logger.error(f"Error parsing date: {date_str}, Error: {e}")
            raise forms.ValidationError('فرمت تاریخ نامعتبر است. از فرمت YYYY/MM/DD استفاده کنید (مثال: 1403/01/17).')

    def clean_amount(self):
        """اعتبارسنجی مبلغ."""
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError('وارد کردن مبلغ کل فاکتور الزامی است.')
        if not isinstance(amount, Decimal):
            raise forms.ValidationError('مقدار نامعتبر برای مبلغ.')
        # if amount <= Decimal('0'):
        #     raise forms.ValidationError('مبلغ کل فاکتور باید بزرگتر از صفر باشد.')
        return amount

    def clean(self):
        """اعتبارسنجی کلی فرم."""
        cleaned_data = super().clean()
        return cleaned_data
# ====

# --- Form for Factor Items (used in Formset) ---
class FactorItemForm(forms.ModelForm):
    class Meta:
        model = FactorItem
        fields = ['description', 'quantity', 'unit_price'] # Exclude 'amount' and 'factor'
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'required': 'required'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm ltr-input quantity-field', 'step': 'any', 'min': '0.01', 'required': 'required'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control form-control-sm ltr-input unit-price-field', 'step': 'any', 'min': '0', 'required': 'required'}),
        }
        labels = {
            'description': _('شرح ردیف'),
            'quantity': _('تعداد/مقدار'),
            'unit_price': _('قیمت واحد (ریال)'),
        }

    def clean(self):
        """Calculate amount and perform row-level validation."""
        cleaned_data = super().clean()
        # Check if marked for deletion or essentially empty
        if cleaned_data.get('DELETE'):
            return cleaned_data

        description = cleaned_data.get('description')
        quantity = cleaned_data.get('quantity')
        unit_price = cleaned_data.get('unit_price')

        # Check if required fields are missing (should be caught by widgets but good practice)
        if not description or quantity is None or unit_price is None:
             # If form is not marked for deletion and fields are missing, it's an error
             # This might happen if 'required' is removed from widgets
             if not self.empty_permitted or self.has_changed():
                 raise forms.ValidationError(_("لطفاً تمام فیلدهای ردیف را تکمیل کنید یا ردیف را حذف کنید."), code='incomplete_row')
             else:
                 # Allow empty extra forms if nothing was entered
                 return cleaned_data


        errors = {}
        if quantity <= Decimal('0'):
            errors['quantity'] = forms.ValidationError(_('تعداد باید بزرگتر از صفر باشد.'), code='quantity_not_positive')
        if unit_price < Decimal('0'): # Allow zero price?
            errors['unit_price'] = forms.ValidationError(_('قیمت واحد نمی‌تواند منفی باشد.'), code='unit_price_negative')

        if errors:
            raise forms.ValidationError(errors)

        # Calculate amount
        calculated_amount = (quantity * unit_price).quantize(Decimal('0.01')) # Ensure 2 decimal places
        if calculated_amount <= Decimal('0'):
             # Add non-field error if calculation results in non-positive
             self.add_error(None, forms.ValidationError(_('مبلغ محاسبه شده ردیف (تعداد × قیمت) باید مثبت باشد.'), code='amount_calculated_not_positive'))
        else:
             # Store calculated amount for the view
             cleaned_data['amount'] = calculated_amount
             logger.debug(f"FactorItemForm clean: Calculated amount={calculated_amount} for desc='{description}'")

        return cleaned_data