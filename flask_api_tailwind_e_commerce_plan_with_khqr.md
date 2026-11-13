# Technical Implementation Plan: ....Shop (Flask + Tailwind CSS + KHQR — Zero JavaScript)

This document outlines a **100% server-rendered, zero-JavaScript** architecture for the **ADV PP Final Project**, powered by **Python Flask**, **PostgreSQL**, **Cloudflare R2**, **Tailwind CSS**, and the **Bakong KHQR API**.

---

## 1. System Architecture & Tech Stack (Zero-JS SSR)

By relying entirely on **Server-Side Rendering (SSR)** with Flask and Jinja2, the application requires **no custom JavaScript** on the client side while still delivering a responsive, modern storefront:

* **Backend & Routing:** Python 3.10+ with **Flask** (using Blueprints to organize Public Storefront routes, Admin Management routes, and Backend Service APIs).
* **Database & ORM:** **PostgreSQL** (Neon, Supabase, Railway, or local Postgres) with **Flask-SQLAlchemy**, **Flask-Migrate**, and **`psycopg2-binary`**.
* **Object Storage (Images):** **Cloudflare R2** accessed via Python's **`boto3`** SDK and served directly via an R2 Public Bucket URL.
* **Shopping Cart State:** **Flask Server-Side Session (`flask.session`)** using signed cookies—all "Add to Cart", "Update Quantity", and "Remove" actions are handled via standard HTML `<form method="POST">` submissions.
* **Payment Integration & Auto-Check:** **`bakong-khqr`** Python SDK connected to the **NBC Bakong Open API**, paired with HTML **`<meta http-equiv="refresh" content="3">`** on the payment screen to automatically verify payment status without JavaScript.
* **Authentication:** **Flask-Login** (session-based authentication) protecting all Admin routes.
* **Frontend & Styling:** **Tailwind CSS** compiled into a static stylesheet (`app/static/css/output.css`) via the standalone Tailwind CLI so the browser executes zero JavaScript.

---

## 2. Project Directory Structure

```text
my-shop/
├── app/
│   ├── __init__.py               # Flask app factory, Postgres DB, LoginManager & context processors
│   ├── models.py                 # SQLAlchemy models (Admin, Product, Order, OrderItem)
│   ├── routes/
│   │   ├── public.py             # Public storefront, session cart, checkout & KHQR refresh routes
│   │   └── admin.py              # Protected Admin product CRUD & order history routes
│   ├── services/
│   │   ├── khqr_service.py       # Bakong KHQR generation & Open API verification service
│   │   └── r2_service.py         # Cloudflare R2 image upload & deletion service (boto3)
│   ├── static/
│   │   └── css/
│   │       ├── input.css         # Tailwind directives (@tailwind base; components; utilities;)
│   │       └── output.css        # Compiled static Tailwind CSS (zero JS)
│   └── templates/
│       ├── base.html             # Shared Tailwind navbar, live session cart badge, flash messages
│       ├── public/
│       │   ├── index.html        # Home Page (Product Grid)
│       │   ├── product.html      # Product Detail + Pure HTML Facebook/Telegram Share links
│       │   ├── cart.html         # Shopping Cart Page (HTML POST forms for qty/remove)
│       │   ├── checkout.html     # Guest Info Form
│       │   ├── checkout_qr.html  # KHQR Display Page with <meta http-equiv="refresh" content="3">
│       │   └── confirm.html      # Order Confirmation Page
│       └── admin/
│           ├── login.html        # Admin Login Page
│           ├── products.html     # Admin Product List Table
│           ├── product_form.html # Create / Edit Product Form (multipart/form-data -> R2)
│           ├── orders.html       # Admin Order History Table
│           └── order_detail.html # Dedicated Order Details Page (items & shipping address)
├── migrations/                   # Flask-Migrate (Alembic) PostgreSQL schema versions
├── .env                          # Secret keys, Postgres URL, R2 & Bakong credentials (gitignored)
├── .env.example                  # Template for environment variables
├── requirements.txt              # Python dependencies
├── seed.py                       # Script to create default Admin & sample products
└── run.py                        # Application entry point
```

---

## 3. PostgreSQL Database Schema Design (`app/models.py`)

PostgreSQL enforces strict data types, `NUMERIC(10, 2)` decimal precision for currency, and timezone-aware timestamps.

