from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from Tanbakhsystem.views import Tanbakhsystem_DashboardView, TanbakhWorkflowView
from core.views import DashboardView

# from core.views import IndexView, ProjectListView, ProjectDetailView, AllLinksView
# from tanbakh.views import TanbakhListView, TanbakhDetailView, DashboardView

urlpatterns = [
                  path('admin/', admin.site.urls),
                  # path('', Tanbakhsystem_DashboardView.as_view(), name='dashboard'),
                  path('', DashboardView.as_view(), name='dashboard_flows'),
                  path('accounts/', include('accounts.urls')),
                  path('core/', include('core.urls')),
                  path('reports/', include('reports.urls')),
                  # path('Tanbakhsystem/', include('Tanbakhsystem.urls')),
                  path('tanbakh/', include('tanbakh.urls')),  # اضافه کردن اپلیکیشن tanbakh
                  # path('all_links', AllLinksView.as_view(),name='all_links'),  # اضافه کردن اپلیکیشن tanbakh
                  path('workflow/', TanbakhWorkflowView.as_view(), name='workflow'),

              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


                  # path('tanbakhs/',  DashboardView.as_view(), name='dashboard'),
                  # path('', Tanbakhsystem_DashboardView.as_view(), name='dashboard'),  # داشبورد به عنوان صفحه اصلی
                  # path('', IndexView.as_view(), name='index'),
                  # path('projects/', ProjectListView.as_view(), name='project_list'),
                  # path('projects/<int:pk>/', ProjectDetailView.as_view(), name='project_detail'),
                  # path('tanbakhs/<int:pk>/', TanbakhDetailView.as_view(), name='tanbakh_detail'),
                  # path('login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
                  # path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
