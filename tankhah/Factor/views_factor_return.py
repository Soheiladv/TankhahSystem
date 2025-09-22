from django.shortcuts import get_object_or_404, redirect
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
