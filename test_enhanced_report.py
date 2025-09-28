#!/usr/bin/env python
"""
تست گزارش بهبود یافته تخصیص بودجه
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from budgets.models import BudgetAllocation
from reports.views_enhanced import BudgetAllocationReportEnhancedView

def test_enhanced_report():
    """تست گزارش بهبود یافته تخصیص بودجه"""
    
    print("🧪 تست گزارش بهبود یافته تخصیص بودجه...")
    print("=" * 60)
    
    try:
        # پیدا کردن تخصیص بودجه
        budget_allocation = BudgetAllocation.objects.filter(is_active=True).first()
        if not budget_allocation:
            print("❌ هیچ تخصیص بودجه فعالی یافت نشد!")
            return
        
        print(f"✅ تخصیص بودجه پیدا شد: ID={budget_allocation.pk}")
        print(f"   سازمان: {budget_allocation.organization.name}")
        print(f"   سرفصل: {budget_allocation.budget_item.name}")
        print(f"   مبلغ: {budget_allocation.allocated_amount:,.0f}")
        
        # ایجاد درخواست تست
        factory = RequestFactory()
        request = factory.get(f'/reports/budget-allocation/{budget_allocation.pk}/report-enhanced/')
        request.META['HTTP_HOST'] = '127.0.0.1:8000'
        
        # پیدا کردن کاربر
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            print("❌ کاربر سوپروایزر پیدا نشد!")
            return
        
        request.user = user
        
        # تست view
        print("\n1️⃣ تست BudgetAllocationReportEnhancedView...")
        view = BudgetAllocationReportEnhancedView()
        view.request = request
        view.kwargs = {'pk': budget_allocation.pk}
        
        # تست get_object
        try:
            obj = view.get_object()
            view.object = obj
            print(f"   ✅ Object: {obj}")
            print(f"   سازمان: {obj.organization.name}")
            print(f"   سرفصل: {obj.budget_item.name}")
            print(f"   مبلغ: {obj.allocated_amount:,.0f}")
        except Exception as e:
            print(f"   ❌ خطا در get_object: {e}")
            return
        
        # تست get_context_data
        print("\n2️⃣ تست get_context_data...")
        try:
            context = view.get_context_data()
            print(f"   ✅ Context keys: {list(context.keys())}")
            
            # بررسی آیتم‌های خاص
            print("\n3️⃣ آیتم‌های خاص در context:")
            if 'report_title' in context:
                print(f"   📄 عنوان گزارش: {context['report_title']}")
            
            if 'allocated_amount_main' in context:
                print(f"   💰 مبلغ تخصیص: {context['allocated_amount_main']:,.0f}")
            
            if 'consumed_amount_main' in context:
                print(f"   💸 مبلغ مصرف: {context['consumed_amount_main']:,.0f}")
            
            if 'remaining_amount_main' in context:
                print(f"   💵 مانده: {context['remaining_amount_main']:,.0f}")
            
            if 'utilization_percentage_main' in context:
                print(f"   📊 درصد مصرف: {context['utilization_percentage_main']:.1f}%")
            
            if 'linked_tankhahs' in context:
                print(f"   🔗 تنخواه‌های مرتبط: {len(context['linked_tankhahs'])}")
                for tankhah in context['linked_tankhahs'][:3]:
                    print(f"      - {tankhah.number}: {tankhah.amount:,.0f}")
            
            if 'linked_transactions' in context:
                print(f"   💳 تراکنش‌های مرتبط: {len(context['linked_transactions'])}")
                for tx in context['linked_transactions'][:3]:
                    print(f"      - {tx.transaction_type}: {tx.amount:,.0f}")
            
            if 'related_budget_allocations_list' in context:
                print(f"   📊 تخصیص‌های مرتبط: {len(context['related_budget_allocations_list'])}")
                for ba in context['related_budget_allocations_list'][:3]:
                    print(f"      - {ba['budget_item_name']}: {ba['allocated_amount']:,.0f}")
            
            # بررسی تاریخ‌های فارسی جلالی
            if 'allocation_date_jalali' in context:
                print(f"   📅 تاریخ تخصیص (جلالی): {context['allocation_date_jalali']}")
            
            if 'current_date_jalali' in context:
                print(f"   📅 تاریخ فعلی (جلالی): {context['current_date_jalali']}")
            
            if 'current_time_jalali' in context:
                print(f"   🕐 زمان فعلی (جلالی): {context['current_time_jalali']}")
            
        except Exception as e:
            print(f"   ❌ خطا در get_context_data: {e}")
            import traceback
            traceback.print_exc()
            return
        
        print("\n✅ تست کامل شد!")
        print(f"\n🔗 لینک گزارش: http://127.0.0.1:8000/reports/budget-allocation/{budget_allocation.pk}/report-enhanced/")
        
    except Exception as e:
        print(f"❌ خطا در تست: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_report()

