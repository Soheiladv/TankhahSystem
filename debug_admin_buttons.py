#!/usr/bin/env python
import os
import sys
import django

# تنظیم Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.urls import reverse
from django.contrib.auth import get_user_model
from tankhah.models import Factor
from core.models import Status

User = get_user_model()

def debug_admin_buttons():
    print("=" * 80)
    print("🔍 بررسی مشکل دکمه‌های ادمین")
    print("=" * 80)
    
    # پیدا کردن کاربر ادمین
    admin_user = User.objects.filter(is_superuser=True).first()
    if admin_user:
        print(f"✅ کاربر ادمین: {admin_user.username}")
        print(f"   is_superuser: {admin_user.is_superuser}")
        print(f"   is_staff: {admin_user.is_staff}")
        print()
    else:
        print("❌ کاربر ادمین پیدا نشد")
        return
    
    # پیدا کردن فاکتور
    try:
        factor = Factor.objects.get(id=78)
        print(f"✅ فاکتور: {factor.number}")
        print(f"   وضعیت فعلی: {factor.status.name if factor.status else 'بدون وضعیت'}")
        print(f"   ID وضعیت فعلی: {factor.status.id if factor.status else 'None'}")
        print()
    except Factor.DoesNotExist:
        print("❌ فاکتور با ID 78 پیدا نشد")
        return
    
    # بررسی URL ها
    try:
        control_url = reverse('admin_workflow_control', args=['factor', 78])
        print(f"✅ URL کنترل گردش کار: {control_url}")
    except Exception as e:
        print(f"❌ خطا در URL کنترل: {e}")
    
    try:
        change_url = reverse('admin_change_status', args=['factor', 78])
        print(f"✅ URL تغییر وضعیت: {change_url}")
    except Exception as e:
        print(f"❌ خطا در URL تغییر وضعیت: {e}")
    
    print()
    
    # بررسی وضعیت‌های موجود
    print("📋 وضعیت‌های موجود:")
    statuses = Status.objects.filter(is_active=True).order_by('id')
    for status in statuses:
        print(f"   {status.id}: {status.name} (کد: {status.code})")
    print()
    
    # بررسی permissions
    print("🔐 بررسی دسترسی‌ها:")
    permissions = admin_user.get_all_permissions()
    admin_permissions = [p for p in permissions if 'admin' in p]
    for perm in admin_permissions:
        print(f"   ✅ {perm}")
    print()
    
    # بررسی اینکه آیا کاربر دسترسی دارد
    has_control = admin_user.has_perm('tankhah.admin_workflow_control')
    has_change = admin_user.has_perm('tankhah.admin_change_status')
    has_reset = admin_user.has_perm('tankhah.admin_reset_workflow')
    
    print("🎯 دسترسی‌های مورد نیاز:")
    print(f"   admin_workflow_control: {'✅' if has_control else '❌'}")
    print(f"   admin_change_status: {'✅' if has_change else '❌'}")
    print(f"   admin_reset_workflow: {'✅' if has_reset else '❌'}")
    print()
    
    # بررسی مشکل احتمالی در JavaScript
    print("🔧 بررسی مشکل احتمالی:")
    print("   1. آیا jQuery بارگذاری شده است؟")
    print("   2. آیا toastr بارگذاری شده است？")
    print("   3. آیا CSRF token درست است؟")
    print("   4. آیا URL درست است؟")
    print()
    
    # تست تغییر وضعیت
    print("🧪 تست تغییر وضعیت:")
    if factor.status:
        print(f"   وضعیت فعلی: {factor.status.name} (ID: {factor.status.id})")
        # پیدا کردن وضعیت دیگری
        other_status = Status.objects.filter(is_active=True).exclude(id=factor.status.id).first()
        if other_status:
            print(f"   وضعیت پیشنهادی برای تغییر: {other_status.name} (ID: {other_status.id})")
        else:
            print("   ❌ وضعیت دیگری برای تغییر پیدا نشد")
    else:
        print("   ❌ فاکتور وضعیت ندارد")
    
    print("=" * 80)

if __name__ == "__main__":
    debug_admin_buttons()
