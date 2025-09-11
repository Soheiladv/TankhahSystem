import datetime
import logging

from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_jalali.admin.widgets import AdminjDateWidget

from BudgetsSystem.base import JalaliDateForm
from BudgetsSystem.utils import convert_to_farsi_numbers, convert_jalali_to_gregorian, convert_gregorian_to_jalali
from accounts.models import CustomProfile, CustomUser, City, Province, CustomUserGroup
from .models import MyGroup, Role


class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)
    group = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), widget=forms.CheckboxSelectMultiple,
                                           required=False
                                           )
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),  # فرض کرده‌ایم که مدلی بنام Role دارید
        required=False,
        empty_label="بدون نقش"
    )

    class Meta:
        model = CustomUser
        # fields = '__all__'
        fields = ('username', 'email', 'first_name', 'last_name', 'groups')

        widgets = {
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),

        }

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'رمز عبور'})
        self.fields['password2'].widget = forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'تکرار رمز عبور'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
class AssignRoleForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=CustomUser.objects.all(),
        label="کاربر",
        widget=forms.Select(attrs={'class': 'form-control', 'placeholder': 'انتخاب کاربر'})
    )
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-control'}),
        label="انتخاب نقش‌ها"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not 'class' in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control mb-3'
class UniqueGroupValidator:
    def __init__(self, exclude=None):
        self.exclude = exclude

    def __call__(self, value):
        if MyGroup.objects.filter(name__iexact=value).exclude(id=self.exclude).exists():
            raise ValidationError(
                _("گروه با این نام قبلاً ثبت شده است."),
                code='unique'
            )
# برای مدیریت گروه‌ها از این فرم جداگانه استفاده کنید
class UserGroupForm(forms.Form):
    users = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        label=_("کاربران"),
        required=False
    )

    def __init__(self, *args, **kwargs):
        group = kwargs.pop('group', None)
        super().__init__(*args, **kwargs)
        if group:
            initial = kwargs.get('initial', {})
            initial['users'] = CustomUser.objects.filter(customusergroup__mygroup=group)
            self.initial = initial

    def save(self, group):
        # حذف همه کاربران فعلی از گروه
        CustomUserGroup.objects.filter(mygroup=group).delete()
        # اضافه کردن کاربران جدید
        for user in self.cleaned_data['users']:
            CustomUserGroup.objects.create(mygroup=group, customuser=user)
class MyGroupForm(forms.ModelForm):
    class Meta:
        model = MyGroup
        fields = ['name', 'roles', 'description', ]  # 'users',
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('نام گروه را وارد کنید')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('توضیحات گروه')}),
            'roles': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['roles'].queryset = Role.objects.all()
        # self.fields['users'].queryset = get_user_model().objects.all()
        self.fields['name'].widget.attrs.update({'class': 'form-control', 'placeholder': _('نام گروه را وارد کنید')})

    def clean_users(self):
        users = self.cleaned_data['users']
        if not users:
            raise forms.ValidationError(_("حداقل یک کاربر باید به گروه اضافه شود."))

        # بررسی برای کاربران غیرفعال
        inactive_users = [user for user in users if not user.is_active]
        if inactive_users:
            raise forms.ValidationError(_("کاربران غیرفعال نمی‌توانند به گروه اضافه شوند: %s") % ', '.join(
                [user.username for user in inactive_users]))

        return users

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        form.save_m2m()  # ذخیره روابط M2M

        form = MyGroupForm(data={'name': 'tesret', 'admin': [1, 2, 3]})
        if form.is_valid():
            print('Is Ok ')
            form.save()
        else:
            print(form.errors)
#################################
class CustomUserForm(forms.ModelForm):
    # role = forms.ModelChoiceField(queryset=Role.objects.all(), required=False)
    password1 = forms.CharField(label="رمز عبور جدید", widget=forms.PasswordInput, required=False)
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('نقش‌ها')
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=MyGroup.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('گروه‌ها')
    )

    password2 = forms.CharField(label="تکرار رمز عبور جدید", widget=forms.PasswordInput, required=False)

    class Meta:
        model = CustomUser
        # fields = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser')
        fields = ['username', 'email', 'first_name', 'last_name',
                  'is_active', 'is_staff', 'is_superuser', 'roles',
                  'groups']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1", "")
        password2 = cleaned_data.get("password2", "")
        if password1 or password2:
            if password1 != password2:
                raise forms.ValidationError("رمزهای عبور وارد شده مطابقت ندارند.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password1 = self.cleaned_data.get("password1", "")
        if password1:
            user.set_password(password1)
        if commit:
            user.save()
        return user
class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label='پسورد فعلی')
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label='پسورد جدید')
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}),
                                    label='تأیید پسورد جدید')
