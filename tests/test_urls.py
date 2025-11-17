from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path('tab-test/', TemplateView.as_view(template_name='test/comprehensive_tab_test.html'), name='tab_test'),
]
