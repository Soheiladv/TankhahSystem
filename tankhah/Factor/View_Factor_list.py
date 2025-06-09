
import logging
logger = logging.getLogger(__name__)

from django.views.generic import ListView
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils.translation import gettext_lazy as _
from tankhah.models import Factor, FactorItem
from core.PermissionBase import PermissionBaseView
from decimal import Decimal
import logging
try:
    from jdatetime import date as jdate
except ImportError:
    jdate = None
    logging.error("jdatetime is not installed. Please install it using 'pip install jdatetime'")

logger = logging.getLogger(__name__)

class OK_NOGroup_FactorListView(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tankhah/factor_list.html'
    context_object_name = 'factors'
    paginate_by = 10
    extra_context = {'title': _('لیست فاکتورها')}
    permission_codenames = ['tankhah.factor_view']

    def get_queryset(self):
        user = self.request.user
        user_posts = user.userpost_set.filter(is_active=True, end_date__isnull=True)
        if not user_posts.exists():
            logger.info(f"User {user.username} has no active posts, returning empty queryset")
            return Factor.objects.none()

        if jdate is None:
            messages.error(self.request, _('ماژول jdatetime نصب نیست. لطفاً با مدیر سیستم تماس بگیرید.'))
            return Factor.objects.none()

        user_orgs = [up.post.organization for up in user_posts]
        is_hq_user = any(up.post.organization.org_type == 'HQ' for up in user_posts)

        # فیلتر اولیه فاکتورها
        if is_hq_user:
            queryset = Factor.objects.all()
            logger.info("HQ user, retrieving all factors")
        else:
            queryset = Factor.objects.filter(tankhah__organization__in=user_orgs)
            logger.info(f"Filtering factors for user organizations: {[org.name for org in user_orgs]}")

        # فیلترهای اضافی
        query = self.request.GET.get('q', '').strip()
        date_query = self.request.GET.get('date', '').strip()
        status_query = self.request.GET.get('status', '').strip()

        if query or date_query or status_query:
            filter_conditions = Q()
            if query:
                try:
                    query_num = float(query.replace(',', ''))
                    filter_conditions |= Q(amount=query_num)
                except ValueError:
                    pass
                filter_conditions |= (
                    Q(number__icontains=query) |
                    Q(tankhah__number__icontains=query) |
                    Q(description__icontains=query) |
                    Q(tankhah__project__name__icontains=query)
                )
            if date_query:
                try:
                    parts = date_query.split('-')
                    if len(parts) == 1:  # فقط سال
                        year = int(parts[0])
                        gregorian_year = year - 621
                        filter_conditions &= Q(date__year=gregorian_year)
                    elif len(parts) == 2:  # سال و ماه
                        year, month = map(int, parts)
                        jalali_date = jdate(year, month, 1)
                        gregorian_date = jalali_date.togregorian()
                        filter_conditions &= Q(date__year=gregorian_date.year, date__month=gregorian_date.month)
                    elif len(parts) == 3:  # تاریخ کامل
                        year, month, day = map(int, parts)
                        jalali_date = jdate(year, month, day)
                        gregorian_date = jalali_date.togregorian()
                        filter_conditions &= Q(date__date=gregorian_date)
                    else:
                        raise ValueError("Invalid date format")
                except ValueError as e:
                    messages.error(self.request, _('فرمت تاریخ نامعتبر است. از فرمت‌های 1403، 1403-05 یا 1403-05-15 استفاده کنید.'))
                    filter_conditions &= Q(date__isnull=True)
                except Exception as e:
                    messages.error(self.request, _('خطا در پردازش تاریخ: ') + str(e))
                    filter_conditions &= Q(date__isnull=True)
            if status_query and status_query in dict(Factor.STATUS_CHOICES):
                filter_conditions &= Q(status=status_query)

            queryset = queryset.filter(filter_conditions).distinct()

        # بهینه‌سازی کوئری
        queryset = queryset.select_related(
            'tankhah', 'tankhah__project', 'tankhah__organization', 'locked_by_stage'
        ).order_by('tankhah__project__name', 'tankhah__number', '-date')

        logger.info(f"Final factor count: {queryset.count()}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['query'] = self.request.GET.get('q', '')
        context['date_query'] = self.request.GET.get('date', '')
        context['status_query'] = self.request.GET.get('status', '')
        context['is_hq'] = any(up.post.organization.org_type == 'HQ' for up in user.userpost_set.all())
        context['status_choices'] = Factor.STATUS_CHOICES

        # گروه‌بندی فاکتورها بر اساس پروژه و تنخواه
        factor_list = context[self.context_object_name]
        grouped_factors = {}
        for factor in factor_list:
            try:
                tankhah = factor.tankhah
                project_key = tankhah.project.name if tankhah.project else _('بدون پروژه')
                if project_key not in grouped_factors:
                    grouped_factors[project_key] = {
                        'project': tankhah.project,
                        'tankhahs': {}
                    }

                tankhah_key = tankhah.number
                if tankhah_key not in grouped_factors[project_key]['tankhahs']:
                    grouped_factors[project_key]['tankhahs'][tankhah_key] = {
                        'tankhah': tankhah,
                        'factors': [],
                        'total_amount': Decimal('0')
                    }

                grouped_factors[project_key]['tankhahs'][tankhah_key]['factors'].append(factor)
                grouped_factors[project_key]['tankhahs'][tankhah_key]['total_amount'] += factor.amount or Decimal('0')

                current_stage_order = tankhah.current_stage.order if tankhah.current_stage else 0
                user_posts = user.userpost_set.filter(is_active=True, end_date__isnull=True)
                user_can_approve = any(
                    p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists()
                    for p in user_posts
                ) and tankhah.status in ['DRAFT', 'PENDING']
                factor.can_approve = user_can_approve
                factor.is_locked = factor.locked_by_stage is not None and factor.locked_by_stage.order < current_stage_order

            except Exception as e:
                logger.error(f"Error processing factor {factor.number}: {str(e)}")
                factor.can_approve = False
                factor.is_locked = True

        context['grouped_factors'] = grouped_factors
        context['errors'] = []
        return context

from django.db.models import Q, Sum, Prefetch

class FactorListView(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tankhah/factor_list.html'
    context_object_name = 'factors'
    paginate_by = 10
    extra_context = {'title': _('لیست فاکتورها')}
    permission_codenames = ['tankhah.factor_view']

    def get_queryset(self):
        """بازگرداندن کوئری‌ست فیلترشده فاکتورها با بهینه‌سازی برای MySQL."""
        user = self.request.user
        logger.info(f"[FactorListView] User: {user}, is_superuser: {user.is_superuser}")

        # بررسی نصب jdatetime
        if jdate is None:
            messages.error(self.request, _('ماژول jdatetime نصب نیست. لطفاً با مدیر سیستم تماس بگیرید.'))
            return Factor.objects.none()

        # سازمان‌های کاربر
        user_posts = user.userpost_set.filter(is_active=True, end_date__isnull=True)
        if not user_posts.exists():
            logger.info(f"[FactorListView] User {user.username} has no active posts, returning empty queryset")
            return Factor.objects.none()

        user_orgs = [up.post.organization for up in user_posts]
        is_hq_user = any(up.post.organization.org_type == 'HQ' for up in user_posts)

        # فیلتر اولیه
        if is_hq_user:
            queryset = Factor.objects.all()
            logger.info("[FactorListView] HQ user, retrieving all factors")
        else:
            queryset = Factor.objects.filter(tankhah__organization__in=user_orgs)
            logger.info(f"[FactorListView] Filtering factors for organizations: {[org.name for org in user_orgs]}")

        # فیلترهای اضافی
        query = self.request.GET.get('q', '').strip()
        date_query = self.request.GET.get('date', '').strip()
        status_query = self.request.GET.get('status', '').strip()

        filter_conditions = Q()

        # فیلتر جستجو
        if query:
            try:
                query_num = Decimal(query.replace(',', ''))
                filter_conditions |= Q(amount=query_num)
            except (ValueError, Decimal.InvalidOperation):
                pass
            filter_conditions |= (
                Q(number__icontains=query) |
                Q(tankhah__number__icontains=query) |
                Q(description__icontains=query) |
                Q(tankhah__project__name__icontains=query)
            )
            logger.info(f"[FactorListView] Search query '{query}', count: {queryset.filter(filter_conditions).count()}")

        # فیلتر تاریخ (شمسی به میلادی)
        if date_query:
            try:
                parts = date_query.split('-')
                if len(parts) == 1:  # فقط سال
                    year = int(parts[0])
                    gregorian_year = year - 621
                    filter_conditions &= Q(date__year=gregorian_year)
                elif len(parts) == 2:  # سال و ماه
                    year, month = map(int, parts)
                    jalali_date = jdate(year, month, 1)
                    gregorian_date = jalali_date.togregorian()
                    filter_conditions &= Q(date__year=gregorian_date.year, date__month=gregorian_date.month)
                elif len(parts) == 3:  # تاریخ کامل
                    year, month, day = map(int, parts)
                    jalali_date = jdate(year, month, day)
                    gregorian_date = jalali_date.togregorian()
                    filter_conditions &= Q(date=gregorian_date)
                else:
                    raise ValueError("Invalid date format")
            except ValueError as e:
                logger.warning(f"[FactorListView] Invalid date format: {date_query}, error: {str(e)}")
                messages.error(self.request, _('فرمت تاریخ نامعتبر است (1403، 1403-05، یا 1403-05-15).'))
                filter_conditions &= Q(date__isnull=True)
            logger.info(f"[FactorListView] Date filter '{date_query}', count: {queryset.filter(filter_conditions).count()}")

        # فیلتر وضعیت
        if status_query and status_query in dict(Factor.STATUS_CHOICES):
            filter_conditions &= Q(status=status_query)
            logger.info(f"[FactorListView] Status filter '{status_query}', count: {queryset.filter(filter_conditions).count()}")

        # اعمال فیلترها
        if filter_conditions:
            queryset = queryset.filter(filter_conditions)
            if not queryset.exists():
                messages.info(self.request, _('هیچ فاکتوری یافت نشد.'))
                logger.info("[FactorListView] No factors found with filters")

        # بهینه‌سازی کوئری برای MySQL
        final_queryset = queryset.select_related(
            'tankhah', 'tankhah__project', 'tankhah__organization', 'locked_by_stage'
        ).prefetch_related(
            Prefetch('items', queryset=FactorItem.objects.all())  # اصلاح Prefetch
        ).order_by('tankhah__organization__name', 'tankhah__project__name', 'tankhah__number', '-date')

        logger.info(f"[FactorListView] Final factor count: {final_queryset.count()}")
        return final_queryset

    def get_context_data(self, **kwargs):
        """ایجاد کنتکست با گروه‌بندی فاکتورها بر اساس شعبه، پروژه، تنخواه و وضعیت."""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        logger.info(f"[FactorListView] Creating context for user: {user}")

        # اطلاعات پایه کنتکست
        user_posts = user.userpost_set.filter(is_active=True, end_date__isnull=True)
        context['is_hq'] = any(up.post.organization.org_type == 'HQ' for up in user_posts)
        context['query'] = self.request.GET.get('q', '')
        context['date_query'] = self.request.GET.get('date', '')
        context['status_query'] = self.request.GET.get('status', '')
        context['status_choices'] = Factor.STATUS_CHOICES

        # گروه‌بندی فاکتورها
        factor_list = context[self.context_object_name]
        grouped_by_org = {}

        for factor in factor_list:
            try:
                tankhah = factor.tankhah
                org = tankhah.organization
                org_key = org.name if org else _('بدون شعبه')
                project_key = tankhah.project.name if tankhah.project else _('بدون پروژه')
                tankhah_key = tankhah.number

                # مقداردهی اولیه شعبه
                if org_key not in grouped_by_org:
                    grouped_by_org[org_key] = {
                        'organization': org,
                        'projects': {},
                        'total_amount': Decimal('0')
                    }

                # مقداردهی اولیه پروژه
                if project_key not in grouped_by_org[org_key]['projects']:
                    grouped_by_org[org_key]['projects'][project_key] = {
                        'project': tankhah.project,
                        'tankhahs': {},
                        'total_amount': Decimal('0')
                    }

                # مقداردهی اولیه تنخواه
                if tankhah_key not in grouped_by_org[org_key]['projects'][project_key]['tankhahs']:
                    grouped_by_org[org_key]['projects'][project_key]['tankhahs'][tankhah_key] = {
                        'tankhah': tankhah,
                        'factors': {
                            'approved': [],
                            'rejected': [],
                            'others': []
                        },
                        'total_amount': Decimal('0')
                    }

                # دسته‌بندی فاکتور بر اساس وضعیت
                factor_amount = factor.amount or Decimal('0')
                factor_status = factor.status.lower()
                if factor_status == 'approved':
                    grouped_by_org[org_key]['projects'][project_key]['tankhahs'][tankhah_key]['factors']['approved'].append(factor)
                elif factor_status == 'rejected':
                    grouped_by_org[org_key]['projects'][project_key]['tankhahs'][tankhah_key]['factors']['rejected'].append(factor)
                else:
                    grouped_by_org[org_key]['projects'][project_key]['tankhahs'][tankhah_key]['factors']['others'].append(factor)

                # محاسبه مبالغ
                grouped_by_org[org_key]['projects'][project_key]['tankhahs'][tankhah_key]['total_amount'] += factor_amount
                grouped_by_org[org_key]['projects'][project_key]['total_amount'] += factor_amount
                grouped_by_org[org_key]['total_amount'] += factor_amount

                # محاسبه دسترسی تأیید
                current_stage_order = tankhah.current_stage.order if tankhah.current_stage else 0
                user_can_approve = any(
                    p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists()
                    for p in user_posts
                ) and tankhah.status in ['DRAFT', 'PENDING']
                factor.can_approve = user_can_approve
                factor.is_locked = factor.locked_by_stage is not None and factor.locked_by_stage.order < current_stage_order

            except Exception as e:
                logger.error(f"[FactorListView] Error processing factor {factor.number}: {str(e)}")
                factor.can_approve = False
                factor.is_locked = True

        context['grouped_by_org'] = grouped_by_org
        context['errors'] = []
        logger.info(f"[FactorListView] Number of organizations: {len(grouped_by_org)}")
        return context

