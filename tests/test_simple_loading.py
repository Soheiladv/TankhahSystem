#!/usr/bin/env python
"""
تست ساده بارگذاری سرفصل‌های بودجه
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

def test_simple_loading():
    """تست ساده بارگذاری سرفصل‌های بودجه"""
    
    print("🧪 تست ساده بارگذاری سرفصل‌های بودجه...")
    print("=" * 60)
    
    try:
        # ایجاد درخواست تست
        factory = RequestFactory()
        request = factory.get('/reports/reports/comprehensive-budget/')
        request.META['HTTP_HOST'] = '127.0.0.1:8000'
        
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
                print(f"   تعداد سازمان‌ها: {len(period_data['organization_summaries'])}")
                
                # 3. تست API سرفصل‌ها
                if period_data['organization_summaries']:
                    org = period_data['organization_summaries'][0]
                    print(f"\n3️⃣ تست API سرفصل‌ها برای سازمان: {org['name']}")
                    
                    api_view = BudgetItemsForOrgPeriodAPIView()
                    api_request = factory.get(f'/reports/api/budget-items-for-org-period/{period.pk}/{org["id"]}/')
                    api_request.user = user
                    api_request.META['HTTP_HOST'] = '127.0.0.1:8000'
                    
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
                                
                            # بررسی وجود دکمه‌های بارگذاری
                            if 'btn-load-tankhahs' in html_content:
                                print("   ✅ دکمه‌های بارگذاری تنخواهها موجود است")
                            else:
                                print("   ⚠️ دکمه‌های بارگذاری تنخواهها موجود نیست")
                                
                            # بررسی وجود کانتینرها
                            if 'tankhahsContainer' in html_content:
                                print("   ✅ کانتینر تنخواهها موجود است")
                            else:
                                print("   ⚠️ کانتینر تنخواهها موجود نیست")
                        else:
                            print(f"   ❌ API سرفصل‌ها ناموفق: {data.get('status')}")
                    else:
                        print(f"   ❌ خطای HTTP در API سرفصل‌ها: {response.status_code}")
                        print(f"   محتوا: {response.content.decode('utf-8')[:200]}...")
                
                # 4. تست render_to_response
                print("\n4️⃣ تست render_to_response...")
                response = view.render_to_response(context)
                print(f"   وضعیت HTTP: {response.status_code}")
                
                if response.status_code == 200:
                    print("   ✅ render_to_response موفقیت‌آمیز بود")
                    
                    # بررسی محتوای HTML
                    response.render()
                    content = response.content.decode('utf-8')
                    
                    # بررسی وجود JavaScript
                    if 'btn-load-items' in content:
                        print("   ✅ دکمه‌های بارگذاری سرفصل‌ها در HTML موجود است")
                    else:
                        print("   ❌ دکمه‌های بارگذاری سرفصل‌ها در HTML موجود نیست")
                    
                    if 'budgetItemsContainer' in content:
                        print("   ✅ کانتینر سرفصل‌های بودجه در HTML موجود است")
                    else:
                        print("   ❌ کانتینر سرفصل‌های بودجه در HTML موجود نیست")
                    
                    if 'در حال بارگذاری سرفصل‌های بودجه' in content:
                        print("   ✅ پیام بارگذاری در HTML موجود است")
                    else:
                        print("   ❌ پیام بارگذاری در HTML موجود نیست")
                    
                    if 'addEventListener' in content:
                        print("   ✅ JavaScript در HTML موجود است")
                    else:
                        print("   ❌ JavaScript در HTML موجود نیست")
                    
                    if 'csrfmiddlewaretoken' in content:
                        print("   ✅ CSRF token در HTML موجود است")
                    else:
                        print("   ❌ CSRF token در HTML موجود نیست")
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
    test_simple_loading()
