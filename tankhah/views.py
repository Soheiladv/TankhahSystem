import logging

from django.contrib.contenttypes.models import ContentType
from django.core import cache
from django.utils import timezone
import jdatetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, View, TemplateView, ListView

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from accounts.models import CustomUser
from core.models import UserPost, WorkflowStage, SubProject, Project
from tankhah.models import ApprovalLog, Tankhah, StageApprover, Factor, FactorItem, FactorDocument, TankhahDocument, \
    FactorHistory
from budgets.budget_calculations import create_budget_transaction

from .utils import restrict_to_user_organization, get_factor_current_stage
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from budgets.budget_calculations import get_tankhah_remaining_budget, get_factor_remaining_budget
from core.PermissionBase import PermissionBaseView, get_lowest_access_level

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import permission_required
from .models import ItemCategory
from .forms import ItemCategoryForm
from django.db import transaction
from budgets.models import BudgetTransaction
from core.models import AccessRule, Organization
from django.db.models import Max, Q
from django.utils import timezone
logger = logging.getLogger('TankhahViews')

def RulesUserGuideView(request):
    extra_context = {'title': _('راهنمای کاربر: تخصیص قوانین دسترسی')}
    return render(request, template_name='help/ruls.new.html')
###########################################
# ثبت و ویرایش تنخواه
def get_subprojects(request):
    logger.info('ورود به تابع get_subprojects')
    project_id = request.GET.get('project_id')
    if not project_id:
        logger.warning('project_id دریافت نشد')
        return JsonResponse({'subprojects': []}, status=400)

    try:
        project_id = int(project_id)
        user_orgs = set(up.post.organization for up in request.user.userpost_set.all())
        logger.info(f'project_id: {project_id}, user_orgs: {user_orgs}')

        project = Project.objects.get(id=project_id)
        logger.info(f'پروژه {project_id}: {project.name}')

        # همه ساب‌پروژه‌ها رو بر اساس project_id برگردون، بدون فیلتر سازمان
        subprojects = SubProject.objects.filter(project_id=project_id).values('id', 'name')
        logger.info(f'subprojects found: {list(subprojects)}')
        return JsonResponse({'subprojects': list(subprojects)})
    except Project.DoesNotExist:
        logger.error(f'پروژه با id {project_id} یافت نشد')
        return JsonResponse({'subprojects': []}, status=404)
    except ValueError:
        logger.error(f'project_id نامعتبر: {project_id}')
        return JsonResponse({'subprojects': []}, status=400)
    except Exception as e:
        logger.error(f'خطا در get_subprojects: {str(e)}')
        return JsonResponse({'subprojects': []}, status=500)
def old___get_subprojects(request):
    logger.info('ورود به تابع get_subprojects')
    project_id = request.GET.get('project_id')
    if not project_id:
        logger.warning('project_id دریافت نشد')
        return JsonResponse({'subprojects': []}, status=400)

    try:
        project_id = int(project_id)
        logger.info(f'project_id: {project_id}')

        project = Project.objects.get(id=project_id)
        logger.info(f'پروژه {project_id}: {project.name}')

        # همه ساب‌پروژه‌ها رو بدون فیلتر سازمان برگردون
        subprojects = SubProject.objects.filter(project_id=project_id).values('id', 'name')
        logger.info(f'subprojects found: {list(subprojects)}')
        return JsonResponse({'subprojects': list(subprojects)})
    except Project.DoesNotExist:
        logger.error(f'پروژه با id {project_id} یافت نشد')
        return JsonResponse({'subprojects': []}, status=404)
    except ValueError:
        logger.error(f'project_id نامعتبر: {project_id}')
        return JsonResponse({'subprojects': []}, status=400)
    except Exception as e:
        logger.error(f'خطا در get_subprojects: {str(e)}')
        return JsonResponse({'subprojects': []}, status=500)

    #* ** * * ** * ** **

#--------------------------------------------
"""بررسی سطح فاکتور"""
def mark_approval_seen(request, tankhah):
    user_post = UserPost.objects.filter(user=request.user, end_date__isnull=True).first()
    if user_post:
        from tankhah.models import ApprovalLog
        ApprovalLog.objects.filter(
            tankhah=tankhah,
            post__level__lte=user_post.post.level,
            seen_by_higher=False
        ).update(seen_by_higher=True, seen_at=timezone.now())
        logger.info(f"Approval logs for Tankhah {tankhah.id} marked as seen by {request.user.username}")
