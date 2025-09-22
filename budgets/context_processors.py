"""
Context processors برای budgets
"""
from django.db.models import Q
from budgets.models import PaymentOrder
from core.models import Status

def payment_order_stats(request):
    """
    آمار دستورات پرداخت برای نمایش در نوار کناری
    """
    if not request.user.is_authenticated:
        return {}
    
    try:
        # آمار دستورات در انتظار تایید
        pending_status = Status.objects.filter(code='PO_PENDING').first()
        pending_orders_count = PaymentOrder.objects.filter(
            status=pending_status
        ).count() if pending_status else 0
        
        # آمار دستورات تایید شده
        approved_status = Status.objects.filter(code='PO_APPROVED').first()
        approved_orders_count = PaymentOrder.objects.filter(
            status=approved_status
        ).count() if approved_status else 0
        
        return {
            'pending_orders_count': pending_orders_count,
            'approved_orders_count': approved_orders_count,
        }
    except Exception:
        return {
            'pending_orders_count': 0,
            'approved_orders_count': 0,
        }
