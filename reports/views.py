import json
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.core.serializers.json import DjangoJSONEncoder as DecimalEncoder
from django.db.models import F
from django.db.models import Sum, Count, Avg, Q
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import TemplateView

from core.PermissionBase import PermissionBaseView  # فرض می‌کنم این مسیر درسته
from core.models import Organization, Status, Project
from core.views import DecimalEncoder
from reports.forms import FinancialReportForm
from reports.models import FinancialReport
from tankhah.models import Tankhah, ApprovalLog, Factor, TankhahDocument, FactorItem

User = get_user_model()
# Create your views here.
from django.views.generic import DetailView
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from .models import FinancialReport, Tankhah
from .forms import FinancialReportForm
from django.http import Http404
import logging
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Prefetch, Q, DecimalField, Count
from django.db.models.functions import Coalesce
from django.views.generic import DetailView
from django.utils.translation import gettext_lazy as _
import jdatetime # برای نمایش تاریخ شمسی

logger = logging.getLogger(__name__)

# مدل‌های مورد نیاز
from budgets.models import BudgetAllocation,  BudgetTransaction
from core.models import SubProject
from core.models import Organization, Project, Status # و هر مدل دیگری از core که لازم است
# from core.PermissionBase import PermissionBaseView # اگر از این استفاده می‌کنید
from django.contrib.auth.mixins import LoginRequiredMixin # جایگزین ساده

# توابع محاسباتی بودجه
from budgets.budget_calculations import (
    get_project_total_budget,
    get_project_remaining_budget,
    get_subproject_remaining_budget, calculate_remaining_amount,

)

class TankhahFinancialReportView(PermissionBaseView, DetailView):
    model = Tankhah
    template_name = 'reports/financial_report.html'
    permission_codenames = ['tankhah.Tankhah_view']
    check_organization = True

    def get_object(self, queryset=None):
        tankhah = super().get_object(queryset)
        # شرط: فقط برای مرحله آخر قبل از پرداخت (مثلاً HQ_FIN_PENDING)
        # if tankhah.current_stage.name != 'HQ_FIN_PENDING':
        #     raise Http404("گزارش مالی فقط در مرحله نهایی قبل از پرداخت قابل دسترسی است.")
        return tankhah

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object
        report, created = FinancialReport.objects.get_or_create(tankhah=tankhah)

        # تولید گزارش اولیه یا بروزرسانی
        if created or tankhah.status != report.last_status:
            report.generate_report()
            report.last_status = tankhah.status
            report.save()

        # اگه PAID شد و شماره پرداخت داره
        if tankhah.status == 'PAID' and tankhah.payment_number:
            report.payment_number = tankhah.payment_number
            report.generate_report()
            report.save()

        context['form'] = FinancialReportForm(instance=report)
        context['report'] = report
        context['title'] = f"گزارش مالی تنخواه {tankhah.number}"
        context['project'] = tankhah.project
        context['subproject'] = tankhah.subproject
        return context

    def post(self, request, *args, **kwargs):
        tankhah = self.get_object()
        report, created = FinancialReport.objects.get_or_create(tankhah=tankhah)
        form = FinancialReportForm(request.POST, instance=report)

        if form.is_valid():
            form.save()
            report.generate_report()
            messages.success(request, _("شماره پرداخت با موفقیت ذخیره شد."))
        else:
            messages.error(request, _("خطا در ذخیره شماره پرداخت."))

        return redirect('tankhah_financial_report', pk=tankhah.pk)
#################################
def print_financial_report(request, report_id):
    return HttpResponse(f"چاپ گزارش {report_id}")
def send_to_accounting(request, report_id):
    return HttpResponse(f"ارسال گزارش {report_id} به حسابداری")
######
class TankhahDetailView(PermissionBaseView, TemplateView):
    template_name = 'Reports/tankhah_detail.html'
    permission_codenames = ['tankhah.Tankhah_view']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_orgs = [up.post.organization for up in user.userpost_set.all()]
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)

        # فیلترها
        org_id = self.request.GET.get('org')
        project_id = self.request.GET.get('project')
        search_query = self.request.GET.get('search', '')

        # گرفتن تنخواه‌ها
        if is_hq_user:
            tankhahs = Tankhah.objects.all()
            organizations = Organization.objects.exclude(org_type='HQ')
        else:
            tankhahs = Tankhah.objects.filter(organization__in=user_orgs)
            organizations = user_orgs

        if org_id:
            tankhahs = tankhahs.filter(organization_id=org_id)
        if project_id:
            tankhahs = tankhahs.filter(project_id=project_id)
        if search_query:
            tankhahs = tankhahs.filter(id__icontains=search_query)  # جستجو بر اساس ID

        # صفحه‌بندی
        paginator = Paginator(tankhahs, 10)  # 10 تنخواه در هر صفحه
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj

        # سازمان‌ها و پروژه‌ها برای نوار کناری
        org_data = []
        for org in organizations:
            org_tankhahs = tankhahs.filter(organization=org)
            projects = Project.objects.filter(organizations=org)
            org_info = {
                'id': org.id,
                'name': org.name,
                'tankhah_count': org_tankhahs.count(),
                'projects': [{'id': p.id, 'name': p.name, 'tankhah_count': org_tankhahs.filter(project=p).count()} for p
                             in projects]
            }
            org_data.append(org_info)
        context['org_data'] = org_data

        return context


# -------------------------
#  New
# -------------------------
# ===== IMPORTS & DEPENDENCIES =====
import json
import logging
from decimal import Decimal
from datetime import timedelta
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db.models import Sum, Count, Avg, F, Q, Subquery, OuterRef
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_str
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from django.utils.functional import cached_property

# Your project's models and base views
from core.PermissionBase import PermissionBaseView
from core.models import Organization, Project, Status, Action
from tankhah.models import Tankhah, Factor, FactorItem, ApprovalLog, TankhahDocument



# KNOWLEDGE_BIT: For complex views, it's better to have a dedicated utility file.
# For now, we'll keep the logic here.

# ===== THE REFACTORED AND OPTIMIZED VIEW =====

