from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('inbox/', views.notifications_inbox, name='inbox'),
    path('unread/', views.unread_notifications, name='unread'),
    path('delete/<int:notification_id>/', views.delete_notification, name='delete'),
    path('mark-as-read/<int:notification_id>/', views.mark_as_read, name='mark_as_read'),
    path('api/count/', views.test_unread_count, name='test_unread_count'),
    path('api/list/', views.get_notifications, name='get_notifications'),
]

