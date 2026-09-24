from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=150)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30)
    address = models.TextField(blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tax/GST Number")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        if self.company_name:
            return f"{self.name} ({self.company_name})"
        return self.name

class Product(models.Model):
    UNIT_CHOICES = [
        ('PCS', 'Pieces (pcs)'),
        ('KG', 'Kilograms (kg)'),
        ('GM', 'Grams (gm)'),
        ('LTR', 'Liters (ltr)'),
        ('MTR', 'Meters (mtr)'),
        ('BOX', 'Boxes (box)'),
        ('PKT', 'Packets (pkt)'),
        ('SET', 'Sets (set)'),
        ('UNIT', 'Units (unit)'),
    ]

    name = models.CharField(max_length=250)
    sku = models.CharField(max_length=60, unique=True, verbose_name="SKU / Item Code")
    barcode = models.CharField(max_length=80, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='PCS')
    
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Purchase / Cost Price")
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Selling Price")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), verbose_name="Tax Rate (%)")
    
    current_stock = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Current Stock")
    min_stock_level = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('5.00'), verbose_name="Min Reorder Level")
    
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def is_low_stock(self):
        return 0 < self.current_stock <= self.min_stock_level

    @property
    def is_out_of_stock(self):
        return self.current_stock <= 0

    @property
    def stock_status(self):
        if self.is_out_of_stock:
            return 'out_of_stock'
        elif self.is_low_stock:
            return 'low_stock'
        return 'in_stock'

    @property
    def total_cost_value(self):
        return self.current_stock * self.cost_price

    @property
    def total_retail_value(self):
        return self.current_stock * self.selling_price

class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('IN_PURCHASE', 'Stock In (Purchase)'),
        ('OUT_SALE', 'Stock Out (Invoice / Sale)'),
        ('ADJ_ADD', 'Manual Adjustment (+)'),
        ('ADJ_SUB', 'Manual Adjustment (-)'),
        ('RETURN_CUSTOMER', 'Customer Return (+)'),
        ('RETURN_SUPPLIER', 'Supplier Return (-)'),
        ('DAMAGE', 'Damaged / Expired (-)'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    previous_stock = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    resulting_stock = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), blank=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Invoice #, PO #, Reason")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} - {self.get_movement_type_display()} ({self.quantity})"
