# budgets/urls.py
from django.urls import path

from reports.ComprehensiveBudgetReportView import ComprehensiveBudgetReportView
# وارد کردن تمام ویوهای مورد نیاز از بخش‌های مختلف
from .views import BudgetDashboardView, NumberToWordsView, budget_Help, TransactionTypeListView, \
    TransactionTypeCreateView, TransactionTypeUpdateView, TransactionTypeDeleteView, \
    OrganizationBudgetAllocationListView
from .budget_calculations import get_budget_info
from .ApproveReject.view_ApproveReject import ApproveRejectView
from .BudgetPeriod.views_BudgetPeriod import *
from .BudgetAllocation.views_BudgetAllocation import *
from .BudgetAllocation.get_projects_by_organization import get_projects_by_organization
from .ProjectBudgetAllocation.views_ProjectBudgetAllocation import *
from .ProjectBudgetAllocation.view_Update_Project_Budget_Allocation import Project__Budget__Allocation__Edit__View
from .BudgetTransaction.view_budgetTransaction import *
from .Budget_Items.views_Budget_item import *
from .BudgetReturn.view_BudgetReturn import BudgetReturnView
from .BudgetReturn.views_BudgetTransferView import BudgetTransferView
from .BudgetReturn.budget_Api_Return import ProjectAllocationFreeBudgetAPI, ProjectAllocationAPI
from .Payee.view_Payee import *
from .PaymentOrder.view_PaymentOrder import *
from core.views import BudgetAllocationView

# app_name = 'budgets'

