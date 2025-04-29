# tankhah/forms.py
import logging
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import jdatetime

from tankhah.forms import MultipleFileField, MultipleFileInput
from tankhah.models import Factor, Tankhah, FactorItem
from core.models import WorkflowStage, Project,SubProject
from django.db.models import Q
from tankhah.utils import restrict_to_user_organization
from decimal import Decimal
import os

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory
from django.db.models import Q

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
                    status__in=['DRAFT', 'PENDING'],
                    current_stage__order=initial_stage_order
                )
            else:
                projects = Project.objects.filter(organizations__in=user_orgs)
                subprojects = SubProject.objects.filter(project__in=projects)
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

# from multiupload.fields import MultipleFileField, MultipleFileInput # Assuming this is used


# Assuming ALLOWED_EXTENSIONS and ALLOWED_EXTENSIONS_STR are defined elsewhere


# # --- Document Forms (Unchanged unless needed) ---
# class FactorDocumentForm(forms.Form):
#     files = MultipleFileField(
#         label=_("بارگذاری اسناد فاکتور (فقط {} مجاز است)".format(ALLOWED_EXTENSIONS_STR)),
#         required=False,
#         widget=MultipleFileInput(
#             attrs={
#                 'multiple': True,
#                 'class': 'form-control form-control-sm',
#                 'accept': ",".join(ALLOWED_EXTENSIONS)
#             }
#         )
#     )
#     # clean_files method remains the same
#
#
# class TankhahDocumentForm(forms.Form):
#     documents = MultipleFileField(
#         label=_("بارگذاری مدارک تنخواه (فقط {} مجاز است)".format(ALLOWED_EXTENSIONS_STR)),
#         required=False,
#         widget=MultipleFileInput(
#             attrs={
#                 'multiple': True,
#                 'class': 'form-control form-control-sm',
#                 'accept': ",".join(ALLOWED_EXTENSIONS)
#             }
#         )
#     )
#     # clean_documents method remains the same
#
#
# # --- Factor Form (Main form for Step 1) ---
# class FactorWizardStep1Form(forms.ModelForm): # Renamed for clarity
#     date = forms.CharField(
#         label=_('تاریخ فاکتور'), # Changed label slightly
#         required=True,
#         widget=forms.TextInput(attrs={
#             'data-jdp': '', # For Jalali datepicker
#             'class': 'form-control form-control-sm', # Use form-control-sm
#             'placeholder': _('مثال: 1404/02/09') # Simpler placeholder
#         })
#     )
#
#     class Meta:
#         model = Factor
#         # REMOVED 'amount' field - will be calculated from items
#         fields = ['tankhah', 'date', 'description']
#         widgets = {
#             'tankhah': forms.Select(attrs={'class': 'form-select form-select-sm'}), # Use form-select
#             'description': forms.Textarea(
#                 attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': _('توضیحات کلی فاکتور (اختیاری)')}),
#         }
#         labels = {
#             'tankhah': _('انتخاب تنخواه مرتبط'),
#             'date': _('تاریخ فاکتور'),
#             'description': _('توضیحات کلی'),
#         }
#
#     def __init__(self, *args, **kwargs):
#         self.user = kwargs.pop('user', None)
#         # Tankhah instance might be passed from wizard's initial data if editing
#         self.tankhah_instance = kwargs.get('initial', {}).get('tankhah')
#         super().__init__(*args, **kwargs)
#
#         # --- Filter Tankhah queryset ---
#         initial_stage = WorkflowStage.objects.order_by('order').first()
#         if not initial_stage:
#              logger.warning("No initial workflow stage found. Tankhah list might be empty.")
#              self.fields['tankhah'].queryset = Tankhah.objects.none()
#              return
#
#         initial_stage_order = initial_stage.order
#         base_queryset = Tankhah.objects.filter(
#             status__in=['DRAFT', 'PENDING'],
#             current_stage__order=initial_stage_order
#         ).select_related('project', 'subproject', 'organization') # Optimize query
#
#         if self.user:
#             user_orgs_qs = restrict_to_user_organization(self.user) # This should return a QuerySet or None
#             if user_orgs_qs is None: # Superuser or unrestricted
#                  self.fields['tankhah'].queryset = base_queryset
#             elif user_orgs_qs.exists():
#                 # Filter based on user's organizations and related projects/subprojects
#                 user_org_ids = list(user_orgs_qs.values_list('id', flat=True))
#                 projects = Project.objects.filter(organizations__in=user_org_ids)
#                 # Filter Tankhahs directly linked to user's orgs OR linked to projects in user's orgs
#                 queryset = base_queryset.filter(
#                     Q(organization__in=user_org_ids) | Q(project__in=projects)
#                 ).distinct()
#                 self.fields['tankhah'].queryset = queryset
#                 # logger.info(f"Filtered Tankhah queryset for user {self.user}: {list(queryset.values_list('id', flat=True))}")
#             else: # User has no organizations assigned
#                  self.fields['tankhah'].queryset = Tankhah.objects.none()
#         else: # Should not happen if view requires login
#             self.fields['tankhah'].queryset = Tankhah.objects.none()
#
#         # Set initial value if editing or coming back to step
#         if self.tankhah_instance:
#              self.fields['tankhah'].initial = self.tankhah_instance
#              # Ensure the instance is in the queryset if editing
#              if self.tankhah_instance not in self.fields['tankhah'].queryset:
#                   self.fields['tankhah'].queryset = (self.fields['tankhah'].queryset | Tankhah.objects.filter(pk=self.tankhah_instance.pk)).distinct()
#
#
#         # Set initial date format correctly if editing
#         if self.instance and self.instance.pk and self.instance.date:
#             # Ensure date is converted to aware datetime before formatting
#             aware_date = timezone.make_aware(self.instance.date) if timezone.is_naive(self.instance.date) else self.instance.date
#             j_date = jdatetime.date.fromgregorian(date=aware_date.date()) # Use aware_date.date()
#             self.initial['date'] = j_date.strftime('%Y/%m/%d')
#
#
#     def clean_date(self):
#         date_str = self.cleaned_data.get('date')
#         if not date_str:
#             # Error logged by required=True
#             return None
#         try:
#             # Ensure the format is correct before parsing
#             if not isinstance(date_str, str) or len(date_str.split('/')) != 3:
#                  raise ValueError("Incorrect date format string")
#             j_date = jdatetime.datetime.strptime(date_str.strip(), '%Y/%m/%d')
#             gregorian_datetime = j_date.togregorian()
#             # Make it timezone aware using Django settings timezone
#             aware_datetime = timezone.make_aware(gregorian_datetime)
#             logger.debug(f"Date '{date_str}' converted to aware datetime: {aware_datetime}")
#             return aware_datetime
#         except (ValueError, TypeError) as e:
#             logger.warning(f"Invalid date format or value: '{date_str}', Error: {e}")
#             raise forms.ValidationError(_('فرمت تاریخ نامعتبر است. لطفاً از فرمت YYYY/MM/DD استفاده کنید (مثال: 1404/02/09).'))
#
#     def clean_tankhah(self):
#          tankhah = self.cleaned_data.get('tankhah')
#          if not tankhah:
#               raise forms.ValidationError(_("انتخاب تنخواه الزامی است."))
#          # Add checks for tankhah status/stage again here if needed, although view handles it too
#          initial_stage = WorkflowStage.objects.order_by('order').first()
#          if tankhah.status not in ['DRAFT', 'PENDING'] or (initial_stage and tankhah.current_stage.order != initial_stage.order):
#                raise forms.ValidationError(_("تنخواه انتخاب شده در وضعیت یا مرحله معتبری برای ثبت فاکتور نیست."))
#          return tankhah
#
#
# # --- Factor Item Form (For Step 2 Formset) ---
# class FactorItemWizardForm(forms.ModelForm): # Renamed for clarity
#     class Meta:
#         model = FactorItem
#         fields = ['description', 'amount', 'quantity']
#         widgets = {
#             'description': forms.TextInput(
#                 attrs={'class': 'form-control form-control-sm', 'placeholder': _('شرح ردیف کالا/خدمت')}),
#             'amount': forms.NumberInput(
#                 attrs={'class': 'form-control form-control-sm ltr-input amount-field', 'step': '1', 'min': '1', 'placeholder': _('مبلغ واحد (ریال)')}), # Min should be > 0
#             'quantity': forms.NumberInput(
#                 attrs={'class': 'form-control form-control-sm ltr-input quantity-field', 'placeholder': _('تعداد'), 'min': '1'}),
#         }
#         labels = { # Optional: Add labels if needed above fields
#              'description': _('شرح'),
#              'amount': _('مبلغ واحد'),
#              'quantity': _('تعداد'),
#         }
#
#     def clean(self):
#         cleaned_data = super().clean()
#         amount = cleaned_data.get('amount')
#         quantity = cleaned_data.get('quantity')
#         description = cleaned_data.get('description', '').strip()
#
#         # Check if the form is marked for deletion by the formset management form
#         if self.prefix and cleaned_data.get(f'{self.prefix}-DELETE', False):
#             return cleaned_data # Skip validation if marked for deletion
#
#         # Determine if the form is essentially empty
#         is_empty = not description and (amount is None or amount == 0) and (quantity is None or quantity == 1)
#
#         if is_empty:
#             if not self.instance or not self.instance.pk: # Only mark new, empty forms
#                  cleaned_data['DELETE'] = True
#             return cleaned_data
#
#         # Validation for non-empty rows
#         errors = {}
#         if not description:
#             errors['description'] = ValidationError(_('شرح ردیف الزامی است.'))
#         if amount is None or amount <= 0:
#             errors['amount'] = ValidationError(_('مبلغ واحد باید بزرگ‌تر از صفر باشد.'))
#         if quantity is None or quantity < 1:
#             # Should be caught by min="1", but double-check
#             errors['quantity'] = ValidationError(_('تعداد باید حداقل ۱ باشد.'))
#
#         if errors:
#             raise ValidationError(errors)
#
#         return cleaned_data
#
# # Create the Formset for Step 2
# FactorItemWizardFormSet = forms.inlineformset_factory(
#     Factor, # Parent model
#     FactorItem, # Child model
#     form=FactorItemWizardForm,
#     extra=1, # Start with one extra empty form
#     can_delete=True, # Allow deleting rows
#     min_num=1, # Require at least one item
#     validate_min=True, # Enforce min_num validation
# )
#
# class ConfirmationForm(forms.Form):
#     pass  # فرم خالی برای مرحله تأیید

