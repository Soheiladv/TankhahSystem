from django.urls import path
from .admin_backup import (
    backup_list_view,
    backup_delete_view,
    backup_encrypt_view,
    backup_create_view,
    backup_restore_view,
    backup_mysql_view
)
from .schedule_views import (
    schedule_list_view,
    schedule_create_view,
    schedule_edit_view,
    schedule_detail_view,
    schedule_delete_view,
    schedule_toggle_view,
    schedule_run_view,
    schedule_logs_view,
    schedule_test_view,
    schedule_ajax_status
)
from .backup_location_views import (
    backup_locations_list,
    backup_location_detail,
    backup_location_test,
    backup_location_set_default,
    backup_location_toggle_status,
    backup_location_create,
    backup_location_edit,
    backup_location_delete,
    backup_location_ajax_status
)

app_name = 'backup'

urlpatterns = [
    # URLs اصلی پشتیبان‌گیری
    path('', backup_list_view, name='list'),
    path('create/', backup_create_view, name='create'),
    path('delete/<str:file_name>/', backup_delete_view, name='delete'),
    path('encrypt/<str:file_name>/', backup_encrypt_view, name='encrypt'),
    path('restore/<str:file_name>/', backup_restore_view, name='restore'),
    path('mysql/', backup_mysql_view, name='mysql'),
    
    # URLs اسکچول‌های پشتیبان‌گیری
    path('schedule/', schedule_list_view, name='schedule_list'),
    path('schedule/create/', schedule_create_view, name='schedule_create'),
    path('schedule/<int:schedule_id>/', schedule_detail_view, name='schedule_detail'),
    path('schedule/<int:schedule_id>/edit/', schedule_edit_view, name='schedule_edit'),
    path('schedule/<int:schedule_id>/delete/', schedule_delete_view, name='schedule_delete'),
    path('schedule/<int:schedule_id>/toggle/', schedule_toggle_view, name='schedule_toggle'),
    path('schedule/<int:schedule_id>/run/', schedule_run_view, name='schedule_run'),
    path('schedule/logs/', schedule_logs_view, name='schedule_logs'),
    path('schedule/test/', schedule_test_view, name='schedule_test'),
    path('schedule/<int:schedule_id>/status/', schedule_ajax_status, name='schedule_ajax_status'),
    
    # URLs مسیرهای پشتیبان‌گیری
    path('locations/', backup_locations_list, name='locations_list'),
    path('locations/create/', backup_location_create, name='location_create'),
    path('locations/<int:location_id>/', backup_location_detail, name='location_detail'),
    path('locations/<int:location_id>/edit/', backup_location_edit, name='location_edit'),
    path('locations/<int:location_id>/delete/', backup_location_delete, name='location_delete'),
    path('locations/<int:location_id>/test/', backup_location_test, name='location_test'),
    path('locations/<int:location_id>/set-default/', backup_location_set_default, name='location_set_default'),
    path('locations/<int:location_id>/toggle/', backup_location_toggle_status, name='location_toggle'),
    path('locations/<int:location_id>/status/', backup_location_ajax_status, name='location_ajax_status'),
]
