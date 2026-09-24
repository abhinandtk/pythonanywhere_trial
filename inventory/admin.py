from django.contrib import admin
from .models import Category, Supplier, Product, StockMovement

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'company_name', 'phone', 'email', 'tax_id']
    search_fields = ['name', 'company_name', 'phone']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'unit', 'cost_price', 'selling_price', 'current_stock', 'min_stock_level', 'stock_status_badge', 'is_active']
    list_filter = ['category', 'is_active', 'unit']
    search_fields = ['name', 'sku', 'barcode']
    readonly_fields = ['created_at', 'updated_at']

    def stock_status_badge(self, obj):
        return obj.stock_status
    stock_status_badge.short_description = 'Status'

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'product', 'movement_type', 'quantity', 'previous_stock', 'resulting_stock', 'reference_number', 'created_by']
    list_filter = ['movement_type', 'created_at']
    search_fields = ['product__name', 'product__sku', 'reference_number', 'notes']
    readonly_fields = ['created_at']
