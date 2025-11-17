from importlib import import_module

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import include, path
from django.views.generic.base import RedirectView
from django.views.i18n import JavaScriptCatalog

from accounts.RCMS_Lock.views import lock_status
from accounts.views import LockStatusView, SetTimeLockView, TimeLockListView
from BudgetsSystem import views
from BudgetsSystem.Dashboard_Project.DashboardView_1 import \
    TabbedFinancialDashboardView
from BudgetsSystem.view.view_Dashboard import (DashboardView,
                                               ReportsDashboardMainView)
from BudgetsSystem.views import GuideView, TanbakhWorkflowView, soft_Help
from version_tracker.admin_backup import backup_admin

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('backup-admin/', backup_admin.urls),
                  path('backup/', include('version_tracker.backup_urls')),

                  # Specific patterns first
                  path('dashboard/', TabbedFinancialDashboardView.as_view(), name='index1'),
                  path('accounts/', include('accounts.urls')),
                  path('', include('core.urls')),
                  # داشبورد گزارش‌ها: استفاده از روتر جدید اپ reports.dashboard
                  path('reports/dashboard/', include('reports.dashboard.urls')),
                  path('reports/', include('reports.urls')),  # اضافه کردن اپلیکیشن reports
                  path('tankhah/', include('tankhah.urls')),  # اضافه کردن اپلیکیشن tankhah
                  path('version_tracker/', include('version_tracker.urls')),  # اضافه کردن اپلیکیشن tankhah
                  path('budgets/', include('budgets.urls')),  # اضافه کردن اپلیکیشن بودجه
                  path('pr/', include('purchase_requests.urls')), # اضافه کردن اپلیکیشن درخواست کالا
                  path('workflow/', TanbakhWorkflowView.as_view(), name='workflow'),  # help workflow
                  path('inbox/notifications/', include('notificationApp.urls', namespace='notifications')),
                  path('about/', views.about, name='about'),
                  path("lock-status/", lock_status, name="lock_status"),
                  path('set-lock/', SetTimeLockView.as_view(), name='set_time_lock'),
                  path('view-locks/', TimeLockListView.as_view(), name='timelock_list'),
                  path('js-catalog', JavaScriptCatalog.as_view(), name='js-catalog'),
                  path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('admin/img/favicon.ico')), name='favicon'),
                  path('guide/', GuideView.as_view(), name='guide'),
                  path('guide/soft_Help/', soft_Help , name='soft_help'),

                  # Default pattern last
                  path('', DashboardView.as_view(), name='index'),
                #   path("select2/", include("django_select2.urls")),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


urlpatterns +=[
    path('usb-key-validator/', include('usb_key_validator.urls')),
]# validate_usb_key

# ثبت مسیرهای تست فقط زمانی که ماژول test_urls وجود داشته باشد (برای جلوگیری از خطا در تولید)
try:
    import_module('test_urls')
except ModuleNotFoundError:
    pass
else:
    urlpatterns.append(path('test/', include('test_urls')))
