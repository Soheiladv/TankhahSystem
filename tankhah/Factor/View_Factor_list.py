import jdatetime

from accounts.AccessRule.check_user_access import check_user_factor_access
from core.models import PostAction
from tankhah.constants import ACTION_TYPES
from tankhah.utils import get_factor_current_stage
from django.views.generic import ListView
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils.translation import gettext_lazy as _
from tankhah.models import Factor, FactorItem, ApprovalLog
from core.PermissionBase import PermissionBaseView
from decimal import Decimal
from django.db.models import Q, Sum, Prefetch
import logging
logger = logging.getLogger('Factor_listLogger')

try:
    from jdatetime import date as jdate
except ImportError:
    jdate = None
    logging.error("jdatetime is not installed. Please install it using 'pip install jdatetime'")
#---------------------------------.
class FactorListView(PermissionBaseView, ListView):# اصلی
    model = Factor
    template_name = 'tankhah/factor_list.html'
    context_object_name = 'factors'
    permission_codenames = ['tankhah.factor_view']
    check_organization = True
    organization_filter_field = 'tankhah__organization__id__in'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        logger.info(f"[FACTOR_LIST] شروع دریافت لیست فاکتورها برای کاربر: {user.username}")

        # کوئری پایه با بهینه‌سازی - فقط فیلدهای موجود
        qs = super().get_queryset().select_related(
            'tankhah__organization',
            'tankhah__project',
            'created_by',
            'category',
            'locked_by_stage',
            'tankhah__project_budget_allocation__budget_item' # Correct path ends here
          ).prefetch_related(
            'items',
            Prefetch(
                'approval_logs',
                queryset=ApprovalLog.objects.select_related('user', 'post').order_by('-timestamp'),
                to_attr='all_logs'  # 💡 RENAME: Fetch all logs to find the last one
            )
            # Prefetch(
            #     'approval_logs',
            #     queryset=ApprovalLog.objects.filter(
            #         action__in=['APPROVED', 'INTERMEDIATE_APPROVE', 'FINAL_APPROVE', 'APPROVE', 'TEMP_APPROVED']
            #     ).select_related('user', 'post', 'stage').order_by('-timestamp'),
            #     to_attr='approvers_raw'
            # )
        )

        initial_count = qs.count()
        logger.info(f"[FACTOR_LIST] تعداد اولیه فاکتورها: {initial_count}")

        # دریافت سازمان‌های کاربر
        user_org_ids = set()
        user_level = None

        try:
            for user_post in user.userpost_set.filter(is_active=True).select_related('post__organization'):
                org = user_post.post.organization
                user_org_ids.add(org.id)
                # اضافه کردن سازمان‌های والد
                while org.parent_organization:
                    org = org.parent_organization
                    user_org_ids.add(org.id)
                user_level = min(user_level, user_post.post.level) if user_level else user_post.post.level
        except Exception as e:
            logger.error(f"[FACTOR_LIST] خطا در دریافت سازمان‌های کاربر: {e}")
            user_org_ids = set()
            user_level = None

        logger.info(f"[FACTOR_LIST] سازمان‌های کاربر: {user_org_ids}, سطح: {user_level}")

        # اعمال فیلترها
        filter_conditions = Q()

        # فیلتر جستجو
        query = self.request.GET.get('q', '').strip()
        if query:
            filter_conditions &= (
                    Q(number__icontains=query) |
                    Q(description__icontains=query) |
                    Q(tankhah__number__icontains=query) |
                    Q(tankhah__project__name__icontains=query) |
                    Q(tankhah__organization__name__icontains=query)
            )
            logger.info(f"[FACTOR_LIST] فیلتر جستجو اعمال شد: {query}")

        # فیلتر وضعیت
        status_query = self.request.GET.get('status', '').strip()
        if status_query:
            filter_conditions &= Q(status=status_query)
            logger.info(f"[FACTOR_LIST] فیلتر وضعیت اعمال شد: {status_query}")

        # فیلتر تاریخ شمسی
        date_query = self.request.GET.get('date', '').strip()
        if date_query:
            try:
                year, month, day = map(int, date_query.split('/'))
                logger.debug(f"[FACTOR_LIST] Parsed date: {year}/{month}/{day}")
                jalali_date_obj = jdatetime.date(year, month, day)
                logger.debug(f"[FACTOR_LIST] Jalali date object: {jalali_date_obj}")
                gregorian_date_obj = jalali_date_obj.togregorian()
                logger.debug(f"[FACTOR_LIST] Gregorian date: {gregorian_date_obj}")
                filter_conditions &= Q(date=gregorian_date_obj)
                logger.info(f"[FACTOR_LIST] Date filter applied: {date_query} -> {gregorian_date_obj}")
            except Exception as e:
              logger.error(f"[FACTOR_LIST] Error processing date '{date_query}': {e}", exc_info=True)
              messages.warning(self.request, _("فرمت تاریخ نامعتبر است. لطفاً از فرمت 1403/05/15 استفاده کنید."))
            # try:
            #     # تبدیل تاریخ شمسی به میلادی
            #     if '/' in date_query:
            #         date_parts = date_query.split('/')
            #         if len(date_parts) == 3:
            #             year, month, day = map(int, date_parts)
            #             jalali_date = jdatetime.date(year, month, day)
            #             # gregorian_date = jalali_date.togregorian()
            #             gregorian_date = jalali_date.strftime("%Y:%m:%d %H:%M:%S")
            #             filter_conditions &= Q(date=gregorian_date)
            #             logger.info(f"[FACTOR_LIST] فیلتر تاریخ اعمال شد: {date_query} -> {gregorian_date}")
            #         else:
            #             raise ValueError("فرمت تاریخ نامعتبر")
            #     else:
            #         raise ValueError("فرمت تاریخ نامعتبر")
            # except (ValueError, TypeError) as e:
            #     logger.warning(f"[FACTOR_LIST] خطا در تبدیل تاریخ: {e}")
            #     messages.warning(self.request, _("فرمت تاریخ نامعتبر است. لطفاً از فرمت 1403/05/15 استفاده کنید."))

        # فیلتر محدودیت سازمانی
        if not (user.is_superuser or user.has_perm('tankhah.Tankhah_view_all')):
            if user_org_ids:
                filter_conditions &= Q(tankhah__organization__id__in=user_org_ids)
                logger.info(f"[FACTOR_LIST] محدودیت سازمانی اعمال شد")
            else:
                # اگر کاربر هیچ سازمانی ندارد، هیچ فاکتوری نمایش نده
                filter_conditions &= Q(pk__in=[])
                logger.warning(f"[FACTOR_LIST] کاربر هیچ سازمانی ندارد")

        # اعمال فیلترها
        if filter_conditions:
            qs = qs.filter(filter_conditions)
            logger.info(f"[FACTOR_LIST] پس از اعمال فیلترها: {qs.count()}")

        # مرتب‌سازی
        qs = qs.order_by('-date', '-created_at', '-pk')

        logger.info(f"[FACTOR_LIST] تعداد نهایی فاکتورها: {qs.count()}")
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        logger.info(f"[FACTOR_LIST_CONTEXT] شروع ایجاد context برای کاربر: {user.username}")

        # بررسی دسترسی‌های کاربر
        is_hq = (
                user.is_superuser or
                user.has_perm('tankhah.Tankhah_view_all') or
                user.userpost_set.filter(
                    is_active=True,
                    post__organization__org_type__fname='HQ'
                ).exists()
        )

        # دریافت اطلاعات کاربر
        user_level = None
        user_org_ids = set()

        try:
            user_posts = list(
                user.userpost_set.filter(is_active=True)
                .select_related('post__organization')
                .prefetch_related('post__stageapprover_set')
            )

            for user_post in user_posts:
                user_org_ids.add(user_post.post.organization.id)
                user_level = min(user_level, user_post.post.level) if user_level else user_post.post.level
        except Exception as e:
            logger.error(f"[FACTOR_LIST_CONTEXT] خطا در دریافت اطلاعات کاربر: {e}")

        # اضافه کردن متغیرهای context
        context.update({
            'is_hq': is_hq,
            'query': self.request.GET.get('q', ''),
            'status_query': self.request.GET.get('status', ''),
            'date_query': self.request.GET.get('date', ''),
            # 'status_choices': Factor.status.code,
            'user_level': user_level,
            'user_org_ids': user_org_ids,
        })

        # گروه‌بندی فاکتورها
        grouped_by_org = {}
        factor_list = list(context.get(self.context_object_name, []))  # تبدیل به لیست

        logger.info(f"[FACTOR_LIST_CONTEXT] پردازش {len(factor_list)} فاکتور برای گروه‌بندی")

        for factor in factor_list:
            try:
                tankhah = factor.tankhah
                if not tankhah or not tankhah.organization or not tankhah.project:
                    logger.warning(f"[FACTOR_LIST_CONTEXT] فاکتور {factor.number} فاقد تنخواه، سازمان یا پروژه")
                    continue

                org_name = tankhah.organization.name
                project_name = tankhah.project.name
                tankhah_number = tankhah.number

                # ایجاد ساختار گروه‌بندی
                if org_name not in grouped_by_org:
                    grouped_by_org[org_name] = {
                        'org_obj': tankhah.organization,
                        'projects': {},
                        'total_amount': Decimal('0'),
                        'total_factors': 0
                    }

                if project_name not in grouped_by_org[org_name]['projects']:
                    grouped_by_org[org_name]['projects'][project_name] = {
                        'project_obj': tankhah.project,
                        'tankhahs': {},
                        'total_amount': Decimal('0'),
                        'total_factors': 0
                    }

                if tankhah_number not in grouped_by_org[org_name]['projects'][project_name]['tankhahs']:
                    grouped_by_org[org_name]['projects'][project_name]['tankhahs'][tankhah_number] = {
                        'tankhah_obj': tankhah,
                        'factors': {
                            'draft': [],
                            'pending': [],
                            'pending_approval': [],
                            'partial': [],
                            'approve': [],
                            'rejected': [],
                            'paid': [],
                            'others': []
                        },
                        'total_amount': Decimal('0'),
                        'total_factors': 0
                    }

                # تعیین کلید وضعیت
                status_key = self._get_status_key(factor.status)

                # اضافه کردن فاکتور به گروه مناسب
                grouped_by_org[org_name]['projects'][project_name]['tankhahs'][tankhah_number]['factors'][
                    status_key].append(factor)

                # محاسبه مبالغ
                factor_amount = factor.amount or Decimal('0')
                grouped_by_org[org_name]['projects'][project_name]['tankhahs'][tankhah_number][
                    'total_amount'] += factor_amount
                grouped_by_org[org_name]['projects'][project_name]['tankhahs'][tankhah_number]['total_factors'] += 1
                grouped_by_org[org_name]['projects'][project_name]['total_amount'] += factor_amount
                grouped_by_org[org_name]['projects'][project_name]['total_factors'] += 1
                grouped_by_org[org_name]['total_amount'] += factor_amount
                grouped_by_org[org_name]['total_factors'] += 1

                # پردازش تأییدکنندگان
                self._process_factor_approvers(factor)

                # بررسی دسترسی‌های فاکتور
                self._check_factor_permissions(factor, user, tankhah)

                # تبدیل تاریخ به شمسی
                self._convert_dates_to_jalali(factor)

                logger.debug(
                    f"[FACTOR_LIST_CONTEXT] فاکتور {factor.number}: can_approve={getattr(factor, 'can_approve', False)}, is_locked={getattr(factor, 'is_locked', True)}")

            except Exception as e:
                logger.error(f"[FACTOR_LIST_CONTEXT] خطا در پردازش فاکتور {getattr(factor, 'pk', 'نامشخص')}: {e}",
                             exc_info=True)
                # تنظیم مقادیر پیش‌فرض در صورت خطا
                self._set_default_factor_values(factor)

        context['grouped_by_org'] = grouped_by_org

        # محاسبه آمار کلی
        total_factors = sum(org_data['total_factors'] for org_data in grouped_by_org.values())
        total_amount = sum(org_data['total_amount'] for org_data in grouped_by_org.values())

        context.update({
            'total_factors': total_factors,
            'total_amount': total_amount,
            'organizations_count': len(grouped_by_org)
        })

        logger.info(
            f"[FACTOR_LIST_CONTEXT] گروه‌بندی تکمیل شد. {len(grouped_by_org)} سازمان، {total_factors} فاکتور، مبلغ کل: {total_amount}")

        return context

    def _get_status_key(self, status):
        """تعیین کلید وضعیت برای گروه‌بندی"""
        status_mapping = {
            'DRAFT': 'draft',
            'PENDING': 'pending',
            'PENDING_APPROVAL': 'pending_approval',
            'PARTIAL': 'partial',
            'APPROVE': 'approve',
            'REJECT': 'rejected',
            'PAID': 'paid',
            'APPROVED_INTERMEDIATE': 'approve',
            'APPROVED_FINAL': 'approve',
            'TEMP_APPROVED': 'approve'
        }
        return status_mapping.get(status, 'others')

    def _process_factor_approvers(self, factor):
        """پردازش تأییدکنندگان فاکتور"""
        try:
            all_logs = getattr(factor, 'all_logs', [])
            last_log = all_logs[0] if all_logs else None

            # دستیابی به label فارسی از ACTION_TYPES
            action_label_map = dict(ACTION_TYPES)  # تبدیل به دیکشنری: {'DRAFT': 'پیش‌نویس', 'CREATE': 'ایجاد', ...}

            if last_log and last_log.user:
                factor.last_actor_name = last_log.user.get_full_name() or last_log.user.username
                factor.last_action_verb = action_label_map.get(last_log.action, 'نامشخص')
            else:
                factor.last_actor_name = 'بدون اقدام'
                factor.last_action_verb = 'بدون اقدام'

            approver_names = []
            seen_users = set()
            for log in all_logs:
                if log.action in ['APPROVE', 'APPROVED_INTERMEDIATE', 'APPROVED_FINAL',
                                  'TEMP_APPROVED'] and log.user and log.user.id not in seen_users:
                    name = log.user.get_full_name() or log.user.username
                    approver_names.append(name)
                    seen_users.add(log.user.id)

            factor.approvers_display_list = '، '.join(approver_names) if approver_names else 'بدون تأییدکننده'
            logger.debug(
                f"[FACTOR_APPROVERS] فاکتور {getattr(factor, 'number', 'نامشخص')}: {len(approver_names)} تأییدکننده")
        except Exception as e:
            logger.error(
                f"[FACTOR_APPROVERS] خطا در پردازش تأییدکنندگان فاکتور {getattr(factor, 'number', 'نامشخص')}: {e}",
                exc_info=True)
            factor.last_actor_name = 'خطا'
            factor.last_action_verb = 'خطا'
            factor.approvers_display_list = 'خطا در بارگذاری'

    def _check_factor_permissions(self, factor, user, tankhah):
        """بررسی دسترسی‌های فاکتور"""
        try:
            # دریافت مرحله فعلی
            current_stage_order = get_factor_current_stage(factor)

            # بررسی دسترسی کاربر
            access_info = check_user_factor_access(
                user.username,
                tankhah=tankhah,
                action_type='APPROVE',
                entity_type='FACTOR',
                default_stage_order=current_stage_order
            )

            # تعیین امکان تأیید
            factor.can_approve = (
                    access_info.get('has_access', False) and
                    factor.status in ['DRAFT', 'PENDING', 'PENDING_APPROVAL', 'PARTIAL'] and
                    not getattr(factor, 'locked', False) and
                    not getattr(tankhah, 'is_locked', False) and
                    not getattr(tankhah, 'is_archived', False)
            )

            # تعیین وضعیت قفل
            factor.is_locked = (
                    getattr(factor, 'locked', False) or
                    getattr(tankhah, 'is_locked', False) or
                    getattr(tankhah, 'is_archived', False) or
                    (factor.locked_by_stage and factor.locked_by_stage.order < current_stage_order)
            )

            logger.debug(
                f"[FACTOR_PERMISSIONS] فاکتور {getattr(factor, 'number', 'نامشخص')}: can_approve={factor.can_approve}, is_locked={factor.is_locked}")

        except Exception as e:
            logger.error(
                f"[FACTOR_PERMISSIONS] خطا در بررسی دسترسی‌های فاکتور {getattr(factor, 'number', 'نامشخص')}: {e}")
            factor.can_approve = False
            factor.is_locked = True


    def _set_default_factor_values(self, factor):
        """تنظیم مقادیر پیش‌فرض در صورت خطا"""
        factor.can_approve = False
        factor.is_locked = True
        factor.approvers_display = _('خطا در بارگذاری تأییدکنندگان')
        factor.last_approver = None
        factor.jalali_date = ''
        factor.jalali_created_at = ''

    def _convert_dates_to_jalali(self, factor):
        """Converts Gregorian dates to Jalali strings for display."""
        try:
            # 💡 IMPROVEMENT: Check if the date field exists and is not None
            if factor.date:
                # Use jdatetime directly as it's more reliable
                jalali_date_obj = jdatetime.date.fromgregorian(date=factor.date)
                factor.jalali_date = jalali_date_obj.strftime('%Y/%m/%d')
            else:
                # Set a default empty string if the date is None
                factor.jalali_date = ''

            if factor.created_at:
                # Ensure created_at is a datetime object before conversion
                jalali_datetime_obj = jdatetime.datetime.fromgregorian(datetime=factor.created_at)
                factor.jalali_created_at = jalali_datetime_obj.strftime('%Y/%m/%d %H:%M')
            else:
                factor.jalali_created_at = ''

        except Exception as e:
            logger.error(f"[DATE_CONVERSION_ERROR] for factor {getattr(factor, 'pk', 'N/A')}: {e}")
            # In case of any error, set default empty values to prevent template errors
            factor.jalali_date = _('خطا در تاریخ')
            factor.jalali_created_at = _('خطا در تاریخ')


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
            'tankhah__organization',
            'tankhah__project',
            'tankhah__status',  # Using tankhah__status as current_stage is deprecated
            'status',  # Also select the factor's own status
            'created_by',
            'category'
        ).prefetch_related(
            'items',
            Prefetch(
                'approval_logs',
                # ########## CRITICAL FIX ##########
                # We filter by the `code` field within the `action` ForeignKey.
                queryset=ApprovalLog.objects.filter(action__code='APPROVE').select_related('user', 'post').order_by(
                    'timestamp'),
                # ##################################
                to_attr='approvers_list'
            )
        ).order_by('-date', '-pk')

    def get_context_data(self, **kwargs):
        """آماده‌سازی داده‌ها برای تمپلیت با ساختار داده پایدار."""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        from core.models import Status  # Import Status for choices

        status_choices_queryset = Status.objects.filter(is_active=True).values_list('pk', 'name')
        context.update({
            'is_hq': self._user_is_hq(user),
            'query': self.request.GET.get('q', ''),
            'status_query': self.request.GET.get('status', ''),
            'status_choices': status_choices_queryset,  # Pass the corrected queryset of tuples
        })

        grouped_data = {}
        user_posts = list(
            user.userpost_set.filter(is_active=True).select_related('post').prefetch_related('post__stageapprover_set'))

        for factor in context['factors']:
            try:
                # To prevent errors if a related object is missing
                if not (hasattr(factor, 'tankhah') and factor.tankhah and
                        hasattr(factor.tankhah, 'organization') and factor.tankhah.organization and
                        hasattr(factor.tankhah, 'project') and factor.tankhah.project):
                    logger.warning(f"Skipping factor {factor.pk} due to missing related tankhah/org/project.")
                    continue

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
                            'pending': [], 'approve': [], 'rejecte': [],
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

