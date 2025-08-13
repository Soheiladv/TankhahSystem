# ===== view_Nfactor.py (ادامه فایل) =====

# --- import های اضافی مورد نیاز برای این ویو ---
from django.views import View
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.db import transaction

# ===== IMPORTS =====
import logging
from django.views.generic import DetailView, UpdateView, FormView, TemplateView
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

# --- مدل‌ها و کلاس‌های مورد نیاز ---
from core.PermissionBase import PermissionBaseView
from tankhah.models import Factor, ApprovalLog, FactorHistory, FactorItem
from core.models import Transition, Action  # <--- مدل کلیدی گردش کار

logger = logging.getLogger('PerformFactorActionView')  # لاگر مخصوص
from core.PermissionBase import PermissionBaseView
from tankhah.Factor.Approved.forms import FactorItemApprovalFormSet, ItemActionForm


class FactorApprovalView(PermissionBaseView, TemplateView):
    """
    **ویوی نهایی و یکپارچه:**
    این ویو به عنوان یک داشبورد کامل برای مشاهده و اقدام روی ردیف‌های فاکتور عمل می‌کند.
    """
    template_name = 'tankhah/Approved/factor_approval_new.html'
    permission_required = 'tankhah.factor_approve'

    def get_context_data(self, **kwargs):
        """
        داده‌های لازم برای تمپلیت را آماده می‌کند، از جمله ساختن لیست فرم‌ها.
        """
        # کامنت: ابتدا context پیش‌فرض را می‌گیریم.
        context = super().get_context_data(**kwargs)
        # کامنت: فاکتور و کاربر را یک بار از URL و درخواست استخراج می‌کنیم.
        factor = get_object_or_404(Factor, pk=self.kwargs['pk'])
        user = self.request.user

        logger.debug(f"[FactorApprovalView:GET] Preparing context for Factor PK {factor.pk}")

        context['factor'] = factor
        context['title'] = _('بررسی و اقدام فاکتور') + f" #{factor.number}"

        # کامنت: برای هر ردیف فاکتور، یک فرم اقدام مجزا می‌سازیم.
        item_forms = [
            ItemActionForm(prefix=f"item_{item.pk}", item=item, user=user, factor=factor)
            for item in factor.items.all()
        ]
        context['item_forms'] = item_forms

        context['approval_history'] = ApprovalLog.objects.filter(factor=factor).order_by('-timestamp').select_related(
            'user', 'post', 'action')
        return context

    def post(self, request, *args, **kwargs):
        """
        منطق اصلی پردازش تمام فرم‌های ارسال شده.
        """
        factor = get_object_or_404(Factor, pk=self.kwargs['pk'])
        user = request.user
        logger.info(f"[FactorApprovalView:POST] Received POST for Factor PK {factor.pk} from User '{user.username}'.")

        # کامنت: فرم‌ها را با داده‌های POST بازسازی می‌کنیم تا اعتبارسنجی شوند.
        item_forms = [
            ItemActionForm(request.POST, prefix=f"item_{item.pk}", item=item, user=user, factor=factor)
            for item in factor.items.all()
        ]

        if not all(f.is_valid() for f in item_forms):
            messages.error(request, "اطلاعات ارسالی نامعتبر است.")
            # کامنت: اگر فرم نامعتبر بود، صفحه را با خطاهای نمایش داده شده دوباره رندر می‌کنیم.
            return self.render_to_response(self.get_context_data(item_forms=item_forms))

        # کامنت: اقدامات انتخاب شده توسط کاربر (آنهایی که خالی نیستند) را جمع‌آوری می‌کنیم.
        actions_to_process = [
            {'item': FactorItem.objects.get(pk=f.cleaned_data['item_id']),
             'action': get_object_or_404(Action, pk=f.cleaned_data['action']),
             'comment': f.cleaned_data.get('comment', '')}
            for f in item_forms if f.cleaned_data.get('action')
        ]

        if not actions_to_process:
            messages.warning(request, "هیچ اقدامی برای ثبت انتخاب نشده است.")
            return redirect('factor_approval', pk=factor.pk)

        # کامنت: اجرای اقدامات در یک تراکنش اتمیک برای تضمین یکپارچگی داده‌ها.
        try:
            with transaction.atomic():
                for data in actions_to_process:
                    item, action, comment = data['item'], data['action'], data['comment']

                    # کامنت: بررسی مجدد دسترسی در سمت سرور برای امنیت.
                    transition = self._get_valid_transition(user, factor, item, action.id)
                    if not transition:
                        raise PermissionDenied(f"اقدام '{action.name}' روی ردیف '{item.description}' مجاز نیست.")

                    # کامنت: اجرای گذار (تغییر وضعیت).
                    original_status = item.status
                    item.status = transition.to_status
                    item.save(update_fields=['status'])

                    # کامنت: ثبت لاگ تایید.
                    ApprovalLog.objects.create(factor=factor, factor_item=item, user=user, action=action,
                                               from_status=original_status, to_status=item.status, comment=comment)

            messages.success(request, f"{len(actions_to_process)} اقدام با موفقیت ثبت شد.")
        except PermissionDenied as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, "خطایی در هنگام ثبت اقدامات رخ داد.")
            logger.error(f"Error processing actions on Factor PK {factor.pk}: {e}", exc_info=True)

        return redirect('factor_approval', pk=factor.pk)

    def _get_valid_transition(self, user, factor, item, action_id):
        user_post_ids = set(user.userpost_set.filter(is_active=True).values_list('post_id', flat=True))
        try:
            transition = Transition.objects.get(entity_type__code='FACTORITEM', from_status=item.status,
                                                organization=factor.tankhah.organization, action_id=action_id,
                                                is_active=True)
            allowed_post_ids = {p.id for p in transition.allowed_posts.all()}
            if user.is_superuser or not allowed_post_ids.isdisjoint(user_post_ids):
                return transition
        except Transition.DoesNotExist:
            return None
        return None



