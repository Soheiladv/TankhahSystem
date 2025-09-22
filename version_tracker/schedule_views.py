from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _
from notificationApp.models import BackupSchedule, BackupLog, Notification
from notificationApp.utils import execute_scheduled_backup
from .forms import BackupScheduleForm
import logging

logger = logging.getLogger(__name__)

@login_required
def schedule_list_view(request):
    """لیست اسکچول‌های پشتیبان‌گیری"""
    schedules = BackupSchedule.objects.all().order_by('-created_at')
    
    # آمار کلی
    total_schedules = schedules.count()
    active_schedules = schedules.filter(is_active=True).count()
    pending_schedules = schedules.filter(
        is_active=True,
        next_run__isnull=False
    ).count()
    total_logs = BackupLog.objects.count()
    
    # فیلتر
    search = request.GET.get('search')
    if search:
        schedules = schedules.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # صفحه‌بندی
    paginator = Paginator(schedules, 10)
    page_number = request.GET.get('page')
    schedules = paginator.get_page(page_number)
    
    context = {
        'schedules': schedules,
        'total_schedules': total_schedules,
        'active_schedules': active_schedules,
        'pending_schedules': pending_schedules,
        'total_logs': total_logs,
        'search': search,
    }
    
    return render(request, 'admin/backup_schedule_list.html', context)

@login_required
def schedule_create_view(request):
    """ایجاد اسکچول جدید"""
    if request.method == 'POST':
        form = BackupScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.created_by = request.user
            schedule.save()
            form.save_m2m()  # ذخیره گیرندگان اعلان
            
            # بروزرسانی زمان اجرای بعدی
            if schedule.is_active:
                schedule.update_next_run()
            
            messages.success(request, _('اسکچول با موفقیت ایجاد شد'))
            return redirect('backup:schedule_detail', schedule.id)
    else:
        form = BackupScheduleForm()
    
    return render(request, 'admin/backup_schedule_form.html', {
        'form': form,
        'schedule': None
    })

@login_required
def schedule_edit_view(request, schedule_id):
    """ویرایش اسکچول"""
    schedule = get_object_or_404(BackupSchedule, id=schedule_id)
    
    if request.method == 'POST':
        form = BackupScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save()
            
            # بروزرسانی زمان اجرای بعدی
            if schedule.is_active:
                schedule.update_next_run()
            
            messages.success(request, _('اسکچول با موفقیت بروزرسانی شد'))
            return redirect('backup:schedule_detail', schedule.id)
    else:
        form = BackupScheduleForm(instance=schedule)
    
    return render(request, 'admin/backup_schedule_form.html', {
        'form': form,
        'schedule': schedule
    })

@login_required
def schedule_detail_view(request, schedule_id):
    """جزئیات اسکچول"""
    schedule = get_object_or_404(BackupSchedule, id=schedule_id)
    
    # لاگ‌های اخیر
    recent_logs = schedule.logs.all().order_by('-started_at')[:10]
    
    # آمار
    total_runs = schedule.logs.count()
    successful_runs = schedule.logs.filter(status='COMPLETED').count()
    failed_runs = schedule.logs.filter(status='FAILED').count()
    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
    
    context = {
        'schedule': schedule,
        'recent_logs': recent_logs,
        'total_runs': total_runs,
        'successful_runs': successful_runs,
        'failed_runs': failed_runs,
        'success_rate': round(success_rate, 1),
    }
    
    return render(request, 'admin/backup_schedule_detail.html', context)

@login_required
@require_http_methods(["POST"])
def schedule_delete_view(request, schedule_id):
    """حذف اسکچول"""
    schedule = get_object_or_404(BackupSchedule, id=schedule_id)
    
    try:
        schedule_name = schedule.name
        schedule.delete()
        messages.success(request, _('اسکچول "{}" با موفقیت حذف شد').format(schedule_name))
    except Exception as e:
        logger.error(f"خطا در حذف اسکچول {schedule_id}: {str(e)}")
        messages.error(request, _('خطا در حذف اسکچول'))
    
    return redirect('backup:schedule_list')

