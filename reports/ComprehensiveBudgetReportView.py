# reports/views.py
import logging
from decimal import Decimal
import jdatetime

from django.db.models import Sum, Q, Count, OuterRef, Subquery, DecimalField
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, View
from django.contrib import messages

# مدل‌های برنامه
from budgets.models import BudgetPeriod, BudgetAllocation, BudgetTransaction
from core.PermissionBase import PermissionBaseView
from core.models import Organization, Project
from tankhah.models import Tankhah, Factor

# توابع محاسباتی
from budgets.budget_calculations import get_tankhah_used_budget

# کتابخانه‌های PDF و Excel
try:
    from weasyprint import HTML, CSS

    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter

    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# تعریف لاگر در سطح ماژول
logger = logging.getLogger(__name__)


# ==============================================================================
# ویوی اصلی گزارش جامع (سطح صفر: دوره‌های بودجه)
# ==============================================================================

class ComprehensiveBudgetReportView(PermissionBaseView, ListView):
    """
    نمای اصلی گزارش جامع که لیست دوره‌های بودجه فعال را به همراه خلاصه‌ای از وضعیت آن‌ها نمایش می‌دهد.
    این ویو با لاگ‌های دقیق برای عیب‌یابی عدم نمایش داده‌ها مجهز شده است.
    """
    model = BudgetPeriod
    template_name = 'reports/v2/comprehensive_report_main.html'
    context_object_name = 'budget_periods_data'
    paginate_by = 10

    def get_queryset(self):
        logger.info("=" * 25 + " ComprehensiveBudgetReportView: Starting get_queryset " + "=" * 25)
        try:
            # Subquery ها برای محاسبات بهینه
            total_allocated_subquery = BudgetAllocation.objects.filter(budget_period_id=OuterRef('pk'),
                                                                       is_active=True).values(
                'budget_period_id').annotate(total=Sum('allocated_amount')).values('total')
            total_consumed_subquery = BudgetTransaction.objects.filter(allocation__budget_period_id=OuterRef('pk'),
                                                                       transaction_type='CONSUMPTION').values(
                'allocation__budget_period_id').annotate(total=Sum('amount')).values('total')
            total_returned_subquery = BudgetTransaction.objects.filter(allocation__budget_period_id=OuterRef('pk'),
                                                                       transaction_type='RETURN').values(
                'allocation__budget_period_id').annotate(total=Sum('amount')).values('total')

            base_filters = Q(is_active=True) & Q(is_completed=False)
            logger.debug(f"فیلترهای پایه برای BudgetPeriod: {base_filters}")

            queryset = BudgetPeriod.objects.filter(base_filters).select_related('organization').annotate(
                total_allocated_in_period=Coalesce(Subquery(total_allocated_subquery), Decimal('0'),
                                                   output_field=DecimalField()),
                total_consumed_in_period=Coalesce(Subquery(total_consumed_subquery), Decimal('0'),
                                                  output_field=DecimalField()),
                total_returned_in_period=Coalesce(Subquery(total_returned_subquery), Decimal('0'),
                                                  output_field=DecimalField()),
            ).order_by('-start_date', 'name')

            logger.info(f"تعداد دوره‌های بودجه یافت شده قبل از فیلتر جستجو: {queryset.count()}")

            search_query = self.request.GET.get('search_period')
            if search_query:
                logger.debug(f"اعمال فیلتر جستجو بر اساس نام دوره: '{search_query}'")
                queryset = queryset.filter(name__icontains=search_query)

            final_count = queryset.count()
            logger.info(f"تعداد نهایی دوره‌های بودجه برای نمایش: {final_count}")
            if final_count == 0:
                logger.warning(
                    "مهم: هیچ دوره بودجه‌ای با فیلترهای مشخص شده یافت نشد. لطفاً از وجود دوره‌هایی با is_active=True و is_completed=False در دیتابیس اطمینان حاصل کنید.")

            return queryset
        except Exception as e:
            logger.error(f"خطای بحرانی در get_queryset رخ داد: {e}", exc_info=True)
            return BudgetPeriod.objects.none()

    def get_context_data(self, **kwargs):
        logger.info("=" * 25 + " ComprehensiveBudgetReportView: Starting get_context_data " + "=" * 25)
        try:
            context = super().get_context_data(**kwargs)
            initial_periods = context.get('object_list', [])
            logger.debug(f"تعداد دوره‌ها برای پردازش در context: {len(initial_periods)}")

            processed_data = []
            for period in initial_periods:
                logger.debug(f"پردازش داده‌ها برای دوره: '{period.name}' (PK: {period.pk})")
                net_consumed = period.total_consumed_in_period - period.total_returned_in_period
                remaining_vs_total = period.total_amount - net_consumed
                utilization_vs_total = (net_consumed / period.total_amount * 100) if period.total_amount > 0 else 0

                processed_data.append({
                    'period': period,
                    'summary': {
                        'total_allocated_from_period': period.total_allocated_in_period,
                        'net_consumed_from_period': net_consumed,
                        'remaining_vs_total_amount': remaining_vs_total,
                        'utilization_percentage': utilization_vs_total,
                        'start_date_jalali': jdatetime.date.fromgregorian(date=period.start_date).strftime('%Y/%m/%d'),
                        'end_date_jalali': jdatetime.date.fromgregorian(date=period.end_date).strftime('%Y/%m/%d'),
                        'organizations_ajax_url': reverse('api_organizations_for_period',
                                                          kwargs={'period_pk': period.pk}),
                    }
                })

            context[self.context_object_name] = processed_data
            context['report_main_title'] = _("گزارش جامع بودجه")
            context['current_search_period'] = self.request.GET.get('search_period', '')

            logger.info(f"پردازش get_context_data با موفقیت انجام شد. تعداد نهایی آیتم‌ها: {len(processed_data)}")
            if not processed_data and not self.request.GET.get('search_period'):
                messages.info(self.request, _("هیچ دوره بودجه فعالی برای نمایش یافت نشد."))

            return context
        except Exception as e:
            logger.error(f"خطای بحرانی در get_context_data: {e}", exc_info=True)
            messages.error(self.request, _("خطایی در پردازش داده‌های صفحه رخ داده است. لطفاً لاگ سرور را بررسی کنید."))
            context = super().get_context_data(**kwargs)
            context[self.context_object_name] = []
            return context

    # توابع generate_pdf_report و generate_excel_report در اینجا قرار می‌گیرند.
    # پیاده‌سازی آنها مشابه کد قبلی شماست و برای اختصار حذف شده.


