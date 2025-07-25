# core/forms.py
import logging
from django import forms
from django.db import transaction
from django.db.models import Max
from django.utils.translation import gettext_lazy as _

from core.models import AccessRule, Post,WorkflowStage, Post, WorkflowStage, AccessRule  # اطمینان حاصل کنید که مدل‌های مورد نیاز وارد شده‌اند
from django.utils.translation import gettext_lazy as _
from collections import defaultdict

from tankhah.constants import ENTITY_TYPES, ACTION_TYPES

logger = logging.getLogger('core_forms.py')
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext as _immediate  # اضافه کردن تابع ترجمه فوری

# لیست‌های ثابت برای انواع موجودیت و اقدام

MANAGED_ACTIONS = [
    ('APPROVED', _('تأیید')),
    ('REJECTD', _('رد')),
    ('EDIT', _('ویرایش')),
    ('VIEW', _('مشاهده')),
    ('SIGN_PAYMENT', _('امضای دستور پرداخت')),
    ('STATUS_CHANGE', _('تغییر وضعیت')),
]
MANAGED_ENTITIES = [
    ('FACTOR', _('فاکتور')),
    ('TANKHAH', _('تنخواه')),
    ('BUDGET', _('بودجه')),
    ('PAYMENTORDER', _('دستور پرداخت')),
    ('REPORTS', _('گزارشات')),
    ('GENERAL', _('عمومی')),
]

# اقدامات نیازمند انتخاب مرحله


class AccessRuleForm_oldModels(forms.ModelForm):
    class Meta:
        model = AccessRule
        fields = [
            'organization', 'branch', 'min_level', 'stage', 'action_type',
            'entity_type', 'is_payment_order_signer', 'is_active'
        ]
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'min_level': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'stage': forms.Select(attrs={'class': 'form-control'}),
            'action_type': forms.Select(attrs={'class': 'form-control'}),
            'entity_type': forms.Select(attrs={'class': 'form-control'}),
            'is_payment_order_signer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'organization': _('سازمان'),
            'branch': _('شاخه'),
            'min_level': _('حداقل سطح'),
            'stage': _('مرحله'),
            'action_type': _('نوع اقدام'),
            'entity_type': _('نوع موجودیت'),
            'is_payment_order_signer': _('امضاکننده دستور پرداخت'),
            'is_active': _('فعال'),
        }

    def clean(self):
        cleaned_data = super().clean()
        entity_type = cleaned_data.get('entity_type')
        is_payment_order_signer = cleaned_data.get('is_payment_order_signer')
        action_type = cleaned_data.get('action_type')

        # اعتبارسنجی: اگر is_payment_order_signer=True، entity_type باید PAYMENTORDER باشد
        if is_payment_order_signer and entity_type != 'PAYMENTORDER':
            self.add_error('entity_type', _('برای امضاکننده دستور پرداخت، نوع موجودیت باید PAYMENTORDER باشد.'))
        # اعتبارسنجی: SIGN_PAYMENT فقط برای PAYMENTORDER
        if action_type == 'SIGN_PAYMENT' and entity_type != 'PAYMENTORDER':
            self.add_error('action_type', _('اقدام SIGN_PAYMENT فقط برای نوع موجودیت PAYMENTORDER مجاز است.'))
        return cleaned_data


