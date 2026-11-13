import unittest
from app import create_app, db
from app.models import Admin, Product, Order, OrderItem
from app.services.khqr_service import KHQRService
from app.services.r2_service import R2Service


class ShopTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "DEMO_MODE": True,
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed test admin
        self.admin = Admin(username="admin")
        self.admin.set_password("admin123")
        db.session.add(self.admin)

        # Seed test products
        self.product1 = Product(
            name="Test Headphones",
            description="High quality noise cancelling headphones",
            price=50.00,
            stock_quantity=10,
            status="active",
        )
        self.product2 = Product(
            name="Live KHQR Test Item",
            description="0.01 dollar test item",
            price=0.01,
            stock_quantity=100,
            status="active",
        )
        db.session.add_all([self.product1, self.product2])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_public_storefront(self):
        """Test home page rendering and search filtering."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Test Headphones", res.data)
        self.assertIn(b"Live KHQR Test Item", res.data)
        self.assertIn(b"MyShop", res.data)

        # Search query
        res_search = self.client.get("/?q=Headphones")
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b"Test Headphones", res_search.data)

    def test_product_detail_and_share_links(self):
        """Test product detail page and pure HTML social share links."""
        res = self.client.get(f"/products/{self.product1.id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Test Headphones", res.data)
        self.assertIn(b"facebook.com/sharer", res.data)
        self.assertIn(b"t.me/share/url", res.data)

    def test_cart_workflow(self):
        """Test Add to Cart, Update Quantity, and Remove Item via pure POST forms."""
        # 1. Add to cart
        res_add = self.client.post(
            f"/cart/add/{self.product1.id}",
            data={"quantity": "2"},
            follow_redirects=True,
        )
        self.assertEqual(res_add.status_code, 200)
        self.assertIn(b"Test Headphones", res_add.data)
        self.assertIn(b"$100.00", res_add.data)

        # 2. Update quantity
        res_update = self.client.post(
            f"/cart/update/{self.product1.id}",
            data={"quantity": "3"},
            follow_redirects=True,
        )
        self.assertEqual(res_update.status_code, 200)
        self.assertIn(b"$150.00", res_update.data)

        # 3. Remove item
        res_remove = self.client.post(
            f"/cart/remove/{self.product1.id}",
            follow_redirects=True,
        )
        self.assertEqual(res_remove.status_code, 200)
        self.assertIn(b"Your cart is empty", res_remove.data)

    def test_checkout_and_khqr_generation(self):
        """Test full checkout flow, order creation, KHQR QR display with 3s refresh."""
        # Add product to cart
        self.client.post(f"/cart/add/{self.product2.id}", data={"quantity": "1"})

        # Submit guest checkout form
        res_checkout = self.client.post(
            "/checkout",
            data={
                "customer_name": "Sokha Tester",
                "customer_email": "sokha@test.com",
                "customer_phone": "012345678",
                "shipping_address": "Street 2004, Phnom Penh",
            },
            follow_redirects=False,
        )
        self.assertEqual(res_checkout.status_code, 302)
        redirect_url = res_checkout.headers["Location"]
        self.assertIn("/checkout/pay/", redirect_url)

        # Follow to KHQR payment page
        res_pay = self.client.get(redirect_url)
        self.assertEqual(res_pay.status_code, 200)
        self.assertIn(b'http-equiv="refresh" content="3"', res_pay.data)
        self.assertIn(b"data:image/png;base64,", res_pay.data)
        self.assertIn(b"KHQR Payment", res_pay.data)

        # Verify Order was created in DB
        order = Order.query.first()
        self.assertIsNotNone(order)
        self.assertEqual(order.customer_name, "Sokha Tester")
        self.assertEqual(order.payment_status, "UNPAID")
        self.assertIsNotNone(order.khqr_md5)

    def test_payment_confirmation_and_stock_deduction(self):
        """Test simulated KHQR payment, stock reduction, and order confirmation."""
        initial_stock = self.product1.stock_quantity
        self.client.post(f"/cart/add/{self.product1.id}", data={"quantity": "2"})

        self.client.post(
            "/checkout",
            data={
                "customer_name": "Dara Customer",
                "customer_email": "dara@test.com",
                "customer_phone": "098765432",
                "shipping_address": "Toul Kork, Phnom Penh",
            },
        )
        order = Order.query.first()

        # Simulate confirmed payment
        res_pay_sim = self.client.post(
            f"/checkout/pay/{order.order_code}/simulate-test-pay",
            follow_redirects=True,
        )
        self.assertEqual(res_pay_sim.status_code, 200)
        self.assertIn(b"Thank You for Your Order!", res_pay_sim.data)
        self.assertIn(b"Payment Settled Successfully", res_pay_sim.data)

        # Check order status in DB
        db.session.refresh(order)
        self.assertEqual(order.payment_status, "PAID")

        # Check stock deduction
        db.session.refresh(self.product1)
        self.assertEqual(self.product1.stock_quantity, initial_stock - 2)

    def test_admin_authentication_and_crud(self):
        """Test admin login, product CRUD, and order history view."""
        # 1. Unauthenticated access redirect
        res_unauth = self.client.get("/admin/products")
        self.assertEqual(res_unauth.status_code, 302)

        # 2. Login
        res_login = self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=True,
        )
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b"Product Catalog Management", res_login.data)

        # 3. Create new product
        res_new_prod = self.client.post(
            "/admin/products/new",
            data={
                "name": "Admin Created Product",
                "description": "Created during automated test",
                "price": "19.99",
                "stock_quantity": "50",
                "status": "active",
            },
            follow_redirects=True,
        )
        self.assertEqual(res_new_prod.status_code, 200)
        self.assertIn(b"Admin Created Product", res_new_prod.data)

        new_prod = Product.query.filter_by(name="Admin Created Product").first()
        self.assertIsNotNone(new_prod)

        # 4. Edit product
        res_edit = self.client.post(
            f"/admin/products/{new_prod.id}/edit",
            data={
                "name": "Admin Edited Product",
                "description": "Updated description",
                "price": "29.99",
                "stock_quantity": "40",
                "status": "active",
            },
            follow_redirects=True,
        )
        self.assertEqual(res_edit.status_code, 200)
        self.assertIn(b"Admin Edited Product", res_edit.data)

        # 5. Delete product
        res_del = self.client.post(
            f"/admin/products/{new_prod.id}/delete",
            follow_redirects=True,
        )
        self.assertEqual(res_del.status_code, 200)
        self.assertIsNone(Product.query.filter_by(name="Admin Edited Product").first())

        # 6. Orders list
        res_orders = self.client.get("/admin/orders")
        self.assertEqual(res_orders.status_code, 200)
        self.assertIn(b"Order Management", res_orders.data)


if __name__ == "__main__":
    unittest.main()
