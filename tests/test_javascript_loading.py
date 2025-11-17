#!/usr/bin/env python
"""
تست JavaScript و بارگذاری سرفصل‌های بودجه
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from reports.ComprehensiveBudgetReportView_fixed import ComprehensiveBudgetReportView, BudgetItemsForOrgPeriodAPIView
from budgets.models import BudgetPeriod, BudgetAllocation
from core.models import Organization

def test_javascript_loading():
    """تست JavaScript و بارگذاری سرفصل‌های بودجه"""
    
    print("🧪 تست JavaScript و بارگذاری سرفصل‌های بودجه...")
    print("=" * 60)
    
    try:
        # ایجاد کلاینت Django
        client = Client()
        
        # پیدا کردن کاربر
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            print("❌ کاربر سوپروایزر پیدا نشد!")
            return
        
        # لاگین کاربر
        client.force_login(user)
        
        # 1. تست صفحه اصلی
        print("1️⃣ تست صفحه اصلی گزارش...")
        response = client.get('/reports/reports/comprehensive-budget/')
        print(f"   وضعیت HTTP: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ صفحه اصلی بارگذاری شد")
            
            # بررسی محتوای HTML
            content = response.content.decode('utf-8')
            
            # بررسی وجود JavaScript
            if 'btn-load-items' in content:
                print("   ✅ دکمه‌های بارگذاری سرفصل‌ها موجود است")
            else:
                print("   ❌ دکمه‌های بارگذاری سرفصل‌ها موجود نیست")
            
            if 'budgetItemsContainer' in content:
                print("   ✅ کانتینر سرفصل‌های بودجه موجود است")
            else:
                print("   ❌ کانتینر سرفصل‌های بودجه موجود نیست")
            
            if 'در حال بارگذاری سرفصل‌های بودجه' in content:
                print("   ✅ پیام بارگذاری موجود است")
            else:
                print("   ❌ پیام بارگذاری موجود نیست")
            
            # بررسی وجود CSRF token
            if 'csrfmiddlewaretoken' in content:
                print("   ✅ CSRF token موجود است")
            else:
                print("   ❌ CSRF token موجود نیست")
            
            # بررسی وجود JavaScript
            if 'addEventListener' in content:
                print("   ✅ JavaScript موجود است")
            else:
                print("   ❌ JavaScript موجود نیست")
            
            # 2. تست API endpoint
            print("\n2️⃣ تست API endpoint...")
            
            # پیدا کردن دوره و سازمان
            period = BudgetPeriod.objects.filter(is_active=True, is_completed=False).first()
            if not period:
                print("   ❌ هیچ دوره بودجه‌ای یافت نشد!")
                return
            
            org = Organization.objects.filter(is_active=True).first()
            if not org:
                print("   ❌ هیچ سازمانی یافت نشد!")
                return
            
            print(f"   دوره: {period.name}")
            print(f"   سازمان: {org.name}")
            
            # تست API
            api_url = f'/reports/api/budget-items-for-org-period/{period.pk}/{org.pk}/'
            print(f"   API URL: {api_url}")
            
            api_response = client.get(api_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            print(f"   وضعیت HTTP: {api_response.status_code}")
            
            if api_response.status_code == 200:
                print("   ✅ API موفقیت‌آمیز بود")
                
                import json
                data = json.loads(api_response.content.decode('utf-8'))
                print(f"   وضعیت API: {data.get('status', 'unknown')}")
                print(f"   طول HTML: {len(data.get('html_content', ''))}")
                
                if data.get('status') == 'success':
                    print("   ✅ API داده‌ها را با موفقیت برگرداند")
                    
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
                    print(f"   ❌ API ناموفق: {data.get('status')}")
            else:
                print(f"   ❌ خطای HTTP در API: {api_response.status_code}")
                print(f"   محتوا: {api_response.content.decode('utf-8')[:200]}...")
            
            # 3. بررسی JavaScript console
            print("\n3️⃣ بررسی JavaScript console...")
            print("   برای بررسی JavaScript console، مراحل زیر را انجام دهید:")
            print("   1. صفحه را در مرورگر باز کنید")
            print("   2. F12 را فشار دهید")
            print("   3. به تب Console بروید")
            print("   4. روی دکمه 'نمایش' کلیک کنید")
            print("   5. خطاهای JavaScript را بررسی کنید")
            
        else:
            print(f"   ❌ خطای HTTP در صفحه اصلی: {response.status_code}")
            print(f"   محتوا: {response.content.decode('utf-8')[:200]}...")
        
        print("\n✅ تست کامل شد!")
        
    except Exception as e:
        print(f"❌ خطا در تست: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_javascript_loading()


