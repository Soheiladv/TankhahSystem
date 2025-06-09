# budgets/urls.py
from django.urls import path

from budgets.BudgetPeriod.views_BudgetPeriod import BudgetPeriodListView, BudgetPeriodDetailView, \
    BudgetPeriodCreateView, BudgetPeriodUpdateView, \
    BudgetPeriodDeleteView
from budgets.views import BudgetDashboardView, \
    OrganizationBudgetAllocationListView, \
    TransactionTypeListView, TransactionTypeCreateView, TransactionTypeUpdateView, TransactionTypeDeleteView, \
    NumberToWordsView, budget_Help

from .ApproveReject.view_ApproveReject import ApproveRejectView
from .BudgetAllocation.get_projects_by_organization import get_projects_by_organization
from .BudgetAllocation.views_BudgetAllocation import BudgetAllocationCreateView, BudgetAllocationListView
from .BudgetAllocation.views_BudgetAllocation import BudgetAllocationDetailView, BudgetAllocationDeleteView, \
    BudgetAllocationUpdateView
from .BudgetReturn.budget_Api_Return import ProjectAllocationFreeBudgetAPI, ProjectAllocationAPI
from .BudgetReturn.view_BudgetReturn import BudgetReturnView
from .BudgetReturn.views_BudgetTransferView import BudgetTransferView
from .BudgetTransaction.view_budgetTransaction import BudgetTransactionListView_2D, BudgetTransactionDetailView, \
    BudgetTransactionListView
from .Payee.view_Payee import PayeeListView, PayeeCreateView, PayeeUpdateView, PayeeDeleteView, PayeeDetailView
from .PaymentOrder.PaymentOrder import PaymentOrderSignView
from .PaymentOrder.view_PaymentOrder import PaymentOrderListView, PaymentOrderCreateView, \
    PaymentOrderUpdateView, PaymentOrderDeleteView, PaymentOrderReviewView

from .ProjectBudgetAllocation.view_Update_Project_Budget_Allocation import Project__Budget__Allocation__Edit__View
from .ProjectBudgetAllocation.views_ProjectBudgetAllocation import ProjectBudgetRealtimeReportView, \
    ProjectBudgetAllocationListView, ProjectBudgetAllocationCreateView, ProjectBudgetAllocationDetailView
from .budget_calculations import get_budget_info

