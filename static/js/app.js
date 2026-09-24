/**
 * Billing & Inventory Core Client-Side Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Sidebar Toggle
    const mobileBtn = document.getElementById('mobileSidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (mobileBtn && sidebar) {
        mobileBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // 2. Auto Dismiss Flash Alerts
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });

    // 3. Invoice / Purchase Item Rows Calculation Logic
    initInvoiceCalculator();

    // 4. Quick Customer Modal Logic
    initQuickCustomerModal();
});

function initInvoiceCalculator() {
    const tableBody = document.getElementById('invoiceItemsTableBody');
    const addRowBtn = document.getElementById('addInvoiceItemRowBtn');
    if (!tableBody) return;

    // Attach row calculation listeners
    function attachRowListeners(row) {
        const productSelect = row.querySelector('.item-product-select');
        const qtyInput = row.querySelector('.item-qty-input');
        const priceInput = row.querySelector('.item-price-input');
        const taxInput = row.querySelector('.item-tax-input');
        const discountInput = row.querySelector('.item-discount-input');
        const removeBtn = row.querySelector('.btn-remove-row');
        const stockBadge = row.querySelector('.item-stock-indicator');

        if (productSelect) {
            productSelect.addEventListener('change', () => {
                const selectedOption = productSelect.options[productSelect.selectedIndex];
                if (selectedOption && selectedOption.dataset) {
                    const price = selectedOption.dataset.price || '0';
                    const tax = selectedOption.dataset.tax || '0';
                    const stock = parseFloat(selectedOption.dataset.stock || '0');
                    const unit = selectedOption.dataset.unit || 'pcs';

                    if (priceInput) priceInput.value = price;
                    if (taxInput) taxInput.value = tax;

                    if (stockBadge) {
                        if (stock <= 0) {
                            stockBadge.innerHTML = `<span class="badge badge-danger">Out of Stock (0 ${unit})</span>`;
                        } else if (stock <= 5) {
                            stockBadge.innerHTML = `<span class="badge badge-warning">Low Stock (${stock} ${unit})</span>`;
                        } else {
                            stockBadge.innerHTML = `<span class="badge badge-success">In Stock (${stock} ${unit})</span>`;
                        }
                    }
                }
                recalculateAll();
            });
        }

        [qtyInput, priceInput, taxInput, discountInput].forEach(input => {
            if (input) {
                input.addEventListener('input', recalculateAll);
            }
        });

        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                const allRows = tableBody.querySelectorAll('.invoice-item-row');
                if (allRows.length > 1) {
                    row.remove();
                    recalculateAll();
                } else {
                    alert('An invoice requires at least one product row.');
                }
            });
        }
    }

    // Attach to initial rows
    tableBody.querySelectorAll('.invoice-item-row').forEach(attachRowListeners);

    // Add new row button
    if (addRowBtn) {
        addRowBtn.addEventListener('click', () => {
            const firstRow = tableBody.querySelector('.invoice-item-row');
            if (!firstRow) return;

            const newRow = firstRow.cloneNode(true);
            // Reset values
            newRow.querySelector('.item-product-select').selectedIndex = 0;
            newRow.querySelector('.item-qty-input').value = '1';
            newRow.querySelector('.item-price-input').value = '0.00';
            newRow.querySelector('.item-tax-input').value = '0';
            newRow.querySelector('.item-discount-input').value = '0';
            newRow.querySelector('.item-line-total').textContent = '0.00';
            const stockBadge = newRow.querySelector('.item-stock-indicator');
            if (stockBadge) stockBadge.innerHTML = '';

            tableBody.appendChild(newRow);
            attachRowListeners(newRow);
            recalculateAll();
        });
    }

    // Overall discount & amount paid listeners
    const invoiceDiscountInput = document.getElementById('invoiceGlobalDiscount');
    const invoicePaidInput = document.getElementById('invoiceAmountPaid');

    if (invoiceDiscountInput) invoiceDiscountInput.addEventListener('input', recalculateAll);
    if (invoicePaidInput) invoicePaidInput.addEventListener('input', recalculateAll);

    // Main Recalculate Function
    function recalculateAll() {
        let subtotal = 0;
        let totalTax = 0;

        tableBody.querySelectorAll('.invoice-item-row').forEach(row => {
            const qty = parseFloat(row.querySelector('.item-qty-input')?.value || 0);
            const price = parseFloat(row.querySelector('.item-price-input')?.value || 0);
            const taxRate = parseFloat(row.querySelector('.item-tax-input')?.value || 0);
            const discount = parseFloat(row.querySelector('.item-discount-input')?.value || 0);

            const lineBase = Math.max(0, (qty * price) - discount);
            const lineTax = (lineBase * taxRate) / 100;
            const lineTotal = lineBase + lineTax;

            const lineTotalEl = row.querySelector('.item-line-total');
            if (lineTotalEl) lineTotalEl.textContent = lineTotal.toFixed(2);

            subtotal += lineBase;
            totalTax += lineTax;
        });

        const globalDiscount = parseFloat(invoiceDiscountInput?.value || 0);
        const grandTotal = Math.max(0, (subtotal + totalTax) - globalDiscount);

        const amountPaid = parseFloat(invoicePaidInput?.value || 0);
        const balanceDue = Math.max(0, grandTotal - amountPaid);

        // Update UI summary
        const subtotalEl = document.getElementById('calcSubtotal');
        const totalTaxEl = document.getElementById('calcTotalTax');
        const grandTotalEl = document.getElementById('calcGrandTotal');
        const balanceDueEl = document.getElementById('calcBalanceDue');

        if (subtotalEl) subtotalEl.textContent = subtotal.toFixed(2);
        if (totalTaxEl) totalTaxEl.textContent = totalTax.toFixed(2);
        if (grandTotalEl) grandTotalEl.textContent = grandTotal.toFixed(2);
        if (balanceDueEl) balanceDueEl.textContent = balanceDue.toFixed(2);
    }

    // Initial calculation
    recalculateAll();
}

function initQuickCustomerModal() {
    const modal = document.getElementById('quickCustomerModal');
    const openBtn = document.getElementById('btnOpenQuickCustomer');
    const closeBtn = document.getElementById('btnCloseQuickCustomer');
    const form = document.getElementById('quickCustomerForm');
    const customerSelect = document.getElementById('invoiceCustomerSelect');

    if (!modal || !openBtn) return;

    openBtn.addEventListener('click', (e) => {
        e.preventDefault();
        modal.classList.add('active');
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', () => modal.classList.remove('active'));
    }

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);

            try {
                const response = await fetch('/billing/customers/create/?format=json', {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                    },
                    body: formData
                });

                const data = await response.json();
                if (response.ok && data.status === 'success') {
                    if (customerSelect) {
                        const newOption = new Option(data.name + (data.phone ? ` (${data.phone})` : ''), data.id, true, true);
                        customerSelect.add(newOption);
                    }
                    modal.classList.remove('active');
                    form.reset();
                    alert(`Customer '${data.name}' added successfully!`);
                } else {
                    alert('Error saving customer: ' + JSON.stringify(data.errors));
                }
            } catch (err) {
                console.error(err);
                alert('An error occurred while saving customer.');
            }
        });
    }
}