class FactorApprovalView_____(PermissionBaseView, TemplateView):
    """
    **ویوی نهایی و یکپارچه:**
    این ویو به عنوان یک داشبورد کامل عمل می‌کند که هم اطلاعات فاکتور را نمایش می‌دهد
    و هم فرم‌های اقدام روی ردیف‌ها را مدیریت می‌کند.
    از TemplateView استفاده می‌کنیم چون منطق فرم ما سفارشی است.
    """
    template_name = 'tankhah/Approved/factor_approval.html'  # <--- نام تمپلیت نهایی
    permission_codename = 'tankhah.factor_approve'
    permission_required = 'tankhah.factor_approve' # مطمئن شوید این پرمیشن در مدل Factor وجود دارد

    def get_form_kwargs(self):
        """
        پارامترهای اضافی (فاکتور و کاربر) را برای استفاده در get_context_data و post آماده می‌کند.
        """
        # این متد دیگر برای ساخت فرم استفاده نمی‌شود، فقط برای دسترسی آسان به آبجکت‌هاست.
        kwargs = super().get_form_kwargs()
        kwargs['factor'] = get_object_or_404(Factor, pk=self.kwargs['pk'])
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """
        داده‌های لازم برای تمپلیت را آماده می‌کند.
        برای درخواست GET، فرم‌های خالی می‌سازد.
        برای درخواست POST نامعتبر، فرم‌ها را با داده‌ها و خطاهایشان بازسازی می‌کند.
        """
        context = super().get_context_data(**kwargs)
        factor = get_object_or_404(Factor, pk=self.kwargs['pk'])
        user = self.request.user

        context['factor'] = factor
        context['title'] = _('بررسی و اقدام فاکتور') + f" #{factor.number}"

        # به صورت دستی برای هر ردیف فاکتور یک فرم می‌سازیم.
        item_forms = []
        for item in factor.items.all():
            prefix = f"item_{item.pk}"
            # اگر درخواست POST باشد، فرم را با داده‌های ارسالی پر می‌کنیم.
            if self.request.method == 'POST':
                item_forms.append(ItemActionForm(self.request.POST, prefix=prefix, item=item, user=user, factor=factor))
            else:
                item_forms.append(ItemActionForm(prefix=prefix, item=item, user=user, factor=factor))

        context['item_forms'] = item_forms
        context['approval_history'] = ApprovalLog.objects.filter(factor=factor).order_by('-timestamp').select_related(
            'user', 'post', 'action')

        return context

    def post(self, request, *args, **kwargs):
        """
        منطق اصلی پردازش تمام فرم‌های ارسال شده در این متد قرار دارد.
        """
        # get_context_data را فراخوانی می‌کنیم تا فرم‌ها با داده‌های POST ساخته شوند.
        context = self.get_context_data()
        item_forms = context['item_forms']
        factor = context['factor']
        user = request.user

        if not all(f.is_valid() for f in item_forms):
            messages.error(request, "اطلاعات ارسالی نامعتبر است.")
            return self.render_to_response(context)

        actions_to_process = [
            {'item': FactorItem.objects.get(pk=f.cleaned_data['item_id']),
             'action': get_object_or_404(Action, pk=f.cleaned_data['action']),
             'comment': f.cleaned_data.get('comment', '')}
            for f in item_forms if f.cleaned_data.get('action')
        ]

        if not actions_to_process:
            messages.warning(request, "هیچ اقدامی برای ثبت انتخاب نشده است.")
            return redirect('factor_approval', pk=factor.pk)

        # اجرای اقدامات
        try:
            with transaction.atomic():
                for data in actions_to_process:
                    item, action, comment = data['item'], data['action'], data['comment']

                    transition = self._get_valid_transition(user, factor, item, action.id)
                    if not transition:
                        raise PermissionDenied(f"اقدام '{action.name}' روی ردیف '{item.description}' مجاز نیست.")

                    original_status = item.status
                    item.status = transition.to_status
                    item.save(update_fields=['status'])

                    ApprovalLog.objects.create(factor=factor, factor_item=item, user=user, action=action,
                                               from_status=original_status, to_status=item.status, comment=comment)

            messages.success(request, f"{len(actions_to_process)} اقدام با موفقیت ثبت شد.")

        except PermissionDenied as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, "خطایی در هنگام ثبت اقدامات رخ داد.")
            logger.error(f"Error processing actions on Factor PK {factor.pk}: {e}", exc_info=True)

        return redirect('factor_approval', pk=factor.pk)

    def _get_valid_transition(self, user, factor, item, action_id):
        user_post_ids = set(user.userpost_set.filter(is_active=True).values_list('post_id', flat=True))
        try:
            transition = Transition.objects.get(entity_type__code='FACTORITEM', from_status=item.status,
                                                organization=factor.tankhah.organization, action_id=action_id,
                                                is_active=True)
            allowed_post_ids = {p.id for p in transition.allowed_posts.all()}
            if user.is_superuser or not allowed_post_ids.isdisjoint(user_post_ids):
                return transition
        except Transition.DoesNotExist:
            return None
        return None


