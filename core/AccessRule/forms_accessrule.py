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

class ____PostAccessRuleForm(forms.Form):
    def __init__(self, *args, **kwargs):
        user_organizations = kwargs.pop('user_organizations', None)
        super().__init__(*args, **kwargs)
        logger.info("مقداردهی اولیه PostAccessRuleForm")

        # بارگذاری پست‌های فعال
        posts_query = Post.objects.filter(is_active=True).select_related('organization')
        if user_organizations:
            posts_query = posts_query.filter(organization__in=user_organizations)
        self.posts = posts_query
        logger.info(f"{self.posts.count()} پست فعال بارگذاری شد: {[p.name for p in self.posts]}")

        # بارگذاری مراحل فعال
        self.stages = WorkflowStage.objects.filter(is_active=True)
        logger.info(f"{self.stages.count()} مرحله فعال بارگذاری شد: {[s.name for s in self.stages]}")

        # هشدار در صورت نبود پست یا مرحله
        if not self.posts:
            logger.warning("هیچ پست فعالی یافت نشد. فرم خالی خواهد بود")
        if not self.stages:
            logger.warning("هیچ مرحله فعالی یافت نشد. فیلدهای قانون بدون انتخاب مرحله خواهند بود")

        # تولید ساختار post_fields برای قالب
        self.post_fields = []
        valid_action_types = dict(AccessRule.ACTION_TYPES)
        valid_entity_types = dict(AccessRule.ENTITY_TYPES)

        try:
            for post in self.posts:
                post_data = {
                    'post': post,
                    'level_field': {
                        'name': f'post_{post.id}_level',
                        'label': f"{_('سطح')} {post.name}",
                        'value': post.level,
                    },
                    'rule_fields': []
                }

                # فیلد سطح پست
                self.fields[f'post_{post.id}_level'] = forms.IntegerField(
                    label=f"{_('سطح')} {post.name}",
                    initial=post.level,
                    min_value=1,
                    required=False,
                    widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 100px'})
                )
                logger.debug(f"فیلد سطح برای پست {post.id} اضافه شد")

                # تولید فیلدهای قوانین
                for entity_type, entity_label in AccessRule.ENTITY_TYPES:
                    if entity_type not in valid_entity_types:
                        logger.warning(f"نوع موجودیت نامعتبر رد شد: {entity_type}")
                        continue
                    for action_type, action_label in AccessRule.ACTION_TYPES:
                        if action_type not in valid_action_types:
                            logger.warning(f"نوع اقدام نامعتبر رد شد: {action_type}")
                            continue
                        rule_field_name = f'post_{post.id}_rule_{entity_type}_{action_type}'
                        stage_field_name = f'{rule_field_name}_stage'

                        # بررسی قوانین موجود
                        rule_exists = AccessRule.objects.filter(
                            post=post,
                            entity_type=entity_type,
                            action_type=action_type,
                            is_active=True
                        ).first()
                        rule_initial = bool(rule_exists)
                        stage_initial = rule_exists.stage.id if rule_exists and rule_exists.stage else None

                        # فیلد قانون
                        self.fields[rule_field_name] = forms.BooleanField(
                            label=f"{entity_label} - {action_label}",
                            required=False,
                            initial=rule_initial,
                            widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                        )
                        logger.debug(f"فیلد قانون اضافه شد: {rule_field_name}")

                        # فیلد مرحله
                        self.fields[stage_field_name] = forms.ModelChoiceField(
                            queryset=self.stages,
                            label=_('مرحله'),
                            required=False,
                            initial=stage_initial,
                            empty_label=_('انتخاب مرحله'),
                            widget=forms.Select(attrs={'class': 'form-control', 'style': 'width: 200px'})
                        )
                        logger.debug(f"فیلد مرحله اضافه شد: {stage_field_name}")

                        # اضافه کردن به post_fields برای قالب
                        post_data['rule_fields'].append({
                            'entity_type': entity_type,
                            'action_type': action_type,
                            'entity_label': entity_label,
                            'action_label': action_label,
                            'rule_field_name': rule_field_name,
                            'stage_field_name': stage_field_name,
                            'rule_label': f"{entity_label} - {action_label}",
                            'rule_value': rule_initial,
                            'stage_value': stage_initial,
                        })

                self.post_fields.append(post_data)
        except Exception as e:
            logger.exception(f"خطا در مقداردهی اولیه فرم: {str(e)}")
            raise

    def clean(self):
        cleaned_data = super().clean()
        logger.debug("شروع اعتبارسنجی داده‌های فرم: %s", cleaned_data)

        valid_action_types = dict(AccessRule.ACTION_TYPES).keys()
        valid_entity_types = dict(AccessRule.ENTITY_TYPES).keys()
        updates = {}

        try:
            for field_name in list(cleaned_data.keys()):
                if '_rule_' in field_name and not field_name.endswith('_stage'):
                    parts = field_name.split('_')
                    if len(parts) < 5:
                        self.add_error(field_name, "فرمت فیلد نامعتبر است.")
                        continue
                    entity_type = parts[3]
                    action_type = 'SIGN_PAYMENT' if field_name.endswith('_SIGN_PAYMENT') else parts[4]

                    if entity_type not in valid_entity_types:
                        self.add_error(field_name, f"نوع موجودیت {entity_type} نامعتبر است.")
                        continue
                    if action_type not in valid_action_types:
                        self.add_error(field_name, f"نوع اقدام {action_type} نامعتبر است.")
                        continue

                    rule_value = cleaned_data.get(field_name)
                    stage_field_name = f'{field_name}_stage'
                    stage_value = cleaned_data.get(stage_field_name)

                    if rule_value and not stage_value:
                        default_stage = self.stages.first()
                        if default_stage:
                            updates[stage_field_name] = default_stage
                            logger.info(f"مرحله پیش‌فرض {default_stage.name} برای {field_name} تنظیم شد")
                        else:
                            self.add_error(stage_field_name, "هیچ مرحله فعالی وجود ندارد.")
                    elif rule_value and stage_value:
                        logger.debug(f"مرحله {stage_value.name} برای {field_name} انتخاب شده است")
                    elif not rule_value:
                        updates[stage_field_name] = None
                        logger.debug(f"مرحله برای {field_name} پاک شد زیرا قانون انتخاب نشده است")

            cleaned_data.update(updates)

            if not any(cleaned_data.get(field) for field in cleaned_data if '_rule_' in field):
                self.add_error(None, "حداقل یک قانون باید انتخاب شود.")

        except Exception as e:
            logger.exception(f"خطا در اعتبارسنجی فرم: {str(e)}")
            self.add_error(None, f"خطای داخلی در پردازش فرم: {str(e)}")

        logger.debug(f"داده‌های پاک‌شده پس از اعتبارسنجی: {cleaned_data}")
        return cleaned_dat


