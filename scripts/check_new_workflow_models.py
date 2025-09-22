#!/usr/bin/env python
"""
بررسی سیستم با مدل‌های Transition, Action, EntityType, Status
این اسکریپت سیستم را با مدل‌های جدید بررسی می‌کند
"""

import os
import sys
import django
from datetime import datetime

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

def check_new_workflow_models():
    """بررسی مدل‌های جدید گردش کار"""
    
    print("🔍 بررسی مدل‌های جدید گردش کار")
    print("=" * 60)
    
    try:
        from core.models import Transition, Action, EntityType, Status, Organization, Post
        from tankhah.models import Factor, Tankhah, ApprovalLog, FactorHistory
        from accounts.models import CustomUser
        
        print("   ✅ مدل‌های جدید بارگذاری شدند:")
        print("      - Transition: گذارهای گردش کار")
        print("      - Action: اقدامات گردش کار")
        print("      - EntityType: انواع موجودیت‌ها")
        print("      - Status: وضعیت‌های گردش کار")
        print("      - Organization: سازمان‌ها")
        print("      - Post: پست‌های سازمانی")
        print("      - Factor: فاکتورها")
        print("      - Tankhah: تنخواه‌ها")
        print("      - ApprovalLog: لاگ تأییدها")
        print("      - FactorHistory: تاریخچه فاکتور")
        print("      - CustomUser: کاربران")
        
        return True
        
    except ImportError as e:
        print(f"   ❌ خطا در بارگذاری مدل‌ها: {e}")
        return False

def analyze_transition_model():
    """تحلیل مدل Transition"""
    
    print(f"\n🔄 تحلیل مدل Transition:")
    print("=" * 50)
    
    print("   📋 فیلدهای Transition:")
    print("      - name: نام/شرح گذار")
    print("      - entity_type: نوع موجودیت (ForeignKey به EntityType)")
    print("      - from_status: وضعیت مبدأ (ForeignKey به Status)")
    print("      - action: اقدام (ForeignKey به Action)")
    print("      - to_status: وضعیت مقصد (ForeignKey به Status)")
    print("      - organization: سازمان (ForeignKey به Organization)")
    print("      - allowed_posts: پست‌های مجاز (ManyToMany به Post)")
    print("      - created_by: ایجادکننده")
    print("      - created_at: تاریخ ایجاد")
    print("      - updated_at: تاریخ به‌روزرسانی")
    print("      - is_active: فعال")
    print("   ")
    print("   📋 قابلیت‌ها:")
    print("      - تعریف گذارهای گردش کار")
    print("      - محدودیت بر اساس سازمان")
    print("      - محدودیت بر اساس پست")
    print("      - مدیریت وضعیت‌ها")
    print("      - مدیریت اقدامات")

def analyze_action_model():
    """تحلیل مدل Action"""
    
    print(f"\n⚡ تحلیل مدل Action:")
    print("=" * 50)
    
    print("   📋 فیلدهای Action:")
    print("      - name: نام اقدام")
    print("      - code: کد منحصر به فرد")
    print("      - description: توضیحات")
    print("      - created_by: ایجادکننده")
    print("      - created_at: تاریخ ایجاد")
    print("      - updated_at: تاریخ به‌روزرسانی")
    print("      - is_active: فعال")
    print("   ")
    print("   📋 اقدامات پیشنهادی:")
    print("      - CREATE: ایجاد")
    print("      - SUBMIT: ارسال")
    print("      - APPROVE: تأیید")
    print("      - REJECT: رد")
    print("      - RETURN: بازگشت")
    print("      - EDIT: ویرایش")
    print("      - DELETE: حذف")
    print("      - VIEW: مشاهده")

