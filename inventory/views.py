from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, F, Count, Q, Avg
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from .models import Product, Category, Supplier, StockMovement
from .forms import ProductForm, CategoryForm, SupplierForm, StockAdjustmentForm
from billing.models import Invoice, InvoiceItem, Customer, PurchaseOrder

def dashboard(request):
    """Main Analytics & Operational Dashboard"""
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    # Financial KPI Metrics
    total_sales_all_time = Invoice.objects.exclude(status='CANCELLED').aggregate(total=Sum('grand_total'))['total'] or Decimal('0.00')
    total_sales_month = Invoice.objects.exclude(status='CANCELLED').filter(invoice_date__gte=start_of_month).aggregate(total=Sum('grand_total'))['total'] or Decimal('0.00')
    total_paid_received = Invoice.objects.exclude(status='CANCELLED').aggregate(paid=Sum('amount_paid'))['paid'] or Decimal('0.00')
    total_outstanding_due = Invoice.objects.exclude(status='CANCELLED').aggregate(due=Sum('balance_due'))['due'] or Decimal('0.00')
    
    # Inventory KPI Metrics
    total_products_count = Product.objects.filter(is_active=True).count()
    low_stock_products = Product.objects.filter(is_active=True, current_stock__gt=0, current_stock__lte=F('min_stock_level'))
    out_of_stock_products = Product.objects.filter(is_active=True, current_stock__lte=0)
    
    total_stock_cost_value = sum(p.total_cost_value for p in Product.objects.filter(is_active=True))
    total_stock_retail_value = sum(p.total_retail_value for p in Product.objects.filter(is_active=True))
    potential_profit = max(Decimal('0.00'), total_stock_retail_value - total_stock_cost_value)

    # Recent Data
    recent_invoices = Invoice.objects.select_related('customer').order_by('-created_at')[:6]
    recent_movements = StockMovement.objects.select_related('product').order_by('-created_at')[:8]
    
    # Chart Data: Last 7 Days Revenue
    last_7_days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    chart_dates = [d.strftime('%b %d') for d in last_7_days]
    chart_sales = []
    
    for d in last_7_days:
        daily_sum = Invoice.objects.exclude(status='CANCELLED').filter(invoice_date=d).aggregate(s=Sum('grand_total'))['s'] or Decimal('0.00')
        chart_sales.append(float(daily_sum))
        
    # Top 5 Selling Products
    top_selling_items = (
        InvoiceItem.objects.filter(invoice__status__in=['PAID', 'ISSUED', 'PARTIALLY_PAID'])
        .values('product__name', 'product__sku')
        .annotate(total_qty=Sum('quantity'), total_revenue=Sum('total_price'))
        .order_by('-total_qty')[:5]
    )

    context = {
        'total_sales_all_time': total_sales_all_time,
        'total_sales_month': total_sales_month,
        'total_paid_received': total_paid_received,
        'total_outstanding_due': total_outstanding_due,
        'total_products_count': total_products_count,
        'low_stock_count': low_stock_products.count(),
        'out_of_stock_count': out_of_stock_products.count(),
        'low_stock_items': low_stock_products[:5],
        'total_stock_cost_value': total_stock_cost_value,
        'total_stock_retail_value': total_stock_retail_value,
        'potential_profit': potential_profit,
        'recent_invoices': recent_invoices,
        'recent_movements': recent_movements,
        'top_selling_items': top_selling_items,
        'chart_dates_json': json.dumps(chart_dates),
        'chart_sales_json': json.dumps(chart_sales),
    }
    return render(request, 'inventory/dashboard.html', context)

def product_list(request):
    """List products with real-time search, filters and pagination"""
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    stock_filter = request.GET.get('stock_status', '')
    
    products = Product.objects.filter(is_active=True).select_related('category', 'supplier')
    
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(barcode__icontains=query) |
            Q(description__icontains=query)
        )
        
    if category_id:
        products = products.filter(category_id=category_id)
        
    if stock_filter == 'low':
        products = products.filter(current_stock__gt=0, current_stock__lte=F('min_stock_level'))
    elif stock_filter == 'out':
        products = products.filter(current_stock__lte=0)
    elif stock_filter == 'in':
        products = products.filter(current_stock__gt=F('min_stock_level'))
        
    paginator = Paginator(products.order_by('name'), 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.all()
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'stock_filter': stock_filter,
        'total_results': products.count(),
    }
    return render(request, 'inventory/product_list.html', context)

def product_detail(request, pk):
    """Detailed view for a product with stock history"""
    product = get_object_or_404(Product, pk=pk)
    movements = product.movements.all().order_by('-created_at')[:20]
    
    # Recent invoice sales with this product
    recent_sales = InvoiceItem.objects.filter(product=product).select_related('invoice', 'invoice__customer').order_by('-invoice__invoice_date')[:10]
    
    context = {
        'product': product,
        'movements': movements,
        'recent_sales': recent_sales,
    }
    return render(request, 'inventory/product_detail.html', context)

def product_create(request):
    """Create new product with initial stock movement entry"""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                product = form.save()
                # Log initial stock movement if stock > 0
                if product.current_stock > 0:
                    StockMovement.objects.create(
                        product=product,
                        movement_type='IN_PURCHASE',
                        quantity=product.current_stock,
                        previous_stock=Decimal('0.00'),
                        resulting_stock=product.current_stock,
                        unit_price=product.cost_price,
                        reference_number='INITIAL_STOCK',
                        notes='Initial stock added on product creation',
                        created_by=request.user if request.user.is_authenticated else None
                    )
            messages.success(request, f"Product '{product.name}' created successfully!")
            return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = ProductForm()
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Add New Product'})

