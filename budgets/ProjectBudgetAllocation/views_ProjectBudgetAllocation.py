import json
import logging
# --- BudgetAllocation CRUD ---
from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, DeleteView, CreateView, TemplateView
from budgets.BudgetAllocation.forms_BudgetAllocation import BudgetAllocationForm
from budgets.ProjectBudgetAllocation.forms_ProjectBudgetAllocation import ProjectBudgetAllocationForm
from budgets.budget_calculations import (get_organization_budget, get_project_total_budget, get_project_used_budget,
                                         get_project_remaining_budget)
from budgets.get_budget_details import get_budget_details
from budgets.models import BudgetAllocation, BudgetTransaction, BudgetAllocation
from core.PermissionBase import PermissionBaseView
from core.models import Organization, Project, SubProject
from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum, Prefetch, Q, DecimalField
from django.db.models.functions import Coalesce
from django.views.generic import DetailView

logger = logging.getLogger("ProjectBudgetAllocationDetailView")

class older__ProjectBudgetAllocationListView(ListView):
    model = BudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_list.html'
    context_object_name = 'allocations'
    paginate_by = 10

    def get_queryset(self):
        organization_id = self.kwargs['organization_id']
        organization = get_object_or_404(Organization, id=organization_id)
        project_id = self.request.GET.get('project_id')
        queryset = BudgetAllocation.objects.filter(
            budget_allocation__organization=organization,
            budget_allocation__is_active=True
        ).select_related(
            'project', 'subproject', 'budget_allocation__budget_period', 'budget_allocation__organization'
        ).order_by('-allocation_date')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        logger.info(f"Allocations for org {organization_id}: {queryset.count()} records")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = get_object_or_404(Organization, id=self.kwargs['organization_id'])

        # دریافت تخصیص‌های بودجه سازمان
        budget_allocations = BudgetAllocation.objects.filter(
            organization=organization, is_active=True
        ).select_related('budget_period')

        # محاسبه بودجه کل و باقی‌مانده سازمان
        total_org_budget = budget_allocations.aggregate(
            total=Sum('allocated_amount')
        )['total'] or Decimal('0')

        consumed = BudgetTransaction.objects.filter(
            allocation__in=budget_allocations,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        returned = BudgetTransaction.objects.filter(
            allocation__in=budget_allocations,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        remaining_org_budget = total_org_budget - consumed + returned

        # داده‌های پروژه‌ها
        project_data = []
        projects = Project.objects.filter(
            organizations=organization, is_active=True
        ).prefetch_related('subprojects')

        for project in projects:
            project_allocations = BudgetAllocation.objects.filter(
                project=project, subproject__isnull=True
            )
            total_budget = project_allocations.aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')

            # استفاده از related_name صحیح: project_allocations
            project_budget_allocations = BudgetAllocation.objects.filter(
                project_allocations__project=project
            )
            consumed = BudgetTransaction.objects.filter(
                allocation__in=project_budget_allocations,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            returned = BudgetTransaction.objects.filter(
                allocation__in=project_budget_allocations,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            remaining_budget = total_budget - consumed + returned
            remaining_percentage = (
                (remaining_budget / total_budget * 100) if total_budget > 0 else Decimal('0')
            )
            allocated_percentage = (
                (total_budget / total_org_budget * 100) if total_org_budget > 0 else Decimal('0')
            )

            project_data.append({
                'project': project,
                'total_budget': total_budget,
                'remaining_budget': remaining_budget,
                'remaining_percentage': remaining_percentage,
                'allocated_percentage': allocated_percentage
            })

        # بررسی شرایط خاص
        if not budget_allocations.exists():
            messages.warning(self.request, _("هیچ تخصیص بودجه فعالی برای این سازمان یافت نشد"))

        context.update({
            'organization': organization,
            'total_org_budget': total_org_budget,
            'remaining_org_budget': remaining_org_budget,
            'project_data': project_data,
        })
        logger.info(f"Context prepared for organization {organization.id}: {context}")
        return context
class old_BudgetAllocationDetailView(PermissionBaseView, DetailView):
    model = BudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_detail.html'
    context_object_name = 'allocation'
    permission_codename = 'budgets.BudgetAllocation_view'
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    check_organization = True

    def get_object(self, queryset=None):
        """استخراج شیء با بررسی وجود و دسترسی"""
        if queryset is None:
            queryset = self.get_queryset()

        pk = self.kwargs.get(self.pk_url_kwarg)
        queryset = queryset.filter(pk=pk)
        try:
            obj = queryset.get()
            if not obj.is_active:
                logger.error(f"Allocation {obj.pk} is inactive")
                raise Http404(_('تخصیص بودجه غیرفعال است.'))
            return obj
        except BudgetAllocation.DoesNotExist:
            logger.error(f"BudgetAllocation با ID {pk} یافت نشد")
            raise Http404(_("تخصیص بودجه پروژه یافت نشد."))

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return redirect('budgetallocation_list')
        return super().dispatch(request, *args, **kwargs)

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     allocation = self.get_object()
    #     if not allocation:
    #         return context
    #
    #     organization = allocation.budget_allocation.organization
    #     budget_allocation = allocation.budget_allocation
    #     logger.debug(f"Preparing context for allocation {allocation.id}, organization {organization.name}")
    #
    #     # بودجه کل سازمان
    #     total_org_budget = budget_allocation.allocated_amount
    #     logger.debug(f"Total organization budget: {total_org_budget}")
    #
    #     # پیدا کردن زیرپروژه‌های مرتبط
    #     subprojects = SubProject.objects.filter(allocations=allocation)
    #
    #     # محاسبه تراکنش‌ها
    #     consumed = BudgetTransaction.objects.filter(
    #         allocation=budget_allocation,
    #         allocation__project=allocation.project,
    #         transaction_type='CONSUMPTION'
    #     ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    #
    #     returned = BudgetTransaction.objects.filter(
    #         allocation=budget_allocation,
    #         allocation__project=allocation.project,
    #         transaction_type='RETURN'
    #     ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    #
    #     consumed_amount = consumed - returned
    #     logger.debug(f"Consumed: {consumed}, Returned: {returned}, Net consumed: {consumed_amount}")
    #
    #     # بودجه باقی‌مانده
    #     remaining_org_budget = total_org_budget - BudgetTransaction.objects.filter(
    #         allocation=budget_allocation,
    #         transaction_type='CONSUMPTION'
    #     ).aggregate(total=Sum('amount'))['total'] or Decimal('0') + BudgetTransaction.objects.filter(
    #         allocation=budget_allocation,
    #         transaction_type='RETURN'
    #     ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    #     logger.debug(f"Remaining organization budget: {remaining_org_budget}")
    #
    #     # تراکنش‌های اخیر
    #     recent_transactions = BudgetTransaction.objects.filter(
    #         allocation=budget_allocation,
    #         allocation__project=allocation.project
    #     ).order_by('-timestamp')[:10]
    #
    #     context.update({
    #         'organization': organization,
    #         'total_org_budget': total_org_budget,
    #         'consumed_amount': consumed_amount,
    #         'remaining_org_budget': remaining_org_budget,
    #         'subprojects': subprojects,
    #         'recent_transactions': recent_transactions,
    #         'project': allocation.project,
    #     })
    #     # اضافه کردن اطلاعات بودجه
    #     project = allocation.project
    #     context.update({
    #         'total_budget': get_project_total_budget(project),
    #         'used_budget': get_project_used_budget(project),
    #         'remaining_budget': get_project_remaining_budget(project),
    #         'budget_details': get_budget_details(entity=project),
    #     })
    #
    #     return context
    def get_context_data(self, **kwargs):
        """افزودن داده‌های اضافی به کنتکست"""
        context = super().get_context_data(**kwargs)
        allocation = self.object

        organization = allocation.budget_allocation.organization
        budget_allocation = allocation.budget_allocation
        logger.debug(f"Preparing context for allocation {allocation.id}, organization {organization.name}")

        # بودجه کل سازمان
        total_org_budget = budget_allocation.allocated_amount
        logger.debug(f"Total organization budget: {total_org_budget}")

        # پیدا کردن زیرپروژه‌های مرتبط
        subprojects = SubProject.objects.filter(allocations=allocation)

        # محاسبه تراکنش‌ها
        consumed = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            allocation__project=allocation.project,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        returned = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            allocation__project=allocation.project,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        consumed_amount = consumed - returned
        logger.debug(f"Consumed: {consumed}, Returned: {returned}, Net consumed: {consumed_amount}")

        # بودجه باقی‌مانده
        remaining_org_budget = total_org_budget - consumed + returned
        logger.debug(f"Remaining organization budget: {remaining_org_budget}")

        # تراکنش‌های اخیر
        recent_transactions = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            allocation__project=allocation.project
        ).order_by('-timestamp')[:10]

        # اضافه کردن اطلاعات به کنتکست
        context.update({
            'organization': organization,
            'total_org_budget': total_org_budget,
            'consumed_amount': consumed_amount,
            'remaining_org_budget': remaining_org_budget,
            'subprojects': subprojects,
            'recent_transactions': recent_transactions,
            'project': allocation.project,
            'remaining_amount': budget_allocation.get_remaining_amount(),
        })

        # اضافه کردن اطلاعات بودجه پروژه (در صورت نیاز)
        project = allocation.project
        context.update({
            'total_budget': get_project_total_budget(project),
            'used_budget': get_project_used_budget(project),
            'remaining_budget': get_project_remaining_budget(project),
            'budget_details': get_budget_details(entity=project),
        })

        logger.info(f"جزئیات تخصیص بودجه پروژه {allocation.pk} بارگذاری شد")
        return context

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error accessing allocation {self.kwargs.get('pk')}: {str(e)}")
            messages.error(request, _("خطایی در دسترسی به جزئیات تخصیص بودجه رخ داد."))
            return self.redirect_to_organizations()

    def redirect_to_organizations(self):
        return redirect('organization_list')
class  old__ProjectBudgetAllocationDetailView(PermissionBaseView, DetailView): # یا PermissionBaseView
# class  BudgetAllocationDetailView(LoginRequiredMixin, DetailView): # یا PermissionBaseView
    model = BudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_detail.html' # تمپلیتی که ارائه دادید
    context_object_name = 'allocation' # این 'allocation' همان BudgetAllocation است
    # pk_url_kwarg = 'pk' # اگر نام پارامتر در URL 'pk' باشد، این خط لازم نیست

    # permission_codenames = ['budgets.view_BudgetAllocation'] # اگر از PermissionBaseView استفاده می‌کنید
    # check_organization = True # اگر از PermissionBaseView استفاده می‌کنید

    def get_queryset(self):
        # بهینه‌سازی کوئری اولیه
        return super().get_queryset().select_related(
            'budget_allocation',                # BudgetAllocation اصلی که این PBA به آن تعلق دارد
            'budget_allocation__organization',  # سازمانِ BudgetAllocation اصلی
            'budget_allocation__budget_period', # دوره بودجهِ BudgetAllocation اصلی
            'budget_allocation__budget_item',   # سرفصل بودجهِ BudgetAllocation اصلی
            'project',                          # پروژه مرتبط با این PBA
            'subproject',                       # زیرپروژه مرتبط با این PBA (اگر وجود دارد)
            'created_by'                        # کاربر ایجاد کننده این PBA
        ).prefetch_related(
            # اگر BudgetAllocation خودش تراکنش مستقیم دارد (که معمولا ندارد)
            # Prefetch('budget_transactions_directly_on_pba', queryset=BudgetTransaction.objects.order_by('-timestamp'))
        )

    def get_object(self, queryset=None):
        # این متد مسئول واکشی آبجکت بر اساس pk از URL است
        obj = super().get_object(queryset)
        if not obj.is_active: # یا هر شرط دیگری برای فعال بودن
            logger.warning(f"Attempted to access inactive/invalid BudgetAllocation (PK: {obj.pk}).")
            messages.warning(self.request, _('تخصیص بودجه پروژه درخواستی معتبر یا فعال نیست.'))
            raise Http404(_("تخصیص بودجه پروژه درخواستی معتبر یا فعال نیست."))
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # self.object همان نمونه BudgetAllocation است
        pba_instance = self.object # خوانایی بیشتر
        main_budget_allocation = pba_instance.budget_allocation
        organization_instance = main_budget_allocation.organization
        project_instance = pba_instance.project
        subproject_instance = pba_instance.subproject # ممکن است None باشد

        logger.info(f"Preparing context for BudgetAllocation PK: {pba_instance.pk} (Project: {project_instance.name if project_instance else 'N/A'})")
        subprojects_with_their_allocations = []
        if pba_instance.project:  # اگر این تخصیص به یک پروژه اصلی است (و نه یک زیرپروژه)
            # پیدا کردن تمام زیرپروژه‌های فعال این پروژه اصلی
            active_subprojects_of_this_project = SubProject.objects.filter(
                project=pba_instance.project,
                is_active=True
            ).prefetch_related(
                # prefetch کردن BudgetAllocation هایی که به این main_budget_allocation مرتبط هستند
                Prefetch(
                    'project_allocations',  # related_name از SubProject به BudgetAllocation
                    queryset=BudgetAllocation.objects.filter(budget_allocation=main_budget_allocation),
                    to_attr='allocations_from_this_main_ba'  # یک نام برای دسترسی به نتیجه prefetch
                )
            )

            for subp in active_subprojects_of_this_project:
                # مجموع تخصیص‌ها به این subproject از main_budget_allocation فعلی
                # اگر از prefetch بالا استفاده می‌کنید:
                total_allocated_to_subp_from_main_ba = sum(
                    pba.allocated_amount for pba in subp.allocations_from_this_main_ba
                )
                # یا اگر prefetch نمی‌کنید (کوئری N+1 ایجاد می‌کند):
                # total_allocated_to_subp_from_main_ba = BudgetAllocation.objects.filter(
                #     subproject=subp,
                #     budget_allocation=main_budget_allocation # فیلتر بر اساس BudgetAllocation اصلی
                # ).aggregate(total=Coalesce(Sum('allocated_amount'), Decimal('0'), output_field=DecimalField()))['total']

                subprojects_with_their_allocations.append({
                    'instance': subp,  # خود آبجکت SubProject
                    'name': subp.name,
                    'allocated_from_main_ba': total_allocated_to_subp_from_main_ba,
                    # می‌توانید مانده کلی زیرپروژه را هم اینجا محاسبه کنید اگر لازم است
                    # 'overall_remaining': get_subproject_remaining_budget(subp)
                })

        context['subprojects_data_for_report'] = subprojects_with_their_allocations  # نام جدید برای context
        # --- اطلاعات پایه این BudgetAllocation (PBA) ---
        context['pba_details'] = {
            'id': pba_instance.pk,
            'allocated_amount': pba_instance.allocated_amount,
            'allocation_date': pba_instance.allocation_date,
            'description': pba_instance.description,
            'is_active': pba_instance.is_active,
            'created_by': pba_instance.created_by.get_full_name() if pba_instance.created_by else _("نامشخص"),
        }

        # --- اطلاعات BudgetAllocation اصلی (که این PBA از آن منشعب شده) ---
        # تراکنش‌های مرتبط با BudgetAllocation اصلی
        # **مهم:** فرض بر این است که BudgetTransaction به BudgetAllocation لینک می‌شود.
        transactions_on_main_ba = BudgetTransaction.objects.filter(allocation=main_budget_allocation)

        consumed_on_main_ba = transactions_on_main_ba.filter(transaction_type='CONSUMPTION').aggregate(
            total=Coalesce(Sum('amount'), Decimal('0'), output_field=DecimalField())
        )['total']
        returned_on_main_ba = transactions_on_main_ba.filter(transaction_type='RETURN').aggregate(
            total=Coalesce(Sum('amount'), Decimal('0'), output_field=DecimalField())
        )['total']
        # مانده BudgetAllocation اصلی با استفاده از متد مدل (اگر دارد) یا تابع محاسباتی
        # remaining_on_main_ba = main_budget_allocation.get_remaining_amount() # اگر متد دارد
        remaining_on_main_ba = get_budget_details(main_budget_allocation) # یا تابع محاسباتی

        context['main_budget_allocation_summary'] = {
            'instance': main_budget_allocation,
            'total_allocated': main_budget_allocation.allocated_amount,
            'total_consumed_on_it': consumed_on_main_ba, # کل مصرف از این تخصیص اصلی
            'total_returned_to_it': returned_on_main_ba, # کل بازگشتی به این تخصیص اصلی
            'current_remaining_on_it': remaining_on_main_ba,
            'budget_item_name': main_budget_allocation.budget_item.name if main_budget_allocation.budget_item else "-",
            'budget_period_name': main_budget_allocation.budget_period.name if main_budget_allocation.budget_period else "-",
        }

        # --- اطلاعات پروژه ---
        if project_instance:
            # کل بودجه تخصیص یافته به این پروژه (از تمام منابع، نه فقط این PBA)
            total_allocated_to_project_overall = BudgetAllocation.objects.filter(
                project=project_instance, is_active=True
            ).aggregate(total=Coalesce(Sum('allocated_amount'), Decimal('0'), output_field=DecimalField()))['total']

            # مصرف و مانده کلی پروژه با استفاده از توابع محاسباتی شما
            project_remaining_overall = get_project_remaining_budget(project_instance)
            project_consumed_overall = total_allocated_to_project_overall - project_remaining_overall

            context['project_overall_summary'] = {
                'instance': project_instance,
                'total_allocated_overall': total_allocated_to_project_overall,
                'total_consumed_overall': project_consumed_overall,
                'current_remaining_overall': project_remaining_overall,
            }

        # --- اطلاعات زیرپروژه (اگر این PBA مربوط به یک زیرپروژه است) ---
        if subproject_instance:
            # کل بودجه تخصیص یافته به این زیرپروژه (از تمام منابع)
            total_allocated_to_subproject_overall = BudgetAllocation.objects.filter(
                subproject=subproject_instance, is_active=True
            ).aggregate(total=Coalesce(Sum('allocated_amount'), Decimal('0'), output_field=DecimalField()))['total']

            subproject_remaining_overall =  get_project_remaining_budget(subproject_instance)
            subproject_consumed_overall = total_allocated_to_subproject_overall - subproject_remaining_overall

            context['subproject_overall_summary'] = {
                'instance': subproject_instance,
                'total_allocated_overall': total_allocated_to_subproject_overall,
                'total_consumed_overall': subproject_consumed_overall,
                'current_remaining_overall': subproject_remaining_overall,
            }

        # --- سایر تخصیص‌ها به زیرپروژه‌های دیگر همین پروژه از همین BudgetAllocation اصلی ---
        # (این بخش مشابه کد قبلی شماست و منطقی به نظر می‌رسد)
        other_subproject_allocations_from_same_ba = []
        if project_instance and main_budget_allocation:
            other_subproject_allocs_qs = BudgetAllocation.objects.filter(
                budget_allocation=main_budget_allocation,
                project=project_instance,
                subproject__isnull=False,
                is_active=True
            ).exclude(pk=pba_instance.pk).select_related('subproject') # خودش را حذف کن

            for spa in other_subproject_allocs_qs:
                other_subproject_allocations_from_same_ba.append({
                    'subproject_name': spa.subproject.name,
                    'allocated_amount_to_subproject': spa.allocated_amount,
                    # 'remaining_for_subproject': get_subproject_remaining_budget(spa.subproject) # اگر لازم است
                })
        context['other_subproject_allocations_from_same_ba'] = other_subproject_allocations_from_same_ba

        # --- تراکنش‌های اخیر مربوط به BudgetAllocation اصلی ---
        # (برای نمایش به کاربر که از این تخصیص اصلی چه هزینه‌هایی شده)
        context['recent_transactions_on_main_ba'] = transactions_on_main_ba.select_related(
            'related_tankhah', 'created_by' # و سایر فیلدهای لازم برای نمایش
        ).order_by('-timestamp')[:10]


        # برای دسترسی آسان در تمپلیت (علاوه بر context_object_name='allocation')
        context['organization'] = organization_instance
        context['project'] = project_instance
        context['subproject'] = subproject_instance # ممکن است None باشد

        context['title'] = _("جزئیات تخصیص بودجه پروژه:") + f" {project_instance.name if project_instance else ''} "
        if subproject_instance:
            context['title'] += f"({subproject_instance.name}) "
        context['title'] += f"- #{pba_instance.pk}"

        logger.info(f"Context fully prepared for BudgetAllocation PK: {pba_instance.pk}")
        return context
#$-----------
#فهرست بودجه های سازمان
class  ProjectBudgetAllocationListView(ListView):
    template_name = 'budgets/budget/project_budget_allocation_list.html'
    context_object_name = 'allocations'
    paginate_by = 10

    def get_queryset(self):
        organization_id = self.kwargs['organization_id']
        organization = get_object_or_404(Organization, id=organization_id)
        project_id = self.request.GET.get('project_id')

        # فیلتر تخصیص‌های بودجه برای سازمان
        queryset = BudgetAllocation.objects.filter(
            organization=organization,
            is_active=True
        ).select_related(
            'project', 'subproject', 'budget_period', 'organization'
        ).order_by('-allocation_date')

        if project_id:
            queryset = queryset.filter(project_id=project_id)

        logger.info(f"Found {queryset.count()} budget allocations for organization {organization_id}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = get_object_or_404(Organization, id=self.kwargs['organization_id'])

        # دریافت تخصیص‌های بودجه سازمان
        budget_allocations = BudgetAllocation.objects.filter(
            organization=organization, is_active=True
        ).select_related('budget_period')

        # محاسبه بودجه کل و باقی‌مانده سازمان
        total_org_budget = budget_allocations.aggregate(
            total=Sum('allocated_amount')
        )['total'] or Decimal('0')

        consumed = BudgetTransaction.objects.filter(
            allocation__in=budget_allocations,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        returned = BudgetTransaction.objects.filter(
            allocation__in=budget_allocations,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        remaining_org_budget = total_org_budget - consumed + returned

        # داده‌های پروژه‌ها
        project_data = []
        projects = Project.objects.filter(
            organizations=organization, is_active=True
        ).prefetch_related('subprojects')

        for project in projects:
            project_allocations = BudgetAllocation.objects.filter(
                project=project, subproject__isnull=True
            )
            total_budget = project_allocations.aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')

            # محاسبه مصرف و بازگشت برای پروژه
            consumed = BudgetTransaction.objects.filter(
                allocation__in=project_allocations,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            returned = BudgetTransaction.objects.filter(
                allocation__in=project_allocations,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            remaining_budget = total_budget - consumed + returned
            remaining_percentage = (
                (remaining_budget / total_budget * 100) if total_budget > 0 else Decimal('0')
            )
            allocated_percentage = (
                (total_budget / total_org_budget * 100) if total_org_budget > 0 else Decimal('0')
            )

            project_data.append({
                'project': project,
                'total_budget': total_budget,
                'remaining_budget': remaining_budget,
                'remaining_percentage': remaining_percentage,
                'allocated_percentage': allocated_percentage
            })

        # هشدار در صورت عدم وجود تخصیص
        if not budget_allocations.exists():
            messages.warning(self.request, _("هیچ تخصیص بودجه فعالی برای این سازمان یافت نشد"))

        context.update({
            'organization': organization,
            'total_org_budget': total_org_budget,
            'remaining_org_budget': remaining_org_budget,
            'project_data': project_data,
        })
        logger.info(f"Context prepared for organization {organization.id}")
        return context
class ProjectBudgetAllocationDetailView(PermissionBaseView, DetailView):
    model = BudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_detail.html'
    context_object_name = 'allocation'

    def get_queryset(self):
        return super().get_queryset().select_related(
            'budget_period', 'organization', 'budget_item', 'project', 'subproject', 'created_by'
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.is_active:
            logger.warning(f"Attempted to access inactive BudgetAllocation (PK: {obj.pk}).")
            messages.warning(self.request, _('تخصیص بودجه درخواستی معتبر یا فعال نیست.'))
            raise Http404(_("تخصیص بودجه درخواستی معتبر یا فعال نیست."))
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation = self.object
        organization = allocation.organization
        project = allocation.project
        subproject = allocation.subproject

        logger.info(f"Preparing context for BudgetAllocation PK: {allocation.pk} (Project: {project.name if project else 'N/A'})")

        # اطلاعات زیرپروژه‌ها
        subprojects_data = []
        if project:
            active_subprojects = SubProject.objects.filter(
                project=project, is_active=True
            ).prefetch_related('project_allocations')
            for subproject in active_subprojects:
                subproject_allocations = BudgetAllocation.objects.filter(
                    subproject=subproject, is_active=True
                )
                total_allocated = subproject_allocations.aggregate(
                    total=Coalesce(Sum('allocated_amount'), Decimal('0'), output_field=DecimalField())
                )['total']
                subprojects_data.append({
                    'instance': subproject,
                    'name': subproject.name,
                    'allocated_amount': total_allocated,
                })
        context['subprojects_data_for_report'] = subprojects_data

        # اطلاعات تخصیص بودجه (برای هماهنگی با pba_details)
        context['pba_details'] = {
            'id': allocation.pk,
            'allocated_amount': allocation.allocated_amount,
            'allocation_date': allocation.allocation_date,
            'description': allocation.description or '-',
            'is_active': allocation.is_active,
            'created_by': allocation.created_by.get_full_name() if allocation.created_by else _("نامشخص"),
        }

        # اطلاعات بودجه اصلی (برای هماهنگی با main_budget_allocation_summary)
        transactions = BudgetTransaction.objects.filter(allocation=allocation)
        consumed = transactions.filter(transaction_type='CONSUMPTION').aggregate(
            total=Coalesce(Sum('amount'), Decimal('0'), output_field=DecimalField())
        )['total']
        returned = transactions.filter(transaction_type='RETURN').aggregate(
            total=Coalesce(Sum('amount'), Decimal('0'), output_field=DecimalField())
        )['total']
        remaining = allocation.allocated_amount - consumed + returned

        context['main_budget_allocation_summary'] = {
            'instance': allocation,
            'total_allocated': allocation.allocated_amount,
            'total_consumed_on_it': consumed,
            'total_returned_to_it': returned,
            'current_remaining_on_it': remaining,
            'budget_item_name': allocation.budget_item.name if allocation.budget_item else "-",
            'budget_period_name': allocation.budget_period.name if allocation.budget_period else "-",
        }

        # اطلاعات پروژه
        if project:
            project_allocations = BudgetAllocation.objects.filter(project=project, is_active=True)
            total_project_allocated = project_allocations.aggregate(
                total=Coalesce(Sum('allocated_amount'), Decimal('0'), output_field=DecimalField())
            )['total']
            project_transactions = BudgetTransaction.objects.filter(allocation__in=project_allocations)
            project_consumed = project_transactions.filter(transaction_type='CONSUMPTION').aggregate(
                total=Coalesce(Sum('amount'), Decimal('0'), output_field=DecimalField())
            )['total']
            project_returned = project_transactions.filter(transaction_type='RETURN').aggregate(
                total=Coalesce(Sum('amount'), Decimal('0'), output_field=DecimalField())
            )['total']
            project_remaining = total_project_allocated - project_consumed + project_returned

            context['project_overall_summary'] = {
                'instance': project,
                'total_allocated_overall': total_project_allocated,
                'total_consumed_overall': project_consumed,
                'current_remaining_overall': project_remaining,
            }

        # اطلاعات زیرپروژه
        if subproject:
            subproject_allocations = BudgetAllocation.objects.filter(subproject=subproject, is_active=True)
            total_subproject_allocated = subproject_allocations.aggregate(
                total=Coalesce(Sum('allocated_amount'), Decimal('0'), output_field=DecimalField())
            )['total']
            subproject_transactions = BudgetTransaction.objects.filter(allocation__in=subproject_allocations)
            subproject_consumed = subproject_transactions.filter(transaction_type='CONSUMPTION').aggregate(
                total=Coalesce(Sum('amount'), Decimal('0'), output_field=DecimalField())
            )['total']
            subproject_returned = subproject_transactions.filter(transaction_type='RETURN').aggregate(
                total=Coalesce(Sum('amount'), Decimal('0'), output_field=DecimalField())
            )['total']
            subproject_remaining = total_subproject_allocated - subproject_consumed + subproject_returned

            context['subproject_overall_summary'] = {
                'instance': subproject,
                'total_allocated_overall': total_subproject_allocated,
                'total_consumed_overall': subproject_consumed,
                'current_remaining_overall': subproject_remaining,
            }

        # سایر تخصیص‌های زیرپروژه‌ها
        other_subproject_allocations = []
        if project and not subproject:
            other_allocations_qs = BudgetAllocation.objects.filter(
                project=project, subproject__isnull=False, is_active=True
            ).exclude(pk=allocation.pk).select_related('subproject')
            for alloc in other_allocations_qs:
                other_subproject_allocations.append({
                    'subproject_name': alloc.subproject.name,
                    'allocated_amount_to_subproject': alloc.allocated_amount,
                })
        context['other_subproject_allocations_from_same_ba'] = other_subproject_allocations

        # تراکنش‌های اخیر
        context['recent_transactions_on_main_ba'] = transactions.select_related(
            'created_by', 'related_tankhah'
        ).order_by('-timestamp')[:10]

        # اطلاعات اضافی
        context['organization'] = organization
        context['project'] = project
        context['subproject'] = subproject
        context['report_title'] = f"{_('جزئیات تخصیص بودجه')}: {project.name if project else ''} " \
                                 f"{'(' + subproject.name + ')' if subproject else ''} - #{allocation.pk}"

        logger.info(f"Context fully prepared for BudgetAllocation PK: {allocation.pk}")
        return context
# class BudgetAllocationCreateView(PermissionBaseView, CreateView):
class ProjectBudgetAllocationCreateView(PermissionBaseView, CreateView):
    model = BudgetAllocation
    form_class = ProjectBudgetAllocationForm
    template_name = 'budgets/budget/project_budget_allocation.html'
    permission_codenames = ['budgets.BudgetAllocation_add']  # پرمیشن دقیق

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = get_object_or_404(Organization, id=self.kwargs['organization_id'])
        context['organization'] = organization

        # تخصیص‌های بودجه فعال
        budget_allocations = BudgetAllocation.objects.filter(
            organization=organization,
            is_active=True,
            budget_period__is_active=True
        ).select_related('budget_period', 'budget_item', 'project').order_by('-allocation_date')

        if not budget_allocations.exists():
            logger.warning(f"No active BudgetAllocation found for organization {organization.id}")
            messages.warning(self.request, _("هیچ تخصیص بودجه فعالی برای این سازمان یافت نشد"))
            context.update({
                'form': None,
                'projects': [],
                'budget_allocation': None,
                'budget_period': None,
                'total_org_budget': Decimal('0'),
                'remaining_amount': Decimal('0'),
                'remaining_percent': Decimal('0'),
                'warning_threshold': 50,
                'project_data': [],
                'budget_allocations_json': '[]',
                'subprojects_json': '[]',
            })
            return context

        # داده‌های JSON برای جاوااسکریپت
        allocations_list_for_json = [
            {
                'id': alloc.id,
                'name': f"{alloc.budget_item.name} - {alloc.budget_period.name} ({alloc.allocation_date})",
                'allocated_amount': float(alloc.allocated_amount),
                'remaining_amount': float(alloc.get_remaining_amount() or Decimal('0')),
            } for alloc in budget_allocations
        ]
        context['budget_allocations_json'] = json.dumps(allocations_list_for_json, cls=DjangoJSONEncoder)

        # زیرپروژه‌ها
        subprojects_list = list(SubProject.objects.filter(
            project__organizations=organization,
            is_active=True
        ).select_related('project').values('id', 'name', 'project_id'))
        context['subprojects_json'] = json.dumps(subprojects_list, cls=DjangoJSONEncoder)

        # تخصیص اولیه
        form = context.get('form')
        initial_allocation_id = None
        if form:
            if form.initial.get('budget_allocation'):
                initial_allocation_id = form.initial['budget_allocation']
            elif form.is_bound and form.data.get('budget_allocation'):
                initial_allocation_id = form.data['budget_allocation']

        budget_allocation = budget_allocations.filter(id=initial_allocation_id).first() or budget_allocations.first()
        context['budget_allocation'] = budget_allocation

        # محاسبه بودجه سازمان
        budget_totals = budget_allocations.aggregate(
            total_allocated=Sum('allocated_amount'),
            consumed=Sum('transactions__amount', filter=Q(transactions__transaction_type='CONSUMPTION')),
            returned=Sum('transactions__amount', filter=Q(transactions__transaction_type='RETURN'))
        )
        total_org_budget = budget_totals['total_allocated'] or Decimal('0')
        consumed = budget_totals['consumed'] or Decimal('0')
        returned = budget_totals['returned'] or Decimal('0')
        remaining_amount = total_org_budget - consumed + returned
        remaining_percent = (remaining_amount / total_org_budget * 100) if total_org_budget > 0 else Decimal('0')

        # محاسبه برای تخصیص انتخاب‌شده
        allocation_total = budget_allocation.allocated_amount if budget_allocation else Decimal('0')
        allocation_remaining = budget_allocation.get_remaining_amount() if budget_allocation else Decimal('0')
        allocation_remaining_percent = (
            (allocation_remaining / allocation_total * 100) if allocation_total > 0 else Decimal('0')
        )

        # پروژه‌ها
        projects = Project.objects.filter(
            organizations=organization,
            is_active=True
        ).prefetch_related(
            'subprojects',
            'budget_allocations__budget_allocation'
        ).order_by('name')

        project_data = []
        for project in projects:
            project_allocations = BudgetAllocation.objects.filter(
                project=project,
                subproject__isnull=True
            )
            total_budget = project_allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
            project_budget_allocations = BudgetAllocation.objects.filter(
                project_allocations__project=project
            )
            budget_totals = project_budget_allocations.aggregate(
                consumed=Sum('transactions__amount', filter=Q(transactions__transaction_type='CONSUMPTION')),
                returned=Sum('transactions__amount', filter=Q(transactions__transaction_type='RETURN'))
            )
            consumed = budget_totals['consumed'] or Decimal('0')
            returned = budget_totals['returned'] or Decimal('0')
            remaining_budget = total_budget - consumed + returned
            remaining_percentage = (
                (remaining_budget / total_budget * 100) if total_budget > 0 else Decimal('0')
            )

            project.total_budget = total_budget
            project.remaining_budget = remaining_budget
            project.total_percent = (
                (total_budget / total_org_budget * 100) if total_org_budget > 0 else Decimal('0')
            )
            project.remaining_percent = remaining_percentage

            for subproject in project.subprojects.filter(is_active=True):
                subproject_allocations = BudgetAllocation.objects.filter(subproject=subproject)
                subproject_budget = subproject_allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
                subproject_budget_allocations = BudgetAllocation.objects.filter(
                    project_allocations__subproject=subproject
                )
                sub_totals = subproject_budget_allocations.aggregate(
                    consumed=Sum('transactions__amount', filter=Q(transactions__transaction_type='CONSUMPTION')),
                    returned=Sum('transactions__amount', filter=Q(transactions__transaction_type='RETURN'))
                )
                sub_consumed = sub_totals['consumed'] or Decimal('0')
                sub_returned = sub_totals['returned'] or Decimal('0')
                subproject.total_budget = subproject_budget
                subproject.remaining_budget = subproject_budget - sub_consumed + sub_returned
                subproject.remaining_percent = (
                    (subproject.remaining_budget / subproject_budget * 100) if subproject_budget > 0 else Decimal('0')
                )
                subproject.total_percent = (
                    (subproject_budget / total_budget * 100) if total_budget > 0 else Decimal('0')
                )

            project_data.append({
                'project': project,
                'total_budget': total_budget,
                'remaining_budget': remaining_budget,
                'remaining_percentage': remaining_percentage
            })

        context.update({
            'budget_period': budget_allocation.budget_period if budget_allocation else None,
            'total_org_budget': total_org_budget,
            'remaining_amount': remaining_amount,
            'remaining_percent': remaining_percent,
            'allocation_total': allocation_total,
            'allocation_remaining': allocation_remaining,
            'allocation_remaining_percent': allocation_remaining_percent,
            'warning_threshold': budget_allocation.warning_threshold if budget_allocation else 50,
            'projects': projects,
            'project_data': project_data,
        })
        logger.debug(f"Context prepared for organization {organization.id}")
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization_id'] = self.kwargs['organization_id']
        kwargs['user'] = self.request.user
        return kwargs

    def form_invalid(self, form):
        logger.error(f"Form errors: {form.errors.as_json()}")
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید.'))
        return self.render_to_response(self.get_context_data(form=form))

    @transaction.atomic
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        try:
            remaining = form.instance.budget_allocation.get_remaining_amount() or Decimal('0')
            if form.instance.allocated_amount > remaining:
                messages.error(self.request, f'مبلغ تخصیص بیشتر از باقی‌مانده بودجه ({remaining:,} ریال) است.')
                return self.form_invalid(form)
            response = super().form_valid(form)
            logger.info(f"New allocation saved: {self.object.pk} - {self.object.allocated_amount}")
            messages.success(self.request, _("تخصیص بودجه با موفقیت ثبت شد"))
            return response
        except Exception as e:
            logger.error(f"Error saving allocation: {str(e)}", exc_info=True)
            messages.error(self.request, _('خطایی در ثبت تخصیص رخ داد.'))
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('project_budget_allocation_list', kwargs={'organization_id': self.kwargs['organization_id']})

    def dispatch(self, request, *args, **kwargs):
        try:
            Organization.objects.get(id=self.kwargs['organization_id'])
        except Organization.DoesNotExist:
            logger.error(f"Organization with id={self.kwargs['organization_id']} not found")
            messages.error(request, _("سازمان موردنظر یافت نشد"))
            return redirect('budgetperiod_list')
        return super().dispatch(request, *args, **kwargs)
#=.......................
"""BudgetAllocationUpdateView داخل فایل دیگه ای """
class ProjectBudgetAllocationDeleteView(PermissionBaseView, DeleteView):
    model = BudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_delete.html'
    context_object_name = 'allocation'

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        budget_allocation = self.object.budget_allocation
        logger.info(f"Allocation {self.object.pk} deleted")
        success_url = self.get_success_url()
        self.object.delete()
        # به‌روزرسانی remaining_amount
        budget_allocation.remaining_amount = budget_allocation.get_remaining_amount()
        budget_allocation.save(update_fields=['remaining_amount'])
        messages.success(self.request, _("تخصیص بودجه با موفقیت حذف شد"))
        from django.shortcuts import redirect
        return redirect(success_url)

    def get_success_url(self):
        return reverse_lazy('project_budget_allocation_list',
                            kwargs={'organization_id': self.object.budget_allocation.organization_id})
# Reports
class ProjectBudgetRealtimeReportView(PermissionBaseView, TemplateView):
    template_name = 'reports/realtime_report.html'
    permission_codenames= 'budgets.budgetallocation_view'
    pass
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization_id = self.request.GET.get('organization_id')
        project_id = self.request.GET.get('project_id')

        organizations = Organization.objects.filter(is_active=True)
        data = []

        for org in organizations:
            if organization_id and org.id != int(organization_id):
                continue
            org_budget = get_organization_budget(org) or Decimal('0')
            org_remaining = sum(
                alloc.get_remaining_amount() for alloc in BudgetAllocation.objects.filter(
                    organization=org, is_active=True
                )
            ) or Decimal('0')
            projects = Project.objects.filter(organizations=org, is_active=True)
            project_data = []

            for project in projects:
                if project_id and project.id != int(project_id):
                    continue
                total_budget = project.get_total_budget() or Decimal('0')
                remaining_budget = project.get_remaining_budget() or Decimal('0')
                transactions = BudgetTransaction.objects.filter(
                    allocation__project_allocations__project=project
                ).order_by('-timestamp')[:10]  # محدود به 10 تراکنش اخیر
                project_data.append({
                    'project': project,
                    'total_budget': total_budget,
                    'remaining_budget': remaining_budget,
                    'allocated_percentage': (
                        (total_budget / org_budget * 100) if org_budget > 0 else Decimal('0')
                    ),
                    'remaining_percentage': (
                        (remaining_budget / total_budget * 100) if total_budget > 0 else Decimal('0')
                    ),
                    'transactions': transactions,
                })

            data.append({
                'organization': org,
                'total_budget': org_budget,
                'remaining_budget': org_remaining,
                'projects': project_data,
            })

        context.update({
            'report_data': data,
            'organizations': organizations,
            'selected_organization': organization_id,
            'selected_project': project_id,
        })
        logger.debug(f"BudgetRealtimeReportView context: {context}")
        return context