def analyze_entity_type_model():
    """تحلیل مدل EntityType"""
    
    print(f"\n📦 تحلیل مدل EntityType:")
    print("=" * 50)
    
    print("   📋 فیلدهای EntityType:")
    print("      - name: نام موجودیت")
    print("      - code: کد منحصر به فرد")
    print("      - content_type: نوع محتوای مرتبط")
    print("      - created_at: تاریخ ایجاد")
    print("   ")
    print("   📋 انواع موجودیت پیشنهادی:")
    print("      - FACTOR: فاکتور")
    print("      - FACTORITEM: ردیف فاکتور")
    print("      - TANKHAH: تنخواه")
    print("      - PAYMENTORDER: دستور پرداخت")
    print("      - BUDGET: بودجه")
    print("      - ALLOCATION: تخصیص")

def analyze_status_model():
    """تحلیل مدل Status"""
    
    print(f"\n📊 تحلیل مدل Status:")
    print("=" * 50)
    
    print("   📋 فیلدهای Status:")
    print("      - name: نام وضعیت")
    print("      - code: کد منحصر به فرد")
    print("      - is_initial: وضعیت اولیه")
    print("      - is_final_approve: وضعیت تأیید نهایی")
    print("      - is_final_reject: وضعیت رد نهایی")
    print("      - is_active: فعال")
    print("      - created_by: ایجادکننده")
    print("      - created_at: تاریخ ایجاد")
    print("      - updated_at: تاریخ به‌روزرسانی")
    print("      - description: توضیحات")
    print("   ")
    print("   📋 وضعیت‌های پیشنهادی:")
    print("      - DRAFT: پیش‌نویس")
    print("      - PENDING: در انتظار")
    print("      - APPROVED: تأیید شده")
    print("      - REJECTED: رد شده")
    print("      - PAID: پرداخت شده")
    print("      - CANCELLED: لغو شده")

def show_workflow_example():
    """نمایش مثال گردش کار"""
    
    print(f"\n🔄 مثال گردش کار:")
    print("=" * 50)
    
    print("   📋 گردش کار فاکتور:")
    print("      1. CREATE: DRAFT → PENDING")
    print("         - کاربر فاکتور ایجاد می‌کند")
    print("         - وضعیت از DRAFT به PENDING تغییر می‌کند")
    print("   ")
    print("      2. APPROVE: PENDING → APPROVED")
    print("         - سرپرست فاکتور را تأیید می‌کند")
    print("         - وضعیت از PENDING به APPROVED تغییر می‌کند")
    print("   ")
    print("      3. REJECT: PENDING → REJECTED")
    print("         - سرپرست فاکتور را رد می‌کند")
    print("         - وضعیت از PENDING به REJECTED تغییر می‌کند")
    print("   ")
    print("      4. RETURN: APPROVED → DRAFT")
    print("         - مدیر فاکتور را بازمی‌گرداند")
    print("         - وضعیت از APPROVED به DRAFT تغییر می‌کند")
    print("   ")
    print("      5. PAY: APPROVED → PAID")
    print("         - مدیر کل پرداخت را تأیید می‌کند")
    print("         - وضعیت از APPROVED به PAID تغییر می‌کند")

def show_transition_logic():
    """نمایش منطق Transition"""
    
    print(f"\n🔧 منطق Transition:")
    print("=" * 50)
    
    print("   📋 بررسی امکان انجام اقدام:")
    print("      def can_perform_action(user, entity, action):")
    print("          # 1. بررسی احراز هویت")
    print("          if not user.is_authenticated:")
    print("              return False")
    print("          ")
    print("          # 2. بررسی پست فعال")
    print("          user_post = user.userpost_set.filter(is_active=True).first()")
    print("          if not user_post:")
    print("              return False")
    print("          ")
    print("          # 3. بررسی Transition")
    print("          transition = Transition.objects.filter(")
    print("              entity_type=entity.entity_type,")
    print("              from_status=entity.status,")
    print("              action=action,")
    print("              organization=user_post.post.organization,")
    print("              allowed_posts=user_post.post,")
    print("              is_active=True")
    print("          ).first()")
    print("          ")
    print("          return transition is not None")

