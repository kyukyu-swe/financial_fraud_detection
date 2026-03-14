from langchain_core.tools import tool


@tool
def check_fraud_rules(
    amount: float,
    location: str,
    hour: int,
    avg_amount: float,
    last_location: str,
    txn_count_last_1h: int,
) -> dict:
    """
    Apply deterministic fraud rules to a transaction.
    Returns a list of triggered rule flags and an overall rule_risk_level.
    """
    flags = []

    if avg_amount > 0 and amount > avg_amount * 3:
        multiplier = round(amount / avg_amount, 1)
        flags.append(f"amount_spike: {multiplier}x above card average (avg={avg_amount})")

    if last_location and last_location != "unknown" and location != last_location:
        flags.append(f"location_change: {last_location} → {location}")

    if txn_count_last_1h >= 5:
        flags.append(f"high_frequency: {txn_count_last_1h} transactions in last hour")

    if 1 <= hour <= 4:
        flags.append(f"unusual_hour: transaction at {hour:02d}:xx (1am–4am)")

    if amount > 10000:
        flags.append(f"high_amount: {amount} exceeds 10,000 absolute threshold")

    rule_risk_level = "high" if len(flags) >= 2 else ("medium" if len(flags) == 1 else "low")

    return {
        "flags": flags,
        "flag_count": len(flags),
        "rule_risk_level": rule_risk_level,
    }
