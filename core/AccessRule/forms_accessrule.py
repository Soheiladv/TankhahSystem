# core/forms.py
import logging
from django import forms
from django.db import transaction, models, IntegrityError
from django.db.models import Max
from django.utils.translation import gettext_lazy as _

from core.models import AccessRule, Post,WorkflowStage, Post, WorkflowStage, AccessRule  # اطمینان حاصل کنید که مدل‌های مورد نیاز وارد شده‌اند
from django.utils.translation import gettext_lazy as _
from collections import defaultdict

from tankhah.constants import ENTITY_TYPES, ACTION_TYPES
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext as _immediate  # اضافه کردن تابع ترجمه فوری
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

ACTIONS_REQUIRING_STAGE_SELECTION = ['APPROVE', 'REJECT']
ACTIONS_WITHOUT_STAGE = ['EDIT', 'VIEW', 'STATUS_CHANGE', 'CREATE', 'DELETE', 'SIGN_PAYMENT']

# اقدامات نیازمند انتخاب مرحله
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

class PostAccessRuleForm_new________(forms.Form):

    def __init__(self, *args, **kwargs):
        self.posts_query = kwargs.pop('posts_query', None)
        super().__init__(*args, **kwargs)
        logger.info("مقداردهی اولیه PostAccessRuleForm.")

        if not self.posts_query:
            logger.warning("No posts_query provided to PostAccessRuleForm.")
            return

        self.post_fields_data = []
        # به جای استفاده از existing_rules در اینجا، بهتر است برای هر فیلد جداگانه آن را کوئری کنیم
        # تا با تغییرات لحظه‌ای پست‌ها، داده‌ها دقیق‌تر باشند.
        # self.existing_rules = AccessRule.objects.filter(post__in=self.posts_query, is_active=True).select_related('post')


        for post in self.posts_query:
            post_data = {'post': post, 'level_field': None, 'entity_groups': []} # level_field حالا همیشه None است

            # ⛔️⛔️⛔️ این بخش برای فیلد سطح پست (level) حذف شده است ⛔️⛔️⛔️
            # field_name = f'post_{post.id}_level'
            # self.fields[field_name] = forms.IntegerField(
            #     label=_immediate('سطح پست %(post_name)s') % {'post_name': post.name},
            #     required=False,
            #     min_value=1,
            #     initial=post.level, # مقدار اولیه از level موجود پست گرفته می‌شود
            #     widget=forms.NumberInput(attrs={'class': 'form-control'})
            # )
            # post_data['level_field'] = self[field_name] # این بخش نیز اگر فیلد level_field را لازم ندارید، می‌تواند حذف شود

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
                    # 💡 اینجا یک کوئری جداگانه برای هر قانون می‌زنیم تا مطمئن شویم از آخرین وضعیت موجود استفاده می‌کنیم.
                    existing_rule = AccessRule.objects.filter(
                        post=post,
                        entity_type=entity_type,
                        action_type=action_type,
                        is_active=True
                    ).first()

                    if action_type in ACTIONS_REQUIRING_STAGE_SELECTION:
                        # استخراج مراحل منحصربه‌فرد (از قوانین فعال در آن سازمان و موجودیت و اقدام)
                        # این بخش باید فقط مراحل موجود را نمایش دهد
                        stages = AccessRule.objects.filter(
                            organization=post.organization, # مهم: مراحل باید در همان سازمان تعریف شده باشند
                            entity_type=entity_type,
                            action_type=action_type,
                            is_active=True
                        ).values('stage_order', 'stage').order_by('stage_order')

                        seen = set()
                        unique_stages_choices = []
                        for stage in stages:
                            stage_tuple = (stage['stage_order'], stage['stage'])
                            if stage_tuple not in seen:
                                seen.add(stage_tuple)
                                unique_stages_choices.append(
                                    (str(stage['stage_order']), f"{stage['stage'] or 'مرحله ' + str(stage['stage_order'])} (ترتیب: {stage['stage_order']})")
                                )

                        choices = [('', _immediate('غیرفعال'))] + unique_stages_choices
                        # اگر هیچ مرحله‌ای در سازمان موجودیت و اکشن مربوطه وجود ندارد
                        if not unique_stages_choices and not existing_rule:
                            # این گزینه کمک می‌کند تا کاربر بداند چرا گزینه‌ای نیست و باید مرحله جدید اضافه کند.
                            choices += [('new_stage_placeholder', _immediate('هیچ مرحله‌ای تعریف نشده، ابتدا مرحله جدید اضافه کنید'))]

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
                    else: # برای اقدامات بدون مرحله (EDIT, VIEW, CREATE, DELETE, STATUS_CHANGE)
                        self.fields[field_name] = forms.BooleanField(
                            label=action_label,
                            required=False,
                            initial=bool(existing_rule), # اگر قانونی وجود دارد، تیک خورده باشد
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

                # اعتبارسنجی برای اقدامات نیازمند مرحله
                for action_type in ACTIONS_REQUIRING_STAGE_SELECTION:
                    field_name = f'rule_{post.id}_{entity_type}_{action_type}_stage_selection'
                    stage_order_input = cleaned_data.get(field_name) # این می‌تواند رشته‌ای از عدد یا 'new_stage_placeholder' باشد

                    if stage_order_input == 'new_stage_placeholder': # اگر گزینه "هیچ مرحله‌ای تعریف نشده" انتخاب شده باشد
                        self.add_error(field_name, _('لطفاً یک مرحله معتبر انتخاب کنید یا نام مرحله جدید را وارد کنید.'))
                        continue

                    if stage_order_input and stage_order_input != '': # یعنی یک مرحله انتخاب شده (عدد)
                        try:
                            stage_order = int(stage_order_input)
                            has_any_rule = True
                            # اعتبارسنجی که مرحله انتخاب شده واقعا وجود داشته باشد و فعال باشد
                            if not AccessRule.objects.filter(
                                    organization=post.organization, # مهم: باید مرحله در همان سازمان وجود داشته باشد
                                    entity_type=entity_type,
                                    action_type=action_type,
                                    stage_order=stage_order,
                                    is_active=True
                            ).exists():
                                self.add_error(field_name, _('مرحله انتخاب‌شده وجود ندارد یا غیرفعال است.'))
                        except ValueError:
                            self.add_error(field_name, _('ترتیب مرحله باید یک عدد معتبر باشد.'))

                # اعتبارسنجی برای نام مرحله جدید
                if new_stage_name:
                    has_stage_action_selected = False
                    for at in ACTIONS_REQUIRING_STAGE_SELECTION:
                        fn = f'rule_{post.id}_{entity_type}_{at}_stage_selection'
                        if cleaned_data.get(fn) and cleaned_data.get(fn) != '':
                            has_stage_action_selected = True
                            break
                    if not has_stage_action_selected:
                        self.add_error(new_stage_field_name,
                                       _('برای افزودن مرحله جدید، حداقل یک اقدام نیازمند مرحله (تأیید یا رد) باید انتخاب شود.'))
                    has_any_rule = True # اگر نام مرحله جدید وارد شده، یعنی یک قانون احتمالی داریم

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
                # ⛔️⛔️⛔️ این بخش برای به‌روزرسانی سطح پست حذف شده است ⛔️⛔️⛔️
                # level_field_name = f'post_{post.id}_level'
                # if level_field_name in self.cleaned_data and self.cleaned_data[level_field_name]:
                #     post.level = self.cleaned_data[level_field_name]
                #     post.save() # این save، منطق Post.save() را فراخوانی می‌کند و level را بازنویسی می‌کند

                # 💡 اکنون، برای AccessRule از `post.level` فعلی که همیشه توسط Post.save() مدیریت می‌شود، استفاده می‌کنیم.
                current_post_level = post.level # سطح فعلی پست را می‌گیریم

                # مدیریت قوانین دسترسی
                for entity_type, _ in ENTITY_TYPES:
                    new_stage_name = self.cleaned_data.get(f'new_stage_{post.id}_{entity_type}', '').strip()
                    new_stage_order = None

                    # اگر نام مرحله جدید وارد شده یا حداقل یکی از اقدامات نیازمند مرحله انتخاب شده است
                    if new_stage_name:
                        # محاسبه stage_order جدید برای سازمان و موجودیت خاص
                        max_stage_order = AccessRule.objects.filter(
                            organization=post.organization, # مهم: باید در همان سازمان باشد
                            entity_type=entity_type,
                            is_active=True
                        ).aggregate(Max('stage_order'))['stage_order__max'] or 0
                        new_stage_order = max_stage_order + 1

                    for action_type, _ in ACTION_TYPES:
                        field_name = f'rule_{post.id}_{entity_type}_{action_type}_stage_selection'
                        rule_value = self.cleaned_data.get(field_name) # این می‌تواند رشته‌ای از عدد یا '' باشد

                        existing_rule = AccessRule.objects.filter(
                            post=post,
                            entity_type=entity_type,
                            action_type=action_type,
                            is_active=True
                        ).first()

                        if action_type in ACTIONS_REQUIRING_STAGE_SELECTION:
                            # مدیریت قوانین با مرحله (تأیید، رد، امضا)
                            stage_order_to_use = None
                            if rule_value and rule_value != '': # اگر یک مرحله موجود انتخاب شده
                                stage_order_to_use = int(rule_value)
                            elif new_stage_name: # اگر مرحله جدید وارد شده و هیچ مرحله موجودی انتخاب نشده
                                stage_order_to_use = new_stage_order

                            if stage_order_to_use:
                                # 💡 بررسی یکتایی stage_order فقط در سطح سازمان و entity_type
                                # این بررسی باید در clean() انجام شود و اینجا فقط از اعتبار آن مطمئن هستیم.
                                # با این حال، یک بررسی ثانویه در save مدل AccessRule نیز وجود دارد.
                                # (کد مدل AccessRule شما این بررسی را دارد، که خوب است)

                                # تعیین نام مرحله (اگر نام جدید داده شده یا نام موجود استفاده شود)
                                stage_name_to_use = new_stage_name if new_stage_name else next(
                                    (rule.stage for rule in AccessRule.objects.filter(
                                        organization=post.organization,
                                        entity_type=entity_type,
                                        stage_order=stage_order_to_use,
                                        is_active=True
                                    )), f"مرحله {stage_order_to_use}" # نام پیش‌فرض اگر پیدا نشد
                                )

                                # اگر قانون فعلی وجود دارد و مرحله آن تغییر کرده است
                                if existing_rule and existing_rule.stage_order != stage_order_to_use:
                                    existing_rule.is_active = False # غیرفعال کردن قانون قدیمی
                                    existing_rule.save(update_fields=['is_active']) # فقط فیلد is_active را به‌روزرسانی کنید

                                    # حالا بررسی می‌کنیم آیا قانون جدید با همان پست، موجودیت و اقدام و مرحله وجود دارد یا خیر
                                    existing_rule_for_new_stage = AccessRule.objects.filter(
                                        post=post,
                                        entity_type=entity_type,
                                        action_type=action_type,
                                        stage_order=stage_order_to_use,
                                        is_active=False # شاید قبلا غیرفعال شده باشد
                                    ).first()

                                    if existing_rule_for_new_stage:
                                        # اگر قانون غیرفعالی با این مشخصات وجود دارد، آن را فعال می‌کنیم
                                        existing_rule_for_new_stage.is_active = True
                                        existing_rule_for_new_stage.stage = stage_name_to_use # نام مرحله را هم به‌روز می‌کنیم
                                        existing_rule_for_new_stage.created_by = user # ایجادکننده را هم به‌روز می‌کنیم
                                        existing_rule_for_new_stage.save()
                                    else:
                                        # اگر هیچ قانون فعالی یا غیرفعالی با مرحله جدید وجود ندارد، ایجاد می‌کنیم
                                        AccessRule.objects.create(
                                            organization=post.organization,
                                            post=post,
                                            branch=post.branch  ,
                                            min_level=current_post_level, # 💡 استفاده از current_post_level
                                            stage=stage_name_to_use,
                                            stage_order=stage_order_to_use,
                                            action_type=action_type,
                                            entity_type=entity_type,
                                            is_active=True,
                                            auto_advance=True, # این را بر اساس نیازتان تنظیم کنید
                                            triggers_payment_order=False, # این را در بخش امضاکننده مدیریت می‌کنیم
                                            is_final_stage=False, # این را در نهایت حلقه تنظیم خواهیم کرد
                                            min_signatures=1,
                                            created_by=user
                                        )
                                # اگر قانون فعلی وجود دارد و مرحله آن تغییر نکرده، یا قانون جدید است
                                elif not existing_rule: # اگر قانون فعالی وجود ندارد و نیاز به ایجاد است
                                     AccessRule.objects.create(
                                        organization=post.organization,
                                        post=post,
                                        branch=post.branch  ,
                                        min_level=current_post_level, # 💡 استفاده از current_post_level
                                        stage=stage_name_to_use,
                                        stage_order=stage_order_to_use,
                                        action_type=action_type,
                                        entity_type=entity_type,
                                        is_active=True,
                                        auto_advance=True,
                                        triggers_payment_order=False,
                                        is_final_stage=False,
                                        min_signatures=1,
                                        created_by=user
                                    )
                                # اگر قانون وجود دارد و همان مرحله است، نیاز به تغییر نیست (مگر triggers_payment_order)

                            elif existing_rule: # اگر در فرم هیچ مرحله‌ای انتخاب نشده و قانون فعالی وجود دارد
                                existing_rule.is_active = False
                                existing_rule.save(update_fields=['is_active'])

                        else: # مدیریت قوانین بدون مرحله (EDIT, VIEW, CREATE, DELETE, STATUS_CHANGE)
                            if rule_value and not existing_rule: # اگر تیک خورده و قانونی وجود ندارد، ایجاد کن
                                AccessRule.objects.create(
                                    organization=post.organization,
                                    post=post,
                                    branch=post.branch ,
                                    min_level=current_post_level, # 💡 استفاده از current_post_level
                                    stage='', # اینها مرحله ندارند
                                    stage_order=0, # اینها مرحله ندارند
                                    action_type=action_type,
                                    entity_type=entity_type,
                                    is_active=True,
                                    auto_advance=False,
                                    triggers_payment_order=False,
                                    is_final_stage=False,
                                    min_signatures=1,
                                    created_by=user
                                )
                            elif not rule_value and existing_rule: # اگر تیک برداشته شده و قانونی وجود دارد، غیرفعال کن
                                existing_rule.is_active = False
                                existing_rule.save(update_fields=['is_active'])

                        # مدیریت فیلد امضاکننده (triggers_payment_order)
                        signer_field_name = f'signer_{post.id}_{entity_type}_{action_type}'
                        if signer_field_name in self.cleaned_data:
                            is_signer_checked = self.cleaned_data[signer_field_name]
                            # قانون فعال فعلی را پیدا کن
                            rule_for_signer = AccessRule.objects.filter(
                                post=post,
                                entity_type=entity_type,
                                action_type=action_type,
                                is_active=True
                            ).first()

                            if rule_for_signer:
                                if rule_for_signer.triggers_payment_order != is_signer_checked:
                                    rule_for_signer.triggers_payment_order = is_signer_checked
                                    rule_for_signer.created_by = user # به‌روزرسانی ایجادکننده به کاربر فعلی
                                    rule_for_signer.save(update_fields=['triggers_payment_order', 'created_by'])

            # 💡 مرحله نهایی (is_final_stage)
            # این باید پس از ایجاد/به‌روزرسانی همه قوانین تنظیم شود.
            # باید برای هر سازمان و هر entity_type، آخرین مرحله (بالاترین stage_order) را به عنوان is_final_stage تعیین کنیم.
            # بهتر است این منطق را به یک تابع جداگانه یا Signal منتقل کنید تا در هر save تکرار نشود
            # یا فقط برای مراحلی که تغییر کرده‌اند فراخوانی شود.
            for organization in Post.objects.filter(id__in=[p.id for p in self.posts_query]).values_list('organization', flat=True).distinct():
                 for entity_type, _ in ENTITY_TYPES:
                    final_stage_rule = AccessRule.objects.filter(
                        organization=organization,
                        entity_type=entity_type,
                        is_active=True
                    ).order_by('-stage_order').first()

                    # همه قوانین را به is_final_stage=False تنظیم کن
                    AccessRule.objects.filter(
                        organization=organization,
                        entity_type=entity_type,
                        is_final_stage=True
                    ).update(is_final_stage=False)

                    # مرحله نهایی را به True تنظیم کن
                    if final_stage_rule:
                        final_stage_rule.is_final_stage = True
                        final_stage_rule.save(update_fields=['is_final_stage'])

        logger.info("قوانین دسترسی پست با موفقیت ذخیره شدند.")

#---- NEW
ACTIONS_REQUIRING_STAGE = ['APPROVE', 'REJECTE', 'SIGN_PAYMENT']
class PostAccessRuleForm_new(forms.Form):
    def __init__(self, *args, **kwargs):
        self.posts_query = kwargs.pop('posts_query')
        super().__init__(*args, **kwargs)

        if not self.posts_query:
            return

        # --- Performance Boost: Fetch all existing rules in one query ---
        post_ids = [p.id for p in self.posts_query]
        existing_rules_qs = AccessRule.objects.filter(post_id__in=post_ids, is_active=True)
        self.existing_rules_map = {
            (rule.post_id, rule.entity_type, rule.action_type): rule
            for rule in existing_rules_qs
        }

        self.post_fields_data = []

        for post in self.posts_query:
            post_data = {'post': post, 'entity_groups': []}
            entity_groups = {}

            for entity_type, entity_label in ENTITY_TYPES:
                entity_key = (post.id, entity_type)
                entity_groups[entity_key] = {
                    'entity_label': entity_label,
                    'fields': {}
                }

                # --- Create fields for actions ---
                for action_type, action_label in ACTION_TYPES:
                    rule_key = (post.id, entity_type, action_type)
                    field_name = f'rule_{post.id}_{entity_type}_{action_type}'
                    existing_rule = self.existing_rules_map.get(rule_key)

                    if action_type in ACTIONS_REQUIRING_STAGE:
                        self.fields[field_name] = forms.IntegerField(
                            label=action_label,
                            required=False,
                            initial=existing_rule.stage_order if existing_rule else None,
                            widget=forms.NumberInput(attrs={
                                'class': 'form-control form-control-sm stage-order-input',
                                'placeholder': _('ترتیب مرحله'),
                                'min': '1'
                            })
                        )
                    else:
                        self.fields[field_name] = forms.BooleanField(
                            label=action_label,
                            required=False,
                            initial=bool(existing_rule),
                            widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                        )

                    entity_groups[entity_key]['fields'][action_type] = self[field_name]

            post_data['entity_groups'] = list(entity_groups.values())
            self.post_fields_data.append(post_data)

    def clean(self):
        cleaned_data = super().clean()
        has_any_rule = False

        # Check if at least one rule is defined
        for key, value in cleaned_data.items():
            if key.startswith('rule_') and value:
                has_any_rule = True
                break

        if not has_any_rule:
            raise forms.ValidationError(_('حداقل یک قانون دسترسی باید برای یکی از پست‌ها تعریف شود.'))

        return cleaned_data

    def save(self, user):
        logger.info(f"User '{user.username}' is saving access rules.")

        with transaction.atomic():
            post_ids = [p.id for p in self.posts_query]

            # --- Step 1: Deactivate all existing rules for the posts in the form ---
            # 💡 FIX: The result of .update() is a single integer, not a tuple.
            deactivated_count = AccessRule.objects.filter(post_id__in=post_ids).update(is_active=False)
            logger.info(f"Deactivated {deactivated_count} existing rules for {len(post_ids)} posts.")

            # --- Step 2: Create new rules based on form data ---
            rules_to_create = []
            for post in self.posts_query:
                for entity_type, _ in ENTITY_TYPES:
                    for action_type, _ in ACTION_TYPES:
                        field_name = f'rule_{post.id}_{entity_type}_{action_type}'
                        rule_value = self.cleaned_data.get(field_name)

                        if not rule_value:
                            continue

                        rule_data = {
                            'organization': post.organization,
                            'post': post,
                            'branch': post.branch,
                            'min_level': post.level,
                            'entity_type': entity_type,
                            'action_type': action_type,
                            'created_by': user,
                            'is_active': True,
                        }

                        if action_type in ACTIONS_REQUIRING_STAGE:
                            rule_data['stage_order'] = rule_value
                            # You might want a more descriptive default name
                            # e.g., fetching an existing stage name if the order already exists
                            existing_stage_name = AccessRule.objects.filter(
                                organization=post.organization,
                                entity_type=entity_type,
                                stage_order=rule_value
                            ).values_list('stage', flat=True).first()
                            rule_data['stage'] = existing_stage_name or f"مرحله {rule_value}"
                        else:  # Actions without stage
                            rule_data['stage_order'] = 0
                            rule_data['stage'] = ''

                        rules_to_create.append(AccessRule(**rule_data))

            if rules_to_create:
                # Use ignore_conflicts=False to ensure constraints are checked
                AccessRule.objects.bulk_create(rules_to_create, ignore_conflicts=False)
                logger.info(f"Successfully created/updated {len(rules_to_create)} access rules.")

            # --- Step 3: Update is_final_stage flags ---
            self._update_final_stage_flags(post_ids)

    def _update_final_stage_flags(self, post_ids):
        """Sets the is_final_stage flag for the highest stage_order within each org-entity group."""
        org_ids = Post.objects.filter(id__in=post_ids).values_list('organization_id', flat=True).distinct()

        for org_id in org_ids:
            for entity_type, _ in ENTITY_TYPES:
                # Find the highest stage order for active rules
                max_stage = AccessRule.objects.filter(
                    organization_id=org_id,
                    entity_type=entity_type,
                    is_active=True,
                    stage_order__gt=0
                ).aggregate(max_order=models.Max('stage_order'))

                max_order = max_stage.get('max_order')

                # Set all to False first
                AccessRule.objects.filter(
                    organization_id=org_id,
                    entity_type=entity_type
                ).update(is_final_stage=False)

                # Set the highest one(s) to True
                if max_order is not None:
                    AccessRule.objects.filter(
                        organization_id=org_id,
                        entity_type=entity_type,
                        stage_order=max_order
                    ).update(is_final_stage=True)
                    logger.info(f"Updated final stage for Org:{org_id}, Entity:{entity_type} to order {max_order}")


class PostAccessRuleHybridForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.posts_query = kwargs.pop('posts_query')
        self.user = kwargs.pop('user', None)  # اضافه کردن این خط
        super().__init__(*args, **kwargs)

        if not self.posts_query:
            return

        post_ids = [p.id for p in self.posts_query]
        existing_rules_map = {
            (rule.post_id, rule.entity_type, rule.action_type): rule
            for rule in AccessRule.objects.filter(post_id__in=post_ids, is_active=True)
        }

        self.post_fields_data = []
        for post in self.posts_query:
            post_data = {'post': post, 'entity_groups': []}
            for entity_type, entity_label in ENTITY_TYPES:
                entity_group = {'entity_label': entity_label, 'entity_code': entity_type, 'rules': []}
                for action_type, action_label in ACTION_TYPES:
                    field_name = f'rule__{post.id}__{entity_type}__{action_type}'
                    rule_key = (post.id, entity_type, action_type)
                    is_active = bool(existing_rules_map.get(rule_key))
                    self.fields[field_name] = forms.BooleanField(required=False, initial=is_active)
                    entity_group['rules'].append({
                        'action_label': action_label,
                        'field': self[field_name],
                    })
                post_data['entity_groups'].append(entity_group)
            self.post_fields_data.append(post_data)

    def save(self):
        try:
            with transaction.atomic():
                post_ids = [p.id for p in self.posts_query]
                AccessRule.objects.filter(post_id__in=post_ids).delete()

                successful_saves = 0
                for post in self.posts_query:
                    branch = getattr(post, 'branch', None)

                    for entity_type, _ in ENTITY_TYPES:
                        for action_type, _ in ACTION_TYPES:
                            field_name = f'rule__{post.id}__{entity_type}__{action_type}'
                            if self.cleaned_data.get(field_name):
                                try:
                                    AccessRule.objects.create(
                                        organization=post.organization,
                                        post=post,
                                        branch=branch,
                                        min_level=post.level,
                                        entity_type=entity_type,
                                        action_type=action_type,
                                        created_by=self.user,  # استفاده از self.user
                                        is_active=True,
                                        stage_order=1,
                                        stage=action_type
                                    )
                                    successful_saves += 1
                                except Exception as e:
                                    logger.error(f"Failed to create rule for post {post.id}: {str(e)}")
                                    continue

                return successful_saves > 0

        except Exception as e:
            logger.error(f"Critical error in save method: {str(e)}")
            raise