# from .PaymentOrder.view_PaymentOrder import  PaymentOrderListView, PaymentOrderCreateView, \
#             PaymentOrderUpdateView, PaymentOrderDeleteView
urlpatterns = [
    path('budgets-dashboard',BudgetDashboardView.as_view(), name='budgets_dashboard'),  # داشبورد

    # BudgetPeriod
    path('budgetperiod/',BudgetPeriodListView.as_view(), name='budgetperiod_list'),
    path('budgetperiod/<int:pk>/',BudgetPeriodDetailView.as_view(), name='budgetperiod_detail'),
    path('budgetperiod/add/',BudgetPeriodCreateView.as_view(), name='budgetperiod_create'),
    path('budgetperiod/<int:pk>/edit/',BudgetPeriodUpdateView.as_view(), name='budgetperiod_update'),
    path('budgetperiod/<int:pk>/delete/',BudgetPeriodDeleteView.as_view(), name='budgetperiod_delete'),

    # BudgetAllocation
    path('budgetallocation/',BudgetAllocationListView.as_view(), name='budgetallocation_list'),
    path('budgetallocation/<int:pk>/',BudgetAllocationDetailView.as_view(), name='budgetallocation_detail'),
    # path('budgetallocation/add/',BudgetAllocationCreateView.as_view(), name='budgetallocation_add'),
    path('budgetallocation/<int:pk>/edit/',BudgetAllocationUpdateView.as_view(), name='budgetallocation_update'),
    path('budgetallocation/<int:pk>/delete/',BudgetAllocationDeleteView.as_view(),
         name='budgetallocation_delete'),
    path('budgetallocations/create/',BudgetAllocationCreateView.as_view(), name='budgetallocation_create'),

    # Organization Budget
    path('organization/<int:org_id>/allocations/', OrganizationBudgetAllocationListView.as_view(), name='organization_budgetallocation_list'),

    # ProjectBudgetAllocation
    path('organization/<int:organization_id>/project-budget-allocations/',ProjectBudgetAllocationListView.as_view(), name='project_budget_allocation_list'),#فهرست بودجه های سازمان
    path('organization/<int:organization_id>/project-budget-allocation/',ProjectBudgetAllocationCreateView.as_view(), name='project_budget_allocation'),
    # path('project-budget-allocation/<int:pk>/detail/',ProjectBudgetAllocationDetailView.as_view(), name='project_budget_allocation_detail'),
    path('project-budget-allocation/<int:pk>/',ProjectBudgetAllocationDetailView.as_view(), name='project_budget_allocation_detail'),

    # path('project__budget__allocation__edit__view/<int:pk>/edit/',Project__Budget__Allocation__Edit__View.as_view(), name='project__budget__allocation__edit__view'),

    path('budget/allocation/<int:pk>/edit/', Project__Budget__Allocation__Edit__View.as_view(), name='project__budget__allocation__edit__view'),


    # path('project-budget-allocation/<int:pk>/delete/',ProjectBudgetAllocationDeleteView.as_view(), name='project_budget_allocation_delete'),

    # BudgetTransaction
    path('budgettransaction/',BudgetTransactionListView.as_view(), name='budgettransaction_list'),
    path('budget/allocation/<int:allocation_id>/transactions/', BudgetTransactionListView_2D.as_view(),
         name='budget_transaction_list_2d'),
    path('budgettransaction/<int:pk>/',BudgetTransactionDetailView.as_view(), name='budgettransaction_detail'),

   # TransactionType
    path('transactiontype/',TransactionTypeListView.as_view(), name='transactiontype_list'),
    path('transactiontype/add/',TransactionTypeCreateView.as_view(), name='transactiontype_add'),
    path('transactiontype/<int:pk>/edit/',TransactionTypeUpdateView.as_view(), name='transactiontype_edit'),
    path('transactiontype/<int:pk>/delete/',TransactionTypeDeleteView.as_view(), name='transactiontype_delete'),


    # path('budgetallocations/<int:pk>/update/', BudgetAllocationUpdateView.as_view(), name='budgetallocation_update'),

    # path('get_projects_by_organization/',get_projects_by_organization, name='get_projects_by_organization'),# گرفتن پروژه‌های سازمان
    path('api/projects-by-organization/',  get_projects_by_organization, name='get_projects_by_organization'),

    path('convert_number_to_words/', NumberToWordsView.as_view(), name='convert_number_to_words'),

   #Api get_budget_info
    path('get-budget-info/', get_budget_info, name='get_budget_info'),

]
urlpatterns +=[
    # PaymentOrder
    path('paymentorder/', PaymentOrderListView.as_view(), name='paymentorder_list'),
    path('paymentorder/add/', PaymentOrderCreateView.as_view(), name='paymentorder_add'),
    path('paymentorder/<int:pk>/edit/', PaymentOrderUpdateView.as_view(), name='paymentorder_edit'),
    path('paymentorder/<int:pk>/delete/', PaymentOrderDeleteView.as_view(), name='paymentorder_delete'),

    path('payment-order/<int:pk>/sign/', PaymentOrderSignView.as_view(), name='payment_order_sign'),

    path('payment-orders/review/',   PaymentOrderReviewView.as_view(), name='payment_order_review'),
] # دستورپرداخت

