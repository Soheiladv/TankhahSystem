"""
Enhanced Budget Allocation Report View
"""
import logging
from decimal import Decimal
from django.db.models import Sum, Q, Prefetch, Count
from django.db.models.functions import Coalesce
import jdatetime
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from budgets.models import BudgetAllocation, BudgetTransaction, BudgetItem
from core.PermissionBase_Optimized import PermissionBaseView
from core.models import Organization, Status
from tankhah.models import Tankhah, Factor

logger = logging.getLogger(__name__)

class BudgetAllocationReportEnhancedView(PermissionBaseView, DetailView):
    """Enhanced Budget Allocation Report View with advanced features"""
    
    model = BudgetAllocation
    template_name = 'reports/report_budget_allocation_enhanced.html'
    context_object_name = 'budget_allocation'
    pk_url_kwarg = 'pk'
    permission_codename = 'BudgetAllocation.BudgetAllocation_reports'

    def get_queryset(self):
        """Optimized queryset with prefetching"""
        return super().get_queryset().select_related(
            'organization',
            'budget_period',
            'budget_item',
            'created_by'
        ).prefetch_related(
            Prefetch(
                'transactions',
                queryset=BudgetTransaction.objects.select_related('related_tankhah', 'created_by').order_by('-timestamp')
            ),
            Prefetch(
                'tankhahs',
                queryset=Tankhah.objects.select_related('status', 'created_by').order_by('-date')
            )
        )

    def get_object(self, queryset=None):
        """Get object with validation"""
        obj = super().get_object(queryset)
        
        if not obj.is_active:
            logger.warning(f"Attempted to view report for inactive BudgetAllocation (PK: {obj.pk})")
            messages.warning(self.request, _('این تخصیص بودجه فعال نیست.'))
            raise Http404

        return obj

    def get_context_data(self, **kwargs):
        """Enhanced context data with advanced analytics"""
        context = super().get_context_data(**kwargs)
        budget_allocation = self.object
        
        logger.info(f"Preparing enhanced report for BudgetAllocation PK: {budget_allocation.pk}")

        # Basic information
        context.update({
            'report_title': _("گزارش پیشرفته تخصیص بودجه"),
            'organization': budget_allocation.organization,
            'budget_period': budget_allocation.budget_period,
            'budget_item': budget_allocation.budget_item,
            'allocated_amount_main': budget_allocation.allocated_amount,
            'allocation_date_main': budget_allocation.allocation_date,
            'allocation_date_jalali': jdatetime.date.fromgregorian(date=budget_allocation.allocation_date).strftime('%Y/%m/%d') if budget_allocation.allocation_date else '',
            'description_main': budget_allocation.description,
            'is_active_main': budget_allocation.is_active,
            'created_by_main': budget_allocation.created_by,
            'current_date_jalali': jdatetime.date.today().strftime('%Y/%m/%d'),
            'current_time_jalali': jdatetime.datetime.now().strftime('%H:%M'),
        })

        # Calculate financial metrics
        consumed_amount = self._calculate_consumed_amount(budget_allocation)
        remaining_amount = budget_allocation.allocated_amount - consumed_amount
        utilization_percentage = (consumed_amount / budget_allocation.allocated_amount * 100) if budget_allocation.allocated_amount > 0 else Decimal('0')

        context.update({
            'consumed_amount_main': consumed_amount,
            'remaining_amount_main': remaining_amount,
            'utilization_percentage_main': utilization_percentage,
        })

        # Related budget allocations
        context['related_budget_allocations_list'] = self._get_related_allocations(budget_allocation)

        # Linked tankhahs and transactions
        context['linked_tankhahs'] = budget_allocation.tankhahs.all()[:10]
        context['linked_transactions'] = budget_allocation.transactions.all()[:20]

        # Advanced analytics
        context.update(self._get_advanced_analytics(budget_allocation))

        logger.info(f"Enhanced report context prepared for BudgetAllocation PK: {budget_allocation.pk}")
        return context

    def _calculate_consumed_amount(self, budget_allocation):
        """Calculate total consumed amount"""
        try:
            consumed = BudgetTransaction.objects.filter(
                allocation=budget_allocation,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            returned = BudgetTransaction.objects.filter(
                allocation=budget_allocation,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            return consumed - returned
        except Exception as e:
            logger.error(f"Error calculating consumed amount: {e}")
            return Decimal('0')

    def _get_related_allocations(self, budget_allocation):
        """Get related budget allocations"""
        try:
            related_allocations = BudgetAllocation.objects.filter(
                organization=budget_allocation.organization,
                budget_period=budget_allocation.budget_period,
                is_active=True
            ).exclude(pk=budget_allocation.pk).select_related('budget_item')[:10]

            related_data = []
            for allocation in related_allocations:
                consumed = self._calculate_consumed_amount(allocation)
                remaining = allocation.allocated_amount - consumed
                utilization = (consumed / allocation.allocated_amount * 100) if allocation.allocated_amount > 0 else Decimal('0')

                related_data.append({
                    'instance': allocation,
                    'budget_item_name': allocation.budget_item.name,
                    'allocated_amount': allocation.allocated_amount,
                    'consumed_amount': consumed,
                    'remaining_amount': remaining,
                    'utilization_percentage': utilization,
                    'is_active': allocation.is_active,
                })

            return related_data
        except Exception as e:
            logger.error(f"Error getting related allocations: {e}")
            return []

    def _get_advanced_analytics(self, budget_allocation):
        """Get advanced analytics data"""
        try:
            # Monthly consumption trend
            monthly_data = self._get_monthly_consumption(budget_allocation)
            
            # Status distribution
            status_distribution = self._get_status_distribution(budget_allocation)
            
            # Top transactions
            top_transactions = self._get_top_transactions(budget_allocation)
            
            return {
                'monthly_consumption': monthly_data,
                'status_distribution': status_distribution,
                'top_transactions': top_transactions,
            }
        except Exception as e:
            logger.error(f"Error getting advanced analytics: {e}")
            return {}

    def _get_monthly_consumption(self, budget_allocation):
        """Get monthly consumption data"""
        try:
            from django.db.models.functions import ExtractMonth, ExtractYear
            
            monthly_data = BudgetTransaction.objects.filter(
                allocation=budget_allocation,
                transaction_type='CONSUMPTION'
            ).annotate(
                month=ExtractMonth('timestamp'),
                year=ExtractYear('timestamp')
            ).values('year', 'month').annotate(
                total=Sum('amount')
            ).order_by('year', 'month')
            
            return list(monthly_data)
        except Exception as e:
            logger.error(f"Error getting monthly consumption: {e}")
            return []

    def _get_status_distribution(self, budget_allocation):
        """Get status distribution for linked tankhahs"""
        try:
            status_data = budget_allocation.tankhahs.values('status__name').annotate(
                count=Count('id')
            ).order_by('-count')
            
            return list(status_data)
        except Exception as e:
            logger.error(f"Error getting status distribution: {e}")
            return []

    def _get_top_transactions(self, budget_allocation):
        """Get top transactions by amount"""
        try:
            top_transactions = budget_allocation.transactions.order_by('-amount')[:5]
            return [
                {
                    'amount': tx.amount,
                    'type': tx.get_transaction_type_display(),
                    'date': tx.timestamp,
                    'description': tx.description,
                }
                for tx in top_transactions
            ]
        except Exception as e:
            logger.error(f"Error getting top transactions: {e}")
            return []

    def render_to_response(self, context, **response_kwargs):
        """Handle different output formats"""
        output_format = self.request.GET.get('format', 'html').lower()
        
        if output_format == 'json':
            return self._render_json_response(context)
        elif output_format == 'excel':
            return self._render_excel_response(context)
        elif output_format == 'pdf':
            return self._render_pdf_response(context)
        
        return super().render_to_response(context, **response_kwargs)

    def _render_json_response(self, context):
        """Render JSON response for API calls"""
        data = {
            'budget_allocation': {
                'id': context['budget_allocation'].pk,
                'allocated_amount': float(context['allocated_amount_main']),
                'consumed_amount': float(context['consumed_amount_main']),
                'remaining_amount': float(context['remaining_amount_main']),
                'utilization_percentage': float(context['utilization_percentage_main']),
            },
            'linked_tankhahs': [
                {
                    'id': tankhah.pk,
                    'number': tankhah.number,
                    'amount': float(tankhah.amount),
                    'status': tankhah.status.name if tankhah.status else 'نامشخص',
                }
                for tankhah in context['linked_tankhahs']
            ],
            'linked_transactions': [
                {
                    'id': tx.pk,
                    'amount': float(tx.amount),
                    'type': tx.transaction_type,
                    'timestamp': tx.timestamp.isoformat(),
                }
                for tx in context['linked_transactions']
            ]
        }
        return JsonResponse(data)

    def _render_excel_response(self, context):
        """Render Excel response"""
        # TODO: Implement Excel export
        return HttpResponse("Excel export not implemented yet", content_type='text/plain')

    def _render_pdf_response(self, context):
        """Render PDF response"""
        # TODO: Implement PDF export
        return HttpResponse("PDF export not implemented yet", content_type='text/plain')