### 3.1 `admins` Table

| Column | PostgreSQL Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` / `INTEGER` | Primary Key | Unique admin ID |
| `username` | `VARCHAR(80)` | Unique, Not Null | Admin login username |
| `password_hash` | `VARCHAR(255)` | Not Null | Hashed password (`werkzeug.security`) |

### 3.2 `products` Table

| Column | PostgreSQL Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` / `INTEGER` | Primary Key | Unique product ID |
| `name` | `VARCHAR(150)` | Not Null | Product title |
| `description` | `TEXT` | Nullable | Detailed product description |
| `price` | `NUMERIC(10, 2)` | Not Null | Exact unit price |
| `stock_quantity` | `INTEGER` | Default `0`, Not Null | Available inventory count |
| `image_url` | `TEXT` | Nullable | Full Cloudflare R2 public URL (`https://pub-xxx.r2.dev/...`) |
| `image_key` | `VARCHAR(255)` | Nullable | R2 object key (`products/uuid-filename.jpg`) for deletion |
| `status` | `VARCHAR(20)` | Default `'active'` | `'active'` or `'inactive'` |
| `created_at` | `TIMESTAMPTZ` | Default `NOW()` | Creation timestamp |

### 3.3 `orders` Table

| Column | PostgreSQL Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` / `INTEGER` | Primary Key | Internal order ID |
| `order_code` | `VARCHAR(30)` | Unique, Not Null | Public reference (e.g., `ORD-20261113-001`) |
| `customer_name` | `VARCHAR(120)` | Not Null | Guest full name |
| `customer_email` | `VARCHAR(120)` | Not Null | Guest email address |
| `customer_phone` | `VARCHAR(30)` | Not Null | Guest phone number |
| `shipping_address` | `TEXT` | Not Null | Delivery address |
| `total_amount` | `NUMERIC(10, 2)` | Not Null | Total order amount |
| `currency` | `VARCHAR(5)` | Default `'USD'` | `'USD'` or `'KHR'` |
| `payment_status` | `VARCHAR(20)` | Default `'UNPAID'` | `'UNPAID'`, `'PAID'`, or `'EXPIRED'` |
| `khqr_md5` | `VARCHAR(32)` | Unique, Indexed | 32-char MD5 checksum used to verify KHQR payment |
| `payer_bank` | `VARCHAR(50)` | Nullable | Bank name returned by Bakong upon payment |
| `created_at` | `TIMESTAMPTZ` | Default `NOW()` | Order placement timestamp |

### 3.4 `order_items` Table

| Column | PostgreSQL Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` / `INTEGER` | Primary Key | Line item ID |
| `order_id` | `INTEGER` | Foreign Key (`orders.id`) | Parent order (`ON DELETE CASCADE`) |
| `product_id` | `INTEGER` | Foreign Key (`products.id`) | Purchased product |
| `quantity` | `INTEGER` | Not Null | Quantity purchased |
| `unit_price` | `NUMERIC(10, 2)` | Not Null | Snapshot of price at checkout |
| `subtotal` | `NUMERIC(10, 2)` | Not Null | `quantity * unit_price` |

---

## 4. Flask Routes & Controller Endpoints

### 4.1 Public Storefront & Session Cart Routes (`app/routes/public.py`)

* `GET /` — Renders the Home Page grid with all `active` products from PostgreSQL (supports `?q=` search query via HTML GET form).
* `GET /products/<int:id>` — Renders the Product Detail page with stock status, quantity `<input type="number">` form, and server-encoded Facebook/Telegram share links.
* `GET /cart` — Renders the Shopping Cart page by querying PostgreSQL for the product IDs stored in `session['cart']`.
* `POST /cart/add/<int:product_id>` — Adds a product (and selected quantity) into `session['cart']`, flashes a Tailwind success alert, and redirects back.
* `POST /cart/update/<int:product_id>` — Updates item quantity in `session['cart']` (or removes if `quantity <= 0`) and redirects to `/cart`.
* `POST /cart/remove/<int:product_id>` — Deletes item from `session['cart']` and redirects to `/cart`.
* `GET /checkout` — Renders the Guest Information form alongside an order summary.
* `POST /checkout` — Validates guest inputs & PostgreSQL stock, saves an `UNPAID` order + `order_items`, generates the KHQR code via `KHQRService`, and redirects to `/checkout/pay/<order_code>`.
* `GET /checkout/pay/<string:order_code>` — Displays the KHQR code image with `<meta http-equiv="refresh" content="3">`. Every 3 seconds, this route checks `KHQRService.verify_payment(order.khqr_md5)`. Once `PAID`, it updates the order in PostgreSQL, deducts stock, clears `session['cart']`, and redirects to `/order-confirmation/<order_code>`.
* `GET /order-confirmation/<string:order_code>` — Displays the Order Confirmation summary (Order ID, customer info, items, and Total Amount).

