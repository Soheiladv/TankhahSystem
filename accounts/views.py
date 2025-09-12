from django.views.generic import DetailView
from django.conf import settings
import datetime
import hashlib
import logging
import secrets

import jdatetime
from django.apps import apps
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
################## Accounts New Code
# Create user Account
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView, DetailView
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from accounts.RCMS_Lock.security import TimeLock
from accounts.forms import TimeLockForm
from accounts.models import TimeLockModel, City
from core.PermissionBase import PermissionBaseView
# , check_permission_and_organization)
from .forms import ActiveUserForm
from .forms import (CustomUserCreationForm, CustomUserForm, RoleForm, MyGroupForm,
                    ProfileUpdateForm, CustomPasswordChangeForm, ProfileForm, AdvancedProfileSearchForm, UserGroupForm,
                    RoleTransferForm)
from .forms import GroupFilterForm
from .forms import TransferRoleDependenciesForm
from .has_role_permission import has_permission
from .models import ActiveUser
from .models import AuditLog
from .models import CustomProfile, CustomUser, Role, MyGroup, CustomUserGroup

logger = logging.getLogger(__name__)

# Helper Functions

def check_group_membership(request):
    # بررسی عضویت در گروه
    return CustomUserGroup.objects.filter(customuser=request.user).exists()

def test_func(self):
    return check_group_membership(self.request)

def dashboard_view(request):
    cards = [
        {
            "title": "مدیریت کاربران",
            "icon": "fas fa-users",
            "items": [
                {"label": "لیست کاربران", "url": "accounts:user_list", "icon": "fas fa-list", "color": "info"},
                {"label": "افزودن کاربر", "url": "accounts:user_create", "icon": "fas fa-user-plus",
                 "color": "success"},
                {"label": "تغییر رمز عبور", "url": "accounts:password_change", "icon": "fas fa-key",
                 "color": "warning"},
            ],
        },
        {
            "title": "مدیریت نقش‌ها",
            "icon": "fas fa-user-tag",
            "items": [
                {"label": "لیست نقش‌ها", "url": "accounts:role_list", "icon": "fas fa-list", "color": "info"},
                {"label": "ایجاد نقش جدید", "url": "accounts:role_create", "icon": "fas fa-plus", "color": "success"},
            ],
        },

        {
            "title": "مدیریت گروه‌ها",
            "icon": "fas fa-users-cog",
            "items": [
                {"label": "لیست گروه‌ها", "url": "accounts:group_list", "icon": "fas fa-list", "color": "info"},
                {"label": "ایجاد گروه جدید", "url": "accounts:group_create", "icon": "fas fa-plus", "color": "success"},
            ],
        },
        {
            "title": "پروفایل کاربری",
            "icon": "fas fa-id-card",
            "items": [
                {"label": "ویرایش پروفایل", "url": "accounts:profile_update", "icon": "fas fa-user-edit",
                 "color": "primary"},
                {"label": "حذف پروفایل", "url": "accounts:profile_delete", "icon": "fas fa-trash", "color": "danger"},
            ],
        },
        {
            "title": "گزارش‌ها و لاگ‌ها",
            "icon": "fas fa-file-alt",
            "items": [
                {"label": "گزارش فعالیت‌ها", "url": "accounts:audit_log_list", "icon": "fas fa-history",
                 "color": "secondary"},
            ],
        },
        {
            "title": "مدیریت نسخه",
            "icon": "fas fa-soft",
            "items": [
                {"label": " ثبت قفل جدید و نمایش وضعیت ", "url": "accounts:set_time_lock", "icon": "fas fa-history",
                 "color": "warning"},
                {"label": " نمایش لیست تنظیمات قفل ", "url": "accounts:timelock_list", "icon": "fas fa-history",
                 "color": "warning"},
                {"label": "وضعیت قفل ", "url": "accounts:lock_status", "icon": "fas fa-history", "color": "warning"},
                {"label": "فهرست کاربران فعال سیستم ", "url": "accounts:active_user_list", "icon": "fas fa-history",
                 "color": "warning"},
                    ],
        },
        {
            "title": "مدیریت دیتابیس",
            "icon": "fas fa-soft",
            "items": [
                {"label": "  مدیریت دیتابیس ", "url": "accounts:new_databasebackup", "icon": "fas fa-database",
                 "color": "warning"},

            ],
        },
        {
            "title": "چارت مدل ",
            "icon": "fas fa-user-tag",
            "items": [
                {"label": "نمودار مدل ها ", "url": "accounts:model_graph", "icon": "fas fa-chart", "color": "danger"},
            ],
        },
        {
            "title": "مدیریت گردش کار ",
            "icon": "fas fa-user-tag",
            "items": [
                {"label": " داشبورد گردش کار", "url": "workflow_dashboard", "icon": "fas fa-chart", "color": "danger"},
                {"label": " وضعیت گردش کار گردش کار  (A)", "url": "status_list", "icon": "fas fa-chart", "color": "danger"},
                {"label": " اقدام گردش کار (B)", "url": "action_list", "icon": "fas fa-chart", "color": "danger"},
                {"label": " گذار گردش کار (C)", "url": "transition_list", "icon": "fas fa-chart", "color": "danger"},
                # {"label": " مجوز گردش کار (D)", "url": "permission_list", "icon": "fas fa-chart", "color": "danger"},
            ],
        },
    ]

    return render(request, "accounts/dashboardLink.html", {"cards": cards})

#####
@method_decorator(login_required, name='dispatch')
@method_decorator(has_permission('users_can_view_group'), name='dispatch')
class GroupListView(LoginRequiredMixin, ListView):
    model = MyGroup
    form_class = GroupFilterForm  # تغییر نام فرم به GroupFilterForm
    template_name = 'accounts/groups/group_list.html'
    context_object_name = 'groups'

    def get_queryset(self):
        queryset = super().get_queryset()
        form = GroupFilterForm(self.request.GET)
        if form.is_valid():
            name = form.cleaned_data.get('name', '')
            if name:
                queryset = queryset.filter(name__icontains=name)
        for group in queryset:
            group.member_count = CustomUserGroup.objects.filter(mygroup=group).count()
            group.users = [usergroup.customuser for usergroup in CustomUserGroup.objects.filter(mygroup=group)]
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.form_class(self.request.GET or None)
        return context

