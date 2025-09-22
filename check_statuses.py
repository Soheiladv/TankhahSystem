#!/usr/bin/env python
"""
بررسی وضعیت‌های موجود در سیستم
"""
import os
import sys
import django

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from core.models import Status

def check_statuses():
    print("=" * 60)
    print("بررسی وضعیت‌های موجود در سیستم")
    print("=" * 60)
    
    all_statuses = Status.objects.all()
    print(f"تعداد کل وضعیت‌ها: {all_statuses.count()}")
    
    print("\nهمه وضعیت‌ها:")
    for status in all_statuses:
        print(f"  - {status.name} ({status.code}) - اولیه: {status.is_initial} - تایید نهایی: {status.is_final_approve}")
    
    print("\nوضعیت‌های اولیه:")
    initial_statuses = Status.objects.filter(is_initial=True)
    for status in initial_statuses:
        print(f"  - {status.name} ({status.code})")
    
    print("\nوضعیت‌های تایید نهایی:")
    final_statuses = Status.objects.filter(is_final_approve=True)
    for status in final_statuses:
        print(f"  - {status.name} ({status.code})")

if __name__ == "__main__":
    check_statuses()
