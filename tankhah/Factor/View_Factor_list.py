import jdatetime

from accounts.AccessRule.check_user_access import check_user_factor_access
from core.models import PostAction, Status
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

# ============grok =============================================================
class  FactorListView(PermissionBaseView, ListView):
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

        # بررسی دسترسی کامل
        has_full_access = (
                user.is_superuser or
                user.userpost_set.filter(is_active=True, post__organization__org_type__fname='HQ').exists()
        )

        if has_full_access:
            logger.info(f"[FACTOR_LIST] کاربر {user.username} دسترسی کامل دارد. دریافت همه فاکتورها.")
            qs = Factor.objects.all()
        else:
            logger.info(f"[FACTOR_LIST] کاربر {user.username} دسترسی محدود دارد. اعمال فیلتر سازمانی.")
            qs = super().get_queryset()

        # بهینه‌سازی پرس‌وجو
        qs = qs.select_related(
            'tankhah__organization',
            'tankhah__project',
            'created_by',
            'category',
            'locked_by_stage',
            'tankhah__project_budget_allocation__budget_item'
        ).prefetch_related(
            'items',
            Prefetch(
                'approval_logs',
                queryset=ApprovalLog.objects.select_related('user', 'post').order_by('-timestamp'),
                to_attr='all_logs'
            )
        )

        initial_count = qs.count()
        logger.info(f"[FACTOR_LIST] تعداد اولیه فاکتورها: {initial_count}")

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
            filter_conditions &= Q(status__code=status_query)
            logger.info(f"[FACTOR_LIST] فیلتر وضعیت اعمال شد: {status_query}")

        # فیلتر تاریخ
        date_query = self.request.GET.get('date', '').strip()
        if date_query:
            try:
                year, month, day = map(int, date_query.split('/'))
                jalali_date_obj = jdatetime.date(year, month, day)
                gregorian_date_obj = jalali_date_obj.togregorian()
                filter_conditions &= Q(date=gregorian_date_obj)
                logger.info(f"[FACTOR_LIST] فیلتر تاریخ اعمال شد: {date_query} -> {gregorian_date_obj}")
            except (ValueError, TypeError) as e:
                logger.error(f"[FACTOR_LIST] خطا در پردازش تاریخ '{date_query}': {e}", exc_info=True)
                messages.warning(self.request, _("فرمت تاریخ نامعتبر است. لطفاً از فرمت 1403/05/15 استفاده کنید."))

        if filter_conditions:
            qs = qs.filter(filter_conditions)
            logger.info(f"[FACTOR_LIST] تعداد فاکتورها پس از فیلتر: {qs.count()}")

        # فیلتر فاکتورهای نهایی
        active_view = self.request.GET.get('view', 'all')
        if active_view == 'final':
            final_status_ids = list(
                Status.objects.filter(is_final_approve=True, is_active=True).values_list('id', flat=True)
            )
            if not final_status_ids:
                logger.warning("[FACTOR_LIST] هیچ وضعیت نهایی فعالی یافت نشد.")
            qs = qs.filter(status_id__in=final_status_ids)
            logger.info(f"[FACTOR_LIST] نمایش فقط فاکتورهای نهایی: {qs.count()}")

        return qs.order_by('-date', '-created_at', '-pk')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        logger.info(f"[FACTOR_LIST_CONTEXT] شروع ایجاد context برای کاربر: {user.username}")

        # بررسی دسترسی HQ
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
            user_posts = user.userpost_set.filter(is_active=True).select_related('post__organization')
            for user_post in user_posts:
                user_org_ids.add(user_post.post.organization.id)
                user_level = min(user_level, user_post.post.level) if user_level else user_post.post.level
        except Exception as e:
            logger.error(f"[FACTOR_LIST_CONTEXT] خطا در دریافت اطلاعات کاربر: {e}", exc_info=True)

        # گروه‌بندی فاکتورها
        grouped_by_org = {}
        final_factors_grouped = {}
        final_factors_stats = {'count': 0, 'total_amount': Decimal('0')}
        factor_list = list(context.get(self.context_object_name, []))
        final_status_ids = list(
            Status.objects.filter(is_final_approve=True, is_active=True).values_list('id', flat=True)
        )

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

                # گروه‌بندی همه فاکتورها
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
                        'factors': [],
                        'total_amount': Decimal('0'),
                        'total_factors': 0
                    }

                grouped_by_org[org_name]['projects'][project_name]['tankhahs'][tankhah_number]['factors'].append(factor)
                factor_amount = factor.amount or Decimal('0')
                grouped_by_org[org_name]['projects'][project_name]['tankhahs'][tankhah_number][
                    'total_amount'] += factor_amount
                grouped_by_org[org_name]['projects'][project_name]['tankhahs'][tankhah_number]['total_factors'] += 1
                grouped_by_org[org_name]['projects'][project_name]['total_amount'] += factor_amount
                grouped_by_org[org_name]['projects'][project_name]['total_factors'] += 1
                grouped_by_org[org_name]['total_amount'] += factor_amount
                grouped_by_org[org_name]['total_factors'] += 1

                context['status_choices'] = [
                    (status.code, status.name) for status in Status.objects.filter(is_active=True)
                ]

                # گروه‌بندی فاکتورهای نهایی
                if factor.status_id in final_status_ids:
                    final_factors_stats['count'] += 1
                    final_factors_stats['total_amount'] += factor_amount

                    if org_name not in final_factors_grouped:
                        final_factors_grouped[org_name] = {
                            'org_obj': tankhah.organization,
                            'projects': {},
                            'total_amount': Decimal('0'),
                            'total_factors': 0
                        }
                    if project_name not in final_factors_grouped[org_name]['projects']:
                        final_factors_grouped[org_name]['projects'][project_name] = {
                            'project_obj': tankhah.project,
                            'tankhahs': {},
                            'total_amount': Decimal('0'),
                            'total_factors': 0
                        }
                    if tankhah_number not in final_factors_grouped[org_name]['projects'][project_name]['tankhahs']:
                        final_factors_grouped[org_name]['projects'][project_name]['tankhahs'][tankhah_number] = {
                            'tankhah_obj': tankhah,
                            'factors': [],
                            'total_amount': Decimal('0'),
                            'total_factors': 0
                        }

                    final_factors_grouped[org_name]['projects'][project_name]['tankhahs'][tankhah_number][
                        'factors'].append(factor)
                    final_factors_grouped[org_name]['projects'][project_name]['tankhahs'][tankhah_number][
                        'total_amount'] += factor_amount
                    final_factors_grouped[org_name]['projects'][project_name]['tankhahs'][tankhah_number][
                        'total_factors'] += 1
                    final_factors_grouped[org_name]['projects'][project_name]['total_amount'] += factor_amount
                    final_factors_grouped[org_name]['projects'][project_name]['total_factors'] += 1
                    final_factors_grouped[org_name]['total_amount'] += factor_amount
                    final_factors_grouped[org_name]['total_factors'] += 1

                self._process_factor_approvers(factor)
                self._check_factor_permissions(factor, user, tankhah)
                self._convert_dates_to_jalali(factor)

                payee = getattr(factor, 'payee', None)
                if payee:
                    factor.payee_info = {
                        'entity_type': payee.get_entity_type_display(),
                        'name': f"{payee.name or payee.legal_name} {payee.family or ''}".strip(),
                        'national_id': payee.national_id,
                        'payee_type': payee.get_payee_type_display(),
                        'created_by': payee.created_by.get_full_name() if payee.created_by else 'نامشخص',
                    }
                else:
                    factor.payee_info = {
                        'entity_type': 'نامشخص',
                        'name': 'نامشخص',
                        'national_id': '',
                        'payee_type': 'نامشخص',
                        'created_by': 'نامشخص',
                    }
            except Exception as e:
                logger.error(f"[FACTOR_LIST_CONTEXT] خطا در پردازش فاکتور {getattr(factor, 'number', 'نامشخص')}: {e}",
                             exc_info=True)
                self._set_default_factor_values(factor)

            # sss= Status.objects.filter(is_active=True).values('code', 'name')
            # logger.info(f'Status Visuible : is ',sss )

        context.update({
            'is_hq': is_hq,
            'query': self.request.GET.get('q', ''),
            'status_query': self.request.GET.get('status', ''),
            'date_query': self.request.GET.get('date', ''),
            'user_level': user_level,
            'user_org_ids': user_org_ids,
            'grouped_by_org': grouped_by_org,
            'final_factors_grouped': final_factors_grouped,
            'final_factors_stats': final_factors_stats,
            # 'status_choices': Status.objects.filter(is_active=True).values('code', 'name'),
            'active_view': self.request.GET.get('view', 'all'),
            'total_factors': sum(org_data['total_factors'] for org_data in grouped_by_org.values()),
            'total_amount': sum(org_data['total_amount'] for org_data in grouped_by_org.values()),
            'organizations_count': len(grouped_by_org)
        })

        logger.info(
            f"[FACTOR_LIST_CONTEXT] گروه‌بندی تکمیل شد. {len(grouped_by_org)} سازمان، {context['total_factors']} فاکتور، مبلغ کل: {context['total_amount']}")
        return context

    def _get_status_key(self, status):
        status_mapping = {
            'DRAFT': 'draft',
            'PENDING': 'pending',
            'PENDING_APPROVAL': 'pending_approval',
            'PARTIAL': 'partial',
            'APPROVE': 'approve',
            'REJECTED': 'rejected',
            'PAID': 'paid',
            'APPROVED_INTERMEDIATE': 'approve',
            'APPROVED_FINAL': 'approve',
            'TEMP_APPROVED': 'approve'
        }
        return status_mapping.get(status, 'others')

    def _process_factor_approvers(self, factor):
        try:
            all_logs = getattr(factor, 'all_logs', [])
            last_log = all_logs[0] if all_logs else None

            action_label_map = dict(ACTION_TYPES)  # فرض می‌کنیم ACTION_TYPES در تنظیمات تعریف شده است

            if last_log and last_log.user:
                factor.last_actor_name = last_log.user.get_full_name() or last_log.user.username
                factor.last_action_verb = action_label_map.get(last_log.action, 'نامشخص')
            else:
                factor.last_actor_name = 'بدون اقدام'
                factor.last_action_verb = 'بدون اقدام'

            approver_names = []
            seen_users = set()
            for log in all_logs:
                if log.action in ['APPROVE', 'APPROVED_INTERMEDIATE', 'APPROVED_FINAL', 'TEMP_APPROVED'] and log.user and log.user.id not in seen_users:
                    name = log.user.get_full_name() or log.user.username
                    approver_names.append(name)
                    seen_users.add(log.user.id)

            factor.approvers_display_list = '، '.join(approver_names) if approver_names else 'بدون تأییدکننده'
            logger.debug(f"[FACTOR_APPROVERS] فاکتور {getattr(factor, 'number', 'نامشخص')}: {len(approver_names)} تأییدکننده")
        except Exception as e:
            logger.error(f"[FACTOR_APPROVERS] خطا در پردازش تأییدکنندگان فاکتور {getattr(factor, 'number', 'نامشخص')}: {e}", exc_info=True)
            factor.last_actor_name = 'خطا'
            factor.last_action_verb = 'خطا'
            factor.approvers_display_list = 'خطا در بارگذاری'

    def _check_factor_permissions(self, factor, user, tankhah):
        try:
            current_stage_order = get_factor_current_stage(factor)
            if hasattr(current_stage_order, 'stage_order'):
                current_stage_order = current_stage_order.stage_order

            access_info = check_user_factor_access(
                user.username,
                tankhah=tankhah,
                action_type='APPROVE',
                entity_type='FACTOR',
                default_stage_order=current_stage_order
            )

            factor.can_approve = (
                access_info.get('has_access', False) and
                factor.status in ['DRAFT', 'PENDING', 'PENDING_APPROVAL', 'PARTIAL'] and
                not getattr(factor, 'locked', False) and
                not getattr(tankhah, 'is_locked', False) and
                not getattr(tankhah, 'is_archived', False)
            )

            factor.is_locked = (
                getattr(factor, 'locked', False) or
                getattr(tankhah, 'is_locked', False) or
                getattr(tankhah, 'is_archived', False) or
                (factor.locked_by_stage and factor.locked_by_stage.order < current_stage_order)
            )

            logger.debug(f"[FACTOR_PERMISSIONS] فاکتور {getattr(factor, 'number', 'نامشخص')}: can_approve={factor.can_approve}, is_locked={factor.is_locked}")
        except Exception as e:
            logger.error(f"[FACTOR_PERMISSIONS] خطا در بررسی دسترسی‌های فاکتور {getattr(factor, 'number', 'نامشخص')}: {e}")
            factor.can_approve = False
            factor.is_locked = True

    def _set_default_factor_values(self, factor):
        factor.can_approve = False
        factor.is_locked = True
        factor.approvers_display_list = _('خطا در بارگذاری تأییدکنندگان')
        factor.last_actor_name = 'خطا'
        factor.last_action_verb = 'خطا'
        factor.jalali_date = ''
        factor.jalali_created_at = ''

    def _convert_dates_to_jalali(self, factor):
        try:
            if factor.date:
                jalali_date_obj = jdatetime.date.fromgregorian(date=factor.date)
                factor.jalali_date = jalali_date_obj.strftime('%Y/%m/%d')
            else:
                factor.jalali_date = ''

            if factor.created_at:
                jalali_datetime_obj = jdatetime.datetime.fromgregorian(datetime=factor.created_at)
                factor.jalali_created_at = jalali_datetime_obj.strftime('%Y/%m/%d %H:%M')
            else:
                factor.jalali_created_at = ''
        except Exception as e:
            logger.error(f"[DATE_CONVERSION_ERROR] for factor {getattr(factor, 'pk', 'N/A')}: {e}")
            factor.jalali_date = _('خطا در تاریخ')
            factor.jalali_created_at = _('خطا در تاریخ')
