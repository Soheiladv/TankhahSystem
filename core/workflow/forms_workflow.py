from django import forms
from django.urls import reverse_lazy
from django_select2.forms import ModelSelect2Widget, ModelSelect2MultipleWidget

from accounts.models import CustomUser
from core.models import Status, Action, Transition, Post, Permission, Organization
from django.utils.translation import gettext_lazy as _
from django_select2.forms import ModelSelect2Widget
import logging
logger = logging.getLogger('WorkflowPermissionFormLogger')

class StatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = ['name', 'code', 'description', 'is_initial', 'is_final_approve', 'is_final_reject']

        # **تغییر کلیدی:** افزودن کلاس‌های CSS به ویجت‌ها
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': ' '}),
            'is_initial': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_final_approve': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_final_reject': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

        # کمک به تمپلیت با ارسال help_text
        help_texts = {
            'name': _('عنوان فارسی باشد (مثال: پیش نویس).'),
            'code': _('فقط حروف بزرگ انگلیسی، اعداد و آندرلاین مجاز است (مثال: PENDING_APPROVAL).'),
        }
class ActionForm(forms.ModelForm):
    class Meta:
        model = Action
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
class TransitionForm(forms.ModelForm):
    class Meta:
        model = Transition
        fields = ['name', 'entity_type', 'from_status', 'action', 'to_status']
        # **تغییر کلیدی:** افزودن کلاس‌های CSS به ویجت‌ها
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'entity_type': forms.Select(attrs={'class': 'form-select'}),
            'from_status': forms.Select(attrs={'class': 'form-select'}),
            'action': forms.Select(attrs={'class': 'form-select'}),
            'to_status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # محدود کردن گزینه‌ها به رکوردهای فعال برای جلوگیری از انتخاب موارد بازنشسته
        active_statuses = Status.objects.filter(is_active=True)
        active_actions = Action.objects.filter(is_active=True)

        self.fields['from_status'].queryset = active_statuses
        self.fields['action'].queryset = active_actions
        self.fields['to_status'].queryset = active_statuses
# Core

# class PermissionForm_OK(forms.ModelForm):
#     class Meta:
#         model = Permission
#         fields = [
#             'organization',
#             'transition',
#             'entity_type',
#             'on_status',
#             'allowed_actions',
#             'allowed_posts',
#         ]
#         widgets = {
#             'organization': forms.Select(attrs={'class': 'form-control'}),
#             'transition': forms.Select(attrs={'class': 'form-control'}),
#             'entity_type': forms.Select(attrs={'class': 'form-control'}),
#             'on_status': forms.Select(attrs={'class': 'form-control'}),
#             'allowed_actions': forms.SelectMultiple(attrs={'class': 'form-control'}),
#             'allowed_posts': forms.SelectMultiple(attrs={'class': 'form-control'}),
#         }
#         labels = {
#             'organization': 'سازمان',
#             'transition': 'گذار',
#             'entity_type': 'نوع موجودیت',
#             'on_status': 'وضعیت',
#             'allowed_actions': 'اقدامات مجاز',
#             'allowed_posts': 'پست‌های مجاز',
#         }
#
#     def __init__(self, *args, **kwargs):
#         user = kwargs.pop('user', None)  # دریافت کاربر فعلی برای فیلتر کردن
#         super().__init__(*args, **kwargs)
#
#         # فیلتر کردن سازمان‌ها بر اساس دسترسی کاربر (اختیاری)
#         if user:
#             self.fields['organization'].queryset = Organization.objects.filter(
#                 created_by=user
#             )  # فرض بر این است که کاربر فقط به سازمان‌های خودش دسترسی دارد
#
#         # فیلتر کردن گذارها و وضعیت‌ها برای محدود کردن گزینه‌ها
#         self.fields['transition'].queryset = Transition.objects.filter(is_active=True)
#         self.fields['on_status'].queryset = Status.objects.filter(is_active=True)
#         self.fields['allowed_actions'].queryset = Action.objects.filter(is_active=True)
#         self.fields['allowed_posts'].queryset = Post.objects.filter(is_active=True)
#
#     def clean(self):
#         cleaned_data = super().clean()
#         entity_type = cleaned_data.get('entity_type')
#         transition = cleaned_data.get('transition')
#         on_status = cleaned_data.get('on_status')
#
#         # اعتبارسنجی: نوع موجودیت گذار و مجوز باید یکسان باشد
#         if transition and entity_type and transition.entity_type != entity_type:
#             self.add_error('transition', 'نوع موجودیت گذار باید با نوع موجودیت مجوز یکسان باشد.')
#
#         # اعتبارسنجی: وضعیت باید با گذار سازگار باشد
#         if transition and on_status and transition.from_status != on_status:
#             self.add_error('on_status', 'وضعیت انتخاب‌شده باید با وضعیت مبدأ گذار یکسان باشد.')
#
#         return cleaned_data

