#!/usr/bin/env python
"""
ایجاد view بازگشت فاکتور
این اسکریپت view و template برای بازگشت فاکتور به کاربر ایجاد می‌کند
"""

import os
import sys
import django
from datetime import datetime

# تنظیم Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

def create_factor_return_view():
    """ایجاد view بازگشت فاکتور"""
    
    print("🔧 ایجاد view بازگشت فاکتور")
    print("=" * 50)
    
    view_content = '''from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.translation import gettext as _
from django.views.generic import View
from django.http import JsonResponse
from django.db import transaction
import logging

from core.PermissionBase import PermissionBaseView
from tankhah.models import Factor, ApprovalLog, FactorHistory
from notificationApp.utils import send_notification

logger = logging.getLogger('FactorReturn')

class FactorReturnView(PermissionBaseView, View):
    """
    View برای بازگشت فاکتور به کاربر
    """
    permission_codename = 'tankhah.factor_return'
    permission_denied_message = _('شما مجوز بازگشت فاکتور را ندارید.')
    
    def post(self, request, pk):
        """بازگشت فاکتور به کاربر"""
        try:
            factor = get_object_or_404(Factor, pk=pk)
            admin_user = request.user
            reason = request.POST.get('reason', '')
            
            # بررسی شرایط بازگشت
            if not self._can_return_factor(factor, admin_user):
                messages.error(request, _('امکان بازگشت این فاکتور وجود ندارد.'))
                return redirect('factor_detail', pk=factor.pk)
            
            # انجام بازگشت
            with transaction.atomic():
                self._return_factor(factor, admin_user, reason)
                
                # ارسال اعلان
                self._send_notification(factor, admin_user, reason)
                
                messages.success(request, _('فاکتور با موفقیت به کاربر بازگردانده شد.'))
                
            return redirect('factor_detail', pk=factor.pk)
            
        except Exception as e:
            logger.error(f"خطا در بازگشت فاکتور {pk}: {str(e)}")
            messages.error(request, _('خطا در بازگشت فاکتور.'))
            return redirect('factor_detail', pk=factor.pk)
    
    def _can_return_factor(self, factor, admin_user):
        """بررسی امکان بازگشت فاکتور"""
        
        # بررسی وضعیت فاکتور
        if factor.status not in ['PENDING', 'APPROVED']:
            logger.warning(f"فاکتور {factor.pk} در وضعیت {factor.status} قابل بازگشت نیست")
            return False
        
        # بررسی قفل بودن تنخواه
        if factor.tankhah.is_locked:
            logger.warning(f"تنخواه {factor.tankhah.pk} قفل است")
            return False
        
        # بررسی قفل بودن فاکتور
        if factor.is_locked:
            logger.warning(f"فاکتور {factor.pk} قفل است")
            return False
        
        # بررسی مجوز ادمین
        if not admin_user.has_perm('tankhah.factor_return'):
            logger.warning(f"کاربر {admin_user.username} مجوز بازگشت ندارد")
            return False
        
        return True
    
    def _return_factor(self, factor, admin_user, reason):
        """انجام بازگشت فاکتور"""
        
        # تغییر وضعیت فاکتور
        old_status = factor.status
        factor.status = 'DRAFT'
        factor.save()
        
        logger.info(f"وضعیت فاکتور {factor.pk} از {old_status} به DRAFT تغییر کرد")
        
        # ثبت لاگ بازگشت
        ApprovalLog.objects.create(
            factor=factor,
            user=admin_user,
            action='RETURN',
            comment=f"بازگشت فاکتور به کاربر. دلیل: {reason}",
            stage=factor.tankhah.current_stage if factor.tankhah else None
        )
        
        # ثبت تاریخچه
        FactorHistory.objects.create(
            factor=factor,
            change_type=FactorHistory.ChangeType.STATUS_CHANGE,
            changed_by=admin_user,
            description=f"فاکتور از وضعیت {old_status} به DRAFT بازگردانده شد. دلیل: {reason}"
        )
        
        logger.info(f"لاگ بازگشت برای فاکتور {factor.pk} ثبت شد")
    
    def _send_notification(self, factor, admin_user, reason):
        """ارسال اعلان به کاربر"""
        
        try:
            send_notification(
                sender=admin_user,
                recipient=factor.created_by,
                verb=_("بازگردانده شد"),
                target=factor,
                description=_("فاکتور {} به شما بازگردانده شد. دلیل: {}").format(
                    factor.number, reason
                ),
                entity_type='FACTOR'
            )
            
            logger.info(f"اعلان بازگشت برای فاکتور {factor.pk} ارسال شد")
            
        except Exception as e:
            logger.error(f"خطا در ارسال اعلان: {str(e)}")

@login_required
@permission_required('tankhah.factor_return')
def return_factor_ajax(request, pk):
    """بازگشت فاکتور با AJAX"""
    
    try:
        factor = get_object_or_404(Factor, pk=pk)
        reason = request.POST.get('reason', '')
        
        if not FactorReturnView()._can_return_factor(factor, request.user):
            return JsonResponse({
                'success': False,
                'message': _('امکان بازگشت این فاکتور وجود ندارد.')
            })
        
        with transaction.atomic():
            FactorReturnView()._return_factor(factor, request.user, reason)
            FactorReturnView()._send_notification(factor, request.user, reason)
        
        return JsonResponse({
            'success': True,
            'message': _('فاکتور با موفقیت بازگردانده شد.')
        })
        
    except Exception as e:
        logger.error(f"خطا در بازگشت AJAX فاکتور {pk}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': _('خطا در بازگشت فاکتور.')
        })
'''
    
    # ایجاد فایل view
    view_path = "tankhah/Factor/views_factor_return.py"
    try:
        with open(view_path, 'w', encoding='utf-8') as f:
            f.write(view_content)
        print(f"   ✅ فایل view ایجاد شد: {view_path}")
    except Exception as e:
        print(f"   ❌ خطا در ایجاد فایل view: {e}")

