from datetime import datetime, timezone, timedelta
from app.db import engine, Base, SessionLocal
from app.routes.observation import Product, Subscription, ObservationRecord, User
from werkzeug.security import generate_password_hash
import random

def seed_database():
    """Populate database with realistic GeoScope data"""
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Clear existing data (optional - comment out if you want to keep existing data)
        print("🗑️  Clearing existing data...")
        db.query(Subscription).delete()
        db.query(ObservationRecord).delete()
        db.query(Product).delete()
      
        
        # ============================================================
        # 1. CREATE PRODUCTS 
        # ============================================================
        print("\n📦 Creating Products...")
        
        products = [
            Product(
                name="Crop Health Monitoring",
                description="High-res spectral analysis for agriculture.",
                price="$499/mo",
                stripe_price_id="price_1Stb2o9vslVP6XFWGC7vikxQ"
            ),
            Product(
                name="Wildfire Risk Assessment",
                description="Real-time thermal imaging and risk modeling.",
                price="$399/mo",
                stripe_price_id="price_1Stb5D9vslVP6XFW3gJG6GvE"
            ),
            Product(
                name="Urban Expansion Tracking",
                description="Monthly change detection for city planning.",
                price="$299/mo",
                stripe_price_id="price_1Stb7W9vslVP6XFWkEEmUE4g"
            ),
            Product(
                name="Deforestation Alert System",
                description="Instant notification of illegal logging activities.",
                price="$199/mo",
                stripe_price_id="price_1StbA09vslVP6XFWwcltwqQL"
            ),
            Product(
                name="Pro Plan (All Access)",
                description="Complete access to all GeoScope intelligence products, unlimited data downloads, and priority API access.",
                price="$999/mo",
                stripe_price_id="price_1Stai89vslVP6XFWjMs1acaA"
            )
        ]
        
        db.add_all(products)
        db.commit()
        
        # Refresh to get IDs
        for p in products:
            db.refresh(p)
        
        print(f"✅ Created {len(products)} products")

        # ============================================================
        # 2. CREATE USERS (Admin + Demo Test User)
        # ============================================================
        print("\n👥 Seeding users...")
        users = [
            {
                "email": "admin@geoscope.com",
                "password": "password",
                "first_name": "Admin",
                "last_name": "User",
                "is_verified": 1,
                "is_2fa_enabled": 0
            },
            {
                "email": "testuser@geoscope.com",
                "password": "password123",
                "first_name": "Test",
                "last_name": "User",
                "is_verified": 1,
                "is_2fa_enabled": 0
            }
        ]

        for u in users:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if existing:
                print(f"- Updating user {u['email']}")
                existing.password = generate_password_hash(u["password"])
                existing.first_name = u["first_name"]
                existing.last_name = u["last_name"]
                existing.is_verified = u["is_verified"]
                existing.is_2fa_enabled = u["is_2fa_enabled"]
            else:
                print(f"- Creating user {u['email']}")
                new_user = User(
                    email=u["email"],
                    password=generate_password_hash(u["password"]),
                    first_name=u["first_name"],
                    last_name=u["last_name"],
                    is_verified=u["is_verified"],
                    is_2fa_enabled=u["is_2fa_enabled"]
                )
                db.add(new_user)
        db.commit()

        # ============================================================
        # 3. CREATE SUBSCRIPTIONS (Randomly assign some products)
        # ============================================================
        print("\n🔔 Creating subscriptions...")
        all_products = db.query(Product).all()
        admin = db.query(User).filter(User.email == "admin@geoscope.com").first()
        testuser = db.query(User).filter(User.email == "testuser@geoscope.com").first()

        # Clear existing subscriptions for these users to avoid duplicates
        if admin:
            db.query(Subscription).filter(Subscription.user_id == admin.email).delete()
        if testuser:
            db.query(Subscription).filter(Subscription.user_id == testuser.email).delete()

        # Assign subscriptions
        for p in random.sample(all_products, k=min(3, len(all_products))):
            db.add(Subscription(user_id=admin.email, product_id=p.id))
        for p in random.sample(all_products, k=min(2, len(all_products))):
            db.add(Subscription(user_id=testuser.email, product_id=p.id))
        db.commit()
        print("✅ Subscriptions created")

        # ============================================================
        # 4. CREATE SAMPLE OBSERVATIONS (linked to some products)
        # ============================================================
        print("\n🛰️  Creating sample observation records...")
        sample_coords = [
            "-33.865143,151.209900",
            "51.507351,-0.127758",
            "40.712776,-74.005974",
            "-1.292066,36.821945",
            "35.689487,139.691711"
        ]
        satellites = ["Landsat-9", "Sentinel-2", "MODIS", "PlanetScope"]

        observations = []
        now = datetime.now(timezone.utc)
        
        # Products 1 to 4 are the individual data products
        for product_id in [1, 2, 3, 4]:
            print(f"- Generating 100 observations for Product ID {product_id}...")
            for _ in range(100):
                obs = ObservationRecord(
                    timestamp=(now - timedelta(days=random.randint(0, 365))),
                    timezone="UTC",
                    coordinates=f"{round(random.uniform(-90, 90), 6)}, {round(random.uniform(-180, 180), 6)}",
                    satellite_id=random.choice(satellites),
                    spectral_indices=f"{{'NDVI': {round(random.uniform(0.1, 0.9), 2)}}}",
                    notes=f"Synthetic observation for Product {product_id}",
                    product_id=product_id
                )
                observations.append(obs)
                
            # Batch add per product to avoid huge memory spike if we were doing millions
            db.add_all(observations[-100:])
            db.commit()

        print(f"✅ Created {len(observations)} observations total")

    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()