@method_decorator(has_permission('add_mygroup'), name='dispatch')
class GroupCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = MyGroup
    form_class = MyGroupForm
    template_name = 'accounts/groups/group_form.html'
    success_url = reverse_lazy('accounts:group_list')
    success_message = 'گروه با موفقیت ایجاد شد.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['user_form'] = UserGroupForm(self.request.POST)
        else:
            context['user_form'] = UserGroupForm()
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        user_form = context['user_form']
        if user_form.is_valid():
            self.object = form.save()
            user_form.save(self.object)
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "لطفاً خطاهای فرم را برطرف کنید.")
        return self.render_to_response(self.get_context_data(form=form))

@method_decorator(has_permission('change_mygroup'), name='dispatch')
class GroupUpdateView(LoginRequiredMixin, UpdateView):
    model = MyGroup
    form_class = MyGroupForm
    template_name = 'accounts/groups/group_form.html'
    success_url = reverse_lazy('accounts:group_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['user_form'] = UserGroupForm(self.request.POST, group=self.object)
        else:
            context['user_form'] = UserGroupForm(group=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        user_form = context['user_form']
        if user_form.is_valid():
            self.object = form.save()
            user_form.save(self.object)
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "لطفاً خطاهای فرم را برطرف کنید.")
        return self.render_to_response(self.get_context_data(form=form))

@method_decorator(has_permission('delete_mygroup'), name='dispatch')
class GroupDeleteView(LoginRequiredMixin, DeleteView):
    model = MyGroup
    template_name = 'accounts/groups/group_confirm_delete.html'
    success_url = reverse_lazy('accounts:group_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'گروه با موفقیت حذف شد.')
        return super().delete(request, *args, **kwargs)
###############################################################################
# Role Views
class RoleCRUDMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True
    model = Role
    form_class = RoleForm
    template_name = 'accounts/users/rols/role_form.html'
    success_url = reverse_lazy('role_list')
# ==============================================
class RoleListView(PermissionBaseView, ListView):
    model = Role
    template_name = 'accounts/users/rols/role_list.html'
    context_object_name = 'roles'
    permission_codenames = 'see_role'
    check_organization = False
    paginate_by = 10

    def get_queryset(self):
        # برای جلوگیری از خطای N+1 و بهینه‌سازی کوئری
        queryset = super().get_queryset().prefetch_related('permissions')

        # دریافت پارامترهای جستجو و فیلتر از URL
        query = self.request.GET.get('q', '').strip()
        show_inactive = self.request.GET.get('show_inactive') == 'true'

        # اعمال فیلتر وضعیت (فعال/غیرفعال)
        # به صورت پیش‌فرض فقط فعال‌ها نمایش داده می‌شوند
        if not show_inactive:
            queryset = queryset.filter(is_active=True)

        # اعمال فیلتر جستجو
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(permissions__name__icontains=query) # جستجو در نام مجوزها
            ).distinct() # برای جلوگیری از نمایش نتایج تکراری

        return queryset.order_by('-created_at') # مرتب‌سازی بر اساس جدیدترین

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("مدیریت نقش‌ها")
        # ارسال مقادیر فعلی جستجو و فیلتر به تمپلیت برای حفظ وضعیت
        context['query'] = self.request.GET.get('q', '')
        context['show_inactive'] = self.request.GET.get('show_inactive') == 'true'
        context['print_date_now'] = now()
        context['print_time_now'] = f'{now().time().hour}:{now().time().minute}'

        return context
    # ==============================================
# class RoleListView(PermissionBaseView,ListView):
#     model = Role
#     template_name = 'accounts/users/rols/role_list.html'
#     # template_name = 'accounts/role/role_list.html'
#     context_object_name = 'roles'
#     permission_codenames = 'see_role'
#     paginate_by = 10  # صفحه‌بندی با 10 آیتم در هر صفحه
#
#     def get_queryset(self):
#         queryset = super().get_queryset()
#         # فیلتر جستجو
#         query = self.request.GET.get('q', '').strip()
#         if query:
#             queryset = queryset.filter(
#                 Q(name__icontains=query) |
#                 Q(description__icontains=query)
#             )
#             if not queryset.exists():
#                 messages.info(self.request, _("نقشی با این مشخصات یافت نشد."))
#
#         # فقط نقش‌های فعال (اختیاری، اگه بخوای همه رو نشون بده این خط رو حذف کن)
#         # queryset = queryset.filter(is_active=True)
#
#         return queryset.order_by('name')
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['title'] = _("لیست نقش‌ها")
#         context['query'] = self.request.GET.get('q', '')
#         return context


# ===========================================================
class RoleListView1(PermissionBaseView, View):
    template_name = 'accounts/users/rols/role_list.html'
    permission_codenames = 'see_role'
    def get(self, request):
        show_inactive = request.GET.get('show_inactive', 'false') == 'true'
        roles = Role.objects.all() if show_inactive else Role.objects.filter(is_active=True)
        return render(request, self.template_name, {'roles': roles, 'show_inactive': show_inactive})

# =========================================================
# لیست اپ‌هایی که نمی‌خوای نشون داده بشن
EXCLUDED_APPS = [
    'admin_interface',
    # 'notificationsApp',
    'contenttypes',
    'sessions',
    # هر اپ دیگه‌ای که نمی‌خوای رو اضافه کن
]

# @method_decorator(has_permission('create_role'), name='dispatch')
class RoleCreateView(PermissionBaseView,CreateView):
    raise_exception = True
    model = Role
    form_class = RoleForm
    template_name = 'accounts/role/role_form.html'
    success_url = reverse_lazy('accounts:role_list')
    permission_codenames = 'create_role'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permissions = Permission.objects.select_related('content_type').all()
        tree = {}
        for perm in permissions:
            app_config = apps.get_app_config(perm.content_type.app_label)
            if app_config.name not in EXCLUDED_APPS:  # فقط اپ‌های غیراستثنا
                app_label_farsi = app_config.verbose_name
                # print(f"App: {app_config.name}, Verbose: {app_label_farsi}")
                tree.setdefault(app_label_farsi, []).append(perm)
        # print("permissions_tree keys:", list(tree.keys()))
        context['permissions_tree'] = tree
        return context
    def get_permissions_tree(self):
        permissions = Permission.objects.select_related('content_type').all()
        tree = {}
        for perm in permissions:
            app_label = perm.content_type.app_label
            if app_label not in tree:
                tree[app_label] = []
            tree[app_label].append(perm)
        return tree

class __RoleUpdateView(PermissionBaseView,  UpdateView):
    model = Role
    form_class = RoleForm
    template_name = 'accounts/role/role_form.html'
    success_url = reverse_lazy('accounts:role_list')
    permission_codenames = 'modify_role'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permissions = Permission.objects.select_related('content_type').all()
        tree = {}
        for perm in permissions:
            app_config = apps.get_app_config(perm.content_type.app_label)
            if app_config.name not in EXCLUDED_APPS:  # همینجا هم اعمال کن
                app_label_farsi = app_config.verbose_name
                # print(f"App: {app_config.name}, Verbose: {app_label_farsi}")
                tree.setdefault(app_label_farsi, []).append(perm)
        context['permissions_tree'] = tree
        print("Loaded apps:", [app.verbose_name for app in apps.get_app_configs()])
        return context

    def get_permissions_tree(self):
        permissions = Permission.objects.select_related('content_type').all()
        tree = {}
        for perm in permissions:
            app_config = apps.get_app_config(perm.content_type.app_label)
            app_label_farsi = app_config.verbose_name  # اینجا هم فارسی رو بگیر
            print(f"App: {app_config.name}, Verbose: {app_config.verbose_name}")  # برای دیباگ
            tree.setdefault(app_label_farsi, []).append(perm)
        print("permissions_tree keys:", list(tree.keys()))  # برای دیباگ
        return tree

# یک میکس‌این برای جلوگیری از تکرار کد
class RoleFormMixin:
    model = Role
    form_class = RoleForm
    template_name = 'accounts/role/role_form.html'  # آدرس تمپلیت جدید
    success_url = reverse_lazy('accounts:role_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['permissions_tree'] = self.get_permissions_tree()
        context['title'] = _("ایجاد نقش جدید") if 'create' in self.request.path else _("ویرایش نقش")
        context['print_date_now'] = now()
        context['print_time_now'] = f'{now().time().hour}:{now().time().minute}'
        return context

    def get_permissions_tree(self):
        """
        درخت مجوزها را با گروه‌بندی بر اساس نام فارسی اپلیکیشن‌ها ایجاد و مرتب می‌کند.
        """
        # می‌توانید لیست اپلیکیشن‌های مورد نظر برای حذف را در settings.py تعریف کنید
        EXCLUDED_APPS = getattr(settings, 'ROLE_FORM_EXCLUDED_APPS', [
            'admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles'
        ])

        # مجوزها را یکجا با content_type دریافت و مرتب می‌کنیم
        permissions = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'codename')

        tree = {}
        for perm in permissions:
            app_label = perm.content_type.app_label
            # اگر اپلیکیشن در لیست استثناها نبود
            if app_label not in EXCLUDED_APPS:
                try:
                    app_config = apps.get_app_config(app_label)
                    # از verbose_name برای نام فارسی اپلیکیشن استفاده می‌کنیم
                    app_verbose_name = app_config.verbose_name
                    tree.setdefault(app_verbose_name, []).append(perm)
                except LookupError:
                    # اگر اپلیکیشنی پیدا نشد، از آن صرف نظر کن
                    continue

        # مرتب‌سازی دیکشنری بر اساس کلیدها (نام فارسی اپلیکیشن‌ها)
        sorted_tree = dict(sorted(tree.items()))
        return sorted_tree

class RoleUpdateView(PermissionBaseView, RoleFormMixin, UpdateView):
    permission_codenames = 'modify_role'


@method_decorator(has_permission('remove_role'), name='dispatch')
class RoleDeleteView(DeleteView):
    model = Role
    template_name = 'accounts/users/rols/role_confirm_delete.html'
    success_url = reverse_lazy('accounts:role_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = self.get_object()
        context['users'] = role.custom_users.all()
        context['groups'] = role.mygroups.all()
        context['role_form'] = RoleTransferForm()  # فرم انتقال وابستگی‌ها
        return context

    def post(self, request, *args, **kwargs):
        role = self.get_object()
        new_role_id = request.POST.get('new_role')  # دریافت نقش جدید از فرم

        if role.custom_users.exists() or role.mygroups.exists():
            if new_role_id:
                new_role = Role.objects.get(id=new_role_id)
                with transaction.atomic():  # استفاده از تراکنش برای اطمینان از یکپارچگی داده‌ها
                    # انتقال کاربران به نقش جدید
                    for user in role.custom_users.all():
                        user.roles.remove(role)  # حذف نقش قدیمی
                        user.roles.add(new_role)  # اضافه کردن نقش جدید

                    # انتقال گروه‌ها به نقش جدید
                    for group in role.mygroups.all():
                        group.roles.remove(role)  # حذف نقش قدیمی
                        group.roles.add(new_role)  # اضافه کردن نقش جدید

                    role.delete()  # حذف نقش پس از انتقال وابستگی‌ها
                    messages.success(request, _("نقش با موفقیت حذف شد و وابستگی‌ها به نقش جدید منتقل شدند."))
            else:
                messages.error(request,
                               _("این نقش دارای وابستگی‌هایی است. لطفاً یک نقش جدید برای انتقال وابستگی‌ها انتخاب کنید."))
                return render(request, self.template_name, self.get_context_data())
        else:
            role.delete()  # حذف نقش اگر وابستگی‌ای وجود نداشته باشد
            messages.success(request, _("نقش با موفقیت حذف شد."))

        return HttpResponseRedirect(self.get_success_url())

# ==============================================================================================
class RolePrintView(PermissionBaseView, DetailView):
    model = Role
    template_name = 'accounts/role/role_print_view.html'
    context_object_name = 'role'
    permission_codenames = 'see_role'  # یا هر مجوزی که برای دیدن نقش لازم است

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = self.get_object()

        # از همان منطق قبلی برای گرفتن درخت مجوزها استفاده می‌کنیم
        # این کد را می‌توانید از RoleFormMixin کپی کنید یا یک کلاس پایه مشترک بسازید
        # --- شروع منطق get_permissions_tree ---
        EXCLUDED_APPS = getattr(settings, 'ROLE_FORM_EXCLUDED_APPS', [
            'admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles'
        ])
        all_permissions = Permission.objects.select_related('content_type').order_by('content_type__app_label',
                                                                                     'codename')

        tree = {}
        for perm in all_permissions:
            app_label = perm.content_type.app_label
            if app_label not in EXCLUDED_APPS:
                try:
                    app_config = apps.get_app_config(app_label)
                    app_verbose_name = app_config.verbose_name
                    tree.setdefault(app_verbose_name, []).append(perm)
                except LookupError:
                    continue
        sorted_tree = dict(sorted(tree.items()))
        # --- پایان منطق get_permissions_tree ---

        # شناسه مجوزهای اختصاص داده شده به این نقش
        assigned_perm_ids = set(role.permissions.values_list('id', flat=True))

        # ساختار نهایی داده برای تمپلیت
        app_permission_status = []
        for app_name, permissions in sorted_tree.items():
            app_data = {
                'name': app_name,
                'assigned': [],
                'unassigned': []
            }
            for perm in permissions:
                if perm.id in assigned_perm_ids:
                    app_data['assigned'].append(perm)
                else:
                    app_data['unassigned'].append(perm)

            # فقط اپلیکیشن‌هایی را اضافه کن که حداقل یک مجوز (اختصاصی یا غیراختصاصی) دارند
            if app_data['assigned'] or app_data['unassigned']:
                app_permission_status.append(app_data)

        context['title'] = f"چاپ مجوزهای نقش: {role.name}"
        context['app_permission_status'] = app_permission_status
        context['print_date_now'] =  now()
        context['print_time_now'] =  f'{now().time().hour}:{  now().time().minute}'

        return context

# ==============================================================================================

class UserCRUDMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True
    model = CustomUser
    template_name = 'accounts/users/user_form.html'
    success_url = reverse_lazy('user_list')

    def test_func(self):
        return self.request.user.is_superuser

@method_decorator(login_required, name='dispatch')
@method_decorator(has_permission('view_customuser'), name='dispatch')
class UserListView(LoginRequiredMixin, ListView):
    model = CustomUser
    template_name = "accounts/users/user_list.html"
    context_object_name = 'users'

    def get_queryset(self):
        queryset = CustomUser.objects.prefetch_related('roles')

        if self.request.user.is_superuser:
            queryset = queryset.all()
        else:
            # اگر می‌خواهید دسترسی‌های بیشتری برای کاربران عادی اعمال کنید، اینجا اضافه کنید.
            pass

        # جستجو
        search_query = self.request.GET.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        # فیلتر بر اساس وضعیت فعالیت
        active_users = self.request.GET.get('active_users', '')
        inactive_users = self.request.GET.get('inactive_users', '')

        if active_users and not inactive_users:
            queryset = queryset.filter(is_active=True)
        elif inactive_users and not active_users:
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['active_users'] = self.request.GET.get('active_users', '')
        context['inactive_users'] = self.request.GET.get('inactive_users', '')
        return context

@method_decorator(login_required, name='dispatch')
@method_decorator(has_permission('add_customuser'), name='dispatch')
class UserCreateView(LoginRequiredMixin, CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/users/user_create.html'  # مطمئن شوید این قالب وجود دارد
    success_url = reverse_lazy('accounts:user_list')  # یا هر URL که می‌خواهید بعد از موفقیت به آن هدایت شود

    def form_valid(self, form):
        try:
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.save()
            groups = form.cleaned_data.get('groups')
            if groups:
                user.groups.set(groups)
            messages.success(self.request, 'کاربر با موفقیت ایجاد شد.')
        except Exception as e:
            messages.error(self.request, f'خطا در ثبت کاربر: {str(e)}')
            return self.form_invalid(form)
        return super().form_valid(form)

@method_decorator(has_permission('change_customuser'), name='dispatch')
class UserEditView(UserCRUDMixin, UpdateView):
    form_class = CustomUserForm
    template_name = 'accounts/users/user_edit.html'  # مطمئن شوید این قالب وجود دارد
    success_url = reverse_lazy('accounts:user_list')  # یا هر URL که می‌خواهید بعد از موفقیت به آن هدایت شود

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = Role.objects.all()
        context['groups'] = MyGroup.objects.all()
        return context

    def form_valid(self, form):
        user = form.save(commit=False)
        try:
            # ذخیره گروه‌ها
            groups = form.cleaned_data.get('groups')
            if groups:
                user.groups.set(groups)

            # ذخیره نقش‌ها
            roles = form.cleaned_data.get('roles')
            if roles:
                user.roles.set(roles)

            user.save()
            messages.success(self.request, 'اطلاعات کاربر با موفقیت به روز شد.')
        except Exception as e:
            messages.error(self.request, f'خطا در به روز رسانی: {str(e)}')
        return super().form_valid(form)


@method_decorator(has_permission('delete_customuser'), name='dispatch')
class UserDeleteView(UserCRUDMixin, DeleteView):
    template_name = 'accounts?users/user_confirm_delete.html'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not self.request.user.is_superuser and obj != self.request.user:
            raise PermissionDenied("شما مجوز حذف این کاربر را ندارید.")
        return obj

class AssignUsersToGroupView(LoginRequiredMixin, UpdateView):
    model = MyGroup
    form_class = UserGroupForm
    template_name = 'accounts/groups/assign_users_to_group.html'
    success_url = reverse_lazy('accounts:group_list')

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')
        return MyGroup.objects.get(pk=pk)

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'کاربران با موفقیت به گروه اختصاص داده شدند.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = self.get_object()
        return context

# view برای نمایش لیست کاربران یک گروه
class GroupUserListView(LoginRequiredMixin, ListView):
    model = CustomUserGroup
    template_name = 'accounts/groups/group_user_list.html'
    context_object_name = 'user_groups'

    def get_queryset(self):
        group_id = self.kwargs['pk']
        return CustomUserGroup.objects.filter(mygroup_id=group_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = MyGroup.objects.get(pk=self.kwargs['pk'])
        return context
#########################################
# Profile Views
'''
از get_or_create در ProfileView استفاده شده است تا هم برای ایجاد و هم برای ویرایش پروفایل کار کند.
'''
User = get_user_model()
@method_decorator(has_permission('users_view_userprofile'), name='dispatch')
class ProfileView(LoginRequiredMixin , View):
    template_name = 'accounts/profile/profile_list.html'

    def get(self, request):
        if request.user.is_superuser or request.user.is_staff:
            profiles = CustomProfile.objects.all()
            form = None  # برای مدیران و کارکنان لیست نمایش داده شود
        else:
            profile, created = CustomProfile.objects.get_or_create(user=request.user)
            form = ProfileUpdateForm(instance=profile)
            profiles = None  # برای کاربران عادی لیست پروفایل‌ها نداریم
        return render(request, self.template_name, {'profiles': profiles, 'form': form})

    def post(self, request):
        if request.user.is_superuser or request.user.is_staff:
            profile_id = request.POST.get('profile_id')  # فرض بر این است که id پروفایل در فرم ارسال می‌شود
            print(profile_id)
            if profile_id:
                profile = get_object_or_404(CustomProfile, id=profile_id)
            else:
                # اگر profile_id ارسال نشده بود، می‌توانیم به پروفایل کاربر فعلی برگردیم
                profile, created = CustomProfile.objects.get_or_create(user=request.user)
                messages.warning(request, 'پروفایل انتخاب شده یافت نشد.')
        else:
            profile, created = CustomProfile.objects.get_or_create(user=request.user)

        # اینجا می‌توانیم چک کنیم که آیا داده‌های POST نال هستند یا خیر
        if not any(request.POST.values()):
            messages.warning(request, 'لطفاً فرم را پر کنید.')
            form = ProfileUpdateForm(instance=profile)
        else:
            form = ProfileUpdateForm(request.POST, instance=profile)

            if form.is_valid():
                form.save()
                messages.success(request, 'پروفایل با موفقیت به‌روزرسانی شد.')
                return redirect('profile')  # چه مدیر باشد چه کارکنان یا کاربران عادی به صفحه پروفایل بازگردانده شوند
            else:
                messages.error(request, 'لطفاً خطاهای فرم را بررسی کنید.')

        return render(request, self.template_name, {'form': form, 'profiles': None if not (
                request.user.is_superuser or request.user.is_staff) else CustomProfile.objects.all()})

# یک کلاس پایه برای مدیریت پروفایل کاربری
'''
توضیحات کلاس BaseProfileView:
model: این بخش به مدل CustomProfile اشاره دارد که پروفایل کاربری را در آن ذخیره می‌کنیم.
form_class: این فرم برای مدیریت فیلدهای پروفایل استفاده می‌شود. فرم CustomProfileForm که قبلاً تعریف کرده‌ایم، در اینجا به عنوان فرم برای ویرایش یا ثبت اطلاعات استفاده می‌شود.
template_name: این بخش تعیین می‌کند که کدام قالب HTML باید برای این ویو استفاده شود.
context_object_name: برای نام‌گذاری شیء پروفایل در قالب (template) از این متغیر استفاده می‌کنیم.
dispatch: دکوریتور login_required را به متد dispatch اضافه کرده‌ایم تا فقط کاربران لاگین شده بتوانند به این ویو دسترسی داشته باشند.
get_object: این متد به‌طور خودکار پروفایل کاربر را پیدا کرده یا در صورت عدم وجود، آن را ایجاد می‌کند.
form_valid: پس از ارسال فرم و اعتبارسنجی موفق، تغییرات ذخیره شده و پیامی مبنی بر موفقیت ارسال می‌شود.
get_success_url: پس از ذخیره تغییرات، کاربر به صفحه پروفایل خود هدایت می‌شود.
استفاده از کلاس BaseProfileView در ویوهای مختلف:
حالا که کلاس پایه BaseProfileView را داریم، می‌توانیم آن را در هر ویو (view) که به آن نیاز داریم استفاده کنیم. به عنوان مثال:

ویو ProfileCreateView 
'''
@method_decorator(has_permission('users_add_userprofile'), name='dispatch')
class BaseProfileView(LoginRequiredMixin,UpdateView):
    model = CustomProfile
    form_class = ProfileForm
    template_name = 'accounts/profile/profile_form.html'
    context_object_name = 'profile'

    # @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        profile, created = CustomProfile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, 'پروفایل شما با موفقیت به‌روزرسانی شد!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('accounts:profile')
###################################################
# برای ایجاد پروفایل جدی
@method_decorator(has_permission('users_add_userprofile'), name='dispatch')
class ProfileCreateView(BaseProfileView, CreateView):
    model = CustomProfile
    form_class = ProfileForm
    template_name = 'accounts/profile/profile_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request  # ارسال درخواست به فرم
        return kwargs

    def form_valid(self, form):
        user = self.request.user

        try:
            # سعی در بازیابی یا ایجاد پروفایل
            profile, created = CustomProfile.objects.get_or_create(user=user)

            if not created:  # پروفایل وجود داشته باشد
                profile.first_name = form.cleaned_data['first_name']
                profile.last_name = form.cleaned_data['last_name']
                profile.city = form.cleaned_data['city']
                profile.phone_number = form.cleaned_data['phone_number']
                profile.birth_date = form.cleaned_data['birth_date']
                profile.address = form.cleaned_data['address']
                profile.location = form.cleaned_data['location']
                profile.bio = form.cleaned_data['bio']
                profile.zip_code = form.cleaned_data['zip_code']
                profile.save()

            return super().form_valid(form)

        except IntegrityError:
            # در صورتی که خطای یکپارچگی (duplicate entry) رخ دهد
            form.add_error(None, "این کاربر قبلاً پروفایل دارد.")
            return self.form_invalid(form)

################################
# ویو برای نمایش پروفایل یک کاربر خاص (خواندن)
def profile_detail(request, user_id):
    profile = get_object_or_404(CustomProfile, user_id=user_id)
    return render(request, 'accounts/users/profile_detail.html', {'profile': profile})

# ویو برای حذف پروفایل (حذف)
@login_required
def profile_delete(request):
    profile = get_object_or_404(CustomProfile, user=request.user)
    if request.method == 'POST':
        profile.delete()
        messages.success(request, 'پروفایل شما با موفقیت حذف شد.')
        return redirect('home')  # یا هر آدرس دیگری
    return render(request, 'accounts/users/profile_delete.html', {'profile': profile})

# ویوی به‌روز شده
# @check_permission_and_organization(permissions='accounts.change_profile', check_org=False)
# ==================PROFILE UPDATE============================
def profile_update_view(PermissionBase, request):
    """
    ویو برای به‌روزرسانی پروفایل کاربر.
    فقط خود کاربر می‌تونه پروفایلش رو ویرایش کنه چون instance=request.user هست.
    """
    logger.info(f"کاربر {request.user} در حال ویرایش پروفایل")
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'پروفایل شما با موفقیت به‌روزرسانی شد.')
            logger.info(f"پروفایل کاربر {request.user} با موفقیت ذخیره شد")
            return redirect('index')
        else:
            logger.warning(f"فرم پروفایل کاربر {request.user} معتبر نیست: {form.errors}")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'accounts/users/profile_update.html', {'form': form})
# ============================================================

def get_cities(request):
    province_id = request.GET.get('province')
    if province_id:
        try:
            cities = City.objects.filter(province_id=province_id).values('id', 'name')
            print(f"Province ID: {province_id}, Cities found: {cities.count()}")
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'error': str(e)}, status=400)
    else:
        cities = City.objects.all().values('id', 'name')
    return JsonResponse(list(cities), safe=False)

