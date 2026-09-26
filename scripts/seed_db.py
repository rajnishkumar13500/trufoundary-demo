import sys
import os
import random
import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base, SessionLocal
from app.models import User, Product, Order, OrderItem

def seed_database(num_users: int = 50, num_products: int = 100, num_orders: int = 25000):
    print(f"[*] Initializing database schema at {engine.url}...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if already seeded
        existing_orders = db.query(Order).count()
        if existing_orders >= num_orders:
            print(f"[+] Database already has {existing_orders} orders. Skipping seeding.")
            return

        print(f"[*] Seeding {num_users} users...")
        users = []
        for i in range(1, num_users + 1):
            users.append(User(name=f"User {i}", email=f"user{i}@example.com"))
        db.bulk_save_objects(users)
        db.commit()

        print(f"[*] Seeding {num_products} products...")
        products = []
        for i in range(1, num_products + 1):
            products.append(Product(name=f"Product SKU-{i:04d}", price=round(random.uniform(10.0, 500.0), 2), stock=500))
        db.bulk_save_objects(products)
        db.commit()

        # Query back IDs
        user_ids = [u.id for u in db.query(User.id).all()]
        product_ids = [p.id for p in db.query(Product.id).all()]

        print(f"[*] Seeding {num_orders} orders (batch insert)...")
        now = datetime.datetime.now(datetime.timezone.utc)
        batch_size = 5000
        orders_batch = []

        for i in range(1, num_orders + 1):
            uid = random.choice(user_ids)
            # Stagger timestamps across the past 180 days
            order_time = now - datetime.timedelta(minutes=random.randint(1, 259200))
            amount = round(random.uniform(25.0, 1500.0), 2)
            orders_batch.append(
                Order(
                    user_id=uid,
                    status=random.choice(["completed", "completed", "completed", "pending", "shipped"]),
                    total_amount=amount,
                    created_at=order_time
                )
            )

            if len(orders_batch) >= batch_size:
                db.bulk_save_objects(orders_batch)
                db.commit()
                print(f"    Inserted {i}/{num_orders} orders...")
                orders_batch = []

        if orders_batch:
            db.bulk_save_objects(orders_batch)
            db.commit()

        print(f"[OK] Successfully seeded {num_orders} orders across {num_users} users!")

    finally:
        db.close()

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 25000
    seed_database(num_orders=count)
