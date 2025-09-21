import logging
from django.db.models import Prefetch, Min
from django.views.generic import DetailView
from django.utils.translation import gettext_lazy as _
from django.http import Http404
from django.db.models import Q
from tankhah.models import Factor, ApprovalLog, StageApprover
from core.models import Status, UserPost, Status
from core.PermissionBase import PermissionBaseView
from tankhah.Factor.Approved.fun_can_edit_approval import can_edit_approval

# تنظیم لاگ‌گیری برای ردیابی دقیق خطاها و دیباگ
logger = logging.getLogger("FactorApprovalPathView")

# تنظیم سطح لاگ‌گیری و فایل خروجی
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(name)s %(levelname)s: %(message)s',
    filename='logs/factor_approval_path.log',
    filemode='a'
)

class FactorApprovalPathView(PermissionBaseView, DetailView):
    """
    ویو برای نمایش مسیر تأیید فاکتور و وضعیت مراحل آن.
    کاربران با level=7 (پایین‌ترین سطح) باید بتوانند در مرحله ابتدایی (order=1) تأیید کنند و CRUD انجام دهند.
    کاربران با level=1 (مدیرعامل) فقط در مراحل بالاتر (order > 1) تأیید/رد می‌کنند.
    فقط لاگ‌های مربوط به فاکتور فعلی بررسی می‌شوند.
    """
    model = Factor
    template_name = 'tankhah/Factors/factor_approval_path.html'
    context_object_name = 'factor'
    permission_codenames = ['tankhah.factor_view']  # مجوز لازم برای مشاهده فاکتور
    check_organization = True  # بررسی دسترسی سازمانی
    organization_filter_field = 'tankhah__organization'  # فیلد فیلتر سازمانی

    def _user_is_hq(self, user):
        """
        بررسی می‌کند که آیا کاربر دفتر مرکزی (HQ) است یا خیر.
        نتیجه در کش ذخیره می‌شود تا از محاسبات تکراری جلوگیری شود.
        """
        logger.debug(f"[FactorApprovalPathView] بررسی وضعیت HQ برای کاربر: {user.username}")
        if hasattr(user, '_is_hq_cache'):
            logger.debug(f"[FactorApprovalPathView] استفاده از کش HQ برای کاربر '{user.username}': {user._is_hq_cache}")
            return user._is_hq_cache

        is_hq = (
            user.is_superuser or
            user.has_perm('tankhah.Tankhah_view_all') or
            user.userpost_set.filter(
                is_active=True,
                post__organization__org_type__fname='HQ'
            ).exists()
        )
        logger.debug(f"[FactorApprovalPathView] وضعیت HQ کاربر '{user.username}': {is_hq}")
        user._is_hq_cache = is_hq
        return is_hq

    def _get_organization_from_object(self, obj):
        """
        استخراج سازمان از شیء فاکتور برای بررسی دسترسی سازمانی.
        """
        logger.debug(f"[FactorApprovalPathView] استخراج سازمان از فاکتور {obj.number}")
        try:
            if isinstance(obj, Factor):
                return obj.tankhah.organization
            return super()._get_organization_from_object(obj)
        except AttributeError as e:
            logger.error(f"[FactorApprovalPathView] خطا در استخراج سازمان از فاکتور {obj.number}: {str(e)}")
            return None

    def get_queryset(self):
        """
        آماده‌سازی کوئری بهینه برای فاکتورها با لود پیشاپیش روابط کلیدی.
        شامل تنخواه، سازمان، پروژه، مرحله فعلی، و لاگ‌های تأیید.
        """
        logger.info(f"[FactorApprovalPathView] دریافت کوئری‌ست برای کاربر: {self.request.user.username}")
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
        logger.debug(f"[FactorApprovalPathView] کوئری‌ست تولید شد: {queryset.query}")
        return queryset

    def get_object(self, queryset=None):
        """
        دریافت فاکتور با بررسی دسترسی سازمانی.
        کاربران غیر-HQ فقط به فاکتورهای سازمان خود دسترسی دارند.
        """
        logger.info(f"[FactorApprovalPathView] دریافت فاکتور با شناسه: {self.kwargs.get(self.pk_url_kwarg)}")
        if queryset is None:
            queryset = self.get_queryset()

        pk = self.kwargs.get(self.pk_url_kwarg)
        try:
            factor = queryset.get(pk=pk)
            logger.debug(f"[FactorApprovalPathView] فاکتور یافت شد: {factor.number}, سازمان: {factor.tankhah.organization_id if factor.tankhah else 'نامشخص'}")
        except Factor.DoesNotExist:
            logger.error(f"[FactorApprovalPathView] فاکتور با شناسه {pk} یافت نشد")
            raise Http404(_("فاکتور با شناسه داده‌شده یافت نشد."))

        # بررسی دسترسی سازمانی برای کاربران غیر-HQ
        user = self.request.user
        if not self._user_is_hq(user):
            user_organizations = user.userpost_set.filter(
                is_active=True
            ).values_list('post__organization_id', flat=True)
            logger.debug(f"[FactorApprovalPathView] سازمان‌های کاربر {user.username}: {list(user_organizations)}")
            if factor.tankhah.organization_id not in user_organizations:
                logger.warning(f"[FactorApprovalPathView] کاربر {user.username} به سازمان {factor.tankhah.organization_id} دسترسی ندارد")
                raise Http404(_("شما به این فاکتور دسترسی ندارید."))

        return factor

    def get_context_data(self, **kwargs):
        """
        تولید داده‌های متنی برای نمایش مسیر تأیید فاکتور.
        شامل مراحل گردش کار، وضعیت‌ها، لاگ‌ها، و تأییدکنندگان بالقوه.
        فقط لاگ‌های مربوط به فاکتور فعلی بررسی می‌شوند.
        """
        context = super().get_context_data(**kwargs)
        factor = self.object
        tankhah = factor.tankhah
        user = self.request.user
        logger.info(f"[FactorApprovalPathView] تولید مسیر تأیید برای فاکتور: {factor.number}, تنخواه: {tankhah.number}")

        # دریافت سطح کاربر فعلی (سطح بالاتر = level کمتر)
        user_level = user.userpost_set.filter(
            is_active=True, end_date__isnull=True
        ).aggregate(Min('post__level'))['post__level__min'] or 999
        logger.debug(f"[FactorApprovalPathView] سطح کاربر {user.username}: {user_level}")

        # محاسبه پایین‌ترین سطح تأییدکننده (سطح بالاتر = level کمتر)
        max_approved_level = ApprovalLog.objects.filter(
            factor_id=factor.id,  # فقط لاگ‌های فاکتور فعلی
            action='APPROVE',
            post__isnull=False
        ).aggregate(Min('post__level'))['post__level__min'] or 999
        logger.debug(f"[FactorApprovalPathView] پایین‌ترین سطح تأیید شده (max_approved_level): {max_approved_level}")

        # بررسی لاگ‌های فاکتور برای دیباگ
        approval_logs = ApprovalLog.objects.filter(factor_id=factor.id).values(
            'stage__order', 'action', 'post__level', 'user__username', 'seen_by_higher', 'timestamp'
        )
        logger.debug(f"[FactorApprovalPathView] لاگ‌های تأیید برای فاکتور {factor.number}: {list(approval_logs)}")

        # بررسی لاگ‌های تنخواه برای دیباگ (برای اطمینان از عدم تداخل)
        tankhah_logs = ApprovalLog.objects.filter(tankhah=tankhah, factor__isnull=True).values(
            'stage__order', 'action', 'post__level', 'user__username', 'seen_by_higher', 'timestamp'
        )
        logger.debug(f"[FactorApprovalPathView] لاگ‌های تنخواه {tankhah.number} (بدون فاکتور): {list(tankhah_logs)}")

        # دریافت تمام مراحل فعال گردش کار
        workflow_stages = WorkflowStage.objects.filter(
            is_active=True, entity_type='FACTOR'
        ).order_by('order')
        if not workflow_stages.exists():
            logger.error(f"[FactorApprovalPathView] هیچ مرحله فعالی برای گردش کار فاکتور یافت نشد")
            context['error_message'] = _("هیچ مرحله فعالی برای گردش کار یافت نشد.")
            return context

        approval_path = []
        for stage in workflow_stages:
            logger.debug(f"[FactorApprovalPathView] پردازش مرحله: {stage.name} (order={stage.order})")
            stage_info = {
                'stage': stage,
                'status': 'pending',
                'logs': [],
                'potential_approvers': [],
                'is_current': tankhah.current_stage_id == stage.id,
                'is_final': stage.is_final_stage,
                'triggers_payment': stage.triggers_payment_order,
                'can_edit': can_edit_approval(user, tankhah, stage, factor=factor)  # ارسال فاکتور به تابع
            }

            # لاگ‌های تأیید برای این مرحله (فقط فاکتور فعلی)
            stage_logs = [
                {
                    'user': {
                        'full_name': log.user.get_full_name() or log.user.username if log.user else _('کاربر نامشخص'),
                        'username': log.user.username if log.user else _('نام کاربری نامشخص')
                    },
                    'post': {
                        'name': log.post.name if log.post else _('پست نامشخص'),
                        'organization': log.post.organization.name if log.post and log.post.organization else _('سازمان نامشخص'),
                        'level': log.post.level if log.post else 999
                    },
                    'action': log.get_action_display() or _('اقدام نامشخص'),
                    'timestamp': log.timestamp,
                    'comment': log.comment or _('بدون توضیحات'),
                } for log in ApprovalLog.objects.filter(factor_id=factor.id, stage_id=stage.id)
            ]
            stage_info['logs'] = stage_logs
            logger.debug(f"[FactorApprovalPathView] لاگ‌های مرحله {stage.name}: {len(stage_logs)} لاگ یافت شد")

            # تعیین وضعیت مرحله
            if stage_logs:
                has_approve = any(log['action'] == 'تأیید' for log in stage_logs)
                has_reject = any(log['action'] == 'رد' for log in stage_logs)
                stage_info['status'] = 'rejected' if has_reject else 'approved' if has_approve else 'pending'
                logger.debug(f"[FactorApprovalPathView] وضعیت مرحله {stage.name}: {stage_info['status']}")

            # تأییدکنندگان بالقوه (فقط برای مرحله ابتدایی یا اگر سطح کاربر کافی باشد)
            if stage_info['status'] == 'pending' and (stage.order == 1 or user_level <= max_approved_level):
                logger.debug(f"[FactorApprovalPathView] محاسبه تأییدکنندگان بالقوه برای مرحله {stage.name}")
                stage_approvers = StageApprover.objects.filter(
                    stage=stage, is_active=True
                ).select_related('post__organization').prefetch_related(
                    Prefetch('post__accessrule_set', queryset=AccessRule.objects.filter(
                        entity_type='FACTOR', action_type__in=['APPROVE', 'REJECT'], is_active=True
                    ))
                )
                for approver in stage_approvers:
                    post = approver.post
                    # فقط پست‌هایی که سطح برابر یا بالاتر (level کمتر) از max_approved_level دارند
                    if post.level > max_approved_level:
                        logger.debug(f"[FactorApprovalPathView] پست {post.name} (level={post.level}) نادیده گرفته شد، زیرا پایین‌تر از max_approved_level={max_approved_level}")
                        continue
                    access_rules = post.accessrule_set.filter(
                        stage=stage, entity_type='FACTOR', action_type__in=['APPROVE', 'REJECT']
                    )
                    if not access_rules.exists():
                        logger.debug(f"[FactorApprovalPathView] پست {post.name} هیچ قانون دسترسی فعالی برای مرحله {stage.name} ندارد")
                        continue
                    users_in_post = UserPost.objects.filter(
                        post=post, is_active=True, end_date__isnull=True
                    ).select_related('user')
                    if not self._user_is_hq(user):
                        users_in_post = users_in_post.filter(post__organization_id=tankhah.organization_id)
                    if users_in_post.exists():
                        stage_info['potential_approvers'].append({
                            'post': {
                                'name': post.name,
                                'organization': post.organization.name if post.organization else _('سازمان نامشخص'),
                                'level': post.level
                            },
                            'users': [{
                                'full_name': up.user.get_full_name() or up.user.username,
                                'username': up.user.username
                            } for up in users_in_post],
                            'allowed_actions': access_rules.values_list('action_type', flat=True)
                        })
                        logger.debug(f"[FactorApprovalPathView] تأییدکننده بالقوه برای پست {post.name} به مرحله {stage.name} اضافه شد")

            approval_path.append(stage_info)
            if stage_info['status'] == 'rejected':
                logger.info(f"[FactorApprovalPathView] مرحله {stage.name} رد شده است، پایان مسیر تأیید")
                break

        # بررسی دسترسی کلی برای ویرایش در مرحله فعلی
        can_edit_current = can_edit_approval(user, tankhah, tankhah.current_stage, factor=factor)
        has_previous_action = False
        logger.info(f'factor.id is {factor.id}')
        if tankhah.current_stage.order > 1:  # فقط برای مراحل غیرابتدایی
            has_previous_action = ApprovalLog.objects.filter(
                factor_id=factor.id,  # فقط فاکتور فعلی
                stage__order__lt=tankhah.current_stage.order,
                action__in=['APPROVE', 'REJECT'],
                seen_by_higher=True
            ).exists()
        logger.debug(f"[FactorApprovalPathView] دسترسی ویرایش در مرحله فعلی: can_edit={can_edit_current}, has_previous_action={has_previous_action}")

        context.update({
            'approval_path': approval_path,
            'page_title': _(f"مسیر تأیید فاکتور: {factor.number}"),
            'is_hq': self._user_is_hq(user),
            'factor_organization': tankhah.organization.name if tankhah.organization else _('نامشخص'),
            'factor_project': tankhah.project.name if tankhah.project else _('نامشخص'),
            'max_approved_level': max_approved_level,
            'user_level': user_level,
            'can_edit_current': can_edit_current and not has_previous_action,
            'has_previous_action': has_previous_action
        })
        logger.info(f"[FactorApprovalPathView] داده‌های متنی برای فاکتور {factor.number} تولید شد")
        return context