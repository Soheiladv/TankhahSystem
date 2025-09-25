import logging
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import View, TemplateView
from django.http import JsonResponse
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q, Sum

from core.views import PermissionBaseView
from core.models import Organization, Status
from tankhah.models import Tankhah
from budgets.models import BudgetAllocation, BudgetTransaction, BudgetPeriod
from BudgetsSystem.utils import parse_jalali_date_jdate
from accounts.models import CustomUser

logger = logging.getLogger(__name__)


class ReturnExpiredTankhahBudgetView(PermissionBaseView, TemplateView):
    """
    ویو برای انتقال مانده بودجه تنخواه‌های منقضی به بودجه اصلی
    """
    template_name = 'tankhah/return_expired_budget.html'
    permission_codenames = ['tankhah.Tankhah_delete']
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # وضعیت نمایش: فقط منقضی‌ها یا همه (پیش‌فرض: فقط منقضی)
        expired_only = self.request.GET.get('expired_only', '1') == '1'
        
        # پیدا کردن تنخواه‌ها
        current_date = timezone.now().date()
        if expired_only:
            candidate_tankhahs = self._get_expired_tankhahs(user, current_date)
        else:
            candidate_tankhahs = self._get_all_tankhahs_with_remaining(user)

        # غنی سازی برای UI: هدف بازگشت و وضعیت دوره
        enriched = []
        total_remaining = Decimal('0')
        for t in candidate_tankhahs:
            remaining = t.get_remaining_budget() or Decimal('0')
            total_remaining += remaining
            bp = t.project_budget_allocation.budget_period if (t.project_budget_allocation and t.project_budget_allocation.budget_period) else None
            is_period_expired = False
            if bp:
                is_period_expired = (bp.end_date < current_date) or bool(bp.is_completed)
            return_target = 'org' if is_period_expired else 'project'
            enriched.append({
                'obj': t,
                'remaining': remaining,
                'budget_period': bp,
                'is_period_expired': is_period_expired,
                'return_target': return_target,
            })

        context.update({
            'expired_tankhahs': candidate_tankhahs,
            'expired_tankhahs_enriched': enriched,
            'total_remaining': total_remaining,
            'current_date': current_date,
            'title': _('انتقال مانده بودجه تنخواه‌های منقضی'),
            'expired_only': expired_only,
        })
        # recent RETURNs for selective rollback UI
        try:
            from datetime import timedelta
            recent_days = int(self.request.GET.get('recent_days', '30'))
            start_date = timezone.now().date() - timedelta(days=recent_days)
            recent_returns = BudgetTransaction.objects.filter(
                transaction_type='RETURN',
                related_tankhah__isnull=False,
                timestamp__date__gte=start_date
            ).select_related('related_tankhah', 'allocation', 'allocation__budget_period').order_by('-timestamp')[:200]
        except Exception:
            recent_returns = []
        context['recent_returns'] = recent_returns
        
        return context

    def _get_expired_tankhahs(self, user, current_date):
        """
        پیدا کردن تنخواه‌های منقضی بر اساس دسترسی کاربر
        """
        # تعیین دسترسی کاربر
        user_posts = user.userpost_set.filter(
            is_active=True, 
            end_date__isnull=True
        ).select_related('post__organization')
        
        user_org_pks = [up.post.organization.pk for up in user_posts if up.post and up.post.organization]
        is_hq_user = (
            user.is_superuser or
            user.has_perm('tankhah.Tankhah_view_all') or
            any(up.post.organization.org_type and up.post.organization.org_type.org_type == 'HQ'
                for up in user_posts if up.post and up.post.organization)
        )
        
        # فیلتر تنخواه‌ها
        if is_hq_user:
            queryset = Tankhah.objects.all()
        elif user_org_pks:
            queryset = Tankhah.objects.filter(organization__pk__in=user_org_pks)
        else:
            queryset = Tankhah.objects.none()
        
        # فیلتر تنخواه‌های منقضی
        expired_tankhahs = []
        for tankhah in queryset.filter(
            is_archived=False,
            project_budget_allocation__isnull=False
        ).select_related(
            'project_budget_allocation__budget_period',
            'organization',
            'project'
        ):
            if (tankhah.project_budget_allocation and 
                tankhah.project_budget_allocation.budget_period):
                
                budget_period = tankhah.project_budget_allocation.budget_period
                if (budget_period.end_date < current_date or 
                    budget_period.is_completed):
                    
                    remaining = tankhah.get_remaining_budget() or Decimal('0')
                    if remaining > 0:  # فقط تنخواه‌هایی که مانده دارند
                        expired_tankhahs.append(tankhah)
        
        return expired_tankhahs

    def _get_all_tankhahs_with_remaining(self, user):
        """
        تمام تنخواه‌های دارای مانده (صرف‌نظر از انقضا) بر اساس دسترسی کاربر
        """
        user_posts = user.userpost_set.filter(
            is_active=True,
            end_date__isnull=True
        ).select_related('post__organization')

        user_org_pks = [up.post.organization.pk for up in user_posts if up.post and up.post.organization]
        is_hq_user = (
            user.is_superuser or
            user.has_perm('tankhah.Tankhah_view_all') or
            any(up.post.organization.org_type and up.post.organization.org_type.org_type == 'HQ'
                for up in user_posts if up.post and up.post.organization)
        )

        if is_hq_user:
            queryset = Tankhah.objects.all()
        elif user_org_pks:
            queryset = Tankhah.objects.filter(organization__pk__in=user_org_pks)
        else:
            queryset = Tankhah.objects.none()

        result = []
        for tankhah in queryset.filter(
            is_archived=False,
            project_budget_allocation__isnull=False
        ).select_related(
            'project_budget_allocation__budget_period',
            'organization',
            'project'
        ):
            remaining = tankhah.get_remaining_budget() or Decimal('0')
            if remaining > 0:
                result.append(tankhah)
        return result

    def post(self, request, *args, **kwargs):
        """
        انجام انتقال بودجه
        """
        if not request.user.is_authenticated:
            messages.error(request, _('ابتدا وارد شوید.'))
            return redirect('login')
        
        try:
            # عملیات بازگردانی (لغو تراکنش‌های RETURN اخیر برای تست مجدد)
            action = request.POST.get('action')
            if action == 'rollback_returns':
                with transaction.atomic():
                    rollback_date_str = request.POST.get('rollback_date')
                    now = timezone.now()
                    current_date = now.date()
                    aggressive = request.POST.get('aggressive', '') == '1'
                    # اگر تاریخ وارد نشده بود، ۳۰ روز اخیر را رول‌بک کن تا تست ساده شود
                    if rollback_date_str:
                        target_date = parse_jalali_date_jdate(rollback_date_str)
                        qs = BudgetTransaction.objects.filter(
                            transaction_type='RETURN',
                            description__icontains='بازگشت مانده بودجه تنخواه منقضی',
                            timestamp__date=target_date
                        ).select_related('related_tankhah')
                        span_text = target_date.strftime('%Y/%m/%d')
                    else:
                        from datetime import timedelta
                        start_date = (now - timedelta(days=30)).date()
                        qs = BudgetTransaction.objects.filter(
                            transaction_type='RETURN',
                            description__icontains='بازگشت مانده بودجه تنخواه منقضی',
                            timestamp__date__gte=start_date
                        ).select_related('related_tankhah')
                        span_text = _('%(days)d روز اخیر') % {'days': 30}

                    count = qs.count()
                    # اگر چیزی پیدا نشد یا حالت گسترده روشن است، بر اساس لینک تنخواه هم حذف کن
                    if aggressive or count == 0:
                        if rollback_date_str:
                            fallback_qs = BudgetTransaction.objects.filter(
                                transaction_type='RETURN',
                                related_tankhah__isnull=False,
                                timestamp__date=target_date
                            )
                        else:
                            fallback_qs = BudgetTransaction.objects.filter(
                                transaction_type='RETURN',
                                related_tankhah__isnull=False,
                                timestamp__date__gte=start_date
                            )
                        count = fallback_qs.count()
                        qs = fallback_qs

                    ids = list(qs.values_list('id', flat=True))
                    qs.delete()
                    messages.success(request, _('{} تراکنش بازگشت مربوط به {} حذف شد و مانده‌ها بازیابی می‌شوند.').format(count, span_text))
                    logger.info(f"Rollback RETURN transactions ids={ids} span={span_text}")
                return redirect('return_expired_budget')

            if action == 'rollback_selected':
                with transaction.atomic():
                    ids = request.POST.getlist('tx_ids')
                    if not ids:
                        messages.warning(request, _('هیچ تراکنشی انتخاب نشد.'))
                        return redirect('return_expired_budget')
                    qs = BudgetTransaction.objects.filter(id__in=ids, transaction_type='RETURN')
                    count = qs.count()
                    qs.delete()
                    messages.success(request, _('{} تراکنش بازگشت انتخابی حذف شد و مانده‌ها بازیابی می‌شوند.').format(count))
                return redirect('return_expired_budget')

            if action == 'restore_selected':
                # ایجاد تراکنشِ جبرانی برای برگرداندن مانده بدون حذف سوابق
                with transaction.atomic():
                    ids = request.POST.getlist('tx_ids')
                    if not ids:
                        messages.warning(request, _('هیچ تراکنشی انتخاب نشد.'))
                        return redirect('return_expired_budget')
                    selected = BudgetTransaction.objects.filter(id__in=ids, transaction_type='RETURN').select_related('allocation', 'related_tankhah')
                    restored = 0
                    for tx in selected:
                        if not tx.allocation or not tx.related_tankhah:
                            continue
                        try:
                            BudgetTransaction.objects.create(
                                allocation=tx.allocation,
                                transaction_type='ADJUSTMENT',
                                amount=tx.amount,  # افزودن معادل مبلغ بازگشت‌خورده
                                created_by=request.user,
                                description=_('بازگردانی مانده جهت تست مجدد (جبران RETURN {})').format(tx.transaction_id),
                                related_tankhah=tx.related_tankhah,
                            )
                            # یادداشت روی تنخواه
                            t = tx.related_tankhah
                            t.description = (f"{t.description or ''}\n[بازگردانی آزمایشی: +{tx.amount:,.0f} ریال | مرجع: {tx.transaction_id}]").strip()
                            t.save()
                            restored += 1
                        except Exception as e:
                            logger.error(f"Restore adjustment failed for tx {tx.id}: {e}")
                    messages.success(request, _('{} مورد به‌صورت جبرانی برگردانده شد و در لیست ظاهر می‌شود.').format(restored))
                return redirect('return_expired_budget')

            with transaction.atomic():
                # پیدا کردن تنخواه‌های منقضی
                current_date = timezone.now().date()
                expired_tankhahs = self._get_expired_tankhahs(request.user, current_date)
                
                if not expired_tankhahs:
                    messages.warning(request, _('هیچ تنخواه منقضی‌ای یافت نشد.'))
                    return redirect('return_expired_budget')
                
                total_returned = Decimal('0')
                successful_returns = 0
                failed_returns = 0
                # جمع مبالغ بازگشتی به ازای هر سازمان برای ایجاد ردیف بودجه کلان
                org_to_return_sum = {}
                
                for tankhah in expired_tankhahs:
                    try:
                        remaining = tankhah.get_remaining_budget() or Decimal('0')
                        if remaining <= 0:
                            continue
                        
                        # تعیین مقصد بازگشت بر اساس وضعیت دوره بودجه
                        bp = tankhah.project_budget_allocation.budget_period if (tankhah.project_budget_allocation and tankhah.project_budget_allocation.budget_period) else None
                        is_period_expired = False
                        if bp:
                            is_period_expired = (bp.end_date < current_date) or bool(bp.is_completed)
                        # فقط تنخواه‌های منقضی را بازگردان
                        if not is_period_expired:
                            logger.info(f"Skip non-expired tankhah {tankhah.number} in return process")
                            continue
                        return_target = 'org'

                        # ایجاد تراکنش بازگشت بودجه با توضیح مقصد و تاریخ روز
                        self._create_budget_return_transaction(
                            tankhah=tankhah,
                            amount=remaining,
                            user=request.user,
                            return_target=return_target,
                            current_date=current_date,
                        )
                        
                        # به‌روزرسانی تنخواه
                        tankhah.description = (
                            f"{tankhah.description or ''}\n"
                            f"[بازگشت بودجه: {remaining:,.0f} ریال | مقصد: {'بودجه کلان سازمان' if return_target=='org' else 'بودجه پروژه'} | تاریخ: {current_date.strftime('%Y/%m/%d')}]"
                        ).strip()
                        tankhah.save()
                        
                        total_returned += remaining
                        successful_returns += 1
                        # جمع برای سازمان مربوط به تنخواه (برای ایجاد دوره بودجه کلان بازگشتی)
                        if tankhah.organization_id:
                            org_to_return_sum[tankhah.organization_id] = (
                                org_to_return_sum.get(tankhah.organization_id, Decimal('0')) + remaining
                            )
                        
                        logger.info(
                            f"بازگشت بودجه تنخواه {tankhah.number}: {remaining:,.0f} ریال | مقصد: {return_target}"
                        )
                        
                    except Exception as e:
                        logger.error(f"خطا در بازگشت بودجه تنخواه {tankhah.number}: {str(e)}")
                        failed_returns += 1
                        continue
                
                # ایجاد ردیف‌های بودجه کلان بازگشتی در صورت تقاضا
                try:
                    create_periods = request.POST.get('create_return_periods') == '1'
                    period_start = request.POST.get('period_start_date')
                    period_end = request.POST.get('period_end_date')
                    start_date = parse_jalali_date_jdate(period_start) if period_start else current_date
                    end_date = parse_jalali_date_jdate(period_end) if period_end else current_date
                    if create_periods and org_to_return_sum:
                        for org_id, sum_amount in org_to_return_sum.items():
                            try:
                                org = Organization.objects.get(pk=org_id)
                                name = _("بازگشت بودجه تنخواه – ") + current_date.strftime('%Y/%m/%d')
                                BudgetPeriod.objects.create(
                                    name=name,
                                    organization=org,
                                    total_amount=sum_amount,
                                    start_date=start_date,
                                    end_date=end_date,
                                    is_active=True,
                                )
                            except Exception as e_create:
                                logger.error(f"ایجاد دوره بودجه بازگشتی برای سازمان {org_id} ناموفق: {e_create}")
                                messages.warning(request, _('ایجاد ردیف بودجه بازگشتی برای یک سازمان ناموفق بود.'))
                except Exception as e_mod:
                    logger.error(f"خطا در ساخت ردیف‌های بودجه بازگشتی: {e_mod}")
                    messages.warning(request, _('ساخت ردیف‌های بودجه بازگشتی با خطا مواجه شد.'))

                # نمایش نتیجه
                if successful_returns > 0:
                    messages.success(
                        request, 
                        _('بودجه با موفقیت بازگردانده شد. تعداد: {} تنخواه، مبلغ کل: {} ریال').format(
                            successful_returns,
                            f"{total_returned:,.0f}"
                        )
                    )
                
                if failed_returns > 0:
                    messages.warning(
                        request, 
                        _('{} تنخواه با خطا مواجه شدند.').format(failed_returns)
                    )
                
                return redirect('return_expired_budget')
                
        except Exception as e:
            logger.error(f"خطای کلی در بازگشت بودجه: {str(e)}")
            messages.error(request, _('خطا در بازگشت بودجه. لطفاً دوباره تلاش کنید.'))
            return redirect('return_expired_budget')

    def _create_budget_return_transaction(self, tankhah, amount, user, return_target: str = 'project', current_date=None):
        """
        ایجاد تراکنش بازگشت بودجه
        """
        allocation = tankhah.project_budget_allocation
        
        # ایجاد تراکنش RETURN
        target_text = 'بودجه کلان سازمان' if return_target == 'org' else 'بودجه پروژه'
        date_text = current_date.strftime('%Y/%m/%d') if current_date else timezone.now().strftime('%Y/%m/%d')
        transaction = BudgetTransaction.objects.create(
            allocation=allocation,
            transaction_type='RETURN',
            amount=amount,
            created_by=user,
            description=(
                f"بازگشت مانده بودجه تنخواه منقضی {tankhah.number} | مقصد: {target_text} | تاریخ: {date_text}"
            ),
            related_tankhah=tankhah
        )
        
        logger.info(f"تراکنش بازگشت بودجه ایجاد شد: {transaction.transaction_id}")
        return transaction