class FinancialDashboardViewasdasdasd(PermissionBaseView, TemplateView):
    template_name = 'Tankhah/Reports/calc_dashboard.html'
    permission_required = ['tankhah.Dashboard__view']

    # Using cached_property to avoid re-calculating on every access
    @cached_property
    def is_hq_user(self):
        """Checks if the current user is an HQ user."""
        user = self.request.user
        return (user.is_superuser or
                user.has_perm('tankhah.Tankhah_view_all') or
                user.userpost_set.filter(is_active=True, post__organization__org_type__fname='HQ').exists())

    @cached_property
    def get_base_queryset(self):
        """
        #BEST_PRACTICE: Creates the base, permission-filtered queryset for Tankhahs.
        This is the single source of truth for all subsequent calculations.
        """
        user = self.request.user
        if self.is_hq_user:
            queryset = Tankhah.objects.all()
        else:
            user_org_pks = user.userpost_set.filter(is_active=True).values_list('post__organization_id', flat=True)
            queryset = Tankhah.objects.filter(organization_id__in=user_org_pks)

        project_id = self.request.GET.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # Pre-fetching related models to reduce queries later
        return queryset.select_related('organization', 'project', 'status')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        base_tankhah_qs = self.get_base_queryset

        # 1. General Stats (Optimized)
        context.update(self._get_general_stats(base_tankhah_qs))

        # 2. Status Stats (Corrected Query)
        context.update(self._get_status_stats(base_tankhah_qs))

        # 3. Factor Stats (Corrected Query)
        context.update(self._get_factor_stats(base_tankhah_qs))

        # 4. Organization Performance Data (Optimized with Subqueries)
        context.update(self._get_organization_performance(base_tankhah_qs))

        # 5. User Performance Data (Optimized)
        context.update(self._get_user_performance(base_tankhah_qs))

        # 6. Pagination (Done at the end)
        paginator = Paginator(base_tankhah_qs.order_by('-date'), 10)
        page_number = self.request.GET.get('page')
        context['page_obj'] = paginator.get_page(page_number)
        # -+-------------------------------------------------------------------


        # 1. گرفتن سازمان‌های کاربر و چک کردن HQ بودن
        user_orgs_qs = user.userpost_set.filter(is_active=True).select_related('post__organization')
        user_orgs = [up.post.organization for up in user_orgs_qs]
        is_hq_user = any(org.org_type and org.org_type.fname == 'HQ' for org in user_orgs)

        # 2. فیلتر کردن تنخواه‌ها و سازمان‌ها
        if self.request.user.is_superuser or self.request.user.has_perm('tankhah.Tankhah_view_all'):
            all_tankhahs = Tankhah.objects.all()
            organizations = Organization.objects.exclude(org_type__fname='HQ')
        else:
            all_tankhahs = Tankhah.objects.filter(organization__in=user_orgs)
            organizations = user_orgs

        # 3. فیلتر پروژه
        project_id = self.request.GET.get('project')
        if project_id:
            all_tankhahs = all_tankhahs.filter(project_id=project_id)

        # 4. صفحه‌بندی تنخواه‌ها
        # KNOWLEDGE_BIT: Always order a queryset before pagination for consistent results.
        paginator = Paginator(all_tankhahs.order_by('-date'), 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj

        # 5. محاسبات کلی
        # CRITICAL FIX: Changed status='PAID' to status__code='PAID'
        general_stats = all_tankhahs.aggregate(
            total_amount=Coalesce(Sum('amount'), Decimal('0')),
            archived_count=Count('id', filter=Q(is_archived=True)),
            total_count=Count('id'),
            avg_time=Avg(F('archived_at') - F('created_at'), filter=Q(status__code='PAID'))
        )
        context['total_tanbakh_amount'] = float(general_stats['total_amount'])
        context['archived_tanbakhs'] = general_stats['archived_count']
        context['total_tankhahs'] = general_stats['total_count']
        context['avg_processing_time'] = general_stats['avg_time'] or timedelta(0)

        # 6. کش کردن حجم تصاویر (کد شما صحیح و بهینه است)
        # ... (این بخش از کد شما دست نخورده باقی می‌ماند) ...

        # 7. آمار وضعیت تنخواه‌ها
        # CRITICAL FIX: Group by status name and code for chart labels
        status_counts = all_tankhahs.values('status__name', 'status__code').annotate(count=Count('id')).order_by()
        context['status_counts'] = {item['status__name']: item['count'] for item in status_counts if
                                    item['status__name']}

        # 8. تنخواه‌های در انتظار به تفکیک مرحله (فرض می‌کنیم WorkflowStage هنوز استفاده می‌شود)
        # ... (این بخش از کد شما دست نخورده باقی می‌ماند) ...

        # 9. محاسبات فاکتورها
        factors = Factor.objects.filter(tankhah__in=all_tankhahs)
        # CRITICAL FIX: Changed all status filters to status__code
        factor_stats = factors.aggregate(
            total_amount=Coalesce(Sum('amount'), Decimal('0')),
            approved_count=Count('id', filter=Q(status__code='APPROVED')),
            rejected_count=Count('id', filter=Q(status__code='REJECTED')),
            pending_count=Count('id', filter=Q(status__code='PENDING_APPROVAL'))
        )
        context['total_factor_amount'] = float(factor_stats['total_amount'])
        context['approved_factors'] = factor_stats['approved_count']
        context['rejected_factors'] = factor_stats['rejected_count']
        context['pending_factors'] = factor_stats['pending_count']

        # 10. گزارش زمانی (این بخش از کد شما دست نخورده است)
        # ...

        # 11. عملکرد کاربران
        # CRITICAL FIX: Changed action='APPROVE' to action__code='APPROVE' etc.
        user_performance = ApprovalLog.objects.filter(tankhah__in=all_tankhahs).values('user__username').annotate(
            total_approvals=Count('id', filter=Q(action__code='APPROVE')),
            total_rejections=Count('id', filter=Q(action__code='REJECT')),
            # avg_time=Avg(F('timestamp') - F('tankhah__created_at')) # This can be slow, commented out for now
        ).order_by('-total_approvals')
        context['user_performance'] = list(user_performance)

        # 12. دیتای چارت کاربران
        context['user_chart_data'] = json.dumps({
            'labels': [u['user__username'] for u in user_performance if u['user__username']],
            'datasets': [
                {'label': force_str(_('تأییدها')), 'data': [u['total_approvals'] for u in user_performance],
                 'backgroundColor': '#48bb78'},
                {'label': force_str(_('رد شده‌ها')), 'data': [u['total_rejections'] for u in user_performance],
                 'backgroundColor': '#f56565'},
            ]
        }, cls=DecimalEncoder)

        # 13. داده‌های سازمان‌ها (منطق حلقه اصلی شما حفظ شده است)
        org_data = []
        chart_labels = []
        chart_tankhah_amounts = []
        chart_factor_amounts = []
        for org in organizations:
            org_tankhahs = all_tankhahs.filter(organization=org)
            org_factors = factors.filter(tankhah__in=org_tankhahs)

            # CRITICAL FIX: Changed all status filters to status__code
            org_info = {
                'name': org.name,
                'total_tanbakh_amount': float(org_tankhahs.aggregate(total=Sum('amount'))['total'] or 0),
                'total_factor_amount': float(org_factors.aggregate(total=Sum('amount'))['total'] or 0),
                'approved_factors': org_factors.filter(status__code='APPROVED').count(),
                'rejected_factors': org_factors.filter(status__code='REJECTED').count(),
                'pending_factors': org_factors.filter(status__code='PENDING_APPROVAL').count(),
            }
            org_data.append(org_info)

            chart_labels.append(org.name)
            chart_tankhah_amounts.append(org_info['total_tanbakh_amount'])
            chart_factor_amounts.append(org_info['total_factor_amount'])

        context['org_data'] = org_data

        # 14. دیتای چارت مالی
        context['chart_data'] = json.dumps({
            'labels': chart_labels,
            'datasets': [
                {'label': force_str(_('مبلغ تنخواه‌ها')), 'data': chart_tankhah_amounts, 'backgroundColor': '#4299e1'},
                {'label': force_str(_('مبلغ فاکتورها')), 'data': chart_factor_amounts, 'backgroundColor': '#f56565'},
            ]
        }, cls=DecimalEncoder)

        # 15. دیتای چارت وضعیت تنخواه‌ها
        context['status_chart_data'] = json.dumps({
            'labels': list(context['status_counts'].keys()),
            'datasets': [{
                'label': force_str(_('تعداد تنخواه‌ها')),
                'data': list(context['status_counts'].values()),
                'backgroundColor': ['#4299e1', '#f56565', '#48bb78', '#ed8936', '#9f7aea', '#a0aec0', '#4a5568']
            }]
        }, cls=DecimalEncoder)

        return context
    def _get_general_stats(self, tankhah_qs):
        """Calculates and returns general dashboard statistics."""
        # Aggregate multiple stats in one DB hit
        general_stats = tankhah_qs.aggregate(
            total_amount=Coalesce(Sum('amount'), Decimal('0')),
            total_count=Count('id'),
            archived_count=Count('id', filter=Q(is_archived=True)),
            avg_time=Avg(F('archived_at') - F('created_at'), filter=Q(status__code='PAID'))
        )
        return {
            'total_tanbakh_amount': float(general_stats['total_amount']),
            'total_tankhahs': general_stats['total_count'],
            'archived_tanbakhs': general_stats['archived_count'],
            'avg_processing_time': general_stats['avg_time'] or timedelta(0),
        }

    def _get_status_stats(self, tankhah_qs):
        """
        #FIX: Correctly queries status counts and prepares data for the chart.
        """
        status_counts_qs = tankhah_qs.values('status__code', 'status__name').annotate(count=Count('id')).order_by()
        status_counts_dict = {
            item['status__name']: item['count'] for item in status_counts_qs if item['status__name']
        }

        status_chart_data = {
            'labels': list(status_counts_dict.keys()),
            'datasets': [{
                'label': force_str(_('تعداد تنخواه‌ها')),
                'data': list(status_counts_dict.values()),
                'backgroundColor': ['#4299e1', '#f56565', '#48bb78', '#ed8936', '#9f7aea']  # Add more colors if needed
            }]
        }
        return {'status_counts': status_counts_dict, 'status_chart_data': status_chart_data}

    def _get_factor_stats(self, tankhah_qs):
        """
        #FIX: Correctly queries factor counts based on status codes.
        """
        factors_qs = Factor.objects.filter(tankhah__in=tankhah_qs)
        factor_stats = factors_qs.aggregate(
            total_amount=Coalesce(Sum('amount'), Decimal('0')),
            approved_count=Count('id', filter=Q(status__code='APPROVED')),
            rejected_count=Count('id', filter=Q(status__code='REJECTED')),
            pending_count=Count('id', filter=Q(status__code='PENDING_APPROVAL')),
        )
        return {
            'total_factor_amount': float(factor_stats['total_amount']),
            'approved_factors': factor_stats['approved_count'],
            'rejected_factors': factor_stats['rejected_count'],
            'pending_factors': factor_stats['pending_count'],
        }

    def _get_organization_performance(self, tankhah_qs):
        """
        #PERFORMANCE_FIX: Uses Subqueries to calculate org stats efficiently, avoiding loops.
        """
        user = self.request.user
        if self.is_hq_user:
            org_qs = Organization.objects.exclude(org_type__fname='HQ')
        else:
            user_org_pks = user.userpost_set.filter(is_active=True).values_list('post__organization_id', flat=True)
            org_qs = Organization.objects.filter(pk__in=user_org_pks)

        # Define subqueries for aggregation
        tankhah_subquery = Tankhah.objects.filter(organization=OuterRef('pk'), pk__in=tankhah_qs)
        factor_subquery = Factor.objects.filter(tankhah__organization=OuterRef('pk'), tankhah__in=tankhah_qs)

        org_data_qs = org_qs.annotate(
            total_tanbakh_amount=Subquery(
                tankhah_subquery.values('organization').annotate(total=Sum('amount')).values('total')
            ),
            total_factor_amount=Subquery(
                factor_subquery.values('tankhah__organization').annotate(total=Sum('amount')).values('total')
            ),
            approved_factors_count=Subquery(
                factor_subquery.filter(status__code='APPROVED').values('tankhah__organization').annotate(
                    count=Count('id')).values('count')
            )
            # Add more subqueries for other stats if needed
        ).values('name', 'total_tanbakh_amount', 'total_factor_amount', 'approved_factors_count')

        org_chart_data = {
            'labels': [org['name'] for org in org_data_qs],
            'datasets': [
                {'label': force_str(_('مبلغ تنخواه‌ها')),
                 'data': [float(org['total_tanbakh_amount'] or 0) for org in org_data_qs],
                 'backgroundColor': '#4299e1'},
                {'label': force_str(_('مبلغ فاکتورها')),
                 'data': [float(org['total_factor_amount'] or 0) for org in org_data_qs], 'backgroundColor': '#f56565'},
            ]
        }
        return {'org_data': list(org_data_qs), 'org_chart_data': org_chart_data}

    def _get_user_performance(self, tankhah_qs):
        """
        #FIX: Correctly queries user performance based on action codes.
        """
        user_performance_qs = ApprovalLog.objects.filter(
            tankhah__in=tankhah_qs
        ).values('user__username').annotate(
            total_approvals=Count('id', filter=Q(action__code='APPROVE')),
            total_rejections=Count('id', filter=Q(action__code='REJECT')),
        ).order_by('-total_approvals')

        user_chart_data = {
            'labels': [u['user__username'] for u in user_performance_qs if u['user__username']],
            'datasets': [
                {'label': force_str(_('تأییدها')), 'data': [u['total_approvals'] for u in user_performance_qs],
                 'backgroundColor': '#48bb78'},
                {'label': force_str(_('رد شده‌ها')), 'data': [u['total_rejections'] for u in user_performance_qs],
                 'backgroundColor': '#f56565'},
            ]
        }
        return {'user_performance': list(user_performance_qs), 'user_chart_data': user_chart_data}


# KNOWLEDGE_BIT: A custom JSON encoder is crucial for handling complex Python types
# like Decimal when converting to JSON for JavaScript.
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, timedelta):
            return obj.total_seconds()
        return super(DecimalEncoder, self).default(obj)


