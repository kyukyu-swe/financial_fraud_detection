from langchain_core.tools import tool
from datetime import datetime, timedelta
from db.database import SessionLocal, Transaction


@tool
def check_transaction_history(card_id: str) -> dict:
    """
    Retrieve transaction history for a card to establish a behavioral baseline.
    Returns avg_amount, txn_count_last_1h, last_location, and total_txn_count.
    """
    db = SessionLocal()
    try:
        all_txns = (
            db.query(Transaction)
            .filter(Transaction.card_id == card_id)
            .order_by(Transaction.timestamp.desc())
            .limit(50)
            .all()
        )

        if not all_txns:
            return {
                "card_id": card_id,
                "avg_amount": 0.0,
                "txn_count_last_1h": 0,
                "last_location": "unknown",
                "total_txn_count": 0,
                "found": False,
            }

        amounts = [t.amount for t in all_txns]
        avg_amount = round(sum(amounts) / len(amounts), 2)

        cutoff = datetime.utcnow() - timedelta(hours=1)
        recent = [t for t in all_txns if t.timestamp >= cutoff]

        last_location = all_txns[0].location if all_txns else "unknown"

        return {
            "card_id": card_id,
            "avg_amount": avg_amount,
            "txn_count_last_1h": len(recent),
            "last_location": last_location,
            "total_txn_count": len(all_txns),
            "found": True,
        }
    finally:
        db.close()
