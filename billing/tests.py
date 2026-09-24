from django.test import TestCase, Client
from django.urls import reverse
from inventory.models import Category, Supplier, Product, StockMovement
from billing.models import Customer, Invoice, InvoiceItem, Payment, PurchaseOrder
from decimal import Decimal

class BillingInventoryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Hardware")
        self.supplier = Supplier.objects.create(name="Tech Supplies Inc", phone="1234567890")
        self.product = Product.objects.create(
            name="Mechanical Keyboard",
            sku="KB-001",
            category=self.category,
            supplier=self.supplier,
            cost_price=Decimal("50.00"),
            selling_price=Decimal("80.00"),
            tax_rate=Decimal("18.00"),
            current_stock=Decimal("20.00"),
            min_stock_level=Decimal("5.00")
        )
        self.customer = Customer.objects.create(name="John Doe", phone="9876543210")

    def test_dashboard_view(self):
        response = self.client.get(reverse('inventory:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_product_list_and_create(self):
        response = self.client.get(reverse('inventory:product_list'))
        self.assertEqual(response.status_code, 200)

        # Create product via view
        post_data = {
            'name': 'Wireless Mouse',
            'sku': 'MS-002',
            'category': self.category.id,
            'unit': 'PCS',
            'cost_price': '20.00',
            'selling_price': '35.00',
            'tax_rate': '18.00',
            'current_stock': '15.00',
            'min_stock_level': '3.00',
            'is_active': True,
        }
        res = self.client.post(reverse('inventory:product_create'), post_data)
        self.assertEqual(res.status_code, 302) # Redirects to detail
        self.assertTrue(Product.objects.filter(sku='MS-002').exists())

    def test_stock_adjustment(self):
        post_data = {
            'product': self.product.id,
            'movement_type': 'ADJ_ADD',
            'quantity': '10.00',
            'reference_number': 'TEST-ADJ',
            'notes': 'Test addition'
        }
        res = self.client.post(reverse('inventory:stock_adjust'), post_data)
        self.assertEqual(res.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('30.00'))

    def test_invoice_creation_and_stock_deduction(self):
        # 2 x 80 = 160 + 18% tax (28.80) = 188.80 total
        post_data = {
            'customer': self.customer.id,
            'invoice_number': 'INV-TEST-001',
            'invoice_date': '2026-09-24',
            'payment_method': 'CASH',
            'amount_paid': '188.80',
            'product_id[]': [self.product.id],
            'quantity[]': ['2.00'],
            'unit_price[]': ['80.00'],
            'tax_rate[]': ['18.00'],
            'item_discount[]': ['0.00'],
        }
        res = self.client.post(reverse('billing:invoice_create'), post_data)
        self.assertEqual(res.status_code, 302)

        invoice = Invoice.objects.get(invoice_number='INV-TEST-001')
        self.assertEqual(invoice.items.count(), 1)
        self.product.refresh_from_db()
        # Stock was 20, 2 sold -> 18
        self.assertEqual(self.product.current_stock, Decimal('18.00'))
        self.assertEqual(invoice.status, 'PAID')
        self.assertEqual(invoice.grand_total, Decimal('188.80'))
        self.assertEqual(invoice.balance_due, Decimal('0.00'))

    def test_invoice_cancellation_stock_reversal(self):
        # Create invoice
        invoice = Invoice.objects.create(
            invoice_number='INV-CANCEL-001',
            customer=self.customer,
            grand_total=Decimal('100.00')
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            quantity=Decimal('5.00'),
            unit_price=Decimal('80.00'),
            tax_rate=Decimal('0.00')
        )
        # Deduct stock manually for setup
        self.product.current_stock -= Decimal('5.00')
        self.product.save()
        self.assertEqual(self.product.current_stock, Decimal('15.00'))

        # Cancel invoice
        res = self.client.post(reverse('billing:invoice_cancel', kwargs={'pk': invoice.id}))
        self.assertEqual(res.status_code, 302)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'CANCELLED')
        self.product.refresh_from_db()
        # Stock restored from 15 to 20
        self.assertEqual(self.product.current_stock, Decimal('20.00'))
