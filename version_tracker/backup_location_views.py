from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _
from django.core.paginator import Paginator
from .models_backup_locations import BackupLocation
import logging
import os

logger = logging.getLogger(__name__)

@login_required
def backup_locations_list(request):
    """لیست مسیرهای پشتیبان‌گیری"""
    locations = BackupLocation.objects.all().order_by('-is_default', 'name')
    
    # آمار کلی
    total_locations = locations.count()
    active_locations = locations.filter(status='ACTIVE').count()
    network_locations = locations.filter(location_type='NETWORK').count()
    
    # فیلتر
    search = request.GET.get('search')
    if search:
        locations = locations.filter(
            name__icontains=search
        )
    
    # صفحه‌بندی
    paginator = Paginator(locations, 10)
    page_number = request.GET.get('page')
    locations = paginator.get_page(page_number)
    
    context = {
        'locations': locations,
        'total_locations': total_locations,
        'active_locations': active_locations,
        'network_locations': network_locations,
        'search': search,
    }
    
    return render(request, 'admin/backup_locations_list.html', context)

@login_required
def backup_location_detail(request, location_id):
    """جزئیات مسیر پشتیبان‌گیری"""
    location = get_object_or_404(BackupLocation, id=location_id)
    
    # اطلاعات فضای دیسک
    disk_info = location.get_available_space()
    
    # فایل‌های پشتیبان
    backup_files = location.get_backup_files()
    
    context = {
        'location': location,
        'disk_info': disk_info,
        'backup_files': backup_files,
    }
    
    return render(request, 'admin/backup_location_detail.html', context)

@login_required
@require_http_methods(["POST"])
def backup_location_test(request, location_id):
    """تست اتصال به مسیر پشتیبان‌گیری"""
    location = get_object_or_404(BackupLocation, id=location_id)
    
    success, message = location.test_connection()
    
    if success:
        messages.success(request, f"تست اتصال موفق: {message}")
    else:
        messages.error(request, f"تست اتصال ناموفق: {message}")
    
    return redirect('backup:location_detail', location_id)

@login_required
@require_http_methods(["POST"])
def backup_location_set_default(request, location_id):
    """تنظیم مسیر به عنوان پیش‌فرض"""
    location = get_object_or_404(BackupLocation, id=location_id)
    
    # تست اتصال قبل از تنظیم به عنوان پیش‌فرض
    success, message = location.test_connection()
    
    if success:
        location.is_default = True
        location.save()
        messages.success(request, f"مسیر '{location.name}' به عنوان پیش‌فرض تنظیم شد")
    else:
        messages.error(request, f"نمی‌توان مسیر را به عنوان پیش‌فرض تنظیم کرد: {message}")
    
    return redirect('backup:location_detail', location_id)

@login_required
@require_http_methods(["POST"])
def backup_location_toggle_status(request, location_id):
    """تغییر وضعیت مسیر"""
    location = get_object_or_404(BackupLocation, id=location_id)
    
    if location.status == 'ACTIVE':
        location.status = 'INACTIVE'
        messages.info(request, f"مسیر '{location.name}' غیرفعال شد")
    else:
        # تست اتصال قبل از فعال کردن
        success, message = location.test_connection()
        if success:
            location.status = 'ACTIVE'
            messages.success(request, f"مسیر '{location.name}' فعال شد")
        else:
            messages.error(request, f"نمی‌توان مسیر را فعال کرد: {message}")
            return redirect('backup:location_detail', location_id)
    
    location.save()
    return redirect('backup:location_detail', location_id)

@login_required
def backup_location_create(request):
    """ایجاد مسیر جدید"""
    if request.method == 'POST':
        name = request.POST.get('name')
        path = request.POST.get('path')
        location_type = request.POST.get('location_type')
        description = request.POST.get('description')
        
        if not all([name, path, location_type]):
            messages.error(request, "لطفاً تمام فیلدهای ضروری را پر کنید")
            return redirect('backup:location_create')
        
        # بررسی وجود مسیر مشابه
        if BackupLocation.objects.filter(path=path).exists():
            messages.error(request, "مسیر قبلاً وجود دارد")
            return redirect('backup:location_create')
        
        location = BackupLocation.objects.create(
            name=name,
            path=path,
            location_type=location_type,
            description=description,
            created_by=request.user
        )
        
        # تست اتصال
        success, message = location.test_connection()
        if success:
            messages.success(request, f"مسیر '{location.name}' با موفقیت ایجاد شد")
        else:
            messages.warning(request, f"مسیر ایجاد شد اما اتصال ناموفق: {message}")
        
        return redirect('backup:location_detail', location.id)
    
    return render(request, 'admin/backup_location_form.html', {
        'location': None
    })

@login_required
def backup_location_edit(request, location_id):
    """ویرایش مسیر"""
    location = get_object_or_404(BackupLocation, id=location_id)
    
    if request.method == 'POST':
        location.name = request.POST.get('name', location.name)
        location.path = request.POST.get('path', location.path)
        location.location_type = request.POST.get('location_type', location.location_type)
        location.description = request.POST.get('description', location.description)
        
        location.save()
        
        # تست اتصال
        success, message = location.test_connection()
        if success:
            messages.success(request, f"مسیر '{location.name}' با موفقیت بروزرسانی شد")
        else:
            messages.warning(request, f"مسیر بروزرسانی شد اما اتصال ناموفق: {message}")
        
        return redirect('backup:location_detail', location.id)
    
    return render(request, 'admin/backup_location_form.html', {
        'location': location
    })

@login_required
@require_http_methods(["POST"])
def backup_location_delete(request, location_id):
    """حذف مسیر"""
    location = get_object_or_404(BackupLocation, id=location_id)
    
    if location.is_default:
        messages.error(request, "نمی‌توان مسیر پیش‌فرض را حذف کرد")
        return redirect('backup:location_detail', location_id)
    
    location_name = location.name
    location.delete()
    
    messages.success(request, f"مسیر '{location_name}' حذف شد")
    return redirect('backup:locations_list')

@login_required
def backup_location_ajax_status(request, location_id):
    """دریافت وضعیت مسیر به صورت AJAX"""
    location = get_object_or_404(BackupLocation, id=location_id)
    
    disk_info = location.get_available_space()
    backup_files = location.get_backup_files()
    
    return JsonResponse({
        'status': location.status,
        'last_tested': location.last_tested.isoformat() if location.last_tested else None,
        'last_error': location.last_error,
        'disk_info': disk_info,
        'backup_files_count': len(backup_files),
        'is_default': location.is_default,
    })