# ===== THE FINAL, COMPLETE AND CORRECTED VIEW =====

class FinancialDashboardView(PermissionBaseView, TemplateView):
    template_name = 'Tankhah/Reports/calc_dashboard.html'
    permission_required = ['tankhah.Dashboard__view']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    # Using cached_property avoids re-calculating the same value multiple times per request.
    @cached_property
    def is_hq_user(self):
        """Checks if the current user is an HQ user."""
        user = self.request.user
        return (user.is_superuser or
                user.has_perm('tankhah.Tankhah_view_all') or
                user.userpost_set.filter(is_active=True, post__organization__org_type__fname='HQ').exists())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # 1. Base QuerySet Initialization
        if self.is_hq_user:
            all_tankhahs = Tankhah.objects.all()
            organizations = Organization.objects.exclude(org_type__fname='HQ')
        else:
            user_org_pks = user.userpost_set.filter(is_active=True).values_list('post__organization_id', flat=True)
            all_tankhahs = Tankhah.objects.filter(organization_id__in=user_org_pks)
            organizations = Organization.objects.filter(pk__in=user_org_pks)

        # 2. Apply Project Filter
        project_id = self.request.GET.get('project')
        if project_id:
            all_tankhahs = all_tankhahs.filter(project_id=project_id)

        # Add projects to context for the filter dropdown
        context['projects_for_filter'] = Project.objects.filter(is_active=True)

        # 3. Pagination
        paginator = Paginator(all_tankhahs.select_related('organization', 'project', 'status').order_by('-date'), 10)
        page_number = self.request.GET.get('page')
        context['page_obj'] = paginator.get_page(page_number)

        # 4. General Stats Calculation
        # CRITICAL FIX: Changed status='PAID' to status__code='PAID'
        general_stats = all_tankhahs.aggregate(
            total_amount=Coalesce(Sum('amount'), Decimal('0')),
            archived_count=Count('id', filter=Q(is_archived=True)),
            total_count=Count('id'),
            avg_time=Avg(F('archived_at') - F('created_at'), filter=Q(status__code='PAID'))
        )
        context['total_tanbakh_amount'] = float(general_stats['total_amount'])
        context['archived_tanbakhs'] = general_stats['archived_count']
        context['total_tankhahs'] = general_stats['total_count']
        context['avg_processing_time'] = general_stats['avg_time'] or timedelta(0)

        # 5. Image Size Calculation (from your original code)
        cache_key = f"total_image_size_{user.id}_{project_id or 'all'}"
        total_image_size = cache.get(cache_key)
        if total_image_size is None:
            # This can be slow, but we keep the original logic
            image_qs = TankhahDocument.objects.filter(tankhah__in=all_tankhahs)
            total_image_size = sum(
                doc.file_size for doc in image_qs if doc.file_size
            )
            cache.set(cache_key, total_image_size, 3600)
        context['total_image_size_mb'] = (total_image_size or 0) / (1024 * 1024)

        # 6. Factor Stats
        factors = Factor.objects.filter(tankhah__in=all_tankhahs)
        # CRITICAL FIX: Changed all status filters to status__code
        factor_stats = factors.aggregate(
            total_amount=Coalesce(Sum('amount'), Decimal('0')),
            approved_count=Count('id', filter=Q(status__code='APPROVED')),
            rejected_count=Count('id', filter=Q(status__code='REJECTED')),
            pending_count=Count('id', filter=Q(status__code='PENDING_APPROVAL')),
        )
        context.update({
            'total_factor_amount': float(factor_stats['total_amount']),
            'approved_factors': factor_stats['approved_count'],
            'rejected_factors': factor_stats['rejected_count'],
            'pending_factors': factor_stats['pending_count'],
        })

        # 7. Chart Data: Status Counts
        status_counts = all_tankhahs.values('status__name').annotate(count=Count('id')).order_by('-count')
        context['status_chart_data'] = {
            'labels': [s['status__name'] for s in status_counts if s['status__name']],
            'datasets': [{
                'label': force_str(_('تعداد تنخواه‌ها')),
                'data': [s['count'] for s in status_counts if s['status__name']],
                'backgroundColor': ['#4299e1', '#f56565', '#48bb78', '#ed8936', '#9f7aea', '#a0aec0', '#4a5568']
            }]
        }

        # 8. Chart Data: User Performance
        # CRITICAL FIX: Changed action filters to action__code
        user_performance = ApprovalLog.objects.filter(
            tankhah__in=all_tankhahs, user__username__isnull=False
        ).values('user__username').annotate(
            total_approvals=Count('id', filter=Q(action__code='APPROVE')),
            total_rejections=Count('id', filter=Q(action__code='REJECT'))
        ).order_by('-total_approvals')[:10]  # Limit to top 10 users for performance
        context['user_performance'] = list(user_performance)
        context['user_chart_data'] = {
            'labels': [u['user__username'] for u in user_performance],
            'datasets': [
                {'label': force_str(_('تأییدها')), 'data': [u['total_approvals'] for u in user_performance],
                 'backgroundColor': '#48bb78'},
                {'label': force_str(_('رد شده‌ها')), 'data': [u['total_rejections'] for u in user_performance],
                 'backgroundColor': '#f56565'},
            ]
        }

        # 9. Chart Data: Organization Performance (Looping approach from your original code is preserved)
        org_data = []
        for org in organizations:
            org_tankhahs = all_tankhahs.filter(organization=org)
            org_factors = factors.filter(tankhah__in=org_tankhahs)

            # CRITICAL FIX: Use status__code in filters
            org_info = {
                'name': org.name,
                'total_tanbakh_amount': float(org_tankhahs.aggregate(total=Sum('amount'))['total'] or 0),
                'total_factor_amount': float(org_factors.aggregate(total=Sum('amount'))['total'] or 0),
                'approved_factors': org_factors.filter(status__code='APPROVED').count(),
            }
            org_data.append(org_info)

        context['org_data'] = org_data
        context['org_chart_data'] = {
            'labels': [org['name'] for org in org_data],
            'datasets': [
                {'label': force_str(_('مبلغ تنخواه‌ها')), 'data': [org['total_tanbakh_amount'] for org in org_data],
                 'backgroundColor': '#4299e1'},
                {'label': force_str(_('مبلغ فاکتورها')), 'data': [org['total_factor_amount'] for org in org_data],
                 'backgroundColor': '#f56565'},
            ]
        }

        # Serialize chart data using the custom encoder
        context['status_chart_data_json'] = json.dumps(context['status_chart_data'], cls=DecimalEncoder)
        context['user_chart_data_json'] = json.dumps(context['user_chart_data'], cls=DecimalEncoder)
        context['org_chart_data_json'] = json.dumps(context['org_chart_data'], cls=DecimalEncoder)

        return context

