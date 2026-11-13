# MyShop.kh — Flask + Tailwind CSS + Bakong KHQR (Zero JavaScript)

A modern, production-ready, **100% server-side rendered (SSR)** e-commerce web application powered by **Python Flask**, **PostgreSQL**, **Cloudflare R2**, **Tailwind CSS**, and **NBC Bakong KHQR**.

This project implements a complete e-commerce lifecycle with **Zero Client-Side JavaScript**—from catalog browsing, server-side session cart management, and guest checkout to auto-refreshing KHQR payment settlement and full administrative product/order management.

---

## 🌟 Key Architecture Highlights

* **Zero-JavaScript Architecture:** Delivered completely via Flask server-rendered Jinja2 templates and compiled static Tailwind CSS. Shopping cart operations, quantity updates, product additions, removals, and checkout submissions are handled using standard HTML `<form method="POST">` requests.
* **NBC Bakong KHQR Auto-Refresh Flow:** The checkout payment screen uses standard HTML `<meta http-equiv="refresh" content="3">`. Every 3 seconds, the browser auto-refreshes `/checkout/pay/<order_code>`, enabling Flask to verify payment status directly with the Bakong Open API on the server. Once confirmed as `PAID`, stock is deducted in PostgreSQL, the session cart is cleared, and the customer is redirected to the order confirmation page.
* **Cloudflare R2 Object Storage:** Product images are uploaded via Python's `boto3` SDK to Cloudflare R2 S3-compatible object storage and served publicly (with graceful local fallback when running in offline/unconfigured environments).
* **Robust Relational Data Modeling:** Backed by PostgreSQL (or local SQLite for dev) using Flask-SQLAlchemy, Flask-Migrate (Alembic), and strict `NUMERIC(10, 2)` monetary precision.
* **Protected Admin Portal:** Session-based authentication powered by Flask-Login with secure `werkzeug.security` password hashing.

---

## 📁 Directory Structure

```text
final-project/
├── app/
│   ├── __init__.py               # Flask app factory, SQLAlchemy, Migrate, LoginManager & context processors
│   ├── models.py                 # SQLAlchemy models (Admin, Product, Order, OrderItem)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── public.py             # Public storefront, session cart, checkout & KHQR refresh routes
│   │   └── admin.py              # Protected Admin product CRUD & order history routes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── khqr_service.py       # Bakong KHQR generation & Open API verification service
│   │   └── r2_service.py         # Cloudflare R2 image upload & deletion service (boto3)
│   ├── static/
│   │   ├── css/
│   │   │   ├── input.css         # Tailwind source directives
│   │   │   └── output.css        # Minified static Tailwind CSS (zero client JS)
│   │   └── uploads/              # Local storage fallback directory for product images
│   └── templates/
│       ├── base.html             # Shared Tailwind layout, live session cart badge, flash alerts
│       ├── public/
│       │   ├── index.html        # Home Page (responsive catalog grid & search)
│       │   ├── product.html      # Product Detail + pure HTML Facebook & Telegram share links
│       │   ├── cart.html         # Shopping Cart (HTML POST forms for qty updates & removal)
│       │   ├── checkout.html     # Guest Info & Delivery Address Form
│       │   ├── checkout_qr.html  # KHQR Display Page with <meta http-equiv="refresh" content="3">
│       │   └── confirm.html      # Order Confirmation Summary Page
│       └── admin/
│           ├── login.html        # Admin Login Page
│           ├── products.html     # Admin Product Management Table
│           ├── product_form.html # Create / Edit Product Form (multipart upload -> Cloudflare R2)
│           ├── orders.html       # Admin Order History Table with status filtering
│           └── order_detail.html # Dedicated Order Details Page (items, totals, KHQR MD5)
├── migrations/                   # Alembic database migration versions
├── tests/
│   └── test_shop.py              # Automated test suite covering public & admin workflows
├── .env                          # Local environment variables (gitignored)
├── .env.example                  # Environment configuration template
├── requirements.txt              # Python package dependencies
├── seed.py                       # Database seeder (Admin + sample products + $0.01 live test item)
├── run.py                        # Application entry point
└── tailwindcss.exe               # Standalone Tailwind CLI compiler
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites

* **Python 3.10+** (tested on Python 3.12 & Python 3.14)
* **Virtual Environment** (`venv`)

### 2. Setup Virtual Environment & Install Dependencies

```bash
# Clone or navigate into the project directory
cd final-project

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. Configure Environment Variables (`.env`)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` to configure your settings:

```env
FLASK_SECRET_KEY=dev-myshop-khqr-secret-key-2026