### 4.2 Admin Management Routes (`app/routes/admin.py` — `@login_required`)

* `GET /admin/login` & `POST /admin/login` — Renders login form and authenticates admin credentials.
* `POST /admin/logout` — Logs out the admin session and redirects to `/admin/login`.
* `GET /admin/products` — Renders the Admin Product List table (ID, Thumbnail, Name, Price, Stock, Status, Edit/Delete actions).
* `GET /admin/products/new` & `POST /admin/products/new` — Renders Create Product form; on POST, uploads image to **Cloudflare R2** and inserts record into PostgreSQL.
* `GET /admin/products/<int:id>/edit` & `POST /admin/products/<int:id>/edit` — Renders Edit Product form; on POST, updates PostgreSQL and replaces the R2 image if a new file was uploaded.
* `POST /admin/products/<int:id>/delete` — Deletes the product from PostgreSQL and removes its image object from Cloudflare R2.
* `GET /admin/orders` — Renders the Admin Order History table sorted by newest first.
* `GET /admin/orders/<int:id>` — Renders the dedicated Order Details page showing purchased items, quantities, subtotals, payment status, and shipping address.

---

## 5. PostgreSQL & Cloudflare R2 Configuration

### 5.1 Install Required Packages

```bash
pip install flask flask-sqlalchemy flask-migrate flask-login python-dotenv psycopg2-binary boto3 bakong-khqr pillow qrcode
```

### 5.2 Environment Configuration (`.env`)

```env
FLASK_SECRET_KEY=super-secret-flask-key-change-me

# PostgreSQL Connection String (Neon / Supabase / Railway / Local)
DATABASE_URL=postgresql://user:password@ep-cool-forest-123456.ap-southeast-1.aws.neon.tech/myshop?sslmode=require

# Cloudflare R2 Object Storage Configuration
R2_ACCOUNT_ID=your_cloudflare_32_char_account_id
R2_ACCESS_KEY_ID=your_r2_access_key_id
R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
R2_BUCKET_NAME=myshop-products
R2_PUBLIC_URL=https://pub-xxxxxxxxxxxxxxxx.r2.dev

# Bakong KHQR Merchant Configuration
BAKONG_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
BAKONG_ACCOUNT_ID=your_account@aclb
MERCHANT_NAME=MyShop Cambodia
MERCHANT_CITY=Phnom Penh
STORE_LABEL=MyShop Online
MERCHANT_PHONE=85512345678
CURRENCY=USD

# Optional: Custom Relay URL if hosting outside Cambodia
KHQR_RELAY_BASE_URL=
```

### 5.3 PostgreSQL & Cart Badge App Factory (`app/__init__.py`)

```python
import os
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "admin.login"

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret")

    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Inject total cart item count into all Jinja2 templates without JS
    @app.context_processor
    def inject_cart_count():
        cart = session.get("cart", {})
        total_items = sum(cart.values()) if isinstance(cart, dict) else 0
        return {"cart_count": total_items}

    return app
```

### 5.4 Cloudflare R2 Setup & Service (`app/services/r2_service.py`)

1. **Cloudflare Dashboard Setup:**
   * Create an R2 Bucket (e.g., `myshop-products`) -> **Settings** -> **Public Access** -> Enable **R2.dev subdomain** (`https://pub-xxx.r2.dev`).
   * Create an **R2 API Token** with **Object Read & Write** permissions scoped to the bucket.
2. **Python R2 Upload Service:**

