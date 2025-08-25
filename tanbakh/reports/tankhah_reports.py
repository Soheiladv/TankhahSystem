from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from accounts.has_role_permission import has_permission
from tanbakh.models import Tanbakh
from django.utils.translation import gettext_lazy as _


@method_decorator(has_permission('Tanbakh_view'), name='dispatch')
class TanbakhReportView(LoginRequiredMixin, TemplateView):
    template_name = 'tanbakh/Reports/tanbakh_report.html'
    extra_context = {'title': _('گزارش تنخواه')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # فیلتر تنخواه‌ها بر اساس دسترسی
        if user.has_perm('Tanbakh_full_view'):
            context['tanbakhs'] = Tanbakh.objects.all()
        else:
            context['tanbakhs'] = Tanbakh.objects.filter(approved_by=user)  # فقط تنخواه‌های تأییدشده توسط کاربر

        context['total_amount'] = context['tanbakhs'].aggregate(total=Sum('amount'))['total'] or 0
        return context