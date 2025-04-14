from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages



class BudgetReturnView(LoginRequiredMixin, CreateView):
    from budgets.models import BudgetTransaction
    from budgets.BudgetReturn.forms_BudgetReturm import BudgetReturnForm

    model = BudgetTransaction
    form_class = BudgetReturnForm
    template_name = 'budgets/budget/budget_return_form.html'
    success_url = reverse_lazy('budgetallocation_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _('بودجه با موفقیت برگشت داده شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('خطایی در برگشت بودجه رخ داد.'))
        return super().form_invalid(form)

""""گزارش‌گیری بودجه برگشتی:"""
from budgets.models import BudgetHistory

def get_returned_budgets(budget_period):
    from django.contrib.contenttypes.models import ContentType
    from budgets.models import  BudgetAllocation
    return BudgetHistory.objects.filter(
        content_type=ContentType.objects.get_for_model(BudgetAllocation),
        action='RETURN',
        content_object__budget_period=budget_period
    ).values('amount', 'details', 'created_at', 'created_by__username')