```python
import os
import uuid
import boto3
from botocore.config import Config
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

class R2Service:
    def __init__(self):
        self.account_id = os.getenv("R2_ACCOUNT_ID")
        self.bucket_name = os.getenv("R2_BUCKET_NAME")
        self.public_url = os.getenv("R2_PUBLIC_URL", "").rstrip("/")

        self.s3_client = boto3.client(
            service_name="s3",
            endpoint_url=f"https://{self.account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )

    @staticmethod
    def is_allowed_file(filename: str) -> bool:
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def upload_product_image(self, file_storage) -> dict:
        if not file_storage or not file_storage.filename:
            raise ValueError("No file provided")
        if not self.is_allowed_file(file_storage.filename):
            raise ValueError("Invalid image format. Allowed: png, jpg, jpeg, webp")

        clean_name = secure_filename(file_storage.filename)
        object_key = f"products/{uuid.uuid4().hex}-{clean_name}"

        self.s3_client.upload_fileobj(
            Fileobj=file_storage,
            Bucket=self.bucket_name,
            Key=object_key,
            ExtraArgs={
                "ContentType": file_storage.content_type or "image/jpeg",
                "CacheControl": "public, max-age=31536000",
            },
        )

        return {
            "image_url": f"{self.public_url}/{object_key}",
            "image_key": object_key,
        }

    def delete_product_image(self, object_key: str) -> None:
        if not object_key:
            return
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
```

---

## 6. Deep Dive: Bakong KHQR Integration (Zero-JS Auto-Polling)

### 6.1 End-to-End Zero-JS KHQR Payment Flow

Instead of JavaScript `fetch()` polling, the KHQR page uses standard HTML `<meta http-equiv="refresh" content="3">`. Every 3 seconds, the browser reloads `/checkout/pay/<order_code>`, allowing Flask to query the Bakong Open API directly on the server:

```text
[Customer Browser]                 [Flask Server]                   [NBC Bakong Open API]
       |                                 |                                  |
       |-- 1. POST /checkout ----------->|                                  |
       |   (Guest Info + Session Cart)   |-- 2. Save UNPAID Order (Postgres)|
       |<-- 3. Redirect /checkout/pay ---|                                  |
       |                                 |                                  |
       |-- 4. GET /checkout/pay/ORD-1 -->|                                  |
       |                                 |-- 5. Generate EMVCo KHQR + MD5   |
       |<-- 6. Render QR + <meta refresh>|                                  |
       |                                 |                                  |
       |   (Customer scans QR with       |                                  |
       |    ABA / ACLEDA / Bakong App) ->|--------------------------------->| (Payment Settled)
       |                                 |                                  |
       |-- 7. Auto-Reload (every 3s) --->|                                  |
       |      GET /checkout/pay/ORD-1    |-- 8. check_payment(md5) -------->|
       |                                 |<-- 9. Status: "PAID" ------------|
       |                                 |-- 10. Postgres Order=PAID,       |
       |                                 |       Deduct Stock, Clear Cart   |
       |<-- 11. Redirect /confirmation --|                                  |
```

### 6.2 Backend KHQR Service (`app/services/khqr_service.py`)

```python
import os
from bakong_khqr import KHQR, KHQRConfig

class KHQRService:
    def __init__(self):
        token = os.getenv("BAKONG_TOKEN")
        relay_url = os.getenv("KHQR_RELAY_BASE_URL")

        if relay_url:
            config = KHQRConfig(token=token, base_url=relay_url)
            self.khqr = KHQR(config=config)
        else:
            self.khqr = KHQR(token)

        self.account_id = os.getenv("BAKONG_ACCOUNT_ID")
        self.merchant_name = os.getenv("MERCHANT_NAME", "MyShop")
        self.merchant_city = os.getenv("MERCHANT_CITY", "Phnom Penh")
        self.store_label = os.getenv("STORE_LABEL", "MyShop")
        self.phone_number = os.getenv("MERCHANT_PHONE", "85512000000")
        self.currency = os.getenv("CURRENCY", "USD")

    def generate_order_qr(self, amount: float, bill_number: str) -> dict:
        qr_string = self.khqr.create_qr(
            bank_account=self.account_id,
            merchant_name=self.merchant_name,
            merchant_city=self.merchant_city,
            amount=round(float(amount), 2),
            currency=self.currency,
            store_label=self.store_label,
            phone_number=self.phone_number,
            bill_number=bill_number,
            terminal_label="WebCheckout",
        )
        return {
            "qr_string": qr_string,
            "md5": self.khqr.generate_md5(qr_string),
            "qr_image": self.khqr.qr_image(qr=qr_string, format="base64_uri"),
        }

    def verify_payment(self, md5_hash: str) -> dict:
        status = self.khqr.check_payment(md5_hash)
        payment_details = self.khqr.get_payment(md5_hash) if status == "PAID" else None
        return {"status": status, "details": payment_details}
```