#------------------------------------------------

class FactorDeleteView(PermissionRequiredMixin, DeleteView):
    model = Factor
    template_name = 'tankhah/factor_confirm_delete.html'
    success_url = reverse_lazy('factor_list')
    permission_required = 'tankhah.factor_delete'

    def has_permission(self):
        logger.info(f"[FactorDeleteView] Checking permission for user {self.request.user.username}")
        if not super().has_permission():
            logger.warning(f"[FactorDeleteView] User {self.request.user.username} lacks permission tankhah.factor_delete")
            messages.error(self.request, _("شما مجوز حذف فاکتور را ندارید."))
            return False

        factor = self.get_object()
        user = self.request.user
        tankhah = factor.tankhah

        user_post = user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
        if not user_post:
            logger.error(f"[FactorDeleteView] User {user.username} has no active post")
            messages.error(self.request, _("شما پست فعالی ندارید."))
            return False

        if tankhah.is_locked or tankhah.is_archived or factor.is_locked:
            logger.warning(f"[FactorDeleteView] Tankhah {tankhah.number} or Factor {factor.number} is locked/archived")
            messages.error(self.request, _("این فاکتور یا تنخواه قفل/آرشیو شده و قابل حذف نیست."))
            return False

        if factor.status not in ['DRAFT', 'PENDING', 'PENDING_APPROVAL'] and not user.has_perm('tankhah.Factor_full_edit'):
            logger.warning(f"[FactorDeleteView] Factor {factor.number} in status {factor.status} is not deletable")
            messages.error(self.request, _("فاکتور تأییدشده یا ردشده قابل حذف نیست."))
            return False

        is_hq_user = any(
            Organization.objects.filter(id=up.post.organization.id, is_core=True).exists()
            for up in user.userpost_set.filter(is_active=True, end_date__isnull=True)
        )
        if user.is_superuser or is_hq_user or user.has_perm('tankhah.Tankhah_view_all'):
            logger.info(f"[FactorDeleteView] User {user.username} has full access to delete factor {factor.number}")
            if self._has_previous_stage_approval(factor):
                logger.warning(f"[FactorDeleteView] Previous stage approved for factor {factor.number}, deletion blocked")
                messages.error(self.request, _("فاکتور دارای تأیید در مرحله قبلی است و قابل حذف نیست."))
                return False
            return True

        user_posts = user.userpost_set.filter(is_active=True, end_date__isnull=True).select_related('post')
        user_post_ids = [up.post.id for up in user_posts]
        user_orgs = [up.post.organization.id for up in user_posts]
        max_post_level = user_posts.aggregate(max_level=Max('post__level'))['max_level'] or 1
        logger.debug(f"[FactorDeleteView] User posts: {user_post_ids}, orgs: {user_orgs}, max_level: {max_post_level}")

        current_stage_order = get_factor_current_stage(factor)
        logger.debug(f"[FactorDeleteView] Current stage order for factor {factor.number}: {current_stage_order}")

        if not isinstance(current_stage_order, int):
            logger.error(f"[FactorDeleteView] Invalid current_stage_order type: {type(current_stage_order)}, value: {current_stage_order}")
            messages.error(self.request, _("مرحله فعلی فاکتور نامعتبر است."))
            return False

        if self._has_previous_stage_approval(factor):
            logger.warning(f"[FactorDeleteView] Previous stage approved for factor {factor.number}, deletion blocked")
            messages.error(self.request, _("فاکتور دارای تأیید در مرحله قبلی است و قابل حذف نیست."))
            return False

        allowed_rules = AccessRule.objects.filter(
            post__id__in=user_post_ids,
            organization__id__in=user_orgs,
            action_type='DELETE',
            entity_type='FACTOR',
            is_active=True,
            min_level__lte=max_post_level,
            stage_order=current_stage_order
        )
        logger.debug(f"[FactorDeleteView] Access rules query: {allowed_rules.query}")
        if not allowed_rules.exists():
            logger.warning(
                f"[FactorDeleteView] No AccessRule for user {user.username} to delete factor {factor.number} at stage {current_stage_order}"
            )
            messages.error(self.request, _("شما اجازه حذف این فاکتور را ندارید."))
            return False

        logger.info(f"[FactorDeleteView] Permission granted for user {user.username} to delete factor {factor.number}")
        return True

    def _has_previous_stage_approval(self, factor):
        current_stage_order = get_factor_current_stage(factor)
        previous_stage_order = current_stage_order - 1

        if previous_stage_order <= 0:
            logger.debug(f"[FactorDeleteView] No previous stage for factor {factor.number}, current_stage={current_stage_order}")
            return False

        return ApprovalLog.objects.filter(
            factor=factor,
            content_type=ContentType.objects.get_for_model(factor),
            object_id=factor.id,
            stage_order=previous_stage_order,
            action='APPROVE'
        ).exists()

    def perform_delete(self, request):
        factor = self.object
        tankhah = factor.tankhah
        user = request.user
        user_post = user.userpost_set.filter(is_active=True).first()

        if hasattr(factor, 'items') and factor.items.exists():
            logger.warning(f"[FactorDeleteView] Factor {factor.number} has associated items")
            raise PermissionDenied(_("این فاکتور دارای آیتم‌های مرتبط است و قابل حذف نیست."))

        remaining_budget = get_tankhah_remaining_budget(tankhah)
        if remaining_budget is None:
            logger.error(f"[FactorDeleteView] Could not calculate remaining budget for tankhah {tankhah.number}")
            raise ValueError(_("خطا در محاسبه بودجه باقی‌مانده تنخواه."))

        consumption_transaction = BudgetTransaction.objects.filter(
            related_obj=factor,
            content_type=ContentType.objects.get_for_model(Factor),
            transaction_type='CONSUMPTION'
        ).first()
        if consumption_transaction:
            create_budget_transaction(
                allocation=tankhah.project_budget_allocation,
                transaction_type='RETURN',
                amount=consumption_transaction.amount,
                related_obj=factor,
                created_by=user,
                description=f"بازگشت بودجه به دلیل حذف فاکتور {factor.number} در مرحله {get_factor_current_stage(factor)}",
                transaction_id=f"TX-FAC-DEL-{factor.number}-{timezone.now().timestamp()}"
            )
            logger.info(f"[FactorDeleteView] Budget returned for factor {factor.number}: {consumption_transaction.amount}")

        ApprovalLog.objects.create(
            tankhah=tankhah,
            factor=factor,
            user=user,
            action='DELETE',
            stage=tankhah.current_stage.stage,
            stage_order=tankhah.current_stage.stage_order,
            comment=f"حذف فاکتور {factor.number} در مرحله {tankhah.current_stage.stage}",
            post=user_post.post if user_post else None
        )

        FactorHistory.objects.create(
            factor=factor,
            change_type=FactorHistory.ChangeType.DELETION,
            changed_by=user,
            old_data={
                'status': factor.status,
                'amount': str(factor.amount),
                'tankhah': tankhah.number,
                'stage_order': get_factor_current_stage(factor)
            },
            new_data={},
            description=f"فاکتور {factor.number} توسط {user.username} حذف شد"
        )

        recipients = []
        if factor.created_by:
            recipients.append(factor.created_by)
        project = tankhah.project
        if project:
            recipients.extend(
                up.user for up in project.userpost_set.filter(
                    is_active=True, end_date__isnull=True
                ).exclude(user=user)
            )
        self.send_notifications(
            entity=factor,
            action='DELETED',
            priority='HIGH',
            description=f"فاکتور {factor.number} توسط {user.username} حذف شد.",
            recipients=recipients
        )

        factor.is_deleted = True
        factor.deleted_at = timezone.now()
        factor.deleted_by = user
        factor.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
        logger.info(f"[FactorDeleteView] Factor {factor.number} soft deleted by {user.username}")

        cache_key = f"tankhah_remaining_budget_{tankhah.pk}_no_filters"
        cache.delete(cache_key)
        logger.debug(f"[FactorDeleteView] Cleared cache for {cache_key}")

        tankhah.update_remaining_budget()
        tankhah.save(update_fields=['remaining_budget'])