def product_update(request, pk):
    """Update existing product"""
    product = get_object_or_404(Product, pk=pk)
    old_stock = product.current_stock
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            with transaction.atomic():
                updated_product = form.save()
                new_stock = updated_product.current_stock
                # If stock was directly edited in product form, log an adjustment
                if old_stock != new_stock:
                    diff = new_stock - old_stock
                    StockMovement.objects.create(
                        product=updated_product,
                        movement_type='ADJ_ADD' if diff > 0 else 'ADJ_SUB',
                        quantity=abs(diff),
                        previous_stock=old_stock,
                        resulting_stock=new_stock,
                        unit_price=updated_product.cost_price,
                        reference_number='MANUAL_EDIT',
                        notes=f"Stock updated via product edit form from {old_stock} to {new_stock}",
                        created_by=request.user if request.user.is_authenticated else None
                    )
            messages.success(request, f"Product '{product.name}' updated successfully!")
            return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
    return render(request, 'inventory/product_form.html', {'form': form, 'title': f'Edit Product: {product.name}', 'product': product})

def product_delete(request, pk):
    """Soft delete / deactivate or remove product"""
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product_name = product.name
        # Soft delete if linked to invoices or movements, else hard delete
        if product.invoice_items.exists() or product.movements.exists():
            product.is_active = False
            product.save()
            messages.info(request, f"Product '{product_name}' was archived/deactivated because it has existing transactions.")
        else:
            product.delete()
            messages.success(request, f"Product '{product_name}' deleted successfully.")
        return redirect('inventory:product_list')
    return render(request, 'inventory/product_confirm_delete.html', {'product': product})

def stock_adjust(request):
    """Manual stock adjustment (Add, Remove, Damage, Return)"""
    initial_product_id = request.GET.get('product_id')
    initial_data = {}
    if initial_product_id:
        initial_data['product'] = initial_product_id

    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            movement_type = form.cleaned_data['movement_type']
            quantity = form.cleaned_data['quantity']
            ref = form.cleaned_data.get('reference_number', '')
            notes = form.cleaned_data.get('notes', '')

            with transaction.atomic():
                # Lock row for update
                product = Product.objects.select_for_update().get(pk=product.pk)
                prev_stock = product.current_stock

                if movement_type in ['ADJ_ADD', 'RETURN_CUSTOMER']:
                    product.current_stock += quantity
                else: # ADJ_SUB, DAMAGE, RETURN_SUPPLIER
                    product.current_stock -= quantity

                product.save()

                StockMovement.objects.create(
                    product=product,
                    movement_type=movement_type,
                    quantity=quantity,
                    previous_stock=prev_stock,
                    resulting_stock=product.current_stock,
                    unit_price=product.cost_price,
                    reference_number=ref,
                    notes=notes,
                    created_by=request.user if request.user.is_authenticated else None
                )

            messages.success(request, f"Stock updated for '{product.name}'. New stock: {product.current_stock} {product.get_unit_display()}.")
            return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = StockAdjustmentForm(initial=initial_data)

    return render(request, 'inventory/stock_adjust.html', {'form': form})

def stock_movement_list(request):
    """Complete audit log of all stock movements"""
    movements = StockMovement.objects.select_related('product', 'created_by').all()
    movement_type = request.GET.get('movement_type', '')
    q = request.GET.get('q', '').strip()

    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    if q:
        movements = movements.filter(
            Q(product__name__icontains=q) |
            Q(product__sku__icontains=q) |
            Q(reference_number__icontains=q) |
            Q(notes__icontains=q)
        )

    paginator = Paginator(movements, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'movement_types': StockMovement.MOVEMENT_TYPES,
        'selected_type': movement_type,
        'q': q,
    }
    return render(request, 'inventory/stock_movement_list.html', context)

# Category CRUD
def category_list(request):
    categories = Category.objects.annotate(product_count=Count('products')).order_by('name')
    return render(request, 'inventory/category_list.html', {'categories': categories})

def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' created!")
            return redirect('inventory:category_list')
    else:
        form = CategoryForm()
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Add Category'})

def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated!")
            return redirect('inventory:category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'inventory/category_form.html', {'form': form, 'title': f'Edit Category: {category.name}'})

def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f"Category '{name}' deleted!")
        return redirect('inventory:category_list')
    return render(request, 'inventory/category_confirm_delete.html', {'category': category})

# Supplier CRUD
def supplier_list(request):
    suppliers = Supplier.objects.annotate(product_count=Count('products')).order_by('name')
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})

def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f"Supplier '{supplier.name}' created!")
            return redirect('inventory:supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'inventory/supplier_form.html', {'form': form, 'title': 'Add Supplier'})

def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f"Supplier '{supplier.name}' updated!")
            return redirect('inventory:supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'inventory/supplier_form.html', {'form': form, 'title': f'Edit Supplier: {supplier.name}'})

def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        name = supplier.name
        supplier.delete()
        messages.success(request, f"Supplier '{name}' deleted!")
        return redirect('inventory:supplier_list')
    return render(request, 'inventory/supplier_confirm_delete.html', {'supplier': supplier})

# AJAX API endpoint for instant product lookup in Billing
def api_product_search(request):
    q = request.GET.get('term', '').strip()
    products = Product.objects.filter(is_active=True)
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(barcode__icontains=q))
    
    data = []
    for p in products[:30]:
        data.append({
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'unit': p.get_unit_display(),
            'selling_price': str(p.selling_price),
            'cost_price': str(p.cost_price),
            'tax_rate': str(p.tax_rate),
            'current_stock': str(p.current_stock),
            'is_low_stock': p.is_low_stock,
            'is_out_of_stock': p.is_out_of_stock,
        })
    return JsonResponse({'results': data})