# =========================================================================
class FactorListView2(PermissionBaseView, ListView):
    model               = Factor
    template_name       = 'tankhah/Factors/factor_list_final.html'
    context_object_name = 'factors'
    paginate_by         = 20
    permission_codenames = ['tankhah.factor_view']

    def _user_is_hq(self, user):
        if user.is_superuser or user.has_perm('tankhah.Tankhah_view_all'):
            return True
        return user.userpost_set.filter(
            is_active=True,
            post__organization__org_type__fname='HQ'
        ).exists()

    def get_queryset(self):
        user = self.request.user

        qs = Factor.objects.all() if self._user_is_hq(user) else (
            Factor.objects.filter(
                tankhah__organization__id__in=user.userpost_set.filter(
                    is_active=True).values_list('post__organization_id', flat=True))
        )

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

    def get_context_data(self, **kwargs):
        ctx   = super().get_context_data(**kwargs)
        user  = self.request.user
        qs    = ctx[self.context_object_name]

        for f in qs:
            raw_logs = getattr(f, 'approvers_raw', [])
            logger.debug(
                "[APPROVER] Factor %s ⇒ %d logs",
                f.pk, len(raw_logs)
            )
            names = []
            for log in raw_logs:
                logger.debug(
                    "[APPROVER]  • log #%s | action=%s | user=%s",
                    log.pk, log.action, getattr(log.user, 'username', None)
                )
                if log.user:
                    names.append(log.user.get_full_name() or log.user.username)

            f.approvers_display = ', '.join(names) if names else _('بدون تأییدکننده')
            f.last_approver = names[0] if names else None

            names = [log.user.get_full_name() or log.user.username
                     for log in getattr(f, 'approvers_raw', []) if log.user]
            f.approvers_display = ', '.join(names) if names else _('بدون تأییدکننده')
            f.last_approver     = names[0] if names else None

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

        ctx.update({
            'is_hq'        : self._user_is_hq(user),
            'query'        : self.request.GET.get('q', ''),
            'status_query' : self.request.GET.get('status', ''),
            'status_choices': Factor.STATUS_CHOICES,
            'grouped_data' : grouped,
        })
        return ctx
# =========================================================================

