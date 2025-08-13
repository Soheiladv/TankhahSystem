# ===== IMPORTS =====
from django import forms
from django.utils.translation import gettext_lazy as _
from tankhah.models import Factor, FactorItem
from core.models import Transition

from django import forms
from django.forms import inlineformset_factory

from core.models import Action, Transition
from tankhah.models import Factor, FactorItem
import logging

# یک لاگر مخصوص برای این فایل ایجاد می‌کنیم
logger = logging.getLogger('ApprovalFormsLogger')

# ===== FORM =====

class ItemActionForm(forms.Form):
    """
    یک فرم ساده و مستقل برای گرفتن اقدام و توضیحات کاربر برای یک ردیف فاکتور.
    این فرم به هیچ مدلی وابسته نیست (non-ModelForm).
    """
    # یک فیلد مخفی برای نگهداری ID ردیف فاکتور.
    item_id = forms.IntegerField(widget=forms.HiddenInput())

    # دراپ‌داون برای نمایش اقدامات مجاز (تایید، رد و...).
    action = forms.ChoiceField(
        label=_("اقدام جدید"),
        required=False,  # کاربر مجبور نیست برای همه ردیف‌ها اقدام انتخاب کند.
        widget=forms.Select(attrs={'class': 'form-select form-select-sm action-select'})
    )

    # فیلد متنی برای توضیحات (مثلا دلیل رد).
    comment = forms.CharField(
        label=_("توضیحات"),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control form-control-sm comment-input', 'rows': 1})
    )

    def __init__(self, *args, **kwargs):
        """
        در زمان ساخت فرم، پارامترهای اضافی (user, factor, item) را از ویو دریافت کرده
        و بر اساس آنها، لیست اقدامات مجاز را برای دراپ‌داون 'action' می‌سازیم.
        """
        user = kwargs.pop('user')
        factor = kwargs.pop('factor')
        item = kwargs.pop('item')
        super().__init__(*args, **kwargs)

        self.fields['item_id'].initial = item.pk

        # --- شروع بخش دیباگ ---
        logger.info(f"================== DEBUGGING ACTIONS FOR ITEM PK: {item.pk} ==================")

        # ۱. بررسی ورودی‌های اولیه
        logger.info(f"1. Context: User='{user.username}', Factor='{factor.number}', Item='{item.description}'")

        # ۲. بررسی وضعیت فعلی ردیف
        current_status = item.status
        if not current_status:
            logger.error(f"   -> CRITICAL: Item PK {item.pk} has no status! Cannot find transitions.")
            self.fields['action'].choices = [("", "---------")]
            return
        logger.info(f"2. Current Item Status: '{current_status.name}' (ID: {current_status.id})")

        # ۳. بررسی سازمان
        organization = factor.tankhah.organization
        logger.info(f"3. Organization: '{organization.name}' (ID: {organization.id})")

        logger.info(f"--- [ItemActionForm] Building for Item PK: {item.pk} ---")
        logger.debug(f"Context: User='{user.username}', Status='{item.status}', Org='{factor.tankhah.organization}'")

        # ۴. بررسی پست‌های فعال کاربر
        user_posts = user.userpost_set.filter(is_active=True)
        user_post_ids = set(user_posts.values_list('post_id', flat=True))
        logger.info(f"4. User Active Post IDs: {user_post_ids}")

        # ۵. اجرای کوئری برای پیدا کردن گذارهای ممکن
        possible_transitions = Transition.objects.filter(
            entity_type__code='FACTORITEM',
            from_status=current_status,
            organization=organization,
            is_active=True
        ).select_related('action').prefetch_related('allowed_posts')

        logger.info(
            f"5. Query Result: Found {possible_transitions.count()} possible transitions based on status and organization.")

        # ۶. فیلتر کردن گذارها بر اساس دسترسی کاربر
        choices = [("", "---------")]
        if not possible_transitions:
            logger.warning("   -> REASON: No transitions are defined in the database for this status and organization.")
        else:
            for transition in possible_transitions:
                allowed_post_ids = {p.id for p in transition.allowed_posts.all()}
                logger.debug(
                    f"   -> Checking Transition '{transition.action.name}': Allowed Post IDs are {allowed_post_ids}")

                # شرط اصلی دسترسی
                if user.is_superuser or not allowed_post_ids.isdisjoint(user_post_ids):
                    choices.append((transition.action.id, transition.action.name))
                    logger.debug(f"      - ACCESS GRANTED for user '{user.username}'. Action added to choices.")
                else:
                    logger.debug(
                        f"      - ACCESS DENIED for user '{user.username}'. User posts do not match allowed posts.")

        # ۷. نتیجه نهایی
        self.fields['action'].choices = choices
        logger.info(f"7. Final Choices for Dropdown: {choices}")
        if len(choices) == 1:
            logger.warning(f"   -> FINAL RESULT: No actions were authorized for this user on this item.")

        logger.info("================== END DEBUGGING ==================\n")