#-------------- new
# forms.py

# --- فرم مرحله ۱: انتخاب تنخواه ---
class WizardTankhahSelectionForm(forms.Form):
    # Note: We use forms.Form, not ModelForm, as we only need the selection
    tankhah = forms.ModelChoiceField(
        queryset=Tankhah.objects.none(), # Queryset set dynamically in view
        label=_('انتخاب تنخواه مرتبط'),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        empty_label=_("--- ابتدا تنخواه را انتخاب کنید ---"),
        required=True
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # --- Filter Tankhah queryset ---
        initial_stage = WorkflowStage.objects.order_by('order').first()
        if not initial_stage:
            logger.warning("Wizard: No initial workflow stage found.")
            self.fields['tankhah'].queryset = Tankhah.objects.none()
            return

        initial_stage_order = initial_stage.order
        base_queryset = Tankhah.objects.filter(
            status__in=['DRAFT', 'PENDING'],
            current_stage__order=initial_stage_order
        ).select_related('project', 'subproject', 'organization')

        # if self.user:
        #     user_orgs_qs = restrict_to_user_organization(self.user)
        #     if user_orgs_qs is None:
        #          self.fields['tankhah'].queryset = base_queryset
        #     elif user_orgs_qs.exists():
        #         user_org_ids = list(user_orgs_qs.values_list('id', flat=True))
        #         projects = Project.objects.filter(organizations__in=user_org_ids)
        #         queryset = base_queryset.filter(
        #             Q(organization__in=user_org_ids) | Q(project__in=projects)
        #         ).distinct()
        #         self.fields['tankhah'].queryset = queryset
        #     else:
        #          self.fields['tankhah'].queryset = Tankhah.objects.none()
        # else:
        #     self.fields['tankhah'].queryset = Tankhah.objects.none()

        if self.user:
            user_orgs_qs = restrict_to_user_organization(self.user)  # Now returns QuerySet or None
            logger.info(f'user_orgs_qs type: {type(user_orgs_qs)}')  # Log type

            from django.db import models
            if user_orgs_qs is None:  # Case 1: Unrestricted access
                logger.info(f"User {self.user.username} has unrestricted access.")
                self.fields['tankhah'].queryset = base_queryset

            elif isinstance(user_orgs_qs, models.QuerySet):  # Case 2: Returns a QuerySet
                if user_orgs_qs.exists():  # Now .exists() works
                    logger.info(
                        f"User {self.user.username} restricted to orgs: {list(user_orgs_qs.values_list('id', flat=True))}")
                    user_org_ids = list(user_orgs_qs.values_list('id', flat=True))
                    # Find projects WITHIN these organizations
                    projects = Project.objects.filter(organizations__id__in=user_org_ids).distinct()  # Use __id__in
                    # Filter base Tankhah queryset
                    queryset = base_queryset.filter(
                        Q(organization__id__in=user_org_ids) | Q(project__in=projects)
                    ).distinct()
                    self.fields['tankhah'].queryset = queryset
                else:  # Case 3: Empty QuerySet means no organizations assigned
                    logger.info(f"User {self.user.username} is restricted but has no organizations (empty QuerySet).")
                    self.fields['tankhah'].queryset = Tankhah.objects.none()

            else:  # Case 4: Should not happen if function is corrected
                logger.error(
                    f"Unexpected type returned from restrict_to_user_organization for user {self.user.username}: {type(user_orgs_qs)}")
                self.fields['tankhah'].queryset = Tankhah.objects.none()
        else:  # No user
            self.fields['tankhah'].queryset = Tankhah.objects.none()

    def clean_tankhah(self):
        tankhah = self.cleaned_data.get('tankhah')
        if not tankhah:
            # Should be caught by required=True, but double-check
            raise forms.ValidationError(_("انتخاب تنخواه الزامی است."))
        # Optional: Add status/stage checks here too if desired
        # initial_stage = WorkflowStage.objects.order_by('order').first()
        # if tankhah.status not in ['DRAFT', 'PENDING'] or (initial_stage and tankhah.current_stage.order != initial_stage.order):
        #       raise forms.ValidationError(_("تنخواه انتخاب شده معتبر نیست."))
        return tankhah

# --- فرم مرحله ۲: اطلاعات اصلی فاکتور ---
class WizardFactorDetailsForm(forms.Form):
    date = forms.CharField(
        label=_('تاریخ فاکتور'),
        required=True,
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control form-control-sm',
            'placeholder': _('مثال: 1404/02/09')
        })
    )
    amount = forms.DecimalField( # یا IntegerField
        label=_('مبلغ کل فاکتور'),
        required=True,
        min_value=Decimal('0.01'), # اطمینان از مثبت بودن
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': 'any'}), # یا '0.01' برای ریال
        error_messages={
            'min_value': _('مبلغ فاکتور باید مثبت باشد.'),
            'required': _('وارد کردن مبلغ فاکتور الزامی است.')
        } )
    description = forms.CharField( # Use CharField for description
        label=_('توضیحات کلی'),
        required=False, # Make optional if needed
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-sm',
            'rows': 2,
            'placeholder': _('توضیحات کلی فاکتور (اختیاری)')
        })
    )

    # Amount is calculated later, description is the main field here
    class Meta:
        model = Factor
        fields = ['date', 'amount', 'description']
        widgets = {
            'description': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': _('توضیحات کلی فاکتور (اختیاری)')}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'date': _('تاریخ فاکتور'),
            'description': _('توضیحات کلی'),
            'amount': _('مبلغ'),
        }

    def clean_date(self):
        date_str = self.cleaned_data.get('date')
        logger.debug(f"clean_date received: '{date_str}' (type: {type(date_str)})")
        if not date_str:
            raise forms.ValidationError(_('وارد کردن تاریخ الزامی است.'))
        try:
            j_date = jdatetime.datetime.strptime(str(date_str).strip(), '%Y/%m/%d')
            gregorian_datetime = j_date.togregorian()  # Keep as naive datetime

            # --- تصمیم گیری بر اساس نوع فیلد Factor.date ---
            # Option 1: If Factor.date is DateTimeField (Recommended for timezone awareness)
            aware_datetime = timezone.make_aware(gregorian_datetime)
            logger.debug(f"clean_date successfully converted '{date_str}' to aware datetime: {aware_datetime}")
            # Optional future date check
            # if aware_datetime > timezone.now():
            #     raise forms.ValidationError(_("تاریخ فاکتور نمی‌تواند در آینده باشد."))
            return aware_datetime

            # Option 2: If Factor.date is ONLY DateField
            # gregorian_date = gregorian_datetime.date()
            # logger.debug(f"clean_date successfully converted '{date_str}' to date: {gregorian_date}")
            # Optional future date check
            # if gregorian_date > timezone.localdate():
            #     raise forms.ValidationError(_("تاریخ فاکتور نمی‌تواند در آینده باشد."))
            # return gregorian_date
            # --- End Decision ---

        except (ValueError, TypeError) as e:
            logger.error(f"clean_date failed for date '{date_str}': {e}", exc_info=True)
            raise forms.ValidationError(_('فرمت تاریخ نامعتبر است (مثال: 1404/02/09).'))
        except Exception as e:
            logger.error(f"clean_date unexpected error for date '{date_str}': {e}", exc_info=True)
            raise forms.ValidationError(_('خطای ناشناخته در پردازش تاریخ.'))

    # Optional: Add clean_amount if specific cleaning is needed
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        # Add any specific validation for amount if needed
        return amount

