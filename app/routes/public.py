import uuid
from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app,
)
from app import db
from app.models import Product, Order, OrderItem
from app.services.khqr_service import KHQRService

public_bp = Blueprint("public", __name__)
khqr_service = KHQRService()


@public_bp.route("/")
def index():
    search_query = request.args.get("q", "").strip()
    query = Product.query.filter_by(status="active")

    if search_query:
        query = query.filter(
            (Product.name.ilike(f"%{search_query}%"))
            | (Product.description.ilike(f"%{search_query}%"))
        )

    products = query.order_by(Product.id.desc()).all()
    return render_template("public/index.html", products=products, search_query=search_query)


@public_bp.route("/products/<int:id>")
def product_detail(id):
    product = db.get_or_404(Product, id)
    return render_template("public/product.html", product=product)


@public_bp.route("/cart")
def cart():
    raw_cart = session.get("cart", {})
    cart_items = []
    total_amount = 0.0

    if isinstance(raw_cart, dict) and raw_cart:
        product_ids = [int(pid) for pid in raw_cart.keys() if pid.isdigit()]
        products = {p.id: p for p in Product.query.filter(Product.id.in_(product_ids)).all()}

        for pid_str, qty in raw_cart.items():
            if not pid_str.isdigit():
                continue
            pid = int(pid_str)
            product = products.get(pid)
            if product:
                subtotal = float(product.price) * qty
                total_amount += subtotal
                cart_items.append({
                    "product": product,
                    "quantity": qty,
                    "subtotal": subtotal,
                })

    return render_template(
        "public/cart.html",
        cart_items=cart_items,
        total_amount=total_amount,
    )


@public_bp.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = db.get_or_404(Product, product_id)

    try:
        quantity = int(request.form.get("quantity", 1))
    except (ValueError, TypeError):
        quantity = 1

    if quantity < 1:
        quantity = 1

    if not product.is_in_stock:
        flash(f'Sorry, "{product.name}" is currently out of stock.', "error")
        return redirect(request.referrer or url_for("public.product_detail", id=product_id))

    if quantity > product.stock_quantity:
        quantity = product.stock_quantity
        flash(f'Adjusted quantity to available stock ({product.stock_quantity}) for "{product.name}".', "warning")

    cart = session.get("cart", {})
    if not isinstance(cart, dict):
        cart = {}

    pid_str = str(product_id)
    current_qty = cart.get(pid_str, 0)
    new_qty = current_qty + quantity

    if new_qty > product.stock_quantity:
        new_qty = product.stock_quantity
        flash(f'Cart updated to maximum available stock ({product.stock_quantity}) for "{product.name}".', "warning")
    else:
        flash(f'Added {quantity}x "{product.name}" to your cart.', "success")

    cart[pid_str] = new_qty
    session["cart"] = cart
    session.modified = True

    return redirect(request.referrer or url_for("public.cart"))


@public_bp.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    product = db.get_or_404(Product, product_id)

    try:
        quantity = int(request.form.get("quantity", 1))
    except (ValueError, TypeError):
        quantity = 1

    cart = session.get("cart", {})
    if not isinstance(cart, dict):
        cart = {}

    pid_str = str(product_id)

    if quantity <= 0:
        cart.pop(pid_str, None)
        flash(f'Removed "{product.name}" from your cart.', "info")
    else:
        if quantity > product.stock_quantity:
            quantity = product.stock_quantity
            flash(f'Quantity adjusted to available stock ({product.stock_quantity}).', "warning")
        else:
            flash(f'Updated "{product.name}" quantity to {quantity}.', "success")
        cart[pid_str] = quantity

    session["cart"] = cart
    session.modified = True
    return redirect(url_for("public.cart"))


@public_bp.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    product = db.session.get(Product, product_id)
    cart = session.get("cart", {})
    if isinstance(cart, dict):
        cart.pop(str(product_id), None)
        session["cart"] = cart
        session.modified = True

    item_name = product.name if product else "Item"
    flash(f'Removed "{item_name}" from cart.', "info")
    return redirect(url_for("public.cart"))


