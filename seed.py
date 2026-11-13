import os
from app import create_app, db
from app.models import Admin, Product

app = create_app()

SAMPLE_PRODUCTS = [
    {
        "name": "Live KHQR Test Product ($0.01)",
        "description": "Special micro-transaction test product designed for live video walkthroughs. Allows scanning and paying 1 cent live using ABA, ACLEDA, or any Bakong member app without spending real money.",
        "price": 0.01,
        "stock_quantity": 999,
        "image_url": "https://images.unsplash.com/photo-1556742049-0a67c5574f73?w=600&auto=format&fit=crop&q=80",
        "status": "active",
    },
    {
        "name": "Wireless Noise-Cancelling Headphones Pro",
        "description": "High-fidelity wireless over-ear headphones featuring Hybrid Active Noise Cancellation, 40mm titanium diaphragm drivers, and 45-hour extended battery life with fast USB-C charging.",
        "price": 89.99,
        "stock_quantity": 25,
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80",
        "status": "active",
    },
    {
        "name": "Mechanical Gaming Keyboard RGB (Tactile Brown)",
        "description": "Compact 75% mechanical layout with hot-swappable tactile switches, double-shot PBT keycaps, per-key RGB backlighting, and aluminum CNC chassis.",
        "price": 64.50,
        "stock_quantity": 18,
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80",
        "status": "active",
    },
    {
        "name": "Ergonomic Precision Wireless Mouse",
        "description": "Dual-mode Bluetooth & 2.4GHz ultra-quiet ergonomic mouse with hyper-fast scroll wheel, optical sensor up to 4000 DPI, and rechargeable 90-day battery.",
        "price": 29.00,
        "stock_quantity": 30,
        "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=600&auto=format&fit=crop&q=80",
        "status": "active",
    },
    {
        "name": "Water-Resistant Urban Travel Backpack 25L",
        "description": "Minimalist modern backpack built with ballistic 900D waterproof nylon, padded 16-inch laptop compartment, luggage pass-through strap, and hidden anti-theft pocket.",
        "price": 45.00,
        "stock_quantity": 14,
        "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80",
        "status": "active",
    },
    {
        "name": "Smart Fitness & Health Tracker Band",
        "description": "AMOLED touch display tracker with 24/7 heart-rate monitoring, SpO2 blood oxygen sensor, 5ATM water resistance, sleep stage tracking, and 14-day battery life.",
        "price": 38.50,
        "stock_quantity": 40,
        "image_url": "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?w=600&auto=format&fit=crop&q=80",
        "status": "active",
    },
    {
        "name": "Double-Wall Insulated Steel Tumbler 750ml",
        "description": "Vacuum-insulated food-grade 18/8 stainless steel bottle keeping beverages cold for 24 hours or hot for 12 hours. Sweat-free powder coat exterior with leakproof spout lid.",
        "price": 18.00,
        "stock_quantity": 50,
        "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&auto=format&fit=crop&q=80",
        "status": "active",
    },
    {
        "name": "Fast 65W GaN USB-C Dual Port Charger",
        "description": "Next-generation Gallium Nitride (GaN) wall adapter delivering high-efficiency fast charging for MacBooks, iPads, iPhones, and Android devices in a pocket-sized form factor.",
        "price": 24.99,
        "stock_quantity": 35,
        "image_url": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80",
        "status": "active",
    },
]


def seed_database():
    with app.app_context():
        # Create all tables if they don't exist
        db.create_all()

        # Seed default Admin
        admin = Admin.query.filter_by(username="admin").first()
        if not admin:
            admin = Admin(username="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            print(" [Admin] Created default admin account (admin / admin123)")
        else:
            print(" [Admin] Default admin account already exists.")

        # Seed sample products
        added_count = 0
        for p_data in SAMPLE_PRODUCTS:
            existing = Product.query.filter_by(name=p_data["name"]).first()
            if not existing:
                product = Product(
                    name=p_data["name"],
                    description=p_data["description"],
                    price=p_data["price"],
                    stock_quantity=p_data["stock_quantity"],
                    image_url=p_data["image_url"],
                    status=p_data["status"],
                )
                db.session.add(product)
                added_count += 1

        db.session.commit()
        print(f" [Products] Seeded {added_count} new products into database.")
        print(" Database seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
