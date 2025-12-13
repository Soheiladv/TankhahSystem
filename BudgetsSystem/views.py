
############################################Main
# core/views.py
import logging

from django.db import connection
from django.http import JsonResponse
from django.views.generic.base import TemplateView

from core.models import Status
from version_tracker.models import AppVersion, FinalVersion

logger = logging.getLogger(__name__)
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _


def about(request):
    return render(request, template_name='about.html')

class GuideView(TemplateView):
    template_name = 'help/guide.html'

class TanbakhWorkflowView(TemplateView): #help
    template_name =  'help/run_tankhahSystem.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('جریان کار تنخواه‌گردانی')
        context['stages'] = Status.objects.filter(is_active=True).order_by('id')
        return context

def home_view(request, *args, **kwargs):
    final_version = FinalVersion.calculate_final_version()
    latest_version = AppVersion.objects.order_by('-release_date').first()
    return render(request, 'index.html', {'latest_version': latest_version, 'final_version': final_version})

def soft_Help(request):
    return render(request, template_name='help/soft_help.html')

def health_check(request):
    """Health check endpoint for Docker"""
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return JsonResponse({
            'status': 'healthy',
            'database': 'connected'
        }, status=200)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)


