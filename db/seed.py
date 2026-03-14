import random
import uuid
from datetime import datetime, timedelta
from db.database import SessionLocal, Transaction, init_db

LOCATIONS = ["Bangkok", "Chiang Mai", "Phuket", "Singapore", "Tokyo", "London", "New York"]
MERCHANTS = ["mch_coffee_001", "mch_retail_002", "mch_food_003", "mch_travel_004", "mch_online_005"]
CARDS = [f"card_{i:04d}" for i in range(1, 21)]


def seed():
    init_db()
    db = SessionLocal()

    if db.query(Transaction).count() > 0:
        db.close()
        return

    rng = random.Random(42)
    base_time = datetime.utcnow() - timedelta(days=7)
    rows = []

    # 180 normal transactions across cards
    for i in range(180):
        card = rng.choice(CARDS)
        rows.append(Transaction(
            transaction_id=f"txn_{uuid.uuid4().hex[:8]}",
            card_id=card,
            merchant_id=rng.choice(MERCHANTS),
            amount=round(rng.uniform(50, 800), 2),
            currency="THB",
            location="Bangkok",
            timestamp=base_time + timedelta(hours=rng.uniform(0, 168)),
            is_fraud=False,
        ))

    # 20 fraud-like transactions
    fraud_scenarios = [
        # High amount spike
        {"amount": round(rng.uniform(8000, 15000), 2), "location": "Bangkok", "is_fraud": True},
        {"amount": round(rng.uniform(9000, 20000), 2), "location": "Bangkok", "is_fraud": True},
        # Location jump
        {"amount": round(rng.uniform(200, 500), 2), "location": "London", "is_fraud": True},
        {"amount": round(rng.uniform(300, 600), 2), "location": "New York", "is_fraud": True},
        {"amount": round(rng.uniform(100, 400), 2), "location": "Tokyo", "is_fraud": True},
        # Odd hours (1am-4am) + high amount
        {"amount": round(rng.uniform(5000, 12000), 2), "location": "Singapore", "is_fraud": True},
        {"amount": round(rng.uniform(3000, 8000), 2), "location": "Bangkok", "is_fraud": True},
        # Rapid velocity (many transactions close together, handled by frequency check in rules)
        {"amount": round(rng.uniform(100, 300), 2), "location": "Bangkok", "is_fraud": True},
        {"amount": round(rng.uniform(100, 300), 2), "location": "Bangkok", "is_fraud": True},
        {"amount": round(rng.uniform(100, 300), 2), "location": "Bangkok", "is_fraud": True},
        {"amount": round(rng.uniform(100, 300), 2), "location": "Bangkok", "is_fraud": True},
        {"amount": round(rng.uniform(100, 300), 2), "location": "Bangkok", "is_fraud": True},
        {"amount": round(rng.uniform(100, 300), 2), "location": "Bangkok", "is_fraud": True},
        {"amount": round(rng.uniform(5000, 10000), 2), "location": "Phuket", "is_fraud": True},
        {"amount": round(rng.uniform(7000, 18000), 2), "location": "Chiang Mai", "is_fraud": True},
        {"amount": round(rng.uniform(200, 600), 2), "location": "Singapore", "is_fraud": True},
        {"amount": round(rng.uniform(11000, 25000), 2), "location": "Bangkok", "is_fraud": True},
        {"amount": round(rng.uniform(200, 400), 2), "location": "London", "is_fraud": True},
        {"amount": round(rng.uniform(9000, 14000), 2), "location": "Tokyo", "is_fraud": True},
        {"amount": round(rng.uniform(6000, 12000), 2), "location": "New York", "is_fraud": True},
    ]

    fraud_card = CARDS[0]
    rapid_time = datetime.utcnow() - timedelta(minutes=30)
    for i, scenario in enumerate(fraud_scenarios):
        hour_offset = rng.uniform(0, 2) if i < 6 else 0
        ts = rapid_time + timedelta(minutes=i * 3) if scenario["is_fraud"] and scenario["amount"] < 500 else (
            base_time + timedelta(hours=rng.uniform(0, 170), minutes=rng.uniform(0, 60))
        )
        rows.append(Transaction(
            transaction_id=f"txn_{uuid.uuid4().hex[:8]}",
            card_id=fraud_card if scenario["amount"] < 500 else rng.choice(CARDS),
            merchant_id=rng.choice(MERCHANTS),
            amount=scenario["amount"],
            currency="THB",
            location=scenario["location"],
            timestamp=ts,
            is_fraud=scenario["is_fraud"],
        ))

    fraud_count = sum(1 for scenario in fraud_scenarios if scenario["is_fraud"])
    db.add_all(rows)
    db.commit()
    db.close()
    print(f"[seed] Inserted {len(rows)} transactions ({fraud_count} fraud)")


if __name__ == "__main__":
    seed()
