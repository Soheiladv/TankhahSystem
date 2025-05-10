# core/context_processors.py

from version_tracker.models import AppVersion  # فرض می‌کنم مدلت اینه

def version_info(request):
    try:
        final_version = AppVersion.objects.filter(is_final=True).latest('release_date').version_number
    except AppVersion.DoesNotExist:
        final_version = None  # یا یه مقدار پیش‌فرض مثل "0.0.0"
    return {'final_version': final_version}



def notifications(request):
    if request.user.is_authenticated:
        from notifications.models import Notification  # مدل را مستقیماً از پکیج وارد کنید
        unread_notifications = Notification.objects.filter(recipient=request.user, unread=True)
    else:
        unread_notifications = []
    return {'unread_notifications': unread_notifications}

# def notifications(request):
#     if request.user.is_authenticated:
#         from notifications.views import Notification
#         unread_notifications = Notification.objects.filter(user=request.user, unread=False)
#     else:
#         unread_notifications = []
#     return {'unread_notifications': unread_notifications}