class AccessRuleForm(forms.ModelForm):
    class Meta:
        model = AccessRule
        fields = [
            'organization',
            'post',
            'branch',
            'min_level',
            'stage',
            'stage_order',
            'action_type',
            'entity_type',
            'is_active',
            'auto_advance',
            'triggers_payment_order',
            'is_final_stage',
            'min_signatures',
        ]
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'post': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'min_level': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'stage': forms.TextInput(attrs={'class': 'form-control'}),
            'stage_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'action_type': forms.Select(attrs={'class': 'form-control'}),
            'entity_type': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_advance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'triggers_payment_order': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_final_stage': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'min_signatures': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
        labels = {
            'organization': _('سازمان'),
            'post': _('پست'),
            'branch': _('شاخه'),
            'min_level': _('حداقل سطح'),
            'stage': _('نام مرحله'),
            'stage_order': _('ترتیب مرحله'),
            'action_type': _('نوع اقدام'),
            'entity_type': _('نوع موجودیت'),
            'is_active': _('فعال'),
            'auto_advance': _('پیش‌رفت خودکار'),
            'triggers_payment_order': _('فعال‌سازی دستور پرداخت'),
            'is_final_stage': _('مرحله نهایی'),
            'min_signatures': _('حداقل تعداد امضا'),
        }

    def clean(self):
        cleaned_data = super().clean()
        entity_type = cleaned_data.get('entity_type')
        action_type = cleaned_data.get('action_type')
        triggers_payment_order = cleaned_data.get('triggers_payment_order')
        stage = cleaned_data.get('stage')
        stage_order = cleaned_data.get('stage_order')

        # اعتبارسنجی: اگر triggers_payment_order=True، entity_type باید PAYMENTORDER یا FACTOR باشد
        if triggers_payment_order and entity_type not in ['PAYMENTORDER', 'FACTOR']:
            self.add_error('entity_type', _('برای فعال‌سازی دستور پرداخت، نوع موجودیت باید PAYMENTORDER یا FACTOR باشد.'))

        # اعتبارسنجی: SIGN_PAYMENT فقط برای PAYMENTORDER یا FACTOR
        if action_type == 'SIGN_PAYMENT' and entity_type not in ['PAYMENTORDER', 'FACTOR']:
            self.add_error('action_type', _('اقدام SIGN_PAYMENT فقط برای نوع موجودیت PAYMENTORDER یا FACTOR مجاز است.'))

        # اعتبارسنجی: برای APPROVE و REJECT نیاز به stage و stage_order است
        if action_type in ['APPROVED', 'REJECTD', 'SIGN_PAYMENT'] and not stage:
            self.add_error('stage', _('برای این نوع اقدام، نام مرحله الزامی است.'))
        if action_type in ['APPROVED', 'REJECTD', 'SIGN_PAYMENT'] and not stage_order:
            self.add_error('stage_order', _('برای این نوع اقدام، ترتیب مرحله الزامی است.'))

        # اعتبارسنجی: stage_order باید مثبت باشد
        if stage_order is not None and stage_order < 1:
            self.add_error('stage_order', _('ترتیب مرحله باید یک عدد مثبت باشد.'))

        # اعتبارسنجی: min_level باید مثبت باشد
        min_level = cleaned_data.get('min_level')
        if min_level is not None and min_level < 1:
            self.add_error('min_level', _('حداقل سطح باید یک عدد مثبت باشد.'))

        return cleaned_data
