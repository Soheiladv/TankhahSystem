import json
import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Prefetch

from core.PermissionBase import PermissionBaseView
from core.models import Organization, Post, UserPost
from accounts.models import CustomUser

logger = logging.getLogger(__name__)

class OrganizationChartAPIView(PermissionBaseView, APIView):
    permission_codenames = 'core.OrganizationChartAPIView_view'
    check_organization = True
    def get(self, request):
        """
        Return hierarchical data for organization chart.
        Supports filtering by role, organization, and status.
        """
        try:
            # دریافت پارامترهای فیلتر
            role_filter = request.query_params.get('role', None)
            org_id = request.query_params.get('org_id', None)
            branch_id = request.query_params.get('branch_id', None)
            post_id = request.query_params.get('post_id', None)
            status = request.query_params.get('status', None)

            # کوئری پایه برای سازمان‌ها
            queryset = Organization.objects.filter(is_active=True)
            if org_id:
                queryset = queryset.filter(id=org_id)

            # فیلتر پست‌ها بر اساس شاخه و پست خاص
            post_queryset = Post.objects.filter(is_active=True)
            if branch_id:
                post_queryset = post_queryset.filter(branch_id=branch_id)
            if post_id:
                post_queryset = post_queryset.filter(id=post_id)

            organizations = queryset.prefetch_related(
                Prefetch('post_set', queryset=post_queryset.prefetch_related(
                    Prefetch('userpost_set', queryset=UserPost.objects.filter(is_active=True).select_related('user'))
                ).select_related('parent', 'branch')),
                'parent_organization'
            ).select_related('org_type')

            chart_data = {'nodes': [], 'edges': []}
            added_users = set()  # جلوگیری از افزودن کاربران تکراری

            for org in organizations:
                # گره سازمان
                org_node = {
                    'id': f'org_{org.id}',
                    'label': f"{org.name}\n({org.org_type.fname if org.org_type else 'نامشخص'})",
                    'group': 'organization',
                    'title': f"<b>{_('سازمان')}:</b> {org.name}<br><b>{_('نوع')}:</b> {org.org_type.fname if org.org_type else '-'}<br><b>{_('کد')}:</b> {org.code or '-'}",
                    'shape': 'box',
                    'color': '#97C2FC',
                    'font': {'color': '#333'}
                }
                chart_data['nodes'].append(org_node)

                # یال به سازمان والد
                if org.parent_organization:
                    chart_data['edges'].append({
                        'from': f'org_{org.parent_organization.id}',
                        'to': f'org_{org.id}',
                        'arrows': 'to',
                        'color': {'color': '#cccccc', 'highlight': '#848484'},
                        'dashes': True
                    })

                for post in org.post_set.all():
                    # گره پست
                    branch_name = post.branch.name if post.branch else _('بدون شاخه')
                    post_node = {
                        'id': f'post_{post.id}',
                        'label': post.name,
                        'group': 'post',
                        'title': f"<b>{_('پست')}:</b> {post.name}<br><b>{_('سازمان')}:</b> {org.name}<br><b>{_('شاخه')}:</b> {branch_name}<br><b>{_('سطح')}:</b> {post.level}",
                        'shape': 'ellipse',
                        'color': '#FBDBA8',
                        'font': {'size': 11}
                    }
                    chart_data['nodes'].append(post_node)
                    chart_data['edges'].append({
                        'from': f'org_{org.id}',
                        'to': f'post_{post.id}',
                        'arrows': 'to',
                        'color': {'color': '#cccccc', 'highlight': '#848484'}
                    })

                    # یال به پست والد
                    if post.parent:
                        chart_data['edges'].append({
                            'from': f'post_{post.parent.id}',
                            'to': f'post_{post.id}',
                            'arrows': 'to',
                            'color': {'color': '#FFA500', 'highlight': '#FF8C00'},
                            'dashes': [5, 5]
                        })

                    for user_post in post.userpost_set.all():
                        user = user_post.user
                        roles = [role.name for role in user.roles.all() if role.name]
                        if role_filter and role_filter not in roles:
                            continue
                        if status and user_post.status != status:
                            continue

                        if user.id not in added_users:
                            user_node = {
                                'id': f'user_{user.id}',
                                'label': user.get_full_name() or user.username,
                                'group': 'user',
                                'title': f"<b>{_('کاربر')}:</b> {user.get_full_name() or user.username}<br><b>{_('نام کاربری')}:</b> {user.username}<br><b>{_('ایمیل')}:</b> {user.email or '-'}",
                                'shape': 'icon',
                                'icon': {
                                    'face': 'FontAwesome',
                                    'code': '\uf007',
                                    'size': 25,
                                    'color': '#5bc0de'
                                }
                            }
                            chart_data['nodes'].append(user_node)
                            added_users.add(user.id)

                        chart_data['edges'].append({
                            'from': f'post_{post.id}',
                            'to': f'user_{user.id}',
                            'arrows': 'to',
                            'color': {'color': '#848484', 'highlight': '#505050'}
                        })

            return Response(chart_data)
        except Exception as e:
            logger.error(f"Error in OrganizationChartAPIView: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=500)

class OrganizationChartView(PermissionBaseView, LoginRequiredMixin, TemplateView):
    template_name = 'core/chart_API/organization_chart.html'
    permission_codenames = 'core.OrganizationChartView_view'
    check_organization = True
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("نمودار سازمانی")

        try:
            # دریافت لیست نقش‌ها، سازمان‌ها، شاخه‌ها و پست‌ها برای فیلترها
            from core.models import Branch
            from django.db.models import Q
            
            # نقش‌ها - درست کردن کوئری
            roles = list(CustomUser.objects.filter(roles__isnull=False).values_list('roles__name', flat=True).distinct())
            roles = [role for role in roles if role]  # حذف مقادیر خالی
            
            # سازمان‌ها
            organizations = Organization.objects.filter(is_active=True).values('id', 'name', 'code')
            
            # شاخه‌ها
            branches = Branch.objects.filter(is_active=True).values('id', 'name', 'code')
            
            # پست‌ها (برای فیلتر پیشرفته)
            posts = Post.objects.filter(is_active=True).select_related('organization', 'branch').values(
                'id', 'name', 'organization__name', 'branch__name', 'level'
            )
            
            context['roles'] = roles
            context['organizations'] = organizations
            context['branches'] = branches
            context['posts'] = posts

            # در صورت عدم نیاز به داده‌های اولیه در تمپلیت، می‌توان این بخش را حذف کرد
            # زیرا داده‌ها از API دریافت می‌شوند
            context['nodes_json'] = json.dumps([])
            context['edges_json'] = json.dumps([])
            context['posts_json'] = json.dumps(list(posts))

        except Exception as e:
            logger.error(f"Error in OrganizationChartView: {str(e)}", exc_info=True)
            context['error'] = _("خطا در بارگذاری اطلاعات نمودار سازمانی.")

        return context