@login_required
@require_http_methods(["POST"])
def schedule_toggle_view(request, schedule_id):
    """فعال/غیرفعال کردن اسکچول"""
    schedule = get_object_or_404(BackupSchedule, id=schedule_id)
    
    try:
        schedule.is_active = not schedule.is_active
        schedule.save()
        
        # بروزرسانی زمان اجرای بعدی
        if schedule.is_active:
            schedule.update_next_run()
            messages.success(request, _('اسکچول فعال شد'))
        else:
            schedule.next_run = None
            schedule.save()
            messages.success(request, _('اسکچول غیرفعال شد'))
    except Exception as e:
        logger.error(f"خطا در تغییر وضعیت اسکچول {schedule_id}: {str(e)}")
        messages.error(request, _('خطا در تغییر وضعیت اسکچول'))
    
    return redirect('backup:schedule_detail', schedule.id)

@login_required
@require_http_methods(["POST"])
def schedule_run_view(request, schedule_id):
    """اجرای دستی اسکچول"""
    schedule = get_object_or_404(BackupSchedule, id=schedule_id)
    
    try:
        success = execute_scheduled_backup(schedule_id)
        if success:
            messages.success(request, _('اسکچول با موفقیت اجرا شد'))
        else:
            messages.error(request, _('اجرای اسکچول ناموفق بود'))
    except Exception as e:
        logger.error(f"خطا در اجرای دستی اسکچول {schedule_id}: {str(e)}")
        messages.error(request, _('خطا در اجرای اسکچول'))
    
    return redirect('backup:schedule_detail', schedule.id)

@login_required
def schedule_logs_view(request):
    """لیست لاگ‌های پشتیبان‌گیری"""
    logs = BackupLog.objects.all().order_by('-started_at')
    
    # فیلتر بر اساس اسکچول
    schedule_id = request.GET.get('schedule')
    if schedule_id:
        logs = logs.filter(schedule_id=schedule_id)
    
    # فیلتر بر اساس وضعیت
    status = request.GET.get('status')
    if status:
        logs = logs.filter(status=status)
    
    # صفحه‌بندی
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    logs = paginator.get_page(page_number)
    
    # آمار
    total_logs = logs.paginator.count
    successful_logs = logs.paginator.object_list.filter(status='COMPLETED').count()
    failed_logs = logs.paginator.object_list.filter(status='FAILED').count()
    
    # لیست اسکچول‌ها برای فیلتر
    schedules = BackupSchedule.objects.all().order_by('name')
    
    context = {
        'logs': logs,
        'schedules': schedules,
        'total_logs': total_logs,
        'successful_logs': successful_logs,
        'failed_logs': failed_logs,
        'schedule_id': schedule_id,
        'status': status,
    }
    
    return render(request, 'admin/backup_schedule_logs.html', context)

@login_required
def schedule_test_view(request):
    """تست سیستم پشتیبان‌گیری"""
    if request.method == 'POST':
        try:
            from notificationApp.utils import check_and_execute_scheduled_backups
            check_and_execute_scheduled_backups()
            messages.success(request, _('تست سیستم با موفقیت انجام شد'))
        except Exception as e:
            logger.error(f"خطا در تست سیستم: {str(e)}")
            messages.error(request, _('خطا در تست سیستم'))
        return redirect('backup:schedule_list')
    
    # آمار برای نمایش
    from django.utils import timezone
    now = timezone.now()
    
    total_schedules = BackupSchedule.objects.count()
    active_schedules = BackupSchedule.objects.filter(is_active=True).count()
    pending_schedules = BackupSchedule.objects.filter(
        is_active=True,
        next_run__lte=now
    ).count()
    total_logs = BackupLog.objects.count()
    
    context = {
        'total_schedules': total_schedules,
        'active_schedules': active_schedules,
        'pending_schedules': pending_schedules,
        'total_logs': total_logs,
    }
    
    return render(request, 'admin/backup_schedule_test.html', context)

@login_required
def schedule_ajax_status(request, schedule_id):
    """دریافت وضعیت اسکچول به صورت AJAX"""
    schedule = get_object_or_404(BackupSchedule, id=schedule_id)
    
    data = {
        'id': schedule.id,
        'name': schedule.name,
        'is_active': schedule.is_active,
        'next_run': schedule.next_run.isoformat() if schedule.next_run else None,
        'last_run': schedule.last_run.isoformat() if schedule.last_run else None,
        'total_runs': schedule.logs.count(),
        'successful_runs': schedule.logs.filter(status='COMPLETED').count(),
        'failed_runs': schedule.logs.filter(status='FAILED').count(),
    }
    
    return JsonResponse(data)
