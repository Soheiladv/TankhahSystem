"""
کلاس‌های کمکی برای مدیریت پویای سیستم و حذف هاردکدها
"""
from core.models import DynamicConfiguration, Status, Action


class DynamicSystemManager:
    """
    مدیریت پویای سیستم برای حذف کامل هاردکدها
    """
    
    @staticmethod
    def get_entity_type_names():
        """دریافت نام‌های انواع موجودیت‌ها"""
        return DynamicConfiguration.get_value(
            'entity_type_names', 
            'فاکتور,تنخواه,دستور پرداخت,تخصیص بودجه',
            'entity_types'
        ).split(',')
    
    @staticmethod
    def get_action_names():
        """دریافت نام‌های اقدامات"""
        return DynamicConfiguration.get_value(
            'action_names',
            'تأیید,رد,تغییر,ارسال,بازگشت',
            'actions'
        ).split(',')
    
    @staticmethod
    def get_status_type_names():
        """دریافت نام‌های انواع وضعیت‌ها"""
        return DynamicConfiguration.get_value(
            'status_type_names',
            'is_initial,is_final_approve,is_final_reject,is_pending,is_paid,is_rejected',
            'status_types'
        ).split(',')
    
    @staticmethod
    def find_status_by_entity_and_type(entity_type, status_type):
        """پیدا کردن وضعیت بر اساس نوع موجودیت و نوع وضعیت"""
        # ابتدا سعی کن بر اساس entity_type و status_type پیدا کن
        status = Status.objects.filter(
            entity_type=entity_type,
            **{status_type: True}
        ).first()
        
        if not status:
            # اگر پیدا نشد، فقط بر اساس status_type جستجو کن
            status = Status.objects.filter(**{status_type: True}).first()
        
        if not status:
            # اگر هنوز پیدا نشد، بر اساس entity_type جستجو کن
            status = Status.objects.filter(
                entity_type=entity_type,
                is_active=True
            ).first()
        
        if not status:
            # اگر هنوز پیدا نشد، اولین وضعیت موجود را استفاده کن
            status = Status.objects.filter(is_active=True).first()
        
        return status
    
    @staticmethod
    def find_action_by_type(action_type):
        """پیدا کردن Action بر اساس نوع"""
        # ابتدا سعی کن بر اساس نام جستجو کن
        action = Action.objects.filter(
            is_active=True,
            name__icontains=action_type
        ).first()
        
        if not action:
            # اگر پیدا نشد، بر اساس کد جستجو کن
            action = Action.objects.filter(
                is_active=True,
                code__icontains=action_type
            ).first()
        
        if not action:
            # اگر هنوز پیدا نشد، اولین Action موجود را استفاده کن
            action = Action.objects.filter(is_active=True).first()
        
        return action
    
    @staticmethod
    def get_entity_type_for_factor():
        """دریافت نوع موجودیت برای فاکتور"""
        return DynamicConfiguration.get_value('factor_entity_type', 'فاکتور')
    
    @staticmethod
    def get_entity_type_for_payment_order():
        """دریافت نوع موجودیت برای دستور پرداخت"""
        return DynamicConfiguration.get_value('payment_order_entity_type', 'دستور پرداخت')
    
    @staticmethod
    def get_action_for_approve():
        """دریافت Action برای تأیید"""
        return DynamicConfiguration.get_value('approve_action', 'تأیید')
    
    @staticmethod
    def get_action_for_reject():
        """دریافت Action برای رد"""
        return DynamicConfiguration.get_value('reject_action', 'رد')
    
    @staticmethod
    def get_action_for_change():
        """دریافت Action برای تغییر"""
        return DynamicConfiguration.get_value('change_action', 'تغییر')
    
    @staticmethod
    def initialize_default_configurations():
        """مقداردهی اولیه تنظیمات پیش‌فرض"""
        configs = [
            # Entity Types
            ('factor_entity_type', 'فاکتور', 'entity_types', 'نوع موجودیت برای فاکتور'),
            ('payment_order_entity_type', 'دستور پرداخت', 'entity_types', 'نوع موجودیت برای دستور پرداخت'),
            ('tankhah_entity_type', 'تنخواه', 'entity_types', 'نوع موجودیت برای تنخواه'),
            ('budget_allocation_entity_type', 'تخصیص بودجه', 'entity_types', 'نوع موجودیت برای تخصیص بودجه'),
            
            # Actions
            ('approve_action', 'تأیید', 'actions', 'اقدام تأیید'),
            ('reject_action', 'رد', 'actions', 'اقدام رد'),
            ('change_action', 'تغییر', 'actions', 'اقدام تغییر'),
            ('submit_action', 'ارسال', 'actions', 'اقدام ارسال'),
            ('return_action', 'بازگشت', 'actions', 'اقدام بازگشت'),
            
            # Status Types
            ('initial_status_type', 'is_initial', 'status_types', 'نوع وضعیت اولیه'),
            ('final_approve_status_type', 'is_final_approve', 'status_types', 'نوع وضعیت تأیید نهایی'),
            ('final_reject_status_type', 'is_final_reject', 'status_types', 'نوع وضعیت رد نهایی'),
            ('pending_status_type', 'is_pending', 'status_types', 'نوع وضعیت در انتظار'),
            ('paid_status_type', 'is_paid', 'status_types', 'نوع وضعیت پرداخت شده'),
            ('rejected_status_type', 'is_rejected', 'status_types', 'نوع وضعیت رد شده'),
        ]
        
        for key, value, category, description in configs:
            DynamicConfiguration.set_value(key, value, category, description)
