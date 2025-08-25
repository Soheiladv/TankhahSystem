<<<<<<< HEAD
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.shortcuts import render, redirect

from core.PermissionBase import PermissionBaseView
=======
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.shortcuts import render, redirect
>>>>>>> 171b55a74efe3adb976919af53d3bd582bb2266e
from .models import AppVersion, FinalVersion, CodeChangeLog, FileHash
from .forms import AppVersionForm
import logging
logger = logging.getLogger(__name__)
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render
from .models import AppVersion

def version_index_view(request):
    # دریافت آخرین نسخه برای هر اپلیکیشن
    # latest_versions = AppVersion.objects.order_by("app_name", "-created_at").distinct("app_name")

    # لیست کارت‌ها با اضافه کردن نمایش نسخه
    cards = [
        {
            "title": "مدیریت نسخه‌ها",
            "icon": "fas fa-code-branch",
            "items": [
                {"label": "لیست نسخه‌ها", "url": "latest_version", "icon": "fas fa-list", "color": "info", "permission": True},
                {"label": "وضعیت نسخه‌ها", "url": "appversion_list", "icon": "fas fa-list", "color": "info", "permission": True},
                {"label": "جزئیات نسخه", "url": "appversion_detail", "icon": "fas fa-info-circle", "color": "primary", "permission": True, "needs_pk": True},
                {"label": "حذف نسخه", "url": "appversion_delete", "icon": "fas fa-trash", "color": "danger", "permission": True, "needs_pk": True},
                {"label": "تغییرات کد", "url": "codechangelog_list", "icon": "fas fa-file-code", "color": "success", "permission": True},
                {"label": "جزئیات تغییرات کد", "url": "codechangelog_detail", "icon": "fas fa-code", "color": "secondary", "permission": True, "needs_pk": True},
                {"label": "هش فایل‌ها", "url": "filehash_list", "icon": "fas fa-fingerprint", "color": "dark", "permission": True},
                {"label": "راهنمای نسخه‌بندی", "url": "versioning_guide", "icon": "fas fa-book", "color": "primary", "permission": True},
            ],
        },
    ]

    return render(request, "versions/version_index.html", {
        "cards": cards,# "latest_versions": latest_versions
    })


class AppVersionListView(ListView):
    model = AppVersion
    template_name = 'versions/appversion_list.html'
    context_object_name = 'app_versions'
    paginate_by = 10

    def get_queryset(self):
        """فیلتر و مرتب‌سازی نسخه‌ها بر اساس نام فارسی و سایر فیلترها"""
        queryset = super().get_queryset().order_by('-release_date')

        # فیلتر بر اساس نام فارسی اپلیکیشن
        app_name_fa = self.request.GET.get('app_name_fa')
        if app_name_fa:
            queryset = queryset.filter(app_name__icontains=app_name_fa)

        # فیلتر بر اساس نوع نسخه
        version_type = self.request.GET.get('version_type')
        if version_type:
            queryset = queryset.filter(version_type=version_type)

        # فیلتر بر اساس شماره نسخه (major, minor, patch, build)
        major = self.request.GET.get('major')
        minor = self.request.GET.get('minor')
        patch = self.request.GET.get('patch')
        build = self.request.GET.get('build')

        if major:
            queryset = queryset.filter(major=major)
        if minor:
            queryset = queryset.filter(minor=minor)
        if patch:
            queryset = queryset.filter(patch=patch)
        if build:
            queryset = queryset.filter(build=build)

        return queryset

    def get_context_data(self, **kwargs):
        """اضافه کردن داده‌های اضافی به قالب"""
        context = super().get_context_data(**kwargs)

        # افزودن فیلترها به context
        context['app_name_fa_filter'] = self.request.GET.get('app_name_fa', '')
        context['version_type_filter'] = self.request.GET.get('version_type', '')
        context['major_filter'] = self.request.GET.get('major', '')
        context['minor_filter'] = self.request.GET.get('minor', '')
        context['patch_filter'] = self.request.GET.get('patch', '')
        context['build_filter'] = self.request.GET.get('build', '')

        # افزودن لیست نوع‌های نسخه
        context['version_types'] = AppVersion.VERSION_TYPES

        # افزودن پیام‌ها به context
        context['messages'] = messages.get_messages(self.request)

        return context

