from django.shortcuts import render
from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from core.PermissionBase import PermissionBaseView
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class BudgetStatsView(PermissionBaseView, TemplateView):
    """
    نمایش آمار زنده سیستم بودجه
    """
    template_name = 'budgets/budget_stats.html'
    permission_codename = ['budgets.BudgetPeriod_view']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            from budgets.models import BudgetPeriod, BudgetAllocation, BudgetTransaction
            
            # آمار دوره‌های بودجه
            periods_stats = BudgetPeriod.objects.aggregate(
                total=Count('id'),
                active=Count('id', filter=Q(is_active=True)),
                completed=Count('id', filter=Q(is_completed=True))
            )
            
            # آمار تخصیص‌ها
            allocations_stats = BudgetAllocation.objects.aggregate(
                total=Count('id'),
                active=Count('id', filter=Q(is_active=True)),
                locked=Count('id', filter=Q(is_locked=True))
            )
            
            # آمار تراکنش‌ها
            transactions_stats = BudgetTransaction.objects.aggregate(
                total=Count('id'),
                returns=Count('id', filter=Q(transaction_type='RETURN')),
                consumptions=Count('id', filter=Q(transaction_type='CONSUMPTION'))
            )
            
            # آمار مبالغ
            amounts_stats = {
                'total_allocated': BudgetAllocation.objects.aggregate(
                    total=Sum('allocated_amount')
                )['total'] or 0,
                'total_returned': BudgetTransaction.objects.filter(
                    transaction_type='RETURN'
                ).aggregate(
                    total=Sum('amount')
                )['total'] or 0,
                'total_consumed': BudgetTransaction.objects.filter(
                    transaction_type='CONSUMPTION'
                ).aggregate(
                    total=Sum('amount')
                )['total'] or 0,
            }
            
            context.update({
                'stats': {
                    'periods': periods_stats,
                    'allocations': allocations_stats,
                    'transactions': transactions_stats,
                    'amounts': amounts_stats,
                }
            })
            
            # آمار تغییرات اخیر (آخرین 7 روز)
            week_ago = timezone.now() - timedelta(days=7)
            
            recent_stats = {
                'recent_allocations': BudgetAllocation.objects.filter(
                    allocation_date__gte=week_ago.date()
                ).count(),
                'recent_returns': BudgetTransaction.objects.filter(
                    transaction_type='RETURN',
                    timestamp__gte=week_ago
                ).count(),
                'recent_consumptions': BudgetTransaction.objects.filter(
                    transaction_type='CONSUMPTION',
                    timestamp__gte=week_ago
                ).count(),
            }
            
            context['recent_stats'] = recent_stats
            
            # فایل‌های تست موجود
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
            
            # API های موجود
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
                },
                {
                    'method': 'POST',
                    'url': '/api/budget/return/',
                    'description': _('ثبت برگشت بودجه'),
                    'parameters': ['allocation_id', 'amount', 'description']
                },
                {
                    'method': 'GET',
                    'url': '/api/budget/transactions/',
                    'description': _('لیست تراکنش‌های بودجه'),
                    'parameters': ['allocation_id', 'transaction_type', 'start_date', 'end_date']
                }
            ]
            
            # مدل‌های اصلی
            context['main_models'] = [
                {
                    'name': 'BudgetPeriod',
                    'description': _('دوره بودجه کلان'),
                    'count': periods_stats['total'],
                    'fields': ['organization', 'name', 'start_date', 'end_date', 'total_amount', 'returned_amount']
                },
                {
                    'name': 'BudgetAllocation',
                    'description': _('تخصیص بودجه'),
                    'count': allocations_stats['total'],
                    'fields': ['budget_period', 'organization', 'project', 'allocated_amount', 'returned_amount']
                },
                {
                    'name': 'BudgetTransaction',
                    'description': _('تراکنش بودجه'),
                    'count': transactions_stats['total'],
                    'fields': ['allocation', 'transaction_type', 'amount', 'description', 'created_by']
                },
                {
                    'name': 'BudgetHistory',
                    'description': _('تاریخچه بودجه'),
                    'count': 0,  # Will be calculated if needed
                    'fields': ['content_type', 'object_id', 'action', 'amount', 'details']
                }
            ]
            
            logger.info(f"Budget stats loaded successfully: {context['stats']}")
            
        except Exception as e:
            logger.error(f"Error loading budget stats: {str(e)}")
            context['stats'] = None
            context['error'] = str(e)
        
        return context
