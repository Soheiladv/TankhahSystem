
import logging
from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from persiantools import jdatetime

from core.models import PostAction

logger = logging.getLogger(__name__)

from django.views.generic import ListView
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils.translation import gettext_lazy as _
from tankhah.models import Factor, FactorItem, ApprovalLog
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

#---------------------------------

class FactorListView(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tankhah/factor_list.html'
    context_object_name = 'factors'
    permission_codenames = ['tankhah.factor_view']
    check_organization = True
    organization_filter_field = 'tankhah__organization__id__in'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        logger.info(f"--- [FactorListView] START: Fetching queryset for user: {user.username} ---")

        qs = super().get_queryset()
        initial_count = qs.count()
        logger.info(f"Initial queryset count: {initial_count}")

        user_org_ids = set()
        user_level = None
        for user_post in user.userpost_set.filter(is_active=True):
            org = user_post.post.organization
            user_org_ids.add(org.id)
            while org.parent_organization:
                org = org.parent_organization
                user_org_ids.add(org.id)
            user_level = min(user_level, user_post.post.level) if user_level else user_post.post.level
        logger.info(f"User {user.username} organizations: {user_org_ids}, level: {user_level}")

        query = self.request.GET.get('q', '').strip()
        status_query = self.request.GET.get('status', '').strip()
        date_query = self.request.GET.get('date', '').strip()

        filter_conditions = Q()
        if query:
            filter_conditions |= (
                Q(number__icontains=query) |
                Q(description__icontains=query) |
                Q(tankhah__number__icontains=query)
            )
        if status_query:
            filter_conditions &= Q(status=status_query)
        if date_query:
            try:
                gregorian_date = jdatetime.datetime.strptime(date_query, '%Y-%m-%d').togregorian().date()
                filter_conditions &= Q(date=gregorian_date)
            except (ValueError, TypeError):
                messages.warning(self.request, _("فرمت تاریخ برای جستجو نامعتبر است."))

        if filter_conditions:
            qs = qs.filter(filter_conditions)
            logger.info(f"Applied filters (q='{query}', status='{status_query}', date='{date_query}'). New count: {qs.count()}")

        qs = qs.select_related(
            'tankhah__organization', 'tankhah__project', 'tankhah__current_stage', 'created_by', 'category'
        ).prefetch_related(
            'items',
            Prefetch(
                'approval_logs',
                queryset=ApprovalLog.objects.filter(action='APPROVE').select_related('user', 'post').order_by('-timestamp'),
                to_attr='approvers_raw'
            )
        ).order_by('-date', '-pk')

        logger.info(f"Final queryset count: {qs.count()}")
        for factor in qs:
            logger.debug(f"Factor {factor.number}: org={factor.tankhah.organization.id}, status={factor.status}")
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        logger.info(f"--- [FactorListView] START: Creating context for user: {user.username} ---")

        user_level = None
        user_org_ids = set()
        for user_post in user.userpost_set.filter(is_active=True):
            user_org_ids.add(user_post.post.organization.id)
            user_level = min(user_level, user_post.post.level) if user_level else user_post.post.level
        context.update({
            'is_hq': (
                user.is_superuser or
                user.has_perm('tankhah.Tankhah_view_all') or
                user.userpost_set.filter(
                    is_active=True,
                    post__organization__org_type__fname='HQ'
                ).exists()
            ),
            'query': self.request.GET.get('q', ''),
            'status_query': self.request.GET.get('status', ''),
            'date_query': self.request.GET.get('date', ''),
            'status_choices': Factor.STATUS_CHOICES,
            'user_level': user_level,
        })

        grouped_by_org = {}
        factor_list = context.get(self.context_object_name, [])
        logger.info(f"Processing {len(factor_list)} factors for grouping.")

        user_posts = list(
            user.userpost_set.filter(is_active=True).select_related('post').prefetch_related('post__stageapprover_set')
        )

        for factor in factor_list:
            try:
                tankhah = factor.tankhah
                if not tankhah:
                    logger.warning(f"Factor {factor.number} has no tankhah")
                    continue
                org = tankhah.organization
                project = tankhah.project
                if not org or not project:
                    logger.warning(f"Factor {factor.number} missing org or project")
                    continue

                org_name = org.name
                if org_name not in grouped_by_org:
                    grouped_by_org[org_name] = {'org_obj': org, 'projects': {}, 'total_amount': Decimal('0')}
                if project.name not in grouped_by_org[org_name]['projects']:
                    grouped_by_org[org_name]['projects'][project.name] = {'project_obj': project, 'tankhahs': {}, 'total_amount': Decimal('0')}
                if tankhah.number not in grouped_by_org[org_name]['projects'][project.name]['tankhahs']:
                    grouped_by_org[org_name]['projects'][project.name]['tankhahs'][tankhah.number] = {
                        'tankhah_obj': tankhah,
                        'factors': {
                            'pending': [], 'approved': [], 'rejected': [], 'paid': [], 'draft': [], 'others': []
                        },
                        'total_amount': Decimal('0')
                    }

                status_key = factor.status.lower() if factor.status else 'others'
                grouped_by_org[org_name]['projects'][project.name]['tankhahs'][tankhah.number]['factors'][status_key].append(factor)

                factor_amount = factor.amount or Decimal('0')
                grouped_by_org[org_name]['projects'][project.name]['tankhahs'][tankhah.number]['total_amount'] += factor_amount
                grouped_by_org[org_name]['projects'][project.name]['total_amount'] += factor_amount
                grouped_by_org[org_name]['total_amount'] += factor_amount

                raw_logs = getattr(factor, 'approvers_raw', [])
                names = [log.user.get_full_name() or log.user.username for log in raw_logs if log.user]
                factor.approvers_display = ', '.join(names) if names else _('بدون تأییدکننده')
                factor.last_approver = names[0] if names else None

                factor.can_approve = False
                if tankhah.status in ['DRAFT', 'PENDING'] and tankhah.current_stage:
                    for user_post in user_posts:
                        if any(sa.stage_id == tankhah.current_stage_id for sa in user_post.post.stageapprover_set.all()):
                            factor.can_approve = True
                            logger.debug(f"User {user.username} can approve factor {factor.number} in stage {tankhah.current_stage.name}")
                            break
                        if user_post.post.level <= tankhah.current_stage.order:
                            factor.can_approve = True
                            logger.debug(f"User {user.username} can approve factor {factor.number} due to level {user_post.post.level}")
                            break

                factor.is_locked = (
                    factor.locked_by_stage and
                    tankhah.current_stage and
                    factor.locked_by_stage.order < tankhah.current_stage.order
                )
                logger.debug(f"Factor {factor.number}: can_approve={factor.can_approve}, is_locked={factor.is_locked}")

            except Exception as e:
                logger.error(f"Error while grouping factor PK={factor.pk}: {e}", exc_info=True)
                factor.can_approve = False
                factor.is_locked = True
                factor.approvers_display = _('خطا در بارگذاری تأییدکنندگان')
                factor.last_approver = None

        context['grouped_by_org'] = grouped_by_org
        logger.info(f"Finished grouping. Found {len(grouped_by_org)} organization groups.")
        return context

#---------------------------------

##################################
class old_1_FactorListView2(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tankhah/Factors/factor_list_final.html'
    context_object_name = 'factors'
    paginate_by = 20
    permission_codenames = ['tankhah.factor_view']
    organization_filter_field = 'tankhah__organization__id__in'

    def _user_is_hq(self, user):
        """متد متمرکز برای تشخیص کاربر دفتر مرکزی (HQ)."""
        if user.is_superuser or user.has_perm('tankhah.Tankhah_view_all'):
            return True
        return user.userpost_set.filter(
            is_active=True,
            post__organization__org_type__fname='HQ'
        ).exists()

    def get_queryset(self):
        """آماده‌سازی کوئری اصلی برای واکشی فاکتورها."""
        user = self.request.user
        queryset = super().get_queryset()

        # اعمال فیلترهای جستجو
        query = self.request.GET.get('q', '').strip()
        status_query = self.request.GET.get('status', '').strip()
        date_query = self.request.GET.get('date', '').strip()

        filter_conditions = Q()
        if query:
            filter_conditions |= (Q(number__icontains=query) | Q(description__icontains=query) | Q(
                tankhah__number__icontains=query))
        if status_query:
            filter_conditions &= Q(status=status_query)
        if date_query:
            try:
                gregorian_date = jdatetime.datetime.strptime(date_query, '%Y-%m-%d').togregorian().date()
                filter_conditions &= Q(date=gregorian_date)
            except (ValueError, TypeError):
                messages.warning(self.request, _("فرمت تاریخ برای جستجو نامعتبر است."))

        if filter_conditions:
            queryset = queryset.filter(filter_conditions)

        # بهینه‌سازی نهایی کوئری
        return queryset.select_related(
            'tankhah__organization', 'tankhah__project', 'tankhah__current_stage', 'created_by', 'category'
        ).prefetch_related(
            'items',
            Prefetch(
                'approval_logs',
                queryset=ApprovalLog.objects.filter(action='APPROVE').select_related('user', 'post').order_by('date'),
                to_attr='approvers_list'
            )
        ).order_by('-date', '-pk')

    def get_context_data(self, **kwargs):
        """
        ایجاد کنتکست نهایی با ساختار داده پایدار برای جلوگیری از خطاهای تمپلیت.
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context.update({
            'is_hq': self._user_is_hq(user),
            'query': self.request.GET.get('q', ''),
            'status_query': self.request.GET.get('status', ''),
            'status_choices': Factor.STATUS_CHOICES,
        })

        grouped_data = {}
        user_posts = list(
            user.userpost_set.filter(is_active=True).select_related('post').prefetch_related('post__stageapprover_set'))

        factor_list = context.get(self.context_object_name, [])
        logger.info(f"Processing {len(factor_list)} factors for grouping.")

        for factor in factor_list:
            try:
                tankhah = factor.tankhah
                if not tankhah: continue
                org = tankhah.organization
                project = tankhah.project
                if not org or not project: continue

                # ایجاد ساختار گروه‌بندی با کلیدهای عددی (ID)
                if org.id not in grouped_data:
                    grouped_data[org.id] = {'org_obj': org, 'projects': {}}
                if project.id not in grouped_data[org.id]['projects']:
                    grouped_data[org.id]['projects'][project.id] = {'project_obj': project, 'tankhahs': {}}

                # --- بخش کلیدی اصلاح شده: ساختار ثابت و از پیش تعریف شده برای فاکتورها ---
                if tankhah.id not in grouped_data[org.id]['projects'][project.id]['tankhahs']:
                    grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id] = {
                        'tankhah_obj': tankhah,
                        'factors': {  # این دیکشنری همیشه تمام کلیدها را خواهد داشت
                            'pending': [],
                            'approved': [],
                            'rejected': [],
                            'paid': [],
                            'draft': [],
                            'others': []
                        }
                    }

                # افزودن فاکتور به لیست وضعیت مربوطه
                status_key = factor.status.lower()
                target_list = grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id]['factors'].get(
                    status_key, 'others')
                target_list.append(factor)

                # محاسبه دسترسی کاربر برای تایید
                can_approve = False
                if tankhah.status in ['DRAFT', 'PENDING'] and tankhah.current_stage:
                    for user_post in user_posts:
                        if any(sa.stage_id == tankhah.current_stage_id for sa in
                               user_post.post.stageapprover_set.all()):
                            can_approve = True
                            break
                factor.can_approve = can_approve

            except Exception as e:
                logger.error(f"Error while grouping factor PK={factor.pk}: {e}", exc_info=True)

        context['grouped_data'] = grouped_data
        return context
# views.py  ───────────────────────────────────────────────────────────────────
class FactorListView2(PermissionBaseView, ListView):
    """
    نسخهٔ بهینه‌شده با:
      • تعیین HQ در متدِ واحد
      • Prefetch تأییدکنندگان و تبدیل فوری به رشتهٔ قابل‌نمایش
      • گروه‌بندی ساده بر اساس id
    """
    model               = Factor
    # template_name       = 'tankhah/factor_list_redesigned.html'
    template_name       = 'tankhah/Factors/factor_list_final.html'
    context_object_name = 'factors'
    paginate_by         = 20
    permission_codenames = ['tankhah.factor_view']

    # ───────────────────────────────────────────
    # ۱)  تشخیص HQ
    # ───────────────────────────────────────────
    def _user_is_hq(self, user):
        if user.is_superuser or user.has_perm('tankhah.Tankhah_view_all'):
            return True
        return user.userpost_set.filter(
            is_active=True,
            post__organization__org_type__fname='HQ'
        ).exists()

    # ───────────────────────────────────────────
    # ۲)  Queryset + Prefetch approvers
    # ───────────────────────────────────────────
    def get_queryset(self):
        user = self.request.user

        qs = Factor.objects.all() if self._user_is_hq(user) else (
            Factor.objects.filter(
                tankhah__organization__id__in=user.userpost_set.filter(
                    is_active=True).values_list('post__organization_id', flat=True))
        )

        # فیلتر‌های فرم جستجو
        q = self.request.GET.get('q', '').strip()
        status_q = self.request.GET.get('status', '').strip()

        if q:
            qs = qs.filter(
                Q(number__icontains=q) |
                Q(description__icontains=q) |
                Q(tankhah__number__icontains=q)
            )
        if status_q:
            qs = qs.filter(status=status_q)

        # --- Prefetch approvers ---
        approver_qs = (
            ApprovalLog.objects
            .filter(action='APPROVE')
            .select_related('user', 'post')
            .order_by('-timestamp')
        )
        qs = (qs
              .select_related(
                  'tankhah__organization', 'tankhah__project',
                  'tankhah__current_stage', 'created_by', 'category')
              .prefetch_related(
                  'items',
                  Prefetch('approval_logs',
                           queryset=approver_qs,
                           to_attr='approvers_raw'))
              .order_by('-date', '-pk')
        )
        return qs

    # ───────────────────────────────────────────
    # ۳)  Context + گروه‌بندی + ساخت لیست تأیید‌کننده
    # ───────────────────────────────────────────
    def get_context_data(self, **kwargs):
        ctx   = super().get_context_data(**kwargs)
        user  = self.request.user
        qs    = ctx[self.context_object_name]

        # نام‌های تأییدکننده برای هر فاکتور
        for f in qs:
            raw_logs = getattr(f, 'approvers_raw', [])
            logger.debug(  # 🪵 هر فاکتور چند لاگ APPROVE دارد؟
                "[APPROVER] Factor %s ⇒ %d logs",
                f.pk, len(raw_logs)
            )
            names = []
            for log in raw_logs:
                logger.debug(  # 🪵 جزئیات تک‌تک لاگ‌ها
                    "[APPROVER]  • log #%s | action=%s | user=%s",
                    log.pk, log.action, getattr(log.user, 'username', None)
                )
                if log.user:  # user تهی نیست؟
                    names.append(log.user.get_full_name() or log.user.username)

            f.approvers_display = ', '.join(names) if names else _('بدون تأییدکننده')
            f.last_approver = names[0] if names else None

            names = [log.user.get_full_name() or log.user.username
                     for log in getattr(f, 'approvers_raw', []) if log.user]
            f.approvers_display = ', '.join(names) if names else _('بدون تأییدکننده')
            f.last_approver     = names[0] if names else None

        # ---- گروه‌بندی (ID-base) ----
        grouped = {}
        for f in qs:
            try:
                org     = f.tankhah.organization
                project = f.tankhah.project
                tk      = f.tankhah

                grouped.setdefault(org.id, {
                    'org': org, 'projects': {}
                })
                grouped[org.id]['projects'].setdefault(project.id, {
                    'project': project, 'tankhahs': {}
                })
                grouped[org.id]['projects'][project.id]['tankhahs'].setdefault(tk.id, {
                    'tankhah': tk, 'factors': []
                })
                grouped[org.id]['projects'][project.id]['tankhahs'][tk.id]['factors'].append(f)

            except Exception as e:
                logger.error('Grouping error for factor %s: %s', f.pk, e, exc_info=True)

        # ---- سایر متغیرهای قالب ----
        ctx.update({
            'is_hq'        : self._user_is_hq(user),
            'query'        : self.request.GET.get('q', ''),
            'status_query' : self.request.GET.get('status', ''),
            'status_choices': Factor.STATUS_CHOICES,
            'grouped_data' : grouped,
        })
        return ctx
########################
class __OptimizedFactorListView(PermissionBaseView, ListView):
    """
    نسخه نهایی و بهینه شده برای نمایش لیست فاکتورها با گروه‌بندی و دسترسی کامل.
    این ویو از معماری کلاس پایه برای کنترل دسترسی استفاده می‌کند و داده‌ها را
    به صورت بهینه برای تمپلیت آکاردئونی آماده می‌سازد.
    """
    # =========== بخش ۱: تعاریف اصلی ویو ===========
    model = Factor
    template_name = 'tankhah/Factors/factor_list_accordion.html'  # استفاده از نام تمپلیت آکاردئونی جدید
    context_object_name = 'factors'
    paginate_by = 25  # تعداد آیتم‌ها در هر صفحه
    permission_codenames = ['tankhah.factor_view']

    # این متغیر کلیدی به کلاس پایه (PermissionBaseView) می‌گوید که چگونه
    # کوئری این مدل را بر اساس سازمان کاربر فیلتر کند.
    organization_filter_field = 'tankhah__organization__id__in'

    # =========== بخش ۲: متد اصلی برای آماده‌سازی کوئری ===========
    def get_queryset(self):
        """
        این متد مسئول آماده‌سازی کوئری اصلی برای واکشی فاکتورها از دیتابیس است.
        """
        logger.info(
            f"--- [OptimizedFactorListView] START: Fetching queryset for user: {self.request.user.username} ---")

        # مرحله الف: کوئری پایه بر اساس دسترسی از کلاس پدر (PermissionBaseView) فراخوانی می‌شود
        queryset = super().get_queryset()
        logger.info(f"Initial queryset count after permission filter: {queryset.count()}")

        # مرحله ب: اعمال فیلترهای جستجوی کاربر
        query = self.request.GET.get('q', '').strip()
        status_query = self.request.GET.get('status', '').strip()
        date_query = self.request.GET.get('date', '').strip()

        filter_conditions = Q()
        if query:
            filter_conditions |= (Q(number__icontains=query) | Q(description__icontains=query) | Q(
                tankhah__number__icontains=query))
        if status_query:
            filter_conditions &= Q(status=status_query)
        if date_query:
            try:
                gregorian_date = jdatetime.datetime.strptime(date_query, '%Y-%m-%d').togregorian().date()
                filter_conditions &= Q(date=gregorian_date)
            except (ValueError, TypeError):
                messages.warning(self.request, _("فرمت تاریخ برای جستجو نامعتبر است."))

        if filter_conditions:
            queryset = queryset.filter(filter_conditions)
            logger.info(f"Queryset count after applying search filters: {queryset.count()}")

        # مرحله ج: بهینه‌سازی نهایی کوئری با prefetch و select_related
        return queryset.select_related(
            'tankhah__organization', 'tankhah__project', 'tankhah__current_stage', 'created_by', 'category'
        ).prefetch_related(
            'items',
            Prefetch(
                'approval_logs',  # استفاده از related_name صحیح
                queryset=ApprovalLog.objects.filter(action='APPROVE').select_related('user', 'post').order_by('date'),
                to_attr='approvers_list'
            )
        ).order_by('-date', '-pk')

    # =========== بخش ۳: متد اصلی برای آماده‌سازی داده‌های نمایشی ===========
    def get_context_data(self, **kwargs):
        """
        این متد داده‌ها را برای نمایش در تمپلیت گروه‌بندی کرده و محاسبات لازم را انجام می‌دهد.
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user
        logger.info("--- [OptimizedFactorListView] START: Creating context data ---")

        # افزودن اطلاعات فرم جستجو به context
        context.update({
            'is_hq': user.is_hq,  # استفاده از پراپرتی مدل کاربر
            'query': self.request.GET.get('q', ''),
            'status_query': self.request.GET.get('status', ''),
            'status_choices': Factor.STATUS_CHOICES,
        })

        # استفاده از ID به عنوان کلید برای جلوگیری از خطای Unpack در تمپلیت
        grouped_data = {}

        # واکشی بهینه اطلاعات پست‌های کاربر برای محاسبه دسترسی
        user_posts = list(
            user.userpost_set.filter(is_active=True).select_related('post').prefetch_related('post__stageapprover_set'))

        factor_list = context.get(self.context_object_name, [])
        logger.info(f"Processing {len(factor_list)} factors for grouping.")

        for factor in factor_list:
            try:
                tankhah = factor.tankhah
                if not tankhah: continue
                org = tankhah.organization
                project = tankhah.project
                if not org or not project: continue

                # ایجاد ساختار گروه‌بندی با کلیدهای عددی
                if org.id not in grouped_data:
                    grouped_data[org.id] = {'org_obj': org, 'projects': {}}
                if project.id not in grouped_data[org.id]['projects']:
                    grouped_data[org.id]['projects'][project.id] = {'project_obj': project, 'tankhahs': {}}

                # ساختار ثابت و از پیش تعریف شده برای فاکتورها
                if tankhah.id not in grouped_data[org.id]['projects'][project.id]['tankhahs']:
                    grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id] = {
                        'tankhah_obj': tankhah,
                        'factors': {status[0].lower(): [] for status in Factor.STATUS_CHOICES}
                    }

                # افزودن فاکتور به لیست وضعیت مربوطه
                status_key = factor.status.lower()
                if status_key in grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id]['factors']:
                    grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id]['factors'][status_key].append(
                        factor)

                # محاسبه دسترسی کاربر برای تایید
                can_approve = False
                if tankhah.status in ['DRAFT', 'PENDING'] and tankhah.current_stage:
                    for user_post in user_posts:
                        if any(sa.stage_id == tankhah.current_stage_id for sa in
                               user_post.post.stageapprover_set.all()):
                            can_approve = True
                            break
                factor.can_approve = can_approve

            except Exception as e:
                logger.error(f"Error while grouping factor PK={factor.pk}: {e}", exc_info=True)

        context['grouped_data'] = grouped_data
        logger.info(f"Finished grouping context. Found {len(grouped_data)} organization groups.")
        return context
