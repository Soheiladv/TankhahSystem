import json
import logging
from datetime import timedelta

import jdatetime
from django.core import cache
from django.db.models.functions import Coalesce
from django.db.models.functions.datetime import TruncQuarter
from django.utils import timezone

from django.db.models import Sum, Q
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
############################################Main
# core/views.py
from django.views.generic.base import TemplateView

from budgets.budget_calculations import get_project_total_budget, get_project_used_budget
from budgets.models import BudgetAllocation, BudgetTransaction, BudgetPeriod, CostCenter, BudgetHistory
from core.PermissionBase import PermissionBaseView
from core.models import WorkflowStage, Project, Organization
from tankhah.models import Tankhah, ApprovalLog, Factor, FactorItem
from version_tracker.models import FinalVersion, AppVersion


import json
import logging
logger = logging.getLogger(__name__)
import calendar
from datetime import timedelta
from decimal import Decimal
import jdatetime
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import Coalesce, TruncMonth, TruncQuarter
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View

# Model Imports - مطمئن شوید مسیرها درست هستند
from budgets.models import (
    BudgetAllocation, BudgetPeriod, BudgetTransaction, BudgetHistory
)
from tankhah.models import Tankhah, Factor, FactorItem, ApprovalLog, ItemCategory
from core.models import Project, Organization  # اضافه کردن Organization
from notifications.models import Notification

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