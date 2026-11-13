from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import Admin, Product, Order
from app.services.r2_service import R2Service

admin_bp = Blueprint("admin", __name__)
r2_service = R2Service()


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.products"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            login_user(admin)
            flash(f"Welcome back, {admin.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("admin.products"))
        else:
            flash("Invalid username or password.", "error")

    return render_template("admin/login.html")


@admin_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("admin.login"))


@admin_bp.route("/products")
@login_required
def products():
    search = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = Product.query
    if search:
        query = query.filter(
            (Product.name.ilike(f"%{search}%"))
            | (Product.description.ilike(f"%{search}%"))
        )
    if status_filter in ("active", "inactive"):
        query = query.filter_by(status=status_filter)

    product_list = query.order_by(Product.id.desc()).all()
    return render_template(
        "admin/products.html",
        products=product_list,
        search=search,
        status_filter=status_filter,
    )


@admin_bp.route("/products/new", methods=["GET", "POST"])
@login_required
def product_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price_str = request.form.get("price", "0").strip()
        stock_str = request.form.get("stock_quantity", "0").strip()
        status = request.form.get("status", "active").strip()
        image_file = request.files.get("image")

        if not name:
            flash("Product name is required.", "error")
            return render_template("admin/product_form.html", product=None)

        try:
            price = round(float(price_str), 2)
            if price < 0:
                raise ValueError()
        except ValueError:
            flash("Please enter a valid positive price.", "error")
            return render_template("admin/product_form.html", product=None)

        try:
            stock = int(stock_str)
            if stock < 0:
                raise ValueError()
        except ValueError:
            flash("Please enter a valid non-negative stock quantity.", "error")
            return render_template("admin/product_form.html", product=None)

        image_url = None
        image_key = None

        if image_file and image_file.filename:
            try:
                upload_res = r2_service.upload_product_image(image_file)
                image_url = upload_res["image_url"]
                image_key = upload_res["image_key"]
            except Exception as e:
                flash(f"Failed to upload image: {str(e)}", "error")
                return render_template("admin/product_form.html", product=None)

        product = Product(
            name=name,
            description=description,
            price=price,
            stock_quantity=stock,
            status=status if status in ("active", "inactive") else "active",
            image_url=image_url,
            image_key=image_key,
        )
        db.session.add(product)
        db.session.commit()

        flash(f'Product "{product.name}" created successfully!', "success")
        return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", product=None)


@admin_bp.route("/products/<int:id>/edit", methods=["GET", "POST"])
@login_required
def product_edit(id):
    product = db.get_or_404(Product, id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price_str = request.form.get("price", "0").strip()
        stock_str = request.form.get("stock_quantity", "0").strip()
        status = request.form.get("status", "active").strip()
        image_file = request.files.get("image")

        if not name:
            flash("Product name is required.", "error")
            return render_template("admin/product_form.html", product=product)

        try:
            price = round(float(price_str), 2)
            if price < 0:
                raise ValueError()
        except ValueError:
            flash("Please enter a valid positive price.", "error")
            return render_template("admin/product_form.html", product=product)

        try:
            stock = int(stock_str)
            if stock < 0:
                raise ValueError()
        except ValueError:
            flash("Please enter a valid non-negative stock quantity.", "error")
            return render_template("admin/product_form.html", product=product)

        if image_file and image_file.filename:
            try:
                # Delete old image if exists
                if product.image_key:
                    r2_service.delete_product_image(product.image_key)

                upload_res = r2_service.upload_product_image(image_file)
                product.image_url = upload_res["image_url"]
                product.image_key = upload_res["image_key"]
            except Exception as e:
                flash(f"Failed to upload new image: {str(e)}", "error")
                return render_template("admin/product_form.html", product=product)

        product.name = name
        product.description = description
        product.price = price
        product.stock_quantity = stock
        product.status = status if status in ("active", "inactive") else "active"

        db.session.commit()
        flash(f'Product "{product.name}" updated successfully!', "success")
        return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", product=product)


@admin_bp.route("/products/<int:id>/delete", methods=["POST"])
@login_required
def product_delete(id):
    product = db.get_or_404(Product, id)
    name = product.name

    if product.image_key:
        try:
            r2_service.delete_product_image(product.image_key)
        except Exception:
            pass

    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{name}" deleted successfully.', "info")
    return redirect(url_for("admin.products"))


@admin_bp.route("/orders")
@login_required
def orders():
    status_filter = request.args.get("status", "").strip().upper()
    query = Order.query

    if status_filter in ("UNPAID", "PAID", "EXPIRED"):
        query = query.filter_by(payment_status=status_filter)

    order_list = query.order_by(Order.id.desc()).all()
    return render_template("admin/orders.html", orders=order_list, status_filter=status_filter)


@admin_bp.route("/orders/<int:id>")
@login_required
def order_detail(id):
    order = db.get_or_404(Order, id)
    return render_template("admin/order_detail.html", order=order)
