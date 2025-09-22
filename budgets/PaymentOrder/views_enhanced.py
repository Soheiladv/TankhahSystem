"""
ویوهای پیشرفته مدیریت دستورات پرداخت
شامل: مدیریت، تایید، آرشیو و آمار
"""
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError, PermissionDenied
from django.shortcuts import  get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from django.views.generic import ListView, DetailView, UpdateView, View
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
import json

from budgets.PaymentOrder.form_PaymentOrder import PaymentOrderApprovalForm, PaymentOrderForm
from core.PermissionBase import PermissionBaseView
from budgets.models import PaymentOrder
from tankhah.models import Factor, ApprovalLog
from core.models import Status, UserPost, Organization, Transition, Action, EntityType
from notificationApp.utils import send_notification

logger = logging.getLogger(__name__)

# ===================================================================
# API برای دریافت گذارهای مجاز کاربر (با جستجو و صفحه‌بندی)
# ===================================================================
@login_required
def paymentorder_transitions_api(request):
    """
    API برای دریافت گذارهای مجاز کاربر برای دستور پرداخت
    با قابلیت جستجو و صفحه‌بندی برای کاهش حجم داده‌ها
    
    پارامترهای ورودی:
    - po_id: شناسه دستور پرداخت (اجباری)
    - q: عبارت جستجو (اختیاری)
    - page: شماره صفحه (پیش‌فرض: 1)
    - page_size: تعداد آیتم در هر صفحه (پیش‌فرض: 20)
    
    خروجی: JSON شامل لیست گذارهای مجاز با اطلاعات مورد نیاز
    """
    try:
        # دریافت پارامترهای ورودی
        po_id = request.GET.get('po_id')
        if not po_id:
            return JsonResponse({'error': 'شناسه دستور پرداخت الزامی است'}, status=400)
        
        q = request.GET.get('q', '').strip()
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 20)), 100)  # حداکثر 100 آیتم
        
        # دریافت دستور پرداخت و بررسی دسترسی
        payment_order = get_object_or_404(PaymentOrder, pk=po_id)
        user = request.user
        
        logger.info(
            f"[TRANSITIONS_API] User={user.username} requesting transitions for "
            f"PaymentOrder={payment_order.order_number} (status={payment_order.status.code})"
        )
        
        # دریافت EntityType مربوط به PaymentOrder
        ct = ContentType.objects.get_for_model(PaymentOrder)
        entity_type = EntityType.objects.filter(content_type=ct).first() or EntityType.objects.filter(code='PAYMENTORDER').first()
        
        if not entity_type:
            logger.warning(f"[TRANSITIONS_API] No EntityType found for PaymentOrder")
            return JsonResponse({'results': [], 'total': 0, 'page': page})
        
        # دریافت پست‌های فعال کاربر
        user_posts = user.userpost_set.filter(is_active=True).values_list('post_id', flat=True)
        
        # فیلتر پایه برای گذارهای مجاز
        base_queryset = Transition.objects.filter(
            entity_type=entity_type,
            from_status=payment_order.status,
            organization=payment_order.organization,
            is_active=True,
        )
        
        # محدود کردن بر اساس پست‌های کاربر (مگر ادمین/استف)
        if not (user.is_superuser or user.is_staff):
            base_queryset = base_queryset.filter(
                Q(allowed_posts__in=user_posts) | Q(allowed_posts__isnull=True)
            )
        
        # اعمال فیلتر جستجو
        if q:
            base_queryset = base_queryset.filter(
                Q(name__icontains=q) | 
                Q(action__name__icontains=q) | 
                Q(to_status__name__icontains=q)
            )
        
        # بهینه‌سازی کوئری و حذف تکراری‌ها
        base_queryset = base_queryset.select_related('action', 'to_status').distinct()
        
        # محاسبه تعداد کل
        total_count = base_queryset.count()
        
        # صفحه‌بندی
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        transitions = base_queryset[start_index:end_index]
        
        # تبدیل به فرمت مورد نیاز Select2
        results = []
        for transition in transitions:
            results.append({
                'id': transition.id,
                'text': f"{transition.action.name} → {transition.to_status.name}",
                'action_name': transition.action.name,
                'to_status_name': transition.to_status.name,
                'transition_name': transition.name
            })
        
        # محاسبه آیا صفحه بعدی وجود دارد
        has_more = total_count > end_index
        
        logger.debug(
            f"[TRANSITIONS_API] Found {len(results)} transitions for user={user.username}, "
            f"total={total_count}, page={page}, has_more={has_more}"
        )
        
        return JsonResponse({
            'results': results,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'has_more': has_more
        })
        
    except ValueError as e:
        logger.error(f"[TRANSITIONS_API_ERROR] Invalid parameter: {e}")
        return JsonResponse({'error': 'پارامترهای ورودی نامعتبر است'}, status=400)
    except Exception as e:
        logger.error(f"[TRANSITIONS_API_ERROR] Unexpected error: {e}", exc_info=True)
        return JsonResponse({'error': 'خطای پیش‌بینی نشده در سرور'}, status=500)
# ==========================================
class PaymentOrderManagementListView(PermissionBaseView, ListView):
    """
    لیست پیشرفته دستورات پرداخت برای مدیریت
    """
    model = PaymentOrder
    template_name = 'budgets/paymentorder/management_list_enhanced.html'
    context_object_name = 'payment_orders'
    permission_codename = 'budgets.PaymentOrder_view'
    check_organization = True
    paginate_by = 20

    def get_queryset(self):
        """فیلتر کردن دستورات بر اساس پارامترهای جستجو"""
        queryset = super().get_queryset()

        # فیلتر جستجو
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(description__icontains=search) |
                Q(payee__name__icontains=search)
            )

        # فیلتر وضعیت
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status__code=status)

        # فیلتر سازمان
        organization = self.request.GET.get('organization', '')
        if organization:
            queryset = queryset.filter(organization_id=organization)

        # فیلتر تاریخ
        date_from = self.request.GET.get('date_from', '')
        if date_from:
            queryset = queryset.filter(issue_date__gte=date_from)

        date_to = self.request.GET.get('date_to', '')
        if date_to:
            queryset = queryset.filter(issue_date__lte=date_to)

        # فیلتر آرشیو
        show_archived = self.request.GET.get('show_archived', 'false')
        if show_archived == 'true':
            queryset = queryset.filter(is_archived=True)
        else:
            queryset = queryset.filter(is_archived=False)

        # مرتب‌سازی
        sort = self.request.GET.get('sort', '-created_at')
        queryset = queryset.order_by(sort)

        return queryset.select_related(
            'status', 'payee', 'organization', 'created_by'
        ).prefetch_related('related_factors')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # آمار کلی
        queryset = self.get_queryset()
        context['stats'] = {
            'total': queryset.count(),
            'pending': queryset.filter(status__code='PO_DRAFT').count(),
            'approved': queryset.filter(status__code='PO_APPROVED').count(),
            'paid': queryset.filter(status__code='PO_PAID').count(),
            'archived': queryset.filter(is_archived=True).count(),
        }

        # گزینه‌های فیلتر
        context['status_choices'] = Status.objects.filter(
            is_active=True,
            code__startswith='PO_'
        ).values('code', 'name')

        context['organization_choices'] = Organization.objects.filter(
            is_active=True
        ).values('id', 'name')

        # پارامترهای فیلتر
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        context['organization'] = self.request.GET.get('organization', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['show_archived'] = self.request.GET.get('show_archived', 'false')
        context['sort'] = self.request.GET.get('sort', '-created_at')

        return context
# ==========================================

class PaymentOrderDetailView(PermissionBaseView, DetailView):
    """
    جزئیات کامل دستور پرداخت
    """
    model = PaymentOrder
    template_name = 'budgets/paymentorder/detail_enhanced.html'
    context_object_name = 'payment_order'
    permission_codename = 'budgets.PaymentOrder_view'
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_order = self.get_object()

        from django.contrib.contenttypes.models import ContentType
        payment_order_content_type = ContentType.objects.get_for_model(payment_order)
        context['approval_logs'] = ApprovalLog.objects.filter(
            content_type=payment_order_content_type,
            object_id=payment_order.id
        ).order_by('-timestamp')
        context['can_approve'] = self._check_approval_permission()
        context['can_archive'] = payment_order.can_be_archived()
        context['related_factors'] = payment_order.related_factors.all()

        # آمار فاکتورها
        context['factors_stats'] = {
            'total_count': payment_order.related_factors.count(),
            'total_amount': payment_order.related_factors.aggregate(
                total=Sum('amount')
            )['total'] or 0
        }

        return context

    def _check_approval_permission(self):
        """بررسی دسترسی کاربر برای تایید"""
        user = self.request.user
        payment_order = self.get_object()

        user_posts = UserPost.objects.filter(user=user, is_active=True)
        if not user_posts.exists():
            return False

        user_orgs = user_posts.values_list('post__organization__pk', flat=True)
        return payment_order.organization.pk in user_orgs
# ==========================================
class PaymentOrderArchiveView(PermissionBaseView, View):
    """
    ویو آرشیو کردن دستورات پرداخت
    """
    permission_codename = 'budgets.PaymentOrder_archive'
    check_organization = True

    def post(self, request, pk):
        payment_order = get_object_or_404(PaymentOrder, pk=pk)

        if not payment_order.can_be_archived():
            return JsonResponse({
                'success': False,
                'message': 'این دستور پرداخت قابل آرشیو نیست.'
            })

        try:
            payment_order.archive(request.user)
            return JsonResponse({
                'success': True,
                'message': 'دستور پرداخت با موفقیت آرشیو شد.'
            })
        except Exception as e:
            logger.error(f"خطا در آرشیو دستور پرداخت: {e}")
            return JsonResponse({
                'success': False,
                'message': 'خطا در آرشیو دستور پرداخت.'
            })
# ==========================================
class PaymentOrderUnarchiveView(PermissionBaseView, View):
    """
    ویو خارج کردن دستورات پرداخت از آرشیو
    """
    permission_codename = 'budgets.PaymentOrder_archive'
    check_organization = True

    def post(self, request, pk):
        payment_order = get_object_or_404(PaymentOrder, pk=pk)

        try:
            payment_order.unarchive()
            return JsonResponse({
                'success': True,
                'message': 'دستور پرداخت با موفقیت از آرشیو خارج شد.'
            })
        except Exception as e:
            logger.error(f"خطا در خارج کردن از آرشیو: {e}")
            return JsonResponse({
                'success': False,
                'message': 'خطا در خارج کردن از آرشیو.'
            })
# ==========================================
class PaymentOrderBulkArchiveView(PermissionBaseView, View):
    """
    ویو آرشیو دسته‌ای دستورات پرداخت
    """
    permission_codename = 'budgets.PaymentOrder_archive'
    check_organization = True

    def post(self, request):
        try:
            data = json.loads(request.body)
            payment_order_ids = data.get('payment_order_ids', [])
            action = data.get('action', 'archive')

            if not payment_order_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'هیچ دستور پرداختی انتخاب نشده است.'
                })

            payment_orders = PaymentOrder.objects.filter(
                pk__in=payment_order_ids,
                organization__in=self.get_user_active_organizations(request.user)
            )

            success_count = 0
            error_count = 0

            for payment_order in payment_orders:
                try:
                    if action == 'archive' and payment_order.can_be_archived():
                        payment_order.archive(request.user)
                        success_count += 1
                    elif action == 'unarchive' and payment_order.is_archived:
                        payment_order.unarchive()
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    logger.error(f"خطا در {action} دستور پرداخت {payment_order.pk}: {e}")
                    error_count += 1

            return JsonResponse({
                'success': True,
                'message': f'{success_count} دستور پرداخت با موفقیت {action} شد. {error_count} مورد خطا داشت.'
            })

        except Exception as e:
            logger.error(f"خطا در عملیات دسته‌ای: {e}")
            return JsonResponse({
                'success': False,
                'message': 'خطا در انجام عملیات دسته‌ای.'
            })