class AppVersionDetailView(DetailView):
    """نمایش جزئیات یک نسخه اپلیکیشن"""
    model = AppVersion
    template_name = 'versions/appversion_detail.html'
    context_object_name = 'version'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['changes'] = CodeChangeLog.objects.filter(version=self.object)
        context['file_hashes'] = FileHash.objects.filter(app_version=self.object)
        context['final_version'] = FinalVersion.objects.first()
        return context

class AppVersionCreateView(CreateView):
    """ایجاد نسخه جدید (به صورت دستی غیرفعال شده، فقط برای تست)"""
    model = AppVersion
    form_class = AppVersionForm
    template_name = 'versions/appversion_form.html'
    success_url = reverse_lazy('appversion_list')
    messages_url = reverse_lazy('appversion_detail')

    def form_valid(self, form):
        messages.success(self.request, "نسخه جدید با موفقیت ایجاد شد.")
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        messages.warning(request, "ایجاد نسخه جدید به‌صورت دستی غیرفعال است. از سیستم خودکار استفاده کنید.")
        return redirect('appversion_list')

class AppVersionUpdateView(UpdateView):
    """ویرایش نسخه (به صورت دستی غیرفعال شده)"""
    model = AppVersion
    form_class = AppVersionForm
    template_name = 'versions/appversion_form.html'
    success_url = reverse_lazy('appversion_list')

    def form_valid(self, form):
        messages.success(self.request, "نسخه با موفقیت ویرایش شد.")
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        messages.warning(request, "ویرایش نسخه به‌صورت دستی غیرفعال است.")
        return redirect('appversion_list')

