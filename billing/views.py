from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, Q, F
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal
import datetime
import json

from .models import Customer, Invoice, InvoiceItem, Payment, PurchaseOrder, PurchaseOrderItem
from .forms import CustomerForm, PaymentForm, PurchaseOrderForm
from inventory.models import Product, StockMovement, Supplier

def generate_invoice_number():
    """Generates unique sequential invoice number like INV-202609-0001"""
    now = timezone.now()
    prefix = f"INV-{now.strftime('%Y%m')}-"
    last_invoice = Invoice.objects.filter(invoice_number__startswith=prefix).order_by('-invoice_number').first()
    if last_invoice:
        try:
            last_seq = int(last_invoice.invoice_number.split('-')[-1])
            new_seq = last_seq + 1
        except Exception:
            new_seq = 1
    else:
        new_seq = 1
    return f"{prefix}{new_seq:04d}"

def generate_po_number():
    """Generates unique sequential PO number like PO-202609-0001"""
    now = timezone.now()
    prefix = f"PO-{now.strftime('%Y%m')}-"
    last_po = PurchaseOrder.objects.filter(po_number__startswith=prefix).order_by('-po_number').first()
    if last_po:
        try:
            last_seq = int(last_po.po_number.split('-')[-1])
            new_seq = last_seq + 1
        except Exception:
            new_seq = 1
    else:
        new_seq = 1
    return f"{prefix}{new_seq:04d}"

# ================= INVOICE VIEWS =================

def invoice_list(request):
    """List all sales invoices with multi-faceted filtering"""
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    customer_id = request.GET.get('customer', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    invoices = Invoice.objects.select_related('customer').all()

    if query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=query) |
            Q(customer__name__icontains=query) |
            Q(customer__phone__icontains=query) |
            Q(notes__icontains=query)
        )
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    if customer_id:
        invoices = invoices.filter(customer_id=customer_id)
    if date_from:
        invoices = invoices.filter(invoice_date__gte=date_from)
    if date_to:
        invoices = invoices.filter(invoice_date__lte=date_to)

    paginator = Paginator(invoices, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    customers = Customer.objects.all()

    context = {
        'page_obj': page_obj,
        'customers': customers,
        'status_choices': Invoice.STATUS_CHOICES,
        'selected_status': status_filter,
        'selected_customer': customer_id,
        'date_from': date_from,
        'date_to': date_to,
        'query': query,
    }
    return render(request, 'billing/invoice_list.html', context)

def invoice_create(request):
    """Create Invoice with interactive product lines & stock deduction"""
    if request.method == 'POST':
        try:
            customer_id = request.POST.get('customer')
            invoice_number = request.POST.get('invoice_number') or generate_invoice_number()
            invoice_date = request.POST.get('invoice_date') or timezone.now().date()
            due_date = request.POST.get('due_date') or invoice_date
            payment_method = request.POST.get('payment_method', 'CASH')
            discount_amount = Decimal(request.POST.get('discount_amount', '0') or '0')
            notes = request.POST.get('notes', '')
            terms = request.POST.get('terms', '')
            amount_paid_initial = Decimal(request.POST.get('amount_paid', '0') or '0')
            payment_reference = request.POST.get('payment_reference', '')

            # Items data from dynamic rows
            product_ids = request.POST.getlist('product_id[]')
            quantities = request.POST.getlist('quantity[]')
            unit_prices = request.POST.getlist('unit_price[]')
            tax_rates = request.POST.getlist('tax_rate[]')
            item_discounts = request.POST.getlist('item_discount[]')

            if not customer_id:
                messages.error(request, "Please select or create a customer.")
                return redirect('billing:invoice_create')

            if not product_ids or len(product_ids) == 0:
                messages.error(request, "Invoice must contain at least one item.")
                return redirect('billing:invoice_create')

            customer = get_object_or_404(Customer, pk=customer_id)

            with transaction.atomic():
                # 1. Create Invoice instance
                invoice = Invoice.objects.create(
                    invoice_number=invoice_number,
                    customer=customer,
                    invoice_date=invoice_date,
                    due_date=due_date,
                    payment_method=payment_method,
                    discount_amount=discount_amount,
                    notes=notes,
                    terms=terms,
                    created_by=request.user if request.user.is_authenticated else None
                )

                subtotal = Decimal('0.00')
                total_tax = Decimal('0.00')

                # 2. Add Invoice Items and Deduct Inventory Stock
                for i in range(len(product_ids)):
                    pid = product_ids[i]
                    if not pid:
                        continue
                    product = Product.objects.select_for_update().get(pk=pid)
                    qty = Decimal(quantities[i] or '1')
                    price = Decimal(unit_prices[i] or str(product.selling_price))
                    tax_rt = Decimal(tax_rates[i] or str(product.tax_rate))
                    disc = Decimal(item_discounts[i] if i < len(item_discounts) and item_discounts[i] else '0')

                    line_base = (qty * price) - disc
                    line_tax = (line_base * tax_rt) / Decimal('100.00') if tax_rt > 0 else Decimal('0.00')
                    line_total = line_base + line_tax

                    subtotal += line_base
                    total_tax += line_tax

                    # Create Invoice item
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product=product,
                        quantity=qty,
                        unit_price=price,
                        tax_rate=tax_rt,
                        tax_amount=line_tax,
                        discount_amount=disc,
                        total_price=line_total
                    )

                    # Deduct stock & create movement record
                    prev_stock = product.current_stock
                    product.current_stock -= qty
                    product.save()

                    StockMovement.objects.create(
                        product=product,
                        movement_type='OUT_SALE',
                        quantity=qty,
                        previous_stock=prev_stock,
                        resulting_stock=product.current_stock,
                        unit_price=price,
                        reference_number=invoice.invoice_number,
                        notes=f"Sold to {customer.name} (Invoice {invoice.invoice_number})",
                        created_by=request.user if request.user.is_authenticated else None
                    )

                # 3. Finalize totals
                invoice.subtotal = subtotal
                invoice.tax_amount = total_tax
                invoice.grand_total = max(Decimal('0.00'), (subtotal + total_tax) - discount_amount)

                # 4. Handle initial payment if provided
                if amount_paid_initial > 0:
                    Payment.objects.create(
                        invoice=invoice,
                        amount=amount_paid_initial,
                        payment_date=invoice_date,
                        payment_method=payment_method,
                        reference_number=payment_reference,
                        notes="Payment received at invoice creation"
                    )

                invoice.recalculate_totals(save=True)

            messages.success(request, f"Invoice {invoice.invoice_number} created successfully and stock updated!")
            return redirect('billing:invoice_detail', pk=invoice.pk)

        except Exception as e:
            messages.error(request, f"Error creating invoice: {str(e)}")
            return redirect('billing:invoice_create')

    else:
        # Pre-fill data
        customers = Customer.objects.all()
        products = Product.objects.filter(is_active=True).select_related('category')
        new_inv_number = generate_invoice_number()
        today = timezone.now().date().strftime('%Y-%m-%d')

        context = {
            'customers': customers,
            'products': products,
            'new_inv_number': new_inv_number,
            'today': today,
            'payment_methods': Invoice.PAYMENT_METHOD_CHOICES,
        }
        return render(request, 'billing/invoice_create.html', context)

