import logging

from budgets.budget_calculations import get_project_total_budget, get_subproject_remaining_budget
from core.PermissionBase import PermissionBaseView
from tankhah.models import Factor, FactorItem, ApprovalLog, StageApprover, FactorDocument

logger = logging.getLogger(__name__)
# - New
from django.views.generic import ListView
from django.db.models import Q, Prefetch, Count, Sum
from django.db.models.functions import Coalesce
from django.views.generic import DetailView  # یا View سفارشی
from django.utils.translation import gettext_lazy as _
from django.shortcuts import Http404
from decimal import Decimal

from core.models import WorkflowStage, UserPost, Organization
from budgets.budget_calculations import get_tankhah_remaining_budget, get_project_remaining_budget  # و سایر توابع

class FactorStatusReviewView(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tankhah/Reports/factor_status_review_final.html'  # نام تمپلیت جدید
    context_object_name = 'factors_data'
    paginate_by = 10  # کاهش برای خوانایی بهتر با جزئیات بیشتر
    permission_codenames = ['tankhah.factor_view']
    check_organization = True
    permission_denied_message = _('متاسفانه دسترسی لازم برای مشاهده این گزارش را ندارید.')

    def get_queryset(self):
        user = self.request.user
        queryset = Factor.objects.select_related(
            'tankhah', 'tankhah__organization', 'tankhah__project', 'tankhah__current_stage',
            'category', 'created_by'
        ).prefetch_related(
            Prefetch('items', queryset=FactorItem.objects.order_by('pk')),
            Prefetch('approval_logs', queryset=ApprovalLog.objects.select_related('user', 'post', 'post__organization',
                                                                                  'stage').order_by('timestamp'))
            # اضافه کردن post__organization
        ).annotate(
            total_items=Count('items'),
            approved_items_count=Count('items', filter=Q(items__status='APPROVED')),
            rejected_items_count=Count('items', filter=Q(items__status='REJECTED')),
            pending_items_count=Count('items', filter=Q(items__status='PENDING')),
        )

        # ... (بخش فیلترها و جستجو بدون تغییر زیاد، فقط مطمئن شوید که کار می‌کنند) ...
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(number__icontains=search_query) |
                Q(tankhah__number__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(items__description__icontains=search_query)
            ).distinct()

        status_filter = self.request.GET.get('status', '')
        if status_filter and status_filter in [choice[0] for choice in Factor.STATUS_CHOICES]:
            queryset = queryset.filter(status=status_filter)

        organization_filter_id = self.request.GET.get('organization_id')
        if organization_filter_id:
            queryset = queryset.filter(tankhah__organization__id=organization_filter_id)

        project_filter_id = self.request.GET.get('project_id')
        if project_filter_id:
            queryset = queryset.filter(tankhah__project__id=project_filter_id)

        return queryset.order_by('-created_at')

    def get_approver_posts_for_stage(self, stage, entity_type='FACTOR'):
        # ... (بدون تغییر از مثال قبلی، فقط مطمئن شوید post__organization را prefetch/select_related کرده‌اید اگر لازم است) ...
        if not stage:
            return []
        return StageApprover.objects.filter(stage=stage, is_active=True) \
            .select_related('post', 'post__organization')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factors_with_details = []
        user = self.request.user  # برای استفاده در محاسبات بودجه اگر نیاز به فیلتر کاربر باشد

        for factor_item_data in context['object_list']:  # factor_item_data اینجا همان factor است
            factor = factor_item_data  # برای خوانایی بهتر
            previous_actions = []
            for log in factor.approval_logs.all():
                # برای رنگ‌بندی، می‌توانیم یک کلاس CSS بر اساس نوع پست یا سازمان پست تعریف کنیم
                post_branch_class = ''
                if log.post:
                    # مثال: اگر پست شاخه 'FIN' (مالی) دارد، کلاس خاصی بدهیم
                    if log.post.branch == 'FIN':
                        post_branch_class = 'post-branch-finance'
                    elif log.post.branch == 'CEO':
                        post_branch_class = 'post-branch-ceo'
                    # ... سایر شاخه‌ها ...
                    elif log.post.organization and log.post.organization.is_core:
                        post_branch_class = 'post-branch-hq'  # پست دفتر مرکزی

                previous_actions.append({
                    'post_name': log.post.name if log.post else _("نامشخص"),
                    'post_org_name': log.post.organization.name if log.post and log.post.organization else _("نامشخص"),
                    'user_name': log.user.get_full_name() or log.user.username if log.user else _("سیستم"),
                    'action': log.get_action_display(),
                    'timestamp': log.timestamp,
                    'comment': log.comment,
                    'stage_name': log.stage.name if log.stage else _("نامشخص"),
                    'post_branch_class': post_branch_class,  # کلاس برای رنگ‌بندی
                })

            next_possible_approvers = []
            # ... (بخش next_possible_approvers بدون تغییر زیاد) ...
            if factor.tankhah and factor.tankhah.current_stage and not factor.is_locked and factor.status not in [
                'PAID', 'REJECTED']:
                approver_posts = self.get_approver_posts_for_stage(factor.tankhah.current_stage, entity_type='FACTOR')
                if not approver_posts: approver_posts = self.get_approver_posts_for_stage(factor.tankhah.current_stage,
                                                                                          entity_type='TANKHAH')
                for sa in approver_posts:
                    next_possible_approvers.append({
                        'post_name': sa.post.name,
                        'organization_name': sa.post.organization.name,
                    })

            # محاسبه مانده بودجه‌ها
            tankhah_remaining_budget_after_this_factor = Decimal('0')
            project_remaining_budget_after_this_factor = Decimal('0')
            factor_budget_impact_message = ""

            if factor.tankhah:
                # مانده تنخواه *قبل* از کسر این فاکتور (اگر پرداخت نشده)
                # این محاسبه ممکن است نیاز به دقت بیشتری داشته باشد که آیا این فاکتور قبلا از بودجه تنخواه کم شده یا نه
                # فرض می‌کنیم get_tankhah_remaining_budget مبلغ قابل خرج را برمی‌گرداند
                current_tankhah_remaining = get_tankhah_remaining_budget(factor.tankhah)
                if factor.status != 'PAID' and factor.status != 'REJECTED':  # اگر فاکتور هنوز پرداخت یا رد نشده
                    tankhah_remaining_budget_after_this_factor = current_tankhah_remaining - factor.amount
                else:  # اگر پرداخت یا رد شده، تاثیرش قبلا لحاظ شده
                    tankhah_remaining_budget_after_this_factor = current_tankhah_remaining

                if factor.tankhah.project:
                    # مانده پروژه *قبل* از کسر این فاکتور (اگر پرداخت نشده)
                    current_project_remaining = get_project_remaining_budget(factor.tankhah.project)
                    if factor.status != 'PAID' and factor.status != 'REJECTED':
                        project_remaining_budget_after_this_factor = current_project_remaining - factor.amount
                    else:
                        project_remaining_budget_after_this_factor = current_project_remaining

            if factor.status not in ['PAID', 'REJECTED'] and factor.amount > current_tankhah_remaining:
                factor_budget_impact_message = _("هشدار: مبلغ این فاکتور از مانده تنخواه بیشتر است!")
            elif factor.status not in ['PAID',
                                       'REJECTED'] and factor.tankhah and factor.tankhah.project and factor.amount > current_project_remaining:
                factor_budget_impact_message = _("هشدار: مبلغ این فاکتور از مانده مرکز هزینه (پروژه) بیشتر است!")

            factors_with_details.append({
                'factor': factor,
                'previous_actions': previous_actions,
                'next_possible_approvers': next_possible_approvers,
                'item_statuses_summary': {  # اینها از annotate می‌آیند
                    'total': factor.total_items,
                    'approved': factor.approved_items_count,
                    'rejected': factor.rejected_items_count,
                    'pending': factor.pending_items_count,
                },
                'current_tankhah_stage_name': factor.tankhah.current_stage.name if factor.tankhah and factor.tankhah.current_stage else _(
                    "نامشخص"),
                'tankhah_name': factor.tankhah.organization.name if factor.tankhah and factor.tankhah.organization else _(
                    "نامشخص"),  # نام سازمان تنخواه
                'project_name': factor.tankhah.project.name if factor.tankhah and factor.tankhah.project else _(
                    "بدون مرکز هزینه"),  # نام پروژه
                'tankhah_remaining_after_factor': tankhah_remaining_budget_after_this_factor,
                'project_remaining_after_factor': project_remaining_budget_after_this_factor,
                'factor_budget_impact_message': factor_budget_impact_message,
            })

        context['factors_data'] = factors_with_details
        context['title'] = _('بررسی و پیگیری هوشمند وضعیت فاکتورها')
        context['factor_status_choices'] = Factor.STATUS_CHOICES
        from core.models import Organization, Project
        context['organizations_for_filter'] = Organization.objects.filter(is_active=True).order_by('name')
        context['projects_for_filter'] = Project.objects.filter(is_active=True).order_by('name')
        context['current_search'] = self.request.GET.get('search', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_organization_id'] = self.request.GET.get('organization_id', '')
        context['current_project_id'] = self.request.GET.get('project_id', '')

        return context
class AdvancedFactorStatusReviewView(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tankhah/Reports/factor_status_review_final_v2.html'  # نام تمپلیت جدید
    context_object_name = 'factors_data_list'
    paginate_by = 10
    permission_codenames = ['tankhah.factor_view']
    check_organization = True  # این توسط PermissionBaseView شما هندل می‌شود
    permission_denied_message = _('متاسفانه دسترسی لازم برای مشاهده این گزارش را ندارید.')

    def get_queryset(self):
        user = self.request.user
        queryset = Factor.objects.select_related(
            'tankhah', 'tankhah__organization', 'tankhah__project', 'tankhah__current_stage',
            'tankhah__budget_allocation',  # برای دسترسی به budget_item از طریق budget_allocation تنخواه
            'tankhah__budget_allocation__budget_item',
            # فرض بر اینکه BudgetItem از طریق BudgetAllocation تنخواه قابل دسترسی است
            'category', 'created_by'
        ).prefetch_related(
            Prefetch('items', queryset=FactorItem.objects.order_by('pk')),
            Prefetch('approval_logs',
                     queryset=ApprovalLog.objects.select_related(
                         'user', 'post', 'post__organization', 'post__parent', 'stage'
                     ).order_by('timestamp'))
        ).annotate(
            total_items=Count('items'),
            approved_items_count=Count('items', filter=Q(items__status='APPROVED')),
            rejected_items_count=Count('items', filter=Q(items__status='REJECTED')),
            pending_items_count=Count('items', filter=Q(items__status='PENDING')),
        )

        # فیلتر پیش‌فرض: عدم نمایش آرشیو شده‌ها و قفل شده‌ها
        show_archived = self.request.GET.get('show_archived', 'false').lower() == 'true'
        show_locked = self.request.GET.get('show_locked', 'false').lower() == 'true'

        if not show_archived:
            # فرض: فاکتورها مستقیما فیلد is_archived ندارند، بلکه تنخواه آنها دارد
            queryset = queryset.filter(tankhah__is_archived=False)
        if not show_locked:
            queryset = queryset.filter(is_locked=False)  # فیلد is_locked خود فاکتور

        # فیلتر سازمانی (توسط PermissionBaseView شما هندل می‌شود اگر check_organization=True)
        # اگر می‌خواهید اینجا هم اعمال کنید:
        # if not user.is_superuser and not user.has_perm('CAN_VIEW_ALL_FACTOR_REPORTS'): # یک پرمیشن فرضی
        #     user_org_pks = # ... منطق شما برای گرفتن سازمان‌های کاربر ...
        #     queryset = queryset.filter(tankhah__organization__pk__in=user_org_pks)

        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(number__icontains=search_query) | Q(tankhah__number__icontains=search_query) |
                Q(description__icontains=search_query) | Q(items__description__icontains=search_query)
            ).distinct()

        status_filter = self.request.GET.get('status', '')
        if status_filter and status_filter in [choice[0] for choice in Factor.STATUS_CHOICES]:
            queryset = queryset.filter(status=status_filter)

        self.organization_filter_id = self.request.GET.get('organization_id')  # ذخیره برای استفاده در get_context_data
        if self.organization_filter_id:
            queryset = queryset.filter(tankhah__organization__id=self.organization_filter_id)

        project_filter_id = self.request.GET.get('project_id')
        if project_filter_id:
            queryset = queryset.filter(tankhah__project__id=project_filter_id)

        return queryset.order_by('-created_at', '-pk')

    # get_approver_details و get_next_workflow_stages_info مانند قبل

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factors_processed_data = []
        user = self.request.user

        # دریافت queryset فیلتر شده برای محاسبات مجموع در هدر
        filtered_queryset_for_summary = self.get_queryset()  # کوئری با تمام فیلترها

        summary_stats = filtered_queryset_for_summary.aggregate(
            total_count=Count('id'),
            total_amount_sum=Coalesce(Sum('amount'), Decimal(0)),
            approved_count=Count('id', filter=Q(status='APPROVED')),
            approved_amount_sum=Coalesce(Sum('amount', filter=Q(status='APPROVED')), Decimal(0)),
            rejected_count=Count('id', filter=Q(status='REJECTED')),
            rejected_amount_sum=Coalesce(Sum('amount', filter=Q(status='REJECTED')), Decimal(0)),
            pending_count=Count('id', filter=Q(status='PENDING')),  # و سایر وضعیت‌ها
            paid_count=Count('id', filter=Q(status='PAID')),
            paid_amount_sum=Coalesce(Sum('amount', filter=Q(status='PAID')), Decimal(0)),
            locked_count=Count('id', filter=Q(is_locked=True)),  # اگر قبلا از لیست اصلی حذف نشده‌اند
            archived_count=Count('id', filter=Q(tankhah__is_archived=True))  # اگر قبلا از لیست اصلی حذف نشده‌اند
        )
        context['summary_stats'] = summary_stats

        for factor_obj in context['object_list']:  # factor_obj اینجا همان factor است
            factor = factor_obj
            # ... (بخش previous_actions مانند قبل، با کلاس‌های رنگی) ...
            previous_actions_hierarchy = []  # ... (کد کامل این بخش از مثال قبلی)
            current_actionable_approvers = []  # ... (کد کامل این بخش از مثال قبلی)
            can_current_user_act = False  # ... (کد کامل این بخش از مثال قبلی)
            budget_info = {}  # ... (کد کامل این بخش از مثال قبلی، شامل مانده‌ها)

            # دسته بندی بودجه (BudgetItem)
            # این بستگی به مدل شما دارد. یک سناریوی ممکن:
            # Factor -> Tankhah -> BudgetAllocation -> BudgetItem
            budget_item_name = None
            if factor.tankhah and factor.tankhah.budget_allocation and factor.tankhah.budget_allocation.budget_item:
                budget_item_name = factor.tankhah.budget_allocation.budget_item.name
            elif factor.category:  # اگر فاکتور مستقیما دسته بندی دارد که به نوعی سرفصل بودجه است
                # این ممکن است ItemCategory خود فاکتور باشد نه BudgetItem اصلی
                # برای نمایش دقیق BudgetItem، باید لینک درستی در مدل‌ها وجود داشته باشد
                budget_item_name = factor.category.name + " (از دسته فاکتور)"

            factors_processed_data.append({
                'factor': factor,
                'item_statuses_summary': {
                    'total': factor.total_items, 'approved': factor.approved_items_count,
                    'rejected': factor.rejected_items_count, 'pending': factor.pending_items_count,
                },
                'organization_name': factor.tankhah.organization.name if factor.tankhah and factor.tankhah.organization else "---",
                'project_name': factor.tankhah.project.name if factor.tankhah and factor.tankhah.project else _(
                    "بدون مرکز هزینه"),
                'current_tankhah_stage': {
                    'name': factor.tankhah.current_stage.name if factor.tankhah and factor.tankhah.current_stage else _(
                        "نامشخص"),
                } if factor.tankhah else None,
                'previous_actions': previous_actions_hierarchy,  # ... (از مثال قبلی)
                'current_actionable_approvers': current_actionable_approvers,  # ... (از مثال قبلی)
                'can_current_user_act_on_factor': can_current_user_act,  # ... (از مثال قبلی)
                'budget_info': budget_info,  # ... (از مثال قبلی)
                'budget_item_name': budget_item_name,  # نام دسته بندی بودجه
                'is_archived': factor.tankhah.is_archived if factor.tankhah else False,  # وضعیت آرشیو
                'is_locked_factor': factor.is_locked,  # وضعیت قفل خود فاکتور
            })

        context['factors_data_list'] = factors_processed_data
        context['title'] = _('پیگیری پیشرفته و جامع فاکتورها')
        context['factor_status_choices'] = Factor.STATUS_CHOICES
        # برای فیلتر پروژه بر اساس سازمان
        from core.models import Organization, Project
        organizations_for_project_filter = Organization.objects.filter(is_active=True).order_by('name')
        projects_for_filter_qs = Project.objects.filter(is_active=True)
        if self.organization_filter_id:  # استفاده از organization_filter_id که در get_queryset ذخیره شد
            projects_for_filter_qs = projects_for_filter_qs.filter(organizations__id=self.organization_filter_id)

        context['organizations_for_filter'] = organizations_for_project_filter
        context['projects_for_filter'] = projects_for_filter_qs.order_by('name').distinct()

        context['current_search'] = self.request.GET.get('search', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_organization_id'] = self.request.GET.get('organization_id', '')
        context['current_project_id'] = self.request.GET.get('project_id', '')
        context['current_show_archived'] = self.request.GET.get('show_archived', 'false').lower() == 'true'
        context['current_show_locked'] = self.request.GET.get('show_locked', 'false').lower() == 'true'

        return context
class ComprehensiveFactorDetailView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/Reports/comprehensive_factor_detail.html'
    context_object_name = 'factor_data_package'
    pk_url_kwarg = 'factor_pk'
    permission_codenames = ['tankhah.factor_view']
    check_organization = True

    def get_object(self, queryset=None):
        logger.info(f"Attempting to get object for {self.__class__.__name__}")
        if queryset is None:
            queryset = self.model._default_manager.all()
            logger.debug("Default queryset initialized.")

        pk = self.kwargs.get(self.pk_url_kwarg)
        logger.info(f"Factor PK from URL kwargs ('{self.pk_url_kwarg}'): {pk}")

        if pk is None:
            logger.error(f"View {self.__class__.__name__} is missing the pk argument from URL. kwargs: {self.kwargs}")
            raise Http404(_("شناسه فاکتور در URL مشخص نشده است."))

        optimized_queryset = queryset.select_related(
            'tankhah',
            'tankhah__organization',  # OK if Tankhah.organization is ForeignKey
            'tankhah__project',  # OK if Tankhah.project is ForeignKey
            # 'tankhah__project__organization', # <<< این خط مشکل‌ساز است چون Project.organizations یک ManyToManyField است
            'tankhah__current_stage',
            'tankhah__budget_allocation',
            'tankhah__budget_allocation__budget_item',
            'tankhah__budget_allocation__budget_period',
            'category',
            'created_by'
        )
        logger.debug("Applied select_related.")

        optimized_queryset = optimized_queryset.prefetch_related(
            Prefetch('items', queryset=FactorItem.objects.order_by('pk')),
            # بررسی کنید FactorItem فیلد category دارد یا نه برای select_related داخلی
            Prefetch('approval_logs',
                     queryset=ApprovalLog.objects.select_related(
                         'user', 'post', 'post__organization', 'post__parent', 'stage'
                     ).order_by('timestamp')),
            Prefetch('documents', queryset=FactorDocument.objects.order_by('-uploaded_at')),
            # prefetch کردن organizations مربوط به پروژه
            Prefetch('tankhah__project__organizations', queryset=Organization.objects.all())
        )
        logger.debug("Applied prefetch_related.")

        try:
            logger.info(f"Executing query to get Factor with pk={pk}")
            obj = optimized_queryset.get(pk=pk)
            logger.info(f"Factor with pk={pk} found successfully: {obj}")
            return obj
        except self.model.DoesNotExist:
            logger.warning(f"Factor with pk={pk} does not exist in the database.")
            raise Http404(_("فاکتور با شناسه '%(pk)s' یافت نشد.") % {'pk': pk})
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching Factor pk={pk}: {e}", exc_info=True)
            raise

    def get_approver_details(self, stage, entity_type='FACTOR'):
        logger.debug(
            f"Getting approver details for stage: {stage.name if stage else 'No Stage'}, entity_type: {entity_type}")
        if not stage:
            logger.warning("get_approver_details called with no stage.")
            return []

        approver_details_list = []
        # اینجا باید منطق خودتان برای پیدا کردن تأییدکنندگان را پیاده کنید
        # مثال با StageApprover (اگر مدل شما اینگونه است)
        # اگر از PostAction استفاده می‌کنید، کوئری متفاوت خواهد بود
        try:
            stage_approvers_query = StageApprover.objects.filter(stage=stage, is_active=True)
            # اگر StageApprover شما فیلد entity_type دارد:
            # stage_approvers_query = stage_approvers_query.filter(entity_type__iexact=entity_type) # iexact برای case-insensitive

            stage_approvers = stage_approvers_query.select_related(
                'post', 'post__organization', 'post__parent'
            ).order_by('post__level', 'post__name')

            logger.info(
                f"Found {stage_approvers.count()} StageApprover records for stage '{stage.name}' (ID: {stage.id}).")  # Removed entity_type for now

            for sa_idx, sa in enumerate(stage_approvers):
                if not sa.post:
                    logger.warning(
                        f"StageApprover record (PK: {sa.pk}, Index: {sa_idx}) has no associated post. Skipping.")
                    continue
                logger.debug(f"Processing StageApprover (PK: {sa.pk}), Post: {sa.post.name} (PK: {sa.post.pk})")

                users_in_post = UserPost.objects.filter(post=sa.post, is_active=True,
                                                        end_date__isnull=True).select_related('user')
                logger.debug(f"Found {users_in_post.count()} active users for post {sa.post.name}")

                approver_details_list.append({
                    'post_id': sa.post.id,
                    'post_name': sa.post.name,
                    'post_level': sa.post.level,
                    'post_branch': sa.post.get_branch_display() or '',
                    'post_branch_code': sa.post.branch,
                    'organization_name': sa.post.organization.name if sa.post.organization else _("نامشخص"),
                    'users': [{'id': up.user.id, 'name': up.user.get_full_name() or up.user.username} for up in
                              users_in_post]
                })
            logger.info(f"Generated {len(approver_details_list)} approver details for stage '{stage.name}'.")
        except Exception as e:
            logger.error(f"Error in get_approver_details for stage '{stage.name if stage else 'No Stage'}': {e}",
                         exc_info=True)
        return approver_details_list

    def get_context_data(self, **kwargs):
        logger.info(f"Starting get_context_data for {self.__class__.__name__}")
        context = super().get_context_data(**kwargs)
        # آبجکت فاکتور از DetailView.get_object() می‌آید و در context['object'] قرار دارد
        factor = context.get('object')  # استفاده از .get برای جلوگیری از KeyError

        if not factor:
            logger.error("Factor object not found in context. This should not happen if get_object succeeded.")
            # می‌توانید اینجا یک Http404 دیگر ایجاد کنید یا یک مقدار پیش‌فرض برای factor_data_package بگذارید
            context[self.context_object_name] = {
                'error': _("خطا: اطلاعات فاکتور یافت نشد.")
            }
            return context

        user = self.request.user
        logger.info(f"Preparing context for Factor PK: {factor.pk} (Number: {factor.number}) by User: {user.username}")

        # 1. اطلاعات پایه فاکتور و تنخواه مرتبط
        base_info = {
            'number': factor.number,
            'amount': factor.amount,
            'date': factor.date,
            # jdatetime.date.fromgregorian(date=factor.date).strftime('%Y/%m/%d') if factor.date else None,
            'description': factor.description,
            'status': factor.status,
            'status_display': factor.get_status_display(),
            'is_locked': factor.is_locked,
            'category_name': factor.category.name if factor.category else _("بدون دسته"),
            'created_by_name': factor.created_by.get_full_name() or factor.created_by.username if factor.created_by else _(
                "نامشخص"),
            'created_at_display': factor.created_at,  # .strftime('%Y/%m/%d %H:%M')
        }
        logger.debug(f"Base factor info prepared: {base_info}")

        if factor.tankhah:
            logger.debug(f"Factor is linked to Tankhah PK: {factor.tankhah.pk}")
            base_info.update({
                'tankhah_pk': factor.tankhah.pk,
                'tankhah_number': factor.tankhah.number,
                'tankhah_status': factor.tankhah.get_status_display(),
                'tankhah_is_archived': factor.tankhah.is_archived,
                'organization_name': factor.tankhah.organization.name if factor.tankhah.organization else _("نامشخص"),
                'project_pk': factor.tankhah.project.pk if factor.tankhah.project else None,
                'project_name': factor.tankhah.project.name if factor.tankhah.project else _("بدون مرکز هزینه"),
                'current_tankhah_stage_name': factor.tankhah.current_stage.name if factor.tankhah.current_stage else _(
                    "مرحله نامشخص"),
                'budget_item_name': factor.tankhah.budget_allocation.budget_item.name if factor.tankhah.budget_allocation and hasattr(
                    factor.tankhah.budget_allocation,
                    'budget_item') and factor.tankhah.budget_allocation.budget_item else _("سرفصل نامشخص"),
                'budget_period_name': factor.tankhah.budget_allocation.budget_period.name if factor.tankhah.budget_allocation and hasattr(
                    factor.tankhah.budget_allocation,
                    'budget_period') and factor.tankhah.budget_allocation.budget_period else _("دوره بودجه نامشخص"),
            })
        else:
            logger.warning(f"Factor PK: {factor.pk} has no associated Tankhah.")
            base_info.update({
                'tankhah_number': _("ندارد"), 'tankhah_status': _("ندارد"), 'tankhah_is_archived': False,
                'organization_name': _("نامشخص"), 'project_name': _("نامشخص"),
                'current_tankhah_stage_name': _("نامشخص"), 'budget_item_name': _("نامشخص"),
                'budget_period_name': _("نامشخص")
            })
        logger.debug(f"Tankhah related info prepared: {base_info}")

        # 2. ردیف‌های فاکتور (FactorItems)
        factor_items_list = []
        # .all() روی prefetch_related کوئری جدید به دیتابیس نمی‌زند
        factor_items_qs = factor.items.all()  # items از related_name در FactorItem.factor
        logger.debug(f"Processing {factor_items_qs.count()} factor items for Factor PK: {factor.pk}")
        for item_idx, item in enumerate(factor_items_qs):
            logger.debug(f"Item {item_idx + 1} (PK: {item.pk}): Amount={item.amount}, Status={item.status}")
            factor_items_list.append({
                'id': item.pk,
                'description': item.description,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'amount': item.amount,
                'status': item.get_status_display(),
                'status_code': item.status,
                'category_name': item.category.name if hasattr(item, 'category') and item.category else "---",
                # بررسی وجود category در FactorItem
            })

        # 3. تاریخچه اقدامات (Previous Actions)
        previous_actions_chronological = []
        action_logs_qs = factor.approval_logs.all()  # approval_logs از related_name در ApprovalLog.factor
        logger.debug(f"Processing {action_logs_qs.count()} approval logs for Factor PK: {factor.pk}")

        for log_idx, log in enumerate(action_logs_qs):
            action_status_class = ''
            if log.action == 'APPROVE':
                action_status_class = 'text-success'  # یا کلاس CSS
            elif log.action == 'REJECT':
                action_status_class = 'text-danger'
            else:
                action_status_class = 'text-info'
            logger.debug(
                f"Log {log_idx + 1} (PK: {log.pk}): Action={log.action}, User={log.user.username if log.user else 'System'}")

            previous_actions_chronological.append({
                'order': log_idx + 1,
                'post_name': log.post.name if log.post else _("نامشخص"),
                'post_level': log.post.level if log.post else 0,
                'post_branch_code': log.post.branch if log.post else '',
                'post_org_name': log.post.organization.name if log.post and log.post.organization else _("نامشخص"),
                'user_name': log.user.get_full_name() or log.user.username if log.user else _("سیستم"),
                'action': log.get_action_display(), 'action_status_class': action_status_class,
                'timestamp': log.timestamp,  # .strftime('%Y/%m/%d %H:%M')
                'comment': log.comment,
                'stage_name': log.stage.name if log.stage else _("نامشخص"),
            })

        # 4. اقدام‌کنندگان مجاز فعلی
        current_actionable_approvers_list = []
        can_current_user_act_flag = False
        factor_current_stage_for_action = None

        if factor.tankhah and factor.tankhah.current_stage and \
                not factor.is_locked and factor.status not in ['PAID', 'REJECTED']:  # اضافه کردن شرط وضعیت فاکتور
            factor_current_stage_for_action = factor.tankhah.current_stage
            logger.info(
                f"Factor PK: {factor.pk} is actionable. Current Tankhah stage: {factor_current_stage_for_action.name}")

            # entity_type را با توجه به منطق خودتان پاس دهید (مثلاً 'FACTOR' یا 'TANKHAH')
            current_stage_approvers_details = self.get_approver_details(factor_current_stage_for_action,
                                                                        entity_type='FACTOR')
            # اگر برای فاکتور چیزی پیدا نشد، با نوع تنخواه امتحان کنید (فال‌بک)
            if not current_stage_approvers_details and factor_current_stage_for_action:
                logger.info(
                    f"No specific approvers for FACTOR entity in stage {factor_current_stage_for_action.name}. Falling back to TANKHAH entity type.")
                current_stage_approvers_details = self.get_approver_details(factor_current_stage_for_action,
                                                                            entity_type='TANKHAH')

            current_actionable_approvers_list = current_stage_approvers_details
            user_active_posts_ids = UserPost.objects.filter(user=user, is_active=True,
                                                            end_date__isnull=True).values_list('post_id', flat=True)
            logger.debug(f"Logged in user ({user.username}) active post IDs: {list(user_active_posts_ids)}")

            for approver_detail in current_actionable_approvers_list:
                logger.debug(
                    f"Checking eligibility for post_id: {approver_detail['post_id']} ({approver_detail['post_name']})")
                if approver_detail['post_id'] in user_active_posts_ids:
                    can_current_user_act_flag = True
                    approver_detail['is_current_user_eligible'] = True
                    logger.info(f"User {user.username} IS ELIGIBLE to act via post: {approver_detail['post_name']}")
                else:
                    approver_detail['is_current_user_eligible'] = False
        else:
            logger.info(
                f"Factor PK: {factor.pk} is NOT actionable. Locked: {factor.is_locked}, Status: {factor.status}")

        # 5. اطلاعات بودجه‌ای
        budget_details = {
            'tankhah_current_remaining': Decimal('0'), 'tankhah_remaining_after_this': Decimal('0'),
            'project_current_remaining': Decimal('0'), 'project_remaining_after_this': Decimal('0'),
            'impact_message': ""
        }
        if factor.tankhah:
            logger.debug(
                f"Calculating budget details for Factor PK: {factor.pk} linked to Tankhah PK: {factor.tankhah.pk}")
            try:
                # **مهم:** مطمئن شوید توابع get_tankhah_remaining_budget و get_project_remaining_budget وجود دارند و کار می‌کنند.
                current_tankhah_rem = get_tankhah_remaining_budget(factor.tankhah)
                budget_details['tankhah_current_remaining'] = current_tankhah_rem
                budget_details[
                    'tankhah_remaining_after_this'] = current_tankhah_rem - factor.amount if factor.status not in [
                    'PAID', 'REJECTED'] else current_tankhah_rem
                logger.debug(
                    f"Tankhah budget: current_remaining={current_tankhah_rem}, after_this={budget_details['tankhah_remaining_after_this']}")

                if factor.tankhah.project:
                    current_project_rem = get_project_remaining_budget(factor.tankhah.project)
                    budget_details['project_current_remaining'] = current_project_rem
                    budget_details[
                        'project_remaining_after_this'] = current_project_rem - factor.amount if factor.status not in [
                        'PAID', 'REJECTED'] else current_project_rem
                    logger.debug(
                        f"Project ({factor.tankhah.project.name}) budget: current_remaining={current_project_rem}, after_this={budget_details['project_remaining_after_this']}")

                    if factor.status not in ['PAID', 'REJECTED']:
                        if factor.amount > current_tankhah_rem:
                            budget_details['impact_message'] = _(
                                "مبلغ فاکتور ({amount}) از مانده جاری تنخواه ({remaining}) بیشتر است!").format(
                                amount=factor.amount, remaining=current_tankhah_rem)
                            logger.warning(budget_details['impact_message'])
                        elif factor.amount > current_project_rem:  # این شرط باید بعد از شرط تنخواه باشد
                            budget_details['impact_message'] = _(
                                "مبلغ فاکتور ({amount}) از مانده جاری مرکز هزینه ({remaining}) بیشتر است!").format(
                                amount=factor.amount, remaining=current_project_rem)
                            logger.warning(budget_details['impact_message'])
                else:
                    logger.info(f"Tankhah PK: {factor.tankhah.pk} is not linked to any project.")

            except Exception as e:
                logger.error(f"Error calculating budget details for Factor PK {factor.pk}: {e}", exc_info=True)
                budget_details['impact_message'] = _("خطا در محاسبه اطلاعات بودجه.")

        # 6. اسناد ضمیمه فاکتور
        documents_list = list(factor.documents.all())  # documents از related_name در FactorDocument.factor
        logger.debug(f"Found {len(documents_list)} attached documents for Factor PK: {factor.pk}")

        # ساختار نهایی context
        # context['factor_data_package'] در اینجا توسط DetailView به صورت پیش‌فرض با context_object_name مقداردهی می‌شود
        # و مقدار آن همان factor است. ما می‌خواهیم یک دیکشنری جامع‌تر بسازیم.
        context[self.context_object_name] = {  # نام context_object_name که تعریف کرده‌اید
            'factor_instance': factor,  # خود آبجکت فاکتور برای دسترسی مستقیم در تمپلیت
            'base_info': base_info,
            'items': factor_items_list,
            'previous_actions_chronological': previous_actions_chronological,
            'current_actionable_approvers': current_actionable_approvers_list,
            'can_current_user_act_on_factor': can_current_user_act_flag,
            'factor_current_stage_for_action': factor_current_stage_for_action,
            'budget_info': budget_details,
            'attached_documents': documents_list,
        }
        context['title'] = _("جزئیات جامع فاکتور: ") + (
            factor.number if factor and factor.number else str(factor.pk if factor else 'N/A'))
        logger.info(f"Context preparation for Factor PK: {factor.pk} completed successfully. Title: {context['title']}")
        return context
class UltimateFactorDetailView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/Reports/ultimate_factor_detail.html'  # یک تمپلیت جدید و جامع
    context_object_name = 'factor_package'  # نام context اصلی
    pk_url_kwarg = 'factor_pk'  # مطابق با URL شما
    permission_codenames = ['tankhah.factor_view']  # یا مجوز دقیق‌تر
    check_organization = True  # اجازه دهید PermissionBaseView دسترسی سازمانی را بررسی کند

    def get_object(self, queryset=None):
        logger.info(f"[{self.__class__.__name__}] Attempting to get object.")
        if queryset is None:
            queryset = self.model._default_manager.all()
            logger.debug("Default queryset initialized.")

        pk = self.kwargs.get(self.pk_url_kwarg)
        logger.info(f"Factor PK from URL kwargs ('{self.pk_url_kwarg}'): {pk}")

        if pk is None:
            logger.error(f"Missing pk argument. kwargs: {self.kwargs}")
            raise Http404(_("شناسه فاکتور در URL مشخص نشده است."))

        # بهینه‌سازی کوئری با select_related و prefetch_related
        optimized_queryset = queryset.select_related(
            'tankhah',
            'tankhah__organization',
            'tankhah__project',
            'tankhah__subproject',  # اگر تنخواه می‌تواند به زیرپروژه هم لینک شود
            'tankhah__current_stage',
            'tankhah__created_by',
            'tankhah__budget_allocation',  # لینک تنخواه به تخصیص بودجه اصلی
            'tankhah__budget_allocation__budget_item',
            'tankhah__budget_allocation__budget_period',
            'tankhah__project_budget_allocation',  # لینک تنخواه به تخصیص بودجه پروژه
            'tankhah__project_budget_allocation__budget_allocation',  # برای دسترسی به تخصیص اصلی از تخصیص پروژه
            'category',  # دسته بندی خود فاکتور
            'created_by',  # کاربر ایجاد کننده فاکتور
            'locked_by_stage',  # اگر فاکتور توسط مرحله‌ای قفل شده
        ).prefetch_related(
            Prefetch('items', queryset=FactorItem.objects.order_by('pk').select_related('category')),
            # ردیف‌های فاکتور با دسته بندی‌شان
            Prefetch('approval_logs',
                     queryset=ApprovalLog.objects.select_related(
                         'user', 'post', 'post__organization', 'stage'
                     ).order_by('timestamp')),  # تاریخچه اقدامات
            Prefetch('documents',
                     queryset=FactorDocument.objects.select_related('uploaded_by').order_by('-uploaded_at')),
            # اسناد ضمیمه
            Prefetch('tankhah__project__organizations', queryset=Organization.objects.all()),
            # سازمان‌های پروژه (اگر ManyToMany)
            Prefetch('tankhah__approved_by'),  # تاییدکنندگان تنخواه (اگر ManyToMany)
            Prefetch('approved_by'),  # تاییدکنندگان خود فاکتور (اگر ManyToMany)
        )
        logger.debug("Query optimizers (select_related, prefetch_related) applied.")

        try:
            logger.info(f"Executing query to get Factor with pk={pk}")
            obj = optimized_queryset.get(pk=pk)
            logger.info(f"Factor with pk={pk} (Number: {obj.number}) found successfully.")
            return obj
        except self.model.DoesNotExist:
            logger.warning(f"Factor with pk={pk} does not exist.")
            raise Http404(_("فاکتور با شناسه '%(pk)s' یافت نشد.") % {'pk': pk})
        except Exception as e:
            logger.error(f"Unexpected error fetching Factor pk={pk}: {e}", exc_info=True)
            raise

    def get_factor_items_details(self, factor_instance):
        """جزئیات ردیف‌های فاکتور را آماده می‌کند."""
        items_list = []
        for item in factor_instance.items.all():  # از prefetch استفاده می‌کند
            items_list.append({
                'id': item.pk,
                'description': item.description,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'amount': item.amount,
                'status_display': item.get_status_display(),
                'status_code': item.status,
                'category_name': item.category.name if item.category else _("بدون دسته"),
                # 'vat_amount': item.vat_amount, # اگر فیلد مالیات بر ارزش افزوده دارید
                # 'total_with_vat': item.total_with_vat, # اگر فیلد مبلغ کل با مالیات دارید
            })
        logger.debug(f"Prepared {len(items_list)} factor items for factor {factor_instance.pk}")
        return items_list

    def get_approval_history(self, factor_instance):
        """تاریخچه اقدامات و تاییدها را آماده می‌کند."""
        history = []
        for log in factor_instance.approval_logs.all():  # از prefetch استفاده می‌کند
            action_class = ''
            if log.action == 'APPROVE':
                action_class = 'text-success border-success'
            elif log.action == 'REJECT':
                action_class = 'text-danger border-danger'
            elif log.action == 'STAGE_CHANGE':
                action_class = 'text-info border-info'
            else:
                action_class = 'text-muted border-secondary'

            history.append({
                'user_name': log.user.get_full_name() or log.user.username if log.user else _("سیستم"),
                'post_name': log.post.name if log.post else _("نامشخص"),
                'post_org_name': log.post.organization.name if log.post and log.post.organization else _("نامشخص"),
                'action_display': log.get_action_display(),
                'action_class': action_class,
                'timestamp': log.timestamp,
                # jdatetime.datetime.fromgregorian(datetime=log.timestamp).strftime('%Y/%m/%d %H:%M:%S')
                'stage_name': log.stage.name if log.stage else _("نامشخص"),
                'comment': log.comment or _("بدون توضیح"),
            })
        logger.debug(f"Prepared {len(history)} approval log entries for factor {factor_instance.pk}")
        return history

    def get_budget_impact_details(self, factor_instance):
        """اطلاعات تاثیر بودجه‌ای فاکتور را محاسبه می‌کند."""
        details = {
            'factor_amount': factor_instance.amount,
            'tankhah_info': None,
            'project_info': None,
            'subproject_info': None,
            'overall_impact_message': "",
        }

        if not factor_instance.tankhah:
            logger.warning(f"Factor {factor_instance.pk} has no associated Tankhah. Cannot calculate budget impact.")
            details['overall_impact_message'] = _("فاکتور به تنخواه متصل نیست. بررسی بودجه ممکن نیست.")
            return details

        tankhah = factor_instance.tankhah
        current_tankhah_remaining = get_tankhah_remaining_budget(tankhah)
        tankhah_remaining_after_factor = current_tankhah_remaining
        if factor_instance.status not in ['PAID', 'REJECTED']:  # اگر هنوز تاثیرش اعمال نشده
            tankhah_remaining_after_factor -= factor_instance.amount

        details['tankhah_info'] = {
            'number': tankhah.number,
            'amount': tankhah.amount,
            'current_remaining': current_tankhah_remaining,
            'remaining_after_this_factor': tankhah_remaining_after_factor,
            'has_sufficient_budget': factor_instance.amount <= current_tankhah_remaining or factor_instance.status in [
                'PAID', 'REJECTED'],
        }
        logger.debug(f"Tankhah budget impact for factor {factor_instance.pk}: {details['tankhah_info']}")

        if tankhah.project:
            project = tankhah.project
            current_project_remaining = get_project_remaining_budget(project)
            project_remaining_after_factor = current_project_remaining
            if factor_instance.status not in ['PAID', 'REJECTED']:
                project_remaining_after_factor -= factor_instance.amount

            details['project_info'] = {
                'name': project.name,
                'code': project.code,
                'total_budget': get_project_total_budget(project),  # ممکن است نیاز به بهینه سازی داشته باشد
                'current_remaining': current_project_remaining,
                'remaining_after_this_factor': project_remaining_after_factor,
                'has_sufficient_budget': factor_instance.amount <= current_project_remaining or factor_instance.status in [
                    'PAID', 'REJECTED'],
            }
            logger.debug(f"Project budget impact for factor {factor_instance.pk}: {details['project_info']}")

            if tankhah.subproject:  # اگر زیرپروژه هم دارد
                subproject = tankhah.subproject
                current_subproject_remaining = get_subproject_remaining_budget(subproject)
                subproject_remaining_after_factor = current_subproject_remaining
                if factor_instance.status not in ['PAID', 'REJECTED']:
                    subproject_remaining_after_factor -= factor_instance.amount

                details['subproject_info'] = {
                    'name': subproject.name,
                    'total_budget': subproject.allocated_budget,  # یا تابع get_subproject_total_budget
                    'current_remaining': current_subproject_remaining,
                    'remaining_after_this_factor': subproject_remaining_after_factor,
                    'has_sufficient_budget': factor_instance.amount <= current_subproject_remaining or factor_instance.status in [
                        'PAID', 'REJECTED'],
                }
                logger.debug(f"Subproject budget impact for factor {factor_instance.pk}: {details['subproject_info']}")

        # تعیین پیام کلی
        if factor_instance.status not in ['PAID', 'REJECTED']:
            if not details['tankhah_info']['has_sufficient_budget']:
                details['overall_impact_message'] = _("هشدار: مبلغ فاکتور از مانده تنخواه بیشتر است!")
            elif details['project_info'] and not details['project_info']['has_sufficient_budget']:
                details['overall_impact_message'] = _("هشدار: مبلغ فاکتور از مانده مرکز هزینه (پروژه) بیشتر است!")
            elif details['subproject_info'] and not details['subproject_info']['has_sufficient_budget']:
                details['overall_impact_message'] = _("هشدار: مبلغ فاکتور از مانده زیرپروژه بیشتر است!")
        logger.debug(
            f"Overall budget impact message for factor {factor_instance.pk}: '{details['overall_impact_message']}'")
        return details

    def get_next_actions_info(self, factor_instance):
        """اطلاعات مربوط به اقدامات بعدی و تاییدکنندگان مجاز."""
        actions_info = {
            'can_user_act': False,
            'current_stage_name': _("نامشخص"),
            'eligible_approvers': [],  # لیستی از دیکشنری‌ها: {'post_name': ..., 'users': [...]}
            'next_stage': None,  # آبجکت مرحله بعدی اگر مشخص است
        }
        user = self.request.user

        if factor_instance.is_locked or factor_instance.status in ['PAID', 'REJECTED']:
            logger.info(f"Factor {factor_instance.pk} is locked or in a final status. No next actions.")
            return actions_info

        if not factor_instance.tankhah or not factor_instance.tankhah.current_stage:
            logger.warning(f"Factor {factor_instance.pk} has no tankhah or tankhah has no current stage.")
            return actions_info

        current_stage = factor_instance.tankhah.current_stage
        actions_info['current_stage_name'] = current_stage.name

        # یافتن StageApprovers یا PostActions برای این مرحله و نوع فاکتور
        # این منطق باید با سیستم دسترسی شما تطبیق داده شود
        # مثال ساده با StageApprover (بدون در نظر گرفتن entity_type برای سادگی):
        possible_stage_approvers = StageApprover.objects.filter(stage=current_stage, is_active=True) \
            .select_related('post', 'post__organization')
        logger.debug(f"Found {possible_stage_approvers.count()} possible StageApprovers for stage {current_stage.name}")

        user_active_post_ids = list(
            UserPost.objects.filter(user=user, is_active=True, end_date__isnull=True).values_list('post_id', flat=True))

        for sa in possible_stage_approvers:
            users_in_this_post = [up.user.get_full_name() or up.user.username for up in
                                  UserPost.objects.filter(post=sa.post, is_active=True)]
            is_current_user_in_this_post = sa.post_id in user_active_post_ids
            if is_current_user_in_this_post:
                actions_info['can_user_act'] = True

            actions_info['eligible_approvers'].append({
                'post_name': sa.post.name,
                'post_org_name': sa.post.organization.name if sa.post.organization else '',
                'users': ", ".join(users_in_this_post) if users_in_this_post else _("کاربری یافت نشد"),
                'is_current_user_eligible_for_this_post': is_current_user_in_this_post
            })

        # یافتن مرحله بعدی (اگر گردش کار خطی ساده‌ای دارید)
        try:
            actions_info['next_stage'] = WorkflowStage.objects.filter(order__gt=current_stage.order,
                                                                      is_active=True).order_by('order').first()
        except WorkflowStage.DoesNotExist:
            pass
        logger.debug(f"Next actions info for factor {factor_instance.pk}: {actions_info}")
        return actions_info

    def get_context_data(self, **kwargs):
        logger.info(f"[{self.__class__.__name__}] Starting get_context_data.")
        context = super().get_context_data(**kwargs)
        factor_instance = context['object']  # آبجکت فاکتور از get_object
        user = self.request.user
        logger.info(
            f"Preparing context for Factor PK: {factor_instance.pk} (Number: {factor_instance.number}) by User: {user.username}")

        # --- جمع‌آوری اطلاعات پایه فاکتور ---
        from jdatetime import datetime as jdatetime
        factor_base_info = {
            'instance': factor_instance,  # خود آبجکت برای دسترسی به فیلدهای ساده
            'status_display': factor_instance.get_status_display(),
            'category_name': factor_instance.category.name if factor_instance.category else _("بدون دسته"),
            'created_by_name': factor_instance.created_by.get_full_name() or factor_instance.created_by.username if factor_instance.created_by else _(
                "نامشخص"),
            'jalali_date': jdatetime.date.fromgregorian(date=factor_instance.date).strftime(
                '%Y/%m/%d') if factor_instance.date else None,
            'jalali_created_at': jdatetime.datetime.fromgregorian(datetime=factor_instance.created_at).strftime(
                '%Y/%m/%d %H:%M') if factor_instance.created_at else None,
        }
        logger.debug("Factor base info prepared.")

        # --- اطلاعات تنخواه مرتبط ---
        tankhah_info = None
        if factor_instance.tankhah:
            tankhah = factor_instance.tankhah
            tankhah_info = {
                'instance': tankhah,
                'status_display': tankhah.get_status_display(),
                'jalali_date': jdatetime.date.fromgregorian(date=tankhah.date).strftime(
                    '%Y/%m/%d') if tankhah.date else None,
                'organization_name': tankhah.organization.name if tankhah.organization else _("نامشخص"),
                'project_name': tankhah.project.name if tankhah.project else _("بدون پروژه"),
                'subproject_name': tankhah.subproject.name if tankhah.subproject else None,
                'current_stage_name': tankhah.current_stage.name if tankhah.current_stage else _("نامشخص"),
                'created_by_name': tankhah.created_by.get_full_name() or tankhah.created_by.username if tankhah.created_by else _(
                    "نامشخص"),
            }
            if tankhah.budget_allocation:
                tankhah_info[
                    'budget_item_name'] = tankhah.budget_allocation.budget_item.name if tankhah.budget_allocation.budget_item else _(
                    "سرفصل نامشخص")
                tankhah_info[
                    'budget_period_name'] = tankhah.budget_allocation.budget_period.name if tankhah.budget_allocation.budget_period else _(
                    "دوره بودجه نامشخص")
        logger.debug(f"Tankhah info prepared: {bool(tankhah_info)}")

        # --- اطلاعات مرکز هزینه/پروژه ---
        project_details = None
        if factor_instance.tankhah and factor_instance.tankhah.project:
            project = factor_instance.tankhah.project
            project_organizations = project.organizations.all()  # از prefetch
            project_details = {
                'instance': project,
                'organizations_str': ", ".join(
                    [org.name for org in project_organizations]) if project_organizations else _("نامشخص"),
                'total_budget': get_project_total_budget(project),  # این تابع باید بهینه باشد
                'remaining_budget': get_project_remaining_budget(project),  # این تابع باید بهینه باشد
            }
        logger.debug(f"Project details prepared: {bool(project_details)}")

        # --- ساخت پکیج نهایی برای ارسال به تمپلیت ---
        context[self.context_object_name] = {
            'factor_base': factor_base_info,
            'tankhah_info': tankhah_info,
            'project_details': project_details,
            'factor_items': self.get_factor_items_details(factor_instance),
            'approval_history': self.get_approval_history(factor_instance),
            'budget_impact': self.get_budget_impact_details(factor_instance),
            'next_actions': self.get_next_actions_info(factor_instance),
            'attached_documents': list(factor_instance.documents.all()),  # از prefetch
            'current_user_can_act': self.get_next_actions_info(factor_instance)['can_user_act'],
            # برای دکمه‌های اقدام سریع
        }

        context['title'] = _("جزئیات فاکتور:") + f" {factor_instance.number}"
        logger.info(f"Context preparation for Factor PK: {factor_instance.pk} completed. Title: {context['title']}")
        return context
