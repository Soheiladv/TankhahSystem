from django.contrib import messages
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.utils.translation import gettext_lazy as _

from core.PermissionBase import PermissionBaseView
from core.models import Action
from core.workflow.forms_workflow import ActionForm, TransitionForm
from core.workflow.views_workflow import WorkflowAdminRequiredMixin
from core.models import Transition
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, ListView, CreateView, DeleteView
import logging
logger = logging.getLogger('TransitionLogger')
class TransitionListView(PermissionBaseView, ListView):
    model = Transition
    template_name = 'core/workflow/Transition/transition_list.html'
    context_object_name = 'transitions'
    paginate_by = 10

    def get_queryset(self):
        queryset = Transition.objects.filter(is_active=True).select_related(
            'from_status', 'action', 'to_status'
        ).order_by('entity_type', 'from_status__name')

        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset


class TransitionCreateView(PermissionBaseView, CreateView):
    model = Transition
    form_class = TransitionForm
    template_name = 'core/workflow/Transition/transition_form.html'
    success_url = reverse_lazy('transition_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("ایجاد گذار جدید در گردش کار")
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("گذار جدید با موفقیت ایجاد شد."))
        return super().form_valid(form)


class TransitionUpdateView(PermissionBaseView, View):
    """
    ویوی نهایی برای ویرایش یک گذار با منطق "ایجاد نسخه جدید".
    این نسخه مشکل لود نشدن مقادیر ManyToMany را حل می‌کند.
    """
    form_class = TransitionForm
    template_name = 'core/workflow/Transition/transition_form.html'
    permission_codenames = ['core.transition_change']

    def get_object(self, pk):
        """متد کمکی برای گرفتن شیء گذار قدیمی."""
        return get_object_or_404(Transition, pk=pk)

    def get(self, request, *args, **kwargs):
        """
        پردازش درخواست GET:
        فرم را با داده‌های گذار قدیمی پر کرده و به کاربر نمایش می‌دهد.
        """
        old_transition = self.get_object(self.kwargs['pk'])
        # **بدون تغییر:** این بخش به درستی فرم را با مقادیر اولیه پر می‌کند.
        form = self.form_class(instance=old_transition)

        context = {
            'form': form,
            'title': _(f"ایجاد نسخه جدید از گذار: {old_transition.name}"),
            'is_update_mode': True,
            'object': old_transition,  # از object برای سازگاری با تمپلیت استفاده می‌کنیم
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        پردازش درخواست POST:
        ۱. داده‌های فرم را اعتبارسنجی می‌کند.
        ۲. یک گذار "جدید" با داده‌های فرم ایجاد می‌کند.
        ۳. گذار "قدیمی" را غیرفعال (بازنشسته) می‌کند.
        """
        old_transition = self.get_object(self.kwargs['pk'])

        # **اصلاح کلیدی و نهایی:**
        # ما فرم را با داده‌های POST و همچنین instance قدیمی مقداردهی می‌کنیم.
        # این کار به جنگو کمک می‌کند تا بفهمد کدام فیلدها (از جمله ManyToMany) تغییر کرده‌اند.
        form = self.form_class(request.POST, instance=old_transition)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # مرحله ۱: ایجاد و ذخیره گذار جدید
                    # ما یک شیء جدید از روی داده‌های فرم معتبر می‌سازیم.
                    new_transition = Transition(
                        name=form.cleaned_data['name'],
                        organization=form.cleaned_data['organization'],
                        entity_type=form.cleaned_data['entity_type'],
                        from_status=form.cleaned_data['from_status'],
                        action=form.cleaned_data['action'],
                        to_status=form.cleaned_data['to_status'],
                        is_active=form.cleaned_data.get('is_active', True),  # مقدار is_active جدید را می‌گیریم
                        created_by=request.user
                    )
                    new_transition.save()  # ذخیره اولیه برای گرفتن PK

                    # مقادیر ManyToMany را به شیء جدید اضافه می‌کنیم
                    new_transition.allowed_posts.set(form.cleaned_data['allowed_posts'])

                    # مرحله ۲: بازنشسته کردن گذار قدیمی
                    old_transition.is_active = False
                    old_transition.save(update_fields=['is_active'])

                    messages.success(request, _(f"گذار '{old_transition.name}' با موفقیت به‌روزرسانی شد."))
                    return redirect('transition_list')

            except Exception as e:
                messages.error(request, _("خطایی در هنگام ذخیره‌سازی رخ داد."))
                logger.error(f"Error in TransitionUpdateView POST: {e}", exc_info=True)

        # اگر فرم نامعتبر بود، دوباره صفحه را با همان فرم و خطاها نمایش بده
        context = {
            'form': form,  # فرم نامعتبر را به تمپلیت پاس می‌دهیم تا خطاها نمایش داده شوند
            'title': _(f"ایجاد نسخه جدید از گذار: {old_transition.name}"),
            'is_update_mode': True,
            'object': old_transition
        }
        return render(request, self.template_name, context)



class TransitionDeleteView(PermissionBaseView, DeleteView):
    """
    ویو برای حذف یک گذار گردش کار.
    این ویو ابتدا یک صفحه تأیید به کاربر نمایش می‌دهد تا از حذف تصادفی جلوگیری شود.
    """
    model = Transition
    template_name = 'core/workflow/Transition/transition_confirm_delete.html'
    success_url = reverse_lazy('transition_list')  # پس از حذف موفق، به لیست گذارها برگرد
    permission_codenames = ['core.transition_delete']
    context_object_name = 'transition'  # نام شیء در تمپلیت

    def get_context_data(self, **kwargs):
        """
        اطلاعات اضافی را برای نمایش در صفحه تأیید، به کانتکست اضافه می‌کند.
        """
        context = super().get_context_data(**kwargs)
        context['title'] = _(f"تأیید حذف گذار: {self.object.name}")
        return context

    def form_valid(self, form):
        """
        این متد پس از اینکه کاربر روی دکمه "تأیید حذف" کلیک کرد، اجرا می‌شود.
        """
        transition_name = self.object.name
        logger.warning(
            f"User '{self.request.user.username}' is deleting Transition '{transition_name}' (PK: {self.object.pk}).")

        # فراخوانی متد حذف اصلی
        response = super().form_valid(form)

        # نمایش پیغام موفقیت‌آمیز به کاربر
        messages.success(self.request, _(f"گذار '{transition_name}' با موفقیت حذف شد."))

        return response
