#!/usr/bin/env python3
"""
اسکریپت راه‌اندازی scheduler برای اعتبارسنجی روزانه USB Dongle
"""

import os
import sys
import subprocess
import platform
from datetime import datetime, time

def setup_windows_scheduler():
    """راه‌اندازی Windows Task Scheduler"""
    try:
        # مسیر اسکریپت
        script_path = os.path.join(os.path.dirname(__file__), 'daily_usb_validation.bat')
        project_path = os.path.dirname(os.path.dirname(__file__))
        
        # دستور schtasks برای ایجاد task
        task_name = "USBDongleDailyValidation"
        command = f'''schtasks /create /tn "{task_name}" /tr "{script_path}" /sc daily /st 09:00 /f'''
        
        print(f"ایجاد Windows Task: {task_name}")
        print(f"دستور: {command}")
        
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Windows Task با موفقیت ایجاد شد")
            print(f"📅 زمان اجرا: هر روز ساعت 09:00")
            print(f"📁 مسیر اسکریپت: {script_path}")
        else:
            print("❌ خطا در ایجاد Windows Task:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی Windows Scheduler: {e}")

def setup_linux_cron():
    """راه‌اندازی Linux Cron Job"""
    try:
        # مسیر اسکریپت
        script_path = os.path.join(os.path.dirname(__file__), 'daily_usb_validation.sh')
        project_path = os.path.dirname(os.path.dirname(__file__))
        
        # محتوای cron job
        cron_entry = f"0 9 * * * cd {project_path} && python manage.py daily_usb_validation --stats >> /var/log/usb_validation.log 2>&1"
        
        print("ایجاد Linux Cron Job:")
        print(f"📅 زمان اجرا: هر روز ساعت 09:00")
        print(f"📁 مسیر پروژه: {project_path}")
        print(f"📝 Cron Entry: {cron_entry}")
        
        # اضافه کردن به crontab
        with open('/tmp/usb_cron', 'w') as f:
            f.write(cron_entry + '\n')
        
        subprocess.run(['crontab', '/tmp/usb_cron'])
        os.remove('/tmp/usb_cron')
        
        print("✅ Cron Job با موفقیت اضافه شد")
        
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی Linux Cron: {e}")

def create_linux_script():
    """ایجاد اسکریپت Linux"""
    script_content = '''#!/bin/bash
# اسکریپت اعتبارسنجی روزانه USB Dongle برای Linux

echo "شروع اعتبارسنجی روزانه USB Dongle..."
echo "تاریخ: $(date)"

# تغییر به دایرکتوری پروژه
cd "$(dirname "$0")/.."

# اجرای دستور اعتبارسنجی
python manage.py daily_usb_validation --stats

# بررسی نتیجه
if [ $? -eq 0 ]; then
    echo "اعتبارسنجی روزانه با موفقیت انجام شد"
else
    echo "خطا در اعتبارسنجی روزانه"
fi

echo "پایان اعتبارسنجی روزانه"
'''
    
    script_path = os.path.join(os.path.dirname(__file__), 'daily_usb_validation.sh')
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # تنظیم مجوز اجرا
    os.chmod(script_path, 0o755)
    print(f"✅ اسکریپت Linux ایجاد شد: {script_path}")

def test_validation():
    """تست اعتبارسنجی"""
    try:
        print("🧪 تست اعتبارسنجی...")
        project_path = os.path.dirname(os.path.dirname(__file__))
        os.chdir(project_path)
        
        result = subprocess.run([
            sys.executable, 'manage.py', 'daily_usb_validation', '--stats'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ تست اعتبارسنجی موفق")
            print(result.stdout)
        else:
            print("❌ تست اعتبارسنجی ناموفق")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ خطا در تست: {e}")

def main():
    """تابع اصلی"""
    print("🚀 راه‌اندازی Scheduler برای اعتبارسنجی روزانه USB Dongle")
    print("=" * 60)
    
    # تشخیص سیستم عامل
    system = platform.system()
    print(f"سیستم عامل: {system}")
    
    if system == "Windows":
        print("\n📋 راه‌اندازی Windows Task Scheduler...")
        setup_windows_scheduler()
        
    elif system == "Linux":
        print("\n📋 راه‌اندازی Linux Cron Job...")
        create_linux_script()
        setup_linux_cron()
        
    else:
        print(f"❌ سیستم عامل {system} پشتیبانی نمی‌شود")
        return
    
    print("\n🧪 تست اعتبارسنجی...")
    test_validation()
    
    print("\n✅ راه‌اندازی تکمیل شد!")
    print("\n📝 نکات مهم:")
    print("1. اطمینان حاصل کنید که USB در زمان اجرای scheduled task متصل است")
    print("2. لاگ‌ها در /var/log/usb_validation.log (Linux) یا Event Viewer (Windows) ذخیره می‌شوند")
    print("3. برای تغییر زمان اجرا، Task Scheduler یا crontab را ویرایش کنید")

if __name__ == "__main__":
    main()
