from django.urls import path
from . import views

app_name = 'guide'

urlpatterns = [
    path('', views.index, name='index'),
    path('doc/<str:doc_name>/', views.detail, name='detail'),
]
