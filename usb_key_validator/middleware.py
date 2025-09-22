from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext as _
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class USBDongleValidationMiddleware:
    """
    Middleware برای اعتبارسنجی USB Dongle در هر لاگین
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # URL هایی که نیاز به اعتبارسنجی ندارند
        self.exempt_urls = [
            '/admin/login/',
            '/accounts/login/',
            '/usb-key-validator/',
            '/usb-key-validator/enhanced/',
            '/usb-key-validator/dashboard/',
            '/favicon.ico',
            '/static/',
            '/media/',
        ]
    
    def __call__(self, request):
        # بررسی فعال بودن middleware از تنظیمات
        if not getattr(settings, 'USB_DONGLE_VALIDATION_ENABLED', False):
            response = self.get_response(request)
            return response
        
        # بررسی اینکه آیا کاربر لاگین کرده است
        if not request.user.is_authenticated:
            response = self.get_response(request)
            return response
        
        # بررسی URL های معاف
        if any(request.path.startswith(url) for url in self.exempt_urls):
            response = self.get_response(request)
            return response
        
        # بررسی اینکه آیا کاربر قبلاً به صفحه اعتبارسنجی ریدایرکت شده
        if request.path == reverse('usb_key_validator:enhanced_validate'):
            response = self.get_response(request)
            return response
        
        # بررسی اینکه آیا کاربر superuser است (معاف از اعتبارسنجی)
        if request.user.is_superuser:
            response = self.get_response(request)
            return response
        
        # اعتبارسنجی USB Dongle
        try:
            from usb_key_validator.enhanced_utils import dongle_manager
            
            # بررسی cache برای جلوگیری از اعتبارسنجی مکرر
            from django.core.cache import cache
            cache_key = f'usb_validation_{request.user.id}'
            cached_result = cache.get(cache_key)
            
            # استفاده از تنظیمات cache timeout
            cache_timeout = getattr(settings, 'USB_DONGLE_CACHE_TIMEOUT', 300)
            
            if cached_result is None:
                # اعتبارسنجی dongle
                result = dongle_manager.daily_validation_check()
                
                # cache نتیجه با تنظیمات
                cache.set(cache_key, result, cache_timeout)
                
                if not result['valid']:
                    logger.warning(f"USB Dongle validation failed for user {request.user.username}: {result['message']}")
                    
                    # بررسی اینکه آیا کاربر قبلاً به صفحه اعتبارسنجی ریدایرکت شده
                    if request.path != reverse('usb_key_validator:enhanced_validate'):
                        # اضافه کردن پیام خطا
                        messages.error(request, _("اعتبارسنجی USB Dongle ناموفق: {}").format(result['message']))
                        
                        # هدایت به صفحه اعتبارسنجی
                        return redirect('usb_key_validator:enhanced_validate')
            else:
                # استفاده از نتیجه cache شده
                if not cached_result['valid']:
                    logger.warning(f"USB Dongle validation failed (cached) for user {request.user.username}")
                    
                    # بررسی اینکه آیا کاربر قبلاً به صفحه اعتبارسنجی ریدایرکت شده
                    if request.path != reverse('usb_key_validator:enhanced_validate'):
                        messages.error(request, _("اعتبارسنجی USB Dongle ناموفق: {}").format(cached_result['message']))
                        return redirect('usb_key_validator:enhanced_validate')
        
        except Exception as e:
            logger.error(f"Error in USB Dongle validation middleware: {e}")
            # در صورت خطا، اجازه ادامه می‌دهیم تا سیستم متوقف نشود
            pass
        
        response = self.get_response(request)
        return response