def invoice_detail(request, pk):
    """View invoice details, items, payment history, and payment modal"""
    invoice = get_object_or_404(Invoice.objects.select_related('customer', 'created_by').prefetch_related('items__product', 'payments'), pk=pk)
    payment_form = PaymentForm(initial={'amount': invoice.balance_due, 'payment_date': timezone.now().date()})
    
    context = {
        'invoice': invoice,
        'payment_form': payment_form,
    }
    return render(request, 'billing/invoice_detail.html', context)

def invoice_print(request, pk):
    """Print / PDF export template for invoice receipt"""
    invoice = get_object_or_404(Invoice.objects.select_related('customer').prefetch_related('items__product', 'payments'), pk=pk)
    return render(request, 'billing/invoice_print.html', {'invoice': invoice})

def invoice_cancel(request, pk):
    """Cancel invoice and restore stock to inventory"""
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        if invoice.status == 'CANCELLED':
            messages.warning(request, "This invoice is already cancelled.")
            return redirect('billing:invoice_detail', pk=pk)

        with transaction.atomic():
            # Return stock for each item
            for item in invoice.items.all():
                product = Product.objects.select_for_update().get(pk=item.product.pk)
                prev_stock = product.current_stock
                product.current_stock += item.quantity
                product.save()

                StockMovement.objects.create(
                    product=product,
                    movement_type='RETURN_CUSTOMER',
                    quantity=item.quantity,
                    previous_stock=prev_stock,
                    resulting_stock=product.current_stock,
                    unit_price=item.unit_price,
                    reference_number=f"CANCEL-{invoice.invoice_number}",
                    notes=f"Stock restored due to cancellation of Invoice {invoice.invoice_number}",
                    created_by=request.user if request.user.is_authenticated else None
                )

            invoice.status = 'CANCELLED'
            invoice.save()

        messages.success(request, f"Invoice {invoice.invoice_number} has been cancelled and stock returned to inventory.")
        return redirect('billing:invoice_detail', pk=pk)

    return render(request, 'billing/invoice_confirm_cancel.html', {'invoice': invoice})