#------------------------------------------------
"""تأیید آیتم‌های فاکتور"""
class FactorItemRejectView(PermissionBaseView, View):
    permission_codenames = ['tankhah.FactorItem_approve']
    template_name = 'tankhah/factor_item_reject_confirm.html'

    def get(self, request, pk):
        item = get_object_or_404('tankhah.FactorItem', pk=pk)
        factor = item.factor
        tankhah = factor.tankhah
        user_posts = request.user.userpost_set.all()

        # چک دسترسی
        try:
            restrict_to_user_organization(request.user, [tankhah.organization])
        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('dashboard_flows')

        if not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه رد این ردیف را ندارید.'))
            return redirect('dashboard_flows')

        # نمایش فرم تأیید
        return render(request, self.template_name, {
            'item': item,
            'factor': factor,
            'tankhah': tankhah,
        })

    def post(self, request, pk):
        item = get_object_or_404('tankhah.FactorItem', pk=pk)
        factor = item.factor
        tankhah = factor.tankhah
        user_posts = request.user.userpost_set.all()

        # چک دسترسی
        try:
            restrict_to_user_organization(request.user, [tankhah.organization])
        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('dashboard_flows')

        if not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه رد این ردیف را ندارید.'))
            return redirect('dashboard_flows')

        # تصمیم کاربر
        keep_in_tankhah = request.POST.get('keep_in_tankhah') == 'yes'

        with transaction.atomic():
            # رد کردن ردیف فاکتور
            item.status = 'REJECTED'
            item.save()
            logger.info(f"ردیف فاکتور {item.id} رد شد توسط {request.user.username}")

            # ثبت در لاگ
            ApprovalLog.objects.create(
                tankhah=tankhah,
                factor_item=item,
                user=request.user,
                action='REJECT',
                stage=tankhah.current_stage,
                comment='رد شده توسط کاربر'
            )

            if keep_in_tankhah:
                # فاکتور توی تنخواه می‌مونه و به تأیید برمی‌گرده
                factor.status = 'PENDING'
                factor.save()
                messages.info(request, _('ردیف فاکتور رد شد و فاکتور برای تأیید دوباره در تنخواه باقی ماند.'))
            else:
                # فاکتور رد می‌شه، تنخواه دست‌نخورده می‌مونه
                factor.status = 'REJECTED'
                factor.save()
                logger.info(f"فاکتور {factor.number} رد شد توسط {request.user.username}")
                messages.error(request, _('فاکتور رد شد و از جریان تأیید خارج شد.'))

        return redirect('dashboard_flows')# ---######## Approval Views ---
