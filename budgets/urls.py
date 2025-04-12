from django.urls import path
from . import views
from .view_ProjectBudgetAllocation import ProjectBudgetAllocationListView, ProjectBudgetAllocationDetailView, \
    ProjectBudgetAllocationEditView, ProjectBudgetAllocationDeleteView, ProjectBudgetAllocationCreateView
from .views import BudgetPeriodListView, BudgetPeriodDetailView, BudgetPeriodCreateView, BudgetPeriodUpdateView, \
    BudgetPeriodDeleteView, BudgetPeriodDeleteView, BudgetAllocationDetailView, BudgetAllocationCreateView, \
    BudgetAllocationListView, BudgetAllocationDetailView, BudgetAllocationCreateView, \
    BudgetAllocationUpdateView, BudgetAllocationDeleteView, BudgetTransactionListView, BudgetTransactionDetailView, \
    PaymentOrderListView, PaymentOrderDetailView, PaymentOrderCreateView, PaymentOrderUpdateView, \
    PaymentOrderDeleteView, PayeeListView, PayeeDetailView, PayeeCreateView, PayeeUpdateView, PayeeDeleteView, \
    TransactionTypeListView, TransactionTypeDetailView, TransactionTypeCreateView, TransactionTypeUpdateView, \
    TransactionTypeDeleteView, OrganizationBudgetAllocationListView

urlpatterns = [
    path('budgetperiods/', BudgetPeriodListView.as_view(), name='budgetperiod_list'),    # مسیر لیست دوره‌های بودجه (برای دکمه انصراف)
    path('budgetperiods/<int:pk>/', BudgetPeriodDetailView.as_view(), name='budgetperiod_detail'),
    path('budgetperiods/create/', BudgetPeriodCreateView.as_view(), name='budgetperiod_create'),
    path('budgetperiods/<int:pk>/update/', BudgetPeriodUpdateView.as_view(), name='budgetperiod_update'),
    path('budgetperiods/<int:pk>/delete/', BudgetPeriodDeleteView.as_view(), name='budgetperiod_delete'),
]#دوره بودجه کلان
urlpatterns += [
    path('budgetallocations/', BudgetAllocationListView.as_view(), name='budgetallocation_list'),
    path('budgetallocations/<int:pk>/', BudgetAllocationDetailView.as_view(), name='budgetallocation_detail'),
    path('budgetallocations/create/', BudgetAllocationCreateView.as_view(), name='budgetallocation_create'),
    path('budgetallocations/<int:pk>/update/', BudgetAllocationUpdateView.as_view(), name='budgetallocation_update'),
    path('budgetallocations/<int:pk>/delete/', BudgetAllocationDeleteView.as_view(), name='budgetallocation_delete'),

    path('organization/<int:org_id>/allocations/', OrganizationBudgetAllocationListView.as_view(), name='organization_budgetallocation_list'),

]#تخصیص بودجه به هر سطح از Organization
urlpatterns += [
    path('budgettransactions/', BudgetTransactionListView.as_view(), name='budgettransaction_list'),
    path('budgettransactions/<int:pk>/', BudgetTransactionDetailView.as_view(), name='budgettransaction_detail'),
]# هر تغییر در بودجه
urlpatterns += [
    path('paymentorders/', PaymentOrderListView.as_view(), name='paymentorder_list'),
    path('paymentorders/<int:pk>/', PaymentOrderDetailView.as_view(), name='paymentorder_detail'),
    path('paymentorders/create/', PaymentOrderCreateView.as_view(), name='paymentorder_create'),
    path('paymentorders/<int:pk>/update/', PaymentOrderUpdateView.as_view(), name='paymentorder_update'),
    path('paymentorders/<int:pk>/delete/', PaymentOrderDeleteView.as_view(), name='paymentorder_delete'),
]# دستور پرداخت
urlpatterns += [
    path('payees/', PayeeListView.as_view(), name='payee_list'),
    path('payees/<int:pk>/', PayeeDetailView.as_view(), name='payee_detail'),
    path('payees/create/', PayeeCreateView.as_view(), name='payee_create'),
    path('payees/<int:pk>/update/', PayeeUpdateView.as_view(), name='payee_update'),
    path('payees/<int:pk>/delete/', PayeeDeleteView.as_view(), name='payee_delete'),
]#  اطلاعات دریافت‌کننده
urlpatterns += [
    path('transactiontypes/', TransactionTypeListView.as_view(), name='transactiontype_list'),
    path('transactiontypes/<int:pk>/', TransactionTypeDetailView.as_view(), name='transactiontype_detail'),
    path('transactiontypes/create/', TransactionTypeCreateView.as_view(), name='transactiontype_create'),
    path('transactiontypes/<int:pk>/update/', TransactionTypeUpdateView.as_view(), name='transactiontype_update'),
    path('transactiontypes/<int:pk>/delete/', TransactionTypeDeleteView.as_view(), name='transactiontype_delete'),
] # تعریف پویا نوع تراکنش‌ها

from core.views import BudgetAllocationView
urlpatterns += [
    path('budget_allocation_view/', BudgetAllocationView.as_view(),name='budget_allocation_view'),
]

urlpatterns += [
    #صفحه، پروژه‌ها و زیرپروژه‌ها رو با بودجه تخصیص‌یافته، باقی‌مانده، و درصد نشون می‌ده.
    # مسیر تخصیص بودجه به پروژه‌ها و زیرپروژه‌ها

    path('organization/<int:organization_id>/project-budget-allocations/',
         ProjectBudgetAllocationListView.as_view(),
         name='project_budget_allocation_list'),

    path('project-budget-allocation/<int:pk>/detail/',
          ProjectBudgetAllocationDetailView.as_view(),
         name='project_budget_allocation_detail'),

    path('project-budget-allocation/<int:pk>/edit/',
          ProjectBudgetAllocationEditView.as_view(),
         name='project_budget_allocation_edit'),

    path('project-budget-allocation/<int:pk>/delete/',
          ProjectBudgetAllocationDeleteView.as_view(),
         name='project_budget_allocation_delete'),

    path('organization/<int:organization_id>/project-budget-allocation/',
          ProjectBudgetAllocationCreateView.as_view(),
         name='project_budget_allocation'),
]
