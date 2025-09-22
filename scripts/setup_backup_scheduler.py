#!/usr/bin/env python
"""
اسکریپت نصب و راه‌اندازی سیستم پشتیبان‌گیری
"""

import os
import sys
import django
from pathlib import Path

# اضافه کردن مسیر scripts به Python path
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from config import (
    get_project_root, get_django_settings, ensure_logs_dir
)

def setup_django():
    """تنظیم Django environment"""
    project_root = get_project_root()
    
    # اضافه کردن مسیر پروژه به Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # تنظیم Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', get_django_settings())
    django.setup()

def create_sample_schedule():
    """ایجاد اسکچول نمونه"""
    print("🔧 ایجاد اسکچول نمونه...")
    
    try:
        from notificationApp.models import BackupSchedule
        from accounts.models import CustomUser
        
        # پیدا کردن کاربر admin
        admin_user = CustomUser.objects.filter(is_superuser=True).first()
        if not admin_user:
            print("⚠️ کاربر admin یافت نشد. لطفاً ابتدا یک superuser ایجاد کنید.")
            return False
        
        # بررسی وجود اسکچول نمونه
        if BackupSchedule.objects.filter(name="پشتیبان‌گیری روزانه").exists():
            print("✅ اسکچول نمونه قبلاً ایجاد شده است")
            return True
        
        # ایجاد اسکچول نمونه
        schedule = BackupSchedule.objects.create(
            name="پشتیبان‌گیری روزانه",
            description="پشتیبان‌گیری خودکار روزانه از هر دو دیتابیس",
            frequency="DAILY",
            database="BOTH",
            format_type="JSON",
            encrypt=False,
            is_active=True,
            created_by=admin_user,
            notify_on_success=True,
            notify_on_failure=True
        )
        
        # اضافه کردن admin به گیرندگان اعلان
        schedule.notify_recipients.add(admin_user)
        
        print(f"✅ اسکچول نمونه ایجاد شد: {schedule.name}")
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد اسکچول نمونه: {str(e)}")
        return False

def create_sample_notification_rules():
    """ایجاد قوانین اعلان نمونه"""
    print("🔧 ایجاد قوانین اعلان نمونه...")
    
    try:
        from notificationApp.models import NotificationRule
        from core.models import Post
        
        # بررسی وجود قوانین نمونه
        if NotificationRule.objects.filter(entity_type="BACKUP").exists():
            print("✅ قوانین اعلان نمونه قبلاً ایجاد شده‌اند")
            return True
        
        # پیدا کردن پست‌های موجود
        posts = Post.objects.all()[:3]  # حداکثر 3 پست
        
        # ایجاد قوانین نمونه
        rules_data = [
            {
                'entity_type': 'BACKUP',
                'action': 'STARTED',
                'priority': 'MEDIUM',
                'channel': 'IN_APP',
                'description': 'اعلان شروع پشتیبان‌گیری'
            },
            {
                'entity_type': 'BACKUP',
                'action': 'COMPLETED',
                'priority': 'LOW',
                'channel': 'IN_APP',
                'description': 'اعلان تکمیل پشتیبان‌گیری'
            },
            {
                'entity_type': 'BACKUP',
                'action': 'FAILED',
                'priority': 'HIGH',
                'channel': 'EMAIL',
                'description': 'اعلان خطا در پشتیبان‌گیری'
            }
        ]
        
        for rule_data in rules_data:
            rule = NotificationRule.objects.create(
                entity_type=rule_data['entity_type'],
                action=rule_data['action'],
                priority=rule_data['priority'],
                channel=rule_data['channel']
            )
            
            # اضافه کردن پست‌ها به گیرندگان
            for post in posts:
                rule.recipients.add(post)
            
            print(f"✅ قانون اعلان ایجاد شد: {rule.get_entity_type_display()} - {rule.get_action_display()}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد قوانین اعلان نمونه: {str(e)}")
        return False

