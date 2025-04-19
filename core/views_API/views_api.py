# budgets/views_api.py
from rest_framework.views import APIView
from rest_framework.response import Response
from core.models import Organization, Post, UserPost
from accounts.models import CustomUser
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


class OrganizationChartAPIView(APIView):
    def get(self, request):
        """
        Return hierarchical data for organization chart.
        """
        try:
            # دریافت فیلتر نقش (اختیاری)
            role_filter = request.query_params.get('role', None)

            # دریافت تمام سازمان‌های فعال
            organizations = Organization.objects.filter(is_active=True).prefetch_related(
                'post_set__userpost_set__user__roles'
            )

            chart_data = {
                'nodes': [],
                'edges': []
            }

            for org in organizations:
                # گره سازمان
                org_node = {
                    'id': f'org_{org.id}',
                    'label': org.name,
                    'group': 'organization',
                    'data': {
                        'type': 'organization',
                        'is_active': org.is_active,
                        'parent_id': org.parent_organization_id
                    }
                }
                chart_data['nodes'].append(org_node)

                # گره‌های پست
                for post in org.post_set.filter(is_active=True):
                    post_node = {
                        'id': f'post_{post.id}',
                        'label': post.name,
                        'group': 'post',
                        'data': {
                            'type': 'post',
                            'is_active': post.is_active,
                            'organization_id': org.id
                        }
                    }
                    chart_data['nodes'].append(post_node)
                    chart_data['edges'].append({
                        'from': f'org_{org.id}',
                        'to': f'post_{post.id}'
                    })

                    # گره‌های کاربر
                    for user_post in post.userpost_set.filter(is_active=True):
                        user = user_post.user
                        roles = [role.name for role in user.roles.all()]
                        if role_filter and role_filter not in roles:
                            continue

                        user_node = {
                            'id': f'user_{user.id}',
                            'label': user.username,
                            'group': 'user',
                            'data': {
                                'type': 'user',
                                # 'is_active': user.is_active,
                                'roles': roles,
                                'start_date': str(user_post.start_date),
                                'end_date': str(user_post.end_date) if user_post.end_date else None
                            }
                        }
                        chart_data['nodes'].append(user_node)
                        chart_data['edges'].append({
                            'from': f'post_{post.id}',
                            'to': f'user_{user.id}'
                        })

            # افزودن روابط والد-فرزند سازمان‌ها
            for org in organizations:
                if org.parent_organization_id:
                    chart_data['edges'].append({
                        'from': f'org_{org.parent_organization_id}',
                        'to': f'org_{org.id}'
                    })

            return Response(chart_data)
        except Exception as e:
            logger.error(f"Error in OrganizationChartAPIView: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=500)