# -------------------------


#-- گزارش تخصیص بودجه
"""
این تابع مسئول محاسبه و برگرداندن مبلغ باقیمانده برای یک نمونه BudgetAllocation خاص است. این مبلغ باقیمانده از مقدار اولیه‌ای که به این BudgetAllocation تخصیص داده شده، پس از کسر تمام هزینه‌های (مصرف‌های) ثبت شده برای آن و اضافه کردن تمام مبالغ بازگشتی به آن، به دست می‌آید.
این تابع برای نمایش مانده واقعی یک سرفصل بودجه در یک سازمان خاص در یک دوره بودجه خاص بسیار کاربردی است.
نحوه محاسبه:
مقدار اولیه تخصیص (budget_allocation_instance.allocated_amount) را دریافت می‌کند.
تمام BudgetTransactionهای مرتبط با این budget_allocation_instance را که نوعشان CONSUMPTION (مصرف) است، جمع می‌زند.
تمام BudgetTransactionهای مرتبط با این budget_allocation_instance را که نوعشان RETURN (بازگشت) است، جمع می‌زند.
باقیمانده را به این صورت محاسبه می‌کند: مانده = مبلغ اولیه - مجموع مصارف + مجموع بازگشت‌ها.
اطمینان حاصل می‌کند که مانده منفی برنگرداند (حداقل صفر).
پیاده‌سازی:
تابع calculate_remaining_amount که شما در budget_calculations.py دارید، دقیقاً همین کار را انجام می‌دهد! فقط کافیست آن را با آرگومان صحیح فراخوانی کنید.
"""
def get_budget_allocation_remaining_amount(budget_allocation_instance: BudgetAllocation, use_cache=True) -> Decimal:
    """
    محاسبه بودجه باقی‌مانده برای یک نمونه BudgetAllocation خاص.
    از تابع عمومی calculate_remaining_amount استفاده می‌کند.

    Args:
        budget_allocation_instance (BudgetAllocation): نمونه‌ای از مدل BudgetAllocation.
        use_cache (bool): آیا از کش برای این محاسبه استفاده شود یا خیر.

    Returns:
        Decimal: بودجه باقیمانده.
    """
    from budgets.models import BudgetAllocation
    if not isinstance(budget_allocation_instance, BudgetAllocation):
        logger.error(f"Invalid input: Expected BudgetAllocation instance, got {type(budget_allocation_instance)}")
        raise TypeError("ورودی باید نمونه‌ای از BudgetAllocation باشد.")

    # تعریف کلید کش
    cache_key = f"budget_allocation_remaining_{budget_allocation_instance.pk}"
    if use_cache:
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            logger.debug(f"Returning cached remaining amount for BudgetAllocation {budget_allocation_instance.pk}: {cached_value}")
            return cached_value

    # فراخوانی تابع عمومی calculate_remaining_amount
    # amount_field در BudgetAllocation همان 'allocated_amount' است.
    remaining_amount = calculate_remaining_amount(
        allocation=budget_allocation_instance,
        amount_field='allocated_amount',
        model_name='BudgetAllocation'
    )

    if use_cache:
        cache.set(cache_key, remaining_amount, timeout=300) # کش برای ۵ دقیقه
        logger.debug(f"Cached remaining amount for BudgetAllocation {budget_allocation_instance.pk}: {remaining_amount}")

    return remaining_amount

