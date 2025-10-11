#!/usr/bin/env python
"""
بررسی کامل New_FactorCreateView
این اسکریپت تمام جنبه‌های New_FactorCreateView را بررسی می‌کند
"""

import os
import sys
import django
from datetime import datetime

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from django.utils.translation import activate

User = get_user_model()

def analyze_new_factor_create_view():
    """بررسی کامل New_FactorCreateView"""
    
    print("🔍 بررسی کامل New_FactorCreateView")
    print("=" * 60)
    
    # 1. بررسی import ها
    print("1️⃣ بررسی import ها:")
    print("   " + "-" * 40)
    
    try:
        from tankhah.Factor.NF.view_Nfactor import New_FactorCreateView
        print("   ✅ New_FactorCreateView import شد")
        
        from tankhah.Factor.NF.form_Nfactor import FactorForm, FactorItemForm, FactorDocumentForm
        print("   ✅ فرم‌ها import شدند")
        
        from tankhah.models import Factor, Tankhah, FactorItem, FactorDocument
        print("   ✅ مدل‌ها import شدند")
        
        from core.models import AccessRule, Post, Status, Transition, Project, Organization
        print("   ✅ مدل‌های core import شدند")
        
        from notificationApp.utils import send_notification
        print("   ✅ notification utils import شد")
        
    except ImportError as e:
        print(f"   ❌ خطا در import: {e}")
        return
    
    # 2. بررسی کلاس و ویژگی‌ها
    print(f"\n2️⃣ بررسی کلاس و ویژگی‌ها:")
    print("   " + "-" * 40)
    
    print(f"   مدل: {New_FactorCreateView.model}")
    print(f"   فرم: {New_FactorCreateView.form_class}")
    print(f"   تمپلیت: {New_FactorCreateView.template_name}")
    print(f"   مجوزها: {New_FactorCreateView.permission_codename}")
    print(f"   بررسی سازمان: {New_FactorCreateView.check_organization}")
    
    # 3. بررسی متدها
    print(f"\n3️⃣ بررسی متدها:")
    print("   " + "-" * 40)
    
    methods = [
        'get_success_url',
        'get_form_kwargs', 
        'get_context_data',
        'form_valid',
        'form_invalid'
    ]
    
    for method in methods:
        if hasattr(New_FactorCreateView, method):
            print(f"   ✅ {method}: موجود")
        else:
            print(f"   ❌ {method}: موجود نیست")
    
    # 4. بررسی URL
    print(f"\n4️⃣ بررسی URL:")
    print("   " + "-" * 40)
    
    try:
        url = reverse('Nfactor_create')
        print(f"   ✅ URL: {url}")
    except Exception as e:
        print(f"   ❌ خطا در URL: {e}")
    
    # 5. بررسی تمپلیت
    print(f"\n5️⃣ بررسی تمپلیت:")
    print("   " + "-" * 40)
    
    template_path = New_FactorCreateView.template_name
    template_full_path = os.path.join('templates', template_path)
    
    if os.path.exists(template_full_path):
        print(f"   ✅ تمپلیت موجود: {template_full_path}")
        
        # بررسی محتوای تمپلیت
        with open(template_full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        required_elements = [
            'form',
            'formset',
            'document_form',
            'calculation-summary',
            'tankhah-budget-info'
        ]
        
        for element in required_elements:
            if element in content:
                print(f"   ✅ {element}: موجود")
            else:
                print(f"   ❌ {element}: موجود نیست")
    else:
        print(f"   ❌ تمپلیت یافت نشد: {template_full_path}")
    
    # 6. بررسی فرم‌ها
    print(f"\n6️⃣ بررسی فرم‌ها:")
    print("   " + "-" * 40)
    
    try:
        # بررسی FactorForm
        factor_form_fields = FactorForm().fields.keys()
        print(f"   FactorForm فیلدها: {list(factor_form_fields)}")
        
        # بررسی FactorItemForm
        factor_item_form_fields = FactorItemForm().fields.keys()
        print(f"   FactorItemForm فیلدها: {list(factor_item_form_fields)}")
        
        # بررسی FactorDocumentForm
        factor_doc_form_fields = FactorDocumentForm().fields.keys()
        print(f"   FactorDocumentForm فیلدها: {list(factor_doc_form_fields)}")
        
    except Exception as e:
        print(f"   ❌ خطا در بررسی فرم‌ها: {e}")
    
    # 7. بررسی مدل‌ها
    print(f"\n7️⃣ بررسی مدل‌ها:")
    print("   " + "-" * 40)
    
    try:
        # بررسی فیلدهای Factor
        factor_fields = [f.name for f in Factor._meta.fields]
        print(f"   Factor فیلدها: {factor_fields}")
        
        # بررسی فیلدهای FactorItem
        factor_item_fields = [f.name for f in FactorItem._meta.fields]
        print(f"   FactorItem فیلدها: {factor_item_fields}")
        
        # بررسی فیلدهای FactorDocument
        factor_doc_fields = [f.name for f in FactorDocument._meta.fields]
        print(f"   FactorDocument فیلدها: {factor_doc_fields}")
        
    except Exception as e:
        print(f"   ❌ خطا در بررسی مدل‌ها: {e}")
    
    # 8. بررسی مجوزها
    print(f"\n8️⃣ بررسی مجوزها:")
    print("   " + "-" * 40)
    
    required_permissions = ['tankhah.factor_add']
    for permission in required_permissions:
        print(f"   مجوز مورد نیاز: {permission}")
    
    # 9. بررسی workflow
    print(f"\n9️⃣ بررسی workflow:")
    print("   " + "-" * 40)
    
    try:
        # بررسی Status
        draft_status = Status.objects.filter(code='DRAFT', is_initial=True).first()
        if draft_status:
            print(f"   ✅ وضعیت DRAFT موجود: {draft_status}")
        else:
            print(f"   ❌ وضعیت DRAFT یافت نشد")
        
        # بررسی AccessRule
        access_rules_count = AccessRule.objects.filter(entity_type='FACTORITEM').count()
        print(f"   تعداد AccessRule برای FACTORITEM: {access_rules_count}")
        
    except Exception as e:
        print(f"   ❌ خطا در بررسی workflow: {e}")
    
    # 10. بررسی اعلان‌ها
    print(f"\n🔟 بررسی اعلان‌ها:")
    print("   " + "-" * 40)
    
    try:
        from notificationApp.models import NotificationRule
        notification_rules = NotificationRule.objects.filter(entity_type='FACTOR').count()
        print(f"   تعداد NotificationRule برای FACTOR: {notification_rules}")
        
        if notification_rules > 0:
            print("   ✅ اعلان‌ها برای فاکتور تنظیم شده")
        else:
            print("   ⚠️ اعلان‌ها برای فاکتور تنظیم نشده")
            
    except Exception as e:
        print(f"   ❌ خطا در بررسی اعلان‌ها: {e}")

def test_view_functionality():
    """تست عملکرد view"""
    
    print(f"\n🧪 تست عملکرد view:")
    print("=" * 30)
    
    try:
        from tankhah.Factor.NF.view_Nfactor import New_FactorCreateView
        from django.test import RequestFactory
        
        factory = RequestFactory()
        
        # ایجاد request ساختگی
        request = factory.get('/factor/create/new/')
        
        # ایجاد view instance
        view = New_FactorCreateView()
        view.request = request
        
        # تست get_success_url
        success_url = view.get_success_url()
        print(f"   Success URL: {success_url}")
        
        # تست get_context_data
        context = view.get_context_data()
        print(f"   Context keys: {list(context.keys())}")
        
        print("   ✅ تست عملکرد موفق")
        
    except Exception as e:
        print(f"   ❌ خطا در تست عملکرد: {e}")

def show_recommendations():
    """نمایش توصیه‌ها"""
    
    print(f"\n💡 توصیه‌ها:")
    print("=" * 30)
    
    print("✅ نقاط قوت:")
    print("   - ساختار کامل و منظم")
    print("   - بررسی مجوزها")
    print("   - مدیریت تراکنش‌ها")
    print("   - اعلان‌ها")
    print("   - لاگ‌گیری")
    
    print(f"\n⚠️ نکات قابل بهبود:")
    print("   - بررسی error handling")
    print("   - بهینه‌سازی query ها")
    print("   - تست‌های unit")
    print("   - مستندسازی")
    
    print(f"\n🔧 پیشنهادات:")
    print("   - اضافه کردن cache برای بودجه")
    print("   - بهبود validation")
    print("   - اضافه کردن تست‌های بیشتر")

if __name__ == "__main__":
    analyze_new_factor_create_view()
    test_view_functionality()
    show_recommendations()
