"""
View های مدیریتی برای ادمین جهت کنترل گردش کار
"""
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, permission_required
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
from django.contrib.auth.decorators import login_required

from core.models import Status, Transition, Action, EntityType, Organization
from tankhah.models import Factor, Tankhah, ApprovalLog
from accounts.models import CustomUser
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

def is_admin(user):
    """بررسی اینکه کاربر ادمین است یا نه"""
    return user.is_authenticated and (user.is_superuser or user.is_staff)

@login_required
@permission_required('tankhah.admin_workflow_control', raise_exception=True)
def admin_workflow_control(request, entity_type, entity_id):
    """
    صفحه کنترل گردش کار برای ادمین
    """
    logger.debug("[ADMIN_WF_CONTROL] user=%s entity_type=%s entity_id=%s method=%s params=%s",
                 getattr(request.user, 'username', None), entity_type, entity_id, request.method, dict(request.GET))

    # Fallback: پشتیبانی از تغییر وضعیت با GET query برای ادمین‌ها
    try:
        new_status_q = request.GET.get('new_status_id')
        comment_q = request.GET.get('comment') or 'تغییر وضعیت توسط ادمین (GET)'
        if new_status_q:
            logger.debug("[ADMIN_WF_CONTROL][GET_FALLBACK] Requested change via GET: new_status_id=%s", new_status_q)
            # اعمال همان منطق admin_change_status به صورت ایمن
            with transaction.atomic():
                if entity_type == 'factor':
                    entity = get_object_or_404(Factor, id=entity_id)
                elif entity_type == 'tankhah':
                    entity = get_object_or_404(Tankhah, id=entity_id)
                else:
                    messages.error(request, _('نوع موجودیت نامعتبر است.'))
                    return redirect('dashboard')

                try:
                    new_status = get_object_or_404(Status, id=int(new_status_q))
                except ValueError:
                    messages.error(request, _('شناسه وضعیت نامعتبر است.'))
                    return redirect('admin_workflow_control', entity_type=entity_type, entity_id=entity_id)

                old_status = getattr(entity, 'status', None)
                entity.status = new_status
                entity.save()

                content_type = ContentType.objects.get(model=entity_type)
                admin_change_action = Action.objects.filter(code='ADMIN_CHANGE').first()
                if not admin_change_action:
                    admin_change_action = Action.objects.filter(is_active=True).first()
                    if not admin_change_action:
                        admin_change_action = Action.objects.create(
                            name='تغییر وضعیت توسط ادمین',
                            code='ADMIN_CHANGE',
                            description='تغییر وضعیت توسط ادمین',
                            created_by=request.user
                        )

                ApprovalLog.objects.create(
                    content_type=content_type,
                    object_id=entity_id,
                    from_status=old_status,
                    to_status=new_status,
                    action=admin_change_action,
                    user=request.user,
                    post=None,
                    comment=comment_q,
                    is_admin_action=True
                )

                logger.info(
                    "[ADMIN_WF_CONTROL][GET_FALLBACK][OK] user=%s %s:%s %s->%s",
                    getattr(request.user, 'username', None), entity_type, entity_id,
                    getattr(old_status, 'code', None), getattr(new_status, 'code', None)
                )
                messages.success(request, _('وضعیت با موفقیت تغییر یافت.'))
                # پاکسازی querystring با ریدایرکت به همان صفحه بدون پارامتر
                return redirect('admin_workflow_control', entity_type=entity_type, entity_id=entity_id)
    except Exception as ex:
        logger.error("[ADMIN_WF_CONTROL][GET_FALLBACK][ERROR] %s", str(ex), exc_info=True)
        messages.error(request, _('خطا در تغییر وضعیت: %(err)s') % {'err': str(ex)})
        return redirect('admin_workflow_control', entity_type=entity_type, entity_id=entity_id)
    # پیدا کردن موجودیت
    if entity_type == 'factor':
        entity = get_object_or_404(Factor, id=entity_id)
        entity_type_obj = EntityType.objects.get(code='FACTOR')
    elif entity_type == 'tankhah':
        entity = get_object_or_404(Tankhah, id=entity_id)
        entity_type_obj = EntityType.objects.get(code='TANKHAH')
    else:
        messages.error(request, _('نوع موجودیت نامعتبر است.'))
        return redirect('dashboard')
    
    # دریافت تمام وضعیت‌های موجود برای این نوع موجودیت
    # از آنجایی که Status مستقیماً entity_type ندارد، از طریق Transition ها پیدا می‌کنیم
    status_ids = Transition.objects.filter(
        entity_type=entity_type_obj,
        is_active=True
    ).values_list('from_status_id', 'to_status_id').distinct()
    
    # تبدیل به یک لیست از ID ها
    all_status_ids = set()
    for from_id, to_id in status_ids:
        if from_id:
            all_status_ids.add(from_id)
        if to_id:
            all_status_ids.add(to_id)
    
    # اگر هیچ Transition وجود نداشت، تمام Status های فعال را نشان می‌دهیم
    if all_status_ids:
        all_statuses = Status.objects.filter(
            id__in=all_status_ids,
            is_active=True
        ).order_by('id')
    else:
        all_statuses = Status.objects.filter(
            is_active=True
        ).order_by('id')
    
    # دریافت تاریخچه تاییدها
    content_type = ContentType.objects.get(model=entity_type)
    approval_logs = ApprovalLog.objects.filter(
        content_type=content_type,
        object_id=entity_id
    ).select_related('user', 'from_status', 'to_status', 'action', 'post').order_by('-timestamp')
    
    # دریافت transition های ممکن
    current_status = entity.status if hasattr(entity, 'status') else None
    possible_transitions = []
    if current_status:
        # برای Factor باید از طریق tankhah به organization دسترسی پیدا کنیم
        if entity_type == 'factor':
            organization = entity.tankhah.organization
        else:  # tankhah
            organization = entity.organization
            
        possible_transitions = Transition.objects.filter(
            from_status=current_status,
            entity_type=entity_type_obj,
            organization=organization,
            is_active=True
        ).select_related('to_status', 'action')
    
    context = {
        'entity': entity,
        'entity_type': entity_type,
        'all_statuses': all_statuses,
        'approval_logs': approval_logs,
        'possible_transitions': possible_transitions,
        'current_status': current_status,
    }
    
    logger.debug(
        "[ADMIN_WF_CONTROL] Render context summary: current_status=%s total_statuses=%s possible_transitions=%s logs=%s",
        getattr(current_status, 'code', None), len(all_statuses), len(list(possible_transitions) or []), approval_logs.count()
    )

    return render(request, 'tankhah/admin_workflow_control.html', context)

