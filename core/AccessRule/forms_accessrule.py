# core/forms.py
from django import forms
from core.models import AccessRule, Post,WorkflowStage
from django.utils.translation import gettext_lazy as _
import logging
logger = logging.getLogger(__name__)
class AccessRuleForm(forms.ModelForm):
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
class old__PostAccessRuleForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("Initializing PostAccessRuleForm")

        self.posts = Post.objects.filter(is_active=True).select_related('organization')
        logger.info(f"Loaded {self.posts.count()} active posts: {[p.name for p in self.posts]}")

        self.stages = WorkflowStage.objects.filter(is_active=True)
        logger.info(f"Loaded {self.stages.count()} active stages: {[s.name for s in self.stages]}")

        if not self.posts:
            logger.warning("No active posts found. Form will be empty.")
        if not self.stages:
            logger.warning("No active stages found. Rule fields will lack stage selection.")

        for post in self.posts:
            # سطح
            level_field = f'post_{post.id}_level'
            self.fields[level_field] = forms.IntegerField(
                label=f"{_('سطح')} {post.name}",
                initial=post.level,
                min_value=1,
                required=False,
                widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 100px;'})
            )
            logger.debug(f"Added field: {level_field}")

            # قوانین
            for entity_type, entity_label in AccessRule.ENTITY_TYPES:
                for action_type, action_label in AccessRule.ACTION_TYPES:
                    rule_field = f'post_{post.id}_rule_{entity_type}_{action_type}'
                    self.fields[rule_field] = forms.BooleanField(
                        label=f"{entity_label} - {action_label}",
                        required=False,
                        initial=AccessRule.objects.filter(
                            post=post, entity_type=entity_type, action_type=action_type, is_active=True
                        ).exists(),
                        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                    )
                    logger.debug(f"Added field: {rule_field}")

                    stage_field = f'{rule_field}_stage'
                    self.fields[stage_field] = forms.ModelChoiceField(
                        queryset=self.stages,
                        label=_('مرحله'),
                        required=False,
                        empty_label=_('انتخاب مرحله'),
                        widget=forms.Select(attrs={'class': 'form-control', 'style': 'width: 200px; display: inline-block;'})
                    )
                    logger.debug(f"Added field: {stage_field}")

    def clean(self):
        cleaned_data = super().clean()
        logger.debug(f"Cleaned data: {cleaned_data}")
        for field_name in cleaned_data:
            if '_rule_' in field_name and not field_name.endswith('_stage'):
                if cleaned_data[field_name] and not cleaned_data.get(f'{field_name}_stage'):
                    self.add_error(f'{field_name}_stage', _('لطفاً مرحله را انتخاب کنید.'))
                    logger.warning(f"Validation error: Stage missing for {field_name}")
        return cleaned_data


from collections import defaultdict

# Assume these models are defined and imported correctly
# from core.models import Post, WorkflowStage, AccessRule, Organization


