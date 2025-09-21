# core/forms.py
import logging
from django import forms
from django.db import transaction, models, IntegrityError
from django.db.models import Max
from django.utils.translation import gettext_lazy as _

from core.models import Post, Status  # اطمینان حاصل کنید که مدل‌های مورد نیاز وارد شده‌اند
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

# این فرم برای این ویو است PostAccessRuleAssignView که قوانین را ویزاردی مینویسد
class PostAccessRuleHybridForm(forms.Form):
# این فرم برای این ویو است PostAccessRuleAssignView که قوانین را ویزاردی مینویسد
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

# new Form - Edit Accept Post With Level
from collections import defaultdict
class PostAccessRuleAssignForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop('organization')
        self.entity_type = kwargs.pop('entity_type')
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

        WORKFLOW_ACTIONS = [a for a in ACTION_TYPES if a[0] not in ACTIONS_WITHOUT_STAGE]
        STATIC_ACTIONS = [a for a in ACTION_TYPES if a[0] in ACTIONS_WITHOUT_STAGE]

        posts = Post.objects.filter(organization=self.organization, is_active=True).order_by('level', 'name')
        existing_rules = AccessRule.objects.filter(organization=self.organization, entity_type=self.entity_type)
        rules_map = {(rule.post_id, rule.action_type): rule for rule in existing_rules}
        stage_names_map = {rule.stage_order: rule.stage for rule in existing_rules if rule.stage_order}

        # --- بخش ۱: گردش کار (بر اساس level) ---
        self.levels_data = defaultdict(lambda: {'posts_data': [], 'stage_name_field': None})

        for post in posts:
            # یک دیکشنری برای هر پست ایجاد می‌کنیم
            post_data = {'post_obj': post, 'workflow_actions': []}

            for action_code, action_label in WORKFLOW_ACTIONS:
                field_name = f'w_rule__{post.level}__{post.id}__{action_code}'
                self.fields[field_name] = forms.BooleanField(
                    required=False, label=action_label, initial=bool(rules_map.get((post.id, action_code)))
                )
                post_data['workflow_actions'].append(self[field_name])

            self.levels_data[post.level]['posts_data'].append(post_data)

        for level, data in self.levels_data.items():
            stage_name_field_name = f'stage_name__{level}'
            self.fields[stage_name_field_name] = forms.CharField(
                label=f"نام مرحله برای سطح {level}", required=False, initial=stage_names_map.get(level, ''),
                widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
            )
            data['stage_name_field'] = self[stage_name_field_name]

        # --- بخش ۲: دسترسی‌های عمومی ---
        self.static_access_data = []
        for post in posts:
            post_data = {'post_obj': post, 'static_actions': []}
            for action_code, action_label in STATIC_ACTIONS:
                field_name = f's_rule__{post.id}__{action_code}'
                self.fields[field_name] = forms.BooleanField(
                    required=False, label=action_label, initial=bool(rules_map.get((post.id, action_code)))
                )
                post_data['static_actions'].append(self[field_name])
            self.static_access_data.append(post_data)

    def save(self):
        try:
            with transaction.atomic():
                # حذف تمام قوانین قبلی برای این سازمان و موجودیت
                AccessRule.objects.filter(
                    organization=self.organization,
                    entity_type=self.entity_type
                ).delete()

                # ایجاد قوانین جدید بر اساس داده‌های فرم
                for level, data in self.levels_data.items():
                    stage_name = self.cleaned_data.get(f'stage_name__{level}') or f"مرحله سطح {level}"

                    for post in data['posts']:
                        for action_code, _ in ACTION_TYPES:
                            field_name = f'rule__{level}__{post.id}__{action_code}'
                            if self.cleaned_data.get(field_name):
                                AccessRule.objects.create(
                                    organization=self.organization,
                                    post=post,
                                    entity_type=self.entity_type,
                                    stage_order=level,  # <-- نکته کلیدی: stage_order همان level است
                                    stage=stage_name,  # نام مرحله تعریف شده برای آن سطح
                                    action_type=action_code,
                                    min_level=post.level,
                                    branch=post.branch,
                                    created_by=self.user,
                                    is_active=True
                                )
        except Exception as e:
            logger.error(f"Critical error in PostAccessRuleAssignForm save: {e}", exc_info=True)
            raise