class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        # fields = '__all__'
        fields = ('username', 'email', 'is_active', 'is_staff', 'is_superuser',
                  'user_permissions')  # فیلدهای قابل ویرایش 'groups',

        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام کاربری'}),
            # Placeholder فارسی
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ایمیل'}),  # Placeholder فارسی
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام'}),  # Placeholder فارسی
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام خانوادگی'}),
            # Placeholder فارسی
            'groups': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),  # برای چک‌باکس‌های Bootstrap
            'is_active': forms.CheckboxInput(
                attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # اضافه کردن کلاس form-control به فیلدها
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            # تنظیم فیلد ManyToMany با مقادیر انتخاب‌شده
            instance.groups.set(self.cleaned_data['groups'])
        return instance

class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ['name', 'permissions', 'description', 'parent', ]
        widgets = {
            'name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'عنوان نقش', 'aria-label': 'عنوان نقش', }),
            'permissions': forms.SelectMultiple(attrs={'class': 'form-control'}),  # استفاده از CheckboxSelectMultiple
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 1, 'placeholder': 'توضیحات نقش',
                                                 'aria-label': 'توضیحات نقش', }),
            'parent': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['permissions'].queryset = Permission.objects.select_related('content_type').all()
        self.fields['parent'].queryset = Role.objects.all()
###############################################             #########################################
'''برای انتقال وابستگی‌ها به نقش دیگر، یک فرم ایجاد کنید:
'''
class TransferRoleDependenciesForm(forms.Form):
    new_role = forms.ModelChoiceField(queryset=Role.objects.none(), label="انتقال به نقش")

    def __init__(self, *args, **kwargs):
        role_id = kwargs.pop('role_id')
        super().__init__(*args, **kwargs)
        self.fields['new_role'].queryset = Role.objects.exclude(id=role_id)
#######################################################################################################
class AssignRolesToUserForm(forms.Form):
    user = forms.ModelChoiceField(queryset=CustomUser.objects.all(), widget=forms.Select(attrs={
        'class': 'form-control',
        'placeholder': 'انتخاب کاربر',
    }))
    roles = forms.ModelMultipleChoiceField(queryset=Role.objects.all(), widget=forms.SelectMultiple(attrs={
        'class': 'form-control',
    }))

    # groups = forms.ModelMultipleChoiceField(queryset=MyGroup.objects.all(), widget=forms.SelectMultiple(attrs={
    #     'class': 'form-control',
    # }))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تنظیم فونت آوسام برای آیکن‌ها
        self.fields['user'].widget.attrs['class'] = 'form-control'
        self.fields['roles'].widget.attrs['class'] = 'form-control'
        # self.fields['groups'].widget.attrs['class'] = 'form-control'
class AssignRolesToGroupForm(forms.Form):
    group = forms.ModelChoiceField(queryset=MyGroup.objects.all(), widget=forms.Select(attrs={
        'class': 'form-control',
        'placeholder': 'انتخاب گروه',
    }))
    roles = forms.ModelMultipleChoiceField(queryset=Role.objects.all(), widget=forms.SelectMultiple(attrs={
        'class': 'form-control',
    }))
