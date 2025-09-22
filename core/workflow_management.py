"""
سیستم مدیریت یکپارچه قوانین گردش کار
این فایل شامل کلاس‌ها و توابعی برای مدیریت، اعتبارسنجی و سازماندهی قوانین گردش کار است.
بر اساس مدل‌های موجود: Status, Action, Transition, PostAction, Post
"""

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from typing import Dict, List, Tuple, Optional, Any
import json
import logging

logger = logging.getLogger(__name__)

# Import مدل‌های مورد نیاز
from .models import Status, Action, EntityType, Transition, Post, PostAction, Organization


class WorkflowRuleManager:
    """
    مدیریت‌کننده قوانین گردش کار
    """
    
    @staticmethod
    def create_rule_template_from_existing(organization, entity_type, template_name, description=""):
        """
        ایجاد تمپلیت از قوانین موجود در یک سازمان
        """
        try:
            # جمع‌آوری وضعیت‌ها
            statuses = []
            for status in Status.objects.filter(is_active=True):
                statuses.append({
                    'code': status.code,
                    'name': status.name,
                    'description': status.description,
                    'is_initial': status.is_initial,
                    'is_final': status.is_final,
                    'is_active': status.is_active,
                })
            
            # جمع‌آوری اقدامات
            actions = []
            for action in Action.objects.filter(is_active=True):
                actions.append({
                    'code': action.code,
                    'name': action.name,
                    'description': action.description,
                    'action_type': action.action_type,
                    'is_active': action.is_active,
                })
            
            # جمع‌آوری انتقال‌ها
            transitions = []
            for transition in Transition.objects.filter(organization=organization, is_active=True):
                transitions.append({
                    'from_status': transition.from_status.code,
                    'to_status': transition.to_status.code,
                    'action': transition.action.code,
                    'is_active': transition.is_active,
                })
            
            # جمع‌آوری تخصیص اقدامات به پست‌ها
            post_actions = []
            for post_action in PostAction.objects.filter(is_active=True):
                post_actions.append({
                    'post_id': post_action.post.id,
                    'action_code': post_action.action.code,
                    'is_active': post_action.is_active,
                })
            
            # ایجاد تمپلیت
            rules_data = {
                'statuses': statuses,
                'actions': actions,
                'transitions': transitions,
                'post_actions': post_actions,
            }
            
            template = WorkflowRuleTemplate.objects.create(
                name=template_name,
                description=description,
                organization=organization,
                entity_type=entity_type,
                rules_data=rules_data,
                is_active=True,
                is_public=False,
            )
            
            return template
            
        except Exception as e:
            logger.error(f"خطا در ایجاد تمپلیت: {e}")
            return None
    
    @staticmethod
    def validate_workflow_consistency(organization, entity_type):
        """
        اعتبارسنجی سازگاری قوانین گردش کار
        """
        issues = []
        
        try:
            # بررسی وجود وضعیت اولیه
            initial_statuses = Status.objects.filter(
                is_initial=True,
                is_active=True
            )
            if not initial_statuses.exists():
                issues.append("هیچ وضعیت اولیه‌ای تعریف نشده است")
            
            # بررسی وجود وضعیت نهایی
            final_statuses = Status.objects.filter(
                is_final_approve=True,
                is_active=True
            )
            if not final_statuses.exists():
                issues.append("هیچ وضعیت نهایی‌ای تعریف نشده است")
            
            # بررسی انتقال‌های غیرفعال
            inactive_transitions = Transition.objects.filter(
                organization=organization,
                is_active=False
            )
            if inactive_transitions.exists():
                issues.append(f"{inactive_transitions.count()} انتقال غیرفعال وجود دارد")
            
            # بررسی اقدامات بدون تخصیص
            actions_without_posts = Action.objects.filter(
                is_active=True
            ).exclude(
                postaction__isnull=False
            )
            if actions_without_posts.exists():
                issues.append(f"{actions_without_posts.count()} اقدام بدون تخصیص به پست وجود دارد")
            
        except Exception as e:
            logger.error(f"خطا در اعتبارسنجی: {e}")
            issues.append(f"خطا در اعتبارسنجی: {str(e)}")
        
        return issues
    
    @staticmethod
    def get_workflow_summary(organization, entity_type):
        """
        دریافت خلاصه قوانین گردش کار
        """
        try:
            summary = {
                'organization': organization.name,
                'entity_type': entity_type,
                'statuses_count': Status.objects.filter(is_active=True).count(),
                'actions_count': Action.objects.filter(is_active=True).count(),
                'transitions_count': Transition.objects.filter(organization=organization, is_active=True).count(),
                'post_actions_count': PostAction.objects.filter(is_active=True).count(),
                'initial_statuses': list(Status.objects.filter(
                    is_initial=True,
                    is_active=True
                ).values_list('name', flat=True)),
                'final_statuses': list(Status.objects.filter(
                    is_final_approve=True,
                    is_active=True
                ).values_list('name', flat=True)),
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"خطا در دریافت خلاصه: {e}")
            return None
    
    @staticmethod
    def export_workflow_rules(organization, entity_type):
        """
        صادرات قوانین گردش کار
        """
        try:
            # جمع‌آوری تمام قوانین
            statuses = list(Status.objects.filter(is_active=True).values())
            actions = list(Action.objects.filter(is_active=True).values())
            transitions = list(Transition.objects.filter(organization=organization, is_active=True).values())
            post_actions = list(PostAction.objects.filter(is_active=True).values())
            
            export_data = {
                'organization': organization.name,
                'entity_type': entity_type,
                'export_date': str(models.DateTimeField().auto_now),
                'statuses': statuses,
                'actions': actions,
                'transitions': transitions,
                'post_actions': post_actions,
            }
            
            return export_data
            
        except Exception as e:
            logger.error(f"خطا در صادرات: {e}")
            return None