class AppVersionDeleteView(DeleteView):
    """حذف نسخه"""
    model = AppVersion
    template_name = 'versions/appversion_confirm_delete.html'
    success_url = reverse_lazy('appversion_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, "نسخه با موفقیت حذف شد.")
        return super().delete(request, *args, **kwargs)

def latest_version_view(request):
    """نمایش نسخه کامل نهایی و آخرین نسخه اپلیکیشن"""
    """نمایش صفحه اصلی با نسخه نهایی و تگ"""
    # final_version = FinalVersion.objects.first()
    latest_app_version = AppVersion.objects.order_by('-release_date').first()
    final_version = FinalVersion.objects.filter(is_active=True).first()
    app_versions = AppVersion.objects.all().order_by('-release_date')[:10]  # 10 نسخه آخر

    context = {
        'final_version': final_version.version_number if final_version else "نسخه نهایی تعریف نشده",
        'release_date': final_version.release_date if final_version else None,
        'app_versions': app_versions,
    }
    return render(request, 'versions/lastVersion.html', context)

# ویوی جدید برای تغییرات کد
class CodeChangeLogListView(ListView):
    """نمایش لیست تمام تغییرات کد"""
    model = CodeChangeLog
    template_name = 'versions/codechangelog_list.html'
    context_object_name = 'changes'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        app_name = self.request.GET.get('app_name')
        if app_name:
            queryset = queryset.filter(version__app_name=app_name)
        return queryset.order_by('-change_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['final_version'] = FinalVersion.objects.first()

        # گرفتن نام‌های منحصربه‌فرد اپلیکیشن‌ها و نام فارسی
        app_names = AppVersion.objects.values('app_name').distinct()
        context['app_versions'] = [
            {
                'app_name': app['app_name'],
                'app_name_fa': AppVersion.objects.filter(app_name=app['app_name']).first().get_app_name_fa()
            }
            for app in app_names
        ]
        return context

class CodeChangeLogDetailView(DetailView):
    """نمایش جزئیات یک تغییر کد"""
    model = CodeChangeLog
    template_name = 'versions/codechangelog_detail.html'
    context_object_name = 'change'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['diff'] = list(self.object.get_diff())  # تفاوت‌ها به صورت لیست
        context['final_version'] = FinalVersion.objects.first()
        return context

class FileHashListView(ListView):
    model = FileHash
    template_name = 'versions/filehash_list.html'
    context_object_name = 'file_hashes'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        app_name = self.request.GET.get('app_name')
        if app_name:
            queryset = queryset.filter(app_version__app_name=app_name)
        return queryset.order_by('-timestamp')

#############
MONITORED_APPS = {'RCMS', 'hse', 'Reservations', 'facility', 'core', 'accounts', 'version_tracker'}
from django.apps import apps
<<<<<<< HEAD
@login_required(login_url='/accounts/login/')
def update_versions_view1(request):
=======

def update_versions_view(request):
    """به‌روزرسانی نسخه‌ها از طریق رابط کاربری"""
>>>>>>> 171b55a74efe3adb976919af53d3bd582bb2266e
    if request.method == 'POST':
        updates = {}
        try:
            for app_config in apps.get_app_configs():
                if app_config.name not in MONITORED_APPS:
                    logger.debug(f"Skipping app: {app_config.name} (not in monitored apps)")
                    continue
<<<<<<< HEAD
=======

>>>>>>> 171b55a74efe3adb976919af53d3bd582bb2266e
                app_name = app_config.name
                app_path = app_config.path
                logger.info(f"Checking {app_name} for changes...")
                new_version = AppVersion.update_version(app_path, app_name)
                if new_version:
                    updates[app_name] = new_version.version_number

            if updates:
<<<<<<< HEAD
                FinalVersion.calculate_final_version()
=======
                FinalVersion.calculate_final_version()  # به‌روزرسانی نسخه نهایی
>>>>>>> 171b55a74efe3adb976919af53d3bd582bb2266e
                messages.success(request, f"نسخه‌ها به‌روزرسانی شدند: {updates}")
                logger.info(f"Versions updated: {updates}")
            else:
                messages.info(request, "هیچ تغییری تشخیص داده نشد.")
                logger.info("No changes detected.")
        except Exception as e:
            messages.error(request, f"خطا در به‌روزرسانی: {str(e)}")
            logger.error(f"Error updating versions: {str(e)}", exc_info=True)

<<<<<<< HEAD
    try:
        final_version_obj = FinalVersion.objects.filter(is_active=True).latest('release_date')
        final_version = final_version_obj.version_number
        release_date = final_version_obj.release_date
    except FinalVersion.DoesNotExist:
        final_version = None
        release_date = None

    app_versions = AppVersion.objects.all().order_by('-release_date')[:10]
    context = {
        'final_version': final_version,
        'release_date': release_date,
        'app_versions': app_versions,
    }
    return render(request, 'versions/lastVersion.html', context)

 
@login_required(login_url='/accounts/login/')
def update_versions_view(request):
    if request.method == 'POST':
        updates = {}
        try:
            for app_config in apps.get_app_configs():
                if app_config.name not in MONITORED_APPS:
                    logger.debug(f"Skipping app: {app_config.name}")
                    continue
                app_name = app_config.name
                app_path = app_config.path
                new_version = AppVersion.update_version(app_path, app_name)
                if new_version:
                    updates[app_name] = new_version.version_number

            if updates:
                FinalVersion.calculate_final_version()
                messages.success(request, f"نسخه‌ها به‌روزرسانی شدند: {updates}")
            else:
                messages.info(request, "هیچ تغییری تشخیص داده نشد.")
        except Exception as e:
            messages.error(request, f"خطا در به‌روزرسانی: {str(e)}")

    try:
        final_version_obj = FinalVersion.objects.filter(is_active=True).latest('release_date')
        final_version = final_version_obj.version_number
        release_date = final_version_obj.release_date
    except FinalVersion.DoesNotExist:
        final_version = None
        release_date = None

    app_versions = AppVersion.objects.all().order_by('-release_date')[:10]
    context = {
        'final_version': final_version,
        'release_date': release_date,
        'app_versions': app_versions,
    }
    return render(request, 'versions/lastVersion.html', context)
=======
    # نمایش صفحه Index با اطلاعات فعلی
    final_version = FinalVersion.objects.filter(is_active=True).first()
    app_versions = AppVersion.objects.all().order_by('-release_date')[:10]

    context = {
        'final_version': final_version.version_number if final_version else "نسخه نهایی تعریف نشده",
        'release_date': final_version.release_date if final_version else None,
        'app_versions': app_versions,
    }
    return render(request, 'versions/lastVersion.html', context)
>>>>>>> 171b55a74efe3adb976919af53d3bd582bb2266e
