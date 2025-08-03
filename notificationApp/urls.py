from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notifications_inbox, name='notifications_inbox'),
    path('unread/', views.unread_notifications, name='mark_all_as_read'),
    path('delete/<int:notification_id>/', views.delete_notification, name='delete'),
    path('api/count/', views.test_unread_count, name='test_unread_count'),
    path('api/list/', views.get_notifications, name='get_notifications'),
]