# ==========================================
class PaymentOrderStatsView(PermissionBaseView, ListView):
    """
    ویو آمار و گزارشات دستورات پرداخت
    """
    model = PaymentOrder
    template_name = 'budgets/paymentorder/stats.html'
    permission_codename = 'budgets.PaymentOrder_view'
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        # آمار کلی
        total_count = queryset.count()
        total_amount = queryset.aggregate(total=Sum('amount'))['total'] or 0

        # آمار بر اساس وضعیت
        by_status = queryset.values('status__name').annotate(
            count=Count('id'),
            amount=Sum('amount')
        )

        # آمار بر اساس سازمان
        by_organization = queryset.values('organization__name').annotate(
            count=Count('id'),
            amount=Sum('amount')
        )

        # آمار ماهانه - با مدیریت خطای timezone
        from django.db.models.functions import TruncMonth
        from django.db import connection

        try:
            # تلاش برای استفاده از TruncMonth
            by_month = queryset.annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                count=Count('id'),
                amount=Sum('amount')
            ).order_by('month')
            logger.info(f'by_month is {by_month}')
            # تست کردن کوئری با اجرای آن
            list(by_month)

        except (ValueError, Exception) as e:
            # در صورت خطا، از روش raw SQL استفاده می‌کنیم
            logger.warning(f"خطا در TruncMonth، استفاده از raw SQL: {e}")

            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        DATE_FORMAT(created_at, '%%Y-%%m') as month,
                        COUNT(*) as count,
                        COALESCE(SUM(amount), 0) as amount
                    FROM budgets_paymentorder 
                    WHERE created_at IS NOT NULL 
                        AND created_at != '0000-00-00 00:00:00'
                        AND created_at != '1970-01-01 00:00:00'
                    GROUP BY DATE_FORMAT(created_at, '%%Y-%%m')
                    ORDER BY month
                """)

                results = cursor.fetchall()
                by_month = [
                    {
                        'month': row[0],
                        'count': row[1],
                        'amount': float(row[2]) if row[2] else 0
                    }
                    for row in results
                ]
        # محاسبه آمار وضعیت‌های مختلف
        pending_count = queryset.filter(status__code='PENDING').count()
        approved_count = queryset.filter(status__code='APPROVED').count()
        paid_count = queryset.filter(status__code='PAID').count()
        archived_count = queryset.filter(is_archived=True).count()

        context['stats'] = {
            'total': total_count,
            'pending': pending_count,
            'approved': approved_count,
            'paid': paid_count,
            'archived': archived_count,
            'total_amount': total_amount,
            'by_status': by_status,
            'by_organization': by_organization,
            'by_month': by_month
        }

        return context
# ==========================================
@login_required
def create_payment_orders_from_factors(request):
    """
    ایجاد دستورات پرداخت از فاکتورهای تایید نهایی
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'این متد در دسترسی نیست '})

    try:
        # دریافت فاکتورهای تایید نهایی که هنوز دستور پرداخت ندارند
        approved_factors = Factor.objects.filter(
            status__code='FACTOR_APPROVED',
            is_archived=False
        ).exclude(
            payment_orders__isnull=False
        ).select_related('organization', 'created_by', 'tankhah')

        if not approved_factors.exists():
            return JsonResponse({
                'success': False,
                'message': 'هیچ فاکتور تایید نهایی بدون دستور پرداخت یافت نشد.'
            })

        created_orders = []

        with transaction.atomic():
            # گروه‌بندی فاکتورها بر اساس سازمان
            factors_by_org = {}
            for factor in approved_factors:
                org_id = factor.organization.pk
                if org_id not in factors_by_org:
                    factors_by_org[org_id] = []
                factors_by_org[org_id].append(factor)

            # ایجاد دستور پرداخت برای هر سازمان
            for org_id, factors in factors_by_org.items():
                organization = factors[0].organization
                total_amount = sum(factor.amount for factor in factors)

                # پیدا کردن تنخواه مرتبط (اولین فاکتور)
                tankhah = factors[0].tankhah if factors[0].tankhah else None

                # پیدا کردن دریافت‌کننده (اولین فاکتور)
                payee = None
                for factor in factors:
                    if hasattr(factor, 'payee') and factor.payee:
                        payee = factor.payee
                        break

                # ایجاد دستور پرداخت
                payment_order = PaymentOrder.objects.create(
                    order_number=f"PO-{timezone.now().strftime('%Y%m%d%H%M%S')}-{org_id}",
                    organization=organization,
                    tankhah=tankhah,
                    related_tankhah=tankhah,
                    amount=total_amount,
                    payee=payee,
                    description=f"دستور پرداخت برای {len(factors)} فاکتور تایید نهایی",
                    created_by=request.user,
                    status=Status.objects.filter(code='PO_DRAFT').first(),
                    issue_date=timezone.now().date()
                )

                # اتصال فاکتورها
                payment_order.related_factors.set(factors)

                created_orders.append(payment_order)

                # ثبت لاگ
                from django.contrib.contenttypes.models import ContentType
                from core.models import Action
                payment_order_content_type = ContentType.objects.get_for_model(payment_order)
                action = Action.objects.filter(code='CREATED').first()

                ApprovalLog.objects.create(
                    content_type=payment_order_content_type,
                    object_id=payment_order.id,
                    to_status=payment_order.status,
                    action=action,
                    user=request.user,
                    comment=f'ایجاد شده از {len(factors)} فاکتور تایید نهایی'
                )

                # ارسال اعلان به کاربران مرتبط
                send_notification(
                    sender=request.user,
                    users=[factor.tankhah.created_by for factor in factors if
                           factor.tankhah and factor.tankhah.created_by],
                    verb='PAYMENTORDER_CREATED',
                    description=f"دستور پرداخت {payment_order.order_number} برای فاکتورهای شما ایجاد شد.",
                    target=payment_order,
                    entity_type='PAYMENTORDER',
                    priority='HIGH'
                )

        return JsonResponse({
            'success': True,
            'message': f'{len(created_orders)} دستور پرداخت ایجاد شد.',
            'created_orders': [order.order_number for order in created_orders]
        })

    except Exception as e:
        logger.error(f"خطا در ایجاد دستورات پرداخت از فاکتورها: {e}")
        return JsonResponse({
            'success': False,
            'message': 'خطا در ایجاد دستورات پرداخت.'
        })