"""
شرح وظیفه:
این تابع مسئول محاسبه و برگرداندن مجموع خالص مبلغ مصرف شده برای یک نمونه BudgetAllocation خاص است. "خالص" به این معنی است که مبالغ بازگشتی از مبالغ مصرفی کسر می‌شوند.
این تابع برای فهمیدن اینکه چقدر از یک سرفصل بودجه خاص در یک سازمان واقعاً هزینه شده است، مفید است.
نحوه محاسبه:
تمام BudgetTransactionهای مرتبط با این budget_allocation_instance را که نوعشان CONSUMPTION (مصرف) است، جمع می‌زند.
تمام BudgetTransactionهای مرتبط با این budget_allocation_instance را که نوعشان RETURN (بازگشت) است، جمع می‌زند.
مصرف خالص را به این صورت محاسبه می‌کند: مصرف خالص = مجموع مصارف - مجموع بازگشت‌ها.
اطمینان حاصل می‌کند که مصرف خالص منفی برنگرداند (حداقل صفر، اگر بازگشت‌ها بیشتر از مصرف‌ها باشند که منطقی نیست اما برای جلوگیری از خطا در نظر گرفته می‌شود).
"""
def calculate_total_consumed_on_budget_allocation(budget_allocation_instance: BudgetAllocation,
                                                  use_cache=True) -> Decimal:
    """
    محاسبه مجموع خالص مبلغ مصرف شده برای یک نمونه BudgetAllocation.
    مصرف خالص = (مجموع تراکنش‌های مصرف) - (مجموع تراکنش‌های بازگشت).

    Args:
        budget_allocation_instance (BudgetAllocation): نمونه‌ای از مدل BudgetAllocation.
        use_cache (bool): آیا از کش برای این محاسبه استفاده شود یا خیر.

    Returns:
        Decimal: مجموع خالص مصرف شده.
    """
    if not isinstance(budget_allocation_instance, BudgetAllocation):
        logger.error(f"Invalid input: Expected BudgetAllocation instance, got {type(budget_allocation_instance)}")
        raise TypeError("ورودی باید نمونه‌ای از BudgetAllocation باشد.")

    cache_key = f"budget_allocation_total_consumed_{budget_allocation_instance.pk}"
    if use_cache:
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            logger.debug(
                f"Returning cached total consumed for BudgetAllocation {budget_allocation_instance.pk}: {cached_value}")
            return cached_value

    # واکشی تمام تراکنش‌های مصرف و بازگشت در یک کوئری برای بهینگی (اگر تعداد زیاد است)
    # یا دو کوئری جداگانه مانند تابع calculate_remaining_amount
    # در اینجا از روش مشابه calculate_remaining_amount استفاده می‌کنیم برای سادگی و سازگاری

    consumed_transactions = BudgetTransaction.objects.filter(
        allocation=budget_allocation_instance,
        transaction_type='CONSUMPTION'
    )

    total_consumed = consumed_transactions.aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
    )['total']
    logger.debug(f"Total CONSUMPTION for BudgetAllocation {budget_allocation_instance.pk}: {total_consumed}")

    returned_transactions = BudgetTransaction.objects.filter(
        allocation=budget_allocation_instance,
        transaction_type='RETURN'
    )
    total_returned = returned_transactions.aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
    )['total']
    logger.debug(f"Total RETURN for BudgetAllocation {budget_allocation_instance.pk}: {total_returned}")

    net_consumed = total_consumed - total_returned

    # مصرف خالص نمی‌تواند منفی باشد (اگر بازگشت‌ها بیشتر از مصرف‌ها باشند)
    # اما در عمل، بازگشت نباید از مصرف بیشتر شود.
    # اگر این اتفاق بیفتد، نشان‌دهنده یک مشکل در داده یا منطق ثبت تراکنش است.
    # با این حال، برای این تابع، می‌توانیم آن را صفر در نظر بگیریم یا مقدار منفی را برگردانیم تا مشکل مشخص شود.
    # فعلا صفر در نظر می‌گیریم.
    result_net_consumed = max(net_consumed, Decimal('0.00'))

    if use_cache:
        cache.set(cache_key, result_net_consumed, timeout=300)  # کش برای ۵ دقیقه
        logger.debug(
            f"Cached total consumed for BudgetAllocation {budget_allocation_instance.pk}: {result_net_consumed}")

    logger.info(
        f"Net consumed for BudgetAllocation {budget_allocation_instance.pk}: {result_net_consumed} (Raw Consumed: {total_consumed}, Raw Returned: {total_returned})")
    return result_net_consumed