# budgets/forms.py (or in your core/forms.py, ensure models are imported correctly)

from collections import defaultdict

# Assume these models are defined and imported correctly
# from core.models import Post, WorkflowStage, AccessRule, Organization


class PostAccessRuleForm(forms.Form):
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
        logger.debug("Starting form cleaning process.")

        # No specific cross-field validation needed here as the form structure
        # implies the stage is tied to the rule field name itself.
        # The JS ensures signer checkbox is disabled if rule is unchecked.

        # Example of a general form-level validation (as in your original code)
        if not any(value for name, value in cleaned_data.items() if name.startswith('rule_') and value):
            self.add_error(None, _("حداقل یک قانون دسترسی باید انتخاب شود."))
            logger.warning("No access rules selected.")

        logger.debug(f"Form cleaning complete. Cleaned data keys: {list(cleaned_data.keys())}")
        return cleaned_data

    def save(self):
        """
        Saves the access rules based on the cleaned_data.
        This method will delete existing rules for the managed posts and create new ones.
        """
        logger.info("Starting save operation for Access Rules.")

        # Collect post IDs that were part of this form submission
        managed_post_ids = {post_data['post'].id for post_data in self.post_fields_data}
        if not managed_post_ids:
            logger.info("No posts managed by this form submission. Exiting save.")
            return

        # 1. Update Post Levels
        posts_to_update = []
        for post_data in self.post_fields_data:
            post_obj = post_data['post']
            level_field_name = post_data['level_field'].name
            new_level = self.cleaned_data.get(level_field_name)

            if new_level is not None and new_level != post_obj.level:
                post_obj.level = new_level
                posts_to_update.append(post_obj)
                logger.debug(f"Post {post_obj.name} (ID: {post_obj.id}) level updated to {new_level}")

        if posts_to_update:
            Post.objects.bulk_update(posts_to_update, ['level'])
            logger.info(f"Updated levels for {len(posts_to_update)} posts.")

        # 2. Delete existing AccessRules for the managed posts
        # We delete all existing rules for these posts and then recreate them
        AccessRule.objects.filter(post__id__in=managed_post_ids).delete()
        logger.info(f"Deleted existing access rules for posts with IDs: {list(managed_post_ids)}")

        # 3. Create new AccessRules based on the form's cleaned data
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
                        # If the main rule is not active, the signer should also not be active
                        if not is_active:
                            is_payment_order_signer = False

                    if is_active:  # Only create rules that are active
                        rules_to_create.append(
                            AccessRule(
                                post=post_obj,
                                organization=post_obj.organization,
                                branch=post_obj.branch,  # Assuming branch is a CharField, otherwise handle None
                                stage=stage_obj,
                                action_type=action_type,
                                entity_type=entity_type,
                                is_active=True,  # Explicitly set to True for created rules
                                is_payment_order_signer=is_payment_order_signer
                            )
                        )
                        logger.debug(
                            f"Preparing to create rule: Post={post_obj.name}, Entity={entity_type}, Action={action_type}, Stage={stage_obj.name}, Signer={is_payment_order_signer}")

        if rules_to_create:
            AccessRule.objects.bulk_create(rules_to_create,
                                           ignore_conflicts=True)  # Use ignore_conflicts for safety if unique_together is set
            logger.info(f"Successfully created {len(rules_to_create)} new access rules.")
        else:
            logger.info("No active rules were selected, so no new rules were created.")

        logger.info("Access Rule save operation complete.")