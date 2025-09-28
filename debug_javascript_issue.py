#!/usr/bin/env python
"""
دیباگ مشکل JavaScript در بارگذاری سرفصل‌های بودجه
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

def debug_javascript_issue():
    """دیباگ مشکل JavaScript"""
    
    print("🔍 دیباگ مشکل JavaScript در بارگذاری سرفصل‌های بودجه...")
    print("=" * 70)
    
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
        
        # تست get_context_data
        context = view.get_context_data()
        processed_data = context.get('budget_periods_data', [])
        
        if processed_data:
            period_data = processed_data[0]
            print(f"   دوره: {period_data['period'].name}")
            print(f"   تعداد سازمان‌ها: {len(period_data['organization_summaries'])}")
            
            if period_data['organization_summaries']:
                org = period_data['organization_summaries'][0]
                print(f"   سازمان: {org['name']}")
                print(f"   URL سرفصل‌ها: {org['budget_items_ajax_url']}")
                
                # 2. تست API
                print("\n2️⃣ تست API سرفصل‌ها...")
                api_view = BudgetItemsForOrgPeriodAPIView()
                api_request = factory.get(org['budget_items_ajax_url'])
                api_request.user = user
                api_request.META['HTTP_HOST'] = '127.0.0.1:8000'
                
                response = api_view.get(api_request, period_data['period'].pk, org['id'])
                print(f"   وضعیت HTTP: {response.status_code}")
                
                if response.status_code == 200:
                    import json
                    data = json.loads(response.content.decode('utf-8'))
                    print(f"   وضعیت API: {data.get('status', 'unknown')}")
                    print(f"   طول HTML: {len(data.get('html_content', ''))}")
                    
                    if data.get('status') == 'success':
                        print("   ✅ API موفقیت‌آمیز بود")
                        
                        # بررسی محتوای HTML
                        html_content = data.get('html_content', '')
                        
                        # بررسی وجود عناصر مهم
                        checks = [
                            ('سرفصل‌های بودجه', 'عنوان سرفصل‌های بودجه'),
                            ('btn-load-tankhahs', 'دکمه‌های بارگذاری تنخواهها'),
                            ('tankhahsContainer', 'کانتینر تنخواهها'),
                            ('table', 'جدول'),
                            ('thead', 'هدر جدول'),
                            ('tbody', 'بدنه جدول'),
                        ]
                        
                        print("\n3️⃣ بررسی محتوای HTML:")
                        for check, description in checks:
                            if check in html_content:
                                print(f"   ✅ {description}: موجود")
                            else:
                                print(f"   ❌ {description}: موجود نیست")
                        
                        # بررسی ساختار HTML
                        print("\n4️⃣ بررسی ساختار HTML:")
                        if '<div class="budget-items-section">' in html_content:
                            print("   ✅ بخش سرفصل‌های بودجه موجود است")
                        else:
                            print("   ❌ بخش سرفصل‌های بودجه موجود نیست")
                        
                        if '<table class="table table-sm table-hover">' in html_content:
                            print("   ✅ جدول موجود است")
                        else:
                            print("   ❌ جدول موجود نیست")
                        
                        if '<thead class="table-light">' in html_content:
                            print("   ✅ هدر جدول موجود است")
                        else:
                            print("   ❌ هدر جدول موجود نیست")
                        
                        if '<tbody>' in html_content:
                            print("   ✅ بدنه جدول موجود است")
                        else:
                            print("   ❌ بدنه جدول موجود نیست")
                        
                        # بررسی دکمه‌ها
                        print("\n5️⃣ بررسی دکمه‌ها:")
                        if 'btn-load-tankhahs' in html_content:
                            print("   ✅ دکمه‌های بارگذاری تنخواهها موجود است")
                        else:
                            print("   ❌ دکمه‌های بارگذاری تنخواهها موجود نیست")
                        
                        if 'data-url=' in html_content:
                            print("   ✅ ویژگی data-url موجود است")
                        else:
                            print("   ❌ ویژگی data-url موجود نیست")
                        
                        if 'data-target=' in html_content:
                            print("   ✅ ویژگی data-target موجود است")
                        else:
                            print("   ❌ ویژگی data-target موجود نیست")
                        
                        # نمایش نمونه HTML
                        print("\n6️⃣ نمونه HTML:")
                        lines = html_content.split('\n')
                        for i, line in enumerate(lines[:20]):
                            print(f"   {i+1:2d}: {line}")
                        
                        if len(lines) > 20:
                            print(f"   ... و {len(lines) - 20} خط دیگر")
                    
                    else:
                        print(f"   ❌ API ناموفق: {data.get('status')}")
                else:
                    print(f"   ❌ خطای HTTP در API: {response.status_code}")
                    print(f"   محتوا: {response.content.decode('utf-8')[:200]}...")
        
        print("\n✅ دیباگ کامل شد!")
        
    except Exception as e:
        print(f"❌ خطا در دیباگ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_javascript_issue()
