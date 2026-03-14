from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes import (
    extract_features,
    check_history,
    check_rules,
    score_anomaly,
    llm_reason,
    maybe_alert,
    route_after_reason,
)


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("extract_features", extract_features)
    graph.add_node("check_history", check_history)
    graph.add_node("check_rules", check_rules)
    graph.add_node("score_anomaly", score_anomaly)
    graph.add_node("llm_reason", llm_reason)
    graph.add_node("maybe_alert", maybe_alert)

    graph.set_entry_point("extract_features")

    graph.add_edge("extract_features", "check_history")
    graph.add_edge("check_history", "check_rules")
    graph.add_edge("check_rules", "score_anomaly")
    graph.add_edge("score_anomaly", "llm_reason")

    graph.add_conditional_edges(
        "llm_reason",
        route_after_reason,
        {"alert": "maybe_alert", "end": END},
    )

    graph.add_edge("maybe_alert", END)

    return graph.compile()


# Module-level compiled graph instance (imported by FastAPI)
fraud_agent = build_graph()


async def run_agent(transaction: dict) -> dict:
    initial_state: AgentState = {
        "transaction": transaction,
        "history": {},
        "rule_flags": [],
        "rule_risk_level": "low",
        "anomaly_score": 0.0,
        "is_anomalous": False,
        "explanation": "",
        "decision": "allow",
        "alerted": False,
        "alert_id": None,
    }

    final_state = await fraud_agent.ainvoke(initial_state)

    return {
        "transaction_id": transaction.get("transaction_id"),
        "card_id": transaction.get("card_id"),
        "merchant_id": transaction.get("merchant_id"),
        "amount": transaction.get("amount"),
        "location": transaction.get("location"),
        "anomaly_score": round(final_state.get("anomaly_score", 0.0), 4),
        "is_anomalous": final_state.get("is_anomalous", False),
        "rule_flags": final_state.get("rule_flags", []),
        "rule_risk_level": final_state.get("rule_risk_level", "low"),
        "decision": final_state.get("decision", "allow"),
        "explanation": final_state.get("explanation", ""),
        "alerted": final_state.get("alerted", False),
        "alert_id": final_state.get("alert_id"),
    }
