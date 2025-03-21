from django.urls import path
from .views import AppVersionListView, AppVersionDetailView, AppVersionCreateView, AppVersionUpdateView, \
    AppVersionDeleteView, latest_version_view, CodeChangeLogListView, CodeChangeLogDetailView, FileHashListView, \
    version_index_view,update_versions_view
from django.shortcuts import render

urlpatterns = [
    path('', version_index_view , name='version_index_view'),
    path('version_list', AppVersionListView.as_view(), name='appversion_list'),
    path('<int:pk>/', AppVersionDetailView.as_view(), name='appversion_detail'),
    path('create/', AppVersionCreateView.as_view(), name='appversion_create'),
    path('<int:pk>/update/', AppVersionUpdateView.as_view(), name='appversion_update'),
    path('<int:pk>/delete/', AppVersionDeleteView.as_view(), name='appversion_delete'),
    path('versioning-guide/', lambda request: render(request, 'versions/versioning_guide.html'), name='versioning_guide'),
    path('latest/', latest_version_view, name='latest_version'),
    path('changes/', CodeChangeLogListView.as_view(), name='codechangelog_list'),
    path('changes/<int:pk>/', CodeChangeLogDetailView.as_view(), name='codechangelog_detail'),
    path('file-hashes/', FileHashListView.as_view(), name='filehash_list'),
    path('version_index',latest_version_view, name='latest_version'),
    path('update-versions/',   update_versions_view, name='update_versions'),

]