class ApprovalListView1(PermissionBaseView, ListView):
    model =  ApprovalLog
    template_name = 'tankhah/approval_list.html'
    context_object_name = 'approvals'
    paginate_by = 10
    extra_context = {'title': _('تاریخچه تأییدات')}

    def get_queryset(self):
        # تأییدات کاربر فعلی با اطلاعات مرتبط
        return ApprovalLog.objects.filter(user=self.request.user).select_related(
            'tankhah', 'factor_item', 'factor_item__factor', 'stage', 'post'
        ).order_by('-timestamp')
class ApprovalListView(PermissionBaseView, ListView):
    model = 'tankhah.ApprovalLog'
    template_name = 'tankhah/approval_list.html'
    context_object_name = 'approvals'
    paginate_by = 10
    extra_context = {'title': _('تاریخچه تأییدات')}

    def get_queryset(self):
        user = self.request.user
        # اگه کاربر HQ هست، همه تأییدات رو نشون بده
        if hasattr(user, 'is_hq') and user.is_hq:
            return ApprovalLog.objects.select_related(
                'tankhah', 'factor_item', 'factor_item__factor', 'stage', 'post'
            ).order_by('-timestamp')
        # در غیر این صورت، فقط تأییدات کاربر فعلی
        return ApprovalLog.objects.filter(user=user).select_related(
            'tankhah', 'factor_item', 'factor_item__factor', 'stage', 'post'
        ).order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # چک کردن امکان تغییر
        for approval in context['approvals']:
            approval.can_edit = (
                (hasattr(user, 'is_hq') and user.is_hq) or  # HQ همیشه می‌تونه تغییر بده
                (approval.user == user and  # کاربر خودش باشه
                 not ApprovalLog.objects.filter(
                     tankhah=approval.tankhah,
                     stage__order__gt=approval.stage.order,
                     action='APPROVE'
                 ).exists())  # هنوز بالادستی تأیید نکرده
            )
        return context
