#!/usr/bin/env python
"""
اجرای تمام تست‌های API های محاسباتی بودجه
این فایل تمام تست‌ها را به ترتیب اجرا می‌کند.
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def print_header(title):
    """چاپ هدر زیبا"""
    print("\n" + "=" * 60)
    print(f"🚀 {title}")
    print("=" * 60)

def print_section(title):
    """چاپ بخش"""
    print(f"\n📋 {title}")
    print("-" * 40)

def run_test(test_name, command, description):
    """اجرای یک تست"""
    print_section(f"اجرای {test_name}")
    print(f"توضیحات: {description}")
    print(f"دستور: {command}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 دقیقه timeout
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        if result.returncode == 0:
            print(f"✅ {test_name}: موفق ({execution_time:.2f} ثانیه)")
            return True, execution_time, result.stdout
        else:
            print(f"❌ {test_name}: ناموفق ({execution_time:.2f} ثانیه)")
            print(f"خطا: {result.stderr}")
            return False, execution_time, result.stderr
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {test_name}: timeout (بیش از 5 دقیقه)")
        return False, 300, "Timeout"
    except Exception as e:
        print(f"💥 {test_name}: خطای غیرمنتظره - {str(e)}")
        return False, 0, str(e)

def main():
    """تابع اصلی"""
    print_header("تست‌های جامع API های محاسباتی بودجه")
    
    # تنظیم Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
    
    # لیست تست‌ها
    tests = [
        {
            'name': 'تست‌های ساده',
            'command': 'python test_budget_calculations_api_simple.py',
            'description': 'تست‌های سریع و آسان برای بررسی عملکرد کلی API ها'
        },
        {
            'name': 'تست‌های واحد',
            'command': 'python test_budget_calculations_api_unit.py',
            'description': 'تست‌های متمرکز بر روی توابع محاسباتی'
        },
        {
            'name': 'تست‌های یکپارچگی',
            'command': 'python test_budget_calculations_api_integration.py',
            'description': 'تست‌های کامل با داده‌های واقعی'
        },
        {
            'name': 'تست‌های جامع Django',
            'command': 'python manage.py test tests.test_budget_calculations_api',
            'description': 'تست‌های کامل Django Test Framework'
        }
    ]
    
    # نتایج
    results = []
    total_time = 0
    successful_tests = 0
    failed_tests = 0
    
    # اجرای تست‌ها
    for i, test in enumerate(tests, 1):
        print(f"\n[{i}/{len(tests)}]")
        success, execution_time, output = run_test(
            test['name'],
            test['command'],
            test['description']
        )
        
        results.append({
            'name': test['name'],
            'success': success,
            'time': execution_time,
            'output': output
        })
        
        total_time += execution_time
        
        if success:
            successful_tests += 1
        else:
            failed_tests += 1
    
    # نمایش نتایج نهایی
    print_header("نتایج نهایی")
    
    print(f"📊 آمار کلی:")
    print(f"   - تعداد تست‌ها: {len(tests)}")
    print(f"   - موفق: {successful_tests}")
    print(f"   - ناموفق: {failed_tests}")
    print(f"   - درصد موفقیت: {(successful_tests/len(tests)*100):.1f}%")
    print(f"   - زمان کل: {total_time:.2f} ثانیه")
    
    print(f"\n📋 جزئیات نتایج:")
    for result in results:
        status = "✅ موفق" if result['success'] else "❌ ناموفق"
        print(f"   - {result['name']}: {status} ({result['time']:.2f} ثانیه)")
    
    # نمایش تست‌های ناموفق
    if failed_tests > 0:
        print(f"\n❌ تست‌های ناموفق:")
        for result in results:
            if not result['success']:
                print(f"\n🔍 {result['name']}:")
                print(f"   خطا: {result['output'][:200]}...")
    
    # خلاصه نهایی
    print_header("خلاصه نهایی")
    
    if failed_tests == 0:
        print("🎉 تمام تست‌ها با موفقیت انجام شد!")
        print("✅ API های محاسباتی بودجه آماده استفاده هستند")
        print("✅ سیستم کاملاً عملکرد است")
    else:
        print(f"⚠️ {failed_tests} تست ناموفق بود")
        print("🔧 لطفاً خطاها را بررسی و رفع کنید")
        print("📖 برای راهنمایی بیشتر، README_budget_calculations_api_tests.md را مطالعه کنید")
    
    print(f"\n⏰ زمان اجرا: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return failed_tests == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