class ProfileUpdateView(PermissionBaseView):
    permission_codenames = ['users_update_userprofile']
    check_organization = False
    form_class = ProfileUpdateForm
    template_name = 'accounts/users/profile_update.html'
    def get_profile(self, request):
        try:
            return request.user.profile
        except CustomProfile.DoesNotExist:
            logger.info(f"پروفایل برای کاربر {request.user} وجود نداره. در حال ساخت...")
            profile = CustomProfile.objects.create(user=request.user)
            return profile

    def get(self, request, *args, **kwargs):
        profile = self.get_profile(request)
        form = ProfileUpdateForm(instance=profile, user=request.user)
        print(f"Birth date in form: {form['birth_date'].value()}")
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        profile = self.get_profile(request)
        form = ProfileUpdateForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'پروفایل شما با موفقیت به‌روزرسانی شد.')
            return redirect('index')
        return render(request, self.template_name, {'form': form})

# ## برای به‌روزرسانی پروفایل
# @method_decorator(has_permission('users_update_userprofile'), name='dispatch')
# class ProfileUpdateView( BaseProfileView, UpdateView):
#     pass
@login_required
def profile_update_success(request):
    return render(request, 'accounts/users/profile_update_success.html')

@method_decorator(has_permission('users_Search_userprofile'), name='dispatch')
class AdvancedProfileSearchView(LoginRequiredMixin, ListView):
    model = CustomProfile
    template_name = 'accounts/profile/advanced_search.html'
    context_object_name = 'profiles'
    form_class = AdvancedProfileSearchForm

    def get_queryset(self):
        queryset = CustomProfile.objects.all()
        form = self.form_class(self.request.GET)

        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            province = form.cleaned_data.get('province')
            city = form.cleaned_data.get('city')

            filters = Q()  # یک فیلتر خالی برای شروع

            # اضافه کردن فیلترها فقط در صورت داشتن مقدار
            if first_name:
                filters &= Q(first_name__icontains=first_name)
            if last_name:
                filters &= Q(last_name__icontains=last_name)
            if province:
                # فیلتر بر اساس استان
                filters &= Q(city__province=province)
            if city:
                filters &= Q(city=city)

            # اعمال فیلتر به کوئری
            queryset = queryset.filter(filters)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.form_class(self.request.GET)  # ارسال فرم با داده‌های GET
        return context
