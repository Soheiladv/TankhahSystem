# core/views.py
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from core.Branch.forms_branch import BranchForm
from core.PermissionBase import PermissionBaseView
from core.models import Branch
# یک میکس‌این ساده برای مدیریت دسترسی‌ها و لاگین
# این می‌تواند بر اساس PermissionBaseView شما در پروژه واقعی تنظیم شود
# core/views.py
# یا core/Branch/views_branch.py

from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from core.PermissionBase import PermissionBaseView # فرض کنید در core/PermissionBase.py است

# 💡 کلاس پایه جدید برای ویوهای Branch
class BranchBaseMixin(PermissionBaseView): # از PermissionBaseView شما ارث‌بری می‌کند
    # 💡 مشکل اول حل شد: مدل را اینجا تعریف می‌کنیم تا برای همه ویوهای CRUD قابل استفاده باشد
    model = Branch
    success_url = reverse_lazy('branch_list') # به لیست شاخه‌ها برمی‌گردد

# BranchListView
class BranchListView(BranchBaseMixin, ListView):
    template_name = 'core/branch/branch_list.html'
    context_object_name = 'branches'
    # 💡 مجوزها: مطمئن شوید که permission_codenames به درستی ست شده است
    # اگر در PermissionBaseView منطق لازم برای permission_codenames را دارید، نیازی به permission_required نیست
    # در غیر این صورت، از permission_required = 'core.Branch_view' استفاده کنید.
    permission_codenames = 'core.Branch_view'

    def get_queryset(self):
        return Branch.objects.all().order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("لیست شاخه‌های سازمانی")
        return context

# BranchDetailView
class BranchDetailView(BranchBaseMixin, DetailView):
    template_name = 'core/branch/branch_detail.html'
    context_object_name = 'branch'
    permission_codenames = 'core.Branch_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("جزئیات شاخه سازمانی")
        return context

# BranchCreateView
class BranchCreateView(BranchBaseMixin, CreateView):
    template_name = 'core/branch/branch_form.html'
    # 💡 مشکل دوم حل شد: کلاس فرم را مستقیماً ارجاع می‌دهیم
    form_class = BranchForm
    permission_codenames = 'core.Branch_add'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("ایجاد شاخه سازمانی جدید")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("شاخه سازمانی با موفقیت ایجاد شد."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("خطا در ایجاد شاخه سازمانی. لطفا فرم را بررسی کنید."))
        return super().form_invalid(form)

# BranchUpdateView
class BranchUpdateView(BranchBaseMixin, UpdateView):
    template_name = 'core/branch/branch_form.html'
    # 💡 مشکل دوم حل شد: کلاس فرم را مستقیماً ارجاع می‌دهیم
    form_class = BranchForm
    permission_codenames = 'core.Branch_edit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("ویرایش شاخه سازمانی")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("شاخه سازمانی با موفقیت به‌روزرسانی شد."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("خطا در ویرایش شاخه سازمانی. لطفا فرم را بررسی کنید."))
        return super().form_invalid(form)

# BranchDeleteView
class BranchDeleteView(BranchBaseMixin, DeleteView):
    template_name = 'core/branch/branch_confirm_delete.html'
    context_object_name = 'branch'
    permission_codenames = 'core.Branch_delete'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("حذف شاخه سازمانی")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("شاخه سازمانی با موفقیت حذف شد."))
        return super().form_valid(form)