def create_return_template():
    """ایجاد template بازگشت فاکتور"""
    
    print(f"\n🔧 ایجاد template بازگشت فاکتور")
    print("=" * 50)
    
    template_content = '''{% extends 'base.html' %}
{% load i18n static %}

{% block content %}
<div class="container my-4">
    <div class="card">
        <div class="card-header bg-warning text-dark">
            <h5 class="mb-0">
                <i class="fas fa-undo me-2"></i>
                بازگشت فاکتور به کاربر
            </h5>
        </div>
        <div class="card-body">
            
            <!-- اطلاعات فاکتور -->
            <div class="alert alert-info">
                <h6 class="alert-heading">
                    <i class="fas fa-info-circle me-2"></i>
                    اطلاعات فاکتور
                </h6>
                <p class="mb-1"><strong>شماره فاکتور:</strong> {{ factor.number }}</p>
                <p class="mb-1"><strong>وضعیت فعلی:</strong> 
                    <span class="badge bg-{{ factor.status|lower }}">
                        {{ factor.get_status_display }}
                    </span>
                </p>
                <p class="mb-1"><strong>ایجادکننده:</strong> {{ factor.created_by.get_full_name }}</p>
                <p class="mb-0"><strong>مبلغ:</strong> {{ factor.amount|floatformat:0 }} ریال</p>
            </div>
            
            <!-- فرم بازگشت -->
            <form method="post" id="returnForm">
                {% csrf_token %}
                
                <div class="mb-3">
                    <label for="reason" class="form-label">
                        <i class="fas fa-comment me-1"></i>
                        دلیل بازگشت
                    </label>
                    <textarea class="form-control" id="reason" name="reason" rows="4" 
                              placeholder="دلیل بازگشت فاکتور را توضیح دهید..." required></textarea>
                    <div class="form-text">
                        این توضیحات به کاربر ارسال خواهد شد.
                    </div>
                </div>
                
                <!-- هشدار -->
                <div class="alert alert-warning">
                    <h6 class="alert-heading">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        هشدار
                    </h6>
                    <ul class="mb-0">
                        <li>فاکتور به وضعیت "پیش‌نویس" بازگردانده می‌شود</li>
                        <li>بودجه در تعهد آزاد می‌شود</li>
                        <li>اعلان به کاربر ارسال می‌شود</li>
                        <li>این عمل قابل بازگشت نیست</li>
                    </ul>
                </div>
                
                <!-- دکمه‌ها -->
                <div class="d-flex justify-content-between">
                    <a href="{% url 'factor_detail' factor.pk %}" class="btn btn-secondary">
                        <i class="fas fa-arrow-left me-1"></i>
                        بازگشت
                    </a>
                    <button type="submit" class="btn btn-warning" id="returnBtn">
                        <i class="fas fa-undo me-1"></i>
                        بازگرداندن فاکتور
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>

<!-- Modal تأیید -->
<div class="modal fade" id="confirmModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header bg-warning text-dark">
                <h5 class="modal-title">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    تأیید بازگشت فاکتور
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p>آیا مطمئن هستید که می‌خواهید این فاکتور را به کاربر بازگردانید؟</p>
                <div class="alert alert-warning">
                    <strong>توجه:</strong> این عمل قابل بازگشت نیست و فاکتور به وضعیت پیش‌نویس بازمی‌گردد.
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    لغو
                </button>
                <button type="button" class="btn btn-warning" id="confirmReturn">
                    <i class="fas fa-undo me-1"></i>
                    تأیید بازگشت
                </button>
            </div>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('returnForm');
    const returnBtn = document.getElementById('returnBtn');
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    const confirmReturnBtn = document.getElementById('confirmReturn');
    
    // نمایش modal تأیید
    returnBtn.addEventListener('click', function(e) {
        e.preventDefault();
        
        const reason = document.getElementById('reason').value.trim();
        if (!reason) {
            alert('لطفاً دلیل بازگشت را وارد کنید.');
            return;
        }
        
        confirmModal.show();
    });
    
    // تأیید نهایی
    confirmReturnBtn.addEventListener('click', function() {
        confirmModal.hide();
        form.submit();
    });
});
</script>
{% endblock %}
'''
    
    # ایجاد فایل template
    template_path = "templates/tankhah/Factor/factor_return.html"
    try:
        # ایجاد پوشه اگر وجود ندارد
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        print(f"   ✅ فایل template ایجاد شد: {template_path}")
    except Exception as e:
        print(f"   ❌ خطا در ایجاد فایل template: {e}")

