import logging

from django.http import JsonResponse

from budgets.models import BudgetAllocation, BudgetTransaction
from core.models import Organization, Project, Status, UserPost, SubProject
from notificationApp.utils import send_notification
from tankhah.Tankhah.forms_tankhah import  TankhahForm
from tankhah.models import Factor

from django.db.models import Sum, Prefetch
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, View
from django.views.generic.list import ListView

from accounts.models import CustomUser
from budgets.budget_calculations import      get_subproject_total_budget
from django.db.models import Q
from jalali_date import date2jalali
from tankhah.models import Tankhah
import jdatetime
from decimal import Decimal
# tankhah/views.py
from core.views import PermissionBaseView
from django.utils.translation import gettext_lazy as _
from jdatetime import date as jdate
# -------
"""به‌روزرسانی پروژه‌ها بر اساس سازمان"""
from django.views.decorators.http import require_GET


# tankhah/views.py
@require_GET
def get_projects(request):
    org_id = request.GET.get('org_id')
    logger.debug(f"Request received for get_projects with org_id: {org_id}")

    if not org_id:
        logger.warning("No org_id provided in get_projects request")
        return JsonResponse({'projects': []})

    try:
        projects = Project.objects.filter(
            organizations__id=org_id,
            is_active=True
        ).distinct().order_by('name').values('id', 'name')
        projects_list = list(projects)
        logger.debug(f"Found {len(projects_list)} projects for org_id: {org_id}")
        return JsonResponse({'projects': projects_list})
    except Exception as e:
        logger.error(f"Error fetching projects for org_id {org_id}: {str(e)}")
        return JsonResponse({'projects': []}, status=500)


# tankhah/view_folder_tankhah/view_tankhah.py (یا هرجایی که این ویو قرار دارد)

import logging
from django.urls import reverse_lazy, reverse
from django.shortcuts import redirect
from django.db import transaction
from django.contrib import messages
from django.views.generic import CreateView
from django.core.exceptions import ValidationError  # برای مدیریت خطاهای مدل

from core.PermissionBase import PermissionBaseView  # یا LoginRequiredMixin
from tankhah.models import Tankhah
from tankhah.Tankhah.forms_tankhah import TankhahForm  # فرمی که در بالا تعریف کردیم
from core.models import Status, Organization, Project, SubProject
from budgets.models import BudgetAllocation
# from accounts.models import CustomUser # اگر برای notify لازم است
# از django.contrib.auth import get_user_model
# User = get_user_model()

# توابع محاسباتی بودجه (اگر در context برای نمایش اطلاعات بودجه استفاده می‌شوند)
from budgets.budget_calculations import get_project_total_budget, get_project_remaining_budget, \
    get_subproject_remaining_budget
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from decimal import Decimal
import logging

from tankhah.models import Tankhah, Factor, ApprovalLog
from tankhah.forms import TankhahStatusForm
from core.views import PermissionBaseView
from budgets.budget_calculations import (
    get_tankhah_total_budget,
    get_tankhah_used_budget,
    get_tankhah_remaining_budget,
    get_project_total_budget,
    get_project_remaining_budget,
    check_tankhah_lock_status,
)

logger = logging.getLogger("tankhah_views")

