#!/usr/bin/env python
"""
تحلیل API های استفاده نشده در سیستم گزارش‌گیری
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

def analyze_unused_apis():
    """تحلیل API های استفاده نشده"""
    
    print("🔍 تحلیل API های استفاده نشده در سیستم گزارش‌گیری")
    print("=" * 70)
    
    # API های موجود در ComprehensiveBudgetReportView.py
    all_apis = [
        "ComprehensiveBudgetReportView",
        "APIOrganizationsForPeriodView", 
        "BudgetItemsForOrgPeriodAPIView",
        "APIFactorsForTankhahView",
        "APITankhahsForAllocationView",
        "OrganizationAllocationsAPIView",
        "AComprehensiveBudgetReportView",
        "APIBudgetItemsForOrgPeriodView",
        "APITankhahsForPBAView",
        "AA__APIFactorsForTankhahView",
        "AA__BudgetItemsForOrgPeriodAPIView",
        "AzA__OrganizationAllocationsAPIView",
        "AbPITankhahsForAllocationView",
        "AA__APIOrganizationsForPeriodView"
    ]
    
    # API های فعال در urls.py
    active_apis = [
        "ComprehensiveBudgetReportView",
        "APIOrganizationsForPeriodView",
        "BudgetItemsForOrgPeriodAPIView", 
        "APIFactorsForTankhahView",
        "APITankhahsForAllocationView",
        "OrganizationAllocationsAPIView"
    ]
    
    # API های غیرفعال
    inactive_apis = [api for api in all_apis if api not in active_apis]
    
    print(f"📊 آمار کلی:")
    print(f"   کل API ها: {len(all_apis)}")
    print(f"   API های فعال: {len(active_apis)}")
    print(f"   API های غیرفعال: {len(inactive_apis)}")
    
    print(f"\n❌ API های استفاده نشده ({len(inactive_apis)} عدد):")
    for i, api in enumerate(inactive_apis, 1):
        print(f"   {i:2d}. {api}")
    
    print(f"\n✅ API های فعال ({len(active_apis)} عدد):")
    for i, api in enumerate(active_apis, 1):
        print(f"   {i:2d}. {api}")
    
    print(f"\n🔍 تحلیل استفاده:")
    print(f"   • ComprehensiveBudgetReportView: گزارش اصلی - استفاده شده")
    print(f"   • APIOrganizationsForPeriodView: API سازمان‌ها - استفاده شده")
    print(f"   • BudgetItemsForOrgPeriodAPIView: API سرفصل‌ها - استفاده شده")
    print(f"   • APIFactorsForTankhahView: API فاکتورها - استفاده شده")
    print(f"   • APITankhahsForAllocationView: API تنخواه‌ها - استفاده شده")
    print(f"   • OrganizationAllocationsAPIView: API تخصیص‌ها - استفاده شده")
    
    print(f"\n⚠️  API های تکراری و غیرضروری:")
    print(f"   • AComprehensiveBudgetReportView: نسخه دوم گزارش جامع")
    print(f"   • APIBudgetItemsForOrgPeriodView: نسخه دوم API سرفصل‌ها")
    print(f"   • APITankhahsForPBAView: نسخه دوم API تنخواه‌ها")
    print(f"   • AA__APIFactorsForTankhahView: نسخه دوم API فاکتورها")
    print(f"   • AA__BudgetItemsForOrgPeriodAPIView: نسخه سوم API سرفصل‌ها")
    print(f"   • AzA__OrganizationAllocationsAPIView: نسخه دوم API تخصیص‌ها")
    print(f"   • AbPITankhahsForAllocationView: نسخه سوم API تنخواه‌ها")
    print(f"   • AA__APIOrganizationsForPeriodView: نسخه دوم API سازمان‌ها")
    
    print(f"\n💡 پیشنهادات:")
    print(f"   1️⃣ حذف API های تکراری")
    print(f"   2️⃣ یکپارچه‌سازی API های مشابه")
    print(f"   3️⃣ مستندسازی API های فعال")
    print(f"   4️⃣ تست API های استفاده نشده")
    print(f"   5️⃣ بهینه‌سازی کد")
    
    print(f"\n🎯 نتیجه:")
    print(f"   از {len(all_apis)} API موجود، فقط {len(active_apis)} عدد استفاده می‌شود")
    print(f"   {len(inactive_apis)} API غیرضروری و تکراری هستند")
    print(f"   نیاز به پاکسازی و بهینه‌سازی کد وجود دارد")

if __name__ == "__main__":
    analyze_unused_apis()
