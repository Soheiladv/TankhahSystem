
############################################Main
# core/views.py
from django.views.generic.base import TemplateView
from version_tracker.models import FinalVersion, AppVersion

import logging
logger = logging.getLogger(__name__)
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

# Calculation Functions Import
from budgets.budget_calculations import (
    get_project_total_budget,
    get_project_used_budget,
    get_project_remaining_budget
)

def pdate(request):
    return render(request, template_name='budgets/pdate.html')

def about(request):
    return render(request, template_name='about.html')

class GuideView(TemplateView):
    template_name = 'help/guide.html'

class TanbakhWorkflowView(TemplateView): #help
    template_name =  'help/run_tankhahSystem.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('جریان کار تنخواه‌گردانی')
        context['stages'] = WorkflowStage.objects.all().order_by('order')
        return context

def home_view(request, *args, **kwargs):
    final_version = FinalVersion.calculate_final_version()
    latest_version = AppVersion.objects.order_by('-release_date').first()
    return render(request, 'index.html', {'latest_version': latest_version, 'final_version': final_version})




def soft_Help(request):
    return render(request, template_name='help/soft_help.html')