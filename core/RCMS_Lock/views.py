# core/RCMS_Lock/views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from core.RCMS_Lock.security import TimeLock
from core.models import TimeLockModel
from accounts.models import ActiveUser
import datetime

@staff_member_required
def timelock_management(request):
    if request.method == 'POST':
        if 'set_date' in request.POST:
            date_str = request.POST.get('expiry_date')
            try:
                expiry_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                TimeLock.set_expiry_date(expiry_date)
            except ValueError:
                pass
        elif 'remove_lock' in request.POST:
            TimeLock.set_expiry_date(datetime.date(1970, 1, 1))  # تاریخ قدیمی

    context = {
        'current_expiry': TimeLock.get_expiry_date(),
        'is_locked': TimeLock.is_locked()
    }
    return render(request, 'core/locked_page.html', context)


@staff_member_required
def lock_status(request):
    """بررسی وضعیت قفل"""
    is_locked = TimeLock.is_locked()
    expiry_date = TimeLock.get_expiry_date()

    return JsonResponse({
        "locked": is_locked,
        "expiry_date": expiry_date.strftime('%Y-%m-%d') if expiry_date else None
    })

# @staff_member_required
# def set_lock(request):
#     """تنظیم قفل از طریق فرم"""
#     lock_instance = TimeLockModel.objects.first()  # آخرین مقدار قفل را بگیر
#     current_expiry_date = lock_instance.expiry_date if lock_instance else None
#
#     if request.method == "POST":
#         expiry_date = request.POST.get("expiry_date")
#         try:
#             expiry_date = datetime.datetime.strptime(expiry_date, "%Y-%m-%d").date()
#             TimeLock.set_expiry_date(expiry_date)
#
#             if lock_instance:
#                 # اگر رکورد قبلی وجود دارد، تاریخ را به‌روزرسانی می‌کنیم
#                 lock_instance.expiry_date = expiry_date
#                 lock_instance.save()
#             else:
#                 # اگر رکوردی وجود نداشت، یک رکورد جدید می‌سازیم
#                 TimeLockModel.objects.create(expiry_date=expiry_date)
#
#             return redirect("lock_status")
#         except ValueError:
#             return JsonResponse({"error": "تاریخ نامعتبر است."}, status=400)
#
#     return render(request, "core/set_lock.html", {"current_expiry_date": current_expiry_date})
#
# def view_lock_system_date(request):
#     lock = TimeLockModel.objects.first()  # مقدار قفل را از دیتابیس دریافت کن
#     expiry_date = lock.expiry_date if lock else None
#
#
# #
# #######################
# # core/RCMS_Lock/views.py
###
# @staff_member_required
# def set_lock(request):
#     """تنظیم قفل از طریق فرم"""
#     lock_instance = TimeLockModel.objects.first()  # آخرین مقدار قفل را بگیر
#     current_expiry_date = lock_instance.expiry_date if lock_instance else None
#     # قفل تعداد کاربری
#     is_locked = TimeLock.is_locked()
#     expiry_date = TimeLock.get_expiry_date()
#     # تعداد کاربران فعال بر اساس سشن‌ها
#     active_users_count = ActiveUser.objects.count()
#     max_active_users = ActiveUser.MAX_ACTIVE_USERS
#
#     if request.method == "POST":
#         if 'set_date' in request.POST:
#             date_str = request.POST.get('expiry_date')
#             try:
#                 expiry_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
#                 TimeLock.set_expiry_date(expiry_date)
#                 if lock_instance:
#                     lock_instance.expiry_date = expiry_date
#                     lock_instance.save()
#                 else:
#                     TimeLockModel.objects.create(expiry_date=expiry_date)
#                 return redirect('set_lock')
#             except ValueError:
#                 return JsonResponse({"error": "تاریخ نامعتبر است."}, status=400)
#
#         elif 'remove_lock' in request.POST:
#             TimeLock.set_expiry_date(datetime.date(1970, 1, 1))
#             if lock_instance:
#                 lock_instance.expiry_date = datetime.date(1970, 1, 1)
#                 lock_instance.save()
#             return redirect('set_lock')
#
#     if request.headers.get('x-requested-with') == 'XMLHttpRequest':
#         return JsonResponse({
#             "locked": is_locked,
#             "expiry_date": expiry_date.strftime('%Y-%m-%d') if expiry_date else None,
#             "active_users": active_users_count,
#             "max_active_users": max_active_users
#         })
#
#     context = {
#         'current_expiry': expiry_date,
#         'is_locked': is_locked,
#         'active_users_count': active_users_count,
#         'max_active_users': max_active_users,
#     }
#     return render(request, 'core/set_lock.html', context)


##############################################################