# ===== IMPORTS & DEPENDENCIES =====
class ApprovedFactorsListView(PermissionBaseView, ListView):
    """
    لیست فاکتورهای تایید نهایی برای ایجاد دستور پرداخت
    """
    model = Factor
    template_name = 'budgets/paymentorder/approved_factors_list.html'
    context_object_name = 'approved_factors'
    permission_codename = 'budgets.PaymentOrder_view'
    check_organization = True
    paginate_by = 20

    def get_user_active_organizations(self, user):
        """
        Returns a list of organization IDs the user has access to.
        """
        from core.models import UserPost
        org_ids = UserPost.objects.filter(
            user=user, is_active=True, end_date__isnull=True
        ).values_list('post__organization__id', flat=True).distinct()
        logger.debug(f"User {user.username} has access to organizations: {list(org_ids)}")
        return org_ids

    def get_queryset(self):
        """
        فیلتر فاکتورهای تایید نهایی که هنوز دستور پرداخت ندارند.

        Returns:
            QuerySet: Filtered queryset of approved factors.
        """
        queryset = Factor.objects.filter(
            status__code='FACTOR_APPROVED',
            is_locked=False
        ).exclude(
            payment_orders__isnull=False
        ).select_related(
            'created_by', 'tankhah', 'tankhah__organization', 'status'
        ).prefetch_related('payment_orders')

        # فیلتر سازمانی
        user_orgs = self.get_user_active_organizations(self.request.user)
        if not user_orgs:
            logger.warning(f"No active organizations found for user {self.request.user.username}")
            return queryset.none()  # بازگشت کوئری خالی در صورت عدم دسترسی

        queryset = queryset.filter(tankhah__organization_id__in=user_orgs)

        # فیلتر جستجو
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(factor_number__icontains=search) |
                Q(number__icontains=search) |
                Q(description__icontains=search) |
                Q(tankhah__number__icontains=search)
            )
            logger.debug(f"Applied search filter: {search}")

        # فیلتر سازمان
        organization = self.request.GET.get('organization', '')
        if organization:
            try:
                queryset = queryset.filter(tankhah__organization_id=organization)
                logger.debug(f"Applied organization filter: {organization}")
            except ValueError:
                logger.warning(f"Invalid organization ID: {organization}")

        # فیلتر تاریخ
        date_from = self.request.GET.get('date_from', '')
        if date_from:
            try:
                queryset = queryset.filter(created_at__gte=date_from)
                logger.debug(f"Applied date_from filter: {date_from}")
            except ValueError:
                logger.warning(f"Invalid date_from: {date_from}")

        date_to = self.request.GET.get('date_to', '')
        if date_to:
            try:
                queryset = queryset.filter(created_at__lte=date_to)
                logger.debug(f"Applied date_to filter: {date_to}")
            except ValueError:
                logger.warning(f"Invalid date_to: {date_to}")

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        """
        اضافه کردن داده‌های اضافی به context برای رندر قالب.

        Returns:
            dict: Context data including statistics and filter options.
        """
        context = super().get_context_data(**kwargs)

        # آمار فاکتورهای تایید نهایی
        queryset = self.get_queryset()
        try:
            context['stats'] = {
                'total': queryset.count(),
                'total_amount': queryset.aggregate(total=Sum('amount'))['total'] or 0,
                'by_organization': queryset.values('tankhah__organization__name').annotate(
                    count=Count('id'),
                    amount=Sum('amount')
                )
            }
            logger.debug(f"Calculated stats: {context['stats']}")
        except Exception as e:
            logger.error(f"Error calculating stats: {str(e)}", exc_info=True)
            context['stats'] = {'total': 0, 'total_amount': 0, 'by_organization': []}

        # گزینه‌های فیلتر
        try:
            context['organization_choices'] = Organization.objects.filter(
                is_active=True
            ).values('id', 'name')
        except Exception as e:
            logger.error(f"Error fetching organization choices: {str(e)}", exc_info=True)
            context['organization_choices'] = []

        # پارامترهای فیلتر
        context['search'] = self.request.GET.get('search', '')
        context['organization'] = self.request.GET.get('organization', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')

        return context

    @staticmethod
    def execute_transition(payment_order, action_code, user):
        """
        اجرای گذار برای تغییر وضعیت دستور پرداخت.

        Args:
            payment_order: شیء PaymentOrder
            action_code: کد اقدام (مانند SUBMIT، APPROVE)
            user: کاربر انجام‌دهنده اقدام

        Raises:
            PermissionError: اگر گذار مجاز نباشد
        """
        transition = Transition.objects.filter(
            entity_type__code='PAYMENTORDER',
            from_status=payment_order.status,
            action__code=action_code,
            allowed_posts__in=user.userpost_set.filter(is_active=True).values_list('post', flat=True)
        ).first()
        if transition:
            payment_order.status = transition.to_status
            payment_order.save()
            # ثبت لاگ در ApprovalLog
            ApprovalLog.objects.create(
                content_type=ContentType.objects.get_for_model(payment_order),
                object_id=payment_order.id,
                to_status=transition.to_status,
                action=transition.action,
                user=user,
                comment=f"Transitioned via {action_code}"
            )
        else:
            logger.error(f"Transition not allowed for action {action_code} by user {user.username}")
            raise PermissionError("گذار مجاز نیست")
# ==========================================
# ===== CORE BUSINESS LOGIC =====
class PaymentOrderApprovalView(PermissionBaseView , UpdateView):
    """ویو تأیید یا رد دستور پرداخت (دو فرم: اطلاعات + تأیید وضعیت)"""
    model = PaymentOrder
    form_class = PaymentOrderApprovalForm
    template_name = "budgets/paymentorder/approval_form.html"
    # template_name = "budgets/paymentorder/approval_form_enhanced.html"
    context_object_name = "payment_order"
    check_organization = False
    permission_codename = [
        'budgets.PaymentOrder_sign',
        'budgets.PaymentOrder_issue',
        'budgets.PaymentOrder_delete',
        'budgets.PaymentOrder_update',
        'budgets.PaymentOrder_view',
        'budgets.PaymentOrder_add'
    ]

    def get_success_url(self):
        return '/budgets/payment-orders/management/'
    
    def _check_approval_access(self, payment_order):
        """
        بررسی دسترسی کاربر به تایید دستور پرداخت بر اساس مدل‌های گردش کار
        
        قوانین:
        1. سوپروایزر/استاف: همیشه دسترسی دارند
        2. دستورات تایید شده: فقط سوپروایزر/استاف دسترسی دارند
        3. دستورات رد شده: فقط سوپروایزر/استاف دسترسی دارند
        4. دستورات در حال پردازش: بررسی بر اساس EntityType, Transition, Post, UserPost
        """
        user = self.request.user
        
        # سوپروایزر/استاف همیشه دسترسی دارند
        if user.is_superuser or user.is_staff:
            logger.info(f"[ACCESS_GRANTED] User={user.username} is superuser/staff for PaymentOrder={payment_order.order_number}")
            return True
        
        # بررسی پست‌های سطح بالا
        high_level_posts = ['مدیر عامل شرکت', 'هیئت مدیره', 'معاونت مالی/اداری دفتر مرکزی']
        user_high_level_posts = UserPost.objects.filter(
            user=user,
            post__name__in=high_level_posts,
            is_active=True
        ).exists()
        
        if user_high_level_posts:
            logger.info(f"[ACCESS_GRANTED] User={user.username} has high-level post for PaymentOrder={payment_order.order_number}")
            return True
            
        # بررسی وضعیت نهایی (فقط برای کاربران عادی)
        if payment_order.status.is_final_approve or payment_order.status.is_final_reject:
            logger.info(f"[ACCESS_DENIED] User={user.username} denied access to final status PaymentOrder={payment_order.order_number}")
            return False
            
        # بررسی اینکه آیا کاربر قبلاً تایید کرده است
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(payment_order)
        user_has_approved = ApprovalLog.objects.filter(
            content_type=ct,
            object_id=payment_order.id,
            user=user,
            action__code__in=['APPROVED', 'REJECTED'],
            is_active=True
        ).exists()
        
        if user_has_approved:
            logger.info(f"[ACCESS_DENIED] User={user.username} already approved PaymentOrder={payment_order.order_number}")
            return False
            
        # بررسی دسترسی بر اساس مدل‌های گردش کار
        access_granted, reason = self._check_workflow_access(user, payment_order)
        if not access_granted:
            logger.info(f"[ACCESS_DENIED] User={user.username} denied access to PaymentOrder={payment_order.order_number}: {reason}")
            return False
            
        logger.info(f"[ACCESS_GRANTED] User={user.username} granted access to PaymentOrder={payment_order.order_number}")
        return True
    
    def _check_workflow_access(self, user, payment_order):
        """
        بررسی دسترسی کاربر بر اساس مدل‌های گردش کار:
        EntityType -> Transition -> Post -> UserPost
        """
        try:
            # 1. پیدا کردن EntityType برای PaymentOrder
            entity_type = self._get_paymentorder_entity_type()
            if not entity_type:
                return False, "EntityType برای PaymentOrder یافت نشد"
            
            # 2. پیدا کردن Transitionهای موجود برای این وضعیت
            transitions = Transition.objects.filter(
                entity_type=entity_type,
                from_status=payment_order.status,
                organization=payment_order.organization,
                is_active=True
            ).prefetch_related('allowed_posts')
            
            if not transitions.exists():
                return False, f"هیچ Transition فعالی برای وضعیت {payment_order.status.name} یافت نشد"
            
            # 3. پیدا کردن پست‌های فعال کاربر
            user_posts = UserPost.objects.filter(
                user=user,
                is_active=True,
                end_date__isnull=True
            ).select_related('post', 'post__organization')
            
            if not user_posts.exists():
                return False, "کاربر هیچ پست فعالی ندارد"
            
            user_post_ids = set(user_posts.values_list('post_id', flat=True))
            logger.info(f"[WORKFLOW_CHECK] User={user.username} has posts: {list(user_post_ids)}")
            
            # 4. بررسی اینکه آیا کاربر در allowed_posts هر Transition قرار دارد
            for transition in transitions:
                allowed_post_ids = set(transition.allowed_posts.values_list('id', flat=True))
                logger.info(f"[WORKFLOW_CHECK] Transition={transition.name} allows posts: {list(allowed_post_ids)}")
                
                # اگر allowed_posts خالی است، همه دسترسی دارند
                if not allowed_post_ids:
                    logger.info(f"[WORKFLOW_CHECK] Transition={transition.name} allows all posts")
                    return True, "Transition عمومی - همه دسترسی دارند"
                
                # بررسی تقاطع پست‌های کاربر و پست‌های مجاز
                if user_post_ids.intersection(allowed_post_ids):
                    logger.info(f"[WORKFLOW_CHECK] User={user.username} has access via transition={transition.name}")
                    return True, f"دسترسی از طریق Transition {transition.name}"
            
            return False, "کاربر در هیچ Transition مجازی قرار ندارد"
            
        except Exception as e:
            logger.error(f"[WORKFLOW_CHECK_ERROR] User={user.username} PaymentOrder={payment_order.order_number} error: {e}")
            return False, f"خطا در بررسی دسترسی: {e}"
    
    def _get_access_denied_reason(self, payment_order):
        """دریافت دلیل عدم دسترسی با جزئیات بیشتر"""
        user = self.request.user
        
        # مدیر عامل و کاربران سطح بالا همیشه دسترسی دارند
        if user.is_superuser or user.is_staff:
            return None  # دسترسی دارد
        
        # بررسی پست‌های سطح بالا
        high_level_posts = ['مدیر عامل شرکت', 'هیئت مدیره', 'معاونت مالی/اداری دفتر مرکزی']
        user_high_level_posts = UserPost.objects.filter(
            user=user,
            post__name__in=high_level_posts,
            is_active=True
        ).exists()
        
        if user_high_level_posts:
            return None  # دسترسی دارد
        
        if payment_order.status.is_final_approve:
            return "این دستور پرداخت تایید نهایی شده است."
        elif payment_order.status.is_final_reject:
            return "این دستور پرداخت رد شده است."
        else:
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(payment_order)
            user_has_approved = ApprovalLog.objects.filter(
                content_type=ct,
                object_id=payment_order.id,
                user=user,
                action__code__in=['APPROVED', 'REJECTED'],
                is_active=True
            ).exists()
            
            if user_has_approved:
                return "شما قبلاً این دستور پرداخت را تایید/رد کرده‌اید."
            else:
                # بررسی دقیق‌تر بر اساس مدل‌های گردش کار
                access_granted, reason = self._check_workflow_access(user, payment_order)
                if not access_granted:
                    return f"شما مجاز به تایید این دستور پرداخت نیستید. دلیل: {reason}"
                else:
                    return "شما مجاز به تایید این دستور پرداخت نیستید."

    def _get_approval_tree(self, payment_order):
        """
        دریافت درخت تایید بر اساس مدل‌های گردش کار
        """
        try:
            from django.contrib.contenttypes.models import ContentType as DjangoCT
            po_ct = DjangoCT.objects.get_for_model(payment_order)
            
            entity_type = self._get_paymentorder_entity_type()
            logger.info(f"[APPROVAL_TREE_DEBUG] EntityType: {entity_type.code if entity_type else 'None'}")
            if not entity_type:
                logger.warning(f"[APPROVAL_TREE_DEBUG] No EntityType found for PaymentOrder")
                return []
            
            # ابتدا سعی کن Transition های مربوط به وضعیت فعلی را پیدا کن
            transitions_in_status = Transition.objects.filter(
                entity_type=entity_type,
                from_status=payment_order.status,
                organization=payment_order.organization,
                is_active=True
            ).prefetch_related('allowed_posts')

            logger.info(f"[APPROVAL_TREE_DEBUG] Transitions for current status: {transitions_in_status.count()}")
            
            # اگر Transition برای وضعیت فعلی وجود ندارد، از همه Transition های مربوط به این EntityType استفاده کن
            if not transitions_in_status.exists():
                logger.info(f"[APPROVAL_TREE_DEBUG] No transitions for current status, using all transitions for entity type")
                transitions_in_status = Transition.objects.filter(
                    entity_type=entity_type,
                    organization=payment_order.organization,
                    is_active=True
                ).prefetch_related('allowed_posts')
                
                # اگر هنوز هم چیزی پیدا نشد، از همه Transition ها استفاده کن
                if not transitions_in_status.exists():
                    logger.info(f"[APPROVAL_TREE_DEBUG] No transitions for organization, using all transitions for entity type")
                    transitions_in_status = Transition.objects.filter(
                        entity_type=entity_type,
                        is_active=True
                    ).prefetch_related('allowed_posts')

            logger.info(f"[APPROVAL_TREE_DEBUG] Final transitions found: {transitions_in_status.count()}")
            for tr in transitions_in_status:
                logger.info(f"[APPROVAL_TREE_DEBUG] Transition: {tr.name}, Allowed posts: {list(tr.allowed_posts.values_list('name', flat=True))}")

            required_posts = {}
            for tr in transitions_in_status:
                for post in tr.allowed_posts.all():
                    required_posts[post.id] = post

            logger.info(f"[APPROVAL_TREE_DEBUG] Required posts: {list(required_posts.keys())}")

            approval_logs_qs = ApprovalLog.objects.filter(
                content_type=po_ct,
                object_id=payment_order.id,
                from_status=payment_order.status
            ).select_related('user', 'post').order_by('-timestamp')

            logger.info(f"[APPROVAL_TREE_DEBUG] Approval logs found: {approval_logs_qs.count()}")

            post_id_to_logs = {}
            for log in approval_logs_qs:
                if log.post_id:
                    post_id_to_logs.setdefault(log.post_id, []).append(log)

            approval_tree = []
            for post_id, post in required_posts.items():
                logs = post_id_to_logs.get(post_id, [])
                
                # فیلتر کردن فقط لاگ‌های سوپروایزر، نه پست‌ها
                filtered_logs = []
                for log in logs:
                    # فقط لاگ‌های سوپروایزر را فیلتر کن، نه پست‌ها
                    if not (log.user.is_superuser or log.user.is_staff):
                        filtered_logs.append(log)
                
                approval_tree.append({
                    'post': post,
                    'approved': len(logs) > 0,  # از همه لاگ‌ها استفاده کن
                    'approvals': filtered_logs,  # فقط لاگ‌های فیلتر شده را نمایش بده
                })

            # پست‌هایی که لاگ دارند ولی در required نیستند (مثلاً گذار عمومی)
            for post_id, logs in post_id_to_logs.items():
                if post_id not in required_posts:
                    approval_tree.append({
                        'post': logs[0].post,
                        'approved': True,
                        'approvals': logs,
                    })

            logger.info(f"[APPROVAL_TREE] PaymentOrder={payment_order.order_number} tree_nodes={len(approval_tree)}")
            return approval_tree
            
        except Exception as e:
            logger.error(f"[APPROVAL_TREE_ERROR] order={payment_order.order_number} err={e}", exc_info=True)
            return []

    def _get_authorized_users_for_approval(self, payment_order):
        """
        دریافت لیست کاربران مجاز برای تایید دستور پرداخت بر اساس مدل‌های گردش کار
        """
        try:
            # 1. پیدا کردن EntityType برای PaymentOrder
            entity_type = self._get_paymentorder_entity_type()
            logger.info(f"[AUTHORIZED_USERS_DEBUG] EntityType: {entity_type.code if entity_type else 'None'}")
            if not entity_type:
                logger.warning(f"[AUTHORIZED_USERS_DEBUG] No EntityType found for PaymentOrder")
                return []
            
            # 2. پیدا کردن Transitionهای موجود برای این وضعیت
            transitions = Transition.objects.filter(
                entity_type=entity_type,
                from_status=payment_order.status,
                organization=payment_order.organization,
                is_active=True
            ).prefetch_related('allowed_posts')
            
            logger.info(f"[AUTHORIZED_USERS_DEBUG] Transitions for current status: {transitions.count()}")
            
            # اگر Transition برای وضعیت فعلی وجود ندارد، از همه Transition های مربوط به این EntityType استفاده کن
            if not transitions.exists():
                logger.info(f"[AUTHORIZED_USERS_DEBUG] No transitions for current status, using all transitions for entity type")
                transitions = Transition.objects.filter(
                    entity_type=entity_type,
                    organization=payment_order.organization,
                    is_active=True
                ).prefetch_related('allowed_posts')
                
                # اگر هنوز هم چیزی پیدا نشد، از همه Transition ها استفاده کن
                if not transitions.exists():
                    logger.info(f"[AUTHORIZED_USERS_DEBUG] No transitions for organization, using all transitions for entity type")
                    transitions = Transition.objects.filter(
                        entity_type=entity_type,
                        is_active=True
                    ).prefetch_related('allowed_posts')
            
            logger.info(f"[AUTHORIZED_USERS_DEBUG] Final transitions found: {transitions.count()}")
            if not transitions.exists():
                logger.warning(f"[AUTHORIZED_USERS_DEBUG] No transitions found for entity type {entity_type.name}")
                return []
            
            # 3. جمع‌آوری تمام پست‌های مجاز از همه Transitionها
            allowed_post_ids = set()
            for transition in transitions:
                post_ids = set(transition.allowed_posts.values_list('id', flat=True))
                allowed_post_ids.update(post_ids)
                logger.info(f"[AUTHORIZED_USERS_DEBUG] Transition {transition.name} allows posts: {list(post_ids)}")
            
            logger.info(f"[AUTHORIZED_USERS_DEBUG] Total allowed post IDs: {list(allowed_post_ids)}")
            
            # اگر هیچ پست خاصی تعریف نشده، همه پست‌ها مجاز هستند
            if not allowed_post_ids:
                user_posts = UserPost.objects.filter(
                    is_active=True,
                    post__organization=payment_order.organization
                ).select_related('user', 'post')
                logger.info(f"[AUTHORIZED_USERS_DEBUG] Using all posts in organization {payment_order.organization.name}")
            else:
                # ابتدا در organization فعلی جستجو کن
                user_posts = UserPost.objects.filter(
                    post_id__in=allowed_post_ids,
                    is_active=True,
                    post__organization=payment_order.organization
                ).select_related('user', 'post')
                
                # اگر در organization فعلی کاربری پیدا نشد، از همه organization ها استفاده کن
                if not user_posts.exists():
                    logger.info(f"[AUTHORIZED_USERS_DEBUG] No users in current organization, searching all organizations")
                user_posts = UserPost.objects.filter(
                    post_id__in=allowed_post_ids,
                    is_active=True
                ).select_related('user', 'post')
                
                logger.info(f"[AUTHORIZED_USERS_DEBUG] Using specific posts, found {user_posts.count()} user posts")
            
            # 4. ساخت لیست کاربران مجاز
            authorized_users = []
            for user_post in user_posts:
                user = user_post.user
                post = user_post.post
                
                # بررسی اینکه آیا کاربر قبلاً تایید کرده است
                from django.contrib.contenttypes.models import ContentType
                ct = ContentType.objects.get_for_model(payment_order)
                has_approved = ApprovalLog.objects.filter(
                    content_type=ct,
                    object_id=payment_order.id,
                    user=user,
                    action__code__in=['APPROVED', 'REJECTED'],
                    is_active=True
                ).exists()
                
                authorized_users.append({
                    'user': user,
                    'post': post,
                    'username': user.username,
                    'full_name': user.get_full_name() or user.username,
                    'post_name': post.name,
                    'organization': post.organization.name,
                    'has_approved': has_approved,
                    'is_superuser': user.is_superuser,
                    'is_staff': user.is_staff
                })
            
            logger.info(f"[AUTHORIZED_USERS] Found {len(authorized_users)} authorized users")
            return authorized_users
            
        except Exception as e:
            logger.error(f"[AUTHORIZED_USERS_ERROR] PaymentOrder={payment_order.order_number} error: {e}")
            return []

    def _get_paymentorder_entity_type(self):
        """Resolve EntityType for PaymentOrder by content_type, fallback to code."""
        try:
            from django.contrib.contenttypes.models import ContentType as DjangoCT
            ct = DjangoCT.objects.get_for_model(PaymentOrder)
            et = EntityType.objects.filter(content_type=ct).first()
            if et:
                return et
        except Exception:
            pass
        return EntityType.objects.filter(code='PAYMENTORDER').first()

    def get_available_transitions(self, user, payment_order):
        user_posts = user.userpost_set.filter(is_active=True).values_list('post_id', flat=True)
        entity_type = self._get_paymentorder_entity_type()
        base_qs = Transition.objects.filter(
            entity_type=entity_type,
            from_status=payment_order.status,
            organization=payment_order.organization,
            is_active=True,
        )
        if user.is_superuser or user.is_staff:
            qs = base_qs
        else:
            qs = base_qs.filter(
                Q(allowed_posts__in=user_posts) | Q(allowed_posts__isnull=True)
            )
        qs = qs.select_related('action', 'to_status').distinct()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_order = self.get_object()
        
        # بررسی دسترسی بر اساس وضعیت و تاییدات قبلی
        context['can_approve'] = self._check_approval_access(payment_order)
        
        # همیشه درخت تایید و کاربران مجاز را محاسبه کن
        context['approval_tree'] = self._get_approval_tree(payment_order)
        context['authorized_users'] = self._get_authorized_users_for_approval(payment_order)
        
        if not context['can_approve']:
            context['access_denied_reason'] = self._get_access_denied_reason(payment_order)
            return context
            
        available = self.get_available_transitions(self.request.user, payment_order)
        context['available_actions'] = list(available.values_list('action__code', flat=True))
        context['available_to_statuses'] = list(available.values_list('to_status__code', flat=True))
        context['available_transitions'] = available

        # محاسبه آمار تایید
        context['approval_required_count'] = len(context['approval_tree'])
        context['approval_done_count'] = sum(1 for node in context['approval_tree'] if node['approved'])
            
        # بررسی اینکه آیا کاربر قبلاً تایید/رد کرده است
        from django.contrib.contenttypes.models import ContentType as DjangoCT
        po_ct = DjangoCT.objects.get_for_model(payment_order)
        user_has_approval = ApprovalLog.objects.filter(
            content_type=po_ct,
            object_id=payment_order.id,
            user=self.request.user,
            action__code__in=['APPROVED', 'REJECTED'],
            is_active=True
        ).exists()
        context['user_has_previous_approval'] = user_has_approval
        
        # بررسی دسترسی سوپروایزر برای بازگشت
        context['can_revert'] = (
            self.request.user.is_superuser or 
            self.request.user.is_staff or
            self.request.user.has_perm('budgets.PaymentOrder_revert')
        )
        
        # لاگ افراد موثر در گردش کار
        try:
            logger.info(f"[WORKFLOW_PARTICIPANTS] PaymentOrder={payment_order.order_number}, Status={payment_order.status.name}")
            
            # افراد در درخت تایید
            for node in context['approval_tree']:
                logger.info(f"[WORKFLOW_PARTICIPANTS] Post={node['post'].name}, Approved={node['approved']}")
                for log in node.get('approvals', []):
                    logger.info(f"[WORKFLOW_PARTICIPANTS] User={log.user.username}, Action={log.action.name if log.action else 'N/A'}, Time={log.timestamp}")
            
            # افراد در گذارهای موجود
            for transition in available:
                logger.info(f"[WORKFLOW_PARTICIPANTS] Transition={transition.name}, Action={transition.action.name}, ToStatus={transition.to_status.name}")
                for post in transition.allowed_posts.all():
                    logger.info(f"[WORKFLOW_PARTICIPANTS] AllowedPost={post.name}")
            
            # لیست کاربران مجاز برای تایید
            logger.info(f"[WORKFLOW_PARTICIPANTS] Authorized users for approval: {[u['username'] for u in context['authorized_users']]}")
                    
        except Exception as e:
            logger.error(f"[WORKFLOW_PARTICIPANTS_ERROR] {e}")
        et = self._get_paymentorder_entity_type()
        logger.debug(
            f"[APPROVAL_AVAILABLE] order={payment_order.order_number} status={payment_order.status.code} "
            f"entity_type={(et.code if et else 'MISSING')} actions={context['available_actions']} "
            f"to_statuses={context['available_to_statuses']}"
        )
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        payment_order = self.get_object()
        logger.info(
            f"[GET_OBJECT] User={self.request.user.username} retrieved PaymentOrder={payment_order.order_number}, status={payment_order.status.code}")

        # پس از تعیین دریافت‌کننده و ایجاد پیش‌نویس، فقط فیلد action قابل تغییر باشد
        if payment_order.status.code != 'PO_DRAFT' and payment_order.payee:
            for field_name, field in form.fields.items():
                if field_name != 'action_code':
                    field.disabled = True
        return form
 
    def form_valid(self, form):
        payment_order = form.instance
        user = self.request.user
        action_code = form.cleaned_data.get('action_code')
        transition_id = self.request.POST.get('transition_id')
        change_decision = self.request.POST.get('change_decision') == 'true'
        revert_decision = self.request.POST.get('revert_decision') == 'true'

        logger.info(
            f"[APPROVAL_SUBMIT] User={user.username}, "
            f"PaymentOrder={payment_order.order_number}, "
            f"Status={payment_order.status.code}, "
            f"Action={action_code}, "
            f"ChangeDecision={change_decision}"
        )

        # اگر بازگشت تصمیم است (سوپروایزر)
        if revert_decision:
            if not (user.is_superuser or user.is_staff or user.has_perm('budgets.PaymentOrder_revert')):
                messages.error(self.request, "شما مجاز به بازگشت دستور پرداخت نیستید.")
                return self.form_invalid(form)
            
            try:
                from django.contrib.contenttypes.models import ContentType
                from core.models import Status
                
                # پیدا کردن وضعیت قبلی از لاگ‌ها
                ct = ContentType.objects.get_for_model(payment_order)
                last_log = ApprovalLog.objects.filter(
                    content_type=ct,
                    object_id=payment_order.id,
                    is_active=True
                ).order_by('-timestamp').first()
                
                if last_log and last_log.from_status:
                    # بازگشت به وضعیت قبلی
                    payment_order.status = last_log.from_status
                    payment_order.save()
                    
                    # غیرفعال کردن همه لاگ‌های فعلی
                    ApprovalLog.objects.filter(
                        content_type=ct,
                        object_id=payment_order.id,
                        is_active=True
                    ).update(is_active=False)
                    
                    # ثبت لاگ بازگشت
                    ApprovalLog.objects.create(
                        content_type=ct,
                        object_id=payment_order.id,
                        from_status=last_log.to_status,
                        to_status=last_log.from_status,
                        action_id=Action.objects.filter(code='REVERT').first().id if Action.objects.filter(code='REVERT').exists() else None,
                        user=user,
                        comment=f"بازگشت به وضعیت قبلی توسط {user.get_full_name() or user.username}",
                        is_active=True
                    )
                    
                    logger.info(f"[REVERT_DECISION] User={user.username} reverted PaymentOrder {payment_order.order_number} to {last_log.from_status.name}")
                    messages.success(self.request, f"دستور پرداخت به وضعیت {last_log.from_status.name} بازگردانده شد.")
                    return redirect(self.get_success_url())
                else:
                    messages.error(self.request, "وضعیت قبلی یافت نشد.")
                    return self.form_invalid(form)
                    
            except Exception as e:
                logger.error(f"[REVERT_DECISION_ERROR] User={user.username} error: {e}")
                messages.error(self.request, "خطا در بازگشت دستور پرداخت. لطفاً دوباره تلاش کنید.")
                return self.form_invalid(form)

        # اگر تغییر تصمیم است، ابتدا لاگ قبلی را غیرفعال کن
        if change_decision:
            try:
                from django.contrib.contenttypes.models import ContentType
                ct = ContentType.objects.get_for_model(payment_order)
                previous_logs = ApprovalLog.objects.filter(
                    content_type=ct,
                    object_id=payment_order.id,
                    user=user,
                    action__code__in=['APPROVED', 'REJECTED']
                )
                for log in previous_logs:
                    log.is_active = False
                    log.save()
                logger.info(f"[CHANGE_DECISION] User={user.username} deactivated {previous_logs.count()} previous logs")
            except Exception as e:
                logger.error(f"[CHANGE_DECISION_ERROR] User={user.username} error: {e}")
                messages.warning(self.request, "خطا در لغو تصمیم قبلی. لطفاً دوباره تلاش کنید.")
                return self.form_invalid(form)

        if not action_code and not transition_id:
            logger.warning(f"[APPROVAL_SUBMIT] User={user.username} did not select any action")
            messages.error(self.request, "هیچ اقدامی انتخاب نشده است.")
            return self.form_invalid(form)

        try:
            # اگر transition_id ارسال شده، دقیقاً همان گذار را مانند فاکتور اعتبارسنجی و اعمال کن
            if transition_id:
                try:
                    target_transition = Transition.objects.select_related('action', 'to_status').get(pk=transition_id)
                except Transition.DoesNotExist:
                    raise PermissionError("گذار یافت نشد")

                # اعتبارسنجی ها: نوع موجودیت، سازمان، وضعیت مبدأ، فعال بودن
                if target_transition.entity_type.code != 'PAYMENTORDER':
                    raise PermissionError("گذار مربوط به موجودیت دیگری است")
                if target_transition.organization_id != payment_order.organization_id:
                    raise PermissionError("گذار مربوط به سازمان دیگری است")
                if target_transition.from_status_id != payment_order.status_id:
                    raise PermissionError("وضعیت فعلی با گذار انتخابی منطبق نیست")
                if not target_transition.is_active:
                    raise PermissionError("گذار غیرفعال است")

                # کنترل allowed_posts؛ ادمین/استف عبور می‌کند
                if not (user.is_superuser or user.is_staff):
                    user_posts = user.userpost_set.filter(is_active=True).values_list('post_id', flat=True)
                    has_access = target_transition.allowed_posts.filter(pk__in=user_posts).exists()
                    if not has_access and target_transition.allowed_posts.exists():
                        # اگر گذار برای پست خاص تعریف شده و کاربر آن پست را ندارد
                        raise PermissionError("شما برای این گذار پست مجاز ندارید")

                # اعمال گذار و ثبت لاگ
                original_status = payment_order.status
                payment_order.status = target_transition.to_status
                payment_order.save(update_fields=['status'])

                user_post = user.userpost_set.filter(is_active=True).first()
                ApprovalLog.objects.create(
                    content_type=ContentType.objects.get_for_model(payment_order),
                    object_id=payment_order.id,
                    from_status=original_status,
                    to_status=target_transition.to_status,
                    action=target_transition.action,
                    user=user,
                    post=(user_post.post if user_post else None),
                    comment=f"Transitioned via transition_id={transition_id}"
                )
            else:
                # در غیر اینصورت بر اساس action_code رفتار سابق را انجام بده
                self.execute_transition(payment_order, action_code, user)
        except PermissionError as e:
            logger.error(
                f"[APPROVAL_DENIED] User={user.username} not allowed "
                f"to {action_code} PaymentOrder {payment_order.order_number}: {e}"
            )
            available = self.get_available_transitions(user, payment_order)
            available_actions = ', '.join(sorted(set(available.values_list('action__code', flat=True)))) or '—'
            available_to = ', '.join(sorted(set(available.values_list('to_status__code', flat=True)))) or '—'
            messages.error(
                self.request,
                f"اقدام انتخابی مجاز نیست. اقدامات مجاز: {available_actions} / وضعیت‌های مقصد: {available_to}"
            )
            return self.form_invalid(form)

        logger.info(
            f"[APPROVAL_DONE] User={user.username} successfully performed {action_code or ('transition_id='+str(transition_id))} "
            f"on PaymentOrder={payment_order.order_number}"
        )
        # از ذخیره دوباره فرم جلوگیری می‌کنیم تا مقادیر نامعتبر وارد نشوند
        messages.success(self.request, "تغییر وضعیت با موفقیت ثبت شد.")
        return redirect(self.get_success_url())
    #
    # @staticmethod
    # def execute_transition(payment_order, action_code, user):
    #     """اجرای Transition برای تایید/رد با لاگ کامل"""
    #     user_posts = user.userpost_set.filter(is_active=True).values_list('post', flat=True)
    #     logger.info(
    #         f"[TRANSITION] User={user.username}, "
    #         f"PaymentOrder={payment_order.order_number}, "
    #         f"status={payment_order.status.code}, "
    #         f"action={action_code}, "
    #         f"user_posts={list(user_posts)}"
    #     )
    #
    #     # نگه داشتن queryset قبل از گرفتن اولین مورد
    #     transitions_qs = Transition.objects.filter(
    #         entity_type__code='PAYMENTORDER',
    #         from_status=payment_order.status,
    #         action__code=action_code,
    #         allowed_posts__in=user_posts
    #     )
    #
    #     logger.debug(
    #         f"[TRANSITION_DEBUG] Found {transitions_qs.count()} matching transitions: "
    #         f"{[t.to_status.code for t in transitions_qs]}"
    #     )
    #
    #     transition = transitions_qs.first()
    #
    #     if not transition and not (user.is_superuser or user.is_staff):
    #         valid_transitions = Transition.objects.filter(
    #             entity_type__code='PAYMENTORDER',
    #             from_status=payment_order.status
    #         )
    #         logger.warning(
    #             f"[TRANSITION_DENIED_DEBUG] User={user.username} cannot perform {action_code}. "
    #             f"Available transitions from status {payment_order.status.code}: "
    #             f"{[t.to_status.code for t in valid_transitions]}"
    #         )
    #         raise PermissionError("گذار مجاز نیست")
    #
    #     if transition:
    #         logger.info(
    #             f"[TRANSITION_OK] User={user.username} performed {action_code} → "
    #             f"new_status={transition.to_status.code}"
    #         )
    #         payment_order.status = transition.to_status
    #         payment_order.save()
    #
    #         ApprovalLog.objects.create(
    #             content_type=ContentType.objects.get_for_model(payment_order),
    #             object_id=payment_order.id,
    #             to_status=transition.to_status,
    #             action=transition.action,
    #             user=user,
    #             comment=f"Transitioned via {action_code}"
    #         )
    # --------------------------------------------------------------------------------------------
    @staticmethod
    def execute_transition(payment_order, action_code, user):
        user_posts = user.userpost_set.filter(is_active=True).values_list('post_id', flat=True)

        # Resolve EntityType dynamically
        try:
            from django.contrib.contenttypes.models import ContentType as DjangoCT
            ct = DjangoCT.objects.get_for_model(PaymentOrder)
            entity_type = EntityType.objects.filter(content_type=ct).first() or EntityType.objects.filter(code='PAYMENTORDER').first()
        except Exception:
            entity_type = EntityType.objects.filter(code='PAYMENTORDER').first()

        logger.info(
            f"[TRANSITION] user={user.username} order={payment_order.order_number} "
            f"from_status={payment_order.status.code} action={action_code} posts={list(user_posts)} "
            f"entity_type={(entity_type.code if entity_type else 'MISSING')}"
        )

        # همه گذارهای فعال این وضعیت برای محاسبه پست‌های لازم
        all_current_qs = Transition.objects.filter(
            entity_type=entity_type,
            from_status=payment_order.status,
            organization=payment_order.organization,
            is_active=True,
        ).prefetch_related('allowed_posts', 'action', 'to_status')

        required_post_ids = set()
        for tr in all_current_qs:
            for p in tr.allowed_posts.all():
                required_post_ids.add(p.id)

        # اگر محدود به پست خاص است، بررسی اینکه کاربر پست لازم را دارد
        if required_post_ids and not (user.is_superuser or user.is_staff):
            if not set(user_posts).intersection(required_post_ids):
                raise PermissionError("پست کاربر برای این مرحله مجاز نیست")

        # ثبت تایید این کاربر (بدون تغییر وضعیت تا تکمیل تاییدها)
        current_status = payment_order.status
        user_post_obj = user.userpost_set.filter(is_active=True).first()
        ApprovalLog.objects.create(
            content_type=ContentType.objects.get_for_model(payment_order),
            object_id=payment_order.id,
            from_status=current_status,
            to_status=current_status,  # تا تکمیل تاییدها در همان وضعیت می‌ماند
            action=Action.objects.filter(code=action_code).first(),
            user=user,
            post=(user_post_obj.post if user_post_obj else None),
            comment=f"Approval recorded for action {action_code}"
        )

        # بررسی تکمیل تاییدها
        acted_post_ids = set(
            ApprovalLog.objects.filter(
                content_type=ContentType.objects.get_for_model(payment_order),
                object_id=payment_order.id,
                from_status=current_status
            ).exclude(post__isnull=True).values_list('post_id', flat=True)
        )

        # اگر هیچ پست الزامی تعریف نشده، یا همه پست‌های لازم تایید کرده‌اند، گذار انجام شود
        ready_to_transition = (len(required_post_ids) == 0) or required_post_ids.issubset(acted_post_ids)

        if not ready_to_transition:
            logger.info(
                f"[APPROVAL_PENDING] order={payment_order.order_number} current_status={current_status.code} "
                f"required_posts={sorted(list(required_post_ids))} acted_posts={sorted(list(acted_post_ids))}"
            )
            return  # هنوز به وضعیت بعدی نمی‌رویم

        # انتخاب گذار هدف بر اساس action_code
        target_qs = all_current_qs.filter(action__code=action_code)
        transition = None
        if target_qs.exists():
            transition = target_qs.first()
        elif user.is_superuser or user.is_staff:
            # fallback: اگر action تطابق نداشت، اولین گذار فعال را بردار
            transition = all_current_qs.first()

        if not transition:
            available = list(all_current_qs)
            logger.warning(
                f"[TRANSITION_DENIED_READY] user={user.username} action={action_code} order={payment_order.order_number} "
                f"no matching action. available_actions={[t.action.code for t in available]}"
            )
            raise PermissionError("گذار مجاز نیست")

        # تغییر وضعیت نهایی و ثبت لاگ کامل
        payment_order.status = transition.to_status
        payment_order.save(update_fields=['status'])

        ApprovalLog.objects.create(
            content_type=ContentType.objects.get_for_model(payment_order),
            object_id=payment_order.id,
            from_status=current_status,
            to_status=transition.to_status,
            action=transition.action,
            user=user,
            post=(user_post_obj.post if user_post_obj else None),
            comment=f"Transitioned to {transition.to_status.code} via {action_code} after all approvals"
        )
        # --------------------------------------------------------------------------------------------
    # @staticmethod
    # def execute_transition(payment_order, action_code, user):
    #     """اجرای Transition برای تایید/رد"""
    #     transition = Transition.objects.filter(
    #         entity_type__code='PAYMENTORDER',
    #         from_status=payment_order.status,
    #         action__code=action_code,
    #         allowed_posts__in=user.userpost_set.filter(is_active=True).values_list('post', flat=True)
    #     ).first()
    #
    #     if not transition and not (user.is_superuser or user.is_staff):
    #         raise PermissionError("گذار مجاز نیست")
    #
    #     if transition:
    #         payment_order.status = transition.to_status
    #         payment_order.save()
    #         ApprovalLog.objects.create(
    #             content_type=ContentType.objects.get_for_model(payment_order),
    #             object_id=payment_order.id,
    #             to_status=transition.to_status,
    #             action=transition.action,
    #             user=user,
    #             comment=f"Transitioned via {action_code}"
    #         )

    # def _check_permission(self, payment_order):
    #     """ادمین همیشه مجاز است، بقیه باید Transition معتبر داشته باشند"""
    #     user = self.request.user
    #     if user.is_superuser or user.is_staff:
    #         logger.debug(f"User {user.username} is superuser/staff, granting access")
    #         return True
    #
    #     user_posts = UserPost.objects.filter(user=user, is_active=True).values_list("post_id", flat=True)
    #     if not user_posts.exists():
    #         logger.debug(f"No active posts for user {user.username}")
    #         return False
    #
    #     entity_type = EntityType.objects.get(code="PAYMENTORDER")
    #     allowed = Transition.objects.filter(
    #         entity_type=entity_type,
    #         from_status=payment_order.status,
    #         organization=payment_order.organization,
    #         is_active=True,
    #         allowed_posts__in=user_posts
    #     ).exists()
    #     logger.debug(f"Permission check for {user.username} on PaymentOrder {payment_order.order_number}: {allowed}")
    #     return allowed
    #
    # def get_context_data(self, **kwargs):
    #     """آماده‌سازی context با بهینه‌سازی queryها و caching"""
    #     logger.debug(f"Preparing context for PaymentOrder {self.get_object().order_number}")
    #     context = super().get_context_data(**kwargs)
    #     payment_order = self.get_object()
    #
    #     # فرم‌ها
    #     if self.request.POST:
    #         context["order_form"] = PaymentOrderForm(self.request.POST, instance=payment_order, user=self.request.user)
    #         context["approval_form"] = PaymentOrderApprovalForm(self.request.POST, instance=payment_order)
    #     else:
    #         context["order_form"] = PaymentOrderForm(instance=payment_order, user=self.request.user)
    #         context["approval_form"] = PaymentOrderApprovalForm(instance=payment_order)
    #
    #     # وضعیت‌های قابل انتخاب
    #     context["available_statuses"] = self._get_available_statuses(payment_order)
    #
    #     # لاگ‌ها
    #     context["approval_logs"] = ApprovalLog.objects.filter(
    #         content_type=ContentType.objects.get_for_model(payment_order),
    #         object_id=payment_order.id
    #     ).select_related("user", "from_status", "to_status", "action").order_by("-timestamp")
    #
    #     # فاکتورهای مرتبط و آمار
    #     if hasattr(payment_order, "related_factors"):
    #         context["related_factors"] = payment_order.related_factors.select_related("status").prefetch_related("tankhah").all()
    #         cache_key = f"payment_order_{payment_order.pk}_stats"
    #         stats = cache.get(cache_key)
    #         if not stats:
    #             stats = {
    #                 "total_count": payment_order.related_factors.count(),
    #                 "total_amount": payment_order.related_factors.aggregate(total=Sum("amount"))["total"] or 0,
    #                 "approved_count": payment_order.related_factors.filter(status__code="FACTOR_APPROVED").count(),
    #             }
    #             cache.set(cache_key, stats, timeout=300)  # 5 minutes
    #         context["factors_stats"] = stats
    #
    #     # اطلاعات دریافت‌کننده
    #     context["payee_info"] = {
    #         "name": payment_order.payee.name if payment_order.payee else "نامشخص",
    #         "account_number": payment_order.payee_account_number or "نامشخص",
    #         "iban": payment_order.payee_iban or "نامشخص",
    #     }
    #
    #     logger.info(f"Context prepared for PaymentOrder {payment_order.order_number}: {stats}")
    #     return context
    #
    # def _get_available_statuses(self, payment_order):
    #     """وضعیت‌های قابل انتخاب بر اساس Transitionها"""
    #     user = self.request.user
    #     entity_type = EntityType.objects.get(code="PAYMENTORDER")
    #     cache_key = f"available_statuses_{payment_order.pk}_{user.pk}"
    #     statuses = cache.get(cache_key)
    #
    #     if statuses is None:
    #         if user.is_superuser or user.is_staff:
    #             statuses = Status.objects.filter(
    #                 id__in=Transition.objects.filter(
    #                     entity_type=entity_type,
    #                     from_status=payment_order.status,
    #                     organization=payment_order.organization,
    #                     is_active=True
    #                 ).values_list("to_status_id", flat=True)
    #             )
    #         else:
    #             user_posts = UserPost.objects.filter(user=user, is_active=True).values_list("post_id", flat=True)
    #             transitions = Transition.objects.filter(
    #                 entity_type=entity_type,
    #                 from_status=payment_order.status,
    #                 organization=payment_order.organization,
    #                 is_active=True,
    #                 allowed_posts__in=user_posts
    #             ).select_related("to_status").distinct()
    #             statuses = [t.to_status for t in transitions]
    #         cache.set(cache_key, statuses, timeout=300)
    #
    #     logger.debug(f"Available statuses for PaymentOrder {payment_order.order_number}: {[s.code for s in statuses]}")
    #     return statuses
    #
    # def post(self, request, *args, **kwargs):
    #     """مدیریت درخواست POST"""
    #     self.object = self.get_object()
    #     order_form = PaymentOrderForm(request.POST, instance=self.object, user=request.user)
    #     approval_form = PaymentOrderApprovalForm(request.POST, instance=self.object)
    #
    #     if order_form.is_valid() and approval_form.is_valid():
    #         return self.forms_valid(order_form, approval_form)
    #     else:
    #         logger.error(f"Form errors: order_form={order_form.errors}, approval_form={approval_form.errors}")
    #         return self.forms_invalid(order_form, approval_form)
    #
    # def forms_valid(self, order_form, approval_form):
    #     """مدیریت فرم‌های معتبر"""
    #     payment_order = order_form.instance
    #     old_status = payment_order.status
    #     new_status = approval_form.cleaned_data["status"]
    #     notes = approval_form.cleaned_data.get("notes", "")
    #
    #     try:
    #         with transaction.atomic():
    #             # ذخیره فرم اطلاعات (اگر نیاز باشد)
    #             order_form.save()
    #
    #             # اجرای گذار
    #             action_code = 'APPROVE' if new_status.code in ['APPROVED_FINAL', 'PO_APPROVED'] else 'REJECT'
    #             payment_order.execute_transition(
    #                 action_code=action_code,
    #                 user=self.request.user,
    #                 notes=notes
    #             )
    #
    #             # تأیید فاکتورهای مرتبط در صورت تأیید نهایی
    #             if new_status.code in ['APPROVED_FINAL', 'PO_APPROVED']:
    #                 approved_status = Status.objects.filter(code='FACTOR_APPROVED').first()
    #                 if approved_status:
    #                     related_factors = payment_order.related_factors.all()
    #                     for factor in related_factors:
    #                         factor.status = approved_status
    #                         self._log_factor_approval(factor, factor.status, approved_status, f"تأیید از طریق دستور پرداخت {payment_order.order_number}")
    #                     Factor.objects.bulk_update(related_factors, ['status'])
    #                     logger.info(f"Updated {len(related_factors)} factors to FACTOR_APPROVED for PaymentOrder {payment_order.order_number}")
    #
    #             messages.success(self.request, f"وضعیت دستور پرداخت به {new_status.name} تغییر یافت.")
    #             return redirect("paymentorder_management_list")
    #     except Exception as e:
    #         logger.error(f"Error saving PaymentOrder {payment_order.order_number}: {str(e)}", exc_info=True)
    #         messages.error(self.request, f"خطا در ثبت تغییر وضعیت: {str(e)}")
    #         return self.forms_invalid(order_form, approval_form)
    #
    # def forms_invalid(self, order_form, approval_form):
    #     """مدیریت فرم‌های نامعتبر"""
    #     messages.error(self.request, "لطفاً خطاهای فرم‌ها را بررسی کنید.")
    #     return self.render_to_response(self.get_context_data(order_form=order_form, approval_form=approval_form))
    #
    # def _log_factor_approval(self, factor, old_status, new_status, comment):
    #     """ثبت لاگ تأیید فاکتور"""
    #     try:
    #         logger.debug(f"Logging factor approval for Factor {factor.factor_number}")
    #         ApprovalLog.objects.create(
    #             content_type=ContentType.objects.get_for_model(factor),
    #             object_id=factor.id,
    #             from_status=old_status,
    #             to_status=new_status,
    #             action=Action.objects.filter(code='APPROVE').first(),
    #             user=self.request.user,
    #             comment=comment,
    #             post=UserPost.objects.filter(user=self.request.user, is_active=True).first().post
    #             if not self.request.user.is_superuser else None,
    #         )
    #     except Exception as e:
    #         logger.error(f"Error logging factor approval for Factor {factor.factor_number}: {str(e)}", exc_info=True)
    #
    #         # ==========================================

    # def dispatch(self, request, *args, **kwargs):
    #     """چک مجوز قبل از رندر"""
    #     payment_order = self.get_object()
    #     if not self._check_permission(payment_order):
    #         logger.warning(f"User {request.user.username} denied access to approve PaymentOrder {payment_order.order_number}👎")
    #         messages.error(request, "شما مجوز بررسی این دستور پرداخت را ندارید.👎")
    #         raise PermissionDenied("👎شما مجوز بررسی این دستور پرداخت را ندارید.")
    #     return super().dispatch(request, *args, **kwargs)

class PaymentOrderAttachFactorsAPI(PermissionBaseView, View):
    """Attach existing factors to a PaymentOrder via POST JSON {factor_ids:[...]}."""
    permission_codename = 'budgets.PaymentOrder_update'
    check_organization = True

    def post(self, request, pk):
        try:
            payment_order = get_object_or_404(PaymentOrder, pk=pk)
            payload = json.loads(request.body or '{}')
            factor_ids = payload.get('factor_ids') or []
            if not isinstance(factor_ids, list) or not factor_ids:
                return JsonResponse({'success': False, 'message': 'factor_ids نامعتبر است.'}, status=400)

            # Filter factors within same organization (safety)
            factors_qs = Factor.objects.filter(pk__in=factor_ids)
            if hasattr(factors_qs.model, 'organization') and payment_order.organization_id:
                factors_qs = factors_qs.filter(organization_id=payment_order.organization_id)

            factors = list(factors_qs)
            if not factors:
                return JsonResponse({'success': False, 'message': 'فاکتور معتبری یافت نشد.'}, status=404)

            payment_order.related_factors.add(*[f.pk for f in factors])

            # Optional: log
            ApprovalLog.objects.create(
                content_type=ContentType.objects.get_for_model(payment_order),
                object_id=payment_order.id,
                to_status=payment_order.status,
                action=Action.objects.filter(code='LINK').first() if Action.objects.filter(code='LINK').exists() else None,
                user=request.user,
                comment=f"الحاق {len(factors)} فاکتور به دستور پرداخت"
            )

            return JsonResponse({
                'success': True,
                'message': f'{len(factors)} فاکتور به دستور پرداخت الصاق شد.',
                'attached_ids': [f.pk for f in factors]
            })
        except Exception as e:
            logger.error(f"[ATTACH_FACTORS] error: {e}", exc_info=True)
            return JsonResponse({'success': False, 'message': 'خطای غیرمنتظره رخ داد.'}, status=500)