urlpatterns +=[
    # Payee
    path('payee/', PayeeListView.as_view(), name='payee_list'),
    path('payee/add/', PayeeCreateView.as_view(), name='payee_create'),
    path('payee/<int:pk>/edit/', PayeeUpdateView.as_view(), name='payee_update'),
    path('payee/<int:pk>/delete/', PayeeDeleteView.as_view(), name='payee_delete'),
    path('payee/<int:pk>/', PayeeDetailView.as_view(), name='payee_detail'),

]# Payee

urlpatterns += [
    path('budget_Help/',budget_Help,name='budget_Help')
]
from .Budget_Items.views_Budget_item import BudgetItemListView, BudgetItemCreateView, BudgetItemUpdateView, \
    BudgetItemDeleteView, BudgetItemDetailView #, load_budget_periods, LoadBudgetPeriodsView

urlpatterns += [
    path('budgetitems/',  BudgetItemListView.as_view(), name='budgetitem_list'),
    path('budgetitems/create/',  BudgetItemCreateView.as_view(), name='budgetitem_create'),
    path('budgetitems/<int:pk>/update/',  BudgetItemUpdateView.as_view(), name='budgetitem_update'),
    path('budgetitems/<int:pk>/delete/',  BudgetItemDeleteView.as_view(), name='budgetitem_delete'),
    path('budgetitems/<int:pk>/',  BudgetItemDetailView.as_view(), name='budgetitem_detail'),
]
from core.views import BudgetAllocationView
urlpatterns += [
    path('budget_allocation_view/', BudgetAllocationView.as_view(),name='budget_allocation_view'),
]

urlpatterns += [
    path('budgetrealtimeReportView/', ProjectBudgetRealtimeReportView.as_view(),name='budgetrealtimeReportView'),
] # Reports

urlpatterns += [
    path('approve-reject/<str:entity_type>/<int:entity_id>/<str:action>/', ApproveRejectView.as_view(),
         name='approve_reject'),
] # رد بودجه

urlpatterns += [
    path('budget/allocation/<int:allocation_id>/return/', BudgetReturnView.as_view(), name='budget_return'),

    path('budget-transfer/', BudgetTransferView.as_view(), name='budget_transfer'),
    path('budget-return/<int:allocation_id>/', BudgetReturnView.as_view(), name='budget_return'),

    # API
    # path(
        # 'api/project-allocation-free-budget/<int:allocation_id>/', ProjectAllocationFreeBudgetAPI.as_view(),
        # name='project_allocation_free_budget'),
    path('api/project-allocation-free-budget/<int:pk>/', ProjectAllocationFreeBudgetAPI.as_view(),
         name='project_allocation_free_budget'),

     path('api/project-allocations/', ProjectAllocationAPI.as_view(), name='project_allocation_api_list'),

    # یا نام ویو API شما
    # path('ajax/load-budget-periods/', load_budget_periods, name='ajax_load_budget_periods'),
    # path('ajax/load-budget-periods/', LoadBudgetPeriodsView.as_view(), name='ajax_load_budget_periods'),

]  # برگشت بودجه