#--------------------------------------------------------------
'''
دسترسی‌های گردش کار (Workflow Permissions):
ماهیت: ترتیبی، مرحله‌ای، بر اساس سطح (level).
اقدامات: APPROVE, REJECT, FINAL_APPROVE, SUBMIT.
پیاده‌سازی: دقیقاً همان راه حلی که در پاسخ قبلی ارائه شد (گروه‌بندی بر اساس Post.level و تعریف نام مرحله برای هر سطح).
دسترسی‌های عمومی/ثابت (Static Permissions):
ماهیت: غیرترتیبی، باینری (دارد یا ندارد)، مستقل از سطح و مرحله.
اقدامات: VIEW, EDIT, CREATE, DELETE, SIGN_PAYMENT.
پیاده‌سازی: برای هر پست، یک سری چک‌باکس ساده برای این اقدامات وجود خواهد داشت، بدون نیاز به تعریف مرحله یا ترتیب.
دسترسی سلسله مراتبی (Hierarchical Access):
این یک منطق در بک‌اند است. هر زمان که سیستم در حال بررسی یک مجوز است (مثلاً user.has_perm('tankhah.factor_edit', factor_object)), تابع بررسی‌کننده باید نه تنها قوانین سازمان خود فاکتور، بلکه قوانین سازمان‌های والد آن را نیز در نظر بگیرد.
بازطراحی نهایی: فرم و ویو یکپارچه (Unified View)
ما یک ویو و فرم واحد ایجاد می‌کنیم که با استفاده از تب (Tabs) این دو نوع دسترسی را از هم جدا می‌کند.
مرحله ۱: بازنویسی فرم (UnifiedAccessForm)
'''

ACTIONS_WITHOUT_STAGE = [ 'VIEW', 'EDIT', 'CREATE', 'DELETE', 'SIGN_PAYMENT' ]

# این import ها بسیار مهم هستند.
from core.models import Post, Organization, Status