# تأیید و ویرایش تنخواه
class TankhahUpdateView(PermissionBaseView, UpdateView):
    model =  Tankhah
    form_class =  TankhahForm
    template_name = 'tankhah/Tankhah_manage.html'
    success_url = reverse_lazy('tankhah_list')

    def test_func(self):
        # فقط سوپر‌یوزرها یا استف‌ها دسترسی دارن
        return self.request.user.is_superuser or self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, _('شما اجازه دسترسی به این صفحه را ندارید.'))
        return super().handle_no_permission()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.get_object()
        context['title'] = _('ویرایش و تأیید تنخواه') + f" - {tankhah.number}"
        context['can_edit'] = self.request.user.has_perm('tankhah.Tankhah_update') or self.request.user.is_staff

        # وضعیت‌های قفل‌کننده تنخواه
        locked_statuses = ['REJECTED', 'APPROVED', 'PAID', 'HQ_OPS_APPROVED', 'SENT_TO_HQ']
        has_factors = tankhah.factors.exists()  # چک کردن وجود فاکتور
        is_locked = has_factors or tankhah.status in locked_statuses

        context['is_locked'] = is_locked
        # دلیل قفل شدن
        if is_locked:
            if has_factors:
                context['lock_reason'] = _('این تنخواه قابل ویرایش نیست چون فاکتور ثبت‌شده دارد.')
            else:
                context['lock_reason'] = _('این تنخواه قابل ویرایش نیست چون در وضعیت "{}" است.').format(
                    tankhah.get_status_display())
        else:
            context['lock_reason'] = ''

        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tankhah = self.get_object()
        # اگه قفل شده، همه فیلدها رو غیرفعال کن
        locked_statuses = ['REJECTED', 'APPROVED', 'PAID', 'HQ_OPS_APPROVED', 'SENT_TO_HQ']
        if tankhah.factors.exists() or tankhah.status in locked_statuses:
            for field in form.fields.values():
                field.disabled = True
        return form

    def form_valid(self, form):
        tankhah = self.get_object()
        # اگه فاکتور داره یا رد/تأیید شده، نذار تغییر کنه
        locked_statuses = ['REJECTED', 'APPROVED', 'PAID', 'HQ_OPS_APPROVED', 'SENT_TO_HQ']
        if tankhah.factors.exists() or tankhah.status in locked_statuses:
            reason = _('فاکتور ثبت‌شده دارد') if tankhah.factors.exists() else _('در وضعیت "{}" است').format(
                tankhah.get_status_display())
            messages.error(self.request, _('این تنخواه قابل ویرایش نیست چون {}').format(reason))
            return self.form_invalid(form)

        user_post = self.request.user.userpost_set.filter(post__organization=tankhah.organization).first()
        if not user_post or user_post.post.branch != tankhah.current_stage:
            messages.error(self.request, _('شما اجازه تأیید در این مرحله را ندارید.'))
            return self.form_invalid(form)

        next_post = 'core.Post'.objects.filter(parent=user_post.post, organization=tankhah.organization).first() or \
                    'core.Post'.objects.filter(organization__org_type='HQ', branch=tankhah.current_stage, level=1).first()
        if next_post:
            tankhah.last_stopped_post = next_post
        tankhah.save()
        messages.success(self.request, _('تنخواه با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)
# -------
class TankhahListView(PermissionBaseView, ListView):
    model = Tankhah
    template_name = 'tankhah/tankhah_list.html'
    context_object_name = 'tankhahs'
    paginate_by = 10
    extra_context = {'title': _('لیست تنخواه‌ها')}
    check_organization = True
    permission_codenames = ['tankhah.Tankhah_view']

    def get_queryset(self):
        user = self.request.user
        logger.info(f"[TankhahListView] User: {user}, is_superuser: {user.is_superuser}")

        user_posts = UserPost.objects.filter(
            user=user, is_active=True, end_date__isnull=True
        ).select_related('post__organization', 'post__organization__org_type')
        user_org_pks = [up.post.organization.pk for up in user_posts if up.post and up.post.organization]
        is_hq_user = (
                user.is_superuser or
                user.has_perm('tankhah.Tankhah_view_all') or
                any(up.post.organization.org_type and up.post.organization.org_type.org_type == 'HQ'
                    for up in user_posts if up.post and up.post.organization)
        )

        logger.info(
            f"[TankhahListView] User: {user.username}, is_hq_user: {is_hq_user}, User org PKs: {user_org_pks}"
        )

        if is_hq_user:
            queryset = Tankhah.objects.all()
            logger.debug("[TankhahListView] HQ user access: fetching all Tankhahs.")
        elif user_org_pks:
            queryset = Tankhah.objects.filter(organization__pk__in=user_org_pks)
            logger.debug(f"[TankhahListView] Filtered for user organizations: {user_org_pks}")
        else:
            queryset = Tankhah.objects.none()
            logger.info("[TankhahListView] User has no associated organizations. Returning empty queryset.")

        show_archived = self.request.GET.get('show_archived', 'false').lower() == 'true'
        queryset = queryset.filter(is_archived=show_archived)
        logger.debug(f"[TankhahListView] نمایش آرشیو: {show_archived}, تعداد: {queryset.count()}")

        query = self.request.GET.get('q', '').strip()
        date_query = self.request.GET.get('date', '').strip()
        # فیلتر بازه تاریخ شمسی (جلالی)
        date_from_query = self.request.GET.get('date_from', '').strip()
        date_to_query = self.request.GET.get('date_to', '').strip()
        amount_query = self.request.GET.get('amount', '').strip()
        remaining_query = self.request.GET.get('remaining', '').strip()
        stage = self.request.GET.get('stage', '').strip()

        filter_conditions = Q()

        if query:
            filter_conditions &= (
                    Q(number__icontains=query) |
                    Q(organization__name__icontains=query) |
                    Q(project__name__icontains=query) |
                    Q(subproject__name__icontains=query) |
                    Q(description__icontains=query)
            )
            logger.debug(f"[TankhahListView] جستجو '{query}', تعداد: {queryset.filter(filter_conditions).count()}")

        if date_query:
            try:
                date_query_norm = date_query.replace('/', '-')
                parts = date_query_norm.split('-')
                if len(parts) == 1:
                    year = int(parts[0])
                    gregorian_year = year - 621
                    filter_conditions &= Q(date__year=gregorian_year)
                elif len(parts) == 2:
                    year, month = map(int, parts)
                    jalali_date = jdate(year, month, 1)
                    gregorian_date = jalali_date.togregorian()
                    filter_conditions &= Q(date__year=gregorian_date.year, date__month=gregorian_date.month)
                elif len(parts) == 3:
                    year, month, day = map(int, parts)
                    jalali_date = jdate(year, month, day)
                    gregorian_date = jalali_date.togregorian()
                    filter_conditions &= Q(date=gregorian_date)
                else:
                    raise ValueError("Invalid date format")
            except ValueError as e:
                logger.warning(f"[TankhahListView] خطای فرمت تاریخ: {date_query}, error: {str(e)}")
                messages.error(self.request, _('فرمت تاریخ نامعتبر است (1403، 1403-05، یا 1403-05-15).'))
                filter_conditions &= Q(date__isnull=True)
            logger.debug(
                f"[TankhahListView] فیلتر تاریخ '{date_query}', تعداد: {queryset.filter(filter_conditions).count()}")

        # بازه تاریخ (از/تا) با فرمت جلالی و جداکننده / یا -
        if date_from_query or date_to_query:
            try:
                def parse_jalali_to_gregorian(s):
                    s = s.replace('/', '-')
                    y, m, d = map(int, s.split('-'))
                    return jdate(y, m, d).togregorian()

                start_g = parse_jalali_to_gregorian(date_from_query) if date_from_query else None
                end_g = parse_jalali_to_gregorian(date_to_query) if date_to_query else None
                if start_g and end_g:
                    filter_conditions &= Q(date__range=(start_g, end_g))
                elif start_g:
                    filter_conditions &= Q(date__gte=start_g)
                elif end_g:
                    filter_conditions &= Q(date__lte=end_g)
            except Exception as e:
                logger.warning(f"[TankhahListView] خطای بازه تاریخ: from={date_from_query}, to={date_to_query}, err={e}")
                messages.error(self.request, _('بازه تاریخ نامعتبر است.'))
                filter_conditions &= Q(id__in=[])

        if amount_query:
            try:
                amount = Decimal(amount_query.replace(',', ''))
                filter_conditions &= Q(amount=amount)
            except (ValueError, Decimal.InvalidOperation):
                logger.warning(f"[TankhahListView] خطای فرمت مبلغ: {amount_query}")
                messages.error(self.request, _('مبلغ باید عدد باشد.'))
                filter_conditions &= Q(amount__isnull=True)
            logger.debug(
                f"[TankhahListView] فیلتر مبلغ '{amount_query}', تعداد: {queryset.filter(filter_conditions).count()}")

        if remaining_query:
            try:
                remaining = Decimal(remaining_query.replace(',', ''))
                tankhah_ids = [
                    t.id for t in queryset
                    if abs((t.get_remaining_budget() or Decimal('0')) - remaining) < Decimal('0.01')
                ]
                filter_conditions &= Q(id__in=tankhah_ids)
            except (ValueError, Decimal.InvalidOperation):
                logger.warning(f"[TankhahListView] خطای فرمت باقیمانده: {remaining_query}")
                messages.error(self.request, _('باقیمانده باید عدد باشد.'))
                filter_conditions &= Q(id__in=[])
            logger.debug(
                f"[TankhahListView] فیلتر باقیمانده '{remaining_query}', تعداد: {queryset.filter(filter_conditions).count()}")

        if stage:
            try:
                filter_conditions &= Q(current_stage__order=int(stage))
            except ValueError:
                logger.warning(f"[TankhahListView] خطای فرمت مرحله: {stage}")
                messages.error(self.request, _('مرحله باید عدد باشد.'))
            logger.debug(f"[TankhahListView] فیلتر مرحله {stage}, تعداد: {queryset.filter(filter_conditions).count()}")

        if filter_conditions:
            queryset = queryset.filter(filter_conditions)
            if not queryset.exists():
                messages.info(self.request, _('هیچ تنخواهی یافت نشد.'))
                logger.info("[TankhahListView] هیچ تنخواهی با شرایط فیلتر یافت نشد")

        # فیلتر وضعیت: همه | فقط منقضی | فقط غیر منقضی
        from django.utils import timezone as _tz
        current_date = _tz.now().date()
        status_filter = self.request.GET.get('status', '').strip().lower()
        # سازگاری با پارامتر قدیمی expired_only
        if not status_filter:
            if self.request.GET.get('expired_only', 'false').lower() in ('true', '1'):
                status_filter = 'expired'

        if status_filter in ('expired', 'active'):
            filtered_ids = []
            for t in queryset.select_related('project_budget_allocation__budget_period'):
                bp = t.project_budget_allocation.budget_period if (t.project_budget_allocation and t.project_budget_allocation.budget_period) else None
                is_expired = False
                if bp:
                    is_expired = (bp.end_date < current_date) or bool(bp.is_completed)
                if status_filter == 'expired' and is_expired:
                    filtered_ids.append(t.id)
                if status_filter == 'active' and not is_expired:
                    filtered_ids.append(t.id)
            queryset = queryset.filter(id__in=filtered_ids) if filtered_ids else Tankhah.objects.none()

        final_queryset = queryset.select_related(
            'project', 'subproject', 'organization', 'current_stage',
            'created_by', 'project_budget_allocation', 'project_budget_allocation__budget_item',
            'project_budget_allocation__budget_period'
        ).prefetch_related(
            Prefetch(
                'factors',
                queryset=Factor.objects.filter(status__code=['APPROVED', 'PAID']),
                to_attr='paid_and_approved_factors'
            )
        ).order_by('organization__name', 'project__name', '-date')

        logger.debug(f"[TankhahListView] تعداد تنخواه‌های نهایی: {final_queryset.count()}")
        return final_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        logger.info(f"[TankhahListView] ایجاد کنتکست برای کاربر: {user}")

        user_posts = UserPost.objects.filter(
            user=user, is_active=True, end_date__isnull=True
        ).select_related('post__organization', 'post__organization__org_type')
        user_orgs = [up.post.organization for up in user_posts if up.post and up.post.organization]
        user_org_pks = [org.pk for org in user_orgs]
        is_hq_user = (
                user.is_superuser or
                user.has_perm('tankhah.Tankhah_view_all') or
                any(up.post.organization.org_type and up.post.organization.org_type.org_type == 'HQ'
                    for up in user_posts if up.post and up.post.organization)
        )

        logger.debug(
            f"[TankhahListView] get_context_data - is_hq_user: {is_hq_user}, org_pks: {user_org_pks}"
        )

        context['is_hq_user'] = is_hq_user
        context['user_orgs'] = user_orgs
        context['query'] = self.request.GET.get('q', '')
        context['date_query'] = self.request.GET.get('date', '')
        context['date_from_query'] = self.request.GET.get('date_from', '')
        context['date_to_query'] = self.request.GET.get('date_to', '')
        context['amount_query'] = self.request.GET.get('amount', '')
        context['remaining_query'] = self.request.GET.get('remaining', '')
        context['stage'] = self.request.GET.get('stage', '')
        context['show_archived'] = self.request.GET.get('show_archived', 'false').lower() == 'true'
        context['expired_only'] = self.request.GET.get('expired_only', 'false').lower() in ('true','1')
        context['status_filter'] = self.request.GET.get('status', '')
        context['org_display_name'] = (
            _('دفتر مرکزی') if is_hq_user else (user_orgs[0].name if user_orgs else _('بدون سازمان'))
        )
        # حذف فیلد اشتباه قدیمی reminid_tankhahs
        # اضافه کردن اطلاعات منقضی شدن
        from django.utils import timezone
        current_date = timezone.now().date()
        context['current_date'] = current_date

        tankhah_list = context[self.context_object_name]
        grouped_by_org = {}

        org_budget_cache = {}
        org_ids = (
            [org.id for org in user_orgs] if not is_hq_user else
            list(set(tankhah.organization_id for tankhah in tankhah_list if tankhah.organization_id))
        )

        budget_periods = list(
            set(tankhah.project_budget_allocation.budget_period_id
                for tankhah in tankhah_list
                if tankhah.project_budget_allocation)
        )

        for org_id in org_ids:
            if org_id:
                org_budget_cache[org_id] = (
                        BudgetAllocation.objects.filter(
                            organization_id=org_id,
                            budget_period_id__in=budget_periods
                        ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
                )

        for tankhah in tankhah_list:
            try:
                org = tankhah.organization
                org_key = org.name if org else _('بدون شعبه')
                project_key = tankhah.project.name if tankhah.project else _('بدون پروژه')

                if org_key not in grouped_by_org:
                    grouped_by_org[org_key] = {
                        'organization': org,
                        'projects': {},
                        'total_amount': Decimal('0'),
                        'total_remaining': Decimal('0')
                    }

                if project_key not in grouped_by_org[org_key]['projects']:
                    grouped_by_org[org_key]['projects'][project_key] = {
                        'project': tankhah.project,
                        'tankhahs': [],
                        'total_amount': Decimal('0'),
                        'total_remaining': Decimal('0')
                    }

                tankhah_amount = tankhah.amount or Decimal('0')
                tankhah_remaining = tankhah.get_remaining_budget() or Decimal('0')
                grouped_by_org[org_key]['projects'][project_key]['tankhahs'].append(tankhah)
                grouped_by_org[org_key]['projects'][project_key]['total_amount'] += tankhah_amount
                grouped_by_org[org_key]['projects'][project_key]['total_remaining'] += tankhah_remaining
                grouped_by_org[org_key]['total_amount'] += tankhah_amount
                grouped_by_org[org_key]['total_remaining'] += tankhah_remaining

                project = tankhah.project
                if project:
                    tankhah.project_total_budget = get_project_total_budget(project) or Decimal('0')
                    tankhah.project_remaining_budget = get_project_remaining_budget(project) or Decimal('0')
                    tankhah.project_allocated_budget = tankhah.project_total_budget
                    tankhah.project_consumed_percentage = (
                        round(
                            (tankhah.project_total_budget - tankhah.project_remaining_budget) /
                            tankhah.project_total_budget * 100
                        ) if tankhah.project_total_budget > 0 else 0
                    )
                else:
                    tankhah.project_total_budget = Decimal('0')
                    tankhah.project_remaining_budget = Decimal('0')
                    tankhah.project_allocated_budget = Decimal('0')
                    tankhah.project_consumed_percentage = 0

                tankhah.branch_total_budget = org_budget_cache.get(
                    tankhah.organization_id if org else None, Decimal('0')
                )
                tankhah.tankhah_used_budget = (
                        BudgetTransaction.objects.filter(
                            allocation=tankhah.project_budget_allocation,
                            transaction_type='CONSUMPTION',
                            related_tankhah=tankhah
                        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                ) if tankhah.project_budget_allocation else Decimal('0')
                tankhah.factor_used_budget = (
                        tankhah.factors.aggregate(total=Sum('amount'))['total'] or Decimal('0')
                )

            except Exception as e:
                logger.error(f"[TankhahListView] خطا در محاسبه بودجه تنخواه {tankhah.number}: {str(e)}")
                tankhah.project_total_budget = Decimal('0')
                tankhah.project_remaining_budget = Decimal('0')
                tankhah.project_allocated_budget = Decimal('0')
                tankhah.project_consumed_percentage = 0
                tankhah.branch_total_budget = Decimal('0')
                tankhah.tankhah_used_budget = Decimal('0')
                tankhah.factor_used_budget = Decimal('0')

        context['grouped_by_org'] = grouped_by_org
        context['errors'] = []
        logger.debug(f"[TankhahListView] تعداد شعبه‌ها: {len(grouped_by_org)}")
        return context

class TankhahDetailView(PermissionBaseView, DetailView):
    model = Tankhah
    template_name = 'tankhah/tankhah_detail.html'
    context_object_name = 'tankhah'
    permission_codenames = ['tankhah.Tankhah_detail']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    check_organization = True
    def get_queryset(self):
        return Tankhah.objects.select_related(
            'organization', 'project', 'project_budget_allocation', 'subproject', 'created_by'
        ).prefetch_related('factors', 'approval_logs')
    def post(self, request, *args, **kwargs):
        tankhah = self.get_object()
        form = TankhahStatusForm(request.POST, instance=tankhah)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, _('وضعیت تنخواه با موفقیت به‌روزرسانی شد.'))
                logger.info(f"Tankhah {tankhah.pk} status updated by user {request.user.username}")
                return redirect('tankhah_detail', pk=tankhah.pk)
            except Exception as e:
                logger.error(f"Error updating Tankhah {tankhah.pk} status: {str(e)}", exc_info=True)
                messages.error(request, _('خطایی در به‌روزرسانی وضعیت رخ داد.'))
        else:
            messages.error(request, _('فرم نامعتبر است. لطفاً ورودی‌ها را بررسی کنید.'))
        return self.get(request, *args, **kwargs)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object
        logger.debug(f"Processing Tankhah {tankhah.pk} for user {self.request.user.username}")

        # اطلاعات پایه
        context['title'] = _('جزئیات تنخواه') + f" - {tankhah.number}"
        context['current_date'] = jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M')
        context['factors'] = tankhah.factors.all()
        context['approval_logs'] = ApprovalLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Tankhah),
            object_id=tankhah.pk
        ).order_by('timestamp')
        context['status_form'] = TankhahStatusForm(instance=tankhah)

        # بودجه تنخواه
        try:
            context['tankhah_total_budget'] = get_tankhah_total_budget(tankhah) or Decimal('0')
            context['tankhah_used_budget'] = get_tankhah_used_budget(tankhah) or Decimal('0')
            context['tankhah_remaining_budget'] = get_tankhah_remaining_budget(tankhah) or Decimal('0')
            logger.debug(
                f"Tankhah {tankhah.pk}: total={context['tankhah_total_budget']}, "
                f"used={context['tankhah_used_budget']}, remaining={context['tankhah_remaining_budget']}"
            )
        except Exception as e:
            logger.error(f"Error calculating tankhah budgets: {str(e)}", exc_info=True)
            context['tankhah_total_budget'] = Decimal('0')
            context['tankhah_used_budget'] = Decimal('0')
            context['tankhah_remaining_budget'] = Decimal('0')
            messages.error(self.request, _('خطایی در محاسبه بودجه تنخواه رخ داد.'))

        # بودجه پروژه
        if tankhah.project:
            try:
                context['project_total_budget'] = get_project_total_budget(tankhah.project) or Decimal('0')
                context['project_remaining_budget'] = get_project_remaining_budget(tankhah.project) or Decimal('0')
                logger.debug(
                    f"Project {tankhah.project.pk}: total={context['project_total_budget']}, "
                    f"remaining={context['project_remaining_budget']}"
                )
            except Exception as e:
                logger.error(f"Error calculating project budgets: {str(e)}", exc_info=True)
                context['project_total_budget'] = Decimal('0')
                context['project_remaining_budget'] = Decimal('0')
                messages.error(self.request, _('خطایی در محاسبه بودجه پروژه رخ داد.'))
        else:
            context['project_total_budget'] = Decimal('0')
            context['project_remaining_budget'] = Decimal('0')

        # وضعیت قفل
        try:
            is_locked, lock_message = check_tankhah_lock_status(tankhah)
            context['is_locked'] = is_locked
            context['lock_message'] = lock_message
            logger.debug(f"Tankhah {tankhah.pk} lock status: {is_locked}, message: {lock_message}")
        except Exception as e:
            logger.error(f"Error checking lock status: {str(e)}", exc_info=True)
            context['is_locked'] = True
            context['lock_message'] = _('خطا در بررسی وضعیت قفل.')
            messages.error(self.request, context['lock_message'])

        # تاریخ شمسی
        context['jalali_date'] = date2jalali(tankhah.date).strftime('%Y/%m/%d') if tankhah.date else '-'
        for factor in context['factors']:
            factor.jalali_date = date2jalali(factor.date).strftime('%Y/%m/%d') if factor.date else '-'
        for approval in context['approval_logs']:
            approval.jalali_date = jdatetime.datetime.fromgregorian(
                datetime=approval.timestamp
            ).strftime('%Y/%m/%d %H:%M')

        # دسترسی‌ها
        user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()]
        context['is_hq'] = any(org.org_type and org.org_type.org_type == 'HQ' for org in user_orgs if org.org_type)
        context['can_approve'] = (
            tankhah.status in ['DRAFT', 'PENDING'] and
            any(
                p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists()
                for p in self.request.user.userpost_set.all()
            ) and (
                self.request.user.has_perm('tankhah.Tankhah_approve') or
                self.request.user.has_perm('tankhah.Tankhah_part_approve') or
                self.request.user.has_perm('tankhah.FactorItem_approve')
            )
        )
        context['can_delete'] = (
            tankhah.status in ['DRAFT', 'REJECTED'] and
            self.request.user.has_perm('tankhah.Tankhah_delete') and
            not tankhah.factors.filter(status__in=['APPROVED', 'PAID']).exists()
        )

        # دیباگ context
        logger.debug(f"Context for Tankhah {tankhah.pk}: {context}")
        return context