def setup_cron_examples():
    """ایجاد فایل‌های نمونه cron"""
    print("🔧 ایجاد فایل‌های نمونه cron...")
    
    try:
        project_root = get_project_root()
        scripts_dir = project_root / 'scripts'
        
        # فایل cron نمونه برای Linux/Mac
        cron_file = scripts_dir / 'cron_example.txt'
        cron_content = """# نمونه تنظیمات cron برای سیستم پشتیبان‌گیری
# این فایل را کپی کرده و در crontab قرار دهید

# هر 5 دقیقه یکبار بررسی پشتیبان‌گیری‌های زمان‌بندی شده
*/5 * * * * /path/to/python /path/to/scripts/backup_scheduler.py

# هر ساعت یکبار بررسی (کمتر منابع مصرف می‌کند)
0 * * * * /path/to/python /path/to/scripts/backup_scheduler.py

# هر روز ساعت 2 صبح
0 2 * * * /path/to/python /path/to/scripts/backup_scheduler.py

# هر یکشنبه ساعت 3 صبح
0 3 * * 0 /path/to/python /path/to/scripts/backup_scheduler.py

# اجرای اسکچول خاص
0 1 * * * /path/to/python /path/to/scripts/backup_scheduler.py --schedule-id 1

# اجرای تستی (بدون انجام عملیات)
0 0 * * * /path/to/python /path/to/scripts/backup_scheduler.py --dry-run
"""
        
        with open(cron_file, 'w', encoding='utf-8') as f:
            f.write(cron_content)
        
        print(f"✅ فایل cron نمونه ایجاد شد: {cron_file}")
        
        # فایل Windows Task Scheduler نمونه
        task_file = scripts_dir / 'windows_task_example.xml'
        task_content = r"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>اجرای خودکار پشتیبان‌گیری‌های زمان‌بندی شده</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>2024-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>PT5M</Interval>
      </Repetition>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>python</Command>
      <Arguments>scripts/backup_scheduler.py</Arguments>
      <WorkingDirectory>D:\Design & Source Code\Source Coding\BudgetsSystem</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""
        
        with open(task_file, 'w', encoding='utf-8') as f:
            f.write(task_content)
        
        print(f"✅ فایل Windows Task نمونه ایجاد شد: {task_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد فایل‌های cron نمونه: {str(e)}")
        return False

def main():
    """تابع اصلی نصب"""
    print("🚀 شروع نصب و راه‌اندازی سیستم پشتیبان‌گیری...")
    
    # تنظیم Django
    setup_django()
    
    # ایجاد پوشه logs
    ensure_logs_dir()
    
    # اجرای مراحل نصب
    steps = [
        ("ایجاد اسکچول نمونه", create_sample_schedule),
        ("ایجاد قوانین اعلان نمونه", create_sample_notification_rules),
        ("ایجاد فایل‌های cron نمونه", setup_cron_examples),
    ]
    
    results = []
    for step_name, step_func in steps:
        try:
            result = step_func()
            results.append((step_name, result))
        except Exception as e:
            print(f"❌ خطا در {step_name}: {str(e)}")
            results.append((step_name, False))
    
    # نمایش نتایج
    print("\n" + "="*50)
    print("📋 نتایج نصب:")
    print("="*50)
    
    passed = 0
    for step_name, result in results:
        status = "✅ موفق" if result else "❌ ناموفق"
        print(f"{status} - {step_name}")
        if result:
            passed += 1
    
    print("="*50)
    print(f"📊 نتیجه نهایی: {passed}/{len(results)} مرحله موفق")
    
    if passed == len(results):
        print("\n🎉 نصب با موفقیت تکمیل شد!")
        print("\n📋 مراحل بعدی:")
        print("1. وارد Admin Panel شوید: http://127.0.0.1:8000/admin/")
        print("2. به بخش 'BackupSchedule' بروید")
        print("3. اسکچول‌های پشتیبان‌گیری را تنظیم کنید")
        print("4. cron یا Windows Task Scheduler را تنظیم کنید")
        print("5. فایل‌های نمونه در پوشه scripts/ قرار دارند")
        return 0
    else:
        print("\n⚠️ برخی مراحل ناموفق بودند!")
        return 1

if __name__ == '__main__':
    sys.exit(main())
