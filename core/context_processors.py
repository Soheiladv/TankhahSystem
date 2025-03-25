# core/context_processors.py
from version_tracker.models import AppVersion  # فرض می‌کنم مدلت اینه

def version_info(request):
    try:
        final_version = AppVersion.objects.filter(is_final=True).latest('release_date').version_number
    except AppVersion.DoesNotExist:
        final_version = None  # یا یه مقدار پیش‌فرض مثل "0.0.0"
    return {'final_version': final_version}