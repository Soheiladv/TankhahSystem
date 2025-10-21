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
    permission_codename = ['tankhah.Tankhah_update']
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # وضعیت نمایش: فقط منقضی‌ها یا همه (پیش‌فرض: فقط منقضی)
        expired_only = self.request.GET.get('expired_only', '1') == '1'
        # نمایش منقضی‌ها حتی با مانده صفر
        include_zero = self.request.GET.get('include_zero', '0') == '1'
        # فیلتر سازمان انتخاب‌شده (اختیاری)
        selected_org_id = self.request.GET.get('org_id')
        # فیلتر پروژه (اختیاری)
        selected_project_id = self.request.GET.get('project_id')
        try:
            selected_org_id = int(selected_org_id) if selected_org_id else None
        except Exception:
            selected_org_id = None
        try:
            selected_project_id = int(selected_project_id) if selected_project_id else None
        except Exception:
            selected_project_id = None
        
        # پیدا کردن تنخواه‌ها
        current_date = timezone.now().date()
        if expired_only:
            candidate_tankhahs = self._get_expired_tankhahs(user, current_date, selected_org_id=selected_org_id, selected_project_id=selected_project_id)
        else:
            candidate_tankhahs = self._get_all_tankhahs_with_remaining(user, selected_org_id=selected_org_id, selected_project_id=selected_project_id)

        # غنی سازی برای UI: هدف بازگشت و وضعیت دوره
        enriched = []
        total_remaining = Decimal('0')
        for t in candidate_tankhahs:
            remaining = t.get_remaining_budget() or Decimal('0')
            total_remaining += remaining
            bp = t.project_budget_allocation.budget_period if (t.project_budget_allocation and t.project_budget_allocation.budget_period) else None
            is_period_expired = False
            if bp:
                # دوره‌های با تاریخ پایان امروز نیز منقضی محسوب شوند
                is_period_expired = (bp.end_date <= current_date) or bool(bp.is_completed)
            return_target = 'org' if is_period_expired else 'project'
            enriched.append({
                'obj': t,
                'remaining': remaining,
                'budget_period': bp,
                'is_period_expired': is_period_expired,
                'return_target': return_target,
                'reason': None,
            })

        # حالت توضیحی: نمایش منقضی‌ها حتی با مانده صفر و موارد کنارگذاشته‌شده با دلیل
        items_to_show = enriched
        if include_zero and expired_only:
            verbose_list = []
            # دامنه دسترسی کاربر مانند قبل
            user_posts = user.userpost_set.filter(is_active=True).select_related('post__organization', 'post__organization__org_type')
            user_org_pks = [up.post.organization.pk for up in user_posts if up.post and up.post.organization]
            is_hq_user = (
                user.is_superuser or
                user.has_perm('tankhah.Tankhah_view_all') or
                any(up.post.organization.org_type and up.post.organization.org_type.org_type == 'HQ' for up in user_posts if up.post and up.post.organization)
            )
            base_qs = Tankhah.objects.all() if is_hq_user else Tankhah.objects.filter(organization__pk__in=user_org_pks)
            if selected_org_id:
                if is_hq_user or selected_org_id in user_org_pks:
                    base_qs = base_qs.filter(organization_id=selected_org_id)
            if selected_project_id:
                base_qs = base_qs.filter(project_id=selected_project_id)

            for t in base_qs.select_related('project_budget_allocation__budget_period', 'organization', 'project'):
                bp = t.project_budget_allocation.budget_period if (t.project_budget_allocation and t.project_budget_allocation.budget_period) else None
                if not bp:
                    continue
                is_period_expired = (bp.end_date <= current_date) or bool(bp.is_completed)
                if not is_period_expired:
                    continue
                remaining = t.get_remaining_budget() or Decimal('0')
                reason = None
                if t.is_archived:
                    reason = _('آرشیو شده')
                elif not t.project_budget_allocation:
                    reason = _('بدون تخصیص بودجه')
                elif remaining <= 0:
                    reason = _('مانده صفر')
                return_target = 'org' if is_period_expired else 'project'
                verbose_list.append({
                    'obj': t,
                    'remaining': remaining,
                    'budget_period': bp,
                    'is_period_expired': is_period_expired,
                    'return_target': return_target,
                    'reason': reason,
                })
            items_to_show = verbose_list

        # تخصیص‌های منقضی با مانده بلااستفاده (برای بازگشت مستقیم قبل از تنخواه)
        expired_allocations_verbose = []
        try:
            from tankhah.models import Tankhah as _Tankhah
            alloc_qs = BudgetAllocation.objects.select_related('budget_period', 'organization', 'project').filter(
                budget_period__isnull=False,
                budget_period__end_date__lte=current_date,
                is_active=True
            ) | BudgetAllocation.objects.select_related('budget_period', 'organization', 'project').filter(
                budget_period__isnull=False,
                budget_period__is_completed=True,
                is_active=True
            )
            if selected_org_id:
                alloc_qs = alloc_qs.filter(organization_id=selected_org_id)
            if selected_project_id:
                alloc_qs = alloc_qs.filter(project_id=selected_project_id)

            for alloc in alloc_qs:
                # محاسبه مانده واقعی تخصیص
                tx_sum = alloc.transactions.aggregate(
                    consumption=Sum('amount', filter=Q(transaction_type='CONSUMPTION')),
                    returns=Sum('amount', filter=Q(transaction_type='RETURN')),
                    adj_inc=Sum('amount', filter=Q(transaction_type='ADJUSTMENT_INCREASE')),
                    adj_dec=Sum('amount', filter=Q(transaction_type='ADJUSTMENT_DECREASE')),
                )
                from decimal import Decimal as _D
                # برای جلوگیری از بازگشت دوباره: بازگشت‌ها را در مانده لحاظ نکنیم
                gross_spent = (tx_sum['consumption'] or _D('0')) + (tx_sum['adj_dec'] or _D('0'))
                remaining_alloc = alloc.allocated_amount - gross_spent
                if remaining_alloc <= 0:
                    continue
                # آیا تنخواهی به این تخصیص وصل شده است؟
                has_tankhah = _Tankhah.objects.filter(project_budget_allocation=alloc).exists()
                expired_allocations_verbose.append({
                    'allocation': alloc,
                    'remaining': remaining_alloc,
                    'has_tankhah': has_tankhah,
                    'budget_period': alloc.budget_period,
                    'organization': alloc.organization,
                    'project': alloc.project,
                })
        except Exception as e:
            logger.error(f"Error preparing expired allocations list: {e}")

        # گزینه‌های سازمان برای فیلتر (HQ: همه سازمان‌ها؛ شعبه: فقط سازمان‌های خودش)
        user_posts = user.userpost_set.filter(is_active=True).select_related('post__organization', 'post__organization__org_type')
        user_orgs = [up.post.organization for up in user_posts if up.post and up.post.organization]
        is_hq_user = (
            user.is_superuser or
            user.has_perm('tankhah.Tankhah_view_all') or
            any(up.post.organization.org_type and up.post.organization.org_type.org_type == 'HQ' for up in user_posts if up.post and up.post.organization)
        )
        org_options = Organization.objects.all().order_by('name') if is_hq_user else Organization.objects.filter(pk__in=[o.pk for o in user_orgs]).order_by('name')

        context.update({
            'expired_tankhahs': candidate_tankhahs,
            'expired_tankhahs_enriched': enriched,
            'items_to_show': items_to_show,
            'expired_allocations': expired_allocations_verbose,
            'total_remaining': total_remaining,
            'current_date': current_date,
            'title': _('انتقال مانده بودجه تنخواه‌های منقضی'),
            'expired_only': expired_only,
            'include_zero': include_zero,
            'org_options': org_options,
            'selected_org_id': selected_org_id,
            'selected_project_id': selected_project_id,
            'is_hq_user': is_hq_user,
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

    def _get_expired_tankhahs(self, user, current_date, selected_org_id=None, selected_project_id=None):
        """
        پیدا کردن تنخواه‌های منقضی بر اساس دسترسی کاربر
        """
        # تعیین دسترسی کاربر
        user_posts = user.userpost_set.filter(
            is_active=True
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

        if selected_org_id:
            # HQ نامحدود؛ کاربران شعبه فقط اگر سازمان در لیست دسترسی‌شان باشد
            if is_hq_user or selected_org_id in user_org_pks:
                queryset = queryset.filter(organization_id=selected_org_id)
        if selected_project_id:
            queryset = queryset.filter(project_id=selected_project_id)
        
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
                if (budget_period.end_date <= current_date or 
                    budget_period.is_completed):
                    
                    remaining = tankhah.get_remaining_budget() or Decimal('0')
                    if remaining > 0:  # فقط تنخواه‌هایی که مانده دارند
                        expired_tankhahs.append(tankhah)
        
        return expired_tankhahs

    def _get_all_tankhahs_with_remaining(self, user, selected_org_id=None, selected_project_id=None):
        """
        تمام تنخواه‌های دارای مانده (صرف‌نظر از انقضا) بر اساس دسترسی کاربر
        """
        user_posts = user.userpost_set.filter(
            is_active=True
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

        if selected_org_id:
            if is_hq_user or selected_org_id in user_org_pks:
                queryset = queryset.filter(organization_id=selected_org_id)
        if selected_project_id:
            queryset = queryset.filter(project_id=selected_project_id)

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
            # بازگشت مستقیم مانده تخصیص‌های منقضی قبل از تنخواه
            if request.POST.get('action') == 'return_allocations':
                from decimal import Decimal as _D
                ids = request.POST.getlist('allocation_ids')
                if not ids:
                    messages.warning(request, _('هیچ تخصیصی انتخاب نشد.'))
                    return redirect('return_expired_budget')
                with transaction.atomic():
                    selected = BudgetAllocation.objects.filter(id__in=ids).select_related('budget_period', 'organization')
                    total = _D('0')
                    success = 0
                    failed = 0
                    for alloc in selected:
                        try:
                            # بازمحاسبه مانده
                            s = alloc.transactions.aggregate(
                                consumption=Sum('amount', filter=Q(transaction_type='CONSUMPTION')),
                                returns=Sum('amount', filter=Q(transaction_type='RETURN')),
                                adj_inc=Sum('amount', filter=Q(transaction_type='ADJUSTMENT_INCREASE')),
                                adj_dec=Sum('amount', filter=Q(transaction_type='ADJUSTMENT_DECREASE')),
                            )
                            # مصرف خالص بدون لحاظ بازگشت‌ها/افزایش‌ها
                            gross_spent = (s['consumption'] or _D('0')) + (s['adj_dec'] or _D('0'))
                            remaining_alloc = alloc.allocated_amount - gross_spent
                            if remaining_alloc <= 0:
                                continue
                            # ثبت RETURN با مقصد بودجه کلان سازمان (بدون تنخواه مرتبط)
                            BudgetTransaction.objects.create(
                                allocation=alloc,
                                transaction_type='RETURN',
                                amount=remaining_alloc,
                                created_by=request.user,
                                description=_('بازگشت مستقیم مانده تخصیص منقضی به بودجه کلان (بدون تنخواه)'),
                            )
                            total += remaining_alloc
                            success += 1
                        except Exception as e:
                            logger.error(f"Direct return failed for allocation {alloc.id}: {e}")
                            failed += 1
                    if success:
                        base_msg = _('{} تخصیص بازگشت خورد. جمع: {} ریال').format(success, f"{total:,.0f}")
                        if failed:
                            base_msg += _(' | {} مورد ناموفق').format(failed)
                        messages.success(request, base_msg)
                    else:
                        if failed:
                            messages.error(request, _('هیچ تخصیصی بازگشت نخورد و برخی با خطا مواجه شدند.'))
                        else:
                            messages.info(request, _('تخصیص واجد شرایطی برای بازگشت یافت نشد.'))
                return redirect('return_expired_budget')
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
                        bp = (
                            tankhah.project_budget_allocation.budget_period
                            if (tankhah.project_budget_allocation and tankhah.project_budget_allocation.budget_period)
                            else None
                        )
                        is_period_expired = False
                        if bp:
                            is_period_expired = (bp.end_date <= current_date) or bool(bp.is_completed)
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
    permission_codename = ['tankhah.Tankhah_view']
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
