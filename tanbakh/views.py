import jdatetime
from django.shortcuts import redirect
from django.views.generic import ListView, DetailView, CreateView, DeleteView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.contrib import messages

from core.models import UserPost
from .forms import TanbakhForm, FactorItemFormSet
from .models import Tanbakh, Factor
from django.utils.translation import gettext_lazy as _


class TanbakhListView(LoginRequiredMixin, ListView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_list.html'
    context_object_name = 'tanbakhs'
    queryset = Tanbakh.objects.filter(organization__org_type='COMPLEX')
    paginate_by = 10
    extra_context = {'title': _('لیست تنخواه‌ها')}

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(number__icontains=query) |
                Q(organization__name__icontains=query) |
                Q(project__name__icontains=query) |
                Q(status__icontains=query) |
                Q(letter_number__icontains=query)
            )
            if not queryset.exists():
                messages.info(self.request, _('هیچ تنخواهی با این مشخصات یافت نشد.'))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context

import jdatetime
class TanbakhDetailView(LoginRequiredMixin, DetailView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_detail.html'
    context_object_name = 'tanbakh'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['factors'] = self.object.factors.all()
        context['title'] = _('جزئیات تنخواه') + f" - {self.object.number}"
        context['approvals'] = self.object.approvals.all().order_by('date')
        # تاریخ فعلی برای چاپ
        context['current_date'] = jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M')
        # تبدیل تاریخ‌ها به شمسی
        if self.object.date:
            context['jalali_date'] = jdatetime.date.fromgregorian(date=self.object.date).strftime('%Y/%m/%d %H:%M')
        for factor in context['factors']:
            factor.jalali_date = jdatetime.date.fromgregorian(date=factor.date).strftime('%Y/%m/%d %H:%M')
        for approval in context['approvals']:
            approval.jalali_date = jdatetime.datetime.fromgregorian(datetime=approval.date).strftime('%Y/%m/%d %H:%M')
        return context


class TanbakhCreateView(LoginRequiredMixin, CreateView):
    model = Tanbakh
    form_class = TanbakhForm
    template_name = 'tanbakh/tanbakh_form.html'
    # fields = ['date', 'organization', 'project', 'status', 'hq_status', 'last_stopped_post', 'letter_number', 'approved_by']
    success_url = reverse_lazy('tanbakh_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user  # ثبت کاربر فعلی به عنوان ایجادکننده
        messages.success(self.request, _('تنخواه با موفقیت ایجاد شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد تنخواه جدید')
        return context

class TanbakhDeleteView(LoginRequiredMixin, DeleteView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_confirm_delete.html'
    success_url = reverse_lazy('tanbakh_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تنخواه با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)
#ویو تأیید:
class TanbakhApproveView(PermissionRequiredMixin, UpdateView):
    model = Tanbakh
    fields = []  # هیچ فیلدی برای ویرایش دستی نیست
    template_name = 'tanbakh/tanbakh_approve.html'
    permission_required = 'tanbakh.can_approve_tanbakh'

    def form_valid(self, form):
        # سیستم به‌صورت خودکار وضعیت را تغییر می‌دهد
        self.object.status = 'APPROVED'
        self.object.save()
        messages.success(self.request, 'تنخواه با موفقیت تأیید👍 شد.')
        return super().form_valid(form)
#ویو رد
class TanbakhRejectView(PermissionRequiredMixin, UpdateView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_reject.html'
    permission_required = 'tanbakh.can_reject_tanbakh'

    def form_valid(self, form):
        # سیستم به‌صورت خودکار وضعیت را تغییر می‌دهد
        self.object.status = 'REJECTED'
        self.object.save()
        messages.success(self.request, 'تنخواه با موفقیت رد👎 شد.')
        return super().form_valid(form)

###########################################
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Factor, Approval
from .forms import FactorForm, ApprovalForm
from django.utils.translation import gettext_lazy as _
#---
from django.views.generic import TemplateView
from .forms import FactorForm, FactorItemFormSet


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'tanbakh/tanbakh_dashboard.html'
    extra_context = {'title': _('داشبورد مدیریت تنخواه')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # لینک‌ها بر اساس پرمیشن‌ها
        context['links'] = {
            'tanbakh': [
                {'url': 'tanbakh_list', 'label': _('لیست تنخواه‌ها'), 'icon': 'fas fa-list',
                 'perm': 'tanbakh.Tanbakh_view'},
                {'url': 'tanbakh_create', 'label': _('ایجاد تنخواه'), 'icon': 'fas fa-plus',
                 'perm': 'tanbakh.Tanbakh_add'},
            ],
            'factor': [
                {'url': 'factor_list', 'label': _('لیست فاکتورها'), 'icon': 'fas fa-file-invoice',
                 'perm': 'tanbakh.Factor_view'},
                {'url': 'factor_create', 'label': _('ایجاد فاکتور'), 'icon': 'fas fa-plus',
                 'perm': 'tanbakh.Factor_add'},
            ],
            'approval': [
                {'url': 'approval_list', 'label': _('لیست تأییدات'), 'icon': 'fas fa-check-circle',
                 'perm': 'tanbakh.Approval_view'},
                {'url': 'approval_create', 'label': _('ثبت تأیید'), 'icon': 'fas fa-plus',
                 'perm': 'tanbakh.Approval_add'},
            ],
        }

        # فیلتر کردن لینک‌ها بر اساس دسترسی کاربر
        for section in context['links']:
            context['links'][section] = [link for link in context['links'][section] if user.has_perm(link['perm'])]

        return context

# --- Factor Views ---
class FactorListView(LoginRequiredMixin, ListView):
    model = Factor
    template_name = 'tanbakh/factor_list.html'
    context_object_name = 'factors'
    paginate_by = 10
    extra_context = {'title': _('لیست فاکتورها')}

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(number__icontains=query) | \
                       queryset.filter(tanbakh__number__icontains=query)
        return queryset

class FactorDetailView(LoginRequiredMixin, DetailView):
    model = Factor
    template_name = 'tanbakh/factor_detail.html'
    context_object_name = 'factor'
    extra_context = {'title': _('جزئیات فاکتور')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all()
        context['title'] = _('جزئیات فاکتور') + f" - {self.object.number}"
        return context

class FactorCreateView(LoginRequiredMixin, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tanbakh/factor_form.html'
    success_url = reverse_lazy('factor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES)
        else:
            context['item_formset'] = FactorItemFormSet()
        context['title'] = _('ایجاد فاکتور جدید')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        if item_formset.is_valid():
            self.object = form.save()  # ابتدا فاکتور را ذخیره می‌کنیم
            item_formset.instance = self.object  # اقلام را به فاکتور متصل می‌کنیم
            item_formset.save()  # اقلام را ذخیره می‌کنیم
            messages.success(self.request, _('فاکتور و اقلام آن با موفقیت ثبت شدند.'))
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('لطفاً خطاهای فرم را برطرف کنید.'))
        return super().form_invalid(form)

class FactorUpdateView(LoginRequiredMixin, UpdateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tanbakh/factor_form.html'
    success_url = reverse_lazy('factor_list')

    def get(self, request, *args, **kwargs):
        factor = self.get_object()
        # فقط رده‌های پایین‌تر از 2 اجازه ویرایش دارند
        user_post = UserPost.objects.filter(user=request.user).first()
        if user_post and user_post.post.level > 2:
            messages.error(request, _('شما اجازه ویرایش این فاکتور را ندارید.'))
            return redirect('factor_list')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context['item_formset'] = FactorItemFormSet(instance=self.object)
        context['title'] = _('ویرایش فاکتور') + f" - {self.object.number}"
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        if item_formset.is_valid():
            self.object = form.save()  # فاکتور را ذخیره می‌کنیم
            item_formset.instance = self.object  # اقلام را به فاکتور متصل می‌کنیم
            item_formset.save()  # اقلام را ذخیره می‌کنیم
            messages.success(self.request, _('فاکتور و اقلام آن با موفقیت به‌روزرسانی شدند.'))
            return super().form_valid(form)
        else:
            messages.error(self.request, _('لطفاً خطاهای اقلام فاکتور را برطرف کنید.'))
            return self.form_invalid(form)

class FactorDeleteView(LoginRequiredMixin, DeleteView):
    model = Factor
    template_name = 'tanbakh/factor_confirm_delete.html'
    success_url = reverse_lazy('factor_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('فاکتور با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)

# --- Approval Views ---
class ApprovalListView(LoginRequiredMixin, ListView):
    model = Approval
    template_name = 'tanbakh/approval_list.html'
    context_object_name = 'approvals'
    paginate_by = 10
    extra_context = {'title': _('لیست تأییدات')}

class ApprovalDetailView(LoginRequiredMixin, DetailView):
    model = Approval
    template_name = 'tanbakh/approval_detail.html'
    context_object_name = 'approval'
    extra_context = {'title': _('جزئیات تأیید')}

class ApprovalCreateView(PermissionRequiredMixin, CreateView):
    model = Approval
    form_class = ApprovalForm
    template_name = 'tanbakh/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'tanbakh.Approval_add'

    def form_valid(self, form):
        form.instance.user = self.request.user
        user_post = UserPost.objects.filter(user=self.request.user).first()
        user_level = user_post.post.level if user_post else 0

        if form.instance.tanbakh:
            tanbakh = form.instance.tanbakh
            current_status = tanbakh.status
            branch = form.instance.branch

            # بررسی مرحله فعلی (اگر current_stage وجود داشته باشد)
            if hasattr(tanbakh, 'current_stage') and branch != tanbakh.current_stage:
                messages.error(self.request, _('شما نمی‌توانید در این مرحله تأیید کنید.'))
                return self.form_invalid(form)

            if form.instance.is_approved:
                if branch == 'COMPLEX' and current_status == 'PENDING' and user_level <= 2:
                    tanbakh.status = 'APPROVED'
                    tanbakh.hq_status = 'SENT_TO_HQ'
                    if hasattr(tanbakh, 'current_stage'):
                        tanbakh.current_stage = 'OPS'
                elif branch == 'OPS' and current_status == 'APPROVED' and user_level > 2:
                    tanbakh.hq_status = 'HQ_OPS_APPROVED'
                    if hasattr(tanbakh, 'current_stage'):
                        tanbakh.current_stage = 'FIN'
                elif branch == 'FIN' and tanbakh.hq_status == 'HQ_OPS_APPROVED' and user_level > 3:
                    tanbakh.hq_status = 'HQ_FIN_PENDING'
                    tanbakh.status = 'PAID'
                    if hasattr(tanbakh, 'current_stage'):
                        tanbakh.current_stage = 'FIN'  # پایان جریان
                else:
                    messages.error(self.request, _('شما اجازه تأیید در این مرحله را ندارید یا وضعیت نادرست است.'))
                    return self.form_invalid(form)
            else:
                tanbakh.status = 'REJECTED'
            tanbakh.last_stopped_post = user_post.post if user_post else None
            tanbakh.save()

        elif form.instance.factor:
            factor = form.instance.factor
            factor.status = 'APPROVED' if form.instance.is_approved else 'REJECTED'
            factor.save()

        elif form.instance.factor_item:
            item = form.instance.factor_item
            # اگر FactorItem فیلد status داشته باشد
            if hasattr(item, 'status'):
                item.status = 'APPROVED' if form.instance.is_approved else 'REJECTED'
                item.save()
            else:
                messages.warning(self.request, _('ردیف فاکتور فاقد وضعیت است و تأیید اعمال نشد.'))

        messages.success(self.request, _('تأیید با موفقیت ثبت شد.'))
        return super().form_valid(form)

    def get_initial(self):
        initial = super().get_initial()
        initial['tanbakh'] = self.request.GET.get('tanbakh')
        initial['factor'] = self.request.GET.get('factor')
        initial['factor_item'] = self.request.GET.get('factor_item')
        return initial

class ApprovalUpdateView(PermissionRequiredMixin, UpdateView):
    model = Approval
    form_class = ApprovalForm
    template_name = 'tanbakh/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'tanbakh.Approval_update'

    def form_valid(self, form):
        messages.success(self.request, _('تأیید با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

class ApprovalDeleteView(PermissionRequiredMixin, DeleteView):
    model = Approval
    template_name = 'tanbakh/approval_confirm_delete.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'tanbakh.Approval_delete'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تأیید با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)