class ReturnExpiredBudgetAPIView(PermissionBaseView, View):
    """
    API برای دریافت اطلاعات تنخواه‌های منقضی
    """
    permission_codenames = ['tankhah.Tankhah_view']
    check_organization = True

    def get(self, request):
        """
        دریافت لیست تنخواه‌های منقضی به صورت JSON
        """
        try:
            current_date = timezone.now().date()
            expired_tankhahs = self._get_expired_tankhahs(request.user, current_date)
            
            data = []
            total_remaining = Decimal('0')
            
            for tankhah in expired_tankhahs:
                remaining = tankhah.get_remaining_budget() or Decimal('0')
                total_remaining += remaining
                
                data.append({
                    'id': tankhah.id,
                    'number': tankhah.number,
                    'organization': tankhah.organization.name if tankhah.organization else '',
                    'project': tankhah.project.name if tankhah.project else '',
                    'amount': float(tankhah.amount),
                    'remaining': float(remaining),
                    'budget_period': tankhah.project_budget_allocation.budget_period.name if tankhah.project_budget_allocation and tankhah.project_budget_allocation.budget_period else '',
                    'budget_end_date': tankhah.project_budget_allocation.budget_period.end_date.isoformat() if tankhah.project_budget_allocation and tankhah.project_budget_allocation.budget_period else '',
                    'is_completed': tankhah.project_budget_allocation.budget_period.is_completed if tankhah.project_budget_allocation and tankhah.project_budget_allocation.budget_period else False,
                })
            
            return JsonResponse({
                'success': True,
                'tankhahs': data,
                'total_remaining': float(total_remaining),
                'count': len(data)
            })
            
        except Exception as e:
            logger.error(f"خطا در API بازگشت بودجه: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

    def _get_expired_tankhahs(self, user, current_date):
        """
        همان متد از کلاس اصلی
        """
        # تعیین دسترسی کاربر
        user_posts = user.userpost_set.filter(
            is_active=True, 
            end_date__isnull=True
        ).select_related('post__organization')
        
        user_org_pks = [up.post.organization.pk for up in user_posts if up.post and up.post.organization]
        is_hq_user = (
            user.is_superuser or
            user.has_perm('tankhah.Tankhah_view_all') or
            any(up.post.organization.org_type and up.post.organization.org_type.org_type == 'HQ'
                for up in user_posts if up.post and up.post.organization)
        )
        
        # فیلتر تنخواه‌ها
        if is_hq_user:
            queryset = Tankhah.objects.all()
        elif user_org_pks:
            queryset = Tankhah.objects.filter(organization__pk__in=user_org_pks)
        else:
            queryset = Tankhah.objects.none()
        
        # فیلتر تنخواه‌های منقضی
        expired_tankhahs = []
        for tankhah in queryset.filter(
            is_archived=False,
            project_budget_allocation__isnull=False
        ).select_related(
            'project_budget_allocation__budget_period',
            'organization',
            'project'
        ):
            if (tankhah.project_budget_allocation and 
                tankhah.project_budget_allocation.budget_period):
                
                budget_period = tankhah.project_budget_allocation.budget_period
                if (budget_period.end_date < current_date or 
                    budget_period.is_completed):
                    
                    remaining = tankhah.get_remaining_budget() or Decimal('0')
                    if remaining > 0:  # فقط تنخواه‌هایی که مانده دارند
                        expired_tankhahs.append(tankhah)
        
        return expired_tankhahs