class old__BudgetAllocationReportView(LoginRequiredMixin, DetailView): # یا PermissionBaseView
    model = BudgetAllocation
    template_name = 'reports/report_budget_allocation_report_detail.html' # تمپلیت جدید
    context_object_name = 'budget_allocation' # آبجکت BudgetAllocation اصلی
    # pk_url_kwarg = 'pk' # اگر نام پارامتر در URL 'pk' باشد، این خط لازم نیست

    # permission_codenames = ['budgets.view_budgetallocation_report'] # یک پرمیشن جدید برای این گزارش
    # check_organization = True # اگر لازم است دسترسی سازمانی چک شود

    def get_queryset(self):
        return super().get_queryset().select_related(
            'organization',
            'budget_period',
            'budget_item',
            'project', # اگر BudgetAllocation مستقیماً به یک پروژه هم لینک می‌شود (علاوه بر ProjectBudgetAllocation)
            'created_by'
        ).prefetch_related(
            Prefetch(
                'project_allocations', # related_name از BudgetAllocation به ProjectBudgetAllocation
                queryset=BudgetAllocation.objects.filter(is_active=True).select_related(
                    'project', 'subproject', 'created_by'
                ).order_by('project__name', 'subproject__name')
            ),
            Prefetch(
                'transactions', # related_name از BudgetAllocation به BudgetTransaction
                queryset=BudgetTransaction.objects.select_related('related_tankhah', 'created_by').order_by('-timestamp')
            )
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # می‌توانید بررسی‌های اضافی مانند is_active را اینجا انجام دهید
        if not obj.is_active: # یا هر شرط دیگری
            logger.warning(f"Attempted to view report for inactive BudgetAllocation (PK: {obj.pk}).")
            messages.warning(self.request, _('این تخصیص بودجه فعال نیست.'))
            raise Http404
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # self.object همان نمونه BudgetAllocation است
        budget_allocation_instance = self.object
        logger.info(f"Preparing report context for BudgetAllocation PK: {budget_allocation_instance.pk}")

        # --- ۱. اطلاعات پایه BudgetAllocation ---
        context['report_title'] = _("گزارش تفصیلی تخصیص بودجه")
        context['organization'] = budget_allocation_instance.organization
        context['budget_period'] = budget_allocation_instance.budget_period
        context['budget_item'] = budget_allocation_instance.budget_item
        context['allocated_amount_main'] = budget_allocation_instance.allocated_amount
        context['allocation_date_main'] = budget_allocation_instance.allocation_date
        context['description_main'] = budget_allocation_instance.description
        context['is_active_main'] = budget_allocation_instance.is_active
        context['is_stopped_main'] = budget_allocation_instance.is_stopped
        context['created_by_main'] = budget_allocation_instance.created_by

        # --- ۲. محاسبه مصرف و مانده BudgetAllocation اصلی ---
        # استفاده از تابع محاسباتی (اگر وجود دارد و بهینه است)
        total_consumed_main = calculate_total_consumed_on_budget_allocation(budget_allocation_instance)
        remaining_main = get_budget_allocation_remaining_amount(budget_allocation_instance)
        # یا محاسبه مستقیم از prefetch شده‌ها (اگر تابع ندارید):
        # transactions_main = budget_allocation_instance.transactions.all()
        # consumed_direct_on_main = sum(t.amount for t in transactions_main if t.transaction_type == 'CONSUMPTION')
        # returned_direct_to_main = sum(t.amount for t in transactions_main if t.transaction_type == 'RETURN')
        # total_consumed_main = consumed_direct_on_main - returned_direct_to_main
        # remaining_main = budget_allocation_instance.allocated_amount - total_consumed_main
        # (این محاسبه ساده‌شده است و باید با منطق get_remaining_amount شما یکی باشد)


        context['consumed_amount_main'] = total_consumed_main
        context['remaining_amount_main'] = remaining_main
        context['utilization_percentage_main'] = (total_consumed_main / budget_allocation_instance.allocated_amount * 100) \
            if budget_allocation_instance.allocated_amount > 0 else 0

        # --- ۳. لیست ProjectBudgetAllocations مرتبط (توزیع بودجه به پروژه‌ها) ---
        project_allocations_details = []
        total_allocated_to_projects_from_this_ba = Decimal('0')

        # project_allocations از prefetch می‌آید
        for pba in budget_allocation_instance.project_allocations.all():
            total_allocated_to_projects_from_this_ba += pba.allocated_amount

            # مصرف و مانده برای هر ProjectBudgetAllocation
            # این بخش نیاز به دقت دارد: آیا مصرف مستقیماً روی PBA ثبت می‌شود
            # یا مصرف کل پروژه/زیرپروژه از تمام منابع مد نظر است؟
            # برای این گزارش، منطقی است که مصرف *از طریق* این PBA را نشان دهیم.
            # اگر BudgetTransaction به BudgetAllocation اصلی لینک است، باید راهی برای تفکیک
            # مصرف مربوط به این پروژه/زیرپروژه خاص از آن BudgetAllocation پیدا کنیم.
            # این معمولاً نیاز به لینک BudgetTransaction به Project/SubProject دارد.

            # سناریوی ساده‌تر: نمایش مانده کلی پروژه/زیرپروژه (نه فقط از این تخصیص)
            target_entity_name = ""
            target_entity_remaining = Decimal('0')
            target_entity_total_allocated = Decimal('0')

            if pba.subproject:
                target_entity_name = f"{pba.project.name} / {pba.subproject.name}"
                target_entity_remaining = get_subproject_remaining_budget(pba.subproject)
                target_entity_total_allocated = BudgetAllocation.objects.filter(subproject=pba.subproject, is_active=True).aggregate(total=Coalesce(Sum('allocated_amount'), Decimal('0')))['total']
            elif pba.project:
                target_entity_name = pba.project.name
                target_entity_remaining = get_project_remaining_budget(pba.project)
                target_entity_total_allocated = BudgetAllocation.objects.filter(project=pba.project, subproject__isnull=True, is_active=True).aggregate(total=Coalesce(Sum('allocated_amount'), Decimal('0')))['total']

            project_allocations_details.append({
                'instance': pba,
                'target_name': target_entity_name,
                'allocated_to_target_from_this_pba': pba.allocated_amount,
                'target_total_allocated_overall': target_entity_total_allocated, # کل بودجه تخصیص یافته به این پروژه/زیرپروژه از همه جا
                'target_remaining_overall': target_entity_remaining, # مانده کلی این پروژه/زیرپروژه
                # برای درصد مصرف، باید مصرف را هم داشته باشیم
                'target_consumed_overall': target_entity_total_allocated - target_entity_remaining,
                'target_utilization_overall': ( (target_entity_total_allocated - target_entity_remaining) / target_entity_total_allocated * 100) if target_entity_total_allocated > 0 else 0,
            })
        context['project_allocations_list'] = project_allocations_details
        context['total_allocated_to_projects_from_this_ba'] = total_allocated_to_projects_from_this_ba
        context['unallocated_from_main_ba_to_projects'] = budget_allocation_instance.allocated_amount - total_allocated_to_projects_from_this_ba

        # --- ۴. لیست تراکنش‌های اخیر روی BudgetAllocation اصلی ---
        # transactions از prefetch می‌آید
        context['recent_transactions_main'] = budget_allocation_instance.transactions.all()[:15] # 15 تراکنش اخیر

        logger.info(f"Report context for BudgetAllocation PK: {budget_allocation_instance.pk} prepared successfully.")
        return context


# توابع محاسبات بودجه
# مطمئن شوید این توابع در فایل budgets/budget_calculations.py یا جای دیگری تعریف شده‌اند:
# def calculate_total_consumed_on_budget_allocation(budget_allocation_instance): ...
# def get_budget_allocation_remaining_amount(budget_allocation_instance): ...
# def get_project_remaining_budget(project_instance): ...
# def get_subproject_remaining_budget(subproject_instance): ...
# اگر این توابع را ندارید، باید منطق محاسبه را مستقیماً در get_context_data بنویسید یا آن‌ها را ایجاد کنید.

class BudgetAllocationReportView(PermissionBaseView, DetailView):  # یا PermissionBaseView
    model = BudgetAllocation
    template_name = 'reports/report_budget_allocation_report_detail.html'
    context_object_name = 'budget_allocation'
    pk_url_kwarg = 'pk'  # اگر نام پارامتر در URL 'pk' است
    permission_codename = 'BudgetAllocation.BudgetAllocation_reports'
    # اگر از PermissionBaseView استفاده می‌کنید، این خطوط را فعال کنید:
    # permission_codenames = ['budgets.view_budget_allocation_report'] # پرمیشن مناسب
    # check_organization = True # اگر لازم است دسترسی سازمانی چک شود

    def get_queryset(self):
        # Prefetch کردن تراکنش‌ها و تنخواه‌های مرتبط با این BudgetAllocation
        # 'transactions' و 'tankhahs' باید related_nameهای صحیح در مدل‌های BudgetTransaction و Tankhah باشند.
        return super().get_queryset().select_related(
            'organization',
            'budget_period',
            'budget_item',
            'project',  # BudgetAllocation مستقیماً به پروژه لینک می‌شود
            'subproject',  # BudgetAllocation مستقیماً به زیرپروژه لینک می‌شود
            'created_by'
        ).prefetch_related(
            # Prefetch تمام تراکنش‌های مرتبط با این BudgetAllocation
            Prefetch(
                'transactions',
                queryset=BudgetTransaction.objects.select_related('related_tankhah', 'created_by').order_by(
                    '-timestamp')
            ),
            # Prefetch تمام تنخواه‌های مرتبط با این BudgetAllocation (از فیلد project_budget_allocation در Tankhah)
            Prefetch(
                'tankhahs',  # این همان related_name='tankhahs' است که در Tankhah.project_budget_allocation تعریف شده.
                queryset=Tankhah.objects.select_related('project', 'subproject', 'organization', 'current_stage',
                                                        'created_by').order_by('-created_at')
            )
        )

    def get_object(self, queryset=None):
        # تنظیم kwargs برای get_object
        if not hasattr(self, 'kwargs'):
            self.kwargs = {'pk': self.kwargs.get('pk')}
        
        obj = super().get_object(queryset)
        # بررسی دسترسی سازمانی (اگر check_organization = True در PermissionBaseView نیست)
        # اگر از PermissionBaseView استفاده می‌کنید، این بخش را داخل آن هندل کنید.
        # if hasattr(self, 'check_organization') and self.check_organization:
        #     if obj.organization not in self.request.user.user_orgs: # فرض بر اینکه user_orgs را در request.user دارید
        #         raise Http404(_("شما به این سازمان دسترسی ندارید."))

        if not obj.is_active:  # یا هر شرط دیگری که باعث عدم نمایش گزارش شود
            logger.warning(
                f"Attempted to view report for inactive BudgetAllocation (PK: {obj.pk}). User: {self.request.user.username}")
            messages.warning(self.request, _('این تخصیص بودجه فعال نیست و گزارش آن قابل مشاهده نمی‌باشد.'))
            raise Http404

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budget_allocation_instance = self.object  # BudgetAllocation اصلی که گزارش آن را می‌خواهیم
        logger.info(
            f"Preparing report context for BudgetAllocation PK: {budget_allocation_instance.pk}. User: {self.request.user.username}")

        # --- ۱. اطلاعات پایه BudgetAllocation اصلی ---
        context['report_title'] = _("گزارش تفصیلی تخصیص بودجه")
        context['organization'] = budget_allocation_instance.organization
        context['budget_period'] = budget_allocation_instance.budget_period
        context['budget_item'] = budget_allocation_instance.budget_item
        context['allocated_amount_main'] = budget_allocation_instance.allocated_amount
        context['allocation_date_main'] = budget_allocation_instance.allocation_date
        context['description_main'] = budget_allocation_instance.description
        context['is_active_main'] = budget_allocation_instance.is_active
        context['is_stopped_main'] = budget_allocation_instance.is_stopped
        context['created_by_main'] = budget_allocation_instance.created_by
        context['is_locked_main'] = budget_allocation_instance.is_locked  # وضعیت قفل بودن

        # --- ۲. محاسبه مصرف و مانده BudgetAllocation اصلی ---
        # این توابع باید در 'budgets.budget_calculations' وجود داشته باشند.
        total_consumed_main = calculate_total_consumed_on_budget_allocation(budget_allocation_instance)
        remaining_main = get_budget_allocation_remaining_amount(budget_allocation_instance)

        context['consumed_amount_main'] = total_consumed_main
        context['remaining_amount_main'] = remaining_main
        context['utilization_percentage_main'] = (
                    total_consumed_main / budget_allocation_instance.allocated_amount * 100) \
            if budget_allocation_instance.allocated_amount and budget_allocation_instance.allocated_amount > 0 else Decimal(
            '0')

        # --- ۳. لیست تخصیص‌های بودجه *هم‌خانواده* (مرتبط به همان پروژه/زیرپروژه/سازمان) ---
        # این‌ها تخصیص‌های دیگر از مدل BudgetAllocation هستند که به همان گروه مرتبطند.
        # این بخش "project_allocations" قبلی شما را شبیه‌سازی می‌کند اما با کوئری مستقیم.
        related_budget_allocations_details = []

        # ابتدا همه تخصیص‌های بودجه را که به همان سازمان و دوره بودجه تعلق دارند فیلتر کنید
        # سپس بر اساس پروژه و زیرپروژه فیلتر کنید.
        # این کوئری، تخصیص بودجه فعلی را هم شامل می‌شود (که می‌توان آن را بعداً exclude کرد یا در حلقه نادیده گرفت)
        base_related_ba_qs = BudgetAllocation.objects.filter(
            organization=budget_allocation_instance.organization,
            budget_period=budget_allocation_instance.budget_period,
            is_active=True  # فقط تخصیص‌های فعال
        ).select_related('project', 'subproject', 'budget_item', 'organization').order_by('project__name',
                                                                                          'subproject__name',
                                                                                          '-allocation_date')

        # اگر تخصیص اصلی به یک پروژه خاص مرتبط است
        if budget_allocation_instance.project:
            base_related_ba_qs = base_related_ba_qs.filter(project=budget_allocation_instance.project)
            # اگر تخصیص اصلی به زیرپروژه مرتبط است
            if budget_allocation_instance.subproject:
                base_related_ba_qs = base_related_ba_qs.filter(subproject=budget_allocation_instance.subproject)
            else:
                # اگر تخصیص اصلی زیرپروژه ندارد، تخصیص‌های هم‌خانواده بدون زیرپروژه را نمایش دهید
                base_related_ba_qs = base_related_ba_qs.filter(subproject__isnull=True)
        else:  # اگر تخصیص اصلی خودش به پروژه خاصی مرتبط نیست (شاید یک بودجه عمومی‌تر است)
            # در این حالت، ممکن است بخواهید تمام تخصیص‌ها را در آن سازمان و دوره نشان دهید یا فقط تخصیص‌های بدون پروژه.
            # من فرض می‌کنم فقط تخصیص‌های بدون پروژه و زیرپروژه را در نظر بگیریم.
            base_related_ba_qs = base_related_ba_qs.filter(project__isnull=True, subproject__isnull=True)

        for related_ba in base_related_ba_qs:
            # خود آبجکت BudgetAllocation اصلی را در این لیست هم‌خانواده‌ها نمایش ندهید
            if related_ba.pk == budget_allocation_instance.pk:
                continue

            # برای هر تخصیص بودجه مرتبط، مصرف و مانده آن را محاسبه کنید
            # این توابع را باید پیاده‌سازی کرده باشید
            related_consumed = calculate_total_consumed_on_budget_allocation(related_ba)
            related_remaining = get_budget_allocation_remaining_amount(related_ba)

            related_budget_allocations_details.append({
                'instance': related_ba,
                'allocated_amount': related_ba.allocated_amount,
                'consumed_amount': related_consumed,
                'remaining_amount': related_remaining,
                'utilization_percentage': (related_consumed / related_ba.allocated_amount * 100) \
                    if related_ba.allocated_amount and related_ba.allocated_amount > 0 else Decimal('0'),
                'project_name': related_ba.project.name if related_ba.project else _("بدون پروژه"),
                'subproject_name': related_ba.subproject.name if related_ba.subproject else _("بدون زیرپروژه"),
                'allocation_date': related_ba.allocation_date,
                'is_active': related_ba.is_active,
                'is_locked': related_ba.is_locked,
                'budget_item_name': related_ba.budget_item.name if related_ba.budget_item else _("نامشخص"),
                'description': related_ba.description,
            })
        context['related_budget_allocations_list'] = related_budget_allocations_details

        # --- ۴. لیست تنخواه‌های مرتبط با این BudgetAllocation اصلی ---
        # این لیست از related_name='tankhahs' در مدل Tankhah می‌آید و prefetch شده است
        context['linked_tankhahs'] = budget_allocation_instance.tankhahs.all()[:20]  # 20 تنخواه اخیر

        # --- ۵. لیست تراکنش‌های مرتبط با این BudgetAllocation اصلی ---
        # این لیست از related_name='transactions' در مدل BudgetTransaction می‌آید و prefetch شده است
        context['linked_transactions'] = budget_allocation_instance.transactions.all()[:20]  # 20 تراکنش اخیر

        logger.info(
            f"Report context for BudgetAllocation PK: {budget_allocation_instance.pk} prepared successfully. Found {len(context['linked_tankhahs'])} linked tankhahs and {len(context['linked_transactions'])} linked transactions.")
        return context