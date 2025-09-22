#!/usr/bin/env python
"""
اسکریپت تست dongle از طریق وب
این اسکریپت از طریق HTTP API با سیستم dongle ارتباط برقرار می‌کند
"""

import requests
import json
import time

def test_web_dongle():
    """تست dongle از طریق وب"""
    print("🌐 تست dongle از طریق وب...")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8000"
    
    # تست 1: بررسی وضعیت سرور
    print("1. بررسی وضعیت سرور...")
    try:
        response = requests.get(f"{base_url}/usb-key-validator/enhanced/", timeout=10)
        if response.status_code == 200:
            print("✅ سرور در دسترس است")
        else:
            print(f"❌ سرور در دسترس نیست (کد: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ خطا در اتصال به سرور: {e}")
        return False
    
    # تست 2: دریافت لیست USB ها
    print("\n2. دریافت لیست USB ها...")
    try:
        # این یک درخواست GET ساده است
        response = requests.get(f"{base_url}/usb-key-validator/enhanced/", timeout=10)
        if response.status_code == 200:
            print("✅ صفحه USB validation در دسترس است")
            print("   می‌توانید از طریق مرورگر به آدرس زیر بروید:")
            print(f"   {base_url}/usb-key-validator/enhanced/")
        else:
            print(f"❌ صفحه در دسترس نیست (کد: {response.status_code})")
    except Exception as e:
        print(f"❌ خطا در دریافت صفحه: {e}")
    
    # تست 3: بررسی داشبورد
    print("\n3. بررسی داشبورد...")
    try:
        response = requests.get(f"{base_url}/usb-key-validator/dashboard/", timeout=10)
        if response.status_code == 200:
            print("✅ داشبورد در دسترس است")
            print("   می‌توانید از طریق مرورگر به آدرس زیر بروید:")
            print(f"   {base_url}/usb-key-validator/dashboard/")
        else:
            print(f"❌ داشبورد در دسترس نیست (کد: {response.status_code})")
    except Exception as e:
        print(f"❌ خطا در دریافت داشبورد: {e}")
    
    # تست 4: بررسی وضعیت قفل
    print("\n4. بررسی وضعیت قفل...")
    try:
        response = requests.get(f"{base_url}/accounts/set_time_lock/", timeout=10)
        if response.status_code == 200:
            print("✅ صفحه قفل در دسترس است")
            print("   می‌توانید از طریق مرورگر به آدرس زیر بروید:")
            print(f"   {base_url}/accounts/set_time_lock/")
        else:
            print(f"❌ صفحه قفل در دسترس نیست (کد: {response.status_code})")
    except Exception as e:
        print(f"❌ خطا در دریافت صفحه قفل: {e}")
    
    print(f"\n🎯 راهنمای استفاده:")
    print(f"=" * 60)
    print(f"1. مرورگر را باز کنید")
    print(f"2. به آدرس زیر بروید:")
    print(f"   {base_url}/usb-key-validator/enhanced/")
    print(f"3. فلش USB را انتخاب کنید")
    print(f"4. اطلاعات شرکت را وارد کنید:")
    print(f"   - نام شرکت: توسعه گردشگری ایران")
    print(f"   - شناسه نرم‌افزار: RCMS")
    print(f"5. دکمه 'ایجاد Dongle' را کلیک کنید")
    print(f"6. اگر خطای Access Denied دریافت کردید:")
    print(f"   - Django را به عنوان Administrator اجرا کنید")
    print(f"   - یا از اسکریپت run_as_admin_auto.ps1 استفاده کنید")
    
    return True

if __name__ == "__main__":
    try:
        print("🔐 تست سیستم USB Dongle از طریق وب")
        print("=" * 60)
        
        test_web_dongle()
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nبرای خروج Enter را فشار دهید...")