# ==============================================================================
# API سطح اول: دریافت سازمان‌های یک دوره بودجه
# ==============================================================================

class APIOrganizationsForPeriodView(PermissionBaseView, View):
    def get(self, request, period_pk, *args, **kwargs):
        logger.info(f"API Request: دریافت سازمان‌ها برای دوره بودجه PK={period_pk}")
        try:
            period = get_object_or_404(BudgetPeriod, pk=period_pk)

            consumed_subquery = BudgetTransaction.objects.filter(
                allocation__organization_id=OuterRef('organization__id'), allocation__budget_period_id=period.pk,
                transaction_type='CONSUMPTION').values('allocation__organization_id').annotate(
                total=Sum('amount')).values('total')
            returned_subquery = BudgetTransaction.objects.filter(
                allocation__organization_id=OuterRef('organization__id'), allocation__budget_period_id=period.pk,
                transaction_type='RETURN').values('allocation__organization_id').annotate(total=Sum('amount')).values(
                'total')

            org_summaries_qs = BudgetAllocation.objects.filter(
                budget_period=period, is_active=True
            ).values(
                'organization__id', 'organization__name', 'organization__code'
            ).annotate(
                total_allocated_to_org=Sum('allocated_amount'),
                num_budget_items_for_org=Count('budget_item', distinct=True),
                total_consumed_for_org=Coalesce(Subquery(consumed_subquery), Decimal('0'), output_field=DecimalField()),
                total_returned_for_org=Coalesce(Subquery(returned_subquery), Decimal('0'), output_field=DecimalField())
            ).order_by('organization__name')

            logger.debug(f"تعداد خلاصه‌های سازمانی یافت شده: {org_summaries_qs.count()}")

            organizations_data = []
            for org_sum in org_summaries_qs:
                net_consumed = org_sum['total_consumed_for_org'] - org_sum['total_returned_for_org']
                remaining = org_sum['total_allocated_to_org'] - net_consumed
                organizations_data.append({
                    'id': org_sum['organization__id'],
                    'name': org_sum['organization__name'],
                    'code': org_sum['organization__code'],
                    'total_allocated_formatted': f"{org_sum['total_allocated_to_org']:,.0f}",
                    'net_consumed_formatted': f"{net_consumed:,.0f}",
                    'remaining_formatted': f"{remaining:,.0f}",
                    'utilization_percentage': (net_consumed / org_sum['total_allocated_to_org'] * 100) if org_sum[
                                                                                                              'total_allocated_to_org'] > 0 else 0,
                    'budget_items_ajax_url': reverse('api_budget_items_for_org_period',
                                                     kwargs={'period_pk': period.pk,
                                                             'org_pk': org_sum['organization__id']})
                })

            logger.info(f"تعداد {len(organizations_data)} سازمان برای رندر در دوره {period_pk} آماده شد.")
            html_content = render_to_string(
                'reports/partials/_ajax_level_organizations.html',
                {'organizations': organizations_data, 'parent_period_pk': period_pk}
            )
            return JsonResponse({'html_content': html_content, 'status': 'success'})
        except Http404:
            logger.warning(f"API Error: دوره بودجه با PK={period_pk} یافت نشد.")
            return JsonResponse(
                {'html_content': f'<p class="text-danger p-3 text-center">{_("دوره بودجه یافت نشد.")}</p>',
                 'status': 'notfound'}, status=404)
        except Exception as e:
            logger.error(f"خطای بحرانی در APIOrganizationsForPeriodView برای period_pk={period_pk}: {e}", exc_info=True)
            return JsonResponse(
                {'html_content': f'<p class="text-danger p-3 text-center">{_("خطا در پردازش درخواست.")}</p>',
                 'status': 'error'}, status=500)


