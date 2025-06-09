from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from usb_key_validator.views import validate_usb_key

app_name = 'usb_key_validator'

urlpatterns = [
    path('', validate_usb_key, name='validate'),
    # path('usb_manage/', manage_usb_license_view, name='manage_usb_license'),  # URL جدید
]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
