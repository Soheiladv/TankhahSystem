from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('inbox/', views.notifications_inbox, name='inbox'),
    path('unread/', views.unread_notifications, name='unread'),
    path('delete/<int:notification_id>/', views.delete_notification, name='delete'),
    path('mark-as-read/<int:notification_id>/', views.mark_as_read, name='mark_as_read'),
    path('mark-viewed/<int:notification_id>/', views.mark_notification_viewed, name='mark_viewed'),
    path('api/count/', views.test_unread_count, name='test_unread_count'),
    path('api/list/', views.get_notifications, name='get_notifications'),
    path('admin/dashboard/', views.admin_notifications_dashboard, name='admin_dashboard'),
    path('creator/<int:user_id>/', views.creator_notifications_view, name='creator_view'),
]

