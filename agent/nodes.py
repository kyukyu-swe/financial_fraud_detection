import os
import json
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from agent.state import AgentState
from tools.history_tool import check_transaction_history
from tools.rules_tool import check_fraud_rules
from tools.alert_tool import send_alert
from ml.scorer import anomaly_score, is_anomalous


# ---------------------------------------------------------------------------
# LLM setup — switchable via LLM_PROVIDER env var
# ---------------------------------------------------------------------------

def _build_llm():
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
        )
    else:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            temperature=0,
        )


_llm = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = _build_llm()
    return _llm


# ---------------------------------------------------------------------------
# Node: extract_features
# ---------------------------------------------------------------------------

def extract_features(state: AgentState) -> AgentState:
    txn = state["transaction"]
    ts_raw = txn.get("timestamp", datetime.utcnow().isoformat())
    if isinstance(ts_raw, str):
        try:
            ts = datetime.fromisoformat(ts_raw)
        except ValueError:
            ts = datetime.utcnow()
    else:
        ts = ts_raw

    txn["hour_of_day"] = ts.hour
    txn["timestamp"] = ts.isoformat()
    return {"transaction": txn}


# ---------------------------------------------------------------------------
# Node: check_history
# ---------------------------------------------------------------------------

def check_history(state: AgentState) -> AgentState:
    card_id = state["transaction"].get("card_id", "unknown")
    result = check_transaction_history.invoke({"card_id": card_id})
    return {"history": result}


# ---------------------------------------------------------------------------
# Node: check_rules
# ---------------------------------------------------------------------------

def check_rules(state: AgentState) -> AgentState:
    txn = state["transaction"]
    history = state.get("history", {})

    result = check_fraud_rules.invoke({
        "amount": txn.get("amount", 0),
        "location": txn.get("location", "unknown"),
        "hour": txn.get("hour_of_day", 12),
        "avg_amount": history.get("avg_amount", 0),
        "last_location": history.get("last_location", "unknown"),
        "txn_count_last_1h": history.get("txn_count_last_1h", 0),
    })

    return {
        "rule_flags": result["flags"],
        "rule_risk_level": result["rule_risk_level"],
    }


# ---------------------------------------------------------------------------
# Node: score_anomaly
# ---------------------------------------------------------------------------

def score_anomaly(state: AgentState) -> AgentState:
    txn = state["transaction"]
    history = state.get("history", {})

    amount = txn.get("amount", 0)
    hour = txn.get("hour_of_day", 12)
    freq = history.get("txn_count_last_1h", 0)

    score = anomaly_score(amount, hour, freq)
    anomalous = is_anomalous(amount, hour, freq)

    return {"anomaly_score": score, "is_anomalous": anomalous}


# ---------------------------------------------------------------------------
# Node: llm_reason
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a fraud analyst for Omise, a payment processor.
You receive a transaction with supporting signals and must produce a fraud decision.

Respond ONLY with valid JSON in this exact format:
{
  "decision": "allow" | "review" | "block",
  "explanation": "<concise 2-3 sentence explanation for the merchant>"
}

Decision rules:
- "allow"  → transaction appears normal, no significant signals
- "review" → moderate risk, merchant should manually verify
- "block"  → high risk, transaction should be declined immediately"""


def llm_reason(state: AgentState) -> AgentState:
    txn = state["transaction"]
    history = state.get("history", {})
    rule_flags = state.get("rule_flags", [])
    score = state.get("anomaly_score", 0.0)
    is_anom = state.get("is_anomalous", False)

    prompt = f"""Transaction details:
- ID         : {txn.get('transaction_id', 'N/A')}
- Card       : {txn.get('card_id', 'N/A')}
- Merchant   : {txn.get('merchant_id', 'N/A')}
- Amount     : {txn.get('currency', 'THB')} {txn.get('amount', 0):,.2f}
- Location   : {txn.get('location', 'unknown')}
- Time       : {txn.get('timestamp', 'N/A')} (hour {txn.get('hour_of_day', '?')})

Card behavioral baseline:
- Average amount   : {history.get('avg_amount', 'N/A')}
- Transactions/1h  : {history.get('txn_count_last_1h', 'N/A')}
- Last location    : {history.get('last_location', 'N/A')}
- Card seen before : {history.get('found', False)}

Rule engine flags triggered ({len(rule_flags)}):
{chr(10).join(f'  - {f}' for f in rule_flags) if rule_flags else '  (none)'}

Isolation Forest anomaly score: {score:.4f}
  (range: negative=anomalous, 0=boundary, positive=normal)
  Flagged as anomalous: {is_anom}

Based on all the above signals, provide your decision and explanation."""

    llm = get_llm()
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(
            line for line in lines
            if not line.startswith("```")
        ).strip()

    try:
        parsed = json.loads(content)
        decision = parsed.get("decision", "review")
        explanation = parsed.get("explanation", content)
    except json.JSONDecodeError:
        decision = "review"
        explanation = content

    if decision not in ("allow", "review", "block"):
        decision = "review"

    return {"decision": decision, "explanation": explanation}


# ---------------------------------------------------------------------------
# Node: maybe_alert
# ---------------------------------------------------------------------------

def maybe_alert(state: AgentState) -> AgentState:
    txn = state["transaction"]
    result = send_alert.invoke({
        "transaction_id": txn.get("transaction_id", "unknown"),
        "merchant_id": txn.get("merchant_id", "unknown"),
        "risk_score": state.get("anomaly_score", 0.0),
        "decision": state.get("decision", "review"),
        "explanation": state.get("explanation", ""),
        "rule_flags": state.get("rule_flags", []),
    })
    return {"alerted": result.get("alerted", False), "alert_id": result.get("alert_id")}


# ---------------------------------------------------------------------------
# Conditional routing after llm_reason
# ---------------------------------------------------------------------------

def route_after_reason(state: AgentState) -> str:
    if state.get("decision") == "allow":
        return "end"
    return "alert"
