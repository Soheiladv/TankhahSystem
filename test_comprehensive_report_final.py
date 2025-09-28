#!/usr/bin/env python
"""
تست نهایی گزارش جامع بودجه
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from reports.ComprehensiveBudgetReportView_fixed import ComprehensiveBudgetReportView, BudgetItemsForOrgPeriodAPIView
from budgets.models import BudgetPeriod, BudgetAllocation
from core.models import Organization

def test_comprehensive_report():
    """تست کامل گزارش جامع بودجه"""
    
    print("🧪 تست نهایی گزارش جامع بودجه...")
    print("=" * 60)
    
    try:
        # ایجاد درخواست تست
        factory = RequestFactory()
        request = factory.get('/reports/reports/comprehensive-budget/')
        
        # پیدا کردن کاربر
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            print("❌ کاربر سوپروایزر پیدا نشد!")
            return
        
        request.user = user
        
        # 1. تست view اصلی
        print("1️⃣ تست ComprehensiveBudgetReportView...")
        view = ComprehensiveBudgetReportView()
        view.request = request
        
        # تست get_queryset
        queryset = view.get_queryset()
        print(f"   تعداد دوره‌های بودجه: {queryset.count()}")
        
        if queryset.exists():
            period = queryset.first()
            print(f"   دوره نمونه: {period.name}")
            print(f"   سازمان: {period.organization.name}")
            
            # 2. تست get_context_data
            print("\n2️⃣ تست get_context_data...")
            context = view.get_context_data()
            processed_data = context.get('budget_periods_data', [])
            print(f"   تعداد دوره‌های پردازش شده: {len(processed_data)}")
            
            if processed_data:
                period_data = processed_data[0]
                print(f"   دوره: {period_data['period'].name}")
                print(f"   بودجه کل: {period_data['summary']['total_budget']:,.0f}")
                print(f"   تخصیص: {period_data['summary']['total_allocated']:,.0f}")
                print(f"   مصرف: {period_data['summary']['net_consumed']:,.0f}")
                print(f"   مانده: {period_data['summary']['remaining']:,.0f}")
                print(f"   درصد مصرف: {period_data['summary']['utilization_percentage']:.1f}%")
                print(f"   تعداد سازمان‌ها: {len(period_data['organization_summaries'])}")
                
                # 3. تست API سرفصل‌ها
                if period_data['organization_summaries']:
                    org = period_data['organization_summaries'][0]
                    print(f"\n3️⃣ تست API سرفصل‌ها برای سازمان: {org['name']}")
                    
                    api_view = BudgetItemsForOrgPeriodAPIView()
                    api_request = factory.get(f'/reports/api/budget-items-for-org-period/{period.pk}/{org["id"]}/')
                    api_request.user = user
                    
                    response = api_view.get(api_request, period.pk, org['id'])
                    print(f"   وضعیت HTTP: {response.status_code}")
                    
                    if response.status_code == 200:
                        import json
                        data = json.loads(response.content.decode('utf-8'))
                        print(f"   وضعیت API: {data.get('status', 'unknown')}")
                        print(f"   طول HTML: {len(data.get('html_content', ''))}")
                        
                        if data.get('status') == 'success':
                            print("   ✅ API سرفصل‌ها موفقیت‌آمیز بود")
                            
                            # بررسی محتوای HTML
                            html_content = data.get('html_content', '')
                            if 'سرفصل‌های بودجه' in html_content:
                                print("   ✅ محتوای HTML شامل سرفصل‌های بودجه است")
                            else:
                                print("   ⚠️ محتوای HTML شامل سرفصل‌های بودجه نیست")
                                
                            if 'تنخواهها' in html_content:
                                print("   ✅ محتوای HTML شامل تنخواهها است")
                            else:
                                print("   ⚠️ محتوای HTML شامل تنخواهها نیست")
                        else:
                            print(f"   ❌ API سرفصل‌ها ناموفق: {data.get('status')}")
                    else:
                        print(f"   ❌ خطای HTTP در API سرفصل‌ها: {response.status_code}")
                        print(f"   محتوا: {response.content.decode('utf-8')[:200]}...")
                
                # 4. تست render_to_response
                print("\n4️⃣ تست render_to_response...")
                response = view.render_to_response(context)
                print(f"   وضعیت HTTP: {response.status_code}")
                print(f"   نوع محتوا: {response.get('Content-Type', 'نامشخص')}")
                
                if response.status_code == 200:
                    print("   ✅ render_to_response موفقیت‌آمیز بود")
                else:
                    print(f"   ❌ خطای HTTP در render_to_response: {response.status_code}")
            
            else:
                print("   ⚠️ هیچ داده‌ای پردازش نشده")
        else:
            print("   ⚠️ هیچ دوره بودجه‌ای یافت نشد")
        
        print("\n✅ تست کامل شد!")
        
    except Exception as e:
        print(f"❌ خطا در تست: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_comprehensive_report()