# ===== forms.py (ادامه فایل) =====


class FactorItemApprovalForm(forms.ModelForm):
    """
    این فرم سفارشی برای هر ردیف در صفحه تایید فاکتور استفاده می‌شود.
    فقط شامل فیلدهایی است که مدیر باید پر کند.
    """
    # کامنت: یک فیلد ChoiceField برای نمایش اقدامات مجاز ایجاد می‌کنیم.
    action = forms.ChoiceField(label="اقدام", required=False,
                               widget=forms.Select(attrs={'class': 'form-select form-select-sm'}))
    comment = forms.CharField(label="توضیحات", required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 1}))

    class Meta:
        model = FactorItem
        fields = ['action', 'comment']  # فقط همین دو فیلد در فرم هستند
    #
    # def __init__(self, *args, **kwargs):
    #     """
    #     در زمان ساخته شدن فرم، لیست اقدامات مجاز را محاسبه کرده و در فیلد action قرار می‌دهیم.
    #     """
    #     # کامنت: پارامترهای اضافی (کاربر، فاکتور) را که از ویو پاس داده شده‌اند، استخراج می‌کنیم.
    #     user = kwargs.pop('user', None)
    #     factor = kwargs.pop('factor', None)
    #     super().__init__(*args, **kwargs)
    #
    #     # کامنت: اگر کاربر و فاکتور معتبر باشند، به سراغ پیدا کردن اقدامات مجاز می‌رویم.
    #     if user and factor and self.instance:
    #         user_post_ids = set(user.userpost_set.filter(is_active=True).values_list('post_id', flat=True))
    #
    #         # کامنت: گذارهای ممکن برای این ردیف فاکتور در وضعیت فعلی‌اش را پیدا می‌کنیم.
    #         possible_transitions = Transition.objects.filter(
    #             entity_type__code='FACTORITEM',  # مهم: گردش کار در سطح FACTORITEM است
    #             from_status=self.instance.status,
    #             organization=factor.tankhah.organization,
    #             is_active=True
    #         ).prefetch_related('allowed_posts', 'action')
    #
    #         choices = [("", "---------")]  # انتخاب پیش‌فرض
    #         for transition in possible_transitions:
    #             # کامنت: اگر کاربر سوپریوزر است یا پست مجاز را دارد، این اقدام را به لیست انتخاب‌ها اضافه کن.
    #             if user.is_superuser or not {p.id for p in transition.allowed_posts.all()}.isdisjoint(user_post_ids):
    #                 choices.append((transition.action.id, transition.action.name))
    #
    #         self.fields['action'].choices = choices


# ساخت FormSet بر اساس فرم سفارشی بالا
FactorItemApprovalFormSet = inlineformset_factory(
    Factor,
    FactorItem,
    form=FactorItemApprovalForm,
    extra=0,  # هیچ فرم خالی اضافی نمی‌خواهیم
    can_delete=False,  # کاربر نباید ردیف را از این صفحه حذف کند
    edit_only=True  # فقط ردیف‌های موجود را نمایش بده
)