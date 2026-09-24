from django import forms
from .models import Product, Category, Supplier, StockMovement
from decimal import Decimal

class FormStyleMixin:
    """Adds uniform styling and modern input classes to form fields"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-checkbox h-4 w-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500'})
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.update({'class': 'form-select block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm bg-white'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-textarea block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm', 'rows': 3})
            else:
                field.widget.attrs.update({'class': 'form-input block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'})

class ProductForm(FormStyleMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'barcode', 'category', 'supplier', 'unit',
            'cost_price', 'selling_price', 'tax_rate', 'current_stock',
            'min_stock_level', 'description', 'is_active'
        ]
        widgets = {
            'sku': forms.TextInput(attrs={'placeholder': 'e.g. PRD-1001'}),
            'barcode': forms.TextInput(attrs={'placeholder': 'e.g. 8901234567890'}),
            'cost_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'selling_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'tax_rate': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': 'e.g. 18.00'}),
            'current_stock': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'min_stock_level': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

class CategoryForm(FormStyleMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Electronics, Groceries, Apparel'}),
        }

class SupplierForm(FormStyleMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'company_name', 'email', 'phone', 'tax_id', 'address', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Contact Person Name'}),
            'company_name': forms.TextInput(attrs={'placeholder': 'e.g. Acme Corporation'}),
            'phone': forms.TextInput(attrs={'placeholder': '+1 234 567 890'}),
            'tax_id': forms.TextInput(attrs={'placeholder': 'Tax ID / GSTIN'}),
        }

class StockAdjustmentForm(FormStyleMixin, forms.Form):
    ADJUSTMENT_CHOICES = [
        ('ADJ_ADD', 'Add Stock (+) - New Batch / Found Item'),
        ('ADJ_SUB', 'Deduct Stock (-) - Internal Use / Correction'),
        ('DAMAGE', 'Damage / Expiry (-) - Write-off'),
        ('RETURN_CUSTOMER', 'Customer Return (+) - Restock'),
        ('RETURN_SUPPLIER', 'Supplier Return (-) - Sent Back'),
    ]

    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'})
    )
    movement_type = forms.ChoiceField(
        choices=ADJUSTMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'})
    )
    quantity = forms.DecimalField(
        min_value=Decimal('0.01'),
        decimal_places=2,
        widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Quantity to adjust', 'class': 'form-input block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'})
    )
    reference_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Reason / Reference / Batch Code', 'class': 'form-input block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Additional remarks...', 'class': 'form-textarea block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'})
    )