# --- فرم مرحله ۳: آیتم‌های فاکتور (Formset) ---
class WizardFactorItemForm(forms.ModelForm):
    description = forms.CharField(
        label=_('شرح'),
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    quantity = forms.DecimalField(
        label=_('تعداد'),
        decimal_places=2,
        max_digits=10,
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm'})
    )
    amount = forms.DecimalField(
        label=_('مبلغ واحد'),
        decimal_places=2,
        max_digits=15,
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm'})
    )


    class Meta:
        model = FactorItem
        fields = ['description', 'amount', 'quantity']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': _('شرح')}),
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm ltr-input amount-field', 'step': '1', 'min': '1', 'placeholder': _('مبلغ واحد')}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm ltr-input quantity-field', 'min': '1', 'placeholder': _('تعداد')}),
        }

    def clean(self):
        # (Validation logic remains the same as previous FactorItemWizardForm)
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        quantity = cleaned_data.get('quantity')
        description = cleaned_data.get('description', '').strip()
        if self.prefix and cleaned_data.get(f'{self.prefix}-DELETE', False): return cleaned_data
        is_empty = not description and (amount is None or amount == 0) and (quantity is None or quantity == 1)
        if is_empty:
            if not self.instance or not self.instance.pk: cleaned_data['DELETE'] = True
            return cleaned_data
        errors = {}
        if not description: errors['description'] = ValidationError(_('شرح الزامی است.'))
        if amount is None or amount <= 0: errors['amount'] = ValidationError(_('مبلغ باید بزرگ‌تر از صفر باشد.'))
        if quantity is None or quantity < 1: errors['quantity'] = ValidationError(_('تعداد باید حداقل ۱ باشد.'))
        if errors: raise ValidationError(errors)

        # حذف کلید factor از داده‌های تمیز شده
        cleaned_data.pop('factor', None)

        return cleaned_data

