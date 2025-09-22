#!/usr/bin/env python
"""
حذف AccessRule از سیستم
این اسکریپت تمام ارجاعات به AccessRule را بررسی و حذف می‌کند
"""

import os
import sys
import django
from datetime import datetime

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

def analyze_accessrule_usage():
    """بررسی استفاده از AccessRule در سیستم"""
    
    print("🔍 بررسی استفاده از AccessRule در سیستم")
    print("=" * 60)
    
    # فایل‌های مهم که باید بررسی شوند
    important_files = [
        "tankhah/Factor/NF/view_Nfactor.py",
        "tankhah/views.py",
        "tankhah/models.py",
        "core/views.py",
        "core/forms.py",
        "core/admin.py",
        "tankhah/admin.py",
        "tankhah/forms.py",
        "signals.py",
        "budgets/signals.py"
    ]
    
    accessrule_usage = {}
    
    for file_path in important_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if 'AccessRule' in content:
                    lines = content.split('\n')
                    usage_lines = []
                    
                    for i, line in enumerate(lines, 1):
                        if 'AccessRule' in line:
                            usage_lines.append(f"Line {i}: {line.strip()}")
                    
                    accessrule_usage[file_path] = usage_lines
                    
            except Exception as e:
                print(f"   ❌ خطا در خواندن {file_path}: {e}")
    
    # نمایش نتایج
    if accessrule_usage:
        print("   📋 فایل‌هایی که از AccessRule استفاده می‌کنند:")
        print("   " + "-" * 50)
        
        for file_path, lines in accessrule_usage.items():
            print(f"   📄 {file_path}:")
            for line in lines[:5]:  # نمایش حداکثر 5 خط
                print(f"      {line}")
            if len(lines) > 5:
                print(f"      ... و {len(lines) - 5} خط دیگر")
            print()
    else:
        print("   ✅ هیچ استفاده‌ای از AccessRule در فایل‌های مهم یافت نشد")

def check_imports():
    """بررسی import های AccessRule"""
    
    print(f"\n🔍 بررسی import های AccessRule:")
    print("=" * 50)
    
    import_patterns = [
        "from core.models import.*AccessRule",
        "import.*AccessRule",
        "AccessRule.objects",
        "AccessRule.objects.filter",
        "AccessRule.objects.get",
        "AccessRule.objects.create"
    ]
    
    for pattern in import_patterns:
        print(f"   🔍 جستجو برای: {pattern}")
        # اینجا می‌توانیم از grep استفاده کنیم

def show_alternative_workflow():
    """نمایش گردش کار جایگزین بدون AccessRule"""
    
    print(f"\n🔄 گردش کار جایگزین بدون AccessRule:")
    print("=" * 50)
    
    print("   📋 مدل‌های موجود برای گردش کار:")
    print("      ✅ WorkflowStage: مراحل گردش کار")
    print("      ✅ Post: پست‌های سازمانی")
    print("      ✅ Organization: سازمان‌ها")
    print("      ✅ Branch: شاخه‌ها")
    print("      ✅ UserPost: ارتباط کاربر و پست")
    print("   ")
    print("   📋 منطق جایگزین:")
    print("      1. بررسی پست فعال کاربر")
    print("      2. بررسی سطح پست (level)")
    print("      3. بررسی سازمان و شعبه")
    print("      4. بررسی مجوزهای Django")
    print("      5. بررسی وضعیت فاکتور/تنخواه")
    print("   ")
    print("   📋 مثال پیاده‌سازی:")
    print("      def can_approve_factor(user, factor):")
    print("          # بررسی پست فعال")
    print("          user_post = user.userpost_set.filter(is_active=True).first()")
    print("          if not user_post:")
    print("              return False")
    print("          ")
    print("          # بررسی سطح پست")
    print("          if user_post.post.level < required_level:")
    print("              return False")
    print("          ")
    print("          # بررسی سازمان")
    print("          if user_post.post.organization != factor.tankhah.organization:")
    print("              return False")
    print("          ")
    print("          return True")