class TankhahDeleteView(PermissionBaseView, DeleteView):
    model = Tankhah
    template_name = 'tankhah/Tankhah_confirm_delete.html'
    success_url = reverse_lazy('tankhah_list')
    permission_codenames = ['tankhah.Tankhah_delete']

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.factors.exists():
            messages.error(request, _('این تنخواه فاکتور ثبت‌شده دارد و قابل حذف نیست.'))
            return redirect('tankhah_list')
        return super().post(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تنخواه با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)
# ویو تأیید:
class TankhahApproveView(PermissionBaseView, View):
    permission_codenames = ['tankhah.Tankhah_approve']

    def post(self, request, pk):
        tankhah = get_object_or_404( Tankhah, pk=pk)
        user_posts = request.user.userpost_set.all()

        logger.info(f"Processing POST for tankhah {tankhah.number}, current_stage: {tankhah.current_stage.name} (order: {tankhah.current_stage.order})")
        logger.info(f"User posts: {[p.post.name for p in user_posts]}")

        # چک دسترسی به مرحله فعلی
        can_approve = any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts)
        if not can_approve:
            logger.warning(f"User {request.user.username} not authorized to approve stage {tankhah.current_stage.name}")
            messages.error(request, _('شما اجازه تأیید این مرحله را ندارید.'))
            return redirect('dashboard_flows')

        # اگه قفل یا آرشیو شده، اجازه تغییر نده
        if tankhah.is_locked or tankhah.is_archived:
            messages.error(request, _('این تنخواه قفل یا آرشیو شده و قابل تغییر نیست.'))
            return redirect('dashboard_flows')

        # پیدا کردن مرحله بعدی
        from core.models import Status
        next_stage =   WorkflowStage.objects.filter(order__gt=tankhah.current_stage.order).order_by('order').first()
        with transaction.atomic():
            if next_stage:
                tankhah.current_stage = next_stage
                tankhah.status = 'PENDING'
                tankhah.save()
                messages.success(request, _('تنخواه با موفقیت تأیید شد و به مرحله بعدی منتقل شد.'))

                # ارسال نوتیفیکیشن به تأییدکنندگان مرحله بعدی
                approvers = CustomUser.objects.filter(
                    userpost__post__stageapprover_set__stage=next_stage,
                    userpost__post__organization=tankhah.organization
                ).distinct()
                if approvers.exists():
                    send_notification(self.request.user, users=None, posts=None, verb='تنخواه برای تأیید آماده است',
                                      description=approvers, target=self.object,
                                      entity_type=None, priority='MEDIUM')

                    logger.info(f"Notification sent to {approvers.count()} users for stage {next_stage.name}")
                else:
                    logger.warning(f"No approvers found for stage {next_stage.name}")
            else:
                # مرحله آخر: پرداخت
                authorized_final_posts = [approver.post.name for approver in tankhah.current_stage.stageapprover_set.all()]
                if any(p.post.name in authorized_final_posts for p in user_posts):
                    payment_number = request.POST.get('payment_number', '').strip()
                    if not payment_number:
                        messages.error(request, _('لطفاً شماره پرداخت را وارد کنید.'))
                        return redirect('dashboard_flows')
                    tankhah.status = 'PAID'

                    tankhah.payment_number = payment_number
                    tankhah.is_locked = True
                    tankhah.is_archived = True
                    tankhah.save()
                    messages.success(request, _('تنخواه پرداخت شد، قفل و آرشیو شد.'))
                else:
                    tankhah.status = 'COMPLETED'

                    tankhah.is_locked = True
                    tankhah.is_archived = True
                    tankhah.save()
                    messages.success(request, _('تنخواه تکمیل شد، قفل و آرشیو شد.'))

        return redirect('dashboard_flows')
