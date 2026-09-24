from django.contrib import admin
from .models import Customer, Invoice, InvoiceItem, Payment, PurchaseOrder, PurchaseOrderItem

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    readonly_fields = ['total_price', 'tax_amount']

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['created_at']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'company_name', 'phone', 'email', 'tax_id', 'created_at']
    search_fields = ['name', 'company_name', 'phone', 'email']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'invoice_date', 'status', 'grand_total', 'amount_paid', 'balance_due']
    list_filter = ['status', 'invoice_date', 'payment_method']
    search_fields = ['invoice_number', 'customer__name', 'customer__phone']
    inlines = [InvoiceItemInline, PaymentInline]
    readonly_fields = ['created_at', 'updated_at']

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    readonly_fields = ['total_cost']

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'supplier', 'order_date', 'status', 'total_amount']
    list_filter = ['status', 'order_date']
    search_fields = ['po_number', 'supplier__name']
    inlines = [PurchaseOrderItemInline]
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'payment_date', 'payment_method', 'reference_number']
    list_filter = ['payment_date', 'payment_method']
    search_fields = ['invoice__invoice_number', 'reference_number']
