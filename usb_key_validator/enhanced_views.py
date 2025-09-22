from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from usb_key_validator.enhanced_utils import dongle_manager
from usb_key_validator.forms import DongleEditForm, CompanyDongleForm
from accounts.models import TimeLockModel
import hashlib
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

@login_required
def enhanced_usb_validation(request):
    """اعتبارسنجی پیشرفته USB Dongle"""
    usb_drives = dongle_manager.find_usb_drives()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        device = request.POST.get('usb_device')
        
        if not device:
            messages.error(request, _("لطفاً یک USB انتخاب کنید."))
            return redirect('usb_key_validator:enhanced_validate')
        
        try:
            if action == 'create_dongle':
                       # دریافت اطلاعات شرکت از فرم
                       organization_name = request.POST.get('organization_name', '')
                       software_id = request.POST.get('software_id', 'RCMS')
                       
                       # دریافت آخرین قفل از دیتابیس
                       latest_lock = TimeLockModel.objects.filter(is_active=True).order_by('-created_at').first()
                       if not latest_lock:
                           messages.error(request, _("هیچ قفل فعالی در دیتابیس یافت نشد."))
                           return redirect('usb_key_validator:enhanced_validate')
                       
                       # ایجاد dongle با اطلاعات شرکت
                       key_data = latest_lock.lock_key.encode()
                       success, message = dongle_manager.write_dongle_to_multiple_sectors(
                           device, key_data, organization_name, software_id
                       )
                       
                       if success:
                           messages.success(request, f"✅ {message}")
                       else:
                           messages.error(request, f"❌ {message}")
                
            elif action == 'validate_dongle':
                # اعتبارسنجی dongle
                is_valid, message = dongle_manager.validate_dongle_integrity(device)
                
                if is_valid:
                    messages.success(request, f"✅ {message}")
                else:
                    messages.error(request, f"❌ {message}")
                
            elif action == 'repair_dongle':
                # تعمیر dongle
                success, message = dongle_manager.repair_dongle_sectors(device)
                
                if success:
                    messages.success(request, f"✅ {message}")
                else:
                    messages.error(request, f"❌ {message}")
                
            elif action == 'daily_check':
                # بررسی روزانه
                result = dongle_manager.daily_validation_check()
                
                if result['valid']:
                    messages.success(request, f"✅ {result['message']}")
                else:
                    messages.error(request, f"❌ {result['message']}")
        
        except Exception as e:
            messages.error(request, f"خطا در پردازش: {str(e)}")
            logger.error(f"Error in enhanced USB validation: {e}")
    
    # آمار dongle
    dongle_stats = None
    if usb_drives:
        try:
            device = usb_drives[0]['device_id']
            dongle_stats = dongle_manager.get_dongle_statistics(device)
        except:
            pass
    
           # دریافت آخرین قفل برای نمایش اطلاعات شرکت
        latest_lock = TimeLockModel.objects.filter(is_active=True).order_by('-created_at').first()
        
        context = {
            'usb_drives': usb_drives,
            'dongle_stats': dongle_stats,
            'latest_lock': latest_lock,
            'title': _('اعتبارسنجی پیشرفته USB Dongle')
        }
    
    return render(request, 'usb_key_validator/enhanced_validation.html', context)

