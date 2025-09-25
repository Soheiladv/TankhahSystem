from django.urls import path

from .views import BudgetTransferCreateView, BudgetTransferListView

app_name = 'budget_transfer'

urlpatterns = [
    path('', BudgetTransferListView.as_view(), name='transfer_list'),
    path('create/', BudgetTransferCreateView.as_view(), name='transfer_create'),
]
