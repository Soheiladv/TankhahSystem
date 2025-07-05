import logging
from django.db.models import Prefetch
from django.views.generic import DetailView
from django.utils.translation import gettext_lazy as _
from django.http import Http404
# اطمینان از مسیر صحیح ایمپورت‌ها
from core.PermissionBase import PermissionBaseView
from tankhah.models import Factor, ApprovalLog, StageApprover
from core.models import WorkflowStage, UserPost, AccessRule

# تنظیم لاگ‌گیری برای ردیابی خطاها و دیباگ
logger = logging.getLogger("FactorApprovalPathView")

# تنظیم سطح لاگ‌گیری و فایل خروجی
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(name)s %(levelname)s: %(message)s',
    filename='logs/factor_approval_path.log',
    filemode='a'
)

class FactorApprovalPathView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/Factors/factor_approval_path.html'
    context_object_name = 'factor'
    permission_codenames = ['tankhah.factor_view']
    check_organization = True
    organization_filter_field = 'tankhah__organization'  # فیلد فیلتر سازمانی

    def _user_is_hq(self, user):
        """
        بررسی می‌کند که آیا کاربر دفتر مرکزی (HQ) است یا خیر.
        نتیجه در کش ذخیره می‌شود تا از محاسبات تکراری جلوگیری شود.
        """
        logger.debug(f"بررسی وضعیت HQ برای کاربر: {user.username}")
        if hasattr(user, '_is_hq_cache'):
            logger.debug(f"استفاده از وضعیت کش‌شده HQ برای کاربر '{user.username}': {user._is_hq_cache}")
            return user._is_hq_cache

        is_hq = (
            user.is_superuser or
            user.has_perm('tankhah.Tankhah_view_all') or
            user.userpost_set.filter(
                is_active=True,
                post__organization__org_type__fname='HQ'
            ).exists()
        )
        logger.debug(f"وضعیت HQ کاربر '{user.username}': {is_hq}")
        user._is_hq_cache = is_hq
        return is_hq

    def _get_organization_from_object(self, obj):
        """
        استخراج سازمان از شیء فاکتور.
        """
        try:
            if isinstance(obj, Factor):
                return obj.tankhah.organization
            return super()._get_organization_from_object(obj)
        except AttributeError as e:
            logger.error(f"خطا در استخراج سازمان از شیء {obj}: {str(e)}")
            return None

    def get_queryset(self):
        """
        آماده‌سازی کوئری بهینه برای فاکتورها با لود پیشاپیش روابط کلیدی.
        """
        logger.info(f"دریافت کوئری‌ست برای کاربر: {self.request.user.username}")
        queryset = super().get_queryset().select_related(
            'tankhah__organization',
            'tankhah__project',
            'tankhah__current_stage'
        ).prefetch_related(
            Prefetch(
                'approval_logs',
                queryset=ApprovalLog.objects.select_related(
                    'user', 'post', 'stage', 'post__organization'
                ).prefetch_related(
                    Prefetch('post__accessrule_set', queryset=AccessRule.objects.filter(
                        entity_type='FACTOR', is_active=True
                    ))
                ).order_by('timestamp'),
                to_attr='approvers_list'
            )
        )
        logger.debug(f"کوئری‌ست تولید شد: {queryset.query}")
        return queryset

    def get_object(self, queryset=None):
        """
        دریافت فاکتور با بررسی دسترسی سازمانی.
        کاربران غیر-HQ فقط به فاکتورهای سازمان خود دسترسی دارند.
        """
        if queryset is None:
            queryset = self.get_queryset()

        pk = self.kwargs.get(self.pk_url_kwarg)
        logger.info(f"دریافت فاکتور با شناسه: {pk}")
        try:
            factor = queryset.get(pk=pk)
            logger.debug(f"فاکتور یافت شد: {factor.number}, سازمان: {factor.tankhah.organization_id if factor.tankhah else 'نامشخص'}")
        except Factor.DoesNotExist:
            logger.error(f"فاکتور با شناسه {pk} یافت نشد.")
            raise Http404(_("فاکتور با شناسه داده‌شده یافت نشد."))

        # بررسی دسترسی سازمانی برای کاربران غیر-HQ
        user = self.request.user
        if not self._user_is_hq(user):
            user_organizations = user.userpost_set.filter(
                is_active=True
            ).values_list('post__organization_id', flat=True)
            logger.debug(f"سازمان‌های کاربر {user.username}: {list(user_organizations)}")
            if factor.tankhah.organization_id not in user_organizations:
                logger.warning(f"کاربر {user.username} به سازمان {factor.tankhah.organization_id} دسترسی ندارد.")
                raise Http404(_("شما به این فاکتور دسترسی ندارید."))

        return factor

    def get_context_data(self, **kwargs):
        """
        آماده‌سازی داده‌های context برای تمپلیت با تأکید بر تأییدکنندگان و جزئیات پست‌ها.
        """
        context = super().get_context_data(**kwargs)
        factor = self.object
        logger.info(f"تولید مسیر تأیید برای فاکتور: {factor.number}")

        # بررسی وجود تنخواه و مرحله فعلی
        if not factor.tankhah or not factor.tankhah.current_stage:
            logger.error(
                f"تنظیمات نامعتبر برای فاکتور {factor.number}: "
                f"tankhah={factor.tankhah}, current_stage={factor.tankhah.current_stage}"
            )
            context['error_message'] = _("تنخواه یا مرحله فعلی برای این فاکتور تعریف نشده است.")
            return context

        # دریافت تمام مراحل فعال گردش کار
        workflow_stages = WorkflowStage.objects.filter(is_active=True).order_by('order')
        logger.debug(f"تعداد مراحل فعال یافت‌شده: {workflow_stages.count()}")
        if not workflow_stages.exists():
            logger.error(f"هیچ مرحله فعالی برای فاکتور {factor.number} یافت نشد.")
            context['error_message'] = _("هیچ مرحله فعالی برای گردش کار یافت نشد.")
            return context

        # دریافت لاگ‌های تأیید مرتبط با فاکتور
        approval_logs = ApprovalLog.objects.filter(factor_id=factor.id).select_related(
            'user', 'post', 'stage', 'post__organization'
        ).order_by('timestamp')
        logger.debug(f"تعداد لاگ‌های تأیید برای فاکتور {factor.number}: {approval_logs.count()}")

        # آماده‌سازی مسیر تأیید
        approval_path = []
        for stage in workflow_stages:
            logger.debug(f"پردازش مرحله: {stage.name} (ID={stage.id}, order={stage.order})")
            stage_info = {
                'stage': stage,
                'status': 'pending',
                'logs': [],
                'potential_approvers': [],
                'is_current': factor.tankhah.current_stage_id == stage.id,
                'is_final': stage.is_final_stage,
                'triggers_payment': stage.triggers_payment_order
            }

            # فیلتر کردن لاگ‌های تأیید برای مرحله خاص
            stage_logs = [
                {
                    'user': {
                        'full_name': log.user.get_full_name() or log.user.username if log.user else _('کاربر نامشخص'),
                        'username': log.user.username if log.user else _('نام کاربری نامشخص')
                    },
                    'post': {
                        'name': log.post.name if log.post else _('پست نامشخص'),
                        'organization': log.post.organization.name if log.post and log.post.organization else _('سازمان نامشخص'),
                        'branch': log.post.get_branch_display() if log.post and log.post.branch else _('بدون شاخه'),
                        'level': log.post.level if log.post else 0,
                        'order': log.post.is_payment_order_signer if log.post else 0,
                        'max_change_level': log.post.max_change_level if log.post else 0,
                        'is_payment_signer': log.post.is_payment_order_signer if log.post else False,
                        'description': log.post.description or _('بدون توضیحات') if log.post else _('بدون توضیحات')
                    },
                    'action': log.get_action_display() or _('اقدام نامشخص'),
                    'timestamp': log.timestamp,
                    'comment': log.comment or _('بدون توضیحات'),
                    'seen_by_higher': log.seen_by_higher,
                    'seen_at': log.seen_at
                } for log in approval_logs if log.stage_id == stage.id
            ]
            stage_info['logs'] = stage_logs
            logger.debug(f"مرحله {stage.name}: {len(stage_logs)} لاگ تأیید یافت شد.")

            # تعیین وضعیت مرحله
            if stage_logs:
                has_approve = any(log['action'] == 'تأیید' for log in stage_logs)
                has_reject = any(log['action'] == 'رد' for log in stage_logs)
                stage_info['status'] = 'rejected' if has_reject else 'approved' if has_approve else 'pending'
                logger.debug(f"وضعیت مرحله {stage.name}: {stage_info['status']}")

            # دریافت تأییدکنندگان بالقوه
            if stage_info['status'] == 'pending':
                try:
                    stage_approvers = StageApprover.objects.filter(
                        stage=stage, is_active=True
                    ).select_related('post__organization').prefetch_related(
                        Prefetch('post__accessrule_set', queryset=AccessRule.objects.filter(
                            entity_type='FACTOR', action_type__in=['APPROVE', 'REJECT'], is_active=True
                        ))
                    )
                    logger.debug(f"مرحله {stage.name}: {stage_approvers.count()} تأییدکننده بالقوه یافت شد.")
                except StageApprover.DoesNotExist:
                    logger.warning(f"مدل StageApprover یافت نشد برای مرحله {stage.name}")
                    stage_approvers = []

                for approver in stage_approvers:
                    post = approver.post
                    access_rules = post.accessrule_set.filter(
                        stage=stage, entity_type='FACTOR', action_type__in=['APPROVE', 'REJECT']
                    )
                    if not access_rules.exists():
                        logger.debug(f"پست {post.name} هیچ قانون دسترسی فعالی ندارد.")
                        continue

                    users_in_post = UserPost.objects.filter(
                        post=post,
                        is_active=True,
                        end_date__isnull=True
                    ).select_related('user')
                    if not self._user_is_hq(self.request.user):
                        users_in_post = users_in_post.filter(
                            post__organization_id=factor.tankhah.organization_id
                        )
                    logger.debug(f"پست {post.name}: {users_in_post.count()} کاربر فعال یافت شد.")

                    if users_in_post.exists():
                        stage_logs = [
                            {
                                'user': {
                                    'full_name': log.user.get_full_name() or log.user.username if log.user else _(
                                        'کاربر نامشخص'),
                                    'username': log.user.username if log.user else _('نام کاربری نامشخص')
                                },
                                'post': {
                                    'name': log.post.name if log.post else _('پست نامشخص'),
                                    'organization': log.post.organization.name if log.post and log.post.organization else _(
                                        'سازمان نامشخص'),
                                    'branch': log.post.get_branch_display() if log.post and log.post.branch else _(
                                        'بدون شاخه'),
                                    'level': log.post.level if log.post else 0,
                                    'order': log.post.level if log.post else 0,  # اصلاح شده
                                    'max_change_level': log.post.max_change_level if log.post else 0,
                                    'is_payment_signer': log.post.is_payment_order_signer if log.post else False,
                                    'description': log.post.description or _('بدون توضیحات') if log.post else _(
                                        'بدون توضیحات')
                                },
                                'action': log.get_action_display() or _('اقدام نامشخص'),
                                'timestamp': log.timestamp,
                                'comment': log.comment or _('بدون توضیحات'),
                                'seen_by_higher': log.seen_by_higher,
                                'seen_at': log.seen_at
                            } for log in approval_logs if log.stage_id == stage.id
                        ]

                        # در حلقه potential_approvers:
                        stage_info['potential_approvers'].append({
                            'post': {
                                'name': post.name,
                                'organization': post.organization.name if post.organization else _('سازمان نامشخص'),
                                'branch': post.get_branch_display() if post.branch else _('بدون شاخه'),
                                'level': post.level,
                                'order': post.level,  # اصلاح شده
                                'max_change_level': post.max_change_level,
                                'is_payment_signer': post.is_payment_order_signer,
                                'description': post.description or _('بدون توضیحات')
                            },
                            'users': [{
                                'full_name': up.user.get_full_name() or up.user.username,
                                'username': up.user.username
                            } for up in users_in_post],
                            'allowed_actions': access_rules.values_list('action_type', flat=True)
                        })

                        # stage_info['potential_approvers'].append({
                        #     'post': {
                        #         'name': post.name,
                        #         'organization': post.organization.name if post.organization else _('سازمان نامشخص'),
                        #         'branch': post.get_branch_display() if post.branch else _('بدون شاخه'),
                        #         'level': post.level,
                        #         # 'order': post.order,
                        #         'max_change_level': post.max_change_level,
                        #         'is_payment_signer': post.is_payment_order_signer,
                        #         'description': post.description or _('بدون توضیحات')
                        #     },
                        #     'users': [{
                        #         'full_name': up.user.get_full_name() or up.user.username,
                        #         'username': up.user.username
                        #     } for up in users_in_post],
                        #     'allowed_actions': access_rules.values_list('action_type', flat=True)
                        # })

            approval_path.append(stage_info)
            if stage_info['status'] == 'rejected':
                logger.debug(f"مرحله {stage.name} رد شده است، توقف مسیر.")
                break

        # افزودن داده‌ها به context
        context.update({
            'approval_path': approval_path,
            'page_title': _(f"مسیر تأیید فاکتور: {factor.number}"),
            'is_hq': self._user_is_hq(self.request.user),
            'factor_organization': factor.tankhah.organization.name if factor.tankhah.organization else _('نامشخص'),
            'factor_project': factor.tankhah.project.name if factor.tankhah.project else _('نامشخص')
        })
        logger.debug(f"مسیر تأیید با {len(approval_path)} مرحله تولید شد.")
        return context

