#!/usr/bin/env python
"""
تغییر وضعیت اعتبارسنجی USB dongle
این اسکریپت اعتبارسنجی USB dongle را فعال/غیرفعال می‌کند
"""

import os
import sys
import re
from datetime import datetime

def read_env_file():
    """خواندن فایل .env"""
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None

def write_env_file(content):
    """نوشتن فایل .env"""
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ خطا در نوشتن فایل .env: {e}")
        return False

def update_env_setting(key, value):
    """به‌روزرسانی تنظیم در فایل .env"""
    content = read_env_file()
    if content is None:
        print("❌ فایل .env یافت نشد")
        return False
    
    # جستجو و جایگزینی
    pattern = rf'^{key}=.*$'
    replacement = f'{key}={value}'
    
    if re.search(pattern, content, re.MULTILINE):
        # تنظیم موجود است - جایگزینی
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        # تنظیم موجود نیست - اضافه کردن
        new_content = content + f'\n{replacement}\n'
    
    return write_env_file(new_content)

def get_current_setting(key):
    """دریافت تنظیم فعلی از فایل .env"""
    content = read_env_file()
    if content is None:
        return None
    
    pattern = rf'^{key}=(.*)$'
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None

def enable_usb_validation():
    """فعال کردن اعتبارسنجی USB dongle"""
    print("🔧 فعال کردن اعتبارسنجی USB dongle...")
    
    success = update_env_setting('USB_DONGLE_VALIDATION_ENABLED', 'true')
    if success:
        print("✅ اعتبارسنجی USB dongle فعال شد")
        print("⚠️ توجه: Django را restart کنید تا تغییرات اعمال شود")
        print("👥 تأثیر: کاربران نیاز به USB dongle معتبر دارند")
    else:
        print("❌ خطا در فعال کردن اعتبارسنجی")

def disable_usb_validation():
    """غیرفعال کردن اعتبارسنجی USB dongle"""
    print("🚫 غیرفعال کردن اعتبارسنجی USB dongle...")
    
    success = update_env_setting('USB_DONGLE_VALIDATION_ENABLED', 'false')
    if success:
        print("✅ اعتبارسنجی USB dongle غیرفعال شد")
        print("⚠️ توجه: Django را restart کنید تا تغییرات اعمال شود")
        print("👥 تأثیر: همه کاربران می‌توانند بدون مشکل وارد شوند")
    else:
        print("❌ خطا در غیرفعال کردن اعتبارسنجی")

def show_current_status():
    """نمایش وضعیت فعلی"""
    print("📊 وضعیت فعلی اعتبارسنجی USB dongle:")
    print("=" * 50)
    
    current_setting = get_current_setting('USB_DONGLE_VALIDATION_ENABLED')
    if current_setting is None:
        print("❌ تنظیم یافت نشد")
        return
    
    if current_setting.lower() == 'true':
        print("✅ اعتبارسنجی فعال است")
        print("👥 کاربران نیاز به USB dongle معتبر دارند")
        print("⚠️ کاربر snejate و سایر کاربران ممکن است مشکل داشته باشند")
    else:
        print("❌ اعتبارسنجی غیرفعال است")
        print("👥 همه کاربران می‌توانند بدون مشکل وارد شوند")
        print("✅ کاربر snejate و سایر کاربران بدون مشکل هستند")

def show_help():
    """نمایش راهنما"""
    print("📖 راهنمای استفاده:")
    print("=" * 30)
    print("python scripts/toggle_usb_validation.py --enable    # فعال کردن")
    print("python scripts/toggle_usb_validation.py --disable   # غیرفعال کردن")
    print("python scripts/toggle_usb_validation.py --status    # نمایش وضعیت")
    print("python scripts/toggle_usb_validation.py --help      # نمایش راهنما")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='تغییر وضعیت اعتبارسنجی USB dongle')
    parser.add_argument('--enable', action='store_true', help='فعال کردن اعتبارسنجی')
    parser.add_argument('--disable', action='store_true', help='غیرفعال کردن اعتبارسنجی')
    parser.add_argument('--status', action='store_true', help='نمایش وضعیت فعلی')
    parser.add_argument('--show-help', action='store_true', help='نمایش راهنما')
    
    args = parser.parse_args()
    
    if args.enable:
        enable_usb_validation()
    elif args.disable:
        disable_usb_validation()
    elif args.status:
        show_current_status()
    elif args.show_help:
        show_help()
    else:
        show_current_status()
        print("\n" + "="*50)
        show_help()
