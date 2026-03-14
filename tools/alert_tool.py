import json
from langchain_core.tools import tool
from datetime import datetime
from db.database import SessionLocal, Alert


@tool
def send_alert(
    transaction_id: str,
    merchant_id: str,
    risk_score: float,
    decision: str,
    explanation: str,
    rule_flags: list,
) -> dict:
    """
    Send a fraud alert to the merchant and persist it in the alerts table.
    In demo mode this logs to console; in production replace with Twilio/SendGrid.
    """
    db = SessionLocal()
    try:
        alert = Alert(
            transaction_id=transaction_id,
            merchant_id=merchant_id,
            risk_score=risk_score,
            decision=decision,
            explanation=explanation,
            rule_flags=json.dumps(rule_flags),
            timestamp=datetime.utcnow(),
        )
        db.add(alert)
        db.commit()

        print(f"\n{'='*60}")
        print(f"[FRAUD ALERT] Merchant: {merchant_id}")
        print(f"  Transaction : {transaction_id}")
        print(f"  Decision    : {decision.upper()}")
        print(f"  Risk score  : {risk_score:.4f}")
        print(f"  Flags       : {', '.join(rule_flags) if rule_flags else 'none'}")
        print(f"  Explanation : {explanation[:200]}")
        print(f"{'='*60}\n")

        return {"alerted": True, "alert_id": alert.id}
    finally:
        db.close()