@login_required
@permission_required('tankhah.admin_change_status', raise_exception=True)
@require_http_methods(["POST"])
def admin_change_status(request, entity_type, entity_id):
    """
    تغییر وضعیت موجودیت توسط ادمین
    """
    try:
        logger.debug("[ADMIN_CHANGE_STATUS][BEGIN] user=%s entity_type=%s entity_id=%s method=%s POST=%s",
                     getattr(request.user, 'username', None), entity_type, entity_id, request.method, dict(request.POST))
        with transaction.atomic():
            # پیدا کردن موجودیت
            if entity_type == 'factor':
                entity = get_object_or_404(Factor, id=entity_id)
            elif entity_type == 'tankhah':
                entity = get_object_or_404(Tankhah, id=entity_id)
            else:
                return JsonResponse({'success': False, 'message': 'نوع موجودیت نامعتبر است.'})
            
            new_status_id = request.POST.get('new_status_id')
            comment = request.POST.get('comment', 'تغییر وضعیت توسط ادمین')
            
            if not new_status_id:
                logger.warning("[ADMIN_CHANGE_STATUS][INVALID] missing new_status_id")
                return JsonResponse({'success': False, 'message': 'وضعیت جدید انتخاب نشده است.'})
            
            new_status = get_object_or_404(Status, id=new_status_id)
            old_status = entity.status if hasattr(entity, 'status') else None
            
            # تغییر وضعیت
            entity.status = new_status
            entity.save()
            
            # ثبت لاگ
            content_type = ContentType.objects.get(model=entity_type)
            # پیدا کردن یا ایجاد Action برای تغییر وضعیت توسط ادمین
            admin_change_action = Action.objects.filter(code='ADMIN_CHANGE').first()
            if not admin_change_action:
                admin_change_action = Action.objects.filter(is_active=True).first()
                if not admin_change_action:
                    admin_change_action = Action.objects.create(
                        name='تغییر وضعیت توسط ادمین',
                        code='ADMIN_CHANGE',
                        description='تغییر وضعیت توسط ادمین',
                        created_by=request.user
                    )
            
            ApprovalLog.objects.create(
                content_type=content_type,
                object_id=entity_id,
                from_status=old_status,
                to_status=new_status,
                action=admin_change_action,
                user=request.user,
                post=None,  # ادمین ممکن است پست نداشته باشد
                comment=comment,
                is_admin_action=True
            )
            
            logger.info(
                "[ADMIN_CHANGE_STATUS][OK] user=%s %s:%s %s->%s",
                getattr(request.user, 'username', None), entity_type, entity_id,
                getattr(old_status, 'code', None), getattr(new_status, 'code', None)
            )
            
            return JsonResponse({
                'success': True, 
                'message': f'وضعیت با موفقیت به {new_status.name} تغییر یافت.',
                'new_status': new_status.name
            })
            
    except Exception as e:
        logger.error("[ADMIN_CHANGE_STATUS][ERROR] %s", str(e), exc_info=True)
        return JsonResponse({'success': False, 'message': f'خطا در تغییر وضعیت: {str(e)}'})