def invoice_delete(request, pk):
    """Delete invoice with inventory reversal if active"""
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        inv_num = invoice.invoice_number
        with transaction.atomic():
            if invoice.status != 'CANCELLED':
                for item in invoice.items.all():
                    product = Product.objects.select_for_update().get(pk=item.product.pk)
                    prev_stock = product.current_stock
                    product.current_stock += item.quantity
                    product.save()

                    StockMovement.objects.create(
                        product=product,
                        movement_type='RETURN_CUSTOMER',
                        quantity=item.quantity,
                        previous_stock=prev_stock,
                        resulting_stock=product.current_stock,
                        unit_price=item.unit_price,
                        reference_number=f"DEL-{inv_num}",
                        notes=f"Stock returned on deletion of Invoice {inv_num}",
                        created_by=request.user if request.user.is_authenticated else None
                    )
            invoice.delete()

        messages.success(request, f"Invoice {inv_num} deleted successfully.")
        return redirect('billing:invoice_list')

    return render(request, 'billing/invoice_confirm_delete.html', {'invoice': invoice})

def record_payment(request, pk):
    """Record a payment against an invoice"""
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.save()
            invoice.recalculate_totals(save=True)
            messages.success(request, f"Payment of {payment.amount} recorded for Invoice {invoice.invoice_number}.")
        else:
            messages.error(request, "Failed to record payment. Please check form errors.")
    return redirect('billing:invoice_detail', pk=pk)

# ================= CUSTOMER VIEWS =================

def customer_list(request):
    """List customers with search and invoice summary"""
    query = request.GET.get('q', '').strip()
    customers = Customer.objects.annotate(
        invoices_count=Count('invoices'),
        total_spent=Sum('invoices__grand_total', filter=~Q(invoices__status='CANCELLED'))
    ).order_by('name')

    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(company_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query) |
            Q(tax_id__icontains=query)
        )

    paginator = Paginator(customers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'billing/customer_list.html', {'page_obj': page_obj, 'query': query})

def customer_detail(request, pk):
    """Customer profile and financial ledger history"""
    customer = get_object_or_404(Customer, pk=pk)
    invoices = customer.invoices.all().order_by('-invoice_date')
    
    total_billed = sum(i.grand_total for i in invoices.exclude(status='CANCELLED'))
    total_paid = sum(i.amount_paid for i in invoices.exclude(status='CANCELLED'))
    total_due = sum(i.balance_due for i in invoices.exclude(status='CANCELLED'))

    context = {
        'customer': customer,
        'invoices': invoices,
        'total_billed': total_billed,
        'total_paid': total_paid,
        'total_due': total_due,
    }
    return render(request, 'billing/customer_detail.html', context)

