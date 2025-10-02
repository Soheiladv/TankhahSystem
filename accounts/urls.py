from .DashboardReset import DatabaseResetView, DatabaseManageView, DatabaseBackupRestoreView, DatabaseBackupView, \
    new_DatabaseBackupRestoreView, DatabaseModelGraphView
from .Heartbeat import heartbeat_view
app_name = 'accounts'  # این خط باید وجود داشته باشد
from atexit import register
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
# from . import views
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.urls import path
from accounts import views
from accounts.views import (AdvancedProfileSearchView, user_management_view, dashboard_view,
                            ActiveUserListView, TimeLockCreateView, TimeLockListView,
                            SetTimeLockView, lock_status, set_theme, terminate_session,
                            ProfileUpdateView, active_users_view, custom_theme_designer, apply_custom_theme,
                            )
from .views import (
    RoleListView, RoleCreateView, RoleUpdateView, RoleDeleteView,
    UserListView, UserCreateView, UserEditView, UserDeleteView,
    admin_dashboard, it_staff_dashboard, requester_dashboard, default_dashboard,
    UserChangePasswordView, reset_password_to_default, profile_update_success, GroupListView,
    GroupCreateView
)
from .views import TransferRoleDependenciesView, DeactivateRoleView

#########################################################
# from .views import user_list_and_reset_password
urlpatterns = [
                  path("admin_dashboard/", dashboard_view, name="admin_dashboard"),

                  path('user_management_view/', user_management_view, name='user_management_view'),
                  # Authentication URLs
                  path('logout/', auth_views.LogoutView.as_view(), name='logout'),
                  # path('logout/', auth_views.logoutView.as_view(next_page='accounts:login'), name='logout'),

                  path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),

                  # path('Logout/', auth_views.LogoutView.as_view(), name='Logout'),

                  # path('signup/',   views.signup,   name='signup'),
                  path('register/', register, name='register'),
                  # path('RegisterView/',  views.RegisterView.as_view(), name='RegisterView'),
                  # path('profile/',   profile, name='profile'),
                  # path('profile/',   views.profile, name='profile'  ),

                  # path('users/', UserListView.as_view(), name='user_list'),
                  # path('login/',  views.CustomLoginView.as_view(template_name='accounts/login.html'), name='login'),

                  path('PasswordChangeView/', auth_views.PasswordChangeView.as_view(
                      template_name='accounts/password_reset_form.html'), name='PasswordChangeView'),
                  #
                  # path('logout/', auth_views.PasswordResetCompleteView.as_view(
                  #     template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),
                  #
                  # path('logout/', auth_views.PasswordChangeDoneView.as_view(
                  #     template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),
                  # path('logout/', auth_views.PasswordResetView.as_view(
                  #     template_name='accounts/password_reset_email.html'), name='password_reset_email'),
                  # path('logout/', auth_views.PasswordResetConfirmView.as_view(
                  #     template_name='accounts/password_reset_confirm.html'), name='password_reset_confirm'),
                  # path('logout/', auth_views.PasswordResetDoneView.as_view(
                  #     template_name='accounts/password_reset_done.html'), name='password_reset_done'),

                  path('password_change/',
                       PasswordChangeView.as_view(template_name='accounts/password_change_form.html'),
                       name='password_change'),
                  path('password_change/done/', PasswordChangeDoneView.as_view(
                      template_name='accounts/password_change_done.html'), name='password_change_done'),

                  # path('reset_password/<int:user_id>/', views.reset_password, name='reset_password'),

                  # path('user_list_and_reset_password/',  views.user_list_and_reset_password,  name='user_list_and_reset_password'),

                  # path('Profile_update/<int:pk>/',   views.Profile_update.as_view, name='Profile_update'  ),
                  ##################################
                  # path('profiles/', ProfileListView.as_view(), name='profile_list'),
                  # path('profiles/<int:pk>/', ProfileDetailView.as_view(), name='profile_detail'),
                  # path('profiles/create/', ProfileCreateView.as_view(), name='profile_create'),
                  # path('profiles/<int:pk>/update/', ProfileUpdateView.as_view(), name='profile_update'),
                  # path('profiles/<int:pk>/delete/', ProfileDeleteView.as_view(), name='profile_delete'),

                  # path('advanced-search/', AdvancedProfileSearchView.as_view(), name='advanced_profile_search'),

                  ############### New Admin
                  ##########################################################
                  # path('management/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
                  path('management/users/', views.UserListView.as_view(), name='user_list'),
                  path('management/groups/', views.GroupListView.as_view(), name='group_list'),
                  # path('management/profiles/', views.ProfileListView.as_view(), name='profile_list'),
                  # سایر مسیرهای مربوط به پنل مدیریت

                  # path('user/create/', views.user_create, name='user_create'),
                  ################################ Add Rol Crud ###############################################################
                  path("roles/", RoleListView.as_view(), name="role_list"),
                  path("roles/create/", RoleCreateView.as_view(), name="role_create"),
                  path("roles/update/<int:pk>/", RoleUpdateView.as_view(), name="role_update"),
                  path("roles/delete/<int:pk>/", RoleDeleteView.as_view(), name="role_delete"),
                  ################################ Add Rol MyGRoup ###############################################################

                  ##########################################################

                  # Dashboard URLs
                  path("admin_dashboard/", admin_dashboard, name="admin_dashboard"),
                  path("it_staff_dashboard/", it_staff_dashboard, name="it_staff_dashboard"),
                  path("requester_dashboard/", requester_dashboard, name="requester_dashboard"),
                  path("default_dashboard/", default_dashboard, name="default_dashboard"),

                  # User Management URLs
                  path('users/', UserListView.as_view(), name='user_list'),

                  path('users/create/', UserCreateView.as_view(), name='user_create'),
                  path('users/<int:pk>/edit/', UserEditView.as_view(), name='user_edit'),
                  path('users/<int:pk>/delete/', UserDeleteView.as_view(), name='user_delete'),

                  # Password Management URLs
                  path('change-password/<int:pk>/', UserChangePasswordView.as_view(), name='user_change_password'),
                  path('reset_password_to_default/<int:user_id>/', reset_password_to_default,
                       name='reset_password_to_default'),

                  # Profile URLs
                  # path('profile/update/', profile_update_view, name='profile_update'),
                  path('profile/update/', ProfileUpdateView.as_view() , name='profile_update'),
                  path('profile/update/success/', profile_update_success, name='profile_update_success'),
                  # path('profile/update/success/', profile_update_success_view, name='profile_update_success'),
                  # مسیر جدید

                  # Password Reset URLs
                  path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
                  path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
                  path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(),
                       name='password_reset_confirm'),
                  path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
                  path('password_change/',
                       auth_views.PasswordChangeView.as_view(template_name='users/password/password_change_form.html'),
                       name='password_change'),
                  path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
                      template_name='users/password/password_change_done.html'), name='password_change_done'),

                  # Group URLs
                  path('groups/', GroupListView.as_view(), name='group_list'),  # اصلاح شده
                  path('groups/create/', GroupCreateView.as_view(), name='group_create'),  # اصلاح شده
                  # path('groups/<int:pk>/update/', GroupUpdateView.as_view(), name='group_update'),  # اصلاح شده
                  # path('groups/<int:pk>/delete/', GroupDeleteView.as_view(), name='group_delete'),  # اصلاح شده
                  #
                  path('groups/update/<int:pk>/', views.GroupUpdateView.as_view(), name='group_update'),
                  path('groups/delete/<int:pk>/', views.GroupDeleteView.as_view(), name='group_delete'),
                  path('groups/assign/<int:pk>/', views.AssignUsersToGroupView.as_view(), name='assign_users_to_group'),
                  path('groups/users/<int:pk>/', views.GroupUserListView.as_view(), name='group_user_list'),

                  # Role URLs
                  # ============================
                  path('roles/', RoleListView.as_view(), name='roles'),
                  path('roles/create/', RoleCreateView.as_view(), name='role_create'),

                  path('roles/<int:pk>/edit/', RoleUpdateView.as_view(), name='role_update'),
                  path('roles/<int:pk>/delete/', RoleDeleteView.as_view(), name='role_delete'),
                  path('role/<int:pk>/print/', views.RolePrintView.as_view(), name='role_print'),

                  #### تغییر وابستگی در خذف کاربر از رول
                  path('roles/<int:pk>/transfer-dependencies/', TransferRoleDependenciesView.as_view(),
                       name='transfer_role_dependencies'),
                  path('roles/<int:pk>/deactivate/', DeactivateRoleView.as_view(), name='deactivate_role'),

                  path('roles/<int:pk>/deactivate/', DeactivateRoleView.as_view(), name='deactivate_role'),
                  # ============================
                  # Profile URL
                  path('profile/', views.ProfileView.as_view(), name='profile'),  # صفحه اصلی پروفایل (ایجاد/ویرایش)

                  # path('profile/<int:pk>/', views.ProfileView.as_view(), name='profile'),
                  path('profile/create/', views.ProfileCreateView.as_view(), name='profile_create'),
                  path('profile/<int:user_id>/', views.ProfileUpdateView.as_view() , name='profile_update'),

                  path('profile/<int:user_id>/', views.profile_detail, name='profile_detail'),

                  path('profile/delete/', views.profile_delete, name='profile_delete'),  # حذف پروفایل
                  path('advanced-search/', AdvancedProfileSearchView.as_view(), name='advanced_profile_search'),


                  ## AuditLog
                  path('audit-logs/', views.audit_log_list, name='audit_log_list'),
  path('audit-logs/test/create/', views.create_test_audit_log, name='audit_log_test_create'),
  path('my/session-activity/', views.my_session_activity, name='my_session_activity'),
                  # User Limitation
                  path('active-users/', ActiveUserListView.as_view(), name='active_user_list'),
                  path('active-users/create/', views.ActiveUserCreateView.as_view(), name='active_user_create'),
                  path('active-users/<int:pk>/update/', views.ActiveUserUpdateView.as_view(),
                       name='active_user_update'),
                  path('active-users/<int:pk>/delete/', views.ActiveUserDeleteView.as_view(),
                       name='active_user_delete'),
                  # Security lock Time
                  path('manage-timelock/', TimeLockCreateView.as_view(), name='manage_timelock'),
                  path('timelock-list/', TimeLockListView.as_view(), name='timelock_list'),
                  #SetTimeLockView
                  path('set_time_lock/', SetTimeLockView.as_view(), name='set_time_lock'),
                  path('lock_status/',lock_status , name='lock_status'),

                  # Heartbeat
                  path('heartbeat/', heartbeat_view, name='heartbeat'),

                  path('set_theme/', set_theme, name='set_theme'),# User Color
                  path('custom-theme-designer/', custom_theme_designer, name='custom_theme_designer'),
                  path('apply-custom-theme/', apply_custom_theme, name='apply_custom_theme'),

                  path('get_cities/', views.get_cities, name='get_cities'),  # گرفتن شهر

              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns+=[
    path('terminate-session/<int:session_id>/',  terminate_session, name='terminate_session'),
             ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns+=[
    path('active-users/', active_users_view, name='active_users'),
]#تعداد کاربر فعال سیستم

urlpatterns += [
    path('reset-database/', DatabaseResetView.as_view(), name='reset_database'),
    path('database-manage/', DatabaseManageView.as_view(), name='database_manage'),
    path('databasebackuprestore/', DatabaseBackupRestoreView.as_view(), name='databasebackuprestore'),
    path('databasebackup/', DatabaseBackupView.as_view(), name='databasebackup'),
                   path('new_databasebackup/', new_DatabaseBackupRestoreView.as_view(), name='new_databasebackup'),

               ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # Dashboard reset

urlpatterns += [
                   path('model_graph/', DatabaseModelGraphView.as_view(), name='model_graph'),

               ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # Models Graphe