# ------------------------------------------------------------------------------------------------------------------
class FactorApprovalView_new(PermissionBaseView, UpdateView):
    """
    این ویو داشبورد اصلی برای تایید/رد ردیف‌های یک فاکتور است.
    از UpdateView استفاده می‌کنیم چون در حال "ویرایش" وضعیت ردیف‌ها هستیم.
    """
    model = Factor
    template_name = 'tankhah/Approved/factor_item_approve.html'  # <--- یک تمپلیت جدید
    permission_codename = 'tankhah.factor_approve'
    context_object_name = 'factor'

    def get_form_kwargs(self):
        """پارامترهای اضافی را به FormSet پاس می‌دهد."""
        kwargs = super().get_form_kwargs()
        # ما به هر فرم در FormSet نیاز داریم که کاربر و فاکتور را بشناسد.
        kwargs['form_kwargs'] = {'user': self.request.user, 'factor': self.object}
        return kwargs

    def get_form(self, form_class=None):
        """FormSet را به جای فرم معمولی برمی‌گرداند."""
        return FactorItemApprovalFormSet(instance=self.object, **self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        """
        داده‌های کامل و غنی را برای نمایش در داشبورد اقدام آماده می‌کند.
        """
        context = super().get_context_data(**kwargs)
        factor = self.object
        logger.debug(f"[FactorApprovalView] Preparing rich context for Factor PK {factor.pk}")

        context['title'] = _('بررسی و اقدام فاکتور') + f" #{factor.number}"
        context['formset'] = context['form']

        # --- بخش کلیدی: اضافه کردن تاریخچه اقدامات ---
        # کامنت: تمام لاگ‌های تایید مرتبط با این فاکتور را واکشی می‌کنیم.
        # ما فقط لاگ‌های مربوط به ردیف‌ها را نمی‌خواهیم، بلکه کل تاریخچه فاکتور مهم است.
        context['approval_history'] = ApprovalLog.objects.filter(
            factor=factor
        ).order_by('-timestamp').select_related('user', 'post', 'action')
        logger.info(f"Found {context['approval_history'].count()} approval logs for Factor PK {factor.pk}.")

        # --- بخش کلیدی: پیدا کردن کاربران منتظر در مرحله فعلی ---
        # کامنت: این منطق فرض می‌کند که "مرحله فعلی" بر اساس اولین ردیف فاکتور که هنوز تایید نشده، مشخص می‌شود.
        # این یک منطق پیچیده است و می‌توان آن را به روش‌های مختلف پیاده کرد. در اینجا یک نمونه ساده ارائه می‌شود.
        pending_users_info = self._get_pending_users_info(factor)
        context.update(pending_users_info)

        return context

    def form_valid(self, form):
        """
        این متد زمانی اجرا می‌شود که تمام فرم‌های FormSet معتبر باشند.
        تمام اقدامات انتخاب شده توسط کاربر را پردازش می‌کند.
        """
        formset = form
        factor = self.object
        user = self.request.user

        logger.info(f"Processing approval form for Factor PK {factor.pk} by user '{user.username}'.")

        actions_to_process = []
        # کامنت: ابتدا تمام اقدامات را جمع‌آوری و اعتبارسنجی می‌کنیم.
        for item_form in formset:
            action_id = item_form.cleaned_data.get('action')
            if action_id:
                item = item_form.instance
                comment = item_form.cleaned_data.get('comment', '')
                actions_to_process.append({'item': item, 'action_id': action_id, 'comment': comment})

        if not actions_to_process:
            messages.warning(self.request, "هیچ اقدامی برای ثبت انتخاب نشده است.")
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                # کامنت: حالا هر اقدام را یکی یکی پردازش می‌کنیم.
                for action_data in actions_to_process:
                    item = action_data['item']
                    action_id = action_data['action_id']
                    comment = action_data['comment']

                    # بررسی مجدد دسترسی برای امنیت بیشتر
                    valid_transition = self._get_valid_transition(user, factor, item, action_id)
                    if not valid_transition:
                        raise PermissionDenied(f"اقدام غیرمجاز روی ردیف {item.pk}")

                    # اجرای گذار
                    original_status = item.status
                    item.status = valid_transition.to_status
                    item.save(update_fields=['status'])

                    # ثبت لاگ و تاریخچه
                    # (برای سادگی فعلا از ApprovalLog صرف نظر می‌کنیم، می‌توان بعدا اضافه کرد)
                    FactorHistory.objects.create(
                        factor=factor,
                        changed_by=user,
                        change_type='STATUS_CHANGE',
                        description=f"وضعیت ردیف '{item.description}' از '{original_status.name}' به '{item.status.name}' تغییر کرد. توضیحات: {comment}"
                    )

            messages.success(self.request, "اقدامات با موفقیت ثبت شد.")
            logger.info(f"Successfully processed {len(actions_to_process)} actions on Factor PK {factor.pk}.")

        except PermissionDenied as e:
            messages.error(self.request, str(e))
            logger.critical(f"SECURITY ALERT: {e} by user '{user.username}' on Factor PK {factor.pk}.")
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, "خطایی در هنگام ثبت اقدامات رخ داد.")
            logger.error(f"Error processing actions on Factor PK {factor.pk}: {e}", exc_info=True)
            return self.form_invalid(form)

        return redirect(self.get_success_url())

    def get_success_url(self):
        """پس از موفقیت، به همان صفحه برمی‌گردیم."""
        return self.object.get_absolute_url()  # فرض بر اینکه در مدل Factor این متد را دارید

    def _get_valid_transition(self, user, factor, item, action_id):
        # این تابع کمکی مشابه تابع قبلی است، اما برای یک ردیف خاص کار می‌کند
        user_post_ids = set(user.userpost_set.filter(is_active=True).values_list('post_id', flat=True))

        try:
            transition = Transition.objects.get(
                entity_type__code='FACTORITEM', from_status=item.status,
                organization=factor.tankhah.organization, action_id=action_id, is_active=True
            )
            if user.is_superuser or not {p.id for p in transition.allowed_posts.all()}.isdisjoint(user_post_ids):
                return transition
        except Transition.DoesNotExist:
            return None
        return None

    def _get_pending_users_info(self, factor):
        """
        یک تابع کمکی برای پیدا کردن وضعیت فعلی و کاربران منتظر.
        این یک نمونه پیاده‌سازی است و می‌توان آن را بر اساس منطق کسب‌وکار شما تغییر داد.
        """
        # کامنت: اولین ردیف فاکتور که هنوز در وضعیت اولیه (مثلا DRAFT یا PENDING) است را پیدا کن.
        first_pending_item = factor.items.exclude(
            status__code__in=['APPROVED_FOR_PAYMENT', 'REJECTED', 'PAID']
        ).order_by('pk').first()

        if not first_pending_item:
            return {'current_stage_name': 'تکمیل شده', 'pending_users': []}

        # کامنت: گذارهای ممکن برای این ردیف را پیدا کن.
        possible_transitions = Transition.objects.filter(
            entity_type__code='FACTORITEM',
            from_status=first_pending_item.status,
            organization=factor.tankhah.organization
        ).prefetch_related('allowed_posts__userpost_set__user')

        if not possible_transitions.exists():
            return {'current_stage_name': first_pending_item.status.name, 'pending_users': ['تعریف نشده']}

        # کامنت: نام مرحله را از اولین گذار ممکن می‌گیریم.
        # (فرض می‌کنیم تمام گذارهای از یک وضعیت، در یک مرحله هستند)
        current_stage_name = possible_transitions.first().name

        # کامنت: تمام کاربرانی که پست مجاز برای انجام این گذارها را دارند، استخراج می‌کنیم.
        pending_users = set()
        for trans in possible_transitions:
            for post in trans.allowed_posts.all():
                for user_post in post.userpost_set.filter(is_active=True):
                    pending_users.add(user_post.user)

        logger.debug(f"Pending users for stage '{current_stage_name}': {[u.username for u in pending_users]}")
        return {'current_stage_name': current_stage_name, 'pending_users': list(pending_users)}
