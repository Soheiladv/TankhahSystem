#!/usr/bin/env python
"""
اسکریپت دیباگ برای بررسی مشکل بارگذاری سرفصل‌های بودجه
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from reports.ComprehensiveBudgetReportView_fixed import BudgetItemsForOrgPeriodAPIView
from budgets.models import BudgetPeriod, BudgetAllocation
from core.models import Organization

def debug_budget_items():
    """دیباگ API سرفصل‌های بودجه"""
    
    print("🔍 دیباگ بارگذاری سرفصل‌های بودجه...")
    print("=" * 60)
    
    try:
        # ایجاد درخواست تست
        factory = RequestFactory()
        request = factory.get('/reports/api/budget-items-for-org-period/25/1/')
        
        # پیدا کردن کاربر
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            print("❌ کاربر سوپروایزر پیدا نشد!")
            return
        
        request.user = user
        
        # تست API
        print("1️⃣ تست API BudgetItemsForOrgPeriodAPIView...")
        api_view = BudgetItemsForOrgPeriodAPIView()
        
        # تست با دوره و سازمان موجود
        period_pk = 25  # دوره موجود
        org_pk = 1      # سازمان موجود
        
        print(f"   دوره PK: {period_pk}")
        print(f"   سازمان PK: {org_pk}")
        
        # بررسی وجود دوره و سازمان
        try:
            period = BudgetPeriod.objects.get(pk=period_pk)
            print(f"   ✅ دوره پیدا شد: {period.name}")
        except BudgetPeriod.DoesNotExist:
            print(f"   ❌ دوره با PK {period_pk} پیدا نشد!")
            return
        
        try:
            org = Organization.objects.get(pk=org_pk)
            print(f"   ✅ سازمان پیدا شد: {org.name}")
        except Organization.DoesNotExist:
            print(f"   ❌ سازمان با PK {org_pk} پیدا نشد!")
            return
        
        # بررسی تخصیص‌های بودجه
        print("\n2️⃣ بررسی تخصیص‌های بودجه...")
        allocations = BudgetAllocation.objects.filter(
            budget_period=period,
            organization=org,
            is_active=True
        )
        
        print(f"   تعداد تخصیص‌های فعال: {allocations.count()}")
        
        if allocations.exists():
            for alloc in allocations[:3]:
                print(f"   - تخصیص ID: {alloc.pk}")
                print(f"     سرفصل: {alloc.budget_item.name if alloc.budget_item else 'نامشخص'}")
                print(f"     مبلغ: {alloc.allocated_amount:,.0f}")
                print(f"     سازمان: {alloc.organization.name}")
        else:
            print("   ⚠️ هیچ تخصیص بودجه‌ای یافت نشد!")
            
            # بررسی تخصیص‌های غیرفعال
            inactive_allocations = BudgetAllocation.objects.filter(
                budget_period=period,
                organization=org,
                is_active=False
            )
            print(f"   تعداد تخصیص‌های غیرفعال: {inactive_allocations.count()}")
            
            # بررسی تمام تخصیص‌های دوره
            all_allocations = BudgetAllocation.objects.filter(budget_period=period)
            print(f"   تعداد کل تخصیص‌های دوره: {all_allocations.count()}")
            
            if all_allocations.exists():
                print("   تخصیص‌های موجود در دوره:")
                for alloc in all_allocations[:5]:
                    print(f"     - ID: {alloc.pk}, سازمان: {alloc.organization.name}, فعال: {alloc.is_active}")
        
        # تست API
        print("\n3️⃣ تست API...")
        response = api_view.get(request, period_pk, org_pk)
        
        print(f"   وضعیت HTTP: {response.status_code}")
        
        if response.status_code == 200:
            import json
            data = json.loads(response.content.decode('utf-8'))
            print(f"   وضعیت API: {data.get('status', 'unknown')}")
            print(f"   طول HTML: {len(data.get('html_content', ''))}")
            
            if data.get('status') == 'empty':
                print("   ⚠️ API گزارش خالی بودن داده‌ها را داده")
            elif data.get('status') == 'success':
                print("   ✅ API موفقیت‌آمیز بود")
            else:
                print(f"   ❓ وضعیت نامشخص: {data.get('status')}")
        else:
            print(f"   ❌ خطای HTTP: {response.status_code}")
            print(f"   محتوا: {response.content.decode('utf-8')[:200]}...")
        
        # بررسی سایر سازمان‌ها
        print("\n4️⃣ بررسی سایر سازمان‌ها...")
        other_orgs = Organization.objects.filter(is_active=True)[:3]
        for other_org in other_orgs:
            other_allocations = BudgetAllocation.objects.filter(
                budget_period=period,
                organization=other_org,
                is_active=True
            )
            print(f"   سازمان {other_org.name}: {other_allocations.count()} تخصیص")
        
        print("\n✅ دیباگ کامل شد!")
        
    except Exception as e:
        print(f"❌ خطا در دیباگ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_budget_items()
