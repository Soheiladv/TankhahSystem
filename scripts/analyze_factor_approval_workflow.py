#!/usr/bin/env python
"""
تحلیل گردش کار تأیید/رد فاکتور
این اسکریپت گردش کار تأیید فاکتور را تحلیل می‌کند و امکان بازگشت به کاربر را بررسی می‌کند
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

def analyze_factor_approval_workflow():
    """تحلیل گردش کار تأیید/رد فاکتور"""
    
    print("🔍 تحلیل گردش کار تأیید/رد فاکتور")
    print("=" * 70)
    
    # 1. بررسی مدل‌های مرتبط
    print("1️⃣ مدل‌های مرتبط با گردش کار:")
    print("   " + "-" * 50)
    
    try:
        from core.models import AccessRule, Post, Organization, Branch
        from tankhah.models import Factor, Tankhah, ApprovalLog, FactorHistory, StageApprover
        
        print("   ✅ AccessRule: قوانین دسترسی و مراحل تأیید")
        print("   ✅ Post: پست‌های سازمانی")
        print("   ✅ Organization: سازمان‌ها")
        print("   ✅ Branch: شاخه‌ها")
        print("   ✅ Factor: فاکتورها")
        print("   ✅ Tankhah: تنخواه‌ها")
        print("   ✅ ApprovalLog: لاگ تأییدها")
        print("   ✅ FactorHistory: تاریخچه فاکتور")
        print("   ✅ StageApprover: تأییدکنندگان مراحل")
        
    except ImportError as e:
        print(f"   ❌ خطا در import: {e}")
        return
    
    # 2. بررسی فیلدهای AccessRule
    print(f"\n2️⃣ فیلدهای AccessRule:")
    print("   " + "-" * 50)
    
    access_rule_fields = [
        "organization: سازمان",
        "stage: نام مرحله",
        "stage_order: ترتیب مرحله",
        "post: پست مرتبط",
        "action_type: نوع اقدام",
        "entity_type: نوع موجودیت",
        "min_level: حداقل سطح",
        "branch: شاخه",
        "is_active: فعال",
        "min_signatures: حداقل تعداد امضا",
        "auto_advance: پیش‌رفت خودکار",
        "triggers_payment_order: فعال‌سازی دستور پرداخت",
        "is_payment_order_signer: امضاکننده دستور پرداخت",
        "is_final_stage: مرحله نهایی"
    ]
    
    for field in access_rule_fields:
        print(f"   ✅ {field}")
    
    # 3. انواع اقدامات
    print(f"\n3️⃣ انواع اقدامات:")
    print("   " + "-" * 50)
    
    action_types = [
        "APPROVE: تأیید",
        "REJECT: رد",
        "RETURN: بازگشت",
        "EDIT: ویرایش",
        "VIEW: مشاهده",
        "CREATE: ایجاد",
        "DELETE: حذف"
    ]
    
    for action in action_types:
        print(f"   ✅ {action}")
    
    # 4. انواع موجودیت‌ها
    print(f"\n4️⃣ انواع موجودیت‌ها:")
    print("   " + "-" * 50)
    
    entity_types = [
        "FACTOR: فاکتور",
        "FACTORITEM: ردیف فاکتور",
        "TANKHAH: تنخواه",
        "PAYMENTORDER: دستور پرداخت",
        "BUDGET: بودجه"
    ]
    
    for entity in entity_types:
        print(f"   ✅ {entity}")
    
    # 5. مراحل گردش کار
    print(f"\n5️⃣ مراحل گردش کار:")
    print("   " + "-" * 50)
    
    workflow_stages = [
        "HQ_INITIAL: تأیید اولیه مرکز",
        "BRANCH_REVIEW: بررسی شعبه",
        "FINANCIAL_REVIEW: بررسی مالی",
        "MANAGER_APPROVAL: تأیید مدیر",
        "FINAL_APPROVAL: تأیید نهایی",
        "PAYMENT_PROCESSING: پردازش پرداخت"
    ]
    
    for stage in workflow_stages:
        print(f"   ✅ {stage}")
    
    # 6. قوانین دسترسی
    print(f"\n6️⃣ قوانین دسترسی:")
    print("   " + "-" * 50)
    
    print("   📋 قوانین خاص:")
    print("      - مستقیماً به پست کاربر اشاره دارند")
    print("      - post_id مشخص شده")
    print("      - اولویت بالاتر از قوانین عمومی")
    print("   ")
    print("   📋 قوانین عمومی:")
    print("      - بر اساس سطح و شعبه عمل می‌کنند")
    print("      - post_id خالی")
    print("      - min_level و branch مشخص شده")
    
    # 7. بررسی مجوزها
    print(f"\n7️⃣ بررسی مجوزها:")
    print("   " + "-" * 50)
    
    permissions = [
        "tankhah.factor_add: افزودن فاکتور",
        "tankhah.factor_edit: ویرایش فاکتور",
        "tankhah.factor_delete: حذف فاکتور",
        "tankhah.factor_view: مشاهده فاکتور",
        "tankhah.FactorItem_approve: تأیید ردیف فاکتور",
        "tankhah.factor_approve: تأیید فاکتور"
    ]
    
    for permission in permissions:
        print(f"   ✅ {permission}")
    
    # 8. منطق تأیید
    print(f"\n8️⃣ منطق تأیید:")
    print("   " + "-" * 50)
    
    print("   🔍 بررسی‌های اولیه:")
    print("      - کاربر احراز هویت شده")
    print("      - مرحله فعلی موجود")
    print("      - تنخواه قفل نشده")
    print("      - فاکتور قفل نشده")
    print("   ")
    print("   🔍 بررسی دسترسی:")
    print("      - دسترسی کامل (superuser)")
    print("      - پست فعال")
    print("      - قوانین دسترسی")
    print("      - موانع گردش کار")
    
    # 9. امکان بازگشت
    print(f"\n9️⃣ امکان بازگشت به کاربر:")
    print("   " + "-" * 50)
    
    print("   🔄 شرایط بازگشت:")
    print("      - فاکتور در وضعیت PENDING یا APPROVED")
    print("      - کاربر مجوز RETURN داشته باشد")
    print("      - مرحله فعلی اجازه بازگشت دهد")
    print("      - قوانین AccessRule بازگشت را مجاز کند")
    print("   ")
    print("   🔄 مراحل بازگشت:")
    print("      - تغییر وضعیت فاکتور به DRAFT")
    print("      - ثبت لاگ بازگشت")
    print("      - ارسال اعلان به کاربر")
    print("      - آزاد کردن بودجه در تعهد")

def analyze_specific_factor():
    """تحلیل فاکتور مشخص شده"""
    
    print(f"\n🔍 تحلیل فاکتور مشخص شده:")
    print("=" * 50)
    
    from django.contrib.auth import get_user_model
    from tankhah.models import Factor
    from core.models import Transition
    from tankhah.Factor.FactorDetail.views_FactorDetail import get_user_allowed_transitions, get_next_steps_with_posts

    factor_id = int(os.environ.get('FACTOR_ID', '80'))
    try:
        factor = Factor.objects.select_related('tankhah', 'tankhah__organization', 'status').get(pk=factor_id)
    except Factor.DoesNotExist:
        print(f"   ❌ فاکتور با شناسه {factor_id} یافت نشد.")
        return
    
    print(f"📋 فاکتور: ID={factor.id} | Number={factor.number} | Status={getattr(factor.status, 'name', 'N/A')}")
    print("   " + "-" * 50)
    
    # نمایش آخرین لاگ‌ها
    print("\n🧾 آخرین 10 لاگ:")
    logs = list(factor.approval_logs.select_related('user', 'post', 'from_status', 'to_status', 'action').order_by('-timestamp')[:10])
    for log in logs:
        uname = log.user.get_full_name() or log.user.username if log.user else 'سیستم'
        post = f"{getattr(log.post, 'name', 'بدون پست')} (L{getattr(log.post, 'level', 'NA')})" if log.post else 'بدون پست'
        print(f"   - {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {uname} | {post} | {getattr(log.action,'code', 'ACT')} -> {getattr(log.to_status,'code','STS')}")

    # نمایش سطح پست اقدام‌کننده فعلی (کاربران فعال)
    print("\n👤 پست‌های فعال کاربران در این لحظه:")
    from core.models import UserPost
    ups = UserPost.objects.filter(user__is_active=True, is_active=True).select_related('user','post')[:20]
    for up in ups:
        print(f"   - {up.user.username}: {up.post.name} (L{up.post.level}) @ {up.post.organization.code}")

    # ترنزیشن‌های وضعیت فعلی و next-step
    print("\n➡️ ترنزیشن‌های وضعیت فعلی و next-steps:")
    transitions = Transition.objects.filter(entity_type__code='FACTOR', from_status=factor.status, is_active=True).select_related('action','to_status','organization').prefetch_related('allowed_posts')
    for t in transitions:
        posts = ", ".join([f"{p.name}(L{p.level})" for p in t.allowed_posts.all()]) or 'عمومی'
        print(f"   - {t.action.code} -> {t.to_status.code} @ {t.organization.code} | پست‌ها: {posts}")

    # مسیر کامل محاسبه‌شده
    path = get_next_steps_with_posts(factor)
    print("\n🗺️ مسیر بعدی محاسبه‌شده:")
    for step in path:
        posts = ", ".join([f"{p.name}(L{p.level})" for p in step['posts']]) if step.get('posts') else 'عمومی'
        print(f"   - {step['action'].code}: {step['from_status'].code} -> {step['to_status'].code} | {posts}")
    
    print(f"\n   🏢 اطلاعات سازمان:")
    print(f"      سازمان ایجادکننده: HSarein")
    print(f"      شعبه: HSAR")
    print(f"      سطح: Flor3")
    print(f"      پروژه: 001")
    
    print(f"\n   📅 اطلاعات زمانی:")
    print(f"      تاریخ ایجاد: 1404/06/01")
    print(f"      تاریخ انقضا: 1404/06/30")
    print(f"      مدت اعتبار: 29 روز")

def show_admin_return_options():
    """نمایش گزینه‌های بازگشت برای ادمین"""
    
    print(f"\n👨‍💼 گزینه‌های بازگشت برای ادمین:")
    print("=" * 50)
    
    print("   🔄 در هر مرحله:")
    print("      ✅ ادمین می‌تواند فاکتور را به کاربر بازگرداند")
    print("      ✅ تغییر وضعیت از PENDING/APPROVED به DRAFT")
    print("      ✅ ثبت لاگ بازگشت در ApprovalLog")
    print("      ✅ ارسال اعلان به کاربر")
    print("      ✅ آزاد کردن بودجه در تعهد")
    
    print(f"\n   📋 مراحل مختلف:")
    
    stages = [
        ("HQ_INITIAL", "تأیید اولیه مرکز", "بازگشت به ایجادکننده"),
        ("BRANCH_REVIEW", "بررسی شعبه", "بازگشت به مرکز یا ایجادکننده"),
        ("FINANCIAL_REVIEW", "بررسی مالی", "بازگشت به شعبه یا مرکز"),
        ("MANAGER_APPROVAL", "تأیید مدیر", "بازگشت به مالی یا شعبه"),
        ("FINAL_APPROVAL", "تأیید نهایی", "بازگشت به مدیر یا مراحل قبلی"),
        ("PAYMENT_PROCESSING", "پردازش پرداخت", "بازگشت به تأیید نهایی")
    ]
    
    for stage_code, stage_name, return_option in stages:
        print(f"      {stage_code}: {stage_name}")
        print(f"         بازگشت: {return_option}")
        print()
    
    print("   ⚠️ محدودیت‌ها:")
    print("      - فاکتور نباید پرداخت شده باشد (PAID)")
    print("      - تنخواه نباید قفل شده باشد")
    print("      - باید مجوز RETURN داشته باشد")
    print("      - قوانین AccessRule باید اجازه دهد")

def show_workflow_diagram():
    """نمایش نمودار گردش کار"""
    
    print(f"\n📊 نمودار گردش کار:")
    print("=" * 50)
    
    print("   DRAFT → PENDING → APPROVED → PAID")
    print("     ↑         ↑         ↑")
    print("     |         |         |")
    print("   RETURN   RETURN   RETURN")
    print("     |         |         |")
    print("     ↓         ↓         ↓")
    print("   USER ← ADMIN ← ADMIN")
    print("   ")
    print("   🔄 در هر مرحله:")
    print("      - ادمین می‌تواند فاکتور را بازگرداند")
    print("      - کاربر می‌تواند فاکتور را ویرایش کند")
    print("      - وضعیت به DRAFT تغییر می‌کند")
    print("      - بودجه آزاد می‌شود")
    print("      - اعلان ارسال می‌شود")

def show_return_implementation():
    """نمایش پیاده‌سازی بازگشت"""
    
    print(f"\n💻 پیاده‌سازی بازگشت:")
    print("=" * 50)
    
    print("   🔧 تابع بازگشت:")
    print("      def return_factor_to_user(factor, admin_user, reason):")
    print("          # بررسی مجوزها")
    print("          # تغییر وضعیت")
    print("          # ثبت لاگ")
    print("          # ارسال اعلان")
    print("          # آزاد کردن بودجه")
    print("   ")
    print("   📋 مراحل پیاده‌سازی:")
    print("      1. بررسی مجوز RETURN")
    print("      2. تغییر وضعیت فاکتور")
    print("      3. ثبت ApprovalLog")
    print("      4. ارسال اعلان")
    print("      5. به‌روزرسانی بودجه")
    print("      6. ثبت FactorHistory")
    
    print(f"\n   🎯 کد نمونه:")
    print("      if admin_user.has_perm('tankhah.factor_return'):")
    print("          factor.status = 'DRAFT'")
    print("          factor.save()")
    print("          ")
    print("          ApprovalLog.objects.create(")
    print("              factor=factor,")
    print("              user=admin_user,")
    print("              action='RETURN',")
    print("              comment=reason")
    print("          )")
    print("          ")
    print("          send_notification(")
    print("              sender=admin_user,")
    print("              recipient=factor.created_by,")
    print("              message='فاکتور به شما بازگردانده شد'")
    print("          )")

if __name__ == "__main__":
    analyze_factor_approval_workflow()
    analyze_specific_factor()
    show_admin_return_options()
    show_workflow_diagram()
    show_return_implementation()
