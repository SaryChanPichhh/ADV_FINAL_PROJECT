import os
from app import create_app, db
from app.models import Admin, Product

app = create_app()

ZANDO_PRODUCTS = [
    {
        "name": "Live KHQR Micro-Test Item ($0.01)",
        "description": "Special micro-transaction test item for live NBC Bakong KHQR testing. Scan and pay 1 cent live using ABA, ACLEDA, Sathapana, Wing, or any Bakong member app without real expense.",
        "price": 0.01,
        "stock_quantity": 999,
        "image_key": "products/zando-live-khqr-micro-test.jpg",
        "image_url": "/media/products/zando-live-khqr-micro-test.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Vintage Washed Denim Jacket",
        "description": "Classic vintage wash denim jacket cut from 13.5oz premium non-stretch ring-spun cotton. Features custom antique brass buttons, buttoned flap chest pockets, and side welt pockets.",
        "price": 58.00,
        "stock_quantity": 30,
        "image_key": "products/zando-vintage-denim-jacket.jpg",
        "image_url": "/media/products/zando-vintage-denim-jacket.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Heavyweight Streetwear Hoodie",
        "description": "Ultra-heavyweight 480 GSM French Terry cotton hoodie with relaxed dropped-shoulder silhouette, double-layered hood, seamless kangaroo pocket, and minimal embroidered ZANDO chest branding.",
        "price": 39.50,
        "stock_quantity": 45,
        "image_key": "products/heritage-heavyweight-hoodie.jpg",
        "image_url": "/media/products/heritage-heavyweight-hoodie.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Oversized Graphic Drop-Shoulder Tee",
        "description": "Heavyweight 260 GSM combed cotton t-shirt with ribbed crewneck collar, relaxed boxy cut, and contemporary streetwear typography screenprint.",
        "price": 22.00,
        "stock_quantity": 75,
        "image_key": "products/zando-oversized-graphic-tee.jpg",
        "image_url": "/media/products/zando-oversized-graphic-tee.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Urban Streetwear Pullover Hoodie",
        "description": "Premium brushed-fleece cotton blend hoodie with ribbed cuffs, tonal drawstring, and subtle high-density silicone chest emblem.",
        "price": 42.00,
        "stock_quantity": 35,
        "image_key": "products/zando-urban-streetwear-hoodie.jpg",
        "image_url": "/media/products/zando-urban-streetwear-hoodie.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Relaxed Multi-Pocket Cargo Trousers",
        "description": "Modern tactical cargo trousers crafted from durable stretch cotton ripstop with articulated knee darts, adjustable drawstring cuffs, and deep modular utility flap pockets.",
        "price": 42.00,
        "stock_quantity": 40,
        "image_key": "products/zando-relaxed-cargo-pants.jpg",
        "image_url": "/media/products/zando-relaxed-cargo-pants.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Breathable Linen Resort Shirt",
        "description": "Effortlessly breezy camp-collar button-up tailored from 100% natural European linen. Designed for Phnom Penh tropical evenings, beach days, and weekend cafe getaways.",
        "price": 28.50,
        "stock_quantity": 50,
        "image_key": "products/zando-linen-summer-shirt.jpg",
        "image_url": "/media/products/zando-linen-summer-shirt.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Retro Court Minimalist Sneakers",
        "description": "Clean low-top heritage sneakers crafted from full-grain calfskin leather with padded OrthoLite insoles, reinforced eyelets, and stitched natural gum rubber outsoles.",
        "price": 65.00,
        "stock_quantity": 28,
        "image_key": "products/zando-retro-court-sneakers.jpg",
        "image_url": "/media/products/zando-retro-court-sneakers.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Apex Runner Nitro Performance Shoes",
        "description": "High-performance urban running sneakers featuring nitrogen-infused supercritical foam midsoles, breathable engineered mesh uppers, and reflective night-run accents.",
        "price": 78.00,
        "stock_quantity": 32,
        "image_key": "products/apex-runner-nitro-sneakers.jpg",
        "image_url": "/media/products/apex-runner-nitro-sneakers.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Chelsea Suede Leather Ankle Boots",
        "description": "Timeless handcrafted suede leather Chelsea boots with flexible elastic side gussets, dual pull tabs, and durable stacked leather welt soles.",
        "price": 85.00,
        "stock_quantity": 20,
        "image_key": "products/zando-chelsea-suede-boots.jpg",
        "image_url": "/media/products/zando-chelsea-suede-boots.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Italian Leather Crossbody Sling Bag",
        "description": "Sleek compact crossbody bag crafted from smooth pebbled genuine leather with water-repellent nylon lining, internal organizer, and magnetic quick-release metal buckle.",
        "price": 49.00,
        "stock_quantity": 35,
        "image_key": "products/zando-leather-crossbody-bag.jpg",
        "image_url": "/media/products/zando-leather-crossbody-bag.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Heavyweight Canvas Daily Tote Bag",
        "description": "Eco-friendly 16oz organic cotton canvas tote featuring reinforced cross-stitched handles, internal zip pocket for phone/keys, and screen-printed ZANDO typography.",
        "price": 18.00,
        "stock_quantity": 80,
        "image_key": "products/zando-minimalist-canvas-tote.jpg",
        "image_url": "/media/products/zando-minimalist-canvas-tote.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Polarized Matte Black Aviator Sunglasses",
        "description": "Ultralight titanium frame aviator sunglasses with UV400 anti-glare polarized lenses, adjustable silicone nose pads, and protective magnetic leather case.",
        "price": 32.00,
        "stock_quantity": 60,
        "image_key": "products/zando-aviator-black-sunglasses.jpg",
        "image_url": "/media/products/zando-aviator-black-sunglasses.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Chunky Ribbed Knit Cardigan",
        "description": "Cozy oversized cardigan knit from premium wool-blend yarn with tortoiseshell buttons, ribbed shawl collar, and deep front patch pockets.",
        "price": 54.00,
        "stock_quantity": 25,
        "image_key": "products/zando-chunky-knit-cardigan.jpg",
        "image_url": "/media/products/zando-chunky-knit-cardigan.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Nomad Weatherproof Tech Trench",
        "description": "DWR water-resistant 3-layer laminated shell jacket engineered for unpredictable tropical downpours with taped seams, storm flap, and waterproof YKK AquaGuard zippers.",
        "price": 95.00,
        "stock_quantity": 18,
        "image_key": "products/nomad-weatherproof-jacket.jpg",
        "image_url": "/media/products/nomad-weatherproof-jacket.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Chrono-Titanium Minimalist Timepiece",
        "description": "Modern 40mm brushed aerospace titanium case with scratch-resistant sapphire crystal, Japanese quartz chronograph movement, and quick-release Milanese mesh band.",
        "price": 120.00,
        "stock_quantity": 15,
        "image_key": "products/chrono-titanium-watch.jpg",
        "image_url": "/media/products/chrono-titanium-watch.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO Trailblaze Commuter Backpack 28L",
        "description": "Ergonomic modern commute pack with 900D waterproof ballistic nylon, dedicated 16-inch fleece laptop sleeve, hidden RFID passport pocket, and luggage pass-through strap.",
        "price": 62.00,
        "stock_quantity": 30,
        "image_key": "products/trailblaze-tech-backpack.jpg",
        "image_url": "/media/products/trailblaze-tech-backpack.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO StudioPulse Wireless ANC Headphones",
        "description": "Over-ear active noise cancelling headphones with custom 40mm beryllium drivers, memory foam earcups, transparency audio mode, and 50h battery life.",
        "price": 89.00,
        "stock_quantity": 22,
        "image_key": "products/studiopulse-anc-headset.jpg",
        "image_url": "/media/products/studiopulse-anc-headset.jpg",
        "status": "active",
    },
    {
        "name": "ZANDO AeroSound Pro Spatial Earbuds",
        "description": "True wireless earbuds with spatial audio head-tracking, IPX7 sweatproof rating, quad beamforming ENC microphones for crystal-clear phone calls, and wireless charging case.",
        "price": 45.00,
        "stock_quantity": 40,
        "image_key": "products/aerosound-pro-anc-earbuds.jpg",
        "image_url": "/media/products/aerosound-pro-anc-earbuds.jpg",
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

        # Seed products
        added_count = 0
        updated_count = 0
        for p_data in ZANDO_PRODUCTS:
            existing = Product.query.filter_by(name=p_data["name"]).first()
            if not existing:
                product = Product(
                    name=p_data["name"],
                    description=p_data["description"],
                    price=p_data["price"],
                    stock_quantity=p_data["stock_quantity"],
                    image_key=p_data.get("image_key"),
                    image_url=p_data.get("image_url"),
                    status=p_data["status"],
                )
                db.session.add(product)
                added_count += 1
            else:
                existing.description = p_data["description"]
                existing.price = p_data["price"]
                existing.stock_quantity = p_data["stock_quantity"]
                existing.image_key = p_data.get("image_key")
                existing.image_url = p_data.get("image_url")
                existing.status = p_data["status"]
                updated_count += 1

        db.session.commit()
        print(f" [Products] Seeded {added_count} new products, updated {updated_count} existing products.")
        print(f" [Total] Total products in database: {Product.query.count()}")
        print(" ZANDO database seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
