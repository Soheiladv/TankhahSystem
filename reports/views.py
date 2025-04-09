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
from core.models import Organization, WorkflowStage, Project
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

class DecimalEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

class FinancialDashboardView(PermissionBaseView, TemplateView):
    template_name = 'Tankhah/Reports/calc_dashboard.html'
    permission_codenames = ['tankhah.Dashboard__view']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # 1. گرفتن سازمان‌ها و چک کردن HQ
        user_orgs = [up.post.organization for up in user.userpost_set.all()]
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)

        # 2. فیلتر تنخواه‌ها
        project_id = self.request.GET.get('project')
        subproject_id = self.request.GET.get('subproject')  # فیلتر جدید برای ساب‌پروژه
        if is_hq_user:
            all_tankhahs = Tankhah.objects.all()
            organizations = Organization.objects.exclude(org_type='HQ')
        else:
            all_tankhahs = Tankhah.objects.filter(organization__in=user_orgs)
            organizations = user_orgs

        if project_id:
            all_tankhahs = all_tankhahs.filter(project_id=project_id)
        if subproject_id:
            all_tankhahs = all_tankhahs.filter(subproject_id=subproject_id)

        # 3. صفحه‌بندی تنخواه‌ها
        paginator = Paginator(all_tankhahs, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj

        # 4. محاسبات کلی
        context['total_tanbakh_amount'] = float(all_tankhahs.aggregate(total=Sum('amount'))['total'] or 0)
        context['archived_tanbakhs'] = all_tankhahs.filter(is_archived=True).count()
        context['total_tankhahs'] = all_tankhahs.count()
        context['avg_processing_time'] = all_tankhahs.filter(status='PAID').aggregate(
            avg_time=Avg(F('archived_at') - F('created_at'))
        )['avg_time'] or timedelta(0)

        # 5. حجم تصاویر با کش
        cache_key = f"total_image_size_{user.id}"
        total_image_size = cache.get(cache_key)
        if total_image_size is None:
            total_image_size = sum(
                default_storage.size(doc.document.path)
                for tankhah in all_tankhahs
                for doc in tankhah.documents.all()
                if default_storage.exists(doc.document.path)
            )
            cache.set(cache_key, total_image_size, 3600)
        context['total_image_size_mb'] = total_image_size / (1024 * 1024)

        # 6. آمار وضعیت تنخواه‌ها
        status_counts = all_tankhahs.values('status').annotate(count=Count('id'))
        context['status_counts'] = {item['status']: item['count'] for item in status_counts}

        # 7. تنخواه‌های در انتظار به تفکیک مرحله
        stages = WorkflowStage.objects.all()
        context['pending_by_stage'] = {
            stage.name: all_tankhahs.filter(current_stage=stage, status='PENDING').count()
            for stage in stages
        }
        context['stages'] = stages

        # 8. محاسبات فاکتورها
        factors = Factor.objects.filter(tankhah__in=all_tankhahs)
        context['total_factor_amount'] = float(factors.aggregate(total=Sum('amount'))['total'] or 0)
        context['approved_factors'] = factors.filter(status='APPROVED').count()
        context['rejected_factors'] = factors.filter(status='REJECTED').count()
        context['pending_factors'] = factors.filter(status='PENDING').count()

        # 9. گزارش زمانی مراحل
        stage_times = ApprovalLog.objects.filter(tankhah__in=all_tankhahs).values('stage__name').annotate(
            avg_time=Avg(F('timestamp') - F('tankhah__created_at'))
        )
        context['stage_times'] = {
            item['stage__name']: item['avg_time'].days if item['avg_time'] else 0
            for item in stage_times
        }

        # 10. جمع آیتم‌های تأییدشده به تفکیک دسته‌بندی
        context['item_categories'] = FactorItem.objects.filter(
            factor__tankhah__in=all_tankhahs, status='APPROVED'
        ).values('category').annotate(total=Sum(F('amount') * F('quantity')))

        # 11. عملکرد کاربران
        user_performance = ApprovalLog.objects.filter(tankhah__in=all_tankhahs).values('user__username').annotate(
            total_approvals=Count('id', filter=Q(action='APPROVE')),
            total_rejections=Count('id', filter=Q(action='REJECT')),
            avg_time=Avg(F('timestamp') - F('tankhah__created_at'))
        )
        context['user_performance'] = list(user_performance)

        # 12. دیتای چارت کاربران
        context['user_chart_data'] = json.dumps({
            'labels': [u['user__username'] for u in user_performance],
            'datasets': [
                {'label': force_str(_('تأییدها')), 'data': [u['total_approvals'] for u in user_performance],
                 'backgroundColor': '#48bb78'},
                {'label': force_str(_('رد شده‌ها')), 'data': [u['total_rejections'] for u in user_performance],
                 'backgroundColor': '#f56565'},
            ]
        }, cls=DecimalEncoder)

        # 13. داده‌های سازمان‌ها
        org_data = []
        chart_labels = []
        chart_tankhah_amounts = []
        chart_factor_amounts = []
        chart_approved_items = []
        chart_image_sizes = []
        for org in organizations:
            org_tankhahs = all_tankhahs.filter(organization=org)
            org_factors = factors.filter(tankhah__in=org_tankhahs)
            org_image_size = sum(
                default_storage.size(doc.document.path)
                for doc in TankhahDocument.objects.filter(tankhah__in=org_tankhahs)
                if default_storage.exists(doc.document.path)
            ) / (1024 * 1024)
            projects = Project.objects.filter(organizations=org)
            org_info = {
                'name': org.name,
                'total_tanbakh_amount': float(org_tankhahs.aggregate(total=Sum('amount'))['total'] or 0),
                'projects': [
                    {
                        'id': p.id,
                        'name': p.name,
                        'tankhah_count': org_tankhahs.filter(project=p).count(),
                        'subprojects': [
                            {
                                'id': sp.id,
                                'name': sp.name,
                                'tankhah_count': org_tankhahs.filter(subproject=sp).count()
                            } for sp in p.subprojects.all()
                        ]
                    } for p in projects
                ],
                'total_factor_amount': float(org_factors.aggregate(total=Sum('amount'))['total'] or 0),
                'approved_items_amount': float(FactorItem.objects.filter(
                    factor__in=org_factors, status='APPROVED'
                ).aggregate(total=Sum(F('amount') * F('quantity')))['total'] or 0),
                'image_size_mb': org_image_size,
            }
            org_data.append(org_info)
            chart_labels.append(org.name)
            chart_tankhah_amounts.append(org_info['total_tanbakh_amount'])
            chart_factor_amounts.append(org_info['total_factor_amount'])
            chart_approved_items.append(org_info['approved_items_amount'])
            chart_image_sizes.append(org_info['image_size_mb'])

        context['org_data'] = org_data

        # 14. دیتای چارت مالی
        context['chart_data'] = json.dumps({
            'labels': chart_labels,
            'datasets': [
                {'label': force_str(_('مبلغ تنخواه‌ها')), 'data': chart_tankhah_amounts, 'backgroundColor': '#4299e1'},
                {'label': force_str(_('مبلغ فاکتورها')), 'data': chart_factor_amounts, 'backgroundColor': '#f56565'},
                {'label': force_str(_('جمع ردیف‌های تأییدشده')), 'data': chart_approved_items,
                 'backgroundColor': '#48bb78'},
                {'label': force_str(_('حجم تصاویر (مگابایت)')), 'data': chart_image_sizes,
                 'backgroundColor': '#ed8936'},
            ]
        }, cls=DecimalEncoder)

        # 15. دیتای چارت وضعیت
        STATUS_CHOICES_DICT = dict(Tankhah.STATUS_CHOICES)
        context['status_chart_data'] = json.dumps({
            'labels': [force_str(STATUS_CHOICES_DICT.get(status, status)) for status in
                       context['status_counts'].keys()],
            'datasets': [{
                'label': force_str(_('تعداد تنخواه‌ها')),
                'data': list(context['status_counts'].values()),
                'backgroundColor': ['#4299e1', '#f56565', '#48bb78', '#ed8936', '#9f7aea']
            }]
        }, cls=DecimalEncoder)

        return context

class FinancialDashboardView1(PermissionBaseView, TemplateView):
    template_name = 'Tankhah/Reports/calc_dashboard.html'
    permission_codenames = ['tankhah.Dashboard__view']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # 1. گرفتن سازمان‌های کاربر و چک کردن HQ بودن
        user_orgs = [up.post.organization for up in user.userpost_set.all()]
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)

        # 2. فیلتر کردن تنخواه‌ها و سازمان‌ها بر اساس دسترسی کاربر
        if is_hq_user:
            all_tankhahs = Tankhah.objects.all()  # کل تنخواه‌ها برای کاربر HQ
            organizations = Organization.objects.exclude(org_type='HQ')  # همه سازمان‌ها به جز HQ
        else:
            all_tankhahs = Tankhah.objects.filter(organization__in=user_orgs)  # فقط تنخواه‌های سازمان‌های کاربر
            organizations = user_orgs

        # 3. صفحه‌بندی تنخواه‌ها
        paginator = Paginator(all_tankhahs, 10)  # 10 تنخواه در هر صفحه
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        tankhahs = page_obj.object_list  # فقط تنخواه‌های صفحه فعلی برای نمایش جزئیات
        context['page_obj'] = page_obj

        # 4. محاسبات کلی (با کل QuerySet)
        context['total_tanbakh_amount'] = float(all_tankhahs.aggregate(total=Sum('amount'))['total'] or 0)
        context['archived_tanbakhs'] = all_tankhahs.filter(is_archived=True).count()
        context['total_tankhahs'] = all_tankhahs.count()
        context['avg_processing_time'] = all_tankhahs.filter(status='PAID').aggregate(
            avg_time=Avg(F('archived_at') - F('created_at'))
        )['avg_time']
        context['total_image_size_mb'] = sum(
            default_storage.size(doc.document.path) for tankhah in all_tankhahs
            for doc in tankhah.documents.all() if default_storage.exists(doc.document.path)
        ) / (1024 * 1024)
        context['avg_processing_time'] = all_tankhahs.filter(status='PAID').aggregate(
            avg_time=Avg(F('archived_at') - F('created_at'))
        )['avg_time'] or timedelta(0)

        # 5. کش کردن حجم تصاویر (با کل تنخواه‌ها)
        cache_key = f"total_image_size_{user.id}"
        total_image_size = cache.get(cache_key)
        if total_image_size is None:
            total_image_size = sum(
                default_storage.size(doc.document.path)
                for tankhah in all_tankhahs  # کل تنخواه‌ها برای محاسبه دقیق
                for doc in tankhah.documents.all()
                if default_storage.exists(doc.document.path)
            )
            cache.set(cache_key, total_image_size, 3600)  # 1 ساعت کش
        context['total_image_size_mb'] = total_image_size / (1024 * 1024)

        # 6. آمار وضعیت تنخواه‌ها
        status_counts = all_tankhahs.values('status').annotate(count=Count('id'))
        context['status_counts'] = {item['status']: item['count'] for item in status_counts}

        # 7. تنخواه‌های در انتظار به تفکیک مرحله
        stages = WorkflowStage.objects.all()
        context['pending_by_stage'] = {
            stage.name: all_tankhahs.filter(current_stage=stage, status='PENDING').count()
            for stage in stages
        }
        context['stages'] = stages

        # 8. محاسبات فاکتورها
        factors = Factor.objects.filter(tankhah__in=all_tankhahs)  # کل فاکتورها
        context['total_factor_amount'] = float(factors.aggregate(total=Sum('amount'))['total'] or 0)
        context['approved_factors'] = factors.filter(status='APPROVED').count()
        context['rejected_factors'] = factors.filter(status='REJECTED').count()
        context['pending_factors'] = factors.filter(status='PENDING').count()

        # 9. گزارش زمانی (میانگین زمان هر مرحله)
        stage_times = ApprovalLog.objects.values('stage__name').annotate(
            avg_time=Avg(F('timestamp') - F('tankhah__created_at'))
        )
        context['stage_times'] = {
            item['stage__name']: item['avg_time'].days
            for item in stage_times if item['avg_time']
        }

        # 10. گزارش مالی جزئی (جمع آیتم‌های تأیید شده به تفکیک دسته‌بندی)
        context['item_categories'] = FactorItem.objects.filter(
            factor__tankhah__in=all_tankhahs, status='APPROVED'
        ).values('category').annotate(total=Sum(F('amount') * F('quantity')))

        # 11. عملکرد کاربران
        user_performance = ApprovalLog.objects.filter(tankhah__in=all_tankhahs).values('user__username').annotate(
            total_approvals=Count('id', filter=Q(action='APPROVE')),
            total_rejections=Count('id', filter=Q(action='REJECT')),
            avg_time=Avg(F('timestamp') - F('tankhah__created_at'))
        )
        context['user_performance'] = list(user_performance)

        # 12. دیتای چارت کاربران
        context['user_chart_data'] = json.dumps({
            'labels': [u['user__username'] for u in user_performance],
            'datasets': [
                {'label': 'تأییدها', 'data': [u['total_approvals'] for u in user_performance],
                 'backgroundColor': '#48bb78'},
                {'label': 'رد شده‌ها', 'data': [u['total_rejections'] for u in user_performance],
                 'backgroundColor': '#f56565'},
            ]
        }, cls=DecimalEncoder)

        # 13. داده‌های سازمان‌ها
        org_data = []
        chart_labels = []
        chart_tankhah_amounts = []
        chart_factor_amounts = []
        chart_approved_items = []
        chart_image_sizes = []
        for org in organizations:
            org_tankhahs = all_tankhahs.filter(organization=org)  # کل تنخواه‌های سازمان
            org_factors = factors.filter(tankhah__in=org_tankhahs)
            org_image_size = sum(
                default_storage.size(doc.document.path)
                for doc in TankhahDocument.objects.filter(tankhah__in=org_tankhahs)
                if default_storage.exists(doc.document.path)
            ) / (1024 * 1024)
            projects = Project.objects.filter(organizations=org)

            org_info = {
                'name': org.name,
                'total_tanbakh_amount': float(org_tankhahs.aggregate(total=Sum('amount'))['total'] or 0),
                'total_factor_amount': float(org_factors.aggregate(total=Sum('amount'))['total'] or 0),
                'approved_factors': org_factors.filter(status='APPROVED').count(),
                'rejected_factors': org_factors.filter(status='REJECTED').count(),
                'pending_factors': org_factors.filter(status='PENDING').count(),
                'approved_items_amount': float(FactorItem.objects.filter(
                    factor__in=org_factors, status='APPROVED'
                ).aggregate(total=Sum(F('amount') * F('quantity')))['total'] or 0),
                'image_size_mb': org_image_size,
                'projects': [{'id': p.id, 'name': p.name, 'tankhah_count': org_tankhahs.filter(project=p).count()} for p
                             in
                             projects]
            }
            org_data.append(org_info)

            chart_labels.append(org.name)
            chart_tankhah_amounts.append(org_info['total_tanbakh_amount'])
            chart_factor_amounts.append(org_info['total_factor_amount'])
            chart_approved_items.append(org_info['approved_items_amount'])
            chart_image_sizes.append(org_info['image_size_mb'])

        context['org_data'] = org_data

        # 14. دیتای چارت مالی
        context['chart_data'] = json.dumps({
            'labels': chart_labels,
            'datasets': [
                {'label': force_str(_('مبلغ تنخواه‌ها')), 'data': chart_tankhah_amounts, 'backgroundColor': '#4299e1'},
                {'label': force_str(_('مبلغ فاکتورها')), 'data': chart_factor_amounts, 'backgroundColor': '#f56565'},
                {'label': force_str(_('جمع ردیف‌های تأییدشده')), 'data': chart_approved_items,
                 'backgroundColor': '#48bb78'},
                {'label': force_str(_('حجم تصاویر (مگابایت)')), 'data': chart_image_sizes,
                 'backgroundColor': '#ed8936'},
            ]
        }, cls=DecimalEncoder)

        # 15. دیتای چارت وضعیت تنخواه‌ها
        STATUS_CHOICES_DICT = dict(Tankhah.STATUS_CHOICES)
        context['status_chart_data'] = json.dumps({
            'labels': [force_str(STATUS_CHOICES_DICT.get(status, status)) for status in
                       context['status_counts'].keys()],
            'datasets': [{
                'label': force_str(_('تعداد تنخواه‌ها')),
                'data': list(context['status_counts'].values()),
                'backgroundColor': ['#4299e1', '#f56565', '#48bb78', '#ed8936', '#9f7aea']
            }]
        }, cls=DecimalEncoder)

        # فیلتر تنخواه‌ها
        project_id = self.request.GET.get('project')
        if is_hq_user:
            all_tankhahs = Tankhah.objects.all()
            organizations = Organization.objects.exclude(org_type='HQ')
        else:
            all_tankhahs = Tankhah.objects.filter(organization__in=user_orgs)
            organizations = user_orgs

        if project_id:
            all_tankhahs = all_tankhahs.filter(project_id=project_id)

        return context

def print_financial_report(request, report_id):
    return HttpResponse(f"چاپ گزارش {report_id}")

def send_to_accounting(request, report_id):
    return HttpResponse(f"ارسال گزارش {report_id} به حسابداری")

######
class TankhahDetailView(PermissionBaseView, TemplateView):
    template_name = 'Reports/tankhah_detail.html'
    permission_codenames = ['tankhah.Tankhah__view']

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
