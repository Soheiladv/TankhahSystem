from django.urls import path
from .views import (
    IndexView, OrganizationListView, OrganizationDetailView, OrganizationCreateView, OrganizationUpdateView,
    OrganizationDeleteView,
    ProjectListView, ProjectDetailView, ProjectCreateView, ProjectUpdateView, ProjectDeleteView, AllLinksView,DashboardView
)

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('organizations/', OrganizationListView.as_view(), name='organization_list'),
    path('organization/<int:pk>/', OrganizationDetailView.as_view(), name='organization_detail'),
    path('organization/create/', OrganizationCreateView.as_view(), name='organization_create'),
    path('organization/<int:pk>/update/', OrganizationUpdateView.as_view(), name='organization_update'),
    path('organization/<int:pk>/delete/', OrganizationDeleteView.as_view(), name='organization_delete'),
    path('projects/', ProjectListView.as_view(), name='project_list'),
    path('project/<int:pk>/', ProjectDetailView.as_view(), name='project_detail'),
    path('project/create/', ProjectCreateView.as_view(), name='project_create'),
    path('project/<int:pk>/update/', ProjectUpdateView.as_view(), name='project_update'),
    path('project/<int:pk>/delete/', ProjectDeleteView.as_view(), name='project_delete'),

    path('all_links/', AllLinksView.as_view(), name='all_links'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),

]