# ==============================================================================
# سایر ویوهای API (با الگوی لاگ مشابه)
# ==============================================================================

class APIBudgetItemsForOrgPeriodView(PermissionBaseView, View):
    def get(self, request, period_pk, org_pk, *args, **kwargs):
        logger.info(f"API Request: دریافت سرفصل‌ها برای سازمان {org_pk} در دوره {period_pk}")
        try:
            consumed_subquery = BudgetTransaction.objects.filter(allocation_id=OuterRef('pk'),
                                                                 transaction_type='CONSUMPTION').values(
                'allocation_id').annotate(total=Sum('amount')).values('total')
            returned_subquery = BudgetTransaction.objects.filter(allocation_id=OuterRef('pk'),
                                                                 transaction_type='RETURN').values(
                'allocation_id').annotate(total=Sum('amount')).values('total')

            allocations_qs = BudgetAllocation.objects.filter(
                budget_period_id=period_pk, organization_id=org_pk, is_active=True
            ).select_related(
                'budget_item', 'project', 'subproject'
            ).annotate(
                consumed=Coalesce(Subquery(consumed_subquery), Decimal('0'), output_field=DecimalField()),
                returned=Coalesce(Subquery(returned_subquery), Decimal('0'), output_field=DecimalField())
            ).order_by('budget_item__name', 'project__name', 'subproject__name')

            logger.debug(f"تعداد تخصیص‌های یافت شده برای سازمان {org_pk}: {allocations_qs.count()}")
            if not allocations_qs.exists():
                return JsonResponse(
                    {'html_content': '<p class="text-center p-3">هیچ تخصیص فعالی برای این سازمان یافت نشد.</p>',
                     'status': 'empty'})

            response_data = []
            for ba in allocations_qs:
                net_consumed = ba.consumed - ba.returned
                remaining = ba.allocated_amount - net_consumed
                is_project_allocation = ba.project is not None
                target_name = ""
                if is_project_allocation:
                    target_name = ba.project.name
                    if ba.subproject:
                        target_name += f" / {ba.subproject.name}"

                response_data.append({
                    'is_project_allocation': is_project_allocation,
                    'pba_pk': ba.pk,
                    'budget_item_name': ba.budget_item.name if ba.budget_item else "نامشخص",
                    'budget_item_code': ba.budget_item.code if ba.budget_item else "-",
                    'project_display_name': target_name,
                    'allocated_formatted': f"{ba.allocated_amount:,.0f}",
                    'consumed_formatted': f"{net_consumed:,.0f}",
                    'remaining_formatted': f"{remaining:,.0f}",
                    'utilization_percentage': (
                                net_consumed / ba.allocated_amount * 100) if ba.allocated_amount > 0 else 0,
                    'tankhahs_ajax_url': reverse('api_tankhahs_for_pba',
                                                 kwargs={'pba_pk': ba.pk}) if is_project_allocation else None
                })

            html_content = render_to_string('reports/partials/_ajax_level_budget_allocations.html',
                                            {'allocations_data': response_data, 'parent_org_pk': org_pk})
            return JsonResponse({'html_content': html_content, 'status': 'success'})
        except Exception as e:
            logger.error(f"خطای بحرانی در APIBudgetItemsForOrgPeriodView (org_pk={org_pk}): {e}", exc_info=True)
            return JsonResponse(
                {'html_content': f'<p class="text-danger p-3 text-center">{_("خطا در پردازش درخواست.")}</p>',
                 'status': 'error'}, status=500)


