# core/views_workflow.py

from django.views.generic import ListView, CreateView, DetailView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import ListView, CreateView,  DeleteView, TemplateView
from django.urls import reverse_lazy
from core.models import Status

from core.workflow.forms_workflow import StatusForm
class WorkflowDashboardView(TemplateView):
    template_name = 'core/workflow/workFlow_dashboard.html'

# ---------------------------------------------------------------------------------------

# --- Mixin برای کنترل دسترسی ادمین/سوپروایزر ---
class WorkflowAdminRequiredMixin(UserPassesTestMixin):
    """
    این Mixin تضمین می‌کند که فقط سوپریوزر یا کاربران با پرمیشن خاص
    (که می‌توانید تعریف کنید) به این ویوها دسترسی دارند.
    """

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.has_perm('core.add_status')  # مثال

    def handle_no_permission(self):
        messages.error(self.request, _("شما اجازه دسترسی به این بخش را ندارید."))
        return redirect('workflow_dashboard')

# --- ویوهای CRUD برای Status ---

class StatusListView(WorkflowAdminRequiredMixin, ListView):
    model = Status
    template_name = 'core/workflow/Status/status_list.html'
    context_object_name = 'statuses'
    paginate_by = 10

    def get_queryset(self):
        # همیشه فقط رکوردهای فعال را نمایش بده
        queryset = Status.objects.filter(is_active=True).order_by('name')

        # منطق جستجو
        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | Q(code__icontains=search_query)
            )
        return queryset

class StatusCreateView(WorkflowAdminRequiredMixin, CreateView):
    model = Status
    form_class = StatusForm
    template_name = 'core/workflow/Status/status_form.html'
    success_url = reverse_lazy('status_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("ایجاد وضعیت جدید")
        return context

    def form_valid(self, form):
        # کاربر ایجادکننده را به صورت خودکار ست کن
        form.instance.created_by = self.request.user
        messages.success(self.request, _("وضعیت جدید با موفقیت ایجاد شد."))
        return super().form_valid(form)


class StatusUpdateView(WorkflowAdminRequiredMixin, DetailView):
    """
    این ویو برای "ویرایش" استفاده می‌شود، اما در واقع یک فرم ایجاد جدید را
    با داده‌های رکورد قدیمی پر می‌کند تا کاربر یک نسخه جدید ایجاد کند.
    """
    model = Status
    template_name = 'core/workflow/Status/status_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # فرم را با داده‌های شیء فعلی پر می‌کنیم
        form = StatusForm(instance=self.object)
        context['form'] = form
        context['title'] = _(f"ایجاد نسخه جدید از وضعیت: {self.object.name}")
        context['is_update_mode'] = True
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = StatusForm(request.POST)

        if form.is_valid():
            # رکورد جدید را ایجاد کن
            new_instance = form.save(commit=False)
            new_instance.created_by = request.user
            new_instance.save()

            # **منطق کلیدی:** رکورد قدیمی را بازنشسته کن
            self.object.is_active = False
            self.object.save(update_fields=['is_active'])

            messages.success(request, _(f"وضعیت '{self.object.name}' بازنشسته و نسخه جدید ایجاد شد."))
            return redirect('status_list')

        # اگر فرم نامعتبر بود، صفحه را با خطاها نمایش بده
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class StatusDeleteView(WorkflowAdminRequiredMixin, DeleteView):
    model = Status
    template_name = 'core/workflow/Status/confirm_retire.html' # یک تمپلیت عمومی برای تایید بازنشستگی
    success_url = reverse_lazy('status_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _(f"بازنشسته کردن وضعیت: {self.object.name}")
        context['object_type'] = _("وضعیت")
        return context

    def form_valid(self, form):
        # به جای حذف، رکورد را غیرفعال (بازنشسته) می‌کنیم
        self.object.is_active = False
        self.object.save()
        messages.success(self.request, _(f"وضعیت '{self.object.name}' با موفقیت بازنشسته شد."))
        return redirect(self.get_success_url())


# ---------------------------------------------------------------------------------------
### خلاصه نهایی
#
# *   **ما به بیراهه نرفته‌ایم.** ما در حال ساختن یک شالوده **بسیار قوی و استاندارد** هستیم.
# *   **`AccessRule` منسوخ نمی‌شود**، بلکه **تکامل پیدا می‌کند** تا به جای اتصال به مفاهیم مبهم "مرحله"، به "گذارهای" کاملاً مشخص و تعریف شده در فرآیند کسب و کار متصل شود.
# *   با ساختن یک پنل مدیریت CRUD زیبا و راهنما-محور (که نمونه آن را در بالا شروع کردیم)، شما به مدیر سیستم قدرت کامل برای طراحی و تغییر گردش کار را می‌دهید، بدون اینکه نیازی به دخالت شما به عنوان برنامه‌نویس باشد.
#
# اگر این معماری ترکیبی و نقشه راه مورد تأیید شماست، **بریم برای اجرای کامل CRUD و اتصال نهایی آن به ویوهای اصلی برنامه.**