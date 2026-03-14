from typing import TypedDict, Optional


class AgentState(TypedDict):
    # Input
    transaction: dict

    # Populated by check_history node
    history: dict

    # Populated by check_rules node
    rule_flags: list
    rule_risk_level: str

    # Populated by score_anomaly node
    anomaly_score: float
    is_anomalous: bool

    # Populated by llm_reason node
    explanation: str
    decision: str   # "allow" | "review" | "block"

    # Populated by maybe_alert node
    alerted: bool
    alert_id: Optional[int]