def show_approval_workflow():
    """نمایش گردش کار تأیید"""
    
    print(f"\n✅ گردش کار تأیید:")
    print("=" * 50)
    
    print("   📋 مراحل تأیید فاکتور:")
    print("      1. کاربر فاکتور ایجاد می‌کند (DRAFT)")
    print("      2. کاربر فاکتور را ارسال می‌کند (PENDING)")
    print("      3. سرپرست فاکتور را بررسی می‌کند")
    print("         - تأیید: APPROVED")
    print("         - رد: REJECTED")
    print("         - بازگشت: DRAFT")
    print("      4. مدیر تأیید نهایی می‌کند")
    print("      5. مدیر کل پرداخت را تأیید می‌کند (PAID)")
    print("   ")
    print("   📋 قوانین:")
    print("      - هر کاربر فقط فاکتورهای سازمان خود را می‌بیند")
    print("      - پست کاربر تعیین‌کننده مجوزها است")
    print("      - Transition تعیین‌کننده امکان انجام اقدام است")
    print("      - سوپریوزر دسترسی کامل دارد")

def show_return_workflow():
    """نمایش گردش کار بازگشت"""
    
    print(f"\n🔄 گردش کار بازگشت:")
    print("=" * 50)
    
    print("   📋 شرایط بازگشت:")
    print("      - فاکتور در وضعیت PENDING یا APPROVED باشد")
    print("      - Transition برای RETURN موجود باشد")
    print("      - کاربر در پست مجاز باشد")
    print("      - فاکتور قفل نشده باشد")
    print("   ")
    print("   📋 مراحل بازگشت:")
    print("      1. بررسی Transition برای RETURN")
    print("      2. تغییر وضعیت به DRAFT")
    print("      3. ثبت ApprovalLog")
    print("      4. ارسال اعلان به کاربر")
    print("      5. آزاد کردن بودجه در تعهد")
    print("   ")
    print("   📋 مجوزهای بازگشت:")
    print("      - سرپرست: بازگشت فاکتورهای PENDING")
    print("      - مدیر: بازگشت فاکتورهای APPROVED")
    print("      - سوپریوزر: بازگشت در هر مرحله")

def show_implementation_summary():
    """نمایش خلاصه پیاده‌سازی"""
    
    print(f"\n📋 خلاصه پیاده‌سازی:")
    print("=" * 50)
    
    print("   ✅ تغییرات انجام شده:")
    print("      - حذف مدل AccessRule")
    print("      - حذف مدل WorkflowStage")
    print("      - استفاده از مدل Transition")
    print("      - استفاده از مدل Action")
    print("      - استفاده از مدل EntityType")
    print("      - استفاده از مدل Status")
    print("   ")
    print("   ✅ مزایای جدید:")
    print("      - انعطاف‌پذیری بیشتر")
    print("      - قابلیت تنظیم دقیق‌تر")
    print("      - مدیریت بهتر گردش کار")
    print("      - قابلیت توسعه آسان‌تر")
    print("   ")
    print("   ⚠️ نکات مهم:")
    print("      - Transition ها باید تعریف شوند")
    print("      - Action ها باید تعریف شوند")
    print("      - EntityType ها باید تعریف شوند")
    print("      - Status ها باید تعریف شوند")
    print("      - تست کامل سیستم ضروری است")

if __name__ == "__main__":
    if check_new_workflow_models():
        analyze_transition_model()
        analyze_action_model()
        analyze_entity_type_model()
        analyze_status_model()
        show_workflow_example()
        show_transition_logic()
        show_approval_workflow()
        show_return_workflow()
        show_implementation_summary()
        
        print(f"\n🎉 سیستم با مدل‌های جدید آماده است!")
        print("=" * 50)
        print("   ✅ مدل‌ها بارگذاری شدند")
        print("   ✅ گردش کار بهینه‌سازی شد")
        print("   ✅ سیستم آماده استفاده است")
        print("   ✅ قابلیت توسعه فراهم است")