urlpatterns = [
    # ===================================================================
    # ==== داشبورد و ابزارهای اصلی ====
    # ===================================================================
    path('budgets-dashboard', BudgetDashboardView.as_view(), name='budgets_dashboard'),
    path('budget_Help/', budget_Help, name='budget_Help'),
    path('convert_number_to_words/', NumberToWordsView.as_view(), name='convert_number_to_words'),
    path('get-budget-info/', get_budget_info, name='get_budget_info'),
    path('api/projects-by-organization/', get_projects_by_organization, name='get_projects_by_organization'),

    # ===================================================================
    # ==== مدیریت تعاریف پایه ====
    # ===================================================================
    path('budgetperiod/', BudgetPeriodListView.as_view(), name='budgetperiod_list'),
    path('budgetperiod/add/', BudgetPeriodCreateView.as_view(), name='budgetperiod_create'),
    path('budgetperiod/<int:pk>/', BudgetPeriodDetailView.as_view(), name='budgetperiod_detail'),
    path('budgetperiod/<int:pk>/edit/', BudgetPeriodUpdateView.as_view(), name='budgetperiod_update'),
    path('budgetperiod/<int:pk>/delete/', BudgetPeriodDeleteView.as_view(), name='budgetperiod_delete'),

    path('budgetitems/', BudgetItemListView.as_view(), name='budgetitem_list'),
    path('budgetitems/create/', BudgetItemCreateView.as_view(), name='budgetitem_create'),
    path('budgetitems/<int:pk>/', BudgetItemDetailView.as_view(), name='budgetitem_detail'),
    path('budgetitems/<int:pk>/update/', BudgetItemUpdateView.as_view(), name='budgetitem_update'),
    path('budgetitems/<int:pk>/delete/', BudgetItemDeleteView.as_view(), name='budgetitem_delete'),

    path('payee/', PayeeListView.as_view(), name='payee_list'),
    path('payee/add/', PayeeCreateView.as_view(), name='payee_create'),
    path('payee/<int:pk>/', PayeeDetailView.as_view(), name='payee_detail'),
    path('payee/<int:pk>/edit/', PayeeUpdateView.as_view(), name='payee_update'),
    path('payee/<int:pk>/delete/', PayeeDeleteView.as_view(), name='payee_delete'),

    path('transactiontype/', TransactionTypeListView.as_view(), name='transactiontype_list'),
    path('transactiontype/add/', TransactionTypeCreateView.as_view(), name='transactiontype_add'),
    path('transactiontype/<int:pk>/edit/', TransactionTypeUpdateView.as_view(), name='transactiontype_edit'),
    path('transactiontype/<int:pk>/delete/', TransactionTypeDeleteView.as_view(), name='transactiontype_delete'),

    # ===================================================================
    # ==== عملیات اصلی بودجه ====
    # ===================================================================
    path('budgetallocation/', BudgetAllocationListView.as_view(), name='budgetallocation_list'),
    path('budgetallocations/create/', BudgetAllocationCreateView.as_view(), name='budgetallocation_create'),
    path('budgetallocation/<int:pk>/', BudgetAllocationDetailView.as_view(), name='budgetallocation_detail'),
    path('budgetallocation/<int:pk>/edit/', BudgetAllocationUpdateView.as_view(), name='budgetallocation_update'),
    path('budgetallocation/<int:pk>/delete/', BudgetAllocationDeleteView.as_view(), name='budgetallocation_delete'),
    path('organization/<int:org_id>/allocations/', OrganizationBudgetAllocationListView.as_view(),
         name='organization_budgetallocation_list'),

    path('organization/<int:organization_id>/project-budget-allocations/', ProjectBudgetAllocationListView.as_view(),
         name='project_budget_allocation_list'),
    path('organization/<int:organization_id>/project-budget-allocation/', ProjectBudgetAllocationCreateView.as_view(),
         name='project_budget_allocation'),
    path('project-budget-allocation/<int:pk>/', ProjectBudgetAllocationDetailView.as_view(),
         name='project_budget_allocation_detail'),
    path('budget/allocation/<int:pk>/edit/', Project__Budget__Allocation__Edit__View.as_view(),
         name='project__budget__allocation__edit__view'),

    path('budgettransaction/', BudgetTransactionListView.as_view(), name='budgettransaction_list'),
    path('budgettransaction/<int:pk>/', BudgetTransactionDetailView.as_view(), name='budgettransaction_detail'),
    path('budget/allocation/<int:allocation_id>/transactions/', BudgetTransactionListView_2D.as_view(),
         name='budget_transaction_list_2d'),

    path('budget-transfer/', BudgetTransferView.as_view(), name='budget_transfer'),
    path('budget/allocation/<int:allocation_id>/return/', BudgetReturnView.as_view(), name='budget_return'),
    path('api/project-allocation-free-budget/<int:pk>/', ProjectAllocationFreeBudgetAPI.as_view(),
         name='project_allocation_free_budget'),
    path('api/project-allocations/', ProjectAllocationAPI.as_view(), name='project_allocation_api_list'),

    # ===================================================================
    # ==== عملیات پرداخت ====
    # ===================================================================
    path('paymentorder/', PaymentOrderListView.as_view(), name='paymentorder_list'),
    path('paymentorder/add/', PaymentOrderCreateView.as_view(), name='paymentorder_add'),
    path('paymentorder/<int:pk>/edit/', PaymentOrderUpdateView.as_view(), name='paymentorder_edit'),
    path('paymentorder/<int:pk>/delete/', PaymentOrderDeleteView.as_view(), name='paymentorder_delete'),
    path('paymentorders/<int:pk>/', PaymentOrderDetailView.as_view(), name='paymentorder_detail'),
    path('payment-order/<int:pk>/perform-action/<int:action_pk>/', PerformActionView.as_view(), name='paymentorder_perform_action'),
    path('payment-orders/review/',  PaymentOrderReviewView.as_view(), name='payment_order_review'),

    # ===================================================================
    # ==== کارتابل و گزارشات ====
    # ===================================================================
    path('approve-reject/<str:entity_type>/<int:entity_id>/<str:action>/', ApproveRejectView.as_view(),
         name='approve_reject'),
    path('budgetrealtimeReportView/', ProjectBudgetRealtimeReportView.as_view(), name='budgetrealtimeReportView'),

    path('budget_allocation_view/', BudgetAllocationView.as_view(), name='budget_allocation_view'),
]
