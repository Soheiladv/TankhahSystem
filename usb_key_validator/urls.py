from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from usb_key_validator.views import validate_usb_key
from usb_key_validator.enhanced_views import (
    enhanced_usb_validation,
    dongle_ajax_status,
    dongle_ajax_action,
    dongle_dashboard,
    edit_dongle_info,
    create_company_dongle
)

app_name = 'usb_key_validator'

urlpatterns = [
    path('', validate_usb_key, name='validate'),
    path('enhanced/', enhanced_usb_validation, name='enhanced_validate'),
    path('dashboard/', dongle_dashboard, name='dongle_dashboard'),
    path('ajax/status/', dongle_ajax_status, name='dongle_ajax_status'),
    path('ajax/action/', dongle_ajax_action, name='dongle_ajax_action'),
    path('edit/<str:device_id>/', edit_dongle_info, name='edit_dongle'),
    path('create-company/', create_company_dongle, name='create_company_dongle'),
    # path('usb_manage/', manage_usb_license_view, name='manage_usb_license'),  # URL جدید
]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
