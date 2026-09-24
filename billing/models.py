from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from inventory.models import Product, Supplier, StockMovement

class Customer(models.Model):
    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30)
    address = models.TextField(blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="GST / Tax ID")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        if self.company_name:
            return f"{self.name} ({self.company_name})"
        return self.name

    @property
    def total_invoices_count(self):
        return self.invoices.count()

    @property
    def total_billed(self):
        return sum(inv.grand_total for inv in self.invoices.exclude(status='CANCELLED'))

    @property
    def total_due(self):
        return sum(inv.balance_due for inv in self.invoices.filter(status__in=['ISSUED', 'PARTIALLY_PAID', 'OVERDUE']))

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ISSUED', 'Issued / Unpaid'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('UPI', 'UPI / QR Code'),
        ('CARD', 'Credit / Debit Card'),
        ('BANK_TRANSFER', 'Bank Transfer (NEFT/RTGS/IMPS)'),
        ('CHEQUE', 'Cheque'),
        ('CREDIT', 'On Credit (Pay Later)'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ISSUED')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    notes = models.TextField(blank=True, null=True, help_text="Customer notes, bank details, or remarks")
    terms = models.TextField(blank=True, null=True, default="1. Goods once sold will not be taken back.\n2. Payment is due within standard terms.\n3. Thank you for your business!")
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date', '-created_at']

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name}"

    def recalculate_totals(self, save=True):
        items = self.items.all()
        subtotal = Decimal('0.00')
        tax_total = Decimal('0.00')
        
        for item in items:
            subtotal += item.line_subtotal
            tax_total += item.tax_amount
            
        self.subtotal = subtotal
        self.tax_amount = tax_total
        self.grand_total = max(Decimal('0.00'), (self.subtotal + self.tax_amount) - self.discount_amount)
        
        # Calculate amount paid from payments
        total_payments = sum(p.amount for p in self.payments.all())
        self.amount_paid = total_payments
        self.balance_due = max(Decimal('0.00'), self.grand_total - self.amount_paid)
        
        if self.status != 'CANCELLED' and self.status != 'DRAFT':
            if self.balance_due == Decimal('0.00') and self.grand_total > Decimal('0.00'):
                self.status = 'PAID'
            elif self.amount_paid > Decimal('0.00') and self.balance_due > Decimal('0.00'):
                self.status = 'PARTIALLY_PAID'
            elif self.amount_paid == Decimal('0.00'):
                self.status = 'ISSUED'
                
        if save:
            self.save()

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='invoice_items')
    description = models.CharField(max_length=255, blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Tax %")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    @property
    def line_subtotal(self):
        return (self.quantity * self.unit_price) - self.discount_amount

    def save(self, *args, **kwargs):
        line_base = (self.quantity * self.unit_price) - self.discount_amount
        if self.tax_rate > 0:
            self.tax_amount = (line_base * self.tax_rate) / Decimal('100.00')
        else:
            self.tax_amount = Decimal('0.00')
        self.total_price = line_base + self.tax_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} ({self.quantity} x {self.unit_price})"

class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=Invoice.PAYMENT_METHOD_CHOICES, default='CASH')
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text="Transaction ID / Cheque #")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"Payment #{self.id} - {self.invoice.invoice_number} ({self.amount})"

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending / Draft'),
        ('RECEIVED', 'Received / In Stock'),
        ('CANCELLED', 'Cancelled'),
    ]

    po_number = models.CharField(max_length=50, unique=True, verbose_name="PO Number")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    order_date = models.DateField(default=timezone.now)
    received_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-order_date', '-created_at']

    def __str__(self):
        return f"{self.po_number} - {self.supplier.name}"

    def recalculate_total(self, save=True):
        self.total_amount = sum(item.total_cost for item in self.items.all())
        if save:
            self.save()

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} ({self.quantity} @ {self.unit_cost})"
