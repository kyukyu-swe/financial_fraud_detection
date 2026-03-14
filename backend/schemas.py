from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TransactionRequest(BaseModel):
    transaction_id: str
    card_id: str
    merchant_id: str
    amount: float = Field(..., gt=0)
    currency: str = "THB"
    location: str
    timestamp: Optional[str] = None

    def model_post_init(self, __context):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class TransactionResponse(BaseModel):
    transaction_id: str
    card_id: str
    merchant_id: str
    amount: float
    location: str
    anomaly_score: float
    is_anomalous: bool
    rule_flags: list
    rule_risk_level: str
    decision: str
    explanation: str
    alerted: bool
    alert_id: Optional[int] = None
