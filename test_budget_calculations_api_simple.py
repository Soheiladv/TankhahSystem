#!/usr/bin/env python
"""
تست ساده API های محاسباتی بودجه
این فایل برای تست سریع API ها بدون نیاز به Django Test Framework طراحی شده است.
"""

import os
import sys
import django
import requests
import json
import time
from decimal import Decimal

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

class SimpleAPITester:
    """کلاس تست ساده API ها"""
    
    def __init__(self):
        self.client = Client(HTTP_HOST='localhost')
        self.base_url = 'http://localhost:8000'
        self.test_results = []
        
    def create_test_user(self):
        """ایجاد کاربر تست"""
        try:
            self.user = User.objects.get(username='testuser')
        except User.DoesNotExist:
            try:
                self.user = User.objects.create_user(
                    username='testuser',
                    email='test@example.com',
                    password='testpass123'
                )
            except Exception as e:
                # اگر کاربر با ایمیل مشابه وجود دارد، آن را حذف و دوباره ایجاد کن
                try:
                    existing_user = User.objects.get(email='test@example.com')
                    existing_user.delete()
                    self.user = User.objects.create_user(
                        username='testuser',
                        email='test@example.com',
                        password='testpass123'
                    )
                except:
                    # اگر همچنان مشکل داشت، از ایمیل متفاوت استفاده کن
                    self.user = User.objects.create_user(
                        username='testuser',
                        email=f'test_{int(time.time())}@example.com',
                        password='testpass123'
                    )
        
        self.client.force_login(self.user)
        print("✅ کاربر تست ایجاد شد")
    
    def test_calculations_overview(self):
        """تست نمای کلی API ها"""
        try:
            url = reverse('budget_calculations_overview')
            response = self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ نمای کلی API ها:")
                print(f"   - تعداد توابع: {data.get('total_functions', 0)}")
                print(f"   - تعداد دسته‌ها: {len(data.get('functions', {}))}")
                self.test_results.append(('نمای کلی API ها', 'موفق', response.status_code))
            else:
                print(f"❌ نمای کلی API ها: خطا {response.status_code}")
                self.test_results.append(('نمای کلی API ها', 'خطا', response.status_code))
                
        except Exception as e:
            print(f"❌ نمای کلی API ها: خطا - {str(e)}")
            self.test_results.append(('نمای کلی API ها', 'خطا', str(e)))
    
    def test_allocation_calculations(self):
        """تست محاسبات تخصیص بودجه"""
        try:
            url = reverse('budget_allocation_calculations')
            
            # تست GET (محاسبه مبلغ بر اساس درصد)
            params = {
                'base_amount': '1000000',
                'percentage': '10'
            }
            response = self.client.get(url, params)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ محاسبه مبلغ بر اساس درصد:")
                print(f"   - مبلغ پایه: {data.get('base_amount', 0):,.0f}")
                print(f"   - درصد: {data.get('percentage', 0)}%")
                print(f"   - مبلغ محاسبه شده: {data.get('threshold_amount', 0):,.0f}")
                self.test_results.append(('محاسبه مبلغ بر اساس درصد', 'موفق', response.status_code))
            else:
                print(f"❌ محاسبه مبلغ بر اساس درصد: خطا {response.status_code}")
                self.test_results.append(('محاسبه مبلغ بر اساس درصد', 'خطا', response.status_code))
                
        except Exception as e:
            print(f"❌ محاسبات تخصیص بودجه: خطا - {str(e)}")
            self.test_results.append(('محاسبات تخصیص بودجه', 'خطا', str(e)))
    
    def test_organization_calculations(self):
        """تست محاسبات بودجه سازمان"""
        try:
            url = reverse('budget_organization_calculations')
            
            # تست GET (دریافت لیست سازمان‌ها)
            response = self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ لیست سازمان‌ها:")
                print(f"   - تعداد سازمان‌ها: {data.get('total_count', 0)}")
                self.test_results.append(('لیست سازمان‌ها', 'موفق', response.status_code))
            else:
                print(f"❌ لیست سازمان‌ها: خطا {response.status_code}")
                self.test_results.append(('لیست سازمان‌ها', 'خطا', response.status_code))
                
        except Exception as e:
            print(f"❌ محاسبات بودجه سازمان: خطا - {str(e)}")
            self.test_results.append(('محاسبات بودجه سازمان', 'خطا', str(e)))
    
    def test_project_calculations(self):
        """تست محاسبات بودجه پروژه"""
        try:
            url = reverse('budget_project_calculations')
            
            # تست GET (دریافت لیست پروژه‌ها)
            response = self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ لیست پروژه‌ها:")
                print(f"   - تعداد پروژه‌ها: {data.get('total_count', 0)}")
                self.test_results.append(('لیست پروژه‌ها', 'موفق', response.status_code))
            else:
                print(f"❌ لیست پروژه‌ها: خطا {response.status_code}")
                self.test_results.append(('لیست پروژه‌ها', 'خطا', response.status_code))
                
        except Exception as e:
            print(f"❌ محاسبات بودجه پروژه: خطا - {str(e)}")
            self.test_results.append(('محاسبات بودجه پروژه', 'خطا', str(e)))
    
    def test_subproject_calculations(self):
        """تست محاسبات بودجه زیرپروژه"""
        try:
            url = reverse('budget_subproject_calculations')
            
            # تست GET (دریافت لیست زیرپروژه‌ها)
            response = self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ لیست زیرپروژه‌ها:")
                print(f"   - تعداد زیرپروژه‌ها: {data.get('total_count', 0)}")
                self.test_results.append(('لیست زیرپروژه‌ها', 'موفق', response.status_code))
            else:
                print(f"❌ لیست زیرپروژه‌ها: خطا {response.status_code}")
                self.test_results.append(('لیست زیرپروژه‌ها', 'خطا', response.status_code))
                
        except Exception as e:
            print(f"❌ محاسبات بودجه زیرپروژه: خطا - {str(e)}")
            self.test_results.append(('محاسبات بودجه زیرپروژه', 'خطا', str(e)))
    
    def test_tankhah_calculations(self):
        """تست محاسبات بودجه تنخواه"""
        try:
            url = reverse('budget_tankhah_calculations')
            
            # تست GET (دریافت لیست تنخواه‌ها)
            response = self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ لیست تنخواه‌ها:")
                print(f"   - تعداد تنخواه‌ها: {data.get('total_count', 0)}")
                self.test_results.append(('لیست تنخواه‌ها', 'موفق', response.status_code))
            else:
                print(f"❌ لیست تنخواه‌ها: خطا {response.status_code}")
                self.test_results.append(('لیست تنخواه‌ها', 'خطا', response.status_code))
                
        except Exception as e:
            print(f"❌ محاسبات بودجه تنخواه: خطا - {str(e)}")
            self.test_results.append(('محاسبات بودجه تنخواه', 'خطا', str(e)))
    
    def test_factor_calculations(self):
        """تست محاسبات بودجه فاکتور"""
        try:
            url = reverse('budget_factor_calculations')
            
            # تست GET (دریافت لیست فاکتورها)
            response = self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ لیست فاکتورها:")
                print(f"   - تعداد فاکتورها: {data.get('total_count', 0)}")
                self.test_results.append(('لیست فاکتورها', 'موفق', response.status_code))
            else:
                print(f"❌ لیست فاکتورها: خطا {response.status_code}")
                self.test_results.append(('لیست فاکتورها', 'خطا', response.status_code))
                
        except Exception as e:
            print(f"❌ محاسبات بودجه فاکتور: خطا - {str(e)}")
            self.test_results.append(('محاسبات بودجه فاکتور', 'خطا', str(e)))
    
    def test_utility_calculations(self):
        """تست توابع کمکی محاسبات"""
        try:
            url = reverse('budget_utility_calculations')
            
            # تست GET (دریافت لیست توابع کمکی)
            response = self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ لیست توابع کمکی:")
                print(f"   - تعداد توابع: {data.get('total_functions', 0)}")
                self.test_results.append(('لیست توابع کمکی', 'موفق', response.status_code))
            else:
                print(f"❌ لیست توابع کمکی: خطا {response.status_code}")
                self.test_results.append(('لیست توابع کمکی', 'خطا', response.status_code))
                
        except Exception as e:
            print(f"❌ توابع کمکی محاسبات: خطا - {str(e)}")
            self.test_results.append(('توابع کمکی محاسبات', 'خطا', str(e)))
    
    def test_batch_calculations(self):
        """تست محاسبات دسته‌ای"""
        try:
            url = reverse('budget_batch_calculations')
            
            # تست GET (دریافت نمونه محاسبات دسته‌ای)
            response = self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ نمونه محاسبات دسته‌ای:")
                print(f"   - تعداد نمونه‌ها: {len(data.get('sample_calculations', []))}")
                self.test_results.append(('نمونه محاسبات دسته‌ای', 'موفق', response.status_code))
            else:
                print(f"❌ نمونه محاسبات دسته‌ای: خطا {response.status_code}")
                self.test_results.append(('نمونه محاسبات دسته‌ای', 'خطا', response.status_code))
                
        except Exception as e:
            print(f"❌ محاسبات دسته‌ای: خطا - {str(e)}")
            self.test_results.append(('محاسبات دسته‌ای', 'خطا', str(e)))
    
    def test_authentication(self):
        """تست احراز هویت"""
        try:
            # تست بدون احراز هویت
            client = Client(HTTP_HOST='localhost')
            url = reverse('budget_calculations_overview')
            response = client.get(url)
            
            if response.status_code in [401, 302]:  # 401 یا 302 هر دو قابل قبول هستند
                print("✅ احراز هویت: دسترسی بدون احراز هویت رد شد")
                self.test_results.append(('احراز هویت', 'موفق', response.status_code))
            else:
                print(f"❌ احراز هویت: انتظار 401 یا 302، دریافت {response.status_code}")
                self.test_results.append(('احراز هویت', 'خطا', response.status_code))
                
        except Exception as e:
            print(f"❌ احراز هویت: خطا - {str(e)}")
            self.test_results.append(('احراز هویت', 'خطا', str(e)))
    
    def run_all_tests(self):
        """اجرای تمام تست‌ها"""
        print("🚀 شروع تست API های محاسباتی بودجه")
        print("=" * 50)
        
        # ایجاد کاربر تست
        self.create_test_user()
        print()
        
        # اجرای تست‌ها
        self.test_calculations_overview()
        print()
        
        self.test_allocation_calculations()
        print()
        
        self.test_organization_calculations()
        print()
        
        self.test_project_calculations()
        print()
        
        self.test_subproject_calculations()
        print()
        
        self.test_tankhah_calculations()
        print()
        
        self.test_factor_calculations()
        print()
        
        self.test_utility_calculations()
        print()
        
        self.test_batch_calculations()
        print()
        
        self.test_authentication()
        print()
        
        # نمایش نتایج
        self.print_results()
    
    def print_results(self):
        """نمایش نتایج تست"""
        print("=" * 50)
        print("📊 نتایج تست:")
        print("=" * 50)
        
        successful = 0
        failed = 0
        
        for test_name, status, details in self.test_results:
            if status == 'موفق':
                print(f"✅ {test_name}: {status}")
                successful += 1
            else:
                print(f"❌ {test_name}: {status} - {details}")
                failed += 1
        
        print("=" * 50)
        print(f"📈 آمار کلی:")
        print(f"   - موفق: {successful}")
        print(f"   - ناموفق: {failed}")
        print(f"   - مجموع: {len(self.test_results)}")
        print(f"   - درصد موفقیت: {(successful/len(self.test_results)*100):.1f}%")
        print("=" * 50)
        
        if failed == 0:
            print("🎉 تمام تست‌ها با موفقیت انجام شد!")
        else:
            print(f"⚠️  {failed} تست ناموفق بود. لطفاً خطاها را بررسی کنید.")

def main():
    """تابع اصلی"""
    try:
        tester = SimpleAPITester()
        tester.run_all_tests()
    except Exception as e:
        print(f"❌ خطای کلی: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
