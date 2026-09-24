from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import datetime

from inventory.models import Category, Supplier, Product, StockMovement
from billing.models import Customer, Invoice, InvoiceItem, Payment, PurchaseOrder, PurchaseOrderItem

class Command(BaseCommand):
    help = 'Populates the database with realistic sample billing & inventory data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding sample database records..."))

        # 1. Categories
        cat_electronics, _ = Category.objects.get_or_create(name="Electronics", defaults={'description': 'Consumer electronics and devices'})
        cat_accessories, _ = Category.objects.get_or_create(name="Computer Accessories", defaults={'description': 'Keyboards, mice, webcams, headsets'})
        cat_networking, _ = Category.objects.get_or_create(name="Networking & Cables", defaults={'description': 'Routers, switches, ethernet & HDMI cables'})
        cat_office, _ = Category.objects.get_or_create(name="Office & Stationery", defaults={'description': 'Printing paper, notebooks, desk accessories'})
        cat_storage, _ = Category.objects.get_or_create(name="Storage & Drives", defaults={'description': 'SSDs, USB Flash drives, external hard disks'})

        # 2. Suppliers
        sup_apex, _ = Supplier.objects.get_or_create(
            name="Apex Tech Distribution",
            defaults={
                'company_name': 'Apex Technologies International',
                'email': 'orders@apextech.com',
                'phone': '+1 (555) 234-8901',
                'tax_id': 'GSTIN-SUP-0012',
                'address': '742 Evergreen Terrace, Industrial Zone, CA',
                'notes': 'Preferred distributor for computer peripherals'
            }
        )
        sup_nexus, _ = Supplier.objects.get_or_create(
            name="Nexus Hardware Solutions",
            defaults={
                'company_name': 'Nexus Global Logistics',
                'email': 'supply@nexushardware.io',
                'phone': '+1 (555) 876-5432',
                'tax_id': 'GSTIN-SUP-9941',
                'address': '450 Silicon Avenue, Suite 200, TX',
                'notes': 'Primary supplier for storage & networking components'
            }
        )

        # 3. Products
        products_data = [
            {
                'name': 'Logitech MX Master 3S Wireless Mouse',
                'sku': 'LOGI-MX3S',
                'barcode': '097855173546',
                'category': cat_accessories,
                'supplier': sup_apex,
                'unit': 'PCS',
                'cost_price': Decimal('68.00'),
                'selling_price': Decimal('99.99'),
                'tax_rate': Decimal('18.00'),
                'current_stock': Decimal('24.00'),
                'min_stock_level': Decimal('5.00'),
                'description': 'Ergonomic performance wireless mouse with 8K DPI sensor',
            },
            {
                'name': 'Keychron K2 Mechanical Keyboard (RGB)',
                'sku': 'KEY-K2-RGB',
                'barcode': '097855173547',
                'category': cat_accessories,
                'supplier': sup_apex,
                'unit': 'PCS',
                'cost_price': Decimal('55.00'),
                'selling_price': Decimal('89.00'),
                'tax_rate': Decimal('18.00'),
                'current_stock': Decimal('12.00'),
                'min_stock_level': Decimal('5.00'),
                'description': 'Compact 75% layout wireless mechanical keyboard with Gateron switches',
            },
            {
                'name': 'Samsung 980 PRO NVMe SSD 1TB',
                'sku': 'SAM-980P-1TB',
                'barcode': '887276435012',
                'category': cat_storage,
                'supplier': sup_nexus,
                'unit': 'PCS',
                'cost_price': Decimal('75.00'),
                'selling_price': Decimal('119.50'),
                'tax_rate': Decimal('18.00'),
                'current_stock': Decimal('3.00'), # Low Stock!
                'min_stock_level': Decimal('6.00'),
                'description': 'PCIe Gen 4.0 x4 M.2 2280 Internal Solid State Drive',
            },
            {
                'name': 'SanDisk Ultra 128GB USB 3.0 Flash Drive',
                'sku': 'SNDK-128G-U3',
                'barcode': '619659134789',
                'category': cat_storage,
                'supplier': sup_nexus,
                'unit': 'PCS',
                'cost_price': Decimal('8.50'),
                'selling_price': Decimal('15.99'),
                'tax_rate': Decimal('12.00'),
                'current_stock': Decimal('45.00'),
                'min_stock_level': Decimal('10.00'),
                'description': 'High-speed USB 3.0 flash drive with transfer speeds up to 130MB/s',
            },
            {
                'name': 'TP-Link AX3000 WiFi 6 Gigabit Router',
                'sku': 'TPL-AX3000',
                'barcode': '845973082910',
                'category': cat_networking,
                'supplier': sup_nexus,
                'unit': 'PCS',
                'cost_price': Decimal('62.00'),
                'selling_price': Decimal('94.99'),
                'tax_rate': Decimal('18.00'),
                'current_stock': Decimal('0.00'), # Out of stock!
                'min_stock_level': Decimal('4.00'),
                'description': 'Dual-Band Wi-Fi 6 router with OFDMA and MU-MIMO technology',
            },
            {
                'name': 'Cat6 Shielded Ethernet Patch Cable 10m',
                'sku': 'CAB-CAT6-10M',
                'barcode': '724120019234',
                'category': cat_networking,
                'supplier': sup_nexus,
                'unit': 'PCS',
                'cost_price': Decimal('3.20'),
                'selling_price': Decimal('7.50'),
                'tax_rate': Decimal('18.00'),
                'current_stock': Decimal('60.00'),
                'min_stock_level': Decimal('15.00'),
                'description': 'High speed 1Gbps RJ45 Ethernet patch cable for LAN networks',
            },
            {
                'name': 'Dell UltraSharp 27" 4K UHD Monitor',
                'sku': 'DELL-U2723QE',
                'barcode': '884116416180',
                'category': cat_electronics,
                'supplier': sup_apex,
                'unit': 'PCS',
                'cost_price': Decimal('420.00'),
                'selling_price': Decimal('579.00'),
                'tax_rate': Decimal('18.00'),
                'current_stock': Decimal('2.00'), # Low Stock!
                'min_stock_level': Decimal('3.00'),
                'description': '27-inch 4K IPS Black monitor with USB-C Hub and 98% DCI-P3 color gamut',
            },
            {
                'name': 'Anker 65W GaN Fast Wall Charger',
                'sku': 'ANK-65W-GAN',
                'barcode': '194644023912',
                'category': cat_electronics,
                'supplier': sup_apex,
                'unit': 'PCS',
                'cost_price': Decimal('22.00'),
                'selling_price': Decimal('38.99'),
                'tax_rate': Decimal('18.00'),
                'current_stock': Decimal('18.00'),
                'min_stock_level': Decimal('5.00'),
                'description': '3-Port compact USB-C fast charger for laptops, phones and tablets',
            },
            {
                'name': 'A4 Multipurpose Copy Paper (500 Sheets)',
                'sku': 'PPR-A4-500S',
                'barcode': '890103045612',
                'category': cat_office,
                'supplier': sup_apex,
                'unit': 'PKT',
                'cost_price': Decimal('3.80'),
                'selling_price': Decimal('6.50'),
                'tax_rate': Decimal('5.00'),
                'current_stock': Decimal('110.00'),
                'min_stock_level': Decimal('20.00'),
                'description': '75 GSM bright white paper suitable for laser and inkjet printers',
            },
        ]

        created_products = []
        for pdata in products_data:
            prod, created = Product.objects.get_or_create(
                sku=pdata['sku'],
                defaults=pdata
            )
            created_products.append(prod)
            if created and prod.current_stock > 0:
                StockMovement.objects.create(
                    product=prod,
                    movement_type='IN_PURCHASE',
                    quantity=prod.current_stock,
                    previous_stock=Decimal('0.00'),
                    resulting_stock=prod.current_stock,
                    unit_price=prod.cost_price,
                    reference_number='INITIAL-SETUP',
                    notes='Initial seed stock configuration'
                )

        # 4. Customers
        customers_data = [
            {
                'name': 'David Miller',
                'company_name': 'Quantum Design Studios',
                'email': 'david@quantumdesign.com',
                'phone': '+1 (555) 302-9182',
                'tax_id': 'GSTIN-CUST-8812',
                'address': '221 Baker Street, Suite 5B, New York, NY 10001',
                'notes': 'Corporate client with Net-30 payment terms'
            },
            {
                'name': 'Sarah Jenkins',
                'company_name': 'Summit Architecture Group',
                'email': 'sarah.j@summitarch.org',
                'phone': '+1 (555) 714-2299',
                'tax_id': 'GSTIN-CUST-4421',
                'address': '840 Metro Center Blvd, Foster City, CA 94404',
                'notes': 'Regular buyer for workstation accessories'
            },
            {
                'name': 'Alex Carter',
                'company_name': 'CodeCraft Solutions',
                'email': 'alex@codecraft.io',
                'phone': '+1 (555) 619-3388',
                'tax_id': '',
                'address': '101 Pine Street, Seattle, WA 98101',
                'notes': 'Freelance software engineer'
            },
            {
                'name': 'Walk-in Retail Customer',
                'company_name': '',
                'email': '',
                'phone': '+1 (555) 000-0000',
                'tax_id': '',
                'address': 'In-store Point of Sale',
                'notes': 'Cash walk-in purchases'
            }
        ]

        created_customers = []
        for cdata in customers_data:
            cust, _ = Customer.objects.get_or_create(
                name=cdata['name'],
                defaults=cdata
            )
            created_customers.append(cust)

        # 5. Invoices & Payments
        today = timezone.now().date()

        # Invoice 1: Paid in Full
        if not Invoice.objects.filter(invoice_number='INV-202609-0001').exists():
            inv1 = Invoice.objects.create(
                invoice_number='INV-202609-0001',
                customer=created_customers[0],
                invoice_date=today - datetime.timedelta(days=12),
                due_date=today - datetime.timedelta(days=2),
                payment_method='UPI',
                status='PAID',
                notes='Invoice for office hardware upgrade',
                terms='Payment received in full. Thank you for doing business!'
            )
            item1 = InvoiceItem.objects.create(
                invoice=inv1,
                product=created_products[0], # Logitech Mouse
                quantity=Decimal('2.00'),
                unit_price=Decimal('99.99'),
                tax_rate=Decimal('18.00'),
            )
            item2 = InvoiceItem.objects.create(
                invoice=inv1,
                product=created_products[1], # Keychron
                quantity=Decimal('2.00'),
                unit_price=Decimal('89.00'),
                tax_rate=Decimal('18.00'),
            )
            inv1.recalculate_totals(save=True)
            Payment.objects.create(
                invoice=inv1,
                amount=inv1.grand_total,
                payment_date=today - datetime.timedelta(days=12),
                payment_method='UPI',
                reference_number='UPI/TXN/99823412',
                notes='Instant QR payment'
            )
            inv1.recalculate_totals(save=True)

        # Invoice 2: Partially Paid
        if not Invoice.objects.filter(invoice_number='INV-202609-0002').exists():
            inv2 = Invoice.objects.create(
                invoice_number='INV-202609-0002',
                customer=created_customers[1],
                invoice_date=today - datetime.timedelta(days=4),
                due_date=today + datetime.timedelta(days=10),
                payment_method='BANK_TRANSFER',
                status='PARTIALLY_PAID',
                notes='Dell UltraSharp monitor purchase for designer desk'
            )
            InvoiceItem.objects.create(
                invoice=inv2,
                product=created_products[6], # Dell monitor
                quantity=Decimal('1.00'),
                unit_price=Decimal('579.00'),
                tax_rate=Decimal('18.00'),
            )
            InvoiceItem.objects.create(
                invoice=inv2,
                product=created_products[7], # Anker charger
                quantity=Decimal('1.00'),
                unit_price=Decimal('38.99'),
                tax_rate=Decimal('18.00'),
            )
            inv2.recalculate_totals(save=True)
            Payment.objects.create(
                invoice=inv2,
                amount=Decimal('400.00'),
                payment_date=today - datetime.timedelta(days=4),
                payment_method='BANK_TRANSFER',
                reference_number='NEFT/98120349',
                notes='Advance deposit paid'
            )
            inv2.recalculate_totals(save=True)

        # Invoice 3: Issued / Unpaid
        if not Invoice.objects.filter(invoice_number='INV-202609-0003').exists():
            inv3 = Invoice.objects.create(
                invoice_number='INV-202609-0003',
                customer=created_customers[2],
                invoice_date=today - datetime.timedelta(days=1),
                due_date=today + datetime.timedelta(days=7),
                payment_method='CREDIT',
                status='ISSUED',
                discount_amount=Decimal('10.00'),
                notes='Fast delivery requested'
            )
            InvoiceItem.objects.create(
                invoice=inv3,
                product=created_products[3], # SanDisk 128G
                quantity=Decimal('3.00'),
                unit_price=Decimal('15.99'),
                tax_rate=Decimal('12.00'),
            )
            InvoiceItem.objects.create(
                invoice=inv3,
                product=created_products[5], # Cat6 cable
                quantity=Decimal('4.00'),
                unit_price=Decimal('7.50'),
                tax_rate=Decimal('18.00'),
            )
            inv3.recalculate_totals(save=True)

        self.stdout.write(self.style.SUCCESS("Successfully seeded database with products, categories, suppliers, customers, and invoices!"))
