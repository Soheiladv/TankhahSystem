from django.shortcuts import render
from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from core.PermissionBase import PermissionBaseView
import logging

logger = logging.getLogger(__name__)

class BudgetGuideView(PermissionBaseView, TemplateView):
    """
    نمایش راهنمای جامع سیستم بودجه
    """
    template_name = 'budgets/budget_guide.html'
    permission_codename = ['budgets.BudgetPeriod_view']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # آمار کلی سیستم
        from budgets.models import BudgetPeriod, BudgetAllocation, BudgetTransaction
        
        try:
            # آمار دوره‌های بودجه
            total_periods = BudgetPeriod.objects.count()
            active_periods = BudgetPeriod.objects.filter(is_active=True).count()
            completed_periods = BudgetPeriod.objects.filter(is_completed=True).count()
            
            # آمار تخصیص‌ها
            total_allocations = BudgetAllocation.objects.count()
            active_allocations = BudgetAllocation.objects.filter(is_active=True).count()
            locked_allocations = BudgetAllocation.objects.filter(is_locked=True).count()
            
            # آمار تراکنش‌ها
            total_transactions = BudgetTransaction.objects.count()
            return_transactions = BudgetTransaction.objects.filter(transaction_type='RETURN').count()
            consumption_transactions = BudgetTransaction.objects.filter(transaction_type='CONSUMPTION').count()
            
            # محاسبه مجموع مبالغ
            from django.db.models import Sum
            total_allocated = BudgetAllocation.objects.aggregate(
                total=Sum('allocated_amount')
            )['total'] or 0
            
            total_returned = BudgetTransaction.objects.filter(
                transaction_type='RETURN'
            ).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            total_consumed = BudgetTransaction.objects.filter(
                transaction_type='CONSUMPTION'
            ).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            context.update({
                'stats': {
                    'periods': {
                        'total': total_periods,
                        'active': active_periods,
                        'completed': completed_periods,
                    },
                    'allocations': {
                        'total': total_allocations,
                        'active': active_allocations,
                        'locked': locked_allocations,
                    },
                    'transactions': {
                        'total': total_transactions,
                        'returns': return_transactions,
                        'consumptions': consumption_transactions,
                    },
                    'amounts': {
                        'total_allocated': total_allocated,
                        'total_returned': total_returned,
                        'total_consumed': total_consumed,
                    }
                }
            })
            
            logger.info(f"Budget guide loaded with stats: {context['stats']}")
            
        except Exception as e:
            logger.error(f"Error loading budget guide stats: {str(e)}")
            context['stats'] = None
        
        # اطلاعات فایل‌های تست موجود
        context['test_files'] = [
            {
                'name': 'test_budget_return_model_only.py',
                'description': _('تست ساده برگشت بودجه'),
                'status': 'success'
            },
            {
                'name': 'test_budget_return_comprehensive.py',
                'description': _('تست جامع برگشت بودجه'),
                'status': 'success'
            },
            {
                'name': 'analyze_budget_return_flow.py',
                'description': _('تحلیل جریان مبلغ برگشتی'),
                'status': 'success'
            },
            {
                'name': 'test_reallocate_returned_budget.py',
                'description': _('تست تخصیص مجدد مبلغ برگشتی'),
                'status': 'success'
            }
        ]
        
        # اطلاعات API های موجود
        context['api_endpoints'] = [
            {
                'method': 'GET',
                'url': '/api/budget/allocation/{id}/free-budget/',
                'description': _('دریافت مانده آزاد تخصیص بودجه'),
                'parameters': ['id: شناسه تخصیص بودجه']
            },
            {
                'method': 'GET',
                'url': '/api/budget/allocations/',
                'description': _('لیست تخصیص‌های بودجه'),
                'parameters': ['search: جستجو', 'page: شماره صفحه']
            }
        ]
        
        # اطلاعات مدل‌های اصلی
        context['main_models'] = [
            {
                'name': 'BudgetPeriod',
                'description': _('دوره بودجه کلان'),
                'fields': ['organization', 'name', 'start_date', 'end_date', 'total_amount', 'returned_amount']
            },
            {
                'name': 'BudgetAllocation',
                'description': _('تخصیص بودجه'),
                'fields': ['budget_period', 'organization', 'project', 'allocated_amount', 'returned_amount']
            },
            {
                'name': 'BudgetTransaction',
                'description': _('تراکنش بودجه'),
                'fields': ['allocation', 'transaction_type', 'amount', 'description', 'created_by']
            },
            {
                'name': 'BudgetHistory',
                'description': _('تاریخچه بودجه'),
                'fields': ['content_type', 'object_id', 'action', 'amount', 'details']
            }
        ]
        
        return context
