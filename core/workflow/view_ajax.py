
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views import View
from rest_framework.views import APIView

from core.PermissionBase import PermissionBaseView
from core.models import Post, Organization, Transition, Status
# @login_required
# def get_posts_for_organization(request):
#     """
#     یک ویوی API که لیستی از پست‌ها را برای یک سازمان مشخص در قالب JSON برمی‌گرداند.
#     """
#     organization_id = request.GET.get('organization_id')
#     if not organization_id:
#         return JsonResponse({'error': 'Organization ID is required'}, status=400)
#
#     posts = Post.objects.filter(organization_id=organization_id, is_active=True).values('id', 'name', 'level')
#
#     return JsonResponse(list(posts), safe=False)
@login_required
def get_posts_for_organization(request):
    """
    یک ویوی API که لیستی از پست‌ها را برای یک سازمان مشخص در قالب JSON برمی‌گرداند.
    این نسخه شامل اعتبارسنجی ورودی است.
    """
    organization_id = request.GET.get('organization_id')

    # اعتبارسنجی ورودی
    if not organization_id or not organization_id.isdigit():
        return JsonResponse({'error': 'A valid Organization ID is required.'}, status=400)

    try:
        # اطمینان از وجود سازمان (برای امنیت بیشتر)
        Organization.objects.get(pk=organization_id)

        # واکشی و بازگرداندن پست‌ها
        posts = Post.objects.filter(
            organization_id=organization_id,
            is_active=True
        ).values('id', 'name', 'level').order_by('level', 'name')

        return JsonResponse(list(posts), safe=False)

    except Organization.DoesNotExist:
        return JsonResponse({'error': 'Organization not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
class GetTransitionDetailsView(PermissionBaseView, View):
    def get(self, request, *args, **kwargs):
        transition_id = request.GET.get('transition_id')
        try:
            transition = Transition.objects.get(pk=transition_id)
            statuses = Status.objects.filter(
                entity_type=transition.entity_type,
                is_active=True
            ).values_list('pk', 'name')

            return JsonResponse({
                'entity_type': transition.entity_type,
                'entity_type_name': transition.get_entity_type_display(),
                'statuses': dict(statuses)
            })
        except Transition.DoesNotExist:
            return JsonResponse({'error': 'Transition not found'}, status=404)
class GetOrganizationPostsView(PermissionBaseView, View):
    def get(self, request, *args, **kwargs):
        organization_id = request.GET.get('organization_id')
        try:
            posts = Post.objects.filter(
                organization_id=organization_id,
                is_active=True
            ).order_by('level', 'name').values_list('pk', 'name')

            return JsonResponse({
                'posts': dict(posts)
            })
        except Organization.DoesNotExist:
            return JsonResponse({'error': 'Organization not found'}, status=404)


class TransitionDetailAPI(APIView):
    def get(self, request, pk):
        try:
            transition = Transition.objects.get(pk=pk)
            return JsonResponse({
                'organization_id': transition.organization.id,
                'organization_name': transition.organization.name
            })
        except Transition.DoesNotExist:
            return JsonResponse({'error': 'Transition not found'}, status=404)


class PostListAPI(APIView):
    def get(self, request):
        organization_id = request.GET.get('organization_id')
        if not organization_id:
            return JsonResponse({'error': 'organization_id parameter is required'}, status=400)

        posts = Post.objects.filter(
            organization_id=organization_id,
            is_active=True
        ).values('id', 'name')

        return JsonResponse(list(posts), safe=False)
