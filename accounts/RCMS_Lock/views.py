# core/RCMS_Lock/views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.RCMS_Lock.security import TimeLock
from accounts.models import TimeLockModel
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