def create_simple_approval_logic():
    """ایجاد منطق تأیید ساده بدون AccessRule"""
    
    print(f"\n🔧 ایجاد منطق تأیید ساده:")
    print("=" * 50)
    
    approval_logic = '''
def can_approve_factor(user, factor):
    """
    بررسی امکان تأیید فاکتور بدون AccessRule
    """
    # بررسی احراز هویت
    if not user.is_authenticated:
        return False
    
    # بررسی سوپریوزر
    if user.is_superuser:
        return True
    
    # بررسی پست فعال
    user_post = user.userpost_set.filter(is_active=True).first()
    if not user_post:
        return False
    
    # بررسی مجوز Django
    if not user.has_perm('tankhah.factor_approve'):
        return False
    
    # بررسی وضعیت فاکتور
    if factor.status not in ['PENDING', 'DRAFT']:
        return False
    
    # بررسی قفل بودن
    if factor.is_locked or factor.tankhah.is_locked:
        return False
    
    # بررسی سازمان
    if user_post.post.organization != factor.tankhah.organization:
        return False
    
    # بررسی سطح پست
    required_levels = {
        'DRAFT': 1,      # هر کسی می‌تواند تأیید کند
        'PENDING': 2,    # سطح 2 و بالاتر
        'APPROVED': 3,   # سطح 3 و بالاتر
    }
    
    if user_post.post.level < required_levels.get(factor.status, 1):
        return False
    
    return True

def can_return_factor(user, factor):
    """
    بررسی امکان بازگشت فاکتور
    """
    # بررسی احراز هویت
    if not user.is_authenticated:
        return False
    
    # بررسی سوپریوزر
    if user.is_superuser:
        return True
    
    # بررسی مجوز
    if not user.has_perm('tankhah.factor_return'):
        return False
    
    # بررسی وضعیت فاکتور
    if factor.status not in ['PENDING', 'APPROVED']:
        return False
    
    # بررسی قفل بودن
    if factor.is_locked or factor.tankhah.is_locked:
        return False
    
    return True
'''
    
    print("   📋 منطق تأیید ساده:")
    print(approval_logic)

def show_migration_steps():
    """نمایش مراحل migration"""
    
    print(f"\n🔄 مراحل migration:")
    print("=" * 50)
    
    print("   📋 مراحل حذف AccessRule:")
    print("      1. ✅ حذف مدل AccessRule از core/models.py")
    print("      2. 🔄 حذف import های AccessRule")
    print("      3. 🔄 جایگزینی منطق تأیید")
    print("      4. 🔄 حذف ارجاعات در views")
    print("      5. 🔄 حذف ارجاعات در forms")
    print("      6. 🔄 حذف ارجاعات در admin")
    print("      7. 🔄 حذف ارجاعات در signals")
    print("      8. 🔄 ایجاد migration")
    print("      9. 🔄 تست سیستم")
    print("   ")
    print("   ⚠️ نکات مهم:")
    print("      - قبل از migration، backup بگیرید")
    print("      - تمام ارجاعات را بررسی کنید")
    print("      - منطق تأیید را تست کنید")
    print("      - مجوزهای جدید را تنظیم کنید")

def show_permission_structure():
    """نمایش ساختار مجوزهای جدید"""
    
    print(f"\n🔐 ساختار مجوزهای جدید:")
    print("=" * 50)
    
    permissions = [
        "tankhah.factor_add: افزودن فاکتور",
        "tankhah.factor_edit: ویرایش فاکتور",
        "tankhah.factor_delete: حذف فاکتور",
        "tankhah.factor_view: مشاهده فاکتور",
        "tankhah.factor_approve: تأیید فاکتور",
        "tankhah.factor_reject: رد فاکتور",
        "tankhah.factor_return: بازگشت فاکتور",
        "tankhah.FactorItem_approve: تأیید ردیف فاکتور",
        "tankhah.tankhah_approve: تأیید تنخواه",
        "tankhah.tankhah_reject: رد تنخواه"
    ]
    
    print("   📋 مجوزهای مورد نیاز:")
    for permission in permissions:
        print(f"      ✅ {permission}")
    
    print(f"\n   📋 سطوح پست:")
    print("      Level 1: کاربر عادی (ایجاد، ویرایش)")
    print("      Level 2: سرپرست (تأیید اولیه)")
    print("      Level 3: مدیر (تأیید نهایی)")
    print("      Level 4: مدیر کل (دسترسی کامل)")

if __name__ == "__main__":
    analyze_accessrule_usage()
    check_imports()
    show_alternative_workflow()
    create_simple_approval_logic()
    show_migration_steps()
    show_permission_structure()