# #/
# urlpatterns+  = [
#     path('budgetperiods/', BudgetPeriodListView.as_view(), name='budgetperiod_list'),    # مسیر لیست دوره‌های بودجه (برای دکمه انصراف)
#     path('budgetperiods/<int:pk>/', BudgetPeriodDetailView.as_view(), name='budgetperiod_detail'),
#     path('budgetperiods/create/', BudgetPeriodCreateView.as_view(), name='budgetperiod_create'),
#     path('budgetperiods/<int:pk>/update/', BudgetPeriodUpdateView.as_view(), name='budgetperiod_update'),
#     path('budgetperiods/<int:pk>/delete/', BudgetPeriodDeleteView.as_view(), name='budgetperiod_delete'),
# ]#دوره بودجه کلان
# urlpatterns += [
#     path('budgetallocations/', BudgetAllocationListView.as_view(), name='budgetallocation_list'),
#     path('budgetallocations/<int:pk>/', BudgetAllocationDetailView.as_view(), name='budgetallocation_detail'),
#     path('budgetallocations/create/', BudgetAllocationCreateView.as_view(), name='budgetallocation_create'),
#     path('budgetallocations/<int:pk>/update/', BudgetAllocationUpdateView.as_view(), name='budgetallocation_update'),
#     path('budgetallocations/<int:pk>/delete/', BudgetAllocationDeleteView.as_view(), name='budgetallocation_delete'),
#
#     path('organization/<int:org_id>/allocations/', OrganizationBudgetAllocationListView.as_view(), name='organization_budgetallocation_list'),
#
# ]#تخصیص بودجه به هر سطح از Organization
# urlpatterns += [
#     path('budgettransactions/', BudgetTransactionListView.as_view(), name='budgettransaction_list'),
#     path('budgettransactions/<int:pk>/', BudgetTransactionDetailView.as_view(), name='budgettransaction_detail'),
# ]# هر تغییر در بودجه
# urlpatterns += [
#     path('paymentorders/', PaymentOrderListView.as_view(), name='paymentorder_list'),
#     path('paymentorders/<int:pk>/', PaymentOrderDetailView.as_view(), name='paymentorder_detail'),
#     path('paymentorders/create/', PaymentOrderCreateView.as_view(), name='paymentorder_create'),
#     path('paymentorders/<int:pk>/update/', PaymentOrderUpdateView.as_view(), name='paymentorder_update'),
#     path('paymentorders/<int:pk>/delete/', PaymentOrderDeleteView.as_view(), name='paymentorder_delete'),
# ]# دستور پرداخت
# urlpatterns += [
#     path('payees/', PayeeListView.as_view(), name='payee_list'),
#     path('payees/<int:pk>/', PayeeDetailView.as_view(), name='payee_detail'),
#     path('payees/create/', PayeeCreateView.as_view(), name='payee_create'),
#     path('payees/<int:pk>/update/', PayeeUpdateView.as_view(), name='payee_update'),
#     path('payees/<int:pk>/delete/', PayeeDeleteView.as_view(), name='payee_delete'),
# ]#  اطلاعات دریافت‌کننده
# urlpatterns += [
#     path('transactiontypes/', TransactionTypeListView.as_view(), name='transactiontype_list'),
#     path('transactiontypes/<int:pk>/', TransactionTypeDetailView.as_view(), name='transactiontype_detail'),
#     path('transactiontypes/create/', TransactionTypeCreateView.as_view(), name='transactiontype_create'),
#     path('transactiontypes/<int:pk>/update/', TransactionTypeUpdateView.as_view(), name='transactiontype_update'),
#     path('transactiontypes/<int:pk>/delete/', TransactionTypeDeleteView.as_view(), name='transactiontype_delete'),
# ] # تعریف پویا نوع تراکنش‌ها


#
# urlpatterns += [
#     #صفحه، پروژه‌ها و زیرپروژه‌ها رو با بودجه تخصیص‌یافته، باقی‌مانده، و درصد نشون می‌ده.
#     # مسیر تخصیص بودجه به پروژه‌ها و زیرپروژه‌ها
#
#     path('organization/<int:organization_id>/project-budget-allocations/',
#          ProjectBudgetAllocationListView.as_view(),
#          name='project_budget_allocation_list'),
#
#     path('project-budget-allocation/<int:pk>/detail/',
#           ProjectBudgetAllocationDetailView.as_view(),
#          name='project_budget_allocation_detail'),
#
#     path('project-budget-allocation/<int:pk>/edit/',
#           ProjectBudgetAllocationEditView.as_view(),
#          name='project_budget_allocation_edit'),
#
#     path('project-budget-allocation/<int:pk>/delete/',
#           ProjectBudgetAllocationDeleteView.as_view(),
#          name='project_budget_allocation_delete'),
#
#     path('organization/<int:organization_id>/project-budget-allocation/',
#           ProjectBudgetAllocationCreateView.as_view(),
#          name='project_budget_allocation'),
# ]