def customer_create(request):
    """Create customer or handle AJAX customer creation from invoice form"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
                return JsonResponse({
                    'status': 'success',
                    'id': customer.id,
                    'name': customer.name,
                    'phone': customer.phone,
                    'email': customer.email or '',
                    'address': customer.address or ''
                })
            messages.success(request, f"Customer '{customer.name}' created successfully!")
            return redirect('billing:customer_detail', pk=customer.pk)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    else:
        form = CustomerForm()
    return render(request, 'billing/customer_form.html', {'form': form, 'title': 'Add New Customer'})

def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Customer '{customer.name}' updated successfully!")
            return redirect('billing:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'billing/customer_form.html', {'form': form, 'title': f'Edit Customer: {customer.name}'})

def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        name = customer.name
        customer.delete()
        messages.success(request, f"Customer '{name}' deleted successfully.")
        return redirect('billing:customer_list')
    return render(request, 'billing/customer_confirm_delete.html', {'customer': customer})

# ================= PURCHASE ORDERS / STOCK INWARD =================

def purchase_list(request):
    """List purchase orders from suppliers"""
    purchases = PurchaseOrder.objects.select_related('supplier').all()
    paginator = Paginator(purchases, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'billing/purchase_list.html', {'page_obj': page_obj})

def purchase_create(request):
    """Create Purchase Order / Stock Inward from supplier"""
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        po_number = request.POST.get('po_number') or generate_po_number()
        order_date = request.POST.get('order_date') or timezone.now().date()
        notes = request.POST.get('notes', '')
        auto_receive = request.POST.get('auto_receive') == 'on'

        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        unit_costs = request.POST.getlist('unit_cost[]')

        if not supplier_id or not product_ids:
            messages.error(request, "Supplier and at least one item are required.")
            return redirect('billing:purchase_create')

        supplier = get_object_or_404(Supplier, pk=supplier_id)

        with transaction.atomic():
            po = PurchaseOrder.objects.create(
                po_number=po_number,
                supplier=supplier,
                order_date=order_date,
                status='RECEIVED' if auto_receive else 'PENDING',
                received_date=order_date if auto_receive else None,
                notes=notes
            )

            for i in range(len(product_ids)):
                pid = product_ids[i]
                if not pid:
                    continue
                product = Product.objects.select_for_update().get(pk=pid)
                qty = Decimal(quantities[i] or '1')
                cost = Decimal(unit_costs[i] or str(product.cost_price))

                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product=product,
                    quantity=qty,
                    unit_cost=cost
                )

                # If auto receive or inward stock immediately
                if auto_receive:
                    prev_stock = product.current_stock
                    product.current_stock += qty
                    # Update product cost price if changed
                    if cost > 0:
                        product.cost_price = cost
                    product.save()

                    StockMovement.objects.create(
                        product=product,
                        movement_type='IN_PURCHASE',
                        quantity=qty,
                        previous_stock=prev_stock,
                        resulting_stock=product.current_stock,
                        unit_price=cost,
                        reference_number=po.po_number,
                        notes=f"Stock In from {supplier.name} (PO {po.po_number})",
                        created_by=request.user if request.user.is_authenticated else None
                    )

            po.recalculate_total(save=True)

        messages.success(request, f"Purchase Order {po.po_number} created successfully!")
        return redirect('billing:purchase_detail', pk=po.pk)

    suppliers = Supplier.objects.all()
    products = Product.objects.filter(is_active=True)
    new_po_number = generate_po_number()
    today = timezone.now().date().strftime('%Y-%m-%d')

    return render(request, 'billing/purchase_create.html', {
        'suppliers': suppliers,
        'products': products,
        'new_po_number': new_po_number,
        'today': today,
    })

def purchase_detail(request, pk):
    """View purchase order details"""
    po = get_object_or_404(PurchaseOrder.objects.select_related('supplier').prefetch_related('items__product'), pk=pk)
    return render(request, 'billing/purchase_detail.html', {'po': po})

def purchase_receive(request, pk):
    """Mark purchase order as received and add stock to inventory"""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == 'POST':
        if po.status == 'RECEIVED':
            messages.warning(request, "This purchase order is already marked as received.")
            return redirect('billing:purchase_detail', pk=pk)

        with transaction.atomic():
            for item in po.items.all():
                product = Product.objects.select_for_update().get(pk=item.product.pk)
                prev_stock = product.current_stock
                product.current_stock += item.quantity
                if item.unit_cost > 0:
                    product.cost_price = item.unit_cost
                product.save()

                StockMovement.objects.create(
                    product=product,
                    movement_type='IN_PURCHASE',
                    quantity=item.quantity,
                    previous_stock=prev_stock,
                    resulting_stock=product.current_stock,
                    unit_price=item.unit_cost,
                    reference_number=po.po_number,
                    notes=f"Received goods from {po.supplier.name} (PO {po.po_number})",
                    created_by=request.user if request.user.is_authenticated else None
                )

            po.status = 'RECEIVED'
            po.received_date = timezone.now().date()
            po.save()

        messages.success(request, f"Goods from PO {po.po_number} received into inventory successfully!")
        return redirect('billing:purchase_detail', pk=pk)

    return render(request, 'billing/purchase_confirm_receive.html', {'po': po})

# ================= REPORTS & ANALYTICS =================

def sales_report(request):
    """Comprehensive sales and tax report"""
    today = timezone.now().date()
    date_from = request.GET.get('date_from', (today - datetime.timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', today.strftime('%Y-%m-%d'))

    invoices = Invoice.objects.exclude(status='CANCELLED').filter(
        invoice_date__gte=date_from,
        invoice_date__lte=date_to
    ).select_related('customer')

    summary = invoices.aggregate(
        total_revenue=Sum('grand_total'),
        total_tax=Sum('tax_amount'),
        total_discount=Sum('discount_amount'),
        total_paid=Sum('amount_paid'),
        total_due=Sum('balance_due'),
        invoice_count=Count('id')
    )

    # Payment method breakdown
    method_breakdown = (
        invoices.values('payment_method')
        .annotate(count=Count('id'), total=Sum('grand_total'))
        .order_by('-total')
    )

    context = {
        'invoices': invoices.order_by('-invoice_date'),
        'summary': summary,
        'method_breakdown': method_breakdown,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'billing/sales_report.html', context)