def create_return_urls():
    """ایجاد URL برای بازگشت فاکتور"""
    
    print(f"\n🔧 ایجاد URL برای بازگشت فاکتور")
    print("=" * 50)
    
    url_content = '''# اضافه کردن به tankhah/urls.py

from tankhah.Factor.views_factor_return import FactorReturnView, return_factor_ajax

urlpatterns = [
    # ... سایر URL ها ...
    
    # بازگشت فاکتور
    path('factor/<int:pk>/return/', FactorReturnView.as_view(), name='factor_return'),
    path('factor/<int:pk>/return-ajax/', return_factor_ajax, name='factor_return_ajax'),
]
'''
    
    print("   📋 URL های مورد نیاز:")
    print("      path('factor/<int:pk>/return/', FactorReturnView.as_view(), name='factor_return')")
    print("      path('factor/<int:pk>/return-ajax/', return_factor_ajax, name='factor_return_ajax')")

def create_return_button():
    """ایجاد دکمه بازگشت در template فاکتور"""
    
    print(f"\n🔧 ایجاد دکمه بازگشت")
    print("=" * 50)
    
    button_content = '''<!-- اضافه کردن به template فاکتور -->

{% if user.has_perm:'tankhah.factor_return' and factor.status in 'PENDING,APPROVED' %}
    <a href="{% url 'factor_return' factor.pk %}" 
       class="btn btn-warning btn-sm"
       title="بازگرداندن فاکتور به کاربر">
        <i class="fas fa-undo"></i>
        بازگرداندن
    </a>
{% endif %}
'''
    
    print("   📋 کد دکمه بازگشت:")
    print(button_content)

def show_implementation_summary():
    """نمایش خلاصه پیاده‌سازی"""
    
    print(f"\n📋 خلاصه پیاده‌سازی:")
    print("=" * 50)
    
    print("   🔧 فایل‌های ایجاد شده:")
    print("      ✅ tankhah/Factor/views_factor_return.py")
    print("      ✅ templates/tankhah/Factor/factor_return.html")
    print("   ")
    print("   🔧 فایل‌های نیاز به تغییر:")
    print("      📝 tankhah/urls.py (اضافه کردن URL)")
    print("      📝 templates/factor_detail.html (اضافه کردن دکمه)")
    print("   ")
    print("   🔧 مجوزهای مورد نیاز:")
    print("      ✅ tankhah.factor_return")
    print("   ")
    print("   🔧 قابلیت‌ها:")
    print("      ✅ بازگشت فاکتور به کاربر")
    print("      ✅ ثبت لاگ بازگشت")
    print("      ✅ ارسال اعلان")
    print("      ✅ ثبت تاریخچه")
    print("      ✅ تأیید با modal")
    print("      ✅ پشتیبانی از AJAX")

if __name__ == "__main__":
    create_factor_return_view()
    create_return_template()
    create_return_urls()
    create_return_button()
    show_implementation_summary()