class PostAccessRuleForm(forms.Form):
    """
    فرم پویا برای انتساب قوانین دسترسی به پست‌ها بر اساس مراحل گردش کار.
    حالا شامل یک چک‌باکس کلی برای فعال/غیرفعال کردن قوانین یک موجودیت-گروه می‌باشد.
    برای اقدامات تأیید/رد، انتخاب مرحله به صورت رادیویی است.
    """

    def __init__(self, *args, **kwargs):
        posts_query = kwargs.pop('posts_query', None)
        super().__init__(*args, **kwargs)
        logger.info("مقداردهی اولیه PostAccessRuleForm.")

        self.posts = posts_query.order_by('organization__name', 'level',
                                          'name') if posts_query is not None else Post.objects.none()
        self.workflow_stages = WorkflowStage.objects.filter(is_active=True).order_by('order')

        # مراحل گردش کار به همراه یک گزینه "هیچکدام" برای فیلد رادیویی
        # این کار برای اطمینان از اینکه می‌توان مرحله‌ای را انتخاب نکرد، ضروری است
        # 'none' به عنوان مقدار برای "هیچکدام" و None برای stage_obj در rule_item استفاده می‌شود.
        stage_choices = [('', _('هیچکدام (غیرفعال)'))] + \
                        [(str(stage.id), stage.name) for stage in self.workflow_stages]
        self.stage_choices_with_none = stage_choices

        self.post_fields_data = []

        if not self.posts.exists():
            logger.info("هیچ پست فعالی برای مدیریت قوانین دسترسی یافت نشد.")
            return

        for post in self.posts:
            post_data_for_template = {
                'post': post,
                'entity_groups': [],
            }

            # 1. فیلد سطح پست (بدون تغییر)
            level_field_name = f'post_{post.id}_level'
            self.fields[level_field_name] = forms.IntegerField(
                label=_("سطح پست"),
                min_value=1,
                initial=post.level,
                required=False,
                widget=forms.NumberInput(
                    attrs={'class': 'form-control w-25', 'title': _('سطح پست را بر اساس سلسله مراتب تعیین کنید')})
            )
            post_data_for_template['level_field'] = self[level_field_name]

            # 2. فیلدهای قوانین دسترسی برای هر پست
            for entity_code, entity_label in MANAGED_ENTITIES:
                entity_rules = {
                    'entity_id': entity_code,
                    'entity_label': entity_label,
                    'rules': []  # این لیست حالا شامل دیکشنری‌هایی برای رادیو باتن یا چک‌باکس معمولی است
                }

                # فیلد "فعال سازی کلی" (بدون تغییر)
                enable_all_field_name = f'enable_all_{post.id}_{entity_code}'
                initial_enable_all = AccessRule.objects.filter(
                    post=post,
                    entity_type=entity_code,
                    action_type__in=[ac[0] for ac in MANAGED_ACTIONS],
                    is_active=True
                ).exists()

                self.fields[enable_all_field_name] = forms.BooleanField(
                    label=_("فعال‌سازی همه قوانین این گروه"),
                    required=False,
                    initial=initial_enable_all,
                    widget=forms.CheckboxInput(attrs={
                        'class': 'form-check-input enable-all-checkbox',
                        'data-post-id': post.id,
                        'data-entity-code': entity_code,
                        'title': _('فعال یا غیرفعال کردن تمامی قوانین این گروه')
                    })
                )
                entity_rules['enable_all_field'] = self[enable_all_field_name]

                # حالا برای هر ACTION یک فیلد مناسب تولید می‌کنیم
                for action_code, action_label in MANAGED_ACTIONS:
                    if action_code in ACTIONS_REQUIRING_STAGE_SELECTION:
                        # برای اقداماتی مثل تأیید/رد که نیازمند انتخاب مرحله هستند، از RadioSelect استفاده می‌کنیم
                        radio_field_name = f'rule_{post.id}_{entity_code}_{action_code}_stage_selection'

                        # پیدا کردن مرحله فعلی انتخاب شده برای این اقدام (اگر وجود دارد)
                        # به دنبال AccessRule فعال با این post, entity_type, action_type می‌گردیم
                        # و stage_id آن را به عنوان initial انتخاب می‌کنیم.
                        current_rule = AccessRule.objects.filter(
                            post=post,
                            entity_type=entity_code,
                            action_type=action_code,
                            is_active=True
                        ).first()
                        initial_stage_id = str(current_rule.stage) if current_rule and current_rule.stage else ''

                        self.fields[radio_field_name] = forms.ChoiceField(
                            label=action_label,
                            choices=self.stage_choices_with_none,
                            initial=initial_stage_id,
                            required=False,
                            widget=forms.RadioSelect(attrs={
                                'class': 'form-check-input stage-selection-radio',
                                'data-post-id': post.id,
                                'data-entity-code': entity_code,
                                'data-action-code': action_code,
                                'title': _('انتخاب مرحله برای این اقدام')
                            })
                        )
                        entity_rules['rules'].append({
                            'action_id': action_code,
                            'action_label': action_label,
                            'is_radio_select': True,  # نشانگر اینکه این یک فیلد رادیویی است
                            'field': self[radio_field_name],
                            'is_signer_field': None,  # فیلد امضاکننده برای این نوع اقدام مرتبط نیست
                        })

                    elif action_code == 'SIGN_PAYMENT' or (entity_code == 'REPORTS' and action_code == 'VIEW'):
                        # برای اقدامات بدون مرحله خاص (SIGN_PAYMENT و VIEW برای REPORTS)، چک‌باکس معمولی
                        rule_field_name = f'rule_{post.id}_{entity_code}_{action_code}_no_stage'

                        filter_kwargs = {
                            'post': post,
                            'entity_type': entity_code,
                            'action_type': action_code,
                            'is_active': True,
                            'stage__isnull': True  # برای این موارد stage باید null باشد
                        }
                        initial_is_active = AccessRule.objects.filter(**filter_kwargs).exists()

                        self.fields[rule_field_name] = forms.BooleanField(
                            label=action_label,
                            required=False,
                            initial=initial_is_active,
                            widget=forms.CheckboxInput(attrs={
                                'class': 'form-check-input rule-checkbox',
                                'data-post-id': post.id,
                                'data-entity-code': entity_code,
                                'data-action-code': action_code,
                                'title': _('فعال کردن این قانون دسترسی')
                            })
                        )

                        is_signer_field = None
                        if entity_code == 'PAYMENTORDER' and action_code == 'SIGN_PAYMENT':
                            signer_field_name = f'signer_{post.id}_{entity_code}_{action_code}_no_stage'

                            initial_is_signer = AccessRule.objects.filter(
                                **filter_kwargs,
                                is_payment_order_signer=True,
                            ).exists()

                            self.fields[signer_field_name] = forms.BooleanField(
                                label=_("امضاکننده دستور پرداخت"),
                                required=False,
                                initial=initial_is_signer,
                                widget=forms.CheckboxInput(attrs={
                                    'class': 'form-check-input signer-checkbox',
                                    'title': _('این پست می‌تواند دستور پرداخت را امضا کند.')
                                })
                            )
                            is_signer_field = self[signer_field_name]

                        entity_rules['rules'].append({
                            'action_id': action_code,
                            'action_label': action_label,
                            'is_radio_select': False,  # نشانگر اینکه این یک چک‌باکس معمولی است
                            'field': self[rule_field_name],
                            'is_signer_field': is_signer_field,
                        })
                    else:
                        # برای اقدامات 'VIEW' که وابسته به مرحله نیستند (مانند VIEW برای FACTOR, TANKHAH, BUDGET)
                        # اگر VIEW هم بخواهد مرحله داشته باشد، باید به ACTIONS_REQUIRING_STAGE_SELECTION اضافه شود.
                        # در غیر این صورت، این بخش را مانند "اقدامات بدون مرحله" مدیریت می‌کنیم.
                        # فرض بر این است که VIEW فقط برای REPORTS مرحله ندارد، برای بقیه ممکن است مرحله داشته باشد یا نه.
                        # اگر VIEW برای همه موجودیت‌ها بدون مرحله است، آن را به else if بالا منتقل کنید.
                        # اگر VIEW برای FACTOR, TANKHAH, BUDGET مرحله دارد، آن را به ACTIONS_REQUIRING_STAGE_SELECTION اضافه کنید.
                        # برای سادگی، فعلاً فرض می‌کنیم VIEW فقط برای REPORTS بی‌مرحله است.
                        # برای FACTOR, TANKHAH, BUDGET و VIEW نیز از همان منطق ACTIONS_REQUIRING_STAGE_SELECTION استفاده می‌کنیم.
                        # این کار باعث می‌شود هر VIEW که به مرحله نیاز داشته باشد، از رادیو باتن استفاده کند.

                        # در اینجا برای VIEW (برای موجودیت‌های غیر REPORTS) نیز از فیلد رادیویی استفاده می‌کنیم.
                        radio_field_name = f'rule_{post.id}_{entity_code}_{action_code}_stage_selection'

                        current_rule = AccessRule.objects.filter(
                            post=post,
                            entity_type=entity_code,
                            action_type=action_code,
                            is_active=True
                        ).first()
                        initial_stage_id = str(current_rule.stage) if current_rule and current_rule.stage else ''

                        self.fields[radio_field_name] = forms.ChoiceField(
                            label=action_label,
                            choices=self.stage_choices_with_none,
                            initial=initial_stage_id,
                            required=False,
                            widget=forms.RadioSelect(attrs={
                                'class': 'form-check-input stage-selection-radio',
                                'data-post-id': post.id,
                                'data-entity-code': entity_code,
                                'data-action-code': action_code,
                                'title': _('انتخاب مرحله برای این اقدام')
                            })
                        )
                        entity_rules['rules'].append({
                            'action_id': action_code,
                            'action_label': action_label,
                            'is_radio_select': True,
                            'field': self[radio_field_name],
                            'is_signer_field': None,
                        })

                if entity_rules['rules']:
                    post_data_for_template['entity_groups'].append(entity_rules)

            self.post_fields_data.append(post_data_for_template)
        logger.info("مقداردهی اولیه PostAccessRuleForm به پایان رسید.")

    def clean(self):
        cleaned_data = super().clean()
        logger.debug("شروع فرآیند اعتبارسنجی فرم PostAccessRuleForm.")

        for post_data in self.post_fields_data:
            post = post_data['post']
            level_field_name = post_data['level_field'].name
            new_level_from_form = cleaned_data.get(level_field_name)

            if new_level_from_form is not None and new_level_from_form != post.level:
                expected_level = post.parent.level + 1 if post.parent else 1
                if new_level_from_form != expected_level:
                    self.add_error(
                        level_field_name,
                        _("سطح پست باید بر اساس والد ({}) {} باشد.").format(
                            post.parent.name if post.parent else _("بدون والد"),
                            expected_level
                        )
                    )
                    logger.warning(
                        f"سطح نامعتبر {new_level_from_form} برای پست {post.name}. مورد انتظار: {expected_level}. والد: {post.parent.name if post.parent else 'None'}")

        # اعتبارسنجی برای حداقل یک قانون فعال
        at_least_one_rule_active = False
        for post_data in self.post_fields_data:
            for entity_group in post_data['entity_groups']:
                for rule_item in entity_group['rules']:
                    if rule_item['is_radio_select']:
                        # برای فیلدهای رادیویی، اگر یک مرحله انتخاب شده باشد (مقدارش '' نباشد)
                        if cleaned_data.get(rule_item['field'].name) != '':
                            at_least_one_rule_active = True
                            break
                    else:
                        # برای چک‌باکس‌های معمولی
                        if cleaned_data.get(rule_item['field'].name, False):
                            at_least_one_rule_active = True
                            break
                if at_least_one_rule_active:
                    break
            if at_least_one_rule_active:
                break

        if not at_least_one_rule_active:
            self.add_error(None, _("حداقل یک قانون دسترسی باید انتخاب شود."))
            logger.warning("هیچ قانون دسترسی انتخاب نشده است.")

        logger.debug(f"اعتبارسنجی فرم به پایان رسید. کلیدهای داده‌های پاک‌شده: {list(cleaned_data.keys())}")
        return cleaned_data

    def save(self, user=None):
        logger.info("شروع عملیات ذخیره قوانین دسترسی.")

        managed_post_ids = {post_data['post'].id for post_data in self.post_fields_data}
        if not managed_post_ids:
            logger.info("هیچ پست فعالی برای مدیریت قوانین دسترسی یافت نشد. از ذخیره خارج می‌شویم.")
            return

        posts_to_update_individually = []
        for post_data in self.post_fields_data:
            post_obj = post_data['post']
            level_field_name = post_data['level_field'].name
            new_level = self.cleaned_data.get(level_field_name)

            if new_level is not None and new_level != post_obj.level:
                post_obj.level = new_level
                posts_to_update_individually.append(post_obj)
                logger.debug(
                    f"پست {post_obj.name} (ID: {post_obj.id}) برای به‌روزرسانی سطح به {new_level} آماده می‌شود.")

        if posts_to_update_individually:
            for post_obj in posts_to_update_individually:
                post_obj.save(changed_by=user)
            logger.info(f"سطوح {len(posts_to_update_individually)} پست به صورت تک‌تک به‌روزرسانی شد.")

        AccessRule.objects.filter(post__id__in=managed_post_ids).delete()
        logger.info(f"قوانین دسترسی موجود برای پست‌های با IDهای: {list(managed_post_ids)} حذف شد.")

        rules_to_create = []
        for post_data in self.post_fields_data:
            post_obj = post_data['post']
            for entity_group in post_data['entity_groups']:
                entity_type = entity_group['entity_id']
                for rule_item in entity_group['rules']:
                    action_type = rule_item['action_id']

                    if rule_item['is_radio_select']:
                        selected_stage_id = self.cleaned_data.get(rule_item['field'].name)
                        if selected_stage_id:  # اگر مرحله‌ای انتخاب شده باشد (خالی نباشد)
                            stage_obj = self.workflow_stages.get(id=selected_stage_id)
                            rules_to_create.append(
                                AccessRule(
                                    post=post_obj,
                                    organization=post_obj.organization,
                                    branch=post_obj.branch or '',
                                    stage=stage_obj,
                                    action_type=action_type,
                                    entity_type=entity_type,
                                    is_active=True,
                                    is_payment_order_signer=False  # برای رادیو باتن‌ها امضاکننده نداریم
                                )
                            )
                            logger.debug(
                                f"قانون برای ایجاد آماده می‌شود (رادیو): پست={post_obj.name}, موجودیت={entity_type}, اقدام={action_type}, مرحله={stage_obj.name}")
                    else:  # چک‌باکس معمولی
                        is_active = self.cleaned_data.get(rule_item['field'].name, False)
                        is_payment_order_signer = False
                        # stage_obj برای این‌ها None است
                        stage_obj = None

                        if entity_type == 'PAYMENTORDER' and action_type == 'SIGN_PAYMENT':
                            signer_field_name = rule_item['is_signer_field'].name
                            is_payment_order_signer = self.cleaned_data.get(signer_field_name, False)
                            if not is_active:
                                is_payment_order_signer = False  # اگر اصلی غیرفعال شد، امضاکننده هم غیرفعال شود

                        if is_active:
                            rules_to_create.append(
                                AccessRule(
                                    post=post_obj,
                                    organization=post_obj.organization,
                                    branch=post_obj.branch or '',
                                    stage=stage_obj,  # این None خواهد بود
                                    action_type=action_type,
                                    entity_type=entity_type,
                                    is_active=True,
                                    is_payment_order_signer=is_payment_order_signer
                                )
                            )
                            logger.debug(
                                f"قانون برای ایجاد آماده می‌شود (چک‌باکس): پست={post_obj.name}, موجودیت={entity_type}, اقدام={action_type}, مرحله=None, امضاکننده={is_payment_order_signer}")

        if rules_to_create:
            AccessRule.objects.bulk_create(rules_to_create, ignore_conflicts=True)
            logger.info(f"با موفقیت {len(rules_to_create)} قانون دسترسی جدید ایجاد شد.")
        else:
            logger.info("هیچ قانون فعالی انتخاب نشد، بنابراین هیچ قانون جدیدی ایجاد نشد.")

        logger.info("عملیات ذخیره قوانین دسترسی به پایان رسید.")