###########################
from django.contrib.auth import get_user_model
User = get_user_model()
class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomProfile
        fields = ['first_name', 'last_name', 'city', 'phone_number', 'birth_date', 'address', 'location', 'bio',
                  'zip_code', 'description']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام خانوادگی'}),
            'city': forms.Select(attrs={'class': 'form-control', 'placeholder': 'شهر'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره تماس'}),
            # 'birth_date': AdminjDateWidget(attrs={'class': 'form-control', 'placeholder': 'تاریخ تولد'}),
            'birth_date': AdminjDateWidget(attrs={'class': 'jalali_date-date', 'placeholder': 'تاریخ تولد'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'آدرس'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'توضیحات'}),
            'location': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'موقعیت'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'بیوگرافی'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'کد پستی'})
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # بررسی اینکه request موجود است
        if self.request and self.request.user.is_authenticated:
            if not self.instance.pk:  # پروفایل جدید است
                self.instance.user = self.request.user
        # else:
        #     # در صورتی که کاربر وارد نشده باشد، ارور یا هندل دیگری اضافه کنید
        #     raise ValueError("کاربر وارد نشده است")

        for field in self.fields.values():
            if not 'class' in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control mb-3'

import logging

logger = logging.getLogger(__name__)
# accounts/forms.py
from django import forms
from .models import CustomProfile, City, Province
from django.utils.translation import gettext_lazy as _