@login_required
@permission_required('tankhah.admin_reset_workflow', raise_exception=True)
@require_http_methods(["POST"])
def admin_reset_workflow(request, entity_type, entity_id):
    """
    بازنشانی گردش کار به مرحله اول
    """
    try:
        logger.debug("[ADMIN_RESET_WF][BEGIN] user=%s entity_type=%s entity_id=%s method=%s POST=%s",
                     getattr(request.user, 'username', None), entity_type, entity_id, request.method, dict(request.POST))
        with transaction.atomic():
            # پیدا کردن موجودیت
            if entity_type == 'factor':
                entity = get_object_or_404(Factor, id=entity_id)
            elif entity_type == 'tankhah':
                entity = get_object_or_404(Tankhah, id=entity_id)
            else:
                return JsonResponse({'success': False, 'message': 'نوع موجودیت نامعتبر است.'})
            
            # پیدا کردن وضعیت اولیه
            entity_type_obj = EntityType.objects.get(code=entity_type.upper())
            initial_status = Status.objects.filter(
                is_initial=True,
                is_active=True
            ).first()
            
            if not initial_status:
                return JsonResponse({'success': False, 'message': 'وضعیت اولیه پیدا نشد.'})
            
            old_status = entity.status if hasattr(entity, 'status') else None
            
            # بازنشانی به وضعیت اولیه
            entity.status = initial_status
            entity.save()
            
            # حذف لاگ‌های قبلی (اختیاری)
            if request.POST.get('clear_logs') == 'true':
                content_type = ContentType.objects.get(model=entity_type)
                ApprovalLog.objects.filter(
                    content_type=content_type,
                    object_id=entity_id
                ).delete()
            
            # ثبت لاگ بازنشانی
            content_type = ContentType.objects.get(model=entity_type)
            # پیدا کردن یا ایجاد Action برای بازنشانی گردش کار توسط ادمین
            admin_reset_action = Action.objects.filter(code='ADMIN_RESET').first()
            if not admin_reset_action:
                admin_reset_action = Action.objects.filter(is_active=True).first()
                if not admin_reset_action:
                    admin_reset_action = Action.objects.create(
                        name='بازنشانی گردش کار توسط ادمین',
                        code='ADMIN_RESET',
                        description='بازنشانی گردش کار توسط ادمین',
                        created_by=request.user
                    )
            
            ApprovalLog.objects.create(
                content_type=content_type,
                object_id=entity_id,
                from_status=old_status,
                to_status=initial_status,
                action=admin_reset_action,
                user=request.user,
                post=None,
                comment='بازنشانی گردش کار توسط ادمین',
                is_admin_action=True
            )
            
            logger.info(
                "[ADMIN_RESET_WF][OK] user=%s %s:%s old=%s new=%s",
                getattr(request.user, 'username', None), entity_type, entity_id,
                getattr(old_status, 'code', None), getattr(initial_status, 'code', None)
            )
            
            return JsonResponse({
                'success': True, 
                'message': 'گردش کار با موفقیت بازنشانی شد.',
                'new_status': initial_status.name
            })
            
    except Exception as e:
        logger.error("[ADMIN_RESET_WF][ERROR] %s", str(e), exc_info=True)
        return JsonResponse({'success': False, 'message': f'خطا در بازنشانی گردش کار: {str(e)}'})

@login_required
@permission_required('tankhah.admin_workflow_dashboard', raise_exception=True)
def admin_workflow_dashboard(request):
    """
    داشبورد مدیریت گردش کار برای ادمین
    """
    # آمار کلی
    stats = {
        'total_factors': Factor.objects.count(),
        'pending_factors': Factor.objects.filter(status__is_initial=True).count(),
        'approved_factors': Factor.objects.filter(status__is_final_approve=True).count(),
        'rejected_factors': Factor.objects.filter(status__is_final_reject=True).count(),
        'total_tankhahs': Tankhah.objects.count(),
        'pending_tankhahs': Tankhah.objects.filter(status__is_initial=True).count(),
    }
    
    # فاکتورهای مسدود شده (در یک وضعیت بیش از 7 روز)
    from django.utils import timezone
    from datetime import timedelta
    
    blocked_factors = Factor.objects.filter(
        created_at__lt=timezone.now() - timedelta(days=7),
        status__is_final_approve=False,
        status__is_final_reject=False
    ).select_related('status', 'tankhah__organization')[:10]
    
    # آخرین فعالیت‌های ادمین
    admin_logs = ApprovalLog.objects.filter(
        is_admin_action=True
    ).select_related('user', 'from_status', 'to_status').order_by('-timestamp')[:10]
    
    # آمار وضعیت‌ها
    status_stats = Status.objects.filter(is_active=True).values('name', 'code', 'is_initial', 'is_final_approve', 'is_final_reject')
    
    # آمار transition ها
    transition_stats = Transition.objects.filter(is_active=True).count()
    
    # آمار سازمان‌ها
    organization_stats = {
        'total_organizations': Organization.objects.filter(is_active=True).count(),
        'core_organizations': Organization.objects.filter(is_core=True, is_active=True).count(),
    }
    
    context = {
        'stats': stats,
        'blocked_factors': blocked_factors,
        'admin_logs': admin_logs,
        'status_stats': status_stats,
        'transition_stats': transition_stats,
        'organization_stats': organization_stats,
    }
    
    return render(request, 'tankhah/admin_workflow_dashboard.html', context)