# Define the Formset using the correct item form
# WizardFactorItemFormSet = inlineformset_factory(
#     Factor,
#     FactorItem,
#     form=WizardFactorItemForm, # Use the correct form
#     extra=1,
#     can_delete=True,
#     min_num=1,
#     validate_min=True,
# )

WizardFactorItemFormSet = inlineformset_factory(
    parent_model=Factor,
    model=FactorItem,
    form=WizardFactorItemForm,
    fields=('description', 'quantity', 'amount'),
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
    exclude=('factor',)  # حذف فیلد factor
)

ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.xls', '.xlsx']
ALLOWED_EXTENSIONS_STR = ", ".join(ALLOWED_EXTENSIONS)

# --- فرم مرحله ۴: اسناد فاکتور ---
class WizardFactorDocumentForm(forms.Form):
    # Use 'files' name consistent with previous attempts
    # files = MultipleFileField(
    #     label=_("بارگذاری اسناد فاکتور (اختیاری)"),
    #     required=False,
    #     widget=MultipleFileInput(attrs={'multiple': True, 'class': 'form-control form-control-sm', 'accept': ",".join(ALLOWED_EXTENSIONS)})
    # )
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
        # ---> دسترسی به فایل(ها) از cleaned_data <---
        # در متد clean_fieldname، مقدار فیلد در self.cleaned_data['fieldname'] موجود است
        # جنگو به طور خودکار request.FILES را پردازش و لیست فایل‌ها را اینجا قرار می‌دهد
        # حتی اگر از ویجت multiple استفاده کنید، FileField استاندارد لیستی از فایل‌ها را برمی‌گرداند
        uploaded_files_list = self.cleaned_data.get('files')
        logger.debug(f"[WizardFactorDocumentForm] clean_files: دریافت فایل‌ها: {uploaded_files_list}")

        # اگر required=False باشد و فایلی آپلود نشود، مقدار None خواهد بود
        if not uploaded_files_list:
            logger.info("[WizardFactorDocumentForm] clean_files: هیچ فایلی آپلود نشده است.")
            return [] # یا None اگر منطق شما اینطور است

        # اگر از FileField استاندارد با multiple استفاده می‌کنید، uploaded_files_list
        # باید لیستی از آبجکت‌های UploadedFile باشد.
        # اگر از یک فیلد سفارشی MultipleFileField استفاده می‌کنید، ممکن است رفتار متفاوتی داشته باشد.
        # فرض می‌کنیم از FileField استاندارد با multiple استفاده شده:
        if not isinstance(uploaded_files_list, list):
            # اگر به هر دلیلی لیست نبود (مثلا فقط یک فایل آپلود شده)، آن را در لیست بگذارید
            # این حالت معمولا با FileField استاندارد و multiple رخ نمی‌دهد
             uploaded_files_list = [uploaded_files_list]


        invalid_files = []
        valid_files = [] # لیستی برای نگهداری فایل‌های معتبر

        for uploaded_file in uploaded_files_list:
            if not uploaded_file: # پرش از آیتم‌های خالی احتمالی در لیست
                continue

            # بررسی نوع آبجکت فایل (برای اطمینان بیشتر)
            # expected_file_types = (InMemoryUploadedFile, TemporaryUploadedFile) # از django.core.files.uploadedfile
            # if not isinstance(uploaded_file, expected_file_types):
            if not hasattr(uploaded_file, 'name') or not hasattr(uploaded_file, 'size'):
                logger.error(f"Object received in clean_files is not a valid file object: {type(uploaded_file)}")
                raise ValidationError(_("خطایی در پردازش یکی از فایل‌های آپلود شده رخ داد. نوع فایل نامعتبر است."))

            # بررسی پسوند
            try:
                file_name = uploaded_file.name
                ext = os.path.splitext(file_name)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    invalid_files.append(file_name)
                    logger.warning(f"Invalid file type uploaded: {file_name} (type: {ext})")
                else:
                    # اگر فایل معتبر بود، به لیست فایل‌های معتبر اضافه کن
                    valid_files.append(uploaded_file)
            except Exception as e:
                logger.error(f"Error processing file name '{getattr(uploaded_file, 'name', 'N/A')}': {e}")
                # اضافه کردن نام فایل (اگر موجود باشد) به لیست نامعتبر
                invalid_files.append(getattr(uploaded_file, 'name', _('فایل ناشناس')))

        # اگر فایل نامعتبری وجود داشت، خطا ایجاد کن
        if invalid_files:
            invalid_files_str = ", ".join(invalid_files)
            error_msg = _("فایل(های) زیر دارای فرمت غیرمجاز هستند: {files}. فرمت‌های مجاز: {allowed}").format(
                files=invalid_files_str,
                allowed=ALLOWED_EXTENSIONS_STR
            )
            # مهم: خطا را به فیلد 'files' مرتبط کنید
            self.add_error('files', error_msg) # از raise ValidationError مستقیم استفاده نکنید
            # raise ValidationError(error_msg) # استفاده از raise باعث توقف کل اعتبارسنجی می‌شود


        # ---> لیست فایل‌های معتبر را برگردانید <---
        # این مقدار در self.cleaned_data['files'] نهایی قرار می‌گیرد
        return valid_files

