import logging
from django.db.models import Prefetch, Max
from django.views.generic import DetailView
from django.utils.translation import gettext_lazy as _
from django.http import Http404
# اطمینان از مسیر صحیح ایمپورت‌ها
from core.PermissionBase import PermissionBaseView
from tankhah.fun_can_edit_approval import can_edit_approval
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
        context = super().get_context_data(**kwargs)
        factor = self.object
        logger.info(f"Generating approval path for factor: {factor.number}")

        # محاسبه بالاترین سطح تأییدکننده
        max_approved_level = ApprovalLog.objects.filter(
            factor_id=factor.id,
            action='APPROVE',
            post__isnull=False
        ).aggregate(Max('post__level'))['post__level__max'] or 999  # 999 برای سطح پایین‌تر از همه

        # دریافت سطح کاربر فعلی
        user_level = self.request.user.userpost_set.filter(
            is_active=True, end_date__isnull=True
        ).aggregate(Max('post__level'))['post__level__max'] or 999

        # دریافت تمام مراحل فعال گردش کار
        workflow_stages = WorkflowStage.objects.filter(is_active=True).order_by('order')
        if not workflow_stages.exists():
            context['error_message'] = _("هیچ مرحله فعالی برای گردش کار یافت نشد.")
            return context

        approval_path = []
        for stage in workflow_stages:
            stage_info = {
                'stage': stage,
                'status': 'pending',
                'logs': [],
                'potential_approvers': [],
                'is_current': factor.tankhah.current_stage_id == stage.id,
                'is_final': stage.is_final_stage,
                'triggers_payment': stage.triggers_payment_order,
                'can_edit': can_edit_approval(self.request.user, factor.tankhah, stage)  # اضافه کردن وضعیت ویرایش
            }

            # لاگ‌های تأیید
            stage_logs = [
                {
                    'user': {
                        'full_name': log.user.get_full_name() or log.user.username if log.user else _('کاربر نامشخص'),
                        'username': log.user.username if log.user else _('نام کاربری نامشخص')
                    },
                    'post': {
                        'name': log.post.name if log.post else _('پست نامشخص'),
                        'organization': log.post.organization.name if log.post and log.post.organization else _('سازمان نامشخص'),
                        'level': log.post.level if log.post else 0
                    },
                    'action': log.get_action_display() or _('اقدام نامشخص'),
                    'timestamp': log.timestamp,
                    'comment': log.comment or _('بدون توضیحات'),
                } for log in ApprovalLog.objects.filter(factor_id=factor.id, stage_id=stage.id)
            ]
            stage_info['logs'] = stage_logs

            if stage_logs:
                has_approve = any(log['action'] == 'تأیید' for log in stage_logs)
                has_reject = any(log['action'] == 'رد' for log in stage_logs)
                stage_info['status'] = 'rejected' if has_reject else 'approved' if has_approve else 'pending'

            # تأییدکنندگان بالقوه (فقط اگر سطح بالاتری تأیید نکرده باشد)
            if stage_info['status'] == 'pending' and user_level >= max_approved_level:
                stage_approvers = StageApprover.objects.filter(
                    stage=stage, is_active=True
                ).select_related('post__organization').prefetch_related(
                    Prefetch('post__accessrule_set', queryset=AccessRule.objects.filter(
                        entity_type='FACTOR', action_type__in=['APPROVE', 'REJECT'], is_active=True
                    ))
                )
                for approver in stage_approvers:
                    post = approver.post
                    if post.level < max_approved_level:  # نادیده گرفتن پست‌های سطح پایین‌تر
                        continue
                    access_rules = post.accessrule_set.filter(
                        stage=stage, entity_type='FACTOR', action_type__in=['APPROVE', 'REJECT']
                    )
                    if not access_rules.exists():
                        continue
                    users_in_post = UserPost.objects.filter(
                        post=post, is_active=True, end_date__isnull=True
                    ).select_related('user')
                    if not self._user_is_hq(self.request.user):
                        users_in_post = users_in_post.filter(post__organization_id=factor.tankhah.organization_id)
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

            approval_path.append(stage_info)
            if stage_info['status'] == 'rejected':
                break

        context.update({
            'approval_path': approval_path,
            'page_title': _(f"مسیر تأیید فاکتور: {factor.number}"),
            'is_hq': self._user_is_hq(self.request.user),
            'factor_organization': factor.tankhah.organization.name if factor.tankhah.organization else _('نامشخص'),
            'factor_project': factor.tankhah.project.name if factor.tankhah.project else _('نامشخص'),
            'max_approved_level': max_approved_level,
            'user_level': user_level
        })
        return context