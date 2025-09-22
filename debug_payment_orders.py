#!/usr/bin/env python
"""
اسکریپت تشخیصی برای بررسی چرا دستورات پرداخت خودکار ایجاد نمی‌شوند
"""
import os
import sys
import django

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from tankhah.models import Factor, ApprovalLog
from budgets.models import PaymentOrder
from core.models import Status, WorkflowStage
from django.contrib.contenttypes.models import ContentType

def debug_payment_order_creation():
    print("=" * 60)
    print("تشخیص مشکل ایجاد دستورات پرداخت خودکار")
    print("=" * 60)
    
    # 1. بررسی فاکتورهای تایید نهایی
    print("\n1. بررسی فاکتورهای تایید نهایی:")
    final_approved_factors = Factor.objects.filter(
        status__is_final_approve=True
    ).select_related('status', 'tankhah')
    
    print(f"تعداد فاکتورهای تایید نهایی: {final_approved_factors.count()}")
    
    for factor in final_approved_factors[:5]:  # نمایش 5 مورد اول
        print(f"  - فاکتور {factor.id}: {factor.number} - وضعیت: {factor.status.name}")
        print(f"    تنخواه: {factor.tankhah.number if factor.tankhah else 'ندارد'}")
        print(f"    مبلغ: {factor.amount:,} ریال")
    
    # 2. بررسی دستورات پرداخت موجود
    print("\n2. بررسی دستورات پرداخت موجود:")
    existing_payment_orders = PaymentOrder.objects.all()
    print(f"تعداد کل دستورات پرداخت: {existing_payment_orders.count()}")
    
    for po in existing_payment_orders[:5]:
        print(f"  - دستور {po.id}: {po.order_number} - وضعیت: {po.status.name if po.status else 'ندارد'}")
        print(f"    فاکتورهای مرتبط: {po.related_factors.count()}")
    
    # 3. بررسی وضعیت‌های سیستم
    print("\n3. بررسی وضعیت‌های سیستم:")
    
    # وضعیت‌های فاکتور
    factor_statuses = Status.objects.filter(is_final_approve=True)
    print(f"وضعیت‌های تایید نهایی فاکتور: {factor_statuses.count()}")
    for status in factor_statuses:
        print(f"  - {status.name} ({status.code})")
    
    # وضعیت‌های اولیه دستور پرداخت
    po_initial_statuses = Status.objects.filter(is_initial=True)
    print(f"وضعیت‌های اولیه دستور پرداخت: {po_initial_statuses.count()}")
    for status in po_initial_statuses:
        print(f"  - {status.name} ({status.code})")
    
    # 4. بررسی مراحل گردش کار (حذف شده - WorkflowStage وجود ندارد)
    print("\n4. بررسی مراحل گردش کار:")
    print("  - WorkflowStage در پروژه وجود ندارد")
    
    # 5. بررسی ApprovalLog ها
    print("\n5. بررسی لاگ‌های تایید:")
    factor_content_type = ContentType.objects.get_for_model(Factor)
    recent_approvals = ApprovalLog.objects.filter(
        content_type=factor_content_type,
        action__code='APPROVED'
    ).order_by('-timestamp')[:10]
    
    print(f"تعداد لاگ‌های تایید فاکتور: {recent_approvals.count()}")
    for log in recent_approvals:
        print(f"  - فاکتور {log.object_id} - مرحله: {log.stage.name if log.stage else 'ندارد'}")
        print(f"    action: {log.action}")
    
    # 6. بررسی فاکتورهای بدون دستور پرداخت
    print("\n6. بررسی فاکتورهای بدون دستور پرداخت:")
    factors_without_po = Factor.objects.filter(
        status__is_final_approve=True
    ).exclude(
        payment_orders__isnull=False
    )
    
    print(f"فاکتورهای تایید نهایی بدون دستور پرداخت: {factors_without_po.count()}")
    
    # 7. پیشنهادات
    print("\n7. پیشنهادات:")
    if factors_without_po.exists():
        print("  - فاکتورهای تایید نهایی بدون دستور پرداخت وجود دارند")
        print("  - احتمالاً مشکل در سیگنال‌ها یا تنظیمات مراحل است")
        
        print("  - مشکل در سیگنال‌ها یا تنظیمات وضعیت‌ها است")
        
        if not po_initial_statuses.exists():
            print("  - هیچ وضعیت اولیه‌ای برای دستور پرداخت تعریف نشده")
            print("  - باید در پنل ادمین وضعیت‌ها را تنظیم کنید")
    
    print("\n" + "=" * 60)
    print("پایان تشخیص")
    print("=" * 60)

if __name__ == "__main__":
    debug_payment_order_creation()
