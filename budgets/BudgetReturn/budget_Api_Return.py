from django.core.paginator import Paginator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Q
from django.core.cache import cache
from decimal import Decimal
from budgets.models import BudgetAllocation, BudgetTransaction, Tankhah, Factor
import logging
from decimal import Decimal
import logging
logger = logging.getLogger(__name__)

class ProjectAllocationFreeBudgetAPI(APIView):
    def get(self, request, pk):
        logger.debug(f"[API] Starting ProjectAllocationFreeBudgetAPI for pk={pk}")
        try:
            logger.debug(f"[API] Querying BudgetAllocation with pk={pk}")
            allocation = BudgetAllocation.objects.select_related(
                'budget_allocation', 'project'
            ).get(pk=pk, is_active=True, is_locked=False)
            logger.debug(f"[API] Allocation found: id={allocation.id}, project={allocation.project.name}")

            cache_key = f"free_budget_details_{pk}"
            logger.debug(f"[API] Checking cache for key={cache_key}")
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"[API] Cache hit for key={cache_key}, returning cached data")
                return Response(cached_data)

            logger.debug(f"[API] Cache miss, calculating budget details")
            logger.debug(f"[API] Querying transactions for allocation={allocation.budget_allocation.id}, project={allocation.project.id}")
            transactions = BudgetTransaction.objects.filter(
                allocation=allocation.budget_allocation,
                project=allocation.project
            ).aggregate(
                consumed=Sum('amount', filter=Q(transaction_type='CONSUMPTION')),
                returned=Sum('amount', filter=Q(transaction_type='RETURN')),
                adjusted_increase=Sum('amount', filter=Q(transaction_type='ADJUSTMENT_INCREASE')),
                adjusted_decrease=Sum('amount', filter=Q(transaction_type='ADJUSTMENT_DECREASE'))
            )
            logger.debug(f"[API] Transaction aggregates: {transactions}")

            consumed = (transactions['consumed'] or Decimal('0')) + (transactions['adjusted_decrease'] or Decimal('0'))
            returned = (transactions['returned'] or Decimal('0')) + (transactions['adjusted_increase'] or Decimal('0'))
            logger.debug(f"[API] Calculated consumed={consumed}, returned={returned}")

            logger.debug(f"[API] Querying tankhah consumed for allocation={allocation.id}")
            tankhah_data = Tankhah.objects.filter(
                project_budget_allocation=allocation,
                status__in=['APPROVED', 'PAID']
            ).aggregate(total=Sum('amount'))
            tankhah_consumed = tankhah_data['total'] or Decimal('0')
            logger.debug(f"[API] Tankhah consumed: {tankhah_consumed}")

            logger.debug(f"[API] Querying factor consumed for allocation={allocation.id}")
            factor_data = Factor.objects.filter(
                tankhah__project_budget_allocation=allocation,
                status='PAID'
            ).aggregate(total=Sum('amount'))
            factor_consumed = factor_data['total'] or Decimal('0')
            logger.debug(f"[API] Factor consumed: {factor_consumed}")

            logger.debug(f"[API] Calculating free budget")
            free_budget = allocation.allocated_amount - consumed + returned - tankhah_consumed - factor_consumed
            logger.debug(f"[API] Free budget calculated: {free_budget}")

            logger.debug(f"[API] Querying tankhahs for allocation={allocation.id}")
            tankhahs = Tankhah.objects.filter(
                project_budget_allocation=allocation,
                status__in=['APPROVED', 'PAID']
            ).values('number', 'status', 'amount', 'remaining_budget')
            tankhahs_list = list(tankhahs)
            logger.debug(f"[API] Tankhahs retrieved: {tankhahs_list}")

            response_data = {
                'free_budget': float(free_budget),
                'allocated_amount': float(allocation.allocated_amount),
                'consumed_amount': float(consumed),
                'returned_amount': float(returned),
                'tankhah_consumed': float(tankhah_consumed),
                'factor_consumed': float(factor_consumed),
                'tankhahs': tankhahs_list
            }
            logger.debug(f"[API] Response data prepared: {response_data}")

            logger.debug(f"[API] Caching response data with key={cache_key}")
            cache.set(cache_key, response_data, timeout=300)
            logger.info(f"[API] Successfully processed request for pk={pk}, returning response")
            return Response(response_data)

        except BudgetAllocation.DoesNotExist:
            logger.error(f"[API] Allocation not found for pk={pk}")
            return Response({'error': 'تخصیص یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"[API] Unexpected error for pk={pk}: {str(e)}")
            return Response({'error': 'خطای سرور.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProjectAllocationsAPI(APIView):
    def get(self, request):
        logger.debug(f"[API] Starting ProjectAllocationsAPI")
        search = request.GET.get('search', '')
        page = int(request.GET.get('page', 1))
        logger.debug(f"[API] Parameters: search={search}, page={page}")

        queryset = BudgetAllocation.objects.filter(
            is_active=True,
            is_locked=False
        )
        if search:
            logger.debug(f"[API] Applying search filter: {search}")
            queryset = queryset.filter(
                Q(project__name__icontains=search) |
                Q(budget_allocation__organization__name__icontains=search)
            )

        logger.debug(f"[API] Querying allocations")
        paginator = Paginator(queryset, 10)
        allocations = paginator.page(page)
        logger.debug(f"[API] Retrieved {len(allocations)} allocations for page {page}")

        results = [
            {
                'id': alloc.id,
                'project_name': alloc.project.name,
                'organization_name': alloc.budget_allocation.organization.name,
                'allocated_amount': float(alloc.allocated_amount)
            } for alloc in allocations
        ]
        logger.debug(f"[API] Response data: {results}")

        return Response({
            'results': results,
            'pagination': {
                'more': allocations.has_next()
            }
        })



from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from budgets.models import BudgetAllocation
from rest_framework import serializers
class ProjectAllocationSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name')
    organization_name = serializers.CharField(source='budget_allocation.organization.name')
    free_budget = serializers.SerializerMethodField()

    class Meta:
        model = BudgetAllocation
        fields = ['id', 'project_name', 'organization_name', 'allocated_amount', 'free_budget']

    def get_free_budget(self, obj):
        cache_key = f"free_budget_{obj.pk}"
        free_budget = cache.get(cache_key)
        if free_budget is None:
            transactions = BudgetTransaction.objects.filter(
                allocation=obj.budget_allocation,
                project=obj.project
            ).aggregate(
                consumed=Sum('amount', filter=Q(transaction_type='CONSUMPTION')),
                returned=Sum('amount', filter=Q(transaction_type='RETURN'))
            )
            consumed = transactions['consumed'] or Decimal('0')
            returned = transactions['returned'] or Decimal('0')
            tankhah_consumed = Tankhah.objects.filter(
                project_budget_allocation=obj,
                status__in=['APPROVED', 'PAID']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            free_budget = obj.allocated_amount - consumed + returned - tankhah_consumed
            cache.set(cache_key, free_budget, timeout=300)
        return float(free_budget)
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
class ProjectAllocationAPI(generics.ListAPIView):
    serializer_class = ProjectAllocationSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = BudgetAllocation.objects.filter(
            is_active=True,
            is_locked=False
        ).select_related('budget_allocation__organization', 'project')

        # فیلترهای اختیاری
        project_id = self.request.query_params.get('project_id')
        organization_id = self.request.query_params.get('organization_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if organization_id:
            queryset = queryset.filter(budget_allocation__organization_id=organization_id)

        return queryset