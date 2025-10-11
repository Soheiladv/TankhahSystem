#!/usr/bin/env python
"""
اسکریپت اجرای تست برگشت بودجه
این اسکریپت تست جامع برگشت بودجه را اجرا می‌کند و نتایج را نمایش می‌دهد
"""

import os
import sys
import django
from datetime import datetime
import logging

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.test.utils import get_runner
from django.conf import settings
from test_budget_return_comprehensive import BudgetReturnComprehensiveTest

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('budget_return_test.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def run_django_tests():
    """اجرای تست‌ها با استفاده از Django Test Runner"""
    logger.info("شروع اجرای تست‌ها با Django Test Runner...")
    
    # ایجاد Test Runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # اجرای تست‌ها
    failures = test_runner.run_tests(["test_budget_return_comprehensive"])
    
    if failures:
        logger.error(f"❌ {failures} تست ناموفق بود")
        return False
    else:
        logger.info("✅ تمام تست‌ها با موفقیت انجام شدند")
        return True

def run_manual_test():
    """اجرای تست دستی"""
    logger.info("شروع اجرای تست دستی...")
    
    try:
        # ایجاد نمونه تست
        test_instance = BudgetReturnComprehensiveTest()
        
        # اجرای متدهای تست
        test_instance.setUp()
        
        logger.info("\n" + "="*50)
        logger.info("🔍 تست برگشت بودجه از تنخواه")
        logger.info("="*50)
        test_instance.test_budget_return_from_tankhah()
        
        logger.info("\n" + "="*50)
        logger.info("🔍 تست چندین برگشت بودجه")
        logger.info("="*50)
        test_instance.test_multiple_budget_returns()
        
        logger.info("\n" + "="*50)
        logger.info("🔍 تست اعتبارسنجی")
        logger.info("="*50)
        test_instance.test_budget_return_validation()
        
        # پاکسازی
        test_instance.tearDown()
        
        logger.info("\n" + "="*50)
        logger.info("✅ تمام تست‌ها با موفقیت انجام شدند!")
        logger.info("="*50)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطا در اجرای تست: {str(e)}")
        logger.error("جزئیات خطا:", exc_info=True)
        return False

def generate_test_report():
    """تولید گزارش تست"""
    logger.info("تولید گزارش تست...")
    
    report = f"""
# گزارش تست برگشت بودجه از تنخواه

## تاریخ اجرا: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}

## خلاصه تست‌ها

### 1. تست برگشت بودجه از تنخواه
- ✅ ثبت تراکنش برگشت
- ✅ به‌روزرسانی مانده تنخواه
- ✅ به‌روزرسانی مانده تخصیص بودجه
- ✅ به‌روزرسانی مانده دوره بودجه کلان
- ✅ ثبت در تاریخچه بودجه

### 2. تست چندین برگشت بودجه
- ✅ ثبت چندین تراکنش برگشت متوالی
- ✅ محاسبه صحیح مجموع برگشتی
- ✅ به‌روزرسانی صحیح مبالغ در تمام سطوح

### 3. تست اعتبارسنجی
- ✅ جلوگیری از برگشت مبلغ بیش از مانده تنخواه
- ✅ جلوگیری از برگشت مبلغ منفی
- ✅ اعتبارسنجی صحیح ورودی‌ها

## نتیجه‌گیری
تمام تست‌ها با موفقیت انجام شدند و سیستم برگشت بودجه عملکرد صحیحی دارد.

## جزئیات فنی
- مدل‌های تست شده: BudgetTransaction, BudgetAllocation, BudgetPeriod, Tankhah
- عملیات‌های تست شده: RETURN transaction, budget calculations, validation
- سطوح بودجه تست شده: تنخواه، تخصیص، پروژه، دوره بودجه کلان
"""
    
    # ذخیره گزارش
    with open('budget_return_test_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info("گزارش تست در فایل budget_return_test_report.md ذخیره شد")

def main():
    """تابع اصلی"""
    logger.info("=" * 60)
    logger.info("شروع تست جامع سیستم برگشت بودجه")
    logger.info("=" * 60)
    
    # انتخاب روش اجرا
    if len(sys.argv) > 1 and sys.argv[1] == '--django':
        success = run_django_tests()
    else:
        success = run_manual_test()
    
    # تولید گزارش
    if success:
        generate_test_report()
    
    # نمایش نتیجه نهایی
    if success:
        logger.info("\n🎉 تست‌ها با موفقیت کامل انجام شدند!")
        logger.info("📊 گزارش تست در فایل budget_return_test_report.md موجود است")
        logger.info("📝 لاگ کامل در فایل budget_return_test.log موجود است")
    else:
        logger.error("\n💥 برخی تست‌ها ناموفق بودند!")
        logger.error("📝 جزئیات خطا در فایل budget_return_test.log موجود است")
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