class OptimizedFactorListView2(PermissionBaseView, ListView):
    """
    ویوی بهینه برای نمایش لیست فاکتورها با گروه‌بندی آکاردئونی، فیلترهای جستجو و دسترسی‌های سازمانی.
    ویژگی‌ها:
    - بهینه‌سازی کوئری‌ها با select_related و prefetch_related
    - گروه‌بندی مبتنی بر ID برای جلوگیری از مشکلات unpack
    - مدیریت خطاها و لاگ‌گیری دقیق
    - پشتیبانی از فیلترهای جستجو (شماره، توضیحات، وضعیت، تاریخ)
    """
    model = Factor
    template_name = 'tankhah/Factors/factor_list_final1.html'
    context_object_name = 'factors'
    paginate_by = 25
    permission_codenames = ['tankhah.factor_view']
    organization_filter_field = 'tankhah__organization__id__in'

    def _user_is_hq(self, user):
        """
        بررسی وضعیت کاربر به‌عنوان کاربر دفتر مرکزی (HQ).
        نتیجه کش می‌شود تا از محاسبات تکراری جلوگیری شود.
        """
        if hasattr(user, '_is_hq_cache'):
            return user._is_hq_cache

        is_hq = (user.is_superuser or
                 user.has_perm('tankhah.Tankhah_view_all') or
                 user.userpost_set.filter(
                     is_active=True,
                     post__organization__org_type__fname='HQ'
                 ).exists())

        logger.debug(f"[OptimizedFactorListView] User '{user.username}' HQ status: {is_hq}")
        user._is_hq_cache = is_hq
        return is_hq

    def get_queryset(self):
        """
        آماده‌سازی کوئری فاکتورها با فیلترهای جستجو و بهینه‌سازی‌های دیتابیس.
        """
        logger.info(f"--- [OptimizedFactorListView] Fetching queryset for user: {self.request.user.username} ---")

        # کوئری پایه با اعمال فیلترهای دسترسی
        queryset = super().get_queryset()
        logger.debug(f"Initial queryset count: {queryset.count()}")

        # فیلترهای جستجو
        query = self.request.GET.get('q', '').strip()
        status_query = self.request.GET.get('status', '').strip()
        date_query = self.request.GET.get('date', '').strip()

        filter_conditions = Q()
        if query:
            filter_conditions |= (Q(number__icontains=query) |
                                  Q(description__icontains=query) |
                                  Q(tankhah__number__icontains=query))
        if status_query:
            filter_conditions &= Q(status=status_query)
        if date_query:
            try:
                gregorian_date = jdatetime.datetime.strptime(date_query, '%Y-%m-%d').togregorian().date()
                filter_conditions &= Q(date=gregorian_date)
            except (ValueError, TypeError):
                messages.warning(self.request, _("فرمت تاریخ برای جستجو نامعتبر است."))

        if filter_conditions:
            queryset = queryset.filter(filter_conditions)
            logger.debug(f"Queryset count after filters: {queryset.count()}")

        # بهینه‌سازی کوئری با select_related و prefetch_related
        return queryset.select_related(
            'tankhah__organization', 'tankhah__project', 'tankhah__current_stage', 'created_by', 'category'
        ).prefetch_related(
            'items',
            Prefetch(
                'approval_logs',
                queryset=ApprovalLog.objects.filter(action='APPROVE').select_related('user', 'post').order_by('date'),
                to_attr='approvers_list'
            )
        ).order_by('-date', '-pk')

    def get_context_data(self, **kwargs):
        """
        آماده‌سازی داده‌های context برای نمایش در تمپلیت با گروه‌بندی و محاسبات دسترسی.
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user
        logger.info(f"--- [OptimizedFactorListView] Creating context for user: {user.username} ---")

        # اطلاعات پایه برای فرم جستجو
        context.update({
            'is_hq': self._user_is_hq(user),
            'query': self.request.GET.get('q', ''),
            'status_query': self.request.GET.get('status', ''),
            'date_query': self.request.GET.get('date', ''),
            'status_choices': Factor.STATUS_CHOICES,
        })

        # آماده‌سازی گروه‌بندی
        grouped_data = {}
        factor_list = context.get(self.context_object_name, [])
        logger.debug(f"Processing {len(factor_list)} factors for grouping.")

        # کش کردن اطلاعات پست‌های کاربر
        user_posts = list(
            user.userpost_set.filter(is_active=True)
            .select_related('post')
            .prefetch_related('post__stageapprover_set')
        )

        for factor in factor_list:
            try:
                tankhah = factor.tankhah
                if not tankhah:
                    logger.warning(f"Factor {factor.pk} has no tankhah.")
                    continue
                org = tankhah.organization
                project = tankhah.project
                if not org or not project:
                    logger.warning(f"Factor {factor.pk} missing org or project.")
                    continue

                # گروه‌بندی با کلیدهای عددی (ID-based)
                if org.id not in grouped_data:
                    grouped_data[org.id] = {
                        'org_obj': org,
                        'total_amount': Decimal('0'),
                        'projects': {}
                    }
                if project.id not in grouped_data[org.id]['projects']:
                    grouped_data[org.id]['projects'][project.id] = {
                        'project_obj': project,
                        'total_amount': Decimal('0'),
                        'tankhahs': {}
                    }
                if tankhah.id not in grouped_data[org.id]['projects'][project.id]['tankhahs']:
                    grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id] = {
                        'tankhah_obj': tankhah,
                        'total_amount': Decimal('0'),
                        'factors': {status[0].lower(): [] for status in Factor.STATUS_CHOICES}
                    }

                # افزودن فاکتور به لیست وضعیت مربوطه
                status_key = factor.status.lower()
                if status_key in grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id]['factors']:
                    grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id]['factors'][status_key].append(
                        factor)

                # محاسبه مبلغ کل
                factor_amount = factor.amount or Decimal('0')
                grouped_data[org.id]['total_amount'] += factor_amount
                grouped_data[org.id]['projects'][project.id]['total_amount'] += factor_amount
                grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id]['total_amount'] += factor_amount

                # محاسبه تأییدکنندگان
                approvers = [log.user for log in factor.approvers_list if log.user]
                factor.approvers_display = ', '.join(
                    approver.get_full_name() or approver.username for approver in approvers
                ) if approvers else _('بدون تأییدکننده')
                factor.last_approver = approvers[0] if approvers else None

                # محاسبه دسترسی تأیید
                factor.can_approve = False
                if tankhah.status in ['DRAFT', 'PENDING'] and tankhah.current_stage:
                    for user_post in user_posts:
                        if any(sa.stage_id == tankhah.current_stage_id for sa in
                               user_post.post.stageapprover_set.all()):
                            factor.can_approve = True
                            break

            except Exception as e:
                logger.error(f"Error processing factor PK={factor.pk}: {e}", exc_info=True)
                factor.approvers_display = _('خطا در بارگذاری تأییدکنندگان')
                factor.last_approver = None
                factor.can_approve = False

        context['grouped_data'] = grouped_data
        logger.info(f"Finished grouping. Found {len(grouped_data)} organization groups.")
        return context
class OptimizedFactorListView33(PermissionBaseView, ListView):
    """
    ویوی بهینه برای نمایش لیست فاکتورها با گروه‌بندی آکاردئونی، فیلترهای جستجو و دسترسی‌های سازمانی.
    ویژگی‌ها:
    - بهینه‌سازی کوئری‌ها با select_related و prefetch_related
    - گروه‌بندی مبتنی بر ID برای جلوگیری از مشکلات unpack
    - مدیریت خطاها و لاگ‌گیری دقیق
    - پشتیبانی از فیلترهای جستجو (شماره، توضیحات، وضعیت، تاریخ)
    """
    model = Factor
    template_name = 'tankhah/Factors/factor_list_final1.html'
    context_object_name = 'factors'
    paginate_by = 25
    permission_codenames = ['tankhah.factor_view']
    organization_filter_field = 'tankhah__organization__id__in'

    def _user_is_hq(self, user):
        """
        بررسی وضعیت کاربر به‌عنوان کاربر دفتر مرکزی (HQ).
        نتیجه کش می‌شود تا از محاسبات تکراری جلوگیری شود.
        """
        if hasattr(user, '_is_hq_cache'):
            logger.debug(
                f"[OptimizedFactorListView] Using cached HQ status for user '{user.username}': {user._is_hq_cache}")
            return user._is_hq_cache

        is_hq = (user.is_superuser or
                 user.has_perm('tankhah.Tankhah_view_all') or
                 user.userpost_set.filter(
                     is_active=True,
                     post__organization__org_type__fname='HQ'
                 ).exists())

        logger.debug(f"[OptimizedFactorListView] User '{user.username}' HQ status: {is_hq}")
        user._is_hq_cache = is_hq
        return is_hq

    def get_queryset(self):
        """
        آماده‌سازی کوئری فاکتورها با فیلترهای جستجو و بهینه‌سازی‌های دیتابیس.
        """
        logger.info(f"--- [OptimizedFactorListView] Fetching queryset for user: {self.request.user.username} ---")

        # کوئری پایه با اعمال فیلترهای دسترسی
        queryset = super().get_queryset()
        logger.debug(f"Initial queryset count: {queryset.count()}")

        # فیلترهای جستجو
        query = self.request.GET.get('q', '').strip()
        status_query = self.request.GET.get('status', '').strip()
        date_query = self.request.GET.get('date', '').strip()

        filter_conditions = Q()
        if query:
            filter_conditions |= (Q(number__icontains=query) |
                                  Q(description__icontains=query) |
                                  Q(tankhah__number__icontains=query))
        if status_query:
            filter_conditions &= Q(status=status_query)
        if date_query:
            try:
                gregorian_date = jdatetime.datetime.strptime(date_query, '%Y-%m-%d').togregorian().date()
                filter_conditions &= Q(date=gregorian_date)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid date format: {date_query}, error: {e}")
                messages.warning(self.request, _("فرمت تاریخ برای جستجو نامعتبر است."))

        if filter_conditions:
            queryset = queryset.filter(filter_conditions)
            logger.debug(f"Queryset count after filters: {queryset.count()}")

        # بهینه‌سازی کوئری با select_related و prefetch_related
        return queryset.select_related(
            'tankhah__organization', 'tankhah__project', 'tankhah__current_stage', 'created_by', 'category'
        ).prefetch_related(
            'items',
            Prefetch(
                'approval_logs',
                queryset=ApprovalLog.objects.filter(action='APPROVE').select_related('user', 'post').order_by('date'),
                to_attr='approvers_list'
            )
        ).order_by('-date', '-pk')

    def get_context_data(self, **kwargs):
        """
        آماده‌سازی داده‌های context برای نمایش در تمپلیت با گروه‌بندی و محاسبات دسترسی.
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user
        logger.info(f"--- [OptimizedFactorListView] Creating context for user: {user.username} ---")

        # اطلاعات پایه برای فرم جستجو
        context.update({
            'is_hq': self._user_is_hq(user),
            'query': self.request.GET.get('q', ''),
            'status_query': self.request.GET.get('status', ''),
            'date_query': self.request.GET.get('date', ''),
            'status_choices': Factor.STATUS_CHOICES,
        })

        # آماده‌سازی گروه‌بندی
        grouped_data = {}
        factor_list = context.get(self.context_object_name, [])
        logger.debug(f"Processing {len(factor_list)} factors for grouping.")

        # کش کردن اطلاعات پست‌های کاربر
        user_posts = list(
            user.userpost_set.filter(is_active=True)
            .select_related('post')
            .prefetch_related('post__stageapprover_set')
        )

        for factor in factor_list:
            try:
                tankhah = factor.tankhah
                if not tankhah:
                    logger.warning(f"Factor {factor.pk} has no tankhah.")
                    continue
                org = tankhah.organization
                project = tankhah.project
                if not org or not project:
                    logger.warning(f"Factor {factor.pk} missing org or project.")
                    continue

                # گروه‌بندی با کلیدهای عددی (ID-based)
                if org.id not in grouped_data:
                    grouped_data[org.id] = {
                        'org_obj': org,
                        'total_amount': Decimal('0'),
                        'projects': {}
                    }
                if project.id not in grouped_data[org.id]['projects']:
                    grouped_data[org.id]['projects'][project.id] = {
                        'project_obj': project,
                        'total_amount': Decimal('0'),
                        'tankhahs': {}
                    }
                if tankhah.id not in grouped_data[org.id]['projects'][project.id]['tankhahs']:
                    grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id] = {
                        'tankhah_obj': tankhah,
                        'total_amount': Decimal('0'),
                        'factors': {status[0].lower(): [] for status in Factor.STATUS_CHOICES}
                    }

                # افزودن فاکتور به لیست وضعیت مربوطه
                status_key = factor.status.lower()
                if status_key in grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id]['factors']:
                    grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id]['factors'][status_key].append(
                        factor)
                else:
                    logger.warning(f"Invalid status '{status_key}' for factor {factor.pk}")
                    continue

                # محاسبه مبلغ کل
                factor_amount = factor.amount or Decimal('0')
                grouped_data[org.id]['total_amount'] += factor_amount
                grouped_data[org.id]['projects'][project.id]['total_amount'] += factor_amount
                grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id]['total_amount'] += factor_amount

                # محاسبه تأییدکنندگان
                approvers = [log.user for log in getattr(factor, 'approvers_list', []) if log.user]
                if approvers:
                    factor.approvers_display = ', '.join(
                        approver.get_full_name() or approver.username for approver in approvers
                    )
                    factor.last_approver = approvers[0]
                else:
                    factor.approvers_display = _('بدون تأییدکننده')
                    factor.last_approver = None
                    logger.debug(f"No approvers found for factor {factor.pk}")

                # محاسبه دسترسی تأیید
                factor.can_approve = False
                if tankhah.status in ['DRAFT', 'PENDING'] and tankhah.current_stage:
                    for user_post in user_posts:
                        if any(sa.stage_id == tankhah.current_stage_id for sa in
                               user_post.post.stageapprover_set.all()):
                            factor.can_approve = True
                            break
                factor.is_locked = getattr(factor, 'locked_by_stage',
                                           None) and tankhah.current_stage and factor.locked_by_stage.order < tankhah.current_stage.order

            except Exception as e:
                logger.error(f"Error processing factor PK={factor.pk}: {e}", exc_info=True)
                factor.approvers_display = _('خطا در بارگذاری تأییدکنندگان')
                factor.last_approver = None
                factor.can_approve = False
                factor.is_locked = True

        context['grouped_data'] = grouped_data
        logger.info(f"Finished grouping. Found {len(grouped_data)} organization groups.")
        return context