### 6.3 Flask Payment Route & Zero-JS Template (`checkout_qr.html`)

**Route Handler (`app/routes/public.py`):**

```python
@public_bp.route("/checkout/pay/<string:order_code>")
def checkout_pay(order_code):
    order = Order.query.filter_by(order_code=order_code).first_or_404()

    if order.payment_status == "PAID":
        return redirect(url_for("public.order_confirmation", order_code=order.order_code))

    # Check Bakong Open API on every page load / 3-second meta refresh
    verification = khqr_service.verify_payment(order.khqr_md5)
    if verification["status"] == "PAID":
        # Lock rows in PostgreSQL to safely deduct stock once
        locked_order = Order.query.filter_by(id=order.id).with_for_update().first()
        if locked_order.payment_status != "PAID":
            locked_order.payment_status = "PAID"
            for item in locked_order.items:
                product = Product.query.filter_by(id=item.product_id).with_for_update().first()
                if product:
                    product.stock_quantity = max(0, product.stock_quantity - item.quantity)
            db.session.commit()

        session.pop("cart", None)
        return redirect(url_for("public.order_confirmation", order_code=order.order_code))

    qr_data = khqr_service.generate_order_qr(float(order.total_amount), order.order_code)
    return render_template("public/checkout_qr.html", order=order, qr_image=qr_data["qr_image"])
```

**Template (`app/templates/public/checkout_qr.html`):**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <!-- Auto-refresh every 3 seconds to check KHQR payment status without JavaScript -->
  <meta http-equiv="refresh" content="3">
  <title>Scan KHQR to Pay - {{ order.order_code }}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/output.css') }}">
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center p-4">
  <div class="bg-white max-w-md w-full rounded-2xl shadow-lg p-6 text-center border border-gray-100">
    <span class="inline-block bg-red-100 text-red-700 text-xs font-semibold px-3 py-1 rounded-full mb-3">
      KHQR Payment
    </span>
    <h1 class="text-xl font-bold text-gray-900">Scan to Complete Order</h1>
    <p class="text-sm text-gray-500 mt-1">Order ID: <span class="font-mono font-medium">{{ order.order_code }}</span></p>

    <div class="my-6 p-4 bg-white border-2 border-red-600 rounded-xl inline-block">
      <img src="{{ qr_image }}" alt="Bakong KHQR Code" class="w-64 h-64 mx-auto">
    </div>

    <p class="text-2xl font-extrabold text-gray-900">${{ "%.2f"|format(order.total_amount) }}</p>
    <p class="text-xs text-gray-500 mt-2 animate-pulse">
      Waiting for payment... Page refreshes automatically every 3 seconds.
    </p>

    <div class="mt-6">
      <a href="{{ url_for('public.checkout_pay', order_code=order.order_code) }}"
         class="inline-block w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2.5 px-4 rounded-lg transition">
        I Have Paid — Check Now
      </a>
    </div>
  </div>
</body>
</html>
```

### 6.4 Crucial Deployment Note for Cambodia (Geo-IP Restriction)

* **NBC Firewall Rule:** The official Bakong Open API (`https://api-bakong.nbc.gov.kh`) restricts `check_payment` calls to **Cambodian IP addresses**.
* **Solutions:** Deploy on a Cambodian VPS (e.g., MekongNet, Ezecom) or route `check_payment` through a lightweight Cambodian relay server via `KHQR_RELAY_BASE_URL`.
* **Demo Tip:** Seed a **`$0.01` (or `100 KHR`)** test product so you can scan and pay live with your own Bakong/ABA app during your video walkthrough.

---

## 7. Pure HTML + Tailwind CSS Frontend Patterns (Zero JavaScript)

### 7.1 Compiling Tailwind CSS Without JavaScript

Instead of loading the Play CDN `<script>` tag, compile Tailwind into a static CSS file using the standalone Tailwind CLI:

```bash
./tailwindcss -i ./app/static/css/input.css -o ./app/static/css/output.css --minify
```

Link it in `base.html` using a standard stylesheet tag:

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/output.css') }}">
```

### 7.2 Server-Side Session Cart Forms (`cart.html` & `product.html`)

**Add to Cart Form (Home & Product Detail Pages):**

```html
<form action="{{ url_for('public.add_to_cart', product_id=product.id) }}" method="POST" class="flex items-center gap-2">
  <input type="number" name="quantity" value="1" min="1" max="{{ product.stock_quantity }}"
         class="w-20 border border-gray-300 rounded-lg px-3 py-2 text-center">
  <button type="submit"
          class="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4 py-2 rounded-lg transition">
    Add to Cart
  </button>
</form>
```

**Update Quantity & Remove Item Forms (`cart.html`):**

```html
<form action="{{ url_for('public.update_cart', product_id=item.product.id) }}" method="POST" class="inline-flex items-center gap-2">
  <input type="number" name="quantity" value="{{ item.quantity }}" min="1" max="{{ item.product.stock_quantity }}"
         class="w-16 border border-gray-300 rounded px-2 py-1 text-center">
  <button type="submit" class="text-xs bg-gray-200 hover:bg-gray-300 text-gray-800 px-2.5 py-1.5 rounded">
    Update
  </button>
</form>

<form action="{{ url_for('public.remove_from_cart', product_id=item.product.id) }}" method="POST" class="inline">
  <button type="submit" class="text-xs bg-red-100 hover:bg-red-200 text-red-700 px-2.5 py-1.5 rounded">
    Remove
  </button>
</form>
```

### 7.3 Pure HTML Social Share Buttons (`product.html`)

Jinja2's built-in `| urlencode` filter encodes `request.url` directly on the server so standard `<a>` links open Facebook and Telegram share dialogs with zero JavaScript:

```html
<div class="flex items-center gap-3 mt-6">
  <a href="https://www.facebook.com/sharer/sharer.php?u={{ request.url | urlencode }}"
     target="_blank" rel="noopener noreferrer"
     class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition">
    Share on Facebook
  </a>

  <a href="https://t.me/share/url?url={{ request.url | urlencode }}&text={{ ('Check out ' + product.name + ' on ....Shop!') | urlencode }}"
     target="_blank" rel="noopener noreferrer"
     class="bg-sky-500 hover:bg-sky-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition">
    Share on Telegram
  </a>
</div>
```

---

## 8. Step-by-Step Build & Submission Roadmap

1. **Phase 1: Cloud Infrastructure & Backend Foundation**
   * Provision a free **PostgreSQL** database (Neon or Supabase) and create a **Cloudflare R2** bucket with Public Access enabled.
   * Initialize Flask + SQLAlchemy + Flask-Migrate (`flask db init && flask db migrate && flask db upgrade`) and run `seed.py` to create the Admin user and sample products.
   * Build `app/static/css/output.css` using the Tailwind CLI.
2. **Phase 2: Admin Dashboard (Zero-JS CRUD + R2)**
   * Build Admin Login, Product List table (with POST Delete forms), Create/Edit Product forms (`enctype="multipart/form-data"` wired to `R2Service`), and Order History + Order Details pages.
3. **Phase 3: Customer Storefront & Session Cart**
   * Build the Tailwind product grid on the Home Page, Product Detail page with quantity form & pure HTML Facebook/Telegram share links, and server-side session Cart page.
4. **Phase 4: Checkout & Auto-Refreshing KHQR Payment**
   * Implement `/checkout` and `/checkout/pay/<order_code>` with `<meta http-equiv="refresh" content="3">`. Test scanning live with Bakong/ABA and verify automatic stock deduction in PostgreSQL.
5. **Phase 5: Final Deliverables Checklist**
   * [ ] **Live Demo URL** deployed and accessible (connected to PostgreSQL & Cloudflare R2).
   * [ ] **Admin URL** + `username` and `password` documented in `README.md`.
   * [ ] **Public GitHub Repository** pushed (confirm `.env` is listed in `.gitignore`).
   * [ ] **Walkthrough Video Demo** demonstrating product browsing, social sharing, cart management, live KHQR payment auto-confirmation, and Admin product/order management.
   * [ ] **Telegram Topic Submission** formatted with team member names and assigned features.