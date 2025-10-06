from rest_framework import serializers, viewsets, permissions, routers, filters
from django.db.models import Q
from .models import PurchaseRequest, PurchaseRequestItem


class PurchaseRequestItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseRequestItem
        fields = ['id', 'request', 'description', 'sku', 'uom', 'quantity', 'unit_price', 'amount', 'external_item_id']
        read_only_fields = ['amount']


class PurchaseRequestSerializer(serializers.ModelSerializer):
    items = PurchaseRequestItemSerializer(many=True, required=False)

    class Meta:
        model = PurchaseRequest
        fields = [
            'id', 'number', 'organization', 'project', 'subproject', 'date', 'created_by', 'description', 'status',
            'source_system', 'external_id', 'external_payload', 'is_synced', 'synced_at', 'items', 'total_amount'
        ]
        read_only_fields = ['synced_at', 'total_amount', 'created_by']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        validated_data['created_by'] = self.context['request'].user if self.context.get('request') else None
        pr = PurchaseRequest.objects.create(**validated_data)
        for item in items_data:
            PurchaseRequestItem.objects.create(request=pr, **item)
        return pr

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for item in items_data:
                PurchaseRequestItem.objects.create(request=instance, **item)
        return instance


class IsInUserOrganizations(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        # expects a helper that returns org ids
        try:
            from core.PermissionBase import PermissionBaseView
            temp = PermissionBaseView()
            user_org_ids = temp.get_user_active_organizations(request.user)
            return obj.organization_id in (user_org_ids or [])
        except Exception:
            return False


class PurchaseRequestViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseRequestSerializer
    permission_classes = [IsInUserOrganizations]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['number', 'external_id', 'description']
    ordering = ['-date', '-id']

    def get_queryset(self):
        qs = PurchaseRequest.objects.select_related('organization', 'project', 'subproject', 'status', 'created_by')
        if self.request.user.is_superuser:
            return qs
        try:
            from core.PermissionBase import PermissionBaseView
            temp = PermissionBaseView()
            user_org_ids = temp.get_user_active_organizations(self.request.user) or []
            qs = qs.filter(organization_id__in=user_org_ids)
        except Exception:
            qs = qs.none()
        # optional filters
        number = self.request.query_params.get('number')
        external_id = self.request.query_params.get('external_id')
        if number:
            qs = qs.filter(number__icontains=number)
        if external_id:
            qs = qs.filter(external_id__icontains=external_id)
        return qs


class PurchaseRequestItemViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseRequestItemSerializer
    permission_classes = [IsInUserOrganizations]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description', 'sku', 'external_item_id']
    ordering = ['id']

    def get_queryset(self):
        qs = PurchaseRequestItem.objects.select_related('request', 'request__organization')
        if self.request.user.is_superuser:
            return qs
        try:
            from core.PermissionBase import PermissionBaseView
            temp = PermissionBaseView()
            user_org_ids = temp.get_user_active_organizations(self.request.user) or []
            qs = qs.filter(request__organization_id__in=user_org_ids)
        except Exception:
            qs = qs.none()
        pr_id = self.request.query_params.get('request')
        if pr_id:
            qs = qs.filter(request_id=pr_id)
        return qs


router = routers.DefaultRouter()
router.register(r'purchase-requests', PurchaseRequestViewSet, basename='api_purchase_request')
router.register(r'purchase-request-items', PurchaseRequestItemViewSet, basename='api_purchase_request_item')


