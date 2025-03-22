from django.views.generic import ListView
from django.db.models import Sum

from tanbakh.models import Tanbakh


class FinancialReportView(ListView):
    model = Tanbakh
    template_name = 'tanbakh/Reports/financial_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_by_project'] = Tanbakh.objects.filter(status='APPROVED').values('project__name').annotate(total=Sum('amount'))
        context['total_by_organization'] = Tanbakh.objects.filter(status='APPROVED').values('organization__name').annotate(total=Sum('amount'))
        return context


from django.views.generic import ListView
from django.db.models import Count
from tanbakh.models import ApprovalLog

class PerformanceReportView(ListView):
    model = ApprovalLog
    template_name = 'tanbakh/Reports/performance_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['approvals_by_user'] = ApprovalLog.objects.values('user__username').annotate(count=Count('id')).order_by('-count')
        return context