# تنظیم یک لاگر مشخص برای این فرم
logger = logging.getLogger('UnifiedAccessFormLogger')
logger.setLevel(logging.DEBUG)
class UnifiedAccessForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop('organization')
        self.entity_type = kwargs.pop('entity_type')
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

        logger.debug("\n" + "=" * 60)
        logger.debug("= START: UnifiedAccessForm Initialization")
        logger.debug(f"= Organization: '{self.organization.name}' (PK: {self.organization.pk})")
        logger.debug(f"= Entity Type: {self.entity_type}")
        logger.debug("=" * 60 + "\n")

        # مرحله ۱: بررسی ثابت‌ها
        logger.debug("--- Step 1: Checking Constants ---")
        if not ACTION_TYPES:
            logger.error("FATAL: ACTION_TYPES is empty or not imported correctly!")
        else:
            logger.debug(f"ACTION_TYPES loaded successfully ({len(ACTION_TYPES)} items).")

        if not ACTIONS_WITHOUT_STAGE:
            logger.error("FATAL: ACTIONS_WITHOUT_STAGE is empty or not defined!")
        else:
            logger.debug(f"ACTIONS_WITHOUT_STAGE loaded successfully ({len(ACTIONS_WITHOUT_STAGE)} items).")

        # مرحله ۲: تقسیم‌بندی اقدامات
        logger.debug("\n--- Step 2: Categorizing Actions ---")
        WORKFLOW_ACTIONS = [a for a in ACTION_TYPES if a[0] not in ACTIONS_WITHOUT_STAGE]
        STATIC_ACTIONS = [a for a in ACTION_TYPES if a[0] in ACTIONS_WITHOUT_STAGE]
        logger.debug(f"WORKFLOW_ACTIONS calculated: {WORKFLOW_ACTIONS}")
        logger.debug(f"STATIC_ACTIONS calculated: {STATIC_ACTIONS}")

        # مرحله ۳: واکشی پست‌ها
        logger.debug("\n--- Step 3: Fetching Posts ---")
        posts = Post.objects.filter(organization=self.organization, is_active=True).order_by('level', 'name')
        logger.debug(f"Found {posts.count()} active posts for this organization.")

        if not posts.exists():
            logger.warning("No active posts found. Aborting form field creation.")
            self.levels_data = {}
            self.static_access_data = []
            return

        # مرحله ۴: واکشی قوانین موجود
        logger.debug("\n--- Step 4: Fetching Existing Rules ---")
        existing_rules = AccessRule.objects.filter(organization=self.organization, entity_type=self.entity_type)
        logger.debug(f"Found {existing_rules.count()} existing rules for this org/entity.")
        rules_map = {(rule.post_id, rule.action_type): rule for rule in existing_rules}
        stage_names_map = {rule.stage_order: rule.stage for rule in existing_rules if rule.stage_order}
        logger.debug(
            f"Created rules_map with {len(rules_map)} items and stage_names_map with {len(stage_names_map)} items.")

        # مرحله ۵: ساخت فیلدهای فرم
        logger.debug("\n--- Step 5: Building Form Fields ---")
        self.levels_data = defaultdict(lambda: {'posts_data': [], 'stage_name_field': None})
        self.static_access_data = []
        total_fields_created = 0

        # بخش گردش کار
        logger.debug("--- Building WORKFLOW fields ---")
        if WORKFLOW_ACTIONS:
            for post in posts:
                post_data_dict = {'post_obj': post, 'workflow_actions': []}
                for action_code, action_label in WORKFLOW_ACTIONS:
                    field_name = f'w_rule__{post.level}__{post.id}__{action_code}'
                    self.fields[field_name] = forms.BooleanField(required=False, label=action_label,
                                                                 initial=bool(rules_map.get((post.id, action_code))))
                    post_data_dict['workflow_actions'].append(self[field_name])
                    total_fields_created += 1
                self.levels_data[post.level]['posts_data'].append(post_data_dict)

            for level, data in self.levels_data.items():
                stage_name_field_name = f'stage_name__{level}'
                self.fields[stage_name_field_name] = forms.CharField(label=f"نام مرحله برای سطح {level}",
                                                                     required=False,
                                                                     initial=stage_names_map.get(level, ''),
                                                                     widget=forms.TextInput(attrs={
                                                                         'class': 'form-control form-control-sm'}))
                data['stage_name_field'] = self[stage_name_field_name]
                total_fields_created += 1
        else:
            logger.warning("WORKFLOW_ACTIONS list is empty. Skipping workflow field creation.")

        # بخش دسترسی‌های عمومی
        logger.debug("--- Building STATIC ACCESS fields ---")
        if STATIC_ACTIONS:
            for post in posts:
                post_data_dict = {'post_obj': post, 'static_actions': []}
                for action_code, action_label in STATIC_ACTIONS:
                    field_name = f's_rule__{post.id}__{action_code}'
                    self.fields[field_name] = forms.BooleanField(required=False, label=action_label,
                                                                 initial=bool(rules_map.get((post.id, action_code))))
                    post_data_dict['static_actions'].append(self[field_name])
                    total_fields_created += 1
                self.static_access_data.append(post_data_dict)
        else:
            logger.warning("STATIC_ACTIONS list is empty. Skipping static access field creation.")

        logger.debug("\n" + "=" * 60)
        logger.debug(f"= FINISHED: UnifiedAccessForm Initialization")
        logger.debug(f"= Total fields created in form: {len(self.fields)} (calculated: {total_fields_created})")
        logger.debug(f"= Final levels_data keys: {list(self.levels_data.keys())}")
        logger.debug(f"= Final static_access_data length: {len(self.static_access_data)}")
        logger.debug("=" * 60 + "\n")

    def save(self):
        with transaction.atomic():
            AccessRule.objects.filter(organization=self.organization, entity_type=self.entity_type).delete()
            # ۱. ذخیره قوانین گردش کار
            if self.cleaned_data:
                for level, data in self.levels_data.items():
                    stage_name = self.cleaned_data.get(f'stage_name__{level}') or f"مرحله سطح {level}"
                    for post_data in data['posts_data']:
                        post = post_data['post_obj']
                        for action_field in post_data['workflow_actions']:
                            if self.cleaned_data.get(action_field.name):
                                action_code = action_field.name.split('__')[-1]
                                AccessRule.objects.create(organization=self.organization, post=post,
                                                          entity_type=self.entity_type, stage_order=level,
                                                          stage=stage_name, action_type=action_code,
                                                          min_level=post.level, branch=post.branch,
                                                          created_by=self.user, is_active=True)
                # ۲. ذخیره قوانین عمومی
                for post_data in self.static_access_data:
                    post = post_data['post_obj']
                    for action_field in post_data['static_actions']:
                        if self.cleaned_data.get(action_field.name):
                            action_code = action_field.name.split('__')[-1]
                            AccessRule.objects.create(organization=self.organization, post=post,
                                                      entity_type=self.entity_type, action_type=action_code,
                                                      stage_order=None, stage=None, min_level=post.level,
                                                      branch=post.branch, created_by=self.user, is_active=True)


class WorkflowForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop('organization')
        self.entity_type = kwargs.pop('entity_type')
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

        # فقط اقدامات مربوط به گردش کار را در نظر می‌گیریم
        WORKFLOW_ACTIONS = [a for a in ACTION_TYPES if a[0] not in ACTIONS_WITHOUT_STAGE]

        # --- حل باگ لود نشدن تمام سطوح ---
        # مرحله ۱: پیدا کردن سازمان و تمام زیرمجموعه‌های آن به صورت بازگشتی
        orgs_to_include = [self.organization]
        org_queue = [self.organization]
        while org_queue:
            current_org = org_queue.pop(0)
            sub_orgs = list(current_org.sub_organizations.all())  # فرض بر related_name='sub_organizations'
            orgs_to_include.extend(sub_orgs)
            org_queue.extend(sub_orgs)

        org_ids_to_include = [org.pk for org in orgs_to_include]
        logger.debug(f"Querying for posts in organization IDs: {org_ids_to_include}")

        # مرحله ۲: اجرای کوئری برای تمام سازمان‌های پیدا شده
        self.posts = Post.objects.filter(
            organization_id__in=org_ids_to_include,
            is_active=True
        ).select_related('organization', 'branch').order_by('level', 'name')

        logger.debug(f"Found {self.posts.count()} active posts across all related organizations.")

        if not self.posts.exists():
            self.levels_data = {}
            return

        existing_rules = AccessRule.objects.filter(
            organization=self.organization,  # قوانین همچنان برای سازمان اصلی تعریف می‌شوند
            entity_type=self.entity_type,
            action_type__in=[code for code, label in WORKFLOW_ACTIONS]
        )
        rules_map = {(rule.post_id, rule.action_type): rule for rule in existing_rules}
        stage_names_map = {rule.stage_order: rule.stage for rule in existing_rules if rule.stage_order}

        self.levels_data = defaultdict(lambda: {'posts_data': [], 'stage_name_field': None})
        for post in self.posts:
            post_data_dict = {'post_obj': post, 'workflow_actions': []}
            for action_code, action_label in WORKFLOW_ACTIONS:
                field_name = f'w_rule__{post.level}__{post.id}__{action_code}'
                self.fields[field_name] = forms.BooleanField(required=False, label=action_label,
                                                             initial=bool(rules_map.get((post.id, action_code))))
                post_data_dict['workflow_actions'].append(self[field_name])
            self.levels_data[post.level]['posts_data'].append(post_data_dict)

        for level, data in self.levels_data.items():
            stage_name_field_name = f'stage_name__{level}'
            self.fields[stage_name_field_name] = forms.CharField(label=f"نام مرحله برای سطح {level}", required=False,
                                                                 initial=stage_names_map.get(level, ''),
                                                                 widget=forms.TextInput(
                                                                     attrs={'class': 'form-control form-control-sm'}))
            data['stage_name_field'] = self[stage_name_field_name]

    def save(self):
        WORKFLOW_ACTION_CODES = [a[0] for a in ACTION_TYPES if a[0] not in ACTIONS_WITHOUT_STAGE]

        with transaction.atomic():
            # فقط قوانین گردش کار قبلی برای سازمان اصلی را حذف می‌کنیم
            AccessRule.objects.filter(
                organization=self.organization,
                entity_type=self.entity_type,
                action_type__in=WORKFLOW_ACTION_CODES
            ).delete()

            # قوانین گردش کار جدید را بر اساس فرم ایجاد می‌کنیم
            if self.cleaned_data:
                for level, data in self.levels_data.items():
                    stage_name = self.cleaned_data.get(f'stage_name__{level}') or f"مرحله سطح {level}"
                    for post_data in data['posts_data']:
                        post = post_data['post_obj']
                        # قانون فقط برای پستی ایجاد می‌شود که متعلق به سازمان اصلی باشد
                        if post.organization == self.organization:
                            for action_field in post_data['workflow_actions']:
                                if self.cleaned_data.get(action_field.name):
                                    action_code = action_field.name.split('__')[-1]
                                    AccessRule.objects.create(
                                        organization=self.organization, post=post, entity_type=self.entity_type,
                                        stage_order=level, stage=stage_name, action_type=action_code,
                                        min_level=post.level, branch=post.branch, created_by=self.user, is_active=True
                                    )
