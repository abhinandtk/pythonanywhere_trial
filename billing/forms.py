from django import forms
from .models import Customer, Invoice, InvoiceItem, Payment, PurchaseOrder, PurchaseOrderItem
from inventory.forms import FormStyleMixin
from inventory.models import Product
from decimal import Decimal

class CustomerForm(FormStyleMixin, forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'company_name', 'email', 'phone', 'tax_id', 'address', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Customer Full Name'}),
            'company_name': forms.TextInput(attrs={'placeholder': 'Company / Business Name (Optional)'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone / Mobile Number'}),
            'tax_id': forms.TextInput(attrs={'placeholder': 'GSTIN / VAT / Tax ID'}),
            'address': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Billing & Shipping Address'}),
        }

class PaymentForm(FormStyleMixin, forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_date', 'payment_method', 'reference_number', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'reference_number': forms.TextInput(attrs={'placeholder': 'UPI Ref / Cheque No / Transaction ID'}),
            'notes': forms.TextInput(attrs={'placeholder': 'Payment notes...'}),
        }

class PurchaseOrderForm(FormStyleMixin, forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['po_number', 'supplier', 'order_date', 'notes']
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'po_number': forms.TextInput(attrs={'placeholder': 'PO-2026-0001'}),
        }
