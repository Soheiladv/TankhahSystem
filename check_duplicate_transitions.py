#!/usr/bin/env python
"""
اسکریپت برای بررسی ترنزیشن‌های تکراری در دیتابیس
"""
import os
import sys
import django

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from core.models import Transition, Action, Status, Organization
from django.db.models import Count

def check_duplicate_transitions():
    """بررسی ترنزیشن‌های تکراری"""
    print("=== بررسی ترنزیشن‌های تکراری ===")
    
    # ترنزیشن‌های تکراری بر اساس action و from_status
    duplicates = Transition.objects.filter(
        is_active=True, 
        entity_type__code='FACTOR'
    ).values(
        'organization', 'from_status', 'action'
    ).annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    print(f"تعداد ترنزیشن‌های تکراری: {duplicates.count()}")
    
    for dup in duplicates:
        org = Organization.objects.get(id=dup['organization'])
        status = Status.objects.get(id=dup['from_status'])
        action = Action.objects.get(id=dup['action'])
        
        print(f"\nترنزیشن تکراری:")
        print(f"  سازمان: {org.name}")
        print(f"  وضعیت: {status.name}")
        print(f"  اقدام: {action.name}")
        print(f"  تعداد: {dup['count']}")
        
        # نمایش جزئیات ترنزیشن‌های تکراری
        transitions = Transition.objects.filter(
            organization=org,
            from_status=status,
            action=action,
            is_active=True
        )
        
        for i, t in enumerate(transitions, 1):
            posts = list(t.allowed_posts.all())
            print(f"    {i}. ID: {t.id}, نام: {t.name}")
            print(f"       پست‌های مجاز: {[p.name for p in posts]}")
            print(f"       وضعیت مقصد: {t.to_status.name}")

def check_specific_actions():
    """بررسی اقدامات خاص (تایید و رد)"""
    print("\n=== بررسی اقدامات تایید و رد ===")
    
    approve_actions = Action.objects.filter(name__icontains='تایید')
    reject_actions = Action.objects.filter(name__icontains='رد')
    
    print(f"اقدامات تایید: {[a.name for a in approve_actions]}")
    print(f"اقدامات رد: {[a.name for a in reject_actions]}")
    
    for action in approve_actions:
        transitions = Transition.objects.filter(
            action=action,
            entity_type__code='FACTOR',
            is_active=True
        )
        print(f"\nترنزیشن‌های '{action.name}':")
        for t in transitions:
            print(f"  - {t.name} (سازمان: {t.organization.name}, وضعیت: {t.from_status.name})")

if __name__ == "__main__":
    check_duplicate_transitions()
    check_specific_actions()