# workflow/forms.py
class PermissionFormOK  (forms.ModelForm):
    pass
    #
    # class Meta:
    #     model = Permission
    #     fields = ['organization', 'transition', 'allowed_posts', 'entity_type', 'on_status', 'allowed_actions']
    #     widgets = {
    #         'allowed_posts': forms.CheckboxSelectMultiple(),
    #         'allowed_actions': forms.CheckboxSelectMultiple(),
    #     }
    #
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields['organization'].queryset = Organization.objects.filter(is_active=True)
    #     self.fields['transition'].queryset = Transition.objects.filter(is_active=True)
    #     self.fields['on_status'].queryset = Status.objects.filter(is_active=True)
    #     self.fields['allowed_posts'].queryset = Post.objects.none()  # برای شروع خالی
    #
    #     self.fields['allowed_posts'].widget.attrs.update({'class': 'form-control'})
    #     self.fields['allowed_actions'].widget.attrs.update({'class': 'form-control'})
    #
    #
    #


class PermissionForm_____(forms.ModelForm):
    class Meta:
        model = Permission
        fields = ['transition', 'allowed_posts', 'is_active']
        widgets = {
            'transition': ModelSelect2Widget(
                model='workflow.Transition',
                search_fields=['name__icontains'],
                attrs={
                    'class': 'form-control',
                    'data-placeholder': _('جستجوی گذار...'),
                    'data-minimum-input-length': 1,
                }
            ),
            'allowed_posts': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'id': 'allowed_posts'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # فیلتر گذارها بر اساس کاربر
        if user:
            self.fields['transition'].queryset = Transition.objects.filter(
                organization__created_by=user,
                is_active=True
            )

        # تنظیم پست‌های اولیه
        if self.instance.pk:
            self.fields['allowed_posts'].queryset = Post.objects.filter(
                organization=self.instance.organization,
                is_active=True
            )
        else:
            self.fields['allowed_posts'].queryset = Post.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        transition = cleaned_data.get('transition')

        if transition and not transition.is_active:
            self.add_error('transition', _('گذار انتخاب شده فعال نیست'))

        return cleaned_data


class PermissionFormccccccc(forms.ModelForm):
    """
    فرم بهینه برای ایجاد و ویرایش مجوزها.
    این فرم تنها فیلدهای ضروری را از کاربر دریافت می‌کند.
    """
    transition = forms.ModelChoiceField(
        queryset=Transition.objects.filter(is_active=True),
        label=_("انتخاب گذار (فرآیند)"),
        widget=ModelSelect2Widget(
            model=Transition,
            search_fields=['name__icontains', 'organization__name__icontains'],
            attrs={
                'data-placeholder': _('نام فرآیند یا سازمان را جستجو کنید...'),
                'data-minimum-input-length': 1,
            }
        )
    )

    allowed_posts = forms.ModelMultipleChoiceField(
        queryset=Post.objects.none(),  # در ابتدا خالی است و با جاوا اسکریپت پر می‌شود
        label=_("پست‌های مجاز برای اجرای این فرآیند"),
        widget=forms.SelectMultiple(
            attrs={'class': 'form-control', 'size': '10'}
        ),
        required=True,
        help_text=_("پس از انتخاب گذار، لیست پست‌های مرتبط با سازمان آن بارگذاری می‌شود.")
    )

    class Meta:
        model = Permission
        fields = ['transition', 'allowed_posts', 'is_active']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_active': _('فعال'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # اگر فرم در حالت ویرایش باشد (یک نمونه اولیه دارد)،
        # ما باید queryset فیلد allowed_posts را تنظیم کنیم.
        # این کار برای این است که جنگو بتواند مقادیر ذخیره شده قبلی را به درستی نمایش دهد.
        if self.instance and self.instance.pk:
            # سازمان را از گذار ذخیره شده در نمونه پیدا می‌کنیم
            organization = self.instance.transition.organization
            # و queryset را بر اساس آن تنظیم می‌کنیم
            self.fields['allowed_posts'].queryset = Post.objects.filter(
                organization=organization, is_active=True
            )

    def clean(self):
        cleaned_data = super().clean()
        transition = cleaned_data.get('transition')
        allowed_posts = cleaned_data.get('allowed_posts')

        # اعتبارسنجی نهایی در سمت سرور
        # این کار برای امنیت ضروری است، چون کاربر می‌تواند درخواست را دستکاری کند.
        if transition and allowed_posts:
            organization = transition.organization
            for post in allowed_posts:
                if post.organization != organization:
                    self.add_error(
                        'allowed_posts',
                        _("پست '{post_name}' به سازمان '{org_name}' تعلق ندارد.").format(
                            post_name=post.name, org_name=organization.name
                        )
                    )

        return cleaned_data


class PermissionFormsd(forms.ModelForm):
    """
    فرم نهایی برای ایجاد و ویرایش مجوزها، طراحی شده برای کار با AJAX.
    """
    class Meta:
        model = Permission
        # فیلد is_active را هم اضافه می‌کنیم تا در فرم قابل ویرایش باشد
        fields = ['transition', 'allowed_posts', 'is_active']
        widgets = {
            'transition': forms.Select(attrs={'class': 'form-select select2-field'}),
            'allowed_posts': forms.SelectMultiple(attrs={'class': 'form-select select2-field', 'size': '10'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'transition': _("۱. ابتدا فرآیند (گذار) مورد نظر را انتخاب کنید:"),
            'allowed_posts': _("۲. سپس پست‌های مجاز را انتخاب نمایید:"),
            'is_active': _("این مجوز فعال باشد")
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        logger.debug(f"[PermissionForm.__init__] Initializing form for user '{user if user else 'N/A'}'.")

        # کوئری‌ست اولیه گذارها را پر می‌کنیم.
        # این لیست در ابتدا می‌تواند شامل تمام گذارهای فعال باشد.
        self.fields['transition'].queryset = Transition.objects.filter(is_active=True).select_related('from_status', 'action', 'organization')
        self.fields['transition'].label_from_instance = lambda obj: f"{obj.name} ({obj.organization.name})"

        # کوئری‌ست پست‌ها در ابتدا خالی است و توسط AJAX پر خواهد شد.
        # اما اگر در حالت ویرایش باشیم، باید پست‌های انتخاب شده فعلی را به آن اضافه کنیم.
        if self.instance and self.instance.pk:
            logger.debug(f"[PermissionForm.__init__] Populating allowed_posts for existing instance PK: {self.instance.pk}")
            self.fields['allowed_posts'].queryset = self.instance.allowed_posts.all()
        else:
            self.fields['allowed_posts'].queryset = Post.objects.none()

class PermissionForm(forms.ModelForm):
    transition = forms.ModelChoiceField(
        queryset=Transition.objects.filter(is_active=True),
        label=_("گذار (فرآیند)"),
        widget=ModelSelect2Widget(
            model=Transition,
            search_fields=['name__icontains', 'from_status__name__icontains', 'to_status__name__icontains', 'organization__name__icontains'],
            attrs={
                'data-placeholder': _('نام گذار، وضعیت یا سازمان را جستجو کنید...'),
                'data-minimum-input-length': 1,
                'class': 'form-control',
                'id': 'id_transition',
            }
        )
    )

    allowed_posts = forms.ModelMultipleChoiceField(
        queryset=Post.objects.none(),
        widget=ModelSelect2MultipleWidget(
            model=Post,
            search_fields=['name__icontains', 'organization__name__icontains'],
            attrs={
                'data-placeholder': _('پست‌ها را جستجو کنید...'),
                'data-minimum-input-length': 1,
                'class': 'form-control',
                'id': 'id_allowed_posts',
                'size': '10',
            }
        ),
        label=_("پست‌های مجاز"),
        required=True,
        help_text=_("پس از انتخاب گذار، پست‌های مرتبط با سازمان آن بارگذاری می‌شود.")
    )

    class Meta:
        model = Permission
        fields = ['transition', 'allowed_posts', 'is_active']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_active': 'فعال',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # لاگ برای دیباگ
        logger.debug(f"[PermissionForm.__init__] User: {user}, Type: {type(user)}, Is authenticated: {user.is_authenticated if user else 'N/A'}")

        # فیلتر گذارها فقط اگر کاربر معتبر باشد

        if user and isinstance(user,CustomUser) and user.is_authenticated:
            logger.debug(f"[PermissionForm.__init__] Filtering transitions for user: {user.pk}")
            self.fields['transition'].queryset = Transition.objects.filter(
                organization__created_by=user, is_active=True
            ).select_related('organization', 'from_status', 'to_status', 'action').distinct()
        else:
            logger.debug("[PermissionForm.__init__] No valid user, showing all active transitions")
            self.fields['transition'].queryset = Transition.objects.filter(is_active=True).select_related('organization', 'from_status', 'to_status', 'action')

        # تنظیم پست‌ها برای حالت ویرایش
        if self.instance and self.instance.pk:
            organization = self.instance.transition.organization
            logger.debug(f"[PermissionForm.__init__] Loading posts for organization: {organization.id} ({organization.name})")
            self.fields['allowed_posts'].queryset = Post.objects.filter(
                organization=organization, is_active=True
            ).select_related('organization').distinct()

    def clean(self):
        cleaned_data = super().clean()
        transition = cleaned_data.get('transition')
        allowed_posts = cleaned_data.get('allowed_posts')

        # اعتبارسنجی گذار
        if transition and not transition.is_active:
            self.add_error('transition', 'گذار انتخاب‌شده فعال نیست.')

        # اعتبارسنجی پست‌ها
        if transition and allowed_posts:
            organization = transition.organization
            valid_posts = Post.objects.filter(organization=organization, is_active=True).distinct()
            for post in allowed_posts:
                if post not in valid_posts:
                    self.add_error(
                        'allowed_posts',
                        f"پست '{post.name}' به سازمان '{organization.name}' تعلق ندارد."
                    )

        # اعتبارسنجی یکتایی
        if transition:
            existing_perm = Permission.objects.filter(transition=transition).exclude(
                pk=self.instance.pk if self.instance else None
            )
            if existing_perm.exists():
                self.add_error('transition', 'مجوز برای این گذار قبلاً ثبت شده است.')

        return cleaned_data



class PermissionForms(forms.ModelForm):
    transition = forms.ModelChoiceField(
        queryset=Transition.objects.filter(is_active=True),
        label=_("گذار (فرآیند)"),
        widget=ModelSelect2Widget(
            model=Transition,
            search_fields=['name__icontains', 'from_status__name__icontains', 'to_status__name__icontains'],
            attrs={
                'data-placeholder': _('نام گذار یا وضعیت را جستجو کنید...'),
                'data-minimum-input-length': 1,
                'class': 'form-control',
                'id': 'id_transition',
            }
        )
    )

    allowed_posts = forms.ModelMultipleChoiceField(
        queryset=Post.objects.none(),
        widget=ModelSelect2MultipleWidget(
            model=Post,
            search_fields=['name__icontains'],
            attrs={
                'data-placeholder': _('پست‌ها را جستجو کنید...'),
                'data-minimum-input-length': 1,
                'class': 'form-control',
                'id': 'id_allowed_posts',
            }
        ),
        label=_("پست‌های مجاز"),
        required=True,
        help_text=_("پست‌های مرتبط با سازمان گذار انتخاب‌شده نمایش داده می‌شوند.")
    )

    class Meta:
        model = Permission
        fields = ['transition', 'allowed_posts', 'is_active']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_active': _("فعال"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.debug("Initializing PermissionForm")
        if self.instance and self.instance.pk and self.instance.transition:
            try:
                organization = self.instance.transition.organization
                logger.debug(f"Edit mode: Loading posts for organization {organization.id} ({organization.name})")
                self.fields['allowed_posts'].queryset = Post.objects.filter(
                    organization=organization, is_active=True
                ).distinct()
            except AttributeError as e:
                logger.error(f"Error loading posts for instance: {str(e)}")
                self.fields['allowed_posts'].queryset = Post.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        transition = cleaned_data.get('transition')
        allowed_posts = cleaned_data.get('allowed_posts')
        if transition and allowed_posts:
            try:
                organization = transition.organization
                valid_posts = Post.objects.filter(organization=organization, is_active=True).distinct()
                if not all(post in valid_posts for post in allowed_posts):
                    self.add_error(
                        'allowed_posts',
                        _("پست‌های انتخاب‌شده باید متعلق به سازمان '{org_name}' باشند.").format(
                            org_name=organization.name
                        )
                    )
            except AttributeError as e:
                logger.error(f"Error validating posts: {str(e)}")
                self.add_error('allowed_posts', _("خطا در اعتبارسنجی پست‌ها."))
        if transition:
            try:
                existing_perm = Permission.objects.filter(transition=transition).exclude(
                    pk=self.instance.pk if self.instance else None
                )
                if existing_perm.exists():
                    self.add_error('transition', _("مجوز برای این گذار قبلاً ثبت شده است."))
            except Exception as e:
                logger.error(f"Error checking permission uniqueness: {str(e)}")
                self.add_error('transition', _("خطا در بررسی یکتایی مجوز."))
        return cleaned_data