# --- فرم مرحله ۵: اسناد تنخواه ---
class WizardTankhahDocumentForm(forms.Form):
    # Use 'documents' name consistent with previous attempts
    documents = MultipleFileField(
        label=_("بارگذاری مدارک جدید برای تنخواه (اختیاری)"),
        required=False,
        widget=MultipleFileInput(attrs={'multiple': True, 'class': 'form-control form-control-sm', 'accept': ",".join(ALLOWED_EXTENSIONS)})
    )

    def clean_documents(self):
        files = self.cleaned_data.get('documents')
        if files:
            # (Validation logic for extensions remains the same)
            invalid_files = []
            for uploaded_file in files:
                 if uploaded_file:
                     ext = os.path.splitext(uploaded_file.name)[1].lower()
                     if ext not in ALLOWED_EXTENSIONS:
                         invalid_files.append(uploaded_file.name)
            if invalid_files:
                 raise ValidationError(_("فرمت فایل‌های زیر غیرمجاز است: {files}").format(files=", ".join(invalid_files)))
        return files

    def clean_files(self):
        uploaded_files_list = self.cleaned_data.get('files')
        logger.debug(f"[WizardFactorDocumentForm] clean_files: دریافت فایل‌ها: {uploaded_files_list}")
        if not uploaded_files_list:
            logger.info("[WizardFactorDocumentForm] clean_files: هیچ فایلی آپلود نشده است.")
            return []

# --- فرم مرحله ۶: تأیید نهایی (بدون فیلد، فقط برای نمایش) ---
# فرم تأیید نهایی
class WizardConfirmationForm(forms.Form):
    # confirm = forms.BooleanField(label=_('تأیید نهایی'), required=True)
    pass