@login_required
@require_http_methods(["GET"])
def dongle_ajax_status(request):
    """دریافت وضعیت dongle به صورت AJAX"""
    try:
        device = request.GET.get('device')
        if not device:
            return JsonResponse({'error': 'Device not specified'}, status=400)
        
        # اعتبارسنجی
        is_valid, message = dongle_manager.validate_dongle_integrity(device)
        
        # آمار
        stats = dongle_manager.get_dongle_statistics(device)
        
        return JsonResponse({
            'valid': is_valid,
            'message': message,
            'stats': stats,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in dongle AJAX status: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def dongle_ajax_action(request):
    """اجرای عملیات dongle به صورت AJAX"""
    try:
        action = request.POST.get('action')
        device = request.POST.get('device')
        
        if not device:
            return JsonResponse({'error': 'Device not specified'}, status=400)
        
        if action == 'validate':
            is_valid, message = dongle_manager.validate_dongle_integrity(device)
            return JsonResponse({
                'success': is_valid,
                'message': message
            })
        
        elif action == 'repair':
            success, message = dongle_manager.repair_dongle_sectors(device)
            return JsonResponse({
                'success': success,
                'message': message
            })
        
        elif action == 'stats':
            stats = dongle_manager.get_dongle_statistics(device)
            return JsonResponse({
                'success': True,
                'stats': stats
            })
        
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
    except Exception as e:
        logger.error(f"Error in dongle AJAX action: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def dongle_dashboard(request):
    """داشبورد مدیریت dongle"""
    usb_drives = dongle_manager.find_usb_drives()
    
    # آمار کلی
    total_drives = len(usb_drives)
    valid_dongles = 0
    dongle_details = []
    
    for drive in usb_drives:
        try:
            is_valid, message = dongle_manager.validate_dongle_integrity(drive['device_id'])
            stats = dongle_manager.get_dongle_statistics(drive['device_id'])
            
            if is_valid:
                valid_dongles += 1
            
            dongle_details.append({
                'drive': drive,
                'valid': is_valid,
                'message': message,
                'stats': stats
            })
        except:
            dongle_details.append({
                'drive': drive,
                'valid': False,
                'message': 'خطا در بررسی',
                'stats': None
            })
    
    # آخرین بررسی روزانه
    from django.core.cache import cache
    last_daily_check = cache.get('usb_dongle_validation')
    
    context = {
        'usb_drives': usb_drives,
        'total_drives': total_drives,
        'valid_dongles': valid_dongles,
        'dongle_details': dongle_details,
        'last_daily_check': last_daily_check,
        'title': _('داشبورد مدیریت USB Dongle')
    }
    
    return render(request, 'usb_key_validator/dongle_dashboard.html', context)

@login_required
def edit_dongle_info(request, device_id):
    """ویرایش اطلاعات dongle"""
    try:
        # خواندن اطلاعات فعلی dongle
        key_data, signature_data, source_sector = dongle_manager.read_dongle_from_sectors(device_id)
        
        if not signature_data:
            messages.error(request, _("Dongle یافت نشد یا قابل خواندن نیست."))
            return redirect('usb_key_validator:dongle_dashboard')
        
        # آماده‌سازی اطلاعات اولیه
        initial_data = {}
        if isinstance(signature_data, dict):
            initial_data = {
                'organization_name': signature_data.get('organization_name', ''),
                'software_id': signature_data.get('software_id', 'RCMS'),
                'expiry_date': signature_data.get('expiry_date', '')
            }
        
        if request.method == 'POST':
            form = DongleEditForm(request.POST, initial_data=initial_data)
            if form.is_valid():
                # دریافت اطلاعات جدید
                new_org_name = form.cleaned_data['organization_name']
                new_software_id = form.cleaned_data['software_id']
                new_expiry_date = form.cleaned_data['expiry_date']
                
                # ایجاد signature جدید
                new_signature = dongle_manager.create_dongle_signature(
                    key_data, new_org_name, new_software_id, new_expiry_date
                )
                
                # بازنویسی dongle
                success, message = dongle_manager.write_dongle_to_multiple_sectors(
                    device_id, key_data, new_org_name, new_software_id, new_expiry_date
                )
                
                if success:
                    messages.success(request, f"✅ {message}")
                else:
                    messages.error(request, f"❌ {message}")
                
                return redirect('usb_key_validator:dongle_dashboard')
        else:
            form = DongleEditForm(initial_data=initial_data)
        
        context = {
            'form': form,
            'device_id': device_id,
            'signature_data': signature_data,
            'title': _('ویرایش اطلاعات Dongle')
        }
        
        return render(request, 'usb_key_validator/edit_dongle.html', context)
        
    except Exception as e:
        logger.error(f"Error in edit_dongle_info: {e}")
        messages.error(request, f"خطا در ویرایش dongle: {str(e)}")
        return redirect('usb_key_validator:dongle_dashboard')

@login_required
def create_company_dongle(request):
    """ایجاد dongle برای شرکت جدید"""
    if request.method == 'POST':
        form = CompanyDongleForm(request.POST)
        if form.is_valid():
            company_name = form.cleaned_data['company_name']
            software_id = form.cleaned_data['software_id']
            max_users = form.cleaned_data['max_users']
            expiry_days = form.cleaned_data['expiry_days']
            
            # ایجاد قفل جدید برای شرکت
            expiry_date = date.today() + timedelta(days=expiry_days)
            
            # استفاده از RCMS_Lock برای ایجاد قفل جدید
            from core.RCMS_Lock.security import TimeLock
            success = TimeLock.set_expiry_date(expiry_date, max_users, company_name)
            
            if success:
                messages.success(request, f"✅ قفل جدید برای شرکت '{company_name}' ایجاد شد")
                return redirect('usb_key_validator:enhanced_validate')
            else:
                messages.error(request, "❌ خطا در ایجاد قفل جدید")
    else:
        form = CompanyDongleForm()
    
    context = {
        'form': form,
        'title': _('ایجاد Dongle برای شرکت جدید')
    }
    
    return render(request, 'usb_key_validator/create_company_dongle.html', context)