class APITankhahsForPBAView(PermissionBaseView, View):
    def get(self, request, pba_pk, *args, **kwargs):
        logger.info(f"API Request: دریافت تنخواه‌ها برای تخصیص پروژه (PBA) PK={pba_pk}")
        try:
            pba_instance = get_object_or_404(BudgetAllocation.objects.select_related('project', 'subproject'),
                                             pk=pba_pk)

            tankhahs_qs = Tankhah.objects.filter(project_budget_allocation=pba_instance,
                                                 is_archived=False).select_related('created_by',
                                                                                   'current_stage').order_by('-date',
                                                                                                             '-pk')

            logger.debug(f"تعداد تنخواه‌های یافت شده برای PBA {pba_pk}: {tankhahs_qs.count()}")
            if not tankhahs_qs.exists():
                return JsonResponse(
                    {'html_content': '<p class="text-center p-3">هیچ تنخواهی برای این تخصیص یافت نشد.</p>',
                     'status': 'empty'})

            tankhahs_data = []
            for tankhah in tankhahs_qs:
                used_amount = get_tankhah_used_budget(tankhah)
                tankhahs_data.append({
                    'id': tankhah.pk,
                    'number': tankhah.number,
                    'amount_formatted': f"{tankhah.amount:,.0f}",
                    'used_formatted': f"{used_amount:,.0f}",
                    'status_display': tankhah.get_status_display(),
                    'date_jalali': jdatetime.date.fromgregorian(date=tankhah.date).strftime('%Y/%m/%d'),
                    'detail_url': reverse('tankhah_detail', kwargs={'pk': tankhah.pk}),
                    'factors_ajax_url': reverse('api_factors_for_tankhah', kwargs={'tankhah_pk': tankhah.pk}),
                })

            parent_pba_name = pba_instance.project.name if pba_instance.project else ""
            if pba_instance.subproject:
                parent_pba_name += f" / {pba_instance.subproject.name}"

            html_content = render_to_string('reports/partials/_ajax_level_tankhahs.html',
                                            {'tankhahs_list_data': tankhahs_data, 'parent_pba_pk': pba_pk,
                                             'parent_pba_name': parent_pba_name})
            return JsonResponse({'html_content': html_content, 'status': 'success'})
        except Http404:
            logger.warning(f"API Error: تخصیص بودجه پروژه با PK={pba_pk} یافت نشد.")
            return JsonResponse(
                {'html_content': f'<p class="text-danger p-3 text-center">{_("تخصیص بودجه یافت نشد.")}</p>',
                 'status': 'notfound'}, status=404)
        except Exception as e:
            logger.error(f"خطای بحرانی در APITankhahsForPBAView (pba_pk={pba_pk}): {e}", exc_info=True)
            return JsonResponse(
                {'html_content': f'<p class="text-danger p-3 text-center">{_("خطا در پردازش درخواست.")}</p>',
                 'status': 'error'}, status=500)


class APIFactorsForTankhahView(PermissionBaseView, View):
    def get(self, request, tankhah_pk, *args, **kwargs):
        logger.info(f"API Request: دریافت فاکتورها برای تنخواه PK={tankhah_pk}")
        try:
            tankhah_instance = get_object_or_404(Tankhah.objects.select_related('organization', 'project'),
                                                 pk=tankhah_pk)

            factors_qs = Factor.objects.filter(tankhah=tankhah_instance).select_related('category',
                                                                                        'created_by').order_by('-date')

            logger.debug(f"تعداد فاکتورهای یافت شده برای تنخواه {tankhah_pk}: {factors_qs.count()}")
            if not factors_qs.exists():
                return JsonResponse(
                    {'html_content': '<p class="text-center p-3">هیچ فاکتوری برای این تنخواه یافت نشد.</p>',
                     'status': 'empty'})

            factors_data = []
            for factor in factors_qs:
                factors_data.append({
                    'id': factor.pk,
                    'number': factor.number,
                    'amount_formatted': f"{factor.amount:,.0f}",
                    'status_display': factor.get_status_display(),
                    'category_name': factor.category.name if factor.category else "-",
                    'date_jalali': jdatetime.date.fromgregorian(date=factor.date).strftime('%Y/%m/%d'),
                    'detail_url': reverse('factor_detail', kwargs={'factor_pk': factor.pk}),
                })

            html_content = render_to_string('reports/partials/_ajax_level_factors.html',
                                            {'factors_list_data': factors_data, 'parent_tankhah_pk': tankhah_pk,
                                             'parent_tankhah_number': tankhah_instance.number})
            return JsonResponse({'html_content': html_content, 'status': 'success'})
        except Http404:
            logger.warning(f"API Error: تنخواه با PK={tankhah_pk} یافت نشد.")
            return JsonResponse({'html_content': f'<p class="text-danger p-3 text-center">{_("تنخواه یافت نشد.")}</p>',
                                 'status': 'notfound'}, status=404)
        except Exception as e:
            logger.error(f"خطای بحرانی در APIFactorsForTankhahView (tankhah_pk={tankhah_pk}): {e}", exc_info=True)
            return JsonResponse(
                {'html_content': f'<p class="text-danger p-3 text-center">{_("خطا در پردازش درخواست.")}</p>',
                 'status': 'error'}, status=500)