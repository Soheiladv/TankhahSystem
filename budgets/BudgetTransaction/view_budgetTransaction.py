# budgets/views.py
from decimal import Decimal

from django.db.models import Q, Sum
from django.views.generic import ListView, DetailView
import datetime
import  logging

from budgets.models import BudgetTransaction, BudgetAllocation
from core.PermissionBase import PermissionBaseView
from core.models import Project

logger = logging.getLogger(__name__)
# --- BudgetTransaction CRUD ---
class BudgetTransactionListView_2D(PermissionBaseView, ListView):
    model = BudgetTransaction
    template_name = 'budgets/BudgetTransaction/budget_transaction_list.html'
    context_object_name = 'transactions'
    permission_codename = 'budgets.BudgetTransaction_view'

    def get_queryset(self):
        allocation = BudgetAllocation.objects.get(pk=self.kwargs['allocation_id'])
        return BudgetTransaction.objects.filter(
            allocation=allocation.budget_allocation,
            allocation__project=allocation.project
        ).order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation = BudgetAllocation.objects.get(pk=self.kwargs['allocation_id'])
        context['allocation'] = allocation
        return context

class BudgetTransactionListView(PermissionBaseView, ListView):
    model = BudgetTransaction
    template_name = 'budgets/budget/budgettransaction_list.html'
    context_object_name = 'budget_transactions'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(allocation__budget_period__name__icontains=query) |
                Q(allocation__organization__name__icontains=query) |
                Q(description__icontains=query)
            )
        trans_type = self.request.GET.get('transaction_type')
        if trans_type:
            queryset = queryset.filter(transaction_type=trans_type)
        return queryset.order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['transaction_type'] = self.request.GET.get('transaction_type', '')
        context['transaction_types'] = BudgetTransaction.TRANSACTION_TYPES
        logger.debug(f"BudgetTransactionListView context: {context}")
        return context

class BudgetTransactionDetailView(PermissionBaseView, DetailView):
    model = BudgetTransaction
    template_name = 'budgets/budget/budgettransaction_detail.html'
    context_object_name = 'budget_transaction'