class OK___PostAccessRuleForm(forms.Form):
    # These constants should ideally come from your AccessRule model or a dedicated constants file
    MANAGED_ENTITIES = [
        ('FACTOR', _('فاکتور')),
        ('TANKHAH', _('تنخواه')),
        ('BUDGET', _('بودجه')),
        ('PAYMENTORDER', _('دستور پرداخت')),
        ('REPORTS', _('گزارشات')),
    ]
    MANAGED_ACTIONS = [
        ('APPROVE', _('تأیید')),
        ('REJECT', _('رد')),
        ('VIEW', _('مشاهده')),
        ('SIGN_PAYMENT', _('امضای دستور پرداخت')),
    ]

    def __init__(self, *args, **kwargs):
        user_organizations = kwargs.pop('user_organizations', None)
        super().__init__(*args, **kwargs)
        logger.info("Initializing PostAccessRuleForm")

        # Load active posts, optionally filtered by user's organizations
        posts_query = Post.objects.filter(is_active=True).select_related('organization')
        if user_organizations:
            # user_organizations is expected to be a QuerySet of organizations or a list of organization IDs
            posts_query = posts_query.filter(organization__in=user_organizations)
        # Order posts for consistent display in the template
        self.posts = posts_query.order_by('organization__name', 'level', 'name')
        logger.info(f"{self.posts.count()} active posts loaded: {[p.name for p in self.posts]}")

        # Load active workflow stages
        self.stages = WorkflowStage.objects.filter(is_active=True).order_by('order')
        logger.info(f"{self.stages.count()} active stages loaded: {[s.name for s in self.stages]}")

        if not self.posts:
            logger.warning("No active posts found. Form will be empty.")
        if not self.stages:
            logger.warning(
                "No active stages found. Rules will not have stages to select from if they were. This might indicate a problem.")

        # This list will hold the structured data for the template
        # Each dict contains 'post', 'level_field', and 'entity_groups'
        self.post_fields_data = []

        # Optimize by fetching all existing rules for the relevant posts once
        existing_rules = AccessRule.objects.filter(post__in=self.posts)
        existing_rules_map = {}
        # Key: (post_id, entity_type, action_type, stage_id) -> AccessRule object
        for rule in existing_rules:
            existing_rules_map[(rule.post.id, rule.entity_type, rule.action_type, rule.stage.id)] = rule
        logger.debug(f"Total existing rules for selected posts: {len(existing_rules_map)}")

        for post in self.posts:
            # 1. Post Level Field
            level_field_name = f'post_{post.id}_level'
            self.fields[level_field_name] = forms.IntegerField(
                label=_("سطح پست"),
                min_value=1,
                initial=post.level,
                required=False,
                widget=forms.NumberInput(attrs={'class': 'form-control w-25', 'title': _('سطح پست')})
            )

            post_data_for_template = {
                'post': post,
                'level_field': self[level_field_name],  # Use BoundField for template rendering
                'entity_groups': []  # To store rules grouped by entity type
            }

            # Group rules by entity type for the inner accordion in the template
            entity_rules_map = defaultdict(list)

            # 2. Access Rule Fields (checkboxes)
            for entity_code, entity_label in self.MANAGED_ENTITIES:
                for action_code, action_label in self.MANAGED_ACTIONS:
                    for stage_obj in self.stages:
                        # Unique field name for each specific rule (post, entity, action, stage)
                        rule_field_name = f'rule_{post.id}_{entity_code}_{action_code}_{stage_obj.id}'
                        signer_field_name = f'signer_{post.id}_{entity_code}_{action_code}_{stage_obj.id}'

                        # Check if this specific rule combination exists and is active
                        rule_key = (post.id, entity_code, action_code, stage_obj.id)
                        existing_rule = existing_rules_map.get(rule_key)

                        initial_rule_value = existing_rule.is_active if existing_rule else False
                        initial_signer_value = existing_rule.is_payment_order_signer if existing_rule else False

                        # Add the main rule checkbox field
                        self.fields[rule_field_name] = forms.BooleanField(
                            label="",  # Label is handled in the template
                            initial=initial_rule_value,
                            required=False,
                            widget=forms.CheckboxInput(attrs={
                                'class': 'form-check-input rule-checkbox',
                                'data-entity': entity_code,
                                'data-action': action_code,
                                'data-stage': stage_obj.id,
                                'data-post': post.id,
                            })
                        )
                        logger.debug(f"Added rule field: {rule_field_name} (initial: {initial_rule_value})")

                        # Add is_payment_order_signer checkbox only for 'SIGN_PAYMENT' action type
                        is_signer_field = None
                        if action_code == 'SIGN_PAYMENT':
                            self.fields[signer_field_name] = forms.BooleanField(
                                label=_("امضاکننده دستور پرداخت"),
                                initial=initial_signer_value,
                                required=False,
                                widget=forms.CheckboxInput(attrs={
                                    'class': 'form-check-input signer-checkbox',
                                    'data-rule-field': rule_field_name,  # Link to its main rule checkbox
                                })
                            )
                            is_signer_field = self[signer_field_name]  # Get BoundField

                        # Add the rule data to the temporary map for grouping by entity
                        entity_rules_map[entity_code].append({
                            'action_label': action_label,
                            'action_id': action_code,  # Use action_id for logic
                            'stage_obj': stage_obj,  # Pass the full stage object
                            'rule_field': self[rule_field_name],  # Pass BoundField for template rendering
                            'is_signer_field': is_signer_field,  # Pass BoundField or None
                        })

            # Convert the grouped rules into the structure for post_fields_data
            for entity_code, rules_list in entity_rules_map.items():
                entity_label = dict(self.MANAGED_ENTITIES).get(entity_code, _("نامشخص"))
                post_data_for_template['entity_groups'].append({
                    'entity_label': entity_label,
                    'entity_id': entity_code,
                    # Sort rules within each entity group for consistent display
                    'rules': sorted(rules_list, key=lambda x: (x['action_label'], x['stage_obj'].order))
                })
            # Sort entity groups for consistent display within a post
            post_data_for_template['entity_groups'].sort(key=lambda x: x['entity_label'])

            self.post_fields_data.append(post_data_for_template)

    def clean(self):
        cleaned_data = super().clean()
        logger.debug("شروع فرآیند اعتبارسنجی فرم PostAccessRuleForm.")

        # اعتبارسنجی سطوح پست‌ها بر اساس سلسله‌مراتب والد-فرزندی
        for post_data in self.post_fields_data:
            post = post_data['post']
            level_field_name = post_data['level_field'].name
            # سطح جدید را از cleaned_data دریافت کنید، یا اگر تغییر نکرده، سطح فعلی پست را در نظر بگیرید.
            new_level = cleaned_data.get(level_field_name)

            # محاسبه سطح مورد انتظار بر اساس والد پست
            # اگر پستی والد نداشته باشد، سطح مورد انتظارش 1 است.
            # در غیر این صورت، سطح مورد انتظار، سطح والد + 1 است.
            expected_level = post.parent.level + 1 if post.parent else 1

            # تنها در صورتی اعتبارسنجی کنید که new_level مقداری داشته باشد و با سطح مورد انتظار تفاوت داشته باشد.
            if new_level is not None and new_level != expected_level:
                # یک خطا برای فیلد سطح خاص اضافه کنید
                self.add_error(
                    level_field_name,
                    _("سطح پست باید بر اساس والد ({}) {} باشد.").format(
                        post.parent.name if post.parent else _("بدون والد"),
                        expected_level
                    )
                )
                logger.warning(
                    f"سطح نامعتبر {new_level} برای پست {post.name}. مورد انتظار: {expected_level}. والد: {post.parent.name if post.parent else 'None'}")

        # اطمینان از انتخاب حداقل یک قانون (اعتبارسنجی موجود شما)
        # این بررسی ممکن است نیاز به تنظیم داشته باشد اگر فیلدهای 'rule_' شما مستقیماً در سطح بالای cleaned_data نباشند.
        # این فرض می‌کند rule_field.name مستقیماً 'rule_{post.id}_...' است.
        if not any(value for name, value in cleaned_data.items() if name.startswith('rule_') and value):
            self.add_error(None, _("حداقل یک قانون دسترسی باید انتخاب شود."))
            logger.warning("هیچ قانون دسترسی انتخاب نشده است.")

        logger.debug(f"اعتبارسنجی فرم به پایان رسید. کلیدهای داده‌های پاک‌شده: {list(cleaned_data.keys())}")
        return cleaned_data

    def save(self, user=None):  # آرگومان user را بپذیرید
        logger.info("شروع عملیات ذخیره قوانین دسترسی.")

        managed_post_ids = {post_data['post'].id for post_data in self.post_fields_data}
        if not managed_post_ids:
            logger.info("هیچ پستی توسط این فرم مدیریت نمی‌شود. از ذخیره خارج می‌شویم.")
            return

        # 1. به‌روزرسانی سطح پست‌ها
        posts_to_update_individually = []
        for post_data in self.post_fields_data:
            post_obj = post_data['post']
            level_field_name = post_data['level_field'].name
            new_level = self.cleaned_data.get(level_field_name)

            if new_level is not None and new_level != post_obj.level:
                # برای ثبت تاریخچه و فراخوانی Post.save()، پست را به لیست اضافه کنید
                # PostHistory در Post.save() با استفاده از changed_by ایجاد خواهد شد
                post_obj.level = new_level  # سطح را روی آبجکت تغییر دهید
                posts_to_update_individually.append(post_obj)
                logger.debug(
                    f"پست {post_obj.name} (ID: {post_obj.id}) برای به‌روزرسانی سطح به {new_level} آماده می‌شود.")

        if posts_to_update_individually:
            for post_obj in posts_to_update_individually:
                # فراخوانی save() روی هر پست به صورت تک‌تک، Post.save() را اجرا می‌کند
                # این کار باعث ثبت تاریخچه می‌شود
                post_obj.save(changed_by=user)  # changed_by را به save مدل ارسال کنید
            logger.info(f"سطوح {len(posts_to_update_individually)} پست به صورت تک‌تک به‌روزرسانی شد.")

        # 2. حذف قوانین قبلی برای پست‌های مدیریت شده
        AccessRule.objects.filter(post__id__in=managed_post_ids).delete()
        logger.info(f"قوانین دسترسی موجود برای پست‌های با IDهای: {list(managed_post_ids)} حذف شد.")

        # 3. ایجاد قوانین دسترسی جدید
        rules_to_create = []
        for post_data in self.post_fields_data:
            post_obj = post_data['post']
            for entity_group in post_data['entity_groups']:
                entity_type = entity_group['entity_id']
                for rule_item in entity_group['rules']:
                    action_type = rule_item['action_id']
                    stage_obj = rule_item['stage_obj']

                    rule_field_name = rule_item['rule_field'].name
                    is_active = self.cleaned_data.get(rule_field_name, False)

                    is_payment_order_signer = False
                    if rule_item['is_signer_field'] and action_type == 'SIGN_PAYMENT':
                        signer_field_name = rule_item['is_signer_field'].name
                        is_payment_order_signer = self.cleaned_data.get(signer_field_name, False)
                        # اگر قانون اصلی فعال نیست، امضاکننده هم نباید فعال باشد
                        if not is_active:
                            is_payment_order_signer = False

                    if is_active:  # فقط قوانینی که فعال هستند را ایجاد کنید
                        rules_to_create.append(
                            AccessRule(
                                post=post_obj,
                                organization=post_obj.organization,
                                branch=post_obj.branch or '',  # اطمینان از مقداردهی صحیح branch
                                stage=stage_obj,
                                action_type=action_type,
                                entity_type=entity_type,
                                is_active=True,
                                is_payment_order_signer=is_payment_order_signer
                            )
                        )
                        logger.debug(
                            f"قانون برای ایجاد آماده می‌شود: پست={post_obj.name}, موجودیت={entity_type}, اقدام={action_type}, مرحله={stage_obj.name}, امضاکننده={is_payment_order_signer}")

        if rules_to_create:
            # از ignore_conflicts=True برای جلوگیری از خطای تکراری در صورت وجود UniqueConstraint استفاده کنید
            AccessRule.objects.bulk_create(rules_to_create, ignore_conflicts=True)
            logger.info(f"با موفقیت {len(rules_to_create)} قانون دسترسی جدید ایجاد شد.")
        else:
            logger.info("هیچ قانون فعالی انتخاب نشد، بنابراین هیچ قانون جدیدی ایجاد نشد.")

        logger.info("عملیات ذخیره قوانین دسترسی به پایان رسید.")

    # def clean(self):
    #     cleaned_data = super().clean()
    #     logger.debug("Starting form cleaning process.")
    #
    #     # No specific cross-field validation needed here as the form structure
    #     # implies the stage is tied to the rule field name itself.
    #     # The JS ensures signer checkbox is disabled if rule is unchecked.
    #
    #     # Example of a general form-level validation (as in your original code)
    #     if not any(value for name, value in cleaned_data.items() if name.startswith('rule_') and value):
    #         self.add_error(None, _("حداقل یک قانون دسترسی باید انتخاب شود."))
    #         logger.warning("No access rules selected.")
    #
    #     logger.debug(f"Form cleaning complete. Cleaned data keys: {list(cleaned_data.keys())}")
    #     return cleaned_data

    # def save(self):
    #     """
    #     Saves the access rules based on the cleaned_data.
    #     This method will delete existing rules for the managed posts and create new ones.
    #     """
    #     logger.info("Starting save operation for Access Rules.")
    #
    #     # Collect post IDs that were part of this form submission
    #     managed_post_ids = {post_data['post'].id for post_data in self.post_fields_data}
    #     if not managed_post_ids:
    #         logger.info("No posts managed by this form submission. Exiting save.")
    #         return
    #
    #     # 1. Update Post Levels
    #     posts_to_update = []
    #     for post_data in self.post_fields_data:
    #         post_obj = post_data['post']
    #         level_field_name = post_data['level_field'].name
    #         new_level = self.cleaned_data.get(level_field_name)
    #
    #         if new_level is not None and new_level != post_obj.level:
    #             post_obj.level = new_level
    #             posts_to_update.append(post_obj)
    #             logger.debug(f"Post {post_obj.name} (ID: {post_obj.id}) level updated to {new_level}")
    #
    #     if posts_to_update:
    #         Post.objects.bulk_update(posts_to_update, ['level'])
    #         logger.info(f"Updated levels for {len(posts_to_update)} posts.")
    #
    #     # 2. Delete existing AccessRules for the managed posts
    #     # We delete all existing rules for these posts and then recreate them
    #     AccessRule.objects.filter(post__id__in=managed_post_ids).delete()
    #     logger.info(f"Deleted existing access rules for posts with IDs: {list(managed_post_ids)}")
    #
    #     # 3. Create new AccessRules based on the form's cleaned data
    #     rules_to_create = []
    #     for post_data in self.post_fields_data:
    #         post_obj = post_data['post']
    #         for entity_group in post_data['entity_groups']:
    #             entity_type = entity_group['entity_id']
    #             for rule_item in entity_group['rules']:
    #                 action_type = rule_item['action_id']
    #                 stage_obj = rule_item['stage_obj']
    #
    #                 rule_field_name = rule_item['rule_field'].name
    #                 is_active = self.cleaned_data.get(rule_field_name, False)
    #
    #                 is_payment_order_signer = False
    #                 if rule_item['is_signer_field'] and action_type == 'SIGN_PAYMENT':
    #                     signer_field_name = rule_item['is_signer_field'].name
    #                     is_payment_order_signer = self.cleaned_data.get(signer_field_name, False)
    #                     # If the main rule is not active, the signer should also not be active
    #                     if not is_active:
    #                         is_payment_order_signer = False
    #
    #                 if is_active:  # Only create rules that are active
    #                     rules_to_create.append(
    #                         AccessRule(
    #                             post=post_obj,
    #                             organization=post_obj.organization,
    #                             branch=post_obj.branch,  # Assuming branch is a CharField, otherwise handle None
    #                             stage=stage_obj,
    #                             action_type=action_type,
    #                             entity_type=entity_type,
    #                             is_active=True,  # Explicitly set to True for created rules
    #                             is_payment_order_signer=is_payment_order_signer
    #                         )
    #                     )
    #                     logger.debug(
    #                         f"Preparing to create rule: Post={post_obj.name}, Entity={entity_type}, Action={action_type}, Stage={stage_obj.name}, Signer={is_payment_order_signer}")
    #
    #     if rules_to_create:
    #         AccessRule.objects.bulk_create(rules_to_create,
    #                                        ignore_conflicts=True)  # Use ignore_conflicts for safety if unique_together is set
    #         logger.info(f"Successfully created {len(rules_to_create)} new access rules.")
    #     else:
    #         logger.info("No active rules were selected, so no new rules were created.")
    #
    #     logger.info("Access Rule save operation complete.")


# budgets/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _
from core.models import Post, WorkflowStage, AccessRule  # اطمینان حاصل کنید که مدل‌های مورد نیاز وارد شده‌اند
import logging

logger = logging.getLogger(__name__)

# لیست‌های ثابت برای انواع موجودیت و اقدام
MANAGED_ENTITIES = [
    ('FACTOR', _('فاکتور')),
    ('TANKHAH', _('تنخواه')),
    ('BUDGET', _('بودجه')),
    ('PAYMENTORDER', _('دستور پرداخت')),
    ('REPORTS', _('گزارشات')),
]

MANAGED_ACTIONS = [
    ('APPROVE', _('تأیید')),
    ('REJECT', _('رد')),
    ('VIEW', _('مشاهده')),
    ('SIGN_PAYMENT', _('امضای دستور پرداخت')),
]

# اقدامات نیازمند انتخاب مرحله
ACTIONS_REQUIRING_STAGE_SELECTION = ['APPROVE', 'REJECT']


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
                        initial_stage_id = str(current_rule.stage.id) if current_rule and current_rule.stage else ''

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
                        initial_stage_id = str(current_rule.stage.id) if current_rule and current_rule.stage else ''

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