@public_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    raw_cart = session.get("cart", {})
    if not raw_cart or not isinstance(raw_cart, dict):
        flash("Your cart is empty. Add products before checking out.", "warning")
        return redirect(url_for("public.index"))

    product_ids = [int(pid) for pid in raw_cart.keys() if pid.isdigit()]
    products = {p.id: p for p in Product.query.filter(Product.id.in_(product_ids)).all()}

    cart_items = []
    total_amount = 0.0

    for pid_str, qty in raw_cart.items():
        if not pid_str.isdigit():
            continue
        pid = int(pid_str)
        product = products.get(pid)
        if product and product.status == "active":
            subtotal = float(product.price) * qty
            total_amount += subtotal
            cart_items.append({
                "product": product,
                "quantity": qty,
                "subtotal": subtotal,
            })

    if not cart_items:
        flash("Your cart has no valid active items. Please browse our catalog.", "warning")
        return redirect(url_for("public.index"))

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        customer_email = request.form.get("customer_email", "").strip()
        customer_phone = request.form.get("customer_phone", "").strip()
        shipping_address = request.form.get("shipping_address", "").strip()

        if not all([customer_name, customer_email, customer_phone, shipping_address]):
            flash("Please fill in all required customer and delivery fields.", "error")
            return render_template(
                "public/checkout.html",
                cart_items=cart_items,
                total_amount=total_amount,
            )

        # Check stock availability
        for item in cart_items:
            prod = item["product"]
            req_qty = item["quantity"]
            if req_qty > prod.stock_quantity:
                flash(f'Insufficient stock for "{prod.name}". Only {prod.stock_quantity} left.', "error")
                return render_template(
                    "public/checkout.html",
                    cart_items=cart_items,
                    total_amount=total_amount,
                )

        # Generate unique order code
        date_str = datetime.now().strftime("%Y%m%d")
        unique_suffix = uuid.uuid4().hex[:6].upper()
        order_code = f"ORD-{date_str}-{unique_suffix}"

        currency = current_app.config.get("CURRENCY", "USD")

        # Create Order record
        order = Order(
            order_code=order_code,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            shipping_address=shipping_address,
            total_amount=round(total_amount, 2),
            currency=currency,
            payment_status="UNPAID",
        )
        db.session.add(order)
        db.session.flush()

        # Create OrderItem records
        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item["product"].id,
                quantity=item["quantity"],
                unit_price=item["product"].price,
                subtotal=round(item["subtotal"], 2),
            )
            db.session.add(order_item)

        # Generate KHQR code & MD5 hash
        qr_data = khqr_service.generate_order_qr(float(order.total_amount), order.order_code)
        order.khqr_md5 = qr_data["md5"]

        db.session.commit()

        return redirect(url_for("public.checkout_pay", order_code=order.order_code))

    return render_template(
        "public/checkout.html",
        cart_items=cart_items,
        total_amount=total_amount,
    )


@public_bp.route("/checkout/pay/<string:order_code>")
def checkout_pay(order_code):
    order = Order.query.filter_by(order_code=order_code).first_or_404()

    if order.payment_status == "PAID":
        return redirect(url_for("public.order_confirmation", order_code=order.order_code))

    # Check Bakong Open API on every page load / 3-second meta refresh
    verification = khqr_service.verify_payment(order.khqr_md5)
    if verification.get("status") == "PAID":
        _complete_order_payment(order, verification.get("details"))
        return redirect(url_for("public.order_confirmation", order_code=order.order_code))

    qr_data = khqr_service.generate_order_qr(float(order.total_amount), order.order_code)
    return render_template(
        "public/checkout_qr.html",
        order=order,
        qr_image=qr_data["qr_image"],
    )


@public_bp.route("/checkout/pay/<string:order_code>/simulate-test-pay", methods=["POST"])
def simulate_test_pay(order_code):
    """
    Demo/Testing simulator endpoint:
    Allows reviewer/tester to simulate a confirmed KHQR payment in demo mode.
    """
    order = Order.query.filter_by(order_code=order_code).first_or_404()
    if order.payment_status != "PAID":
        _complete_order_payment(order, {"bank": "Demo Bakong Bank"})
        flash("Simulated KHQR payment confirmed successfully!", "success")

    return redirect(url_for("public.order_confirmation", order_code=order.order_code))


def _complete_order_payment(order: Order, payment_details: dict | None = None):
    """
    Helper function to safely mark order PAID, deduct product stock,
    and clear the shopping cart.
    """
    try:
        # Re-fetch with row lock if possible
        locked_order = Order.query.filter_by(id=order.id).first()
        if locked_order and locked_order.payment_status != "PAID":
            locked_order.payment_status = "PAID"
            if payment_details and isinstance(payment_details, dict):
                payer_bank = (
                    payment_details.get("bank")
                    or payment_details.get("payerBank")
                    or payment_details.get("sourceBankName")
                    or "Bakong Payment"
                )
                locked_order.payer_bank = str(payer_bank)[:50]

            for item in locked_order.items:
                product = db.session.get(Product, item.product_id)
                if product:
                    product.stock_quantity = max(0, product.stock_quantity - item.quantity)

            db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error completing order payment: {e}")

    session.pop("cart", None)
    session.modified = True


@public_bp.route("/order-confirmation/<string:order_code>")
def order_confirmation(order_code):
    order = Order.query.filter_by(order_code=order_code).first_or_404()
    return render_template("public/confirm.html", order=order)
