# 🚀 Apex Billing & Inventory Stock Management System

A full-featured, modern Django web application for business **Billing, Invoicing, Point of Sale (POS), and Inventory Stock Control** with full CRUD operations, automated inventory deductions, stock movement audit trails, supplier purchase orders, and financial analytics.

---

## ✨ Key Features

### 1. 📦 Inventory Management (CRUD)
- **Product Catalog**: Manage products with Name, SKU, Barcode, Category, Supplier, Cost Price, Selling Price, Tax (GST/VAT) %, Current Stock, and Minimum Reorder Thresholds.
- **Automated Stock Deduction**: Selling items on invoices automatically reduces current stock in real time.
- **Safe Stock Reversals**: Cancelling or deleting an invoice automatically restores product quantities back into inventory.
- **Stock Movements Audit Log**: Full transaction history tracking every stock addition, sale deduction, damage/loss adjustment, supplier inward order, and customer return.
- **Stock Alerts**: Real-time visual alerts and counters for **Low Stock** and **Out of Stock** items.
- **Category & Supplier Management**: Full CRUD for categorizing items and tracking supplier/vendor records.

### 2. 🧾 Billing & Invoicing (CRUD & POS Engine)
- **Interactive Invoice Builder**:
  - Live search and product dropdown with real-time price, tax %, and stock availability indicators.
  - Dynamic line item addition and removal.
  - Real-time client-side calculation of Subtotal, Tax (GST), Global Discounts, Grand Total, and Outstanding Balances.
  - "+ Quick Add Customer" modal without page refresh.
- **Payment Lifecycle Tracking**:
  - Statuses: `Draft`, `Issued / Unpaid`, `Partially Paid`, `Paid`, `Cancelled`.
  - Multiple payment modes: `Cash`, `UPI / QR`, `Credit / Debit Card`, `Bank Transfer`, `Cheque`, `Credit`.
  - Record partial or full payments against existing invoices.
- **Printable Tax Invoice / PDF Format**:
  - Dedicated clean, professional tax invoice layout with barcode, company credentials, terms & conditions, and payment status stamps.

### 3. 📥 Purchase Orders & Inward Stock
- Create purchase orders for suppliers.
- **One-Click Goods Receipt**: Mark orders as received to automatically replenish inventory stock and update cost baselines.

### 4. 👥 Customer & Supplier Management (CRUD)
- Complete customer directory with contact information, GST/Tax IDs, and addresses.
- **Customer Ledger View**: Complete financial profile showing lifetime amount billed, cleared payments, and current outstanding receivables with full invoice history.

### 5. 📊 Executive Dashboard & Analytics
- Financial KPI cards: Total Revenue, Outstanding Receivables, Total Stock Valuation (Retail & Cost basis).
- **Chart.js 7-Day Revenue Trend** chart.
- Top Selling Products ranking.
- Critical Low Stock warnings with instant restock shortcuts.
- **Sales & Tax Report**: Date range filters with payment method distribution and tax liability calculations.

---

## 🛠️ Tech Stack
- **Backend**: Python 3.14 / Django 6.1
- **Database**: SQLite (Ready for PostgreSQL / MySQL)
- **Frontend**: Responsive HTML5, Vanilla CSS Design System with Plus Jakarta Sans typography, Chart.js for visualizations, and Print Stylesheets.

---

## ⚡ Quick Start Guide

### 1. Install Dependencies
```bash
pip install django
```

### 2. Apply Database Migrations
```bash
python manage.py migrate
```

### 3. (Optional) Load Realistic Sample Data
Populate the database with ready-to-use sample categories, suppliers, products with varied stock levels, customers, invoices, and payments:
```bash
python manage.py seed_data
```

### 4. Start the Development Server
```bash
python manage.py runserver
```
Visit: **`http://127.0.0.1:8000/`**

---

## 🔐 Admin Credentials
- **URL**: `http://127.0.0.1:8000/admin/`
- **Username**: `admin`
- **Password**: `admin`

---

## 📁 Project Structure
```
Trial_app/
├── billing/                       # Billing & Invoicing App
│   ├── models.py                  # Customer, Invoice, InvoiceItem, Payment, PurchaseOrder
│   ├── views.py                   # Invoicing engine, Payments, Customers, POs, Reports
│   ├── urls.py                    # Billing URL routes
│   ├── forms.py                   # Customer, Payment, PO forms
│   ├── context_processors.py      # Global company details & stock alerts
│   ├── admin.py                   # Django admin inlines and registrations
│   └── tests.py                   # Automated test suite
├── inventory/                     # Inventory & Stock Management App
│   ├── models.py                  # Product, Category, Supplier, StockMovement
│   ├── views.py                   # Dashboard, Products CRUD, Stock Adjustments, Movements
│   ├── urls.py                    # Inventory URL routes
│   ├── forms.py                   # Product, Category, Supplier, Stock Adjustment forms
│   ├── admin.py                   # Django admin registrations
│   └── management/commands/       # seed_data command
├── config/                        # Core Django settings & master URL routing
├── templates/                     # Master UI templates & print templates
├── static/                        # CSS Design System & dynamic JavaScript
└── manage.py                      # Django CLI
```