ACTIONS_REQUIRING_STAGE_SELECTION = ['APPROVE', 'REJECT']
ACTIONS_WITHOUT_STAGE = ['EDIT', 'VIEW', 'STATUS_CHANGE', 'CREATE', 'DELETE', 'SIGN_PAYMENT']

from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext as _immediate  # اضافه کردن تابع ترجمه فوری

class PostAccessRuleForm_new(forms.Form):

    def __init__(self, *args, **kwargs):
        self.posts_query = kwargs.pop('posts_query', None)
        super().__init__(*args, **kwargs)
        logger.info("مقداردهی اولیه PostAccessRuleForm.")

        if not self.posts_query:
            logger.warning("No posts_query provided to PostAccessRuleForm.")
            return

        self.post_fields_data = []
        self.existing_rules = AccessRule.objects.filter(post__in=self.posts_query, is_active=True).select_related('post')

        for post in self.posts_query:
            post_data = {'post': post, 'level_field': None, 'entity_groups': []}
            # فیلد برای سطح پست
            field_name = f'post_{post.id}_level'
            self.fields[field_name] = forms.IntegerField(
                label=_immediate('سطح پست %(post_name)s') % {'post_name': post.name},
                required=False,
                min_value=1,
                initial=post.level,
                widget=forms.NumberInput(attrs={'class': 'form-control'})
            )
            post_data['level_field'] = self[field_name]

            # گروه‌بندی قوانین بر اساس موجودیت
            entity_groups = {}
            for entity_type, entity_label in ENTITY_TYPES:
                entity_groups[entity_type] = {
                    'entity_id': entity_type,
                    'entity_label': entity_label,
                    'rules': [],
                    'enable_all_field': None,
                    'new_stage_field': None,
                    'has_stage_actions': any(action_type in ACTIONS_REQUIRING_STAGE_SELECTION for action_type, _ in  ACTION_TYPES)
                }

                # فیلد "فعال‌سازی همه"
                enable_all_field_name = f'enable_all_{post.id}_{entity_type}'
                self.fields[enable_all_field_name] = forms.BooleanField(
                    label=_immediate('فعال‌سازی همه برای %(entity_label)s') % {'entity_label': entity_label},
                    required=False,
                    widget=forms.CheckboxInput(attrs={
                        'class': 'form-check-input enable-all-checkbox',
                        'data-post-id': post.id,
                        'data-entity-code': entity_type
                    })
                )
                entity_groups[entity_type]['enable_all_field'] = self[enable_all_field_name]

                # فیلد برای افزودن مرحله جدید
                if entity_groups[entity_type]['has_stage_actions']:
                    new_stage_field_name = f'new_stage_{post.id}_{entity_type}'
                    self.fields[new_stage_field_name] = forms.CharField(
                        label=_immediate('نام مرحله جدید برای %(entity_label)s') % {'entity_label': entity_label},
                        required=False,
                        widget=forms.TextInput(attrs={
                            'class': 'form-control',
                            'placeholder':_immediate('نام مرحله جدید (برای تأیید یا رد)')
                        })
                    )
                    entity_groups[entity_type]['new_stage_field'] = self[new_stage_field_name]

                # قوانین برای هر اقدام
                for action_type, action_label in ACTION_TYPES:
                    rule_data = {
                        'action_id': action_type,
                        'action_label': action_label,
                        'field': None,
                        'is_signer_field': None,
                        'is_radio_select': action_type in ACTIONS_REQUIRING_STAGE_SELECTION
                    }

                    # فیلد قانون دسترسی
                    field_name = f'rule_{post.id}_{entity_type}_{action_type}_stage_selection'
                    existing_rule = self.existing_rules.filter(
                        post=post,
                        entity_type=entity_type,
                        action_type=action_type
                    ).first()

                    if action_type in ACTIONS_REQUIRING_STAGE_SELECTION:
                        # استخراج مراحل منحصربه‌فرد
                        stages = AccessRule.objects.filter(
                            organization=post.organization,
                            entity_type=entity_type,
                            action_type=action_type,
                            is_active=True
                        ).values('stage_order', 'stage').order_by('stage_order')
                        seen = set()
                        unique_stages = []
                        for stage in stages:
                            stage_tuple = (stage['stage_order'], stage['stage'] or f"مرحله {stage['stage_order']}")
                            if stage_tuple not in seen:
                                seen.add(stage_tuple)
                                unique_stages.append(stage)

                        choices = [('', _immediate('غیرفعال'))]
                        if unique_stages:
                            choices += [
                                (str(stage['stage_order']), f"{stage['stage'] or 'مرحله ' + str(stage['stage_order'])} (ترتیب: {stage['stage_order']})")
                                for stage in unique_stages
                            ]
                        else:
                            choices += [('', _immediate('هیچ مرحله‌ای تعریف نشده است، لطفاً مرحله جدید اضافه کنید'))]

                        self.fields[field_name] = forms.ChoiceField(
                            label=action_label,
                            choices=choices,
                            required=False,
                            initial=str(existing_rule.stage_order) if existing_rule else '',
                            widget=forms.RadioSelect(attrs={
                                'class': 'stage-radio-group',
                                'data-post-id': post.id,
                                'data-entity-code': entity_type,
                                'data-action-code': action_type
                            })
                        )
                    else:
                        self.fields[field_name] = forms.BooleanField(
                            label=action_label,
                            required=False,
                            initial=bool(existing_rule),
                            widget=forms.CheckboxInput(attrs={
                                'class': 'form-check-input rule-checkbox',
                                'data-post-id': post.id,
                                'data-entity-code': entity_type,
                                'data-action-code': action_type
                            })
                        )
                    rule_data['field'] = self[field_name]

                    # فیلد امضاکننده (فقط برای SIGN_PAYMENT در PAYMENTORDER و FACTOR)
                    if entity_type in ['PAYMENTORDER', 'FACTOR'] and action_type == 'SIGN_PAYMENT':
                        signer_field_name = f'signer_{post.id}_{entity_type}_{action_type}'
                        self.fields[signer_field_name] = forms.BooleanField(
                            label=_immediate('امضاکننده'),
                            required=False,
                            initial=existing_rule.triggers_payment_order if existing_rule else False,
                            widget=forms.CheckboxInput(attrs={
                                'class': 'form-check-input signer-checkbox',
                                'data-post-id': post.id,
                                'data-entity-code': entity_type,
                                'data-action-code': action_type
                            })
                        )
                        rule_data['is_signer_field'] = self[signer_field_name]

                    entity_groups[entity_type]['rules'].append(rule_data)

                post_data['entity_groups'] = list(entity_groups.values())
            self.post_fields_data.append(post_data)

        logger.info("مقداردهی اولیه PostAccessRuleForm به پایان رسید.")

    def clean(self):
        logger.debug("شروع فرآیند اعتبارسنجی فرم PostAccessRuleForm.")
        cleaned_data = super().clean()
        has_any_rule = False

        for post in self.posts_query:
            for entity_type, _ in ENTITY_TYPES:
                new_stage_field_name = f'new_stage_{post.id}_{entity_type}'
                new_stage_name = cleaned_data.get(new_stage_field_name, '').strip()

                # بررسی اقدامات نیازمند مرحله
                for action_type in ACTIONS_REQUIRING_STAGE_SELECTION:
                    field_name = f'rule_{post.id}_{entity_type}_{action_type}_stage_selection'
                    stage_order = cleaned_data.get(field_name)

                    if stage_order and stage_order != '':
                        try:
                            stage_order = int(stage_order)
                            has_any_rule = True
                            if not AccessRule.objects.filter(
                                    organization=post.organization,
                                    entity_type=entity_type,
                                    action_type=action_type,
                                    stage_order=stage_order,
                                    is_active=True
                            ).exists():
                                self.add_error(field_name, _('مرحله انتخاب‌شده وجود ندارد یا غیرفعال است.'))
                        except ValueError:
                            self.add_error(field_name, _('ترتیب مرحله باید یک عدد معتبر باشد.'))
                    elif new_stage_name:
                        has_any_rule = True
                        for at in ACTIONS_REQUIRING_STAGE_SELECTION:
                            fn = f'rule_{post.id}_{entity_type}_{at}_stage_selection'
                            if fn in cleaned_data and cleaned_data[fn]:
                                has_any_rule = True
                                break
                        else:
                            self.add_error(new_stage_field_name,
                                           _('برای افزودن مرحله جدید، حداقل یک اقدام نیازمند مرحله (تأیید یا رد) باید انتخاب شود.'))

                # بررسی اقدامات بدون مرحله
                for action_type in ACTIONS_WITHOUT_STAGE:
                    field_name = f'rule_{post.id}_{entity_type}_{action_type}_stage_selection'
                    if cleaned_data.get(field_name):
                        has_any_rule = True

                # اعتبارسنجی امضاکننده
                if entity_type in ['PAYMENTORDER', 'FACTOR']:
                    signer_field_name = f'signer_{post.id}_{entity_type}_SIGN_PAYMENT'
                    if cleaned_data.get(signer_field_name) and not cleaned_data.get(
                            f'rule_{post.id}_{entity_type}_SIGN_PAYMENT_stage_selection'):
                        self.add_error(signer_field_name,
                                       _('برای فعال کردن امضاکننده، باید گزینه امضای دستور پرداخت فعال باشد.'))

        if not has_any_rule:
            logger.warning("هیچ قانون دسترسی انتخاب نشده است.")
            self.add_error(None, _('حداقل یک قانون دسترسی باید انتخاب شود.'))

        logger.debug(f"اعتبارسنجی فرم به پایان رسید. کلیدهای داده‌های پاک‌شده: {list(cleaned_data.keys())}")
        return cleaned_data

    def save(self, user):
        with transaction.atomic():
            for post in self.posts_query:
                # به‌روزرسانی سطح پست
                level_field_name = f'post_{post.id}_level'
                if level_field_name in self.cleaned_data and self.cleaned_data[level_field_name]:
                    post.level = self.cleaned_data[level_field_name]
                    post.save()

                # مدیریت قوانین دسترسی
                for entity_type, _ in ENTITY_TYPES:
                    new_stage_name = self.cleaned_data.get(f'new_stage_{post.id}_{entity_type}', '').strip()
                    new_stage_order = None
                    if new_stage_name or any(
                        self.cleaned_data.get(f'rule_{post.id}_{entity_type}_{at}_stage_selection')
                        for at in ACTIONS_REQUIRING_STAGE_SELECTION
                    ):
                        # محاسبه stage_order با در نظر گرفتن سازمان
                        max_stage_order = AccessRule.objects.filter(
                            organization=post.organization,
                            entity_type=entity_type,
                            is_active=True
                        ).aggregate(Max('stage_order'))['stage_order__max'] or 0
                        new_stage_order = max_stage_order + 1

                    for action_type, _ in ACTION_TYPES:
                        field_name = f'rule_{post.id}_{entity_type}_{action_type}_stage_selection'
                        rule_value = self.cleaned_data.get(field_name)
                        existing_rule = AccessRule.objects.filter(
                            post=post,
                            entity_type=entity_type,
                            action_type=action_type,
                            is_active=True
                        ).first()

                        if action_type in ACTIONS_REQUIRING_STAGE_SELECTION:
                            # مدیریت قوانین با مرحله
                            stage_order = int(rule_value) if rule_value and rule_value != '' else None
                            if new_stage_name and not stage_order:
                                stage_order = new_stage_order
                            if stage_order:
                                # بررسی یکتایی stage_order
                                if AccessRule.objects.filter(
                                    organization=post.organization,
                                    entity_type=entity_type,
                                    stage_order=stage_order,
                                    is_active=True
                                ).exclude(pk=existing_rule.pk if existing_rule else None).exists():
                                    logger.error(f"تکرار stage_order={stage_order} برای سازمان={post.organization}, موجودیت={entity_type}")
                                    raise ValueError(
                                        _immediate("ترتیب مرحله {stage_order} برای سازمان {org} و موجودیت {entity} قبلاً استفاده شده است.").format(
                                            stage_order=stage_order,
                                            org=post.organization,
                                            entity=entity_type
                                        )
                                    )
                                stage_name = new_stage_name if new_stage_name else next(
                                    (rule.stage for rule in AccessRule.objects.filter(
                                        organization=post.organization,
                                        entity_type=entity_type,
                                        stage_order=stage_order,
                                        is_active=True
                                    )), f"مرحله {stage_order}"
                                )
                                if existing_rule and existing_rule.stage_order != stage_order:
                                    existing_rule.is_active = False
                                    existing_rule.save()
                                    existing_rule = None
                                if not existing_rule:
                                    AccessRule.objects.create(
                                        organization=post.organization,
                                        post=post,
                                        branch=post.branch or '',
                                        min_level=post.level,
                                        stage=stage_name,
                                        stage_order=stage_order,
                                        action_type=action_type,
                                        entity_type=entity_type,
                                        is_active=True,
                                        auto_advance=True,
                                        triggers_payment_order=False,
                                        is_final_stage=(stage_order == AccessRule.objects.filter(
                                            organization=post.organization,
                                            entity_type=entity_type,
                                            is_active=True
                                        ).aggregate(Max('stage_order'))['stage_order__max']),
                                        min_signatures=1,
                                        created_by=user
                                    )
                            elif existing_rule:
                                existing_rule.is_active = False
                                existing_rule.save()
                        else:
                            # مدیریت قوانین بدون مرحله
                            if rule_value and not existing_rule:
                                AccessRule.objects.create(
                                    organization=post.organization,
                                    post=post,
                                    branch=post.branch or '',
                                    min_level=post.level,
                                    stage='',
                                    stage_order=0,
                                    action_type=action_type,
                                    entity_type=entity_type,
                                    is_active=True,
                                    auto_advance=False,
                                    triggers_payment_order=False,
                                    is_final_stage=False,
                                    min_signatures=1,
                                    created_by=user
                                )
                            elif not rule_value and existing_rule:
                                existing_rule.is_active = False
                                existing_rule.save()

                        # مدیریت امضاکننده
                        signer_field_name = f'signer_{post.id}_{entity_type}_{action_type}'
                        if signer_field_name in self.cleaned_data and self.cleaned_data[signer_field_name]:
                            rule = AccessRule.objects.filter(
                                post=post,
                                entity_type=entity_type,
                                action_type=action_type,
                                is_active=True
                            ).first()
                            if rule:
                                rule.triggers_payment_order = True
                                rule.created_by = user
                                rule.save()