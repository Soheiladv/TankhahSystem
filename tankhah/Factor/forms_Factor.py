# tankhah/forms.py
import logging
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import jdatetime
from budgets.budget_calculations import get_tankhah_remaining_budget
from tankhah.forms import MultipleFileField, MultipleFileInput
from tankhah.models import Factor, Tankhah, FactorItem, ItemCategory
from core.models import Status, Project, SubProject, Post
from django.db.models import Q

from tankhah.utils import restrict_to_user_organization
logger = logging.getLogger('tankhah')

class W_FactorForm(forms.ModelForm):
    date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('1404/01/17'),
        })
    )

    class Meta:
        model = Factor
        fields = ['tankhah', 'date', 'amount', 'description']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control ltr-input', 'step': '1', 'min': '0'}),
            'tankhah': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('توضیحات فاکتور')}),
        }
        labels = {
            'tankhah': _('تنخواه'),
            'date': _('تاریخ'),
            'amount': _('مبلغ'),
            'description': _('توضیحات'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.tankhah = kwargs.pop('tankhah', None)
        super().__init__(*args, **kwargs)
        initial_stage_order = WorkflowStage.objects.order_by('order').first().order if WorkflowStage.objects.exists() else None

        if self.user:
            user_orgs = self.user.organizations.all()
            if not user_orgs:
                self.fields['tankhah'].queryset = Tankhah.objects.filter(
                    status__code=['DRAFT', 'PENDING'],
                    current_stage__order=initial_stage_order
                )
            else:
                projects = Project.objects.filter(organizations__in=user_orgs)
                subprojects = SubProject.objects.filter(project__in=projects)
                queryset = Tankhah.objects.filter(
                    status__code=['DRAFT', 'PENDING'],
                    current_stage__order=initial_stage_order,
                    is_archived=False,
                    canceled=False,
                    is_locked=False
                ).filter(
                    Q(organization__in=user_orgs) |
                    Q(project__in=projects) |
                    Q(subproject__in=subprojects)
                ).filter(
                    Q(due_date__isnull=True) | Q(due_date__date__gte=timezone.now().date())
                ).filter(
                    remaining_budget__gt=0
                ).distinct()
                self.fields['tankhah'].queryset = queryset
                logger.info(f"Tankhah queryset: {list(queryset.values('number', 'project__name', 'subproject__name'))}")

        if self.tankhah:
            self.fields['tankhah'].initial = self.tankhah
            self.fields['tankhah'].disabled = True

        if self.instance.pk and self.instance.date:
            j_date = jdatetime.date.fromgregorian(date=self.instance.date)
            self.fields['date'].initial = j_date.strftime('%Y/%m/%d')

    def clean_date(self):
        date_str = self.cleaned_data.get('date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ فاکتور اجباری است.'))
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
            gregorian_date = j_date.togregorian()
            return timezone.make_aware(gregorian_date)
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError(_('وارد کردن مبلغ الزامی است.'))
        if amount <= 0:
            raise forms.ValidationError(_('مبلغ باید بزرگ‌تر از صفر باشد.'))
        return amount

    def clean(self):
        cleaned_data = super().clean()
        description = cleaned_data.get('description')
        if description and description.isdigit():
            raise forms.ValidationError(_('توضیحات نمی‌تواند فقط عدد باشد.'))
        logger.info(f"Validated data: {cleaned_data}")
        return cleaned_data


class W_FactorItemForm(forms.ModelForm):
    class Meta:
        model = FactorItem
        fields = ['description', 'amount', 'quantity']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': _('شرح ردیف'),
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm ltr-input amount-field',
                'step': '1',
                'min': '0',
                'placeholder': _('مبلغ'),
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm ltr-input quantity-field',
                'min': '1',
                'placeholder': _('تعداد'),
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        description = cleaned_data.get('description')
        amount = cleaned_data.get('amount')
        quantity = cleaned_data.get('quantity')

        if not description and (amount is None or amount == 0) and (quantity is None or quantity == 1):
            cleaned_data['DELETE'] = True
            return cleaned_data

        if not description:
            raise forms.ValidationError(_('شرح ردیف الزامی است.'))
        if description.isdigit():
            raise forms.ValidationError(_('شرح ردیف نمی‌تواند فقط عدد باشد.'))
        if amount is None or amount <= 0:
            raise forms.ValidationError(_('مبلغ باید بزرگ‌تر از صفر باشد.'))
        if quantity is None or quantity < 1:
            raise forms.ValidationError(_('تعداد باید حداقل ۱ باشد.'))
        return cleaned_data

def get_factor_item_formset():
    return forms.formset_factory(W_FactorForm , extra=1, can_delete=True)

# Assuming ALLOWED_EXTENSIONS and ALLOWED_EXTENSIONS_STR are defined elsewhere
ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.xls', '.xlsx']
ALLOWED_EXTENSIONS_STR = ", ".join(ALLOWED_EXTENSIONS)


# --- Factor Form (Main form for Step 1) ---
class FactorWizardStep1Form(forms.ModelForm): # Renamed for clarity
    date = forms.CharField(
        label=_('تاریخ فاکتور'), # Changed label slightly
        required=True,
        widget=forms.TextInput(attrs={
            'data-jdp': '', # For Jalali datepicker
            'class': 'form-control form-control-sm', # Use form-control-sm
            'placeholder': _('مثال: 1404/02/09') # Simpler placeholder
        })
    )

    class Meta:
        model = Factor
        # REMOVED 'amount' field - will be calculated from items
        fields = ['tankhah', 'date', 'description']
        widgets = {
            'tankhah': forms.Select(attrs={'class': 'form-select form-select-sm'}), # Use form-select
            'description': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': _('توضیحات کلی فاکتور (اختیاری)')}),
        }
        labels = {
            'tankhah': _('انتخاب تنخواه مرتبط'),
            'date': _('تاریخ فاکتور'),
            'description': _('توضیحات کلی'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        # Tankhah instance might be passed from wizard's initial data if editing
        self.tankhah_instance = kwargs.get('initial', {}).get('tankhah')
        super().__init__(*args, **kwargs)

        # --- Filter Tankhah queryset ---
        initial_stage = WorkflowStage.objects.order_by('order').first()
        if not initial_stage:
             logger.warning("No initial workflow stage found. Tankhah list might be empty.")
             self.fields['tankhah'].queryset = Tankhah.objects.none()
             return

        initial_stage_order = initial_stage.order
        base_queryset = Tankhah.objects.filter(
            status__code=['DRAFT', 'PENDING'],
            current_stage__order=initial_stage_order,
            is_archived=False,
            canceled=False,
            is_locked=False
        ).filter(
            Q(due_date__isnull=True) | Q(due_date__date__gte=timezone.now().date())
        ).filter(
            remaining_budget__gt=0
        ).select_related('project', 'subproject', 'organization') # Optimize query

        if self.user:
            user_orgs_qs = restrict_to_user_organization(self.user) # This should return a QuerySet or None
            if user_orgs_qs is None: # Superuser or unrestricted
                 self.fields['tankhah'].queryset = base_queryset
            elif user_orgs_qs.exists():
                # Filter based on user's organizations and related projects/subprojects
                user_org_ids = list(user_orgs_qs.values_list('id', flat=True))
                projects = Project.objects.filter(organizations__in=user_org_ids)
                # Filter Tankhahs directly linked to user's orgs OR linked to projects in user's orgs
                queryset = base_queryset.filter(
                    Q(organization__in=user_org_ids) | Q(project__in=projects)
                ).distinct()
                self.fields['tankhah'].queryset = queryset
                # logger.info(f"Filtered Tankhah queryset for user {self.user}: {list(queryset.values_list('id', flat=True))}")
            else: # User has no organizations assigned
                 self.fields['tankhah'].queryset = Tankhah.objects.none()
        else: # Should not happen if view requires login
            self.fields['tankhah'].queryset = Tankhah.objects.none()

        # Set initial value if editing or coming back to step
        if self.tankhah_instance:
             self.fields['tankhah'].initial = self.tankhah_instance
             # Ensure the instance is in the queryset if editing
             if self.tankhah_instance not in self.fields['tankhah'].queryset:
                  self.fields['tankhah'].queryset = (self.fields['tankhah'].queryset | Tankhah.objects.filter(pk=self.tankhah_instance.pk)).distinct()


        # Set initial date format correctly if editing
        if self.instance and self.instance.pk and self.instance.date:
            # Ensure date is converted to aware datetime before formatting
            aware_date = timezone.make_aware(self.instance.date) if timezone.is_naive(self.instance.date) else self.instance.date
            j_date = jdatetime.date.fromgregorian(date=aware_date.date()) # Use aware_date.date()
            self.initial['date'] = j_date.strftime('%Y/%m/%d')


    def clean_date(self):
        date_str = self.cleaned_data.get('date')
        if not date_str:
            # Error logged by required=True
            return None
        try:
            # Ensure the format is correct before parsing
            if not isinstance(date_str, str) or len(date_str.split('/')) != 3:
                 raise ValueError("Incorrect date format string")
            j_date = jdatetime.datetime.strptime(date_str.strip(), '%Y/%m/%d')
            gregorian_datetime = j_date.togregorian()
            # Make it timezone aware using Django settings timezone
            aware_datetime = timezone.make_aware(gregorian_datetime)
            logger.debug(f"Date '{date_str}' converted to aware datetime: {aware_datetime}")
            return aware_datetime
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid date format or value: '{date_str}', Error: {e}")
            raise forms.ValidationError(_('فرمت تاریخ نامعتبر است. لطفاً از فرمت YYYY/MM/DD استفاده کنید (مثال: 1404/02/09).'))

    def clean_tankhah(self):
         tankhah = self.cleaned_data.get('tankhah')
         if not tankhah:
              raise forms.ValidationError(_("انتخاب تنخواه الزامی است."))
         # Add checks for tankhah status/stage again here if needed, although view handles it too
         initial_stage = WorkflowStage.objects.order_by('order').first()
         if tankhah.status not in ['DRAFT', 'PENDING'] or (initial_stage and tankhah.current_stage.order != initial_stage.order):
               raise forms.ValidationError(_("تنخواه انتخاب شده در وضعیت یا مرحله معتبری برای ثبت فاکتور نیست."))
         return tankhah
# --- Factor Item Form (For Step 2 Formset) ---
class FactorItemWizardForm(forms.ModelForm): # Renamed for clarity
    class Meta:
        model = FactorItem
        fields = ['description', 'amount', 'quantity']
        widgets = {
            'description': forms.TextInput(
                attrs={'class': 'form-control form-control-sm', 'placeholder': _('شرح ردیف کالا/خدمت')}),
            'amount': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm ltr-input amount-field', 'step': '1', 'min': '1', 'placeholder': _('مبلغ واحد (ریال)')}), # Min should be > 0
            'quantity': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm ltr-input quantity-field', 'placeholder': _('تعداد'), 'min': '1'}),
        }
        labels = { # Optional: Add labels if needed above fields
             'description': _('شرح'),
             'amount': _('مبلغ واحد'),
             'quantity': _('تعداد'),
        }

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        quantity = cleaned_data.get('quantity')
        description = cleaned_data.get('description', '').strip()

        # Check if the form is marked for deletion by the formset management form
        if self.prefix and cleaned_data.get(f'{self.prefix}-DELETE', False):
            return cleaned_data # Skip validation if marked for deletion

        # Determine if the form is essentially empty
        is_empty = not description and (amount is None or amount == 0) and (quantity is None or quantity == 1)

        if is_empty:
            if not self.instance or not self.instance.pk: # Only mark new, empty forms
                 cleaned_data['DELETE'] = True
            return cleaned_data

        # Validation for non-empty rows
        errors = {}
        if not description:
            errors['description'] = ValidationError(_('شرح ردیف الزامی است.'))
        if amount is None or amount <= 0:
            errors['amount'] = ValidationError(_('مبلغ واحد باید بزرگ‌تر از صفر باشد.'))
        if quantity is None or quantity < 1:
            # Should be caught by min="1", but double-check
            errors['quantity'] = ValidationError(_('تعداد باید حداقل ۱ باشد.'))

        if errors:
            raise ValidationError(errors)

        return cleaned_data
# Create the Formset for Step 2
FactorItemWizardFormSet = forms.inlineformset_factory(
    Factor, # Parent model
    FactorItem, # Child model
    form=FactorItemWizardForm,
    extra=1, # Start with one extra empty form
    can_delete=True, # Allow deleting rows
    min_num=1, # Require at least one item
    validate_min=True, # Enforce min_num validation
)


class FactorForm(forms.ModelForm):
    date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('1404/01/17'),
        })
    )

    class Meta:
        model = Factor
        fields = ['tankhah', 'date', 'amount', 'description', 'is_emergency', 'category']
        widgets = {
            'tankhah': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'placeholder': _('توضیحات فاکتور')}),
            'is_emergency': forms.CheckboxInput(
                attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'tankhah': _('تنخواه'),
            'date': _('تاریخ'),
            'amount': _('مبلغ کل'),
            'description': _('توضیحات'),
            'category': _('دسته‌بندی'),
            'is_emergency': _('اضطراری'),
        }

    def clean_date(self):
        date_str = self.cleaned_data.get('date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ فاکتور اجباری است.'))
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
            gregorian_date = j_date.togregorian()
            return timezone.make_aware(gregorian_date)
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.tankhah = kwargs.pop('tankhah', None)
        self.formset = kwargs.pop('formset', None)
        super().__init__(*args, **kwargs)
        if self.tankhah:
            self.fields['tankhah'].initial = self.tankhah
            self.fields['tankhah'].queryset = Tankhah.objects.filter(id=self.tankhah.id)
        else:
            self.fields['tankhah'].queryset = Tankhah.objects.filter(status__code=['DRAFT', 'PENDING'])
        self.fields['category'].queryset = ItemCategory.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        formset = self.formset

        if not formset:
            raise forms.ValidationError(_('فرم‌ست آیتم‌ها در دسترس نیست.'))

        items_total = Decimal('0')
        item_errors = []
        for i, form in enumerate(formset):
            if not form.is_valid():
                item_errors.append(f"آیتم {i+1}: {form.errors}")
                logger.warning(f"Invalid item form {i+1}: {form.errors}")
                continue
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                unit_price = form.cleaned_data.get('unit_price', Decimal('0'))
                quantity = form.cleaned_data.get('quantity', 0)
                item_total = unit_price * Decimal(quantity)
                items_total += item_total
                logger.info(f"FactorItemForm: Calculated amount: {item_total}")

        if item_errors:
            raise forms.ValidationError(item_errors)

        if amount is not None and abs(amount - items_total) > 0.01:
            logger.warning(f"Factor: amount ({amount}) != items total ({items_total})")
            raise forms.ValidationError(
                _("مبلغ فاکتور (%(amount)s) با مجموع آیتم‌ها (%(items_total)s) همخوانی ندارد."),
                params={'amount': amount, 'items_total': items_total}
            )

        tankhah = cleaned_data.get('tankhah')
        if tankhah and amount:
            remaining_budget = get_tankhah_remaining_budget(tankhah)
            if amount > remaining_budget:
                raise forms.ValidationError(
                    _("مبلغ فاکتور (%(amount)s) بیشتر از بودجه باقی‌مانده تنخواه (%(remaining)s) است."),
                    params={'amount': amount, 'remaining': remaining_budget}
                )

        return cleaned_data

class FactorItemForm(forms.ModelForm):
    class Meta:
        model = FactorItem
        fields = ['description', 'unit_price', 'quantity']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        unit_price = cleaned_data.get('unit_price')
        quantity = cleaned_data.get('quantity')
        description = cleaned_data.get('description')

        if not description:
            raise forms.ValidationError({"description": _("شرح ردیف اجباری است.")})
        if unit_price is None or unit_price < 0:
            raise forms.ValidationError({"unit_price": _("قیمت واحد باید وارد شود و نمی‌تواند منفی باشد.")})
        if quantity is None or quantity <= 0:
            raise forms.ValidationError({"quantity": _("تعداد باید وارد شود و باید مثبت باشد.")})

        cleaned_data['amount'] = unit_price * Decimal(str(quantity))
        logger.info(f"FactorItemForm: Calculated amount: {cleaned_data['amount']}")
        return cleaned_data


FactorItemFormSet = forms.inlineformset_factory(
    Factor, # Parent model
    FactorItem, # Child model
    form=FactorItemWizardForm,
    extra=1, # Start with one extra empty form
    can_delete=True, # Allow deleting rows
    min_num=1, # Require at least one item
    validate_min=True, # Enforce min_num validation
    # inlineformset_factory(
    # prefix='items'
)


#
# FactorItemFormSet = modelformset_factory(
#     FactorItem,
#     form=FactorItemForm,
#     extra=1,
#     min_num=1,
#     validate_min=True,
#     can_delete=True  # اگر بخواهی حذف آیتم را هم فعال کنی
# )
# --- Document Forms (Unchanged unless needed) ---
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
    # clean_files method remains the same

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
    # clean_documents method remains the same



