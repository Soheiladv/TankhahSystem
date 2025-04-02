from django.shortcuts import render
from django.views.generic import DetailView

from core.PermissionBase import PermissionBaseView
from reports.models import FinancialReport
from tankhah.models import Tankhah


# Create your views here.
class TankhahFinancialReportView(PermissionBaseView, DetailView):
    model = Tankhah
    template_name = 'reports/financial_report.html'
    permission_codenames = ['tankhah.Tankhah_view']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object
        report, created = FinancialReport.objects.get_or_create(tankhah=tankhah)
        if created or not report.payment_number:
            report.generate_report()
        context['report'] = report
        context['title'] = f"گزارش مالی تنخواه {tankhah.number}"
        return context