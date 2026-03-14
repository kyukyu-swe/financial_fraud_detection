import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
import requests
import streamlit as st
import pandas as pd
from datetime import datetime

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(
    page_title="Omise Fraud Detection",
    page_icon="🛡️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_alerts():
    try:
        r = requests.get(f"{API_BASE}/alerts?limit=50", timeout=3)
        return r.json() if r.ok else []
    except Exception:
        return []


def fetch_transactions():
    try:
        r = requests.get(f"{API_BASE}/transactions?limit=50", timeout=3)
        return r.json() if r.ok else []
    except Exception:
        return []


def submit_transaction(payload: dict):
    try:
        r = requests.post(f"{API_BASE}/transaction", json=payload, timeout=60)
        return r.json() if r.ok else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


def decision_badge(decision: str) -> str:
    colors = {"allow": "🟢", "review": "🟡", "block": "🔴"}
    return f"{colors.get(decision, '⚪')} {decision.upper()}"


# ---------------------------------------------------------------------------
# Sidebar — submit test transaction
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🛡️ Omise Fraud Detection")
    st.caption("Real-time AI agent — LangGraph + Isolation Forest")
    st.divider()

    st.subheader("Submit Test Transaction")

    with st.form("txn_form"):
        card_id = st.selectbox("Card ID", [f"card_{i:04d}" for i in range(1, 21)])
        merchant_id = st.selectbox(
            "Merchant",
            ["mch_coffee_001", "mch_retail_002", "mch_food_003", "mch_travel_004", "mch_online_005"],
        )
        amount = st.number_input("Amount (THB)", min_value=1.0, max_value=100000.0, value=500.0, step=50.0)
        location = st.selectbox(
            "Location",
            ["Bangkok", "Chiang Mai", "Phuket", "Singapore", "Tokyo", "London", "New York"],
        )
        timestamp = st.text_input("Timestamp (ISO)", value=datetime.utcnow().isoformat())
        submitted = st.form_submit_button("Evaluate Transaction", use_container_width=True)

    if submitted:
        payload = {
            "transaction_id": f"txn_{uuid.uuid4().hex[:8]}",
            "card_id": card_id,
            "merchant_id": merchant_id,
            "amount": amount,
            "currency": "THB",
            "location": location,
            "timestamp": timestamp,
        }
        with st.spinner("Agent processing..."):
            result = submit_transaction(payload)

        st.divider()
        if "error" in result:
            st.error(f"Error: {result['error']}")
        else:
            dec = result.get("decision", "unknown")
            badge = decision_badge(dec)
            st.markdown(f"### Result: {badge}")
            st.metric("Anomaly Score", f"{result.get('anomaly_score', 0):.4f}")

            flags = result.get("rule_flags", [])
            if flags:
                st.warning("Rule flags triggered:")
                for f in flags:
                    st.markdown(f"  - `{f}`")
            else:
                st.success("No rule flags triggered")

            with st.expander("LLM Explanation"):
                st.write(result.get("explanation", "N/A"))

    st.divider()
    st.caption("Auto-refresh every 5s")
    auto_refresh = st.toggle("Auto-refresh dashboard", value=False)


# ---------------------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------------------

st.title("Fraud Monitoring Dashboard")
st.caption(f"Connected to {API_BASE} · Last updated: {datetime.now().strftime('%H:%M:%S')}")

alerts = fetch_alerts()
transactions = fetch_transactions()

# ---------------------------------------------------------------------------
# Metrics row
# ---------------------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

total_txns = len(transactions)
total_alerts = len(alerts)
blocked = sum(1 for a in alerts if a.get("decision") == "block")
review = sum(1 for a in alerts if a.get("decision") == "review")

col1.metric("Transactions (last 50)", total_txns)
col2.metric("Alerts Raised", total_alerts)
col3.metric("Blocked", blocked, delta=None)
col4.metric("Under Review", review, delta=None)

st.divider()

# ---------------------------------------------------------------------------
# Alert log
# ---------------------------------------------------------------------------

left, right = st.columns([1, 1])

with left:
    st.subheader("Recent Fraud Alerts")
    if alerts:
        for alert in alerts[:15]:
            dec = alert.get("decision", "unknown")
            badge = decision_badge(dec)
            ts = alert.get("timestamp", "")[:19].replace("T", " ")
            with st.expander(f"{badge} · txn `{alert.get('transaction_id')}` · {ts}"):
                st.markdown(f"**Merchant:** `{alert.get('merchant_id')}`")
                st.markdown(f"**Risk score:** `{alert.get('risk_score', 0):.4f}`")
                flags = alert.get("rule_flags", [])
                if flags:
                    st.markdown("**Rule flags:**")
                    for f in flags:
                        st.markdown(f"  - `{f}`")
                st.markdown("**Explanation:**")
                st.info(alert.get("explanation", "N/A"))
    else:
        st.info("No alerts yet. Submit a transaction from the sidebar.")

# ---------------------------------------------------------------------------
# Transaction feed
# ---------------------------------------------------------------------------

with right:
    st.subheader("Transaction Feed (last 50)")
    if transactions:
        df = pd.DataFrame(transactions)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
        df["is_fraud"] = df["is_fraud"].map({True: "⚠️ Fraud", False: "✅ Normal"})
        df = df[["transaction_id", "card_id", "amount", "location", "timestamp", "is_fraud"]]
        df.columns = ["TX ID", "Card", "Amount (THB)", "Location", "Time", "Label"]

        def highlight_fraud(row):
            if "Fraud" in str(row["Label"]):
                return ["background-color: #3d1a1a"] * len(row)
            return [""] * len(row)

        st.dataframe(
            df.style.apply(highlight_fraud, axis=1),
            use_container_width=True,
            height=480,
        )
    else:
        st.info("No transactions in database yet.")

# ---------------------------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------------------------

if auto_refresh:
    import time
    time.sleep(5)
    st.rerun()