# ویو رد:
class TankhahRejectView(PermissionBaseView, View):
    permission_codenames = ['tankhah.Tankhah_approve']
    def get(self, request, pk):
        tankhah = Tankhah.objects.get(pk=pk)
        user_posts = request.user.userpost_set.all()
        if not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه رد این مرحله را ندارید.'))
            return redirect('dashboard_flows')

        tankhah.status = 'REJECTED'
        tankhah.Tankhah.save()
        messages.error(request, _('تنخواه رد شد.'))
        return redirect('dashboard_flows')
# ویو نهایی تنخواه تایید یا رد شده
class TankhahFinalApprovalView(PermissionBaseView,UpdateView):
    """ویو نهایی تنخواه تایید یا رد شده """
    model =   Tankhah
    fields = ['status']
    template_name = 'tankhah/Tankhah_final_approval.html'
    success_url = reverse_lazy('tankhah_list')

    def form_valid(self, form):
        user_orgs = [up.post.organization for up in self.request.user.userpost_set.all()]
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)
        if not is_hq_user:
            messages.error(self.request, _('فقط دفتر مرکزی می‌تواند تأیید نهایی کند.'))
            return self.form_invalid(form)

        # جلوگیری از تأیید اگر تنخواه در مراحل پایین‌تر باشد
        if self.object.current_stage.order < 4:  # قبل از HQ_OPS
            messages.error(self.request, _('تنخواه هنوز در جریان مراحل شعبه است و قابل تأیید نیست.'))
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            if self.object.status == 'PAID':
                self.object.current_stage = 'tankhah.WorkflowStage'.objects.get(name='HQ_FIN')
                self.object.is_archived = True
                self.object.save()
                messages.success(self.request, _('تنخواه پرداخت و آرشیو شد.'))
            elif self.object.status == 'REJECTED':
                messages.warning(self.request, _('تنخواه رد شد.'))
        return super().form_valid(form)

class TankhahManageView(PermissionBaseView, CreateView):
    model =  Tankhah
    form_class = TankhahForm
    template_name = 'tankhah/tankhah_manage.html'
    success_url = reverse_lazy('tankhah_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _('تنخواه با موفقیت ثبت یا به‌روزرسانی شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('مدیریت تنخواه')
        return context