class ProfileUpdateForm(JalaliDateForm):
    birth_date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': 'تاریخ را انتخاب کنید (1404/01/17)',
        }),
        required=False
    )

    class Meta:
        model = CustomProfile
        fields = ['first_name', 'last_name', 'province', 'city', 'phone_number', 'birth_date', 'address', 'description', 'location', 'bio', 'zip_code']
        widgets = {
            'address': forms.Textarea(attrs={'class': 'form-control mb-3', 'rows': 3}),
            'description': forms.Textarea(attrs={'class': 'form-control mb-3', 'rows': 2}),
            'location': forms.Textarea(attrs={'class': 'form-control mb-3', 'rows': 2}),
            'bio': forms.Textarea(attrs={'class': 'form-control mb-3', 'rows': 2}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control mb-3'}),
            'province': forms.Select(attrs={'class': 'form-control mb-3'}),
            'city': forms.Select(attrs={'class': 'form-control mb-3'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control mb-3'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control mb-3'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control mb-3'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not user:
            raise ValueError("کاربر وارد نشده است")

        self.fields['province'].queryset = Province.objects.all()
        self.set_jalali_initial('birth_date', 'birth_date')

        if self.instance and hasattr(self.instance, 'province') and self.instance.province:
            self.fields['city'].queryset = self.instance.province.cities.all()
        else:
            self.fields['city'].queryset = City.objects.all()

    def clean_birth_date(self):
        return self.clean_jalali_date('birth_date')

class ProfileUpdateForm1(forms.ModelForm):
    birth_date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': 'تاریخ را انتخاب کنید (1404/01/17)',
        }),
        required=False
    )

    class Meta:
        model = CustomProfile
        fields = ['first_name', 'last_name', 'province', 'city', 'phone_number', 'birth_date', 'address', 'description', 'location', 'bio', 'zip_code']
        widgets = {
            'address': forms.Textarea(attrs={'class': 'form-control mb-3', 'rows': 3}),
            'description': forms.Textarea(attrs={'class': 'form-control mb-3', 'rows': 2}),
            'location': forms.Textarea(attrs={'class': 'form-control mb-3', 'rows': 2}),
            'bio': forms.Textarea(attrs={'class': 'form-control mb-3', 'rows': 2}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control mb-3'}),
            'province': forms.Select(attrs={'class': 'form-control mb-3'}),
            'city': forms.Select(attrs={'class': 'form-control mb-3'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control mb-3'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control mb-3'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control mb-3'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not user:
            raise ValueError("کاربر وارد نشده است")

        self.fields['province'].queryset = Province.objects.all()

        # تنظیم مقدار اولیه تاریخ شمسی
        if self.instance and self.instance.birth_date:
            jalali_date = jdatetime.date.fromgregorian(date=self.instance.birth_date)
            self.initial['birth_date'] = jalali_date.strftime('%Y/%m/%d')
            logger.info(f"Set initial birth_date to: {self.initial['birth_date']}")
        else:
            self.initial['birth_date'] = ''

        if self.instance and hasattr(self.instance, 'province') and self.instance.province:
            self.fields['city'].queryset = self.instance.province.cities.all()
        else:
            self.fields['city'].queryset = City.objects.all()

    def clean_birth_date(self):
        birth_date_str = self.cleaned_data.get('birth_date')
        logger.info(f"Raw birth_date_str: {birth_date_str}")
        if birth_date_str:
            try:
                j_date = jdatetime.datetime.strptime(birth_date_str, '%Y/%m/%d').date()
                logger.info(f"Detected Jalali format, converted to: {j_date.togregorian()}")
                return j_date.togregorian()
            except ValueError as e:
                logger.error(f"Error parsing date: {e}")
                raise forms.ValidationError("تاریخ را به فرمت درست وارد کنید (مثل 1404/01/17)")
        logger.info("No birth_date provided, returning None")
        return None

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="رمز عبور")

    class Meta:
        model = CustomUser
        # fields = ('username', 'email', 'password', 'is_active', 'is_staff', 'is_superuser')
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser')

    # class Meta:
    #     model = CustomUser
    #     fields = (
    #         'username', 'email', 'password', 'group', 'is_active', 'is_staff',
    #         'is_superuser', 'is_payment_settled', 'phone_number', 'city',
    #         'address', 'bio',
    #     )

    # فیلدهای اضافی
    group = forms.ModelChoiceField(queryset=Group.objects.all(), required=False, label="Group",
                                   widget=forms.Select(attrs={'class': 'form-control'}))
    is_active = forms.BooleanField(required=False, initial=True, label="فعال/غیرفعال", widget=forms.CheckboxInput(
        attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}))
    is_staff = forms.BooleanField(required=False, initial=False, label="کارمند", widget=forms.CheckboxInput(
        attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}))
    is_superuser = forms.BooleanField(required=False, initial=False, label="مدیر سیستم", widget=forms.CheckboxInput(
        attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}))
    is_payment_settled = forms.BooleanField(
        required=False,
        initial=False,
        label="پرداخت تسویه شده",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'})
    )

    # فیلدهای مدل اصلی با ویجت‌های خاص
    email = forms.EmailField(
        required=True,
        label="ایمیل",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ایمیل خود را وارد کنید'})
    )
    username = forms.CharField(
        max_length=30,
        required=True,
        label="نام کاربری",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام کاربری خود را وارد کنید'})
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'رمز عبور'})
    )

    # فیلدهای اضافی برای تکمیل اطلاعات
    phone_number = forms.CharField(
        max_length=11,
        required=False,
        label="شماره تماس",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره تماس خود را وارد کنید'})
    )
    city = forms.ModelChoiceField(
        queryset=Province.objects.all(),
        required=False,
        label="شهر",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    address = forms.CharField(
        required=False,
        label="آدرس",
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'آدرس خود را وارد کنید', 'rows': 3})
    )
    bio = forms.CharField(
        required=False,
        label="بیوگرافی",
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'بیوگرافی خود را وارد کنید', 'rows': 3})
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

    def clean_username(self):
        """بررسی نام کاربری برای یکتا بودن (با تفاوت تنها در حروف بزرگ و کوچک)"""
        username = self.cleaned_data.get("username")
        if username and self._meta.model.objects.filter(username__iexact=username).exists():
            raise ValidationError("نام کاربری قبلاً ثبت شده است.")
        return username

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control mb-3'
# این فرم را برای اضافه کردن گروه‌ها بعد از ثبت نام استفاده کنید
class PostRegistrationGroupForm(forms.Form):
    groups = forms.ModelMultipleChoiceField(queryset=MyGroup.objects.all(),
                                            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self):
        if self.user:
            for group in self.cleaned_data['groups']:
                CustomUserGroup.objects.get_or_create(customuser=self.user, mygroup=group)
class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = '__all__'  # ['username', 'email', 'password1', 'password2']
class AdvancedProfileSearchForm(forms.Form):
    first_name = forms.CharField(required=False, label="نام")
    last_name = forms.CharField(required=False, label="نام خانوادگی")
    province = forms.ModelChoiceField(queryset=Province.objects.all(), required=False, label="استان", empty_label="همه")
    city = forms.ModelChoiceField(queryset=City.objects.none(), required=False, label="شهر", empty_label="همه")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # اگر استان انتخاب شده باشد، شهرها را بر اساس آن فیلتر کن
        if 'province' in self.data:
            try:
                province_id = int(self.data.get('province'))
                self.fields['city'].queryset = City.objects.filter(province_id=province_id)
            except (ValueError, TypeError):
                self.fields['city'].queryset = City.objects.none()
        elif self.instance.pk:  # اگر فرم از یک شیء موجود باشد، شهرهای مرتبط با آن استان را بارگذاری کن
            self.fields['city'].queryset = self.instance.province.city_set.all()
