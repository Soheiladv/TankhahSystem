import logging
from decimal import Decimal

import jdatetime  # Assuming jdatetime is installed
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from Tanbakhsystem.utils import format_jalali_date, to_english_digits, parse_jalali_date
# Assuming models are in the same app or imported correctly
# from tankhah.models import Factor, FactorItem, FactorDocument, Tankhah, ItemCategory, TankhahDocument
# Assuming utility functions/models exist
from core.models import WorkflowStage, Project, SubProject  # Example paths
# Assuming budget functions exist
from tankhah.models import ItemCategory, Tankhah, Factor, FactorItem
from tankhah.utils import restrict_to_user_organization

logger = logging.getLogger(__name__)

# Helper function to convert date (can be moved to utils)
def convert_to_farsi_numbers(text):
    """Converts English digits in a string to Farsi digits."""
    mapping = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
    return str(text).translate(mapping)

class old__FactorForm (forms.ModelForm):
    date = forms.CharField(
        label=_('تاریخ فاکتور'),
        required=True,
        widget=forms.TextInput(attrs={
            'data-jdp': '', # Assuming this triggers a Jalali date picker
            'class': 'form-control form-control-sm',
            'placeholder': convert_to_farsi_numbers(_('مثال: 1403/01/17'))
        })
    )
    # Category is required based on the model
    category = forms.ModelChoiceField(
        queryset=ItemCategory.objects.all(), # Adjust queryset if needed
        label=_("دسته‌بندی هزینه"),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        empty_label=None # Ensure no empty choice if it's required
    )

    class Meta:
        model = Factor
        fields = ['tankhah', 'category', 'date', 'amount', 'description' ]
        widgets = {
            'tankhah': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm ltr-input'}),
            'description': forms.TextInput(attrs={'placeholder': 'شرح...','class': 'form-control form-control-sm', 'rows': 2}),
            }
        labels = {
            'tankhah': _('تنخواه مرتبط'),
            'date': _('تاریخ فاکتور'),
            'amount': _('مبلغ کل فاکتور (ریال)'),
            'description': _('شرح کلی فاکتور'),
            'category': _('دسته‌بندی اصلی هزینه'),
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
            if self.instance.date and not self.initial.get('date'):
                try:
                    self.initial['date'] = format_jalali_date(self.instance.date)
                    logger.debug(f"Set initial date: date={self.initial['date']}")
                except Exception as e:
                    logger.error(f"Error setting initial date for Factor {self.instance.pk}: {e}")

            # فیلتر کردن تنخواه‌ها
        try:
            initial_stage = WorkflowStage.objects.order_by('order').first()
            initial_stage_order = initial_stage.order if initial_stage else 0
            logger.debug(f"Initial stage order: {initial_stage_order}")
        except Exception as e:
            logger.error(f"Error getting initial workflow stage: {e}")
            initial_stage_order = 0

        tankhah_queryset = Tankhah.objects.none()
        if self.user:
            user_orgs = restrict_to_user_organization(self.user)
            logger.debug(f"User organizations: {user_orgs}")
            base_filter = models.Q(
                status__in=['DRAFT', 'PENDING'],
                current_stage__order=initial_stage_order
            )
            if user_orgs is None:
                tankhah_queryset = Tankhah.objects.filter(base_filter)
            else:
                from core.models import Project, SubProject
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
        """Validate that the amount is positive."""
        amount = self.cleaned_data.get('amount')
        if amount is None:
            # Should be caught by model validation, but check form-level too
            raise forms.ValidationError(_('وارد کردن مبلغ کل فاکتور الزامی است.'))
        if not isinstance(amount, Decimal):
             # If it's not Decimal after field cleaning, something is wrong
              raise forms.ValidationError(_('مقدار نامعتبر برای مبلغ.'))
        # if amount <= Decimal('0'):
        #     raise forms.ValidationError(_('مبلغ کل فاکتور باید بزرگتر از صفر باشد.'))
        return amount

    # def clean(self):
    #     """Optional: Add cross-field validation if needed."""
    #     cleaned_data = super().clean()
    #     # Example: Check if description is required for certain categories
    #     # category = cleaned_data.get('category')
    #     # description = cleaned_data.get('description')
    #     # if category and category.name == 'Other' and not description:
    #     #    self.add_error('description', _('Description required for "Other" category.'))
    #     return cleaned_data

    # این متد جدید و اصلی است
    def clean(self):
        cleaned_data = super().clean()
        tankhah = cleaned_data.get('tankhah')
        amount = cleaned_data.get('amount')

        if not tankhah or not amount:
            # اگر فیلدهای اصلی وجود ندارند، از اعتبارسنجی‌های بعدی صرف نظر کن
            return cleaned_data

        # ۱. چک کردن مرحله گردش کار تنخواه
        try:
            initial_stage = WorkflowStage.objects.order_by('order').first()
            if not initial_stage:
                raise forms.ValidationError(_('هیچ مرحله گردش کاری تعریف نشده است.'))

            if tankhah.current_stage_id != initial_stage.id:
                msg = _('فقط در مرحله اولیه ({}) می‌توانید فاکتور ثبت کنید. مرحله فعلی تنخواه: {}').format(
                    initial_stage.name, tankhah.current_stage.name
                )
                raise forms.ValidationError(msg)
        except Exception as e:
            logger.error(f"Error validating workflow stage in FactorForm for tankhah {tankhah.number}: {e}")
            raise forms.ValidationError(_('خطا در بررسی مرحله گردش کار تنخواه.'))

        # ۲. چک کردن وضعیت تنخواه
        if tankhah.status not in ['DRAFT', 'PENDING']:
            raise forms.ValidationError(
                _('فقط برای تنخواه‌های در وضعیت پیش‌نویس یا در انتظار می‌توانید فاکتور ثبت کنید.'))

        # ۳. چک کردن تخصیص بودجه و دوره بودجه
        from budgets.models import BudgetAllocation
        try:
            budget_allocation = tankhah.project_budget_allocation
            if not budget_allocation or not budget_allocation.is_active:
                raise forms.ValidationError(_('تخصیص بودجه معتبر یا فعال برای این تنخواه یافت نشد.'))

            # ۴. چک کردن قفل بودن دوره بودجه (منطق اصلاح شده)
            is_period_locked, lock_reason = budget_allocation.budget_period.is_locked
            if is_period_locked:
                raise forms.ValidationError(lock_reason)

        except BudgetAllocation.DoesNotExist:
            raise forms.ValidationError(_('تخصیص بودجه معتبر برای این تنخواه یافت نشد.'))
        except Exception as e:
            logger.error(f"Error during budget validation in FactorForm for tankhah {tankhah.number}: {e}")
            raise forms.ValidationError(_('خطا در بررسی وضعیت بودجه.'))

        # ۵. چک کردن باقی‌مانده بودجه تنخواه
        try:
            from budgets.budget_calculations import get_tankhah_remaining_budget
            tankhah_remaining = get_tankhah_remaining_budget(tankhah)
            if amount > tankhah_remaining:
                msg = _('مبلغ فاکتور ({:,.0f} ریال) از بودجه باقی‌مانده تنخواه ({:,.0f} ریال) بیشتر است.').format(
                    amount, tankhah_remaining
                )
                raise forms.ValidationError(msg)
        except Exception as e:
            logger.error(f"Error getting remaining tankhah budget in FactorForm: {e}")
            raise forms.ValidationError(_('خطا در بررسی بودجه تنخواه.'))

        unit_price = cleaned_data.get('unit_price', Decimal('0'))
        quantity = cleaned_data.get('quantity', Decimal('0'))
        cleaned_data['amount'] = (unit_price * quantity).quantize(Decimal('0.01'))
        logger.debug(
            f"FactorItemForm clean: Calculated amount={cleaned_data['amount']} for desc='{cleaned_data.get('description')}'")
        return cleaned_data


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
        tankhah_queryset = Tankhah.objects.filter(is_archived=False)
        if self.user and not self.user.is_superuser:
            # user_orgs = restrict_to_user_organization(self.user, 'id')
            user_orgs = restrict_to_user_organization(self.user)
            tankhah_queryset = tankhah_queryset.filter(organization__id__in=user_orgs)

        self.fields['tankhah'].queryset = tankhah_queryset.select_related('organization', 'project', 'current_stage')

        if self.tankhah_instance:
            self.initial['tankhah'] = self.tankhah_instance
            self.fields['tankhah'].disabled = True

        if not self.initial.get('date'):
            self.initial['date'] = jdatetime.date.today().strftime('%Y/%m/%d')

        if self.instance and self.instance.pk:
            if self.instance.date:
                self.initial['date'] = format_jalali_date(self.instance.date)

    def clean_date(self):
        date_str = self.cleaned_data.get('date')
        if not date_str:
            raise forms.ValidationError(_('وارد کردن تاریخ الزامی است.'))
        try:
            return parse_jalali_date(date_str)
        except Exception:
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

        if not tankhah:
            return cleaned_data

        # ۱. چک کردن مرحله گردش کار تنخواه
        try:
            initial_stage = WorkflowStage.objects.filter(is_active=True).order_by('order').first()
            if not initial_stage:
                raise forms.ValidationError(_('هیچ مرحله گردش کاری تعریف نشده است.'))
            if tankhah.current_stage_id != initial_stage.id:
                msg = _('فقط در مرحله اولیه ({}) می‌توانید فاکتور ثبت کنید. مرحله فعلی تنخواه: {}').format(
                    initial_stage.name, tankhah.current_stage.name
                )
                raise forms.ValidationError(msg)
        except Exception as e:
            logger.error(f"Error validating workflow stage in FactorForm for tankhah {tankhah.number}: {e}")
            raise forms.ValidationError(_('خطا در بررسی مرحله گردش کار تنخواه.'))

        # ۲. چک کردن وضعیت تنخواه
        if tankhah.status not in ['DRAFT', 'PENDING']:
            raise forms.ValidationError(
                _('فقط برای تنخواه‌های در وضعیت پیش‌نویس یا در انتظار می‌توانید فاکتور ثبت کنید.'))

        # ۳. چک کردن تخصیص بودجه و دوره بودجه
        from budgets.models import BudgetAllocation
        try:
            budget_allocation = tankhah.project_budget_allocation
            if not budget_allocation or not budget_allocation.is_active:
                raise forms.ValidationError(_('تخصیص بودجه معتبر یا فعال برای این تنخواه یافت نشد.'))

            # ۴. چک کردن قفل بودن دوره بودجه (منطق اصلاح شده)
            is_period_locked, lock_reason = budget_allocation.budget_period.is_locked
            if is_period_locked:
                # به جای `add_error` از `ValidationError` استفاده می‌کنیم تا به صورت مرکزی مدیریت شود
                raise forms.ValidationError(lock_reason)

        except BudgetAllocation.DoesNotExist:
            raise forms.ValidationError(_('تخصیص بودجه معتبر برای این تنخواه یافت نشد.'))

        return cleaned_data


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
            initial_stage = WorkflowStage.objects.order_by('order').first()
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
