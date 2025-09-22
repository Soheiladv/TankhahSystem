#!/usr/bin/env python
"""
اسکریپت برای ایجاد دستی دستورات پرداخت برای فاکتورهای تایید نهایی
"""
import os
import sys
import django

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from tankhah.models import Factor
from budgets.models import PaymentOrder, Payee
from core.models import Status
from django.utils import timezone

def create_payment_orders_for_approved_factors():
    print("=" * 60)
    print("ایجاد دستی دستورات پرداخت برای فاکتورهای تایید نهایی")
    print("=" * 60)
    
    # 1. پیدا کردن فاکتورهای تایید نهایی بدون دستور پرداخت
    approved_factors = Factor.objects.filter(
        status__is_final_approve=True
    ).exclude(
        payment_orders__isnull=False
    ).select_related('tankhah', 'status', 'created_by')
    
    print(f"تعداد فاکتورهای تایید نهایی بدون دستور پرداخت: {approved_factors.count()}")
    
    if not approved_factors.exists():
        print("همه فاکتورهای تایید نهایی قبلاً دستور پرداخت دارند.")
        return
    
    # 2. پیدا کردن یا ایجاد وضعیت اولیه دستور پرداخت
    initial_po_status = Status.objects.filter(
        code='PO_DRAFT'
    ).first()
    
    if not initial_po_status:
        print("📝 ایجاد وضعیت اولیه برای دستور پرداخت...")
        # استفاده از اولین فاکتور برای created_by
        first_factor = approved_factors.first()
        initial_po_status = Status.objects.create(
            name='پیش‌نویس دستور پرداخت',
            code='PO_DRAFT',
            is_initial=True,
            is_final_approve=False,
            is_final_reject=False,
            is_active=True,
            created_by=first_factor.created_by,
            description='وضعیت اولیه برای دستورات پرداخت'
        )
        print(f"✅ وضعیت {initial_po_status.name} ایجاد شد.")
    else:
        print(f"✅ وضعیت اولیه دستور پرداخت: {initial_po_status.name}")
    
    # 3. پیدا کردن یا ایجاد Payee پیش‌فرض
    default_payee = Payee.objects.filter(is_active=True).first()
    if not default_payee:
        print("📝 ایجاد Payee پیش‌فرض...")
        first_factor = approved_factors.first()
        default_payee = Payee.objects.create(
            entity_type='INDIVIDUAL',
            name='سیستم',
            family='پیش‌فرض',
            payee_type='OTHER',
            is_active=True,
            created_by=first_factor.created_by
        )
        print(f"✅ Payee پیش‌فرض {default_payee} ایجاد شد.")
    else:
        print(f"✅ Payee پیش‌فرض: {default_payee}")
    
    # 4. ایجاد دستورات پرداخت
    created_count = 0
    for factor in approved_factors:
        try:
            print(f"\n📋 پردازش فاکتور {factor.number} (مبلغ: {factor.amount:,} ریال)")
            
            # بررسی اینکه قبلاً دستور پرداخت ایجاد نشده باشد
            if PaymentOrder.objects.filter(related_factors=factor).exists():
                print(f"  ⚠️  فاکتور {factor.number} قبلاً دستور پرداخت دارد.")
                continue
            
            # ایجاد دستور پرداخت
            payment_order = PaymentOrder.objects.create(
                tankhah=factor.tankhah,
                related_tankhah=factor.tankhah,
                amount=factor.amount,
                payee=default_payee,
                description=f"دستور پرداخت برای فاکتور {factor.number} (تنخواه: {factor.tankhah.number})",
                organization=factor.tankhah.organization,
                project=factor.tankhah.project,
                status=initial_po_status,
                created_by=factor.created_by,
                created_by_post=None,  # این فیلد اختیاری است
                issue_date=timezone.now().date(),
                min_signatures=1
            )
            
            # اضافه کردن فاکتور به دستور پرداخت
            payment_order.related_factors.add(factor)
            
            print(f"  ✅ دستور پرداخت {payment_order.order_number} ایجاد شد.")
            created_count += 1
            
        except Exception as e:
            print(f"  ❌ خطا در ایجاد دستور پرداخت برای فاکتور {factor.number}: {str(e)}")
    
    print(f"\n🎉 {created_count} دستور پرداخت با موفقیت ایجاد شد.")
    print("=" * 60)

if __name__ == "__main__":
    create_payment_orders_for_approved_factors()