class OptimizedFactorListView(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tankhah/Factors/factor_list_final.html'
    context_object_name = 'factors'
    paginate_by = 20
    permission_codenames = ['tankhah.factor_view']
    organization_filter_field = 'tankhah__organization__id__in'

    def _user_is_hq(self, user):
        """متد متمرکز برای تشخیص کاربر دفتر مرکزی (HQ)."""
        if hasattr(user, '_is_hq_cache'):
            return user._is_hq_cache

        is_hq = (user.is_superuser or
                 user.has_perm('tankhah.Tankhah_view_all') or
                 user.userpost_set.filter(
                     is_active=True,
                     post__organization__org_type__fname='HQ'
                 ).exists())
        user._is_hq_cache = is_hq
        return is_hq

    def get_queryset(self):
        """آماده‌سازی کوئری اصلی برای واکشی فاکتورها."""
        queryset = super().get_queryset()

        query = self.request.GET.get('q', '').strip()
        status_query = self.request.GET.get('status', '').strip()

        if query:
            queryset = queryset.filter(
                Q(number__icontains=query) | Q(description__icontains=query) | Q(tankhah__number__icontains=query))
        if status_query:
            queryset = queryset.filter(status=status_query)

        return queryset.select_related(
            'tankhah__organization', 'tankhah__project', 'tankhah__current_stage', 'created_by', 'category'
        ).prefetch_related(
            'items',
            Prefetch(
                'approval_logs',
                queryset=ApprovalLog.objects.filter(action='APPROVE').select_related('user', 'post').order_by('date'),
                to_attr='approvers_list'
            )
        ).order_by('-date', '-pk')

    def get_context_data(self, **kwargs):
        """آماده‌سازی داده‌ها برای تمپلیت با ساختار داده پایدار."""
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context.update({
            'is_hq': self._user_is_hq(user),
            'query': self.request.GET.get('q', ''),
            'status_query': self.request.GET.get('status', ''),
            'status_choices': Factor.STATUS_CHOICES,
        })

        grouped_data = {}
        user_posts = list(
            user.userpost_set.filter(is_active=True).select_related('post').prefetch_related('post__stageapprover_set'))

        for factor in context['factors']:
            try:
                tankhah = factor.tankhah;
                org = tankhah.organization;
                project = tankhah.project
                if not all([tankhah, org, project]): continue

                if org.id not in grouped_data:
                    grouped_data[org.id] = {'org_obj': org, 'projects': {}}
                if project.id not in grouped_data[org.id]['projects']:
                    grouped_data[org.id]['projects'][project.id] = {'project_obj': project, 'tankhahs': {}}

                # --- FIX: ساختار ثابت و از پیش تعریف شده برای فاکتورها ---
                if tankhah.id not in grouped_data[org.id]['projects'][project.id]['tankhahs']:
                    grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id] = {
                        'tankhah_obj': tankhah,
                        'factors': {  # این دیکشنری همیشه تمام کلیدهای مورد نیاز را خواهد داشت
                            'pending': [], 'approved': [], 'rejected': [],
                            'paid': [], 'draft': [], 'others': []
                        }
                    }

                # افزودن فاکتور به لیست وضعیت مربوطه
                status_key = factor.status.lower()
                target_list = grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id]['factors'].get(
                    status_key)
                if target_list is not None:
                    target_list.append(factor)
                else:  # اگر وضعیتی غیر از موارد استاندارد بود
                    grouped_data[org.id]['projects'][project.id]['tankhahs'][tankhah.id]['factors']['others'].append(
                        factor)

                # محاسبه دسترسی کاربر برای تایید
                factor.can_approve = False
                if tankhah.status in ['DRAFT', 'PENDING'] and tankhah.current_stage:
                    for user_post in user_posts:
                        if any(sa.stage_id == tankhah.current_stage_id for sa in
                               user_post.post.stageapprover_set.all()):
                            factor.can_approve = True
                            break
            except Exception as e:
                logger.error(f"Error while grouping factor PK={factor.pk}: {e}", exc_info=True)

        context['grouped_data'] = grouped_data
        return context

