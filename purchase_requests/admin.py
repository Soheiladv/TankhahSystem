from django.contrib import admin
from .models import PurchaseRequest, PurchaseRequestItem


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = (
        'number', 'organization', 'project', 'date', 'status', 'created_by', 'total_amount',
        'source_system', 'external_id', 'is_synced', 'synced_at',
    )
    list_filter = ('organization', 'project', 'status', 'source_system', 'is_synced', 'date')
    search_fields = ('number', 'external_id', 'description')
    readonly_fields = ('synced_at',)
    autocomplete_fields = ('organization', 'project', 'subproject', 'status', 'created_by')


@admin.register(PurchaseRequestItem)
class PurchaseRequestItemAdmin(admin.ModelAdmin):
    list_display = ('request', 'description', 'sku', 'uom', 'quantity', 'unit_price', 'amount')
    list_filter = ('uom',)
    search_fields = ('description', 'sku', 'external_item_id')
    autocomplete_fields = ('request',)


