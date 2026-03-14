import sys
import os

# Ensure project root is on sys.path so all imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json

from backend.schemas import TransactionRequest, TransactionResponse
from agent.graph import run_agent
from db.database import get_db, Transaction, Alert, init_db
from db.seed import seed
from ml.train import ensure_model

app = FastAPI(
    title="Omise Fraud Detection API",
    description="Real-time AI-powered fraud detection using LangGraph + Isolation Forest",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    print("[startup] Initialising database...")
    init_db()
    seed()
    print("[startup] Ensuring ML model exists...")
    ensure_model()
    print("[startup] Ready.")


@app.post("/transaction", response_model=TransactionResponse)
async def evaluate_transaction(txn: TransactionRequest):
    """
    Submit a transaction for real-time fraud evaluation.
    The LangGraph agent runs feature extraction → rule check → anomaly scoring → LLM reasoning → alert.
    """
    try:
        result = await run_agent(txn.model_dump())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/transactions")
def list_transactions(limit: int = 50, db: Session = Depends(get_db)):
    """Return recent transactions for the dashboard."""
    rows = (
        db.query(Transaction)
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "transaction_id": r.transaction_id,
            "card_id": r.card_id,
            "merchant_id": r.merchant_id,
            "amount": r.amount,
            "currency": r.currency,
            "location": r.location,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "is_fraud": r.is_fraud,
        }
        for r in rows
    ]


@app.get("/alerts")
def list_alerts(limit: int = 50, db: Session = Depends(get_db)):
    """Return recent fraud alerts for the dashboard."""
    rows = (
        db.query(Alert)
        .order_by(Alert.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "transaction_id": r.transaction_id,
            "merchant_id": r.merchant_id,
            "risk_score": r.risk_score,
            "decision": r.decision,
            "explanation": r.explanation,
            "rule_flags": json.loads(r.rule_flags) if r.rule_flags else [],
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in rows
    ]


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