class ApprovalLogListView(PermissionBaseView, ListView):
    model = 'tankhah.ApprovalLog'
    template_name = 'tankhah/approval_log_list.html'
    context_object_name = 'logs'
    paginate_by = 10

    def get_queryset(self):
        # چک کن که tankhah_number توی kwargs باشه
        tankhah_number = self.kwargs.get('tankhah_number')
        if not tankhah_number:
            raise ValueError("پارامتر 'tankhah_number' در URL تعریف نشده است.")
        return ApprovalLog.objects.filter(tankhah__number=tankhah_number).order_by('-timestamp')
class ApprovalDetailView(PermissionBaseView, DetailView):
    model = 'tankhah.ApprovalLog'
    template_name = 'tankhah/approval_detail.html'
    context_object_name = 'approval'
    extra_context = {'title': _('جزئیات تأیید')}
    # نسخه جدید بنویس
class ApprovalCreateView(PermissionRequiredMixin, CreateView):
    model = 'tankhah.ApprovalLog'
    form_class = 'tankhah.forms.ApprovalForm'
    template_name = 'tankhah/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'Tankhah.Approval_add'

    def form_valid(self, form):
        form.instance.user = self.request.user
        user_post = UserPost.objects.filter(user=self.request.user, end_date__isnull=True).first()  # فقط پست فعال
        user_level = user_post.post.level if user_post else 0

        # ثبت لاگ و به‌روزرسانی وضعیت
        if form.instance.tankhah:  # دقت کن که Tankhah باید tankhah باشه (کوچیک)
            tankhah = form.instance.tankhah
            current_status = tankhah.status
            branch = form.instance.action

            if hasattr(tankhah, 'current_stage') and branch != tankhah.current_stage.name:  # مقایسه با نام مرحله
                messages.error(self.request, _('شما نمی‌توانید در این مرحله تأیید کنید.'))
                return self.form_invalid(form)

            if form.instance.action == 'APPROVE':
                if branch == 'COMPLEX' and current_status == 'PENDING' and user_level <= 2:
                    tankhah.status = 'APPROVED'

                    tankhah.current_stage = AccessRule.objects.get(name='OPS')
                elif branch == 'OPS' and current_status == 'APPROVED' and user_level > 2:
                     tankhah.current_stage = WorkflowStage.objects.get(name='FIN')
                elif branch == 'FIN' and  user_level > 3:

                    tankhah.status = 'PAID'
                else:
                    messages.error(self.request, _('شما اجازه تأیید در این مرحله را ندارید یا وضعیت نادرست است.'))
                    return self.form_invalid(form)
            else:
                tankhah.status = 'REJECTED'
            tankhah.last_stopped_post = user_post.post if user_post else None
            tankhah.save()

            # ثبت لاگ برای تنخواه
            form.instance.stage = tankhah.current_stage
            form.instance.post = user_post.post if user_post else None

        elif form.instance.factor:
            factor = form.instance.factor
            tankhah = factor.tankhah  # گرفتن تنخواه مرتبط
            factor.status = 'APPROVED' if form.instance.action == 'APPROVE' else 'REJECTED'
            factor.save()

            # ثبت لاگ برای فاکتور
            form.instance.tankhah = tankhah
            form.instance.stage = tankhah.current_stage if tankhah else None
            form.instance.post = user_post.post if user_post else None

        elif form.instance.factor_item:
            item = form.instance.factor_item
            tankhah = item.factor.tankhah  # گرفتن تنخواه از ردیف فاکتور
            if hasattr(item, 'status'):
                item.status = 'APPROVED' if form.instance.action == 'APPROVE' else 'REJECTED'
                item.save()
            else:
                messages.warning(self.request, _('ردیف فاکتور فاقد وضعیت است و تأیید اعمال نشد.'))

            # ثبت لاگ برای ردیف فاکتور
            form.instance.tankhah = tankhah
            form.instance.stage = tankhah.current_stage if tankhah else None
            form.instance.post = user_post.post if user_post else None

        messages.success(self.request, _('تأیید با موفقیت ثبت شد.'))
        return super().form_valid(form)

    def can_approve_user(self, user, tankhah):
        current_stage = tankhah.current_stage
        approver_posts =   StageApprover.objects.filter(stage=current_stage).values_list('post', flat=True)
        user_posts = user.userpost_set.filter(end_date__isnull=True).values_list('post', flat=True)
        return bool(set(user_posts) & set(approver_posts))

    def get_initial(self):
        initial = super().get_initial()
        initial['tankhah'] = self.request.GET.get('tankhah')  # کوچیک شده
        initial['factor'] = self.request.GET.get('factor')
        initial['factor_item'] = self.request.GET.get('factor_item')
        return initial

    def dispatch(self, request, *args, **kwargs):
        # اصلاح برای گرفتن tankhah
        from tankhah.models import  Tankhah,FactorItem
        if 'tankhah' in request.GET:
            tankhah = Tankhah.objects.get(pk=request.GET['tankhah'])
        elif 'factor' in request.GET:
            tankhah = Factor.objects.get(pk=request.GET['factor']).tankhah
        elif 'factor_item' in request.GET:
            tankhah = FactorItem.objects.get(pk=request.GET['factor_item']).factor.tankhah
        else:
            raise PermissionDenied(_('تنخواه مشخص نشده است.'))

        if not self.can_approve_user(request.user, tankhah):
            raise PermissionDenied(_('شما مجاز به تأیید در این مرحله نیستید.'))
        return super().dispatch(request, *args, **kwargs)