yset = City.objects.none()
#######################################################################
class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput, label="گذرواژه جدید")
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = '__all__'  # ['bio', 'birth_date']
        # fields = ['username', 'email']
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'is_active', 'is_staff', ]
'''
 برای انتخاب نقش جدید، یک فرم ایجاد کنید که لیست تمام نقش‌های موجود را نمایش دهد.
'''
class RoleTransferForm(forms.Form):
    new_role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        label="انتقال وابستگی‌ها به نقش جدید",
        required=False,
    )
class GroupFilterForm(forms.Form):
    name = forms.CharField(max_length=150, required=False, label="جستجو بر اساس نام گروه")
#######################################################################
from .models import ActiveUser
class ActiveUserForm(forms.ModelForm):
    class Meta:
        model = ActiveUser
        fields = ['user', 'session_key']  # فقط کاربر و کلید سشن قابل ویرایش دستی هستن
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'session_key': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # غیرفعال کردن session_key اگه در حال ویرایش باشه
        if self.instance.pk:
            self.fields['session_key'].disabled = True
##########################Security Lock#############################################
from django import forms
from accounts.models import TimeLockModel
# accounts/forms.py
import jdatetime
class TimeLockForm(forms.Form):
    models  = TimeLockModel
    expiry_date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        }),
     )
    max_active_users = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}),
                                          label='حداکثر کاربران فعال', required=False)
    organization_name = forms.CharField(max_length=255, label='نام مجموعه',
                                        widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if not expiry_date:
            raise forms.ValidationError("تاریخ انقضا نمی‌تواند خالی باشد.")
        try:
            # اگر تاریخ به صورت رشته است، به jdatetime تبدیل کنید
            if isinstance(expiry_date, str):
                expiry_date = jdatetime.datetime.strptime(expiry_date, '%Y/%m/%d').date()
            # تبدیل به میلادی
            return expiry_date.togregorian()
        except ValueError:
            raise forms.ValidationError("فرمت تاریخ اشتباه است. لطفاً از فرمت ۱۴۰۴/۰۱/۱۷ استفاده کنید.")
        except Exception as e:
            raise forms.ValidationError(f"خطا در تبدیل تاریخ: {str(e)}")

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.expiry_date:
            jalali_date = jdatetime.date.fromgregorian(date=self.instance.expiry_date)
            self.fields['expiry_date'].initial = jalali_date.strftime('%Y/%m/%d')


# Forms For Backuping
# core/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _

class DatabaseBackupForm(forms.Form):
    DATABASE_TYPES = (
        ('mysql', 'MySQL'),
        ('postgresql', 'PostgreSQL'),
    )
    FORMATS = (
        ('sql', 'SQL'),
        ('zip', 'ZIP'),
    )

    database_type = forms.ChoiceField(
        label=_("نوع دیتابیس"),
        choices=DATABASE_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    format = forms.ChoiceField(
        label=_("فرمت خروجی"),
        choices=FORMATS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    password = forms.CharField(
        label=_("رمز برای رمزگذاری (اختیاری)"),
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("حداقل 8 کاراکتر")}),
        help_text=_("برای رمزگذاری ZIP یا GPG استفاده می‌شود.")
    )
    reset_models = forms.BooleanField(
        label=_("ریست جدول‌ها"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    models_to_reset = forms.CharField(
        label=_("جدول‌های موردنظر برای ریست (با کاما جدا کنید)"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'table1,table2'}),
        help_text=_("نام جدول‌ها را دقیق وارد کنید.")
    )

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 8:
            raise forms.ValidationError(_("رمز باید حداقل 8 کاراکتر باشد."))
        return password

    def clean_models_to_reset(self):
        models = self.cleaned_data.get('models_to_reset')
        reset = self.cleaned_data.get('reset_models')
        if reset and not models:
            raise forms.ValidationError(_("لطفاً جدول‌هایی برای ریست مشخص کنید."))
        return models