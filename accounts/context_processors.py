def user_theme(request):
    """Context processor برای دسترسی به تم کاربر در تمام تمپلیت‌ها"""
    from accounts.models import CustomProfile
    from accounts.theme_config import get_theme_config
    
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            theme = profile.theme
            custom_theme_data = None
            
            # اگر تم سفارشی است، داده‌های آن را نیز ارسال کن
            if theme == 'custom' and hasattr(profile, 'custom_theme_data'):
                custom_theme_data = profile.custom_theme_data
        except:
            # در صورت عدم وجود پروفایل، از مقدار پیش‌فرض مدل استفاده کن
            theme = CustomProfile._meta.get_field('theme').default
            custom_theme_data = None
    else:
        from accounts.models import CustomProfile
        theme = CustomProfile._meta.get_field('theme').default
        custom_theme_data = None
    
    # دریافت تنظیمات تم فعلی
    current_theme_config = get_theme_config(theme)
    
    from accounts.theme_config import get_core_theme_choices, get_extra_theme_choices
    
    return {
        'user_theme': theme,
        'custom_theme_data': custom_theme_data,
        'available_themes': CustomProfile.get_theme_choices(),
        'core_themes': get_core_theme_choices(),
        'extra_themes': get_extra_theme_choices(),
        'current_theme_config': current_theme_config
    }