# PostgreSQL Connection (Neon, Supabase, Railway, or local Postgres)
# Leave empty or commented out to use the local SQLite database (myshop.db)
# DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# Cloudflare R2 Object Storage (optional; falls back to local /static/uploads/ if blank)
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_ACCESS_KEY_ID=your_r2_access_key_id
R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
R2_BUCKET_NAME=myshop-products
R2_PUBLIC_URL=https://pub-xxxxxxxxxxxxxxxx.r2.dev

# Bakong KHQR Configuration
BAKONG_TOKEN=your_bakong_token
BAKONG_ACCOUNT_ID=your_account@aclb
MERCHANT_NAME=MyShop Cambodia
MERCHANT_CITY=Phnom Penh
STORE_LABEL=MyShop Online
MERCHANT_PHONE=85512345678
CURRENCY=USD

# Optional relay for hosting outside Cambodia (Geo-IP restriction bypass)
KHQR_RELAY_BASE_URL=

# Demo Mode (enables safe payment simulation button on checkout page for grading/demos)
DEMO_MODE=true
```

### 4. Database Initialization & Seeding

```bash
# Apply migrations or seed initial data
python seed.py
```

This creates the database tables, seeds the default admin user, and adds 8 realistic sample products including the `$0.01` live test product.

### 5. Compile Tailwind CSS (Zero JavaScript)

The project includes the standalone Tailwind CLI executable. Recompile whenever template classes change:

```bash
# Build minified static CSS
.\tailwindcss.exe -i .\app\static\css\input.css -o .\app\static\css\output.css --minify
```

### 6. Run the Application

```bash
python run.py
```

Open your browser at **[http://127.0.0.1:5000](http://127.0.0.1:5000)**.

---

## 🔑 Default Credentials & Admin Access

* **Admin Login URL:** `http://127.0.0.1:5000/admin/login`
* **Username:** `admin`
* **Password:** `admin123`

---

## 💳 Live KHQR Video Walkthrough Guide

1. **Browsing:** Visit the storefront at `http://127.0.0.1:5000`. Search for products using the search bar or click any item to view its details.
2. **Social Sharing:** On any product page, click **Share on Facebook** or **Share on Telegram**. Notice that these are pure HTML links that encode the server URL with zero JavaScript.
3. **Cart Management:** Add items to cart. Go to `/cart` and update quantities or remove items. All actions are handled via standard HTML POST requests.
4. **Checkout:** Proceed to checkout, fill in the guest customer details (name, email, phone, shipping address), and click **Place Order & Pay with KHQR**.
5. **Live Payment Screen:**
   * An official Bakong EMVCo QR code is generated with MD5 checksum.
   * `<meta http-equiv="refresh" content="3">` re-checks verification automatically every 3 seconds.
   * **Live Test:** If testing with real ABA or Bakong mobile apps, choose the seeded **"Live KHQR Test Product ($0.01)"** to test scanning and paying 1 cent live.
   * **Demo Simulation:** If testing in demo mode or outside Cambodia, click the **"[Demo Mode] Simulate Successful KHQR Payment"** button to simulate payment settlement.
6. **Order Confirmation:** Once settled, the customer is redirected to `/order-confirmation/<order_code>`, stock is automatically decremented in PostgreSQL, and the cart is emptied.
7. **Admin Portal:** Log in at `/admin/login` to see the newly placed order in `/admin/orders` and view full order details in `/admin/orders/<id>`.

---

## 🧪 Running Automated Tests

Run the complete test suite:

```bash
python -m unittest tests/test_shop.py
```

Tests cover:
* Public catalog rendering and search query filtering.
* Product details and pure HTML Facebook/Telegram share links.
* Session shopping cart additions, quantity updates, and removals.
* Checkout form validation and EMVCo KHQR code generation.
* Auto-refreshing payment flow, order settlement, and stock deduction.
* Admin session authentication and full Product CRUD.