##########################################################################
# Password Views
@login_required
def password_change(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, 'پسورد شما با موفقیت تغییر کرد!')
            return redirect('profile')  # Or any other view you want to redirect to
        else:
            messages.error(request, 'لطفاً اطلاعات را درست وارد کنید.')
    else:
        form = CustomPasswordChangeForm(user=request.user)
    return render(request, 'accounts/user/password/password_change.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def reset_password_to_default(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, 'کاربر پیدا نشد.')
        return redirect('user_list')

    default_password = 'D@d123'
    user.set_password(default_password)
    user.save()
    update_session_auth_hash(request, user)
    messages.success(request, 'گذرواژه کاربر به گذرواژه پیش‌فرض تغییر کرد.')
    return redirect('accounts:user_list')

@login_required
def admin_dashboard(request):
    return render(request, "accounts/users/admin_dashboard.html", {"user": request.user})

@login_required
def it_staff_dashboard(request):
    return render(request, "accounts/users/it_staff_dashboard.html", {"user": request.user})

@login_required
def requester_dashboard(request):
    return render(request, "accounts/users/requester_dashboard.html", {"user": request.user})

@login_required
def default_dashboard(request):
    return render(request, "accounts/users/default_dashboard.html", {"user": request.user})

class UserChangePasswordView(FormView):
    form_class = PasswordChangeForm
    template_name = 'accounts/users/change_password.html'
    success_url = reverse_lazy('profile')  # به جای 'profile' نام URL مورد نظر را قرار دهید

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        update_session_auth_hash(self.request, form.user)
        return super().form_valid(form)
#####################################
'''
پیاده‌سازی گزینه‌های جایگزین
برای پیاده‌سازی گزینه‌های جایگزین، باید دو ویوی جدید ایجاد کنید:
۱. انتقال وابستگی‌ها به نقش دیگر
'''
@method_decorator(has_permission('Role_create'), name='dispatch')
class TransferRoleDependenciesView(FormView):
    template_name = 'accounts/role/transfer_role_dependencies.html'
    form_class = TransferRoleDependenciesForm
    success_url = reverse_lazy('accounts:role_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['role_id'] = self.kwargs['pk']
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            role = Role.objects.get(id=self.kwargs['pk'])
            new_role = form.cleaned_data['new_role']

            if not new_role:
                messages.error(self.request, _("نقش جدید انتخاب نشده است."))
                return self.form_invalid(form)

            # انتقال کاربران به نقش جدید
            for user in role.custom_users.all():
                user.roles.remove(role)
                user.roles.add(new_role)

            # انتقال گروه‌ها به نقش جدید
            for group in role.mygroups.all():
                group.roles.remove(role)
                group.roles.add(new_role)

            messages.success(self.request, _("وابستگی‌ها با موفقیت انتقال یافتند."))
            return super().form_valid(form)

'''غیرفعال کردن نقش'''
# @method_decorator(has_permission('delete_customuser'), name='dispatch')
@method_decorator(has_permission('Role_create'), name='dispatch')
class DeactivateRoleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        role = get_object_or_404(Role, pk=pk)

        if role.is_active:
            role.is_active = False
            role.save()
            messages.success(request, _("نقش با موفقیت غیرفعال شد."))
        else:
            messages.warning(request, _("این نقش قبلاً غیرفعال شده است."))

        return redirect('accounts:role_list')  # یا هر URL که مناسب است
# Auditlog.py
def audit_log_list(request):
    # دریافت تمام لاگ‌ها
    logs = AuditLog.objects.all().order_by('-timestamp')

    # فیلتر بر اساس تاریخ جلالی
    if 'date' in request.GET and request.GET['date']:
        jalali_date_str = request.GET['date']
        try:
            # تبدیل تاریخ جلالی به میلادی
            jalali_date = jdatetime.datetime.strptime(jalali_date_str, '%Y/%m/%d %H:%M:%S')
            gregorian_date = jalali_date.togregorian()
            logs = logs.filter(timestamp__date=gregorian_date)
        except ValueError:
            # اگر تاریخ نامعتبر بود، خطا را مدیریت کنید
            pass

    # فیلترها
    if 'user' in request.GET and request.GET['user']:
        logs = logs.filter(user_id=request.GET['user'])

    if 'action' in request.GET and request.GET['action']:
        logs = logs.filter(action=request.GET['action'])

    if 'model_name' in request.GET and request.GET['model_name']:
        logs = logs.filter(model_name=request.GET['model_name'])

    if 'related_object' in request.GET and request.GET['related_object']:
        logs = logs.filter(related_object__icontains=request.GET['related_object'])

    # کنترل نمایش لاگ‌های بدون تغییر
    show_empty = request.GET.get('show_empty', 'false').lower() == 'true'
    if not show_empty:
        logs = logs.exclude(changes="-")  # حذف ردیف‌های بدون تغییر

    # صفحه‌بندی
    paginator = Paginator(logs, 20)  # 20 لاگ در هر صفحه
    page_number = request.GET.get('page')
    logs_page = paginator.get_page(page_number)

    # لیست کاربران و مدل‌ها برای فیلترها
    users = User.objects.all()
    models = []
    for content_type in ContentType.objects.all():
        model_class = content_type.model_class()
        if model_class:
            models.append({
                'model_name': content_type.model,
                'verbose_name': model_class._meta.verbose_name,
                'verbose_name_plural': model_class._meta.verbose_name_plural
            })

    context = {
        'logs': logs_page,
        'users': users,
        'models': models,
        'show_empty': show_empty,  # برای مدیریت نمایش ردیف‌های بدون تغییر
    }
    return render(request, 'accounts/AuditLog/log_list.html', context)
# ویو داشبوردی منو ها
def user_management_view(request):
    user_menu = [
        {"label": "پروفایل کاربری", "url": "accounts:profile", "icon": "fas fa-user", "color": "primary",
         "permission": request.user.has_perm("users_view_userprofile")},
        {"label": "فهرست کاربران", "url": "accounts:user_list", "icon": "fas fa-users", "color": "success",
         "permission": request.user.has_perm("users_view_customuser")},
        {"label": "تغییر گذرواژه", "url": "accounts:password_change", "icon": "fas fa-key", "color": "info",
         "permission": request.user.has_perm("users_view_customuser")},
        {"label": "ثبت کاربر جدید", "url": "accounts:user_create", "icon": "fas fa-user-edit", "color": "warning",
         "permission": request.user.has_perm("users_add_customuser")},
        {"label": "نمایش رول", "url": "accounts:roles", "icon": "fas fa-user-shield", "color": "danger",
         "permission": request.user.has_perm("Role_view")},
        {"label": "نمایش گروه", "url": "accounts:group_list", "icon": "fas fa-users-cog", "color": "secondary",
         "permission": request.user.has_perm("MyGroup_can_view_group")},
        {"label": "نمایش لینک‌ها", "url": "software_links", "icon": "fas fa-link", "color": "secondary",
         "permission": request.user.has_perm("AppMenu_view")},
        {"label": "مدیریت قفل", "url": "set_lock", "icon": "fas fa-lock", "color": "dark",
         "permission": request.user.has_perm("AppMenu_view")},
        {"label": "نمایش لاگ کاربری", "url": "accounts:audit_log_list", "icon": "fas fa-users-viewfinder",
         "color": "secondary", "permission": request.user.has_perm("AuditLog_view")},
    ]

    return render(request, "accounts/accounts_index.html", {"user_menu": user_menu})
###############################################################################
# @method_decorator(has_permission('delete_customuser'), name='dispatch')
class SuperuserRequiredMixin(UserPassesTestMixin):
    """میکسین برای محدود کردن دسترسی فقط به سوپریوزرها"""

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        messages.error(self.request, "شما دسترسی لازم برای مشاهده این صفحه را ندارید.")
        return redirect('accounts:login')

@method_decorator(has_permission('ActiveUser_view'), name='dispatch')
class ActiveUserListView(SuperuserRequiredMixin, ListView):
    """لیست کاربران فعال"""
    model = ActiveUser
    template_name = 'accounts/usersCount/active_user_list.html'
    context_object_name = 'active_users'
    ordering = ['-login_time']

    def get_queryset(self):
        return ActiveUser.objects.filter(
            is_active=True,
            last_activity__gte=now() - datetime.timedelta(minutes=30)
        ).select_related('user').order_by('-last_activity')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['max_active_users'] = ActiveUser.get_max_active_users()  # استفاده از متد به جای ویژگی
        return context

@method_decorator(has_permission('ActiveUser_add'), name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class ActiveUserCreateView(SuperuserRequiredMixin, CreateView):
    """ایجاد کاربر فعال جدید"""
    model = ActiveUser
    form_class = ActiveUserForm
    template_name = 'accounts/usersCount/active_user_form.html'
    success_url = reverse_lazy('accounts:active_user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"کاربر فعال {self.object.user.username} با موفقیت اضافه شد.")
        logger.info(f"Superuser {self.request.user.username} created ActiveUser {self.object}")
        return response

@method_decorator(has_permission('ActiveUser_Update'), name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class ActiveUserUpdateView(SuperuserRequiredMixin, UpdateView):
    """ویرایش کاربر فعال"""
    model = ActiveUser
    form_class = ActiveUserForm
    template_name = 'accounts/usersCount/active_user_form.html'
    success_url = reverse_lazy('accounts:active_user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"کاربر فعال {self.object.user.username} با موفقیت به‌روزرسانی شد.")
        logger.info(f"Superuser {self.request.user.username} updated ActiveUser {self.object}")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'ویرایش'
        return context

@method_decorator(has_permission('ActiveUser_delete'), name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class ActiveUserDeleteView(SuperuserRequiredMixin, DeleteView):
    """حذف کاربر فعال"""
    model = ActiveUser
    template_name = 'accounts/usersCount/active_user_confirm_delete.html'
    success_url = reverse_lazy('accounts:active_user_list')

    def delete(self, request, *args, **kwargs):
        active_user = self.get_object()
        username = active_user.user.username
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f"کاربر فعال {username} با موفقیت حذف شد.")
        logger.info(f"Superuser {request.user.username} deleted ActiveUser {username}")
        return response

################# Security Lock Time  #########################
@method_decorator(staff_member_required, name='dispatch')
class BaseTimeLockView(LoginRequiredMixin, View):
    template_name = None

    def get_context_data(self, **kwargs):
        expiry_date, max_users, _, organization_name = TimeLockModel.get_latest_lock()
        # active_users_count = ActiveUser.objects.count()
        active_users_count = ActiveUser.objects.values("user").distinct().count()
        """اینجا تعداد کاربران منحصربه‌فرد (بر اساس user) رو می‌گیره، که درسته. ولی اگه بخوای فقط کاربران فعال رو بشمری، باید فیلتر is_active=True یا شرط last_activity رو اضافه کنی:"""
        from django.utils.timezone import now
        """فقط کاربرانی که واقعاً فعالن رو می‌شمره."""
        active_users_count = ActiveUser.objects.filter(
            is_active=True,
            last_activity__gte=now() - datetime.timedelta(minutes=30)
        ).values("user").distinct().count()

        is_locked = TimeLock.is_locked(self.request)

        days_remaining = None
        abs_days_remaining = None
        if expiry_date:
            today = jdatetime.date.today()
            days_remaining = (expiry_date - today).days
            abs_days_remaining = abs(days_remaining)
            print(f"Debug - Expiry: {expiry_date}, Days Remaining: {days_remaining}")

        context = {
            "current_expiry": expiry_date,
            "days_remaining": days_remaining,
            "abs_days_remaining": abs_days_remaining,
            "current_max_users": max_users,
            "active_users_count": active_users_count,
            "max_active_users": ActiveUser.MAX_ACTIVE_USERS,
            "is_locked": is_locked,
            "all_locks": TimeLockModel.objects.order_by('-created_at'),
            "organization_name": organization_name,  # اضافه کردن نام مجموعه
        }
        context.update(kwargs)
        return context

    def set_lock(self, expiry_date, max_users=None, organization_name=""):
        try:
            max_users = max_users if max_users is not None else ActiveUser.MAX_ACTIVE_USERS
            if not expiry_date:
                messages.error(self.request, "تاریخ انقضا نمی‌تواند خالی باشد.")
                return False
            with transaction.atomic():  # اجرای عملیات در یک تراکنش
                TimeLockModel.objects.filter(is_active=True).update(is_active=False)

                salt = secrets.token_hex(16)
                lock_key = TimeLockModel.create_lock_key(expiry_date, max_users, salt, organization_name)
                hash_value = hashlib.sha256(
                    f"{expiry_date.isoformat()}-{max_users}-{salt}-{organization_name}".encode()).hexdigest()

                TimeLockModel.objects.create(
                    lock_key=lock_key,
                    hash_value=hash_value,
                    salt=salt,
                    is_active=True,
                    organization_name=organization_name
                )

            messages.success(self.request, "قفل جدید با موفقیت ثبت شد و قفل‌های قبلی غیرفعال شدند.")
            return True
        except Exception as e:
            messages.error(self.request, f"خطا در ثبت قفل: {str(e)}")
            return False

# غیرفعال باشد کارایی ندارد
from django.db import transaction
@method_decorator(staff_member_required, name='dispatch')
class SetTimeLockView(BaseTimeLockView):
    template_name = "accounts/TimeLock/set_time_lock.html"
    success_url = reverse_lazy("accounts:set_time_lock")
    form_class = TimeLockForm

    # def set_lock(self, expiry_date, max_users, organization_name):
    #     return TimeLock.set_expiry_date(expiry_date, max_users, organization_name)
    def set_lock(self, expiry_date, max_users, organization_name):
        return super().set_lock(expiry_date, max_users, organization_name)

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data(form=self.form_class()))

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            expiry_date = form.cleaned_data['expiry_date']
            max_users = form.cleaned_data['max_active_users']
            organization_name = form.cleaned_data['organization_name']
            if self.set_lock(expiry_date, max_users, organization_name):
                return redirect(self.success_url)
        # messages.error(request, f"ورودی‌ها نامعتبر است: {'; '.join([f'{field}: {', '.join(errors)}' for field, errors in form.errors.items()])}")
        # return render(request, self.template_name, self.get_context_data(form=form))
        #

        errors_text = '; '.join([f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()])
        messages.error(request, f"ورودی‌ها نامعتبر است: {errors_text}")
        return render(request, self.template_name, self.get_context_data(form=form))


@method_decorator(staff_member_required, name='dispatch')
class TimeLockCreateView(FormView):
    """ایجاد یک تنظیم جدید برای قفل"""
    template_name = 'accounts/TimeLock/manage_timelock.html'
    form_class = TimeLockForm
    success_url = reverse_lazy('timelock_list')

    def form_valid(self, form):
        instance = form.save()
        return self.render_to_response(self.get_context_data(form=form, generated_hash=instance.hash_value))

@method_decorator(staff_member_required, name='dispatch')
@staff_member_required
def lock_status(request):
    """بررسی وضعیت آخرین قفل ذخیره‌شده"""
    expiry_date, max_users, hash_value = TimeLockModel.get_latest_lock()

    return JsonResponse({
        "expiry_date": expiry_date,
        "max_active_users": max_users,
        "hash_value": hash_value
    })

#########
# غیرفعال باشد کارایی ندارد
@method_decorator(staff_member_required, name='dispatch')
class TimeLockListView(BaseTimeLockView, ListView):
    """نمایش لیست تنظیمات قفل"""
    template_name = 'accounts/TimeLock/timelock_list.html'
    model = TimeLockModel
    context_object_name = 'all_locks'
    ordering = ['-created_at']

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())

@method_decorator(staff_member_required, name='dispatch')
class LockStatusView(BaseTimeLockView):
    """برگرداندن وضعیت قفل به‌صورت JSON"""

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return JsonResponse({
            "locked": context["is_locked"],
            "expiry_date": context["current_expiry"].strftime('%Y-%m-%d') if context["current_expiry"] else None,
            "active_users": context["active_users_count"],
            "max_active_users": context["max_active_users"],
        })

@login_required
def set_theme(request):
    if request.method == 'POST':
        theme = request.POST.get('theme')
        if theme in ['light', 'dark', 'blue', 'green']:
            # اگر پروفایل وجود ندارد، آن را ایجاد کنید
            if not hasattr(request.user, 'profile'):
                CustomProfile.objects.create(user=request.user, theme=theme)
            else:
                request.user.profile.theme = theme
                request.user.profile.save()
    return redirect(request.META.get('HTTP_REFERER', 'index'))

@login_required
def terminate_session(request, session_id):
    """قطع سشن قبلی و اجازه ورود با سشن جدید"""
    try:
        old_session = ActiveUser.objects.get(id=session_id, user=request.user)
        old_session.delete()
        messages.success(request, "سشن قبلی با موفقیت قطع شد. حالا می‌تونید با دستگاه جدید وارد بشید.")
        logger.info(f"سشن {old_session.session_key} برای کاربر {request.user.username} قطع شد.")
    except ActiveUser.DoesNotExist:
        messages.error(request, "سشن مورد نظر پیدا نشد.")
    return redirect('accounts:login')

#################################################################################
def active_users_view(request):
    # محاسبه تعداد کاربران فعال
    active_count = ActiveUser.objects.filter(
        last_activity__gte=now() - datetime.timedelta(minutes=30),
        is_active=True
    ).count()

    # دریافت حداکثر تعداد کاربران مجاز
    max_users = ActiveUser.get_max_active_users()

    context = {
        'active_users_count': active_count,
        'max_active_users': max_users,
        'refresh_interval': 60000,  # رفرش هر 60 ثانیه (برحسب میلی‌ثانیه)
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(context)

    return render(request, 'accounts/active_users.html', context)

