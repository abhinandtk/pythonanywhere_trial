from inventory.models import Product
from billing.models import Invoice

def company_info(request):
    """Provides global site parameters and alerts to all templates"""
    low_stock_count = Product.objects.filter(
        is_active=True,
        current_stock__lte=models_min_stock()
    ).count() if hasattr(Product, 'objects') else 0

    return {
        'APP_NAME': 'Apex Billing & Inventory',
        'APP_VERSION': '2.0.0',
        'CURRENCY': '$',
        'CURRENCY_CODE': 'USD',
        'COMPANY_NAME': 'Apex Retail & Logistics Ltd.',
        'COMPANY_ADDRESS': '100 Innovation Parkway, Suite 400, Tech City, CA 94016',
        'COMPANY_PHONE': '+1 (800) 555-0199',
        'COMPANY_EMAIL': 'billing@apexsolutions.io',
        'COMPANY_GST': 'GSTIN-06AAAAA0000A1Z5',
        'low_stock_alert_count': get_low_stock_count(),
        'unpaid_invoices_count': get_unpaid_invoices_count(),
    }

def models_min_stock():
    # helper for query condition
    from django.db.models import F
    return F('min_stock_level')

def get_low_stock_count():
    try:
        from django.db.models import F
        return Product.objects.filter(is_active=True, current_stock__lte=F('min_stock_level')).count()
    except Exception:
        return 0

def get_unpaid_invoices_count():
    try:
        return Invoice.objects.filter(status__in=['ISSUED', 'PARTIALLY_PAID']).count()
    except Exception:
        return 0