class ApprovalUpdateView(PermissionBaseView, UpdateView):
    model = 'tankhah.ApprovalLog'
    form_class = 'tankhah.forms.ApprovalForm'
    template_name = 'tankhah/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_codenames = ['tankhah.Approval_update']

    def get_queryset(self):
        return ApprovalLog.objects.filter(user=self.request.user)

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        tankhah = self.object.tankhah
        current_stage = tankhah.current_stage
        user_posts = UserPost.objects.filter(user=request.user, end_date__isnull=True).values_list('post', flat=True)
        approver_posts =  StageApprover.objects.filter(stage=current_stage).values_list('post', flat=True)
        can_edit = bool(set(user_posts) & set(approver_posts))

        if not can_edit:
            raise PermissionDenied(_('شما نمی‌توانید این تأیید را ویرایش کنید، چون مرحله تغییر کرده یا دسترسی ندارید.'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        approval = form.instance
        tankhah = approval.tankhah
        user_post = UserPost.objects.filter(user=self.request.user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0

        # به‌روزرسانی وضعیت و انتقال مرحله
        if tankhah:
            current_status = tankhah.status
            branch = form.instance.action

            if tankhah.current_stage != approval.stage:
                messages.error(self.request, _('مرحله تغییر کرده و نمی‌توانید این تأیید را ویرایش کنید.'))
                return self.form_invalid(form)

            if form.instance.action == 'APPROVE':
                if branch == 'COMPLEX' and current_status == 'PENDING' and user_level <= 2:
                    tankhah.status = 'APPROVED'

                    next_stage = WorkflowStage.objects.filter(order__gt=tankhah.current_stage.order).order_by(
                        'order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                elif branch == 'OPS' and current_status == 'APPROVED' and user_level > 2:

                    next_stage = WorkflowStage.objects.filter(order__gt=tankhah.current_stage.order).order_by(
                        'order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                elif branch == 'FIN'   and user_level > 3:
                    tankhah.status = 'PAID'
                    next_stage = None  # مرحله آخر
                else:
                    messages.error(self.request, _('شما اجازه ویرایش در این مرحله را ندارید یا وضعیت نادرست است.'))
                    return self.form_invalid(form)

                # انتقال به مرحله بعدی و اعلان
                if next_stage:
                    tankhah.save()
                    approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage,
                                                          userpost__end_date__isnull=True)
                    if approvers.exists():
                        pass
                    messages.info(self.request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                else:
                    tankhah.is_locked = True
                    tankhah.is_archived = True
                    tankhah.save()
                    messages.success(self.request, _('تنخواه تکمیل و آرشیو شد.'))

            elif form.instance.action == 'REJECT':
                tankhah.status = 'REJECTED'
                tankhah.last_stopped_post = user_post.post if user_post else None
                tankhah.save()
                messages.warning(self.request, _('تنخواه رد شد.'))

        messages.success(self.request, _('تأیید با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('خطا در ویرایش تأیید. لطفاً ورودی‌ها را بررسی کنید.'))
        return super().form_invalid(form)
class ApprovalDeleteView(PermissionBaseView, DeleteView):
    model = 'tankhah.ApprovalLog'
    template_name = 'tankhah/approval_confirm_delete.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'Tankhah.Approval_delete'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تأیید با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)
#---------------------
@permission_required('tankhah.ItemCategory_view')
def itemcategory_list(request):
    categories = ItemCategory.objects.all()
    return render(request, 'tankhah/itemcategory/list.html', {'categories': categories})

@permission_required('tankhah.ItemCategory_add')
def itemcategory_create(request):
    form = ItemCategoryForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('itemcategory_list')
    return render(request, 'tankhah/itemcategory/form.html', {'form': form})

@permission_required('tankhah.ItemCategory_update')
def itemcategory_update(request, pk):
    category = get_object_or_404(ItemCategory, pk=pk)
    form = ItemCategoryForm(request.POST or None, instance=category)
    if form.is_valid():
        form.save()
        return redirect('itemcategory_list')
    return render(request, 'tankhah/itemcategory/form.html', {'form': form})

@permission_required('tankhah.ItemCategory_delete')
def itemcategory_delete(request, pk):
    category = get_object_or_404(ItemCategory, pk=pk)
    if request.method == 'POST':
        category.delete()
        return redirect('itemcategory_list')
    return render(request, 'tankhah/itemcategory/confirm_delete.html', {'category': category})
# --- لیست دسته‌بندی‌ها ---
class ItemCategoryListView(PermissionRequiredMixin, ListView):
    model = ItemCategory
    template_name = 'tankhah/itemcategory/list.html'
    context_object_name = 'categories' # نامی که در template استفاده می‌شود
    permission_required = 'tankhah.view_itemcategory' # مجوز مورد نیاز برای نمایش لیست

    # اگر نیاز به فیلتر یا مرتب سازی خاصی دارید:
    # def get_queryset(self):
    #     return ItemCategory.objects.filter(some_field=True)
# --- ایجاد دسته‌بندی جدید ---
class ItemCategoryCreateView(PermissionRequiredMixin, CreateView):
    model = ItemCategory
    form_class = ItemCategoryForm # استفاده از فرم سفارشی
    template_name = 'tankhah/itemcategory/form.html'
    success_url = reverse_lazy('itemcategory_list') # به کجا بعد از موفقیت ریدایرکت شود
    permission_required = 'tankhah.add_itemcategory' # مجوز مورد نیاز برای ایجاد
# --- به‌روزرسانی دسته‌بندی ---
class ItemCategoryUpdateView(PermissionRequiredMixin, UpdateView):
    model = ItemCategory
    form_class = ItemCategoryForm
    template_name = 'tankhah/itemcategory/form.html'
    context_object_name = 'category' # نامی که در template برای آبجکت استفاده می‌شود (به جای object)
    success_url = reverse_lazy('itemcategory_list')
    permission_required = 'tankhah.change_itemcategory' # مجوز مورد نیاز برای ویرایش
# --- حذف دسته‌بندی ---
class ItemCategoryDeleteView(PermissionRequiredMixin, DeleteView):
    model = ItemCategory
    template_name = 'tankhah/itemcategory/confirm_delete.html'
    context_object_name = 'category' # نامی که در template برای آبجکت استفاده می‌شود
    success_url = reverse_lazy('itemcategory_list')
    permission_required = 'tankhah.delete_itemcategory' # مجوز مورد نیاز برای حذف

    # برای نمایش نام دسته‌بندی در صفحه حذف (اگرچه context_object_name هم این کار را می‌کند)
    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context['category_name'] = self.object.name # اگر بخواهید نام خاصی را پاس دهید
    #     return context



# -- وضعیت تنخواه
@login_required
def upload_tankhah_documents(request, tankhah_id):
    from tankhah.models import   Tankhah
    tankhah = Tankhah.objects.get(id=tankhah_id)
    if request.method == 'POST':
        from tankhah.forms import TankhahDocumentForm
        form = TankhahDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('documents')
            for file in files:
               TankhahDocument.objects.create(Tankhah='tankhah.Tankhah', document=file)
            messages.success(request, 'اسناد با موفقیت آپلود شدند.')
            return redirect('Tankhah_detail', pk='tankhah.Tankhah'.id)
        else:
            messages.error(request, 'خطایی در آپلود اسناد رخ داد.')
    else:
        from tankhah.forms import  TankhahDocumentForm
        form = TankhahDocumentForm()

    return render(request, 'tankhah/upload_documents.html', {
        'form': form,
        'Tankhah': 'tankhah.Tankhah',
        'existing_documents':  Tankhah.documents.all()
    })
class FactorStatusUpdateView(PermissionBaseView, View):
    permission_required = 'tankhah.FactorItem_approve'
    def post(self, request, pk, *args, **kwargs):
        factor = Factor.objects.get(pk=pk)
        tankhah = factor.tankhah
        action = request.POST.get('action')

        if tankhah.is_locked or tankhah.is_archived:
            messages.error(request, _('این تنخواه قفل یا آرشیو شده و قابل تغییر نیست.'))
            return redirect('tankhah_tracking', pk=tankhah.pk)

        user_post = request.user.userpost_set.filter(end_date__isnull=True).first()
        if action == 'REJECT' and factor.status == 'APPROVED':
            factor.status = 'REJECTED'
            tankhah.status = 'REJECTED'
            tankhah.last_stopped_post = user_post.post if user_post else None
        elif action == 'APPROVE' and factor.status == 'REJECTED':
            factor.status = 'APPROVED'
            tankhah.status = 'PENDING' if any(f.status != 'APPROVED' for f in tankhah.factors.all()) else 'APPROVED'

        factor.save()
        tankhah.save()

        # ثبت لاگ
        ApprovalLog.objects.create(
            tankhah=tankhah,
            factor=factor,
            user=request.user,
            action=action,
            stage=tankhah.current_stage,
            post=user_post.post if user_post else None
        )

        # آپدیت مرحله
        workflow_stages = WorkflowStage.objects.order_by('order')
        current_stage = tankhah.current_stage
        if not current_stage:
            tankhah.current_stage = workflow_stages.first()
            tankhah.save()

        # چک کردن تأیید همه فاکتورها توی مرحله فعلی
        approvals_in_current = ApprovalLog.objects.filter(
            tankhah=tankhah, stage=current_stage, action='APPROVE'
        ).count()
        factors_count = tankhah.factors.count()
        if approvals_in_current >= factors_count and action == 'APPROVE':
            # next_stage = workflow_stages.filter(order__gt=current_stage.order).first()
            next_stage = workflow_stages.filter(order__lt=current_stage.order).order_by('-order').first()

            if next_stage:
                tankhah.current_stage = next_stage
                tankhah.status = 'PENDING'
                tankhah.save()
                messages.info(request, _(f"تنخواه به مرحله {next_stage.name} منتقل شد."))
            elif all(f.status == 'APPROVED' for f in tankhah.factors.all()):
                tankhah.status = 'APPROVED'
                tankhah.save()
                messages.info(request, _('تنخواه کاملاً تأیید شد.'))

        messages.success(request, _('وضعیت فاکتور با موفقیت تغییر کرد.'))
        return redirect('tankhah_tracking', pk=tankhah.pk)

@require_POST
def mark_notification_as_read(request, notif_id):

    from notificationApp.models import Notification
    notif = Notification.get(id=notif_id, user=request.user)
    notif.is_read = True
    notif.save()
    return JsonResponse({'status': 'success'})

@login_required
def get_unread_notifications(request):
    # دریافت اعلان‌های خوانده نشده کاربر

    from notificationApp.models import Notification
    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:10]  # 10 اعلان آخر خوانده نشده

    # سریالایز کردن داده‌ها
    serialized_notifications = []
    for notification in unread_notifications:
        serialized_notifications.append({
            'id': notification.id,
            'message': notification.message,
            'tankhah_id': notification.tankhah.id if notification.tankhah else None,
            'tankhah_number': notification.tankhah.number if notification.tankhah else None,
            'created_at': notification.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'is_read': notification.is_read
        })

    # ساخت پاسخ JSON
    response_data = {
        'status': 'success',
        'count': unread_notifications.count(),
        'notifications': serialized_notifications,
        'unread_count': request.user.notifications.filter(is_read=False).count()
    }

    return JsonResponse(response_data)
