"""
Rule Engine — the heart of the Decision Hub.

WHY this exists as a separate module:
  Evaluation logic is pure business logic. It has no HTTP, no DB writes,
  no side effects. Keeping it here means it can be unit-tested without
  a database, and swapped for a more sophisticated engine (Drools, OPA)
  without touching the API layer.

EVALUATION STRATEGY:
  1. Rules are evaluated in priority order (lower number = higher priority)
  2. First REJECT rule → stop evaluation, return REJECT immediately
     Rationale: a hard compliance block (AML_102) overrides everything.
     There is no point scoring a FRAUD rule if the country is sanctioned.
  3. CHALLENGE rules accumulate — they don't stop evaluation
     Rationale: challenges represent soft flags that need human review,
     multiple can co-exist.
  4. If no REJECT and no CHALLENGE → APPROVE
  5. If CHALLENGE rules fired → CHALLENGE (with all reasons listed)

RISK SCORE:
  A simplified numeric signal (0.0–1.0) attached to each decision.
  In a real system this would come from an ML model. Here it is derived
  from the most severe matched rule to give the concept meaning.
  null = no risk signal (clean approve with no matches).
"""

from dataclasses import dataclass

from app.models import DecisionRule


@dataclass
class RuleResult:
    rule_id: str
    matched: bool
    action: str
    reason_code: str
    owner: str


@dataclass
class EngineResult:
    decision: str          # APPROVE | REJECT | CHALLENGE
    allowed: bool
    reasons: list[dict]    # [{rule_id, reason_code, owner}] — only matched rules that matter
    risk_score: float | None
    rules_checked: list[dict]  # full audit list [{rule_id, matched, action}]
    rules_matched: list[dict]  # matched rules for audit


# Risk scores assigned per rule when matched — simplistic but meaningful for demo
_RULE_RISK_SCORES: dict[str, float] = {
    "AML_102": 0.95,
    "FRAUD_017": 0.91,
    "LIMIT_DAILY": 0.70,
}

_DEFAULT_CHALLENGE_RISK = 0.45


def evaluate_condition(rule: DecisionRule, context: dict) -> bool:
    """
    Evaluate a single rule's condition against the transfer context.
    Returns True if the rule condition is met (rule fires).
    """
    ctype = rule.condition_type
    params = rule.condition_params

    if ctype == "THRESHOLD":
        # Example: {"fields": ["daily_sum", "amount"], "operator": "SUM_GT", "threshold": 10000000}
        operator = params.get("operator", "")
        if operator == "SUM_GT":
            total = sum(float(context.get(f, 0) or 0) for f in params["fields"])
            return total > params["threshold"]
        # Extend: GT, LT, EQ, etc.
        return False

    elif ctype == "BLOCKLIST":
        # Example: {"field": "country", "blocked_values": ["IR", "KP", "CU", "SY"]}
        field_value = context.get(params["field"])
        return field_value in params.get("blocked_values", [])

    elif ctype == "COMPOSITE":
        # Example: {"conditions": [{"field": "device_trust", "eq": "LOW"}, {"field": "amount", "gt": 200000}]}
        # All sub-conditions must match (AND logic)
        for cond in params.get("conditions", []):
            field_value = context.get(cond["field"])
            if "eq" in cond:
                if field_value != cond["eq"]:
                    return False
            if "gt" in cond:
                try:
                    if not (float(field_value) > cond["gt"]):
                        return False
                except (TypeError, ValueError):
                    return False
            if "lt" in cond:
                try:
                    if not (float(field_value) < cond["lt"]):
                        return False
                except (TypeError, ValueError):
                    return False
        return True

    # Unknown condition type — fail safe: do not fire the rule
    return False


def run_evaluation(rules: list[DecisionRule], context: dict) -> EngineResult:
    """
    Evaluate all active rules against the context and return a structured result.

    Rules must be pre-sorted by priority (ascending = highest priority first).
    Only active rules should be passed here (filter in the caller).
    """
    rules_checked: list[dict] = []
    rules_matched: list[dict] = []
    challenge_reasons: list[dict] = []
    reject_reason: dict | None = None
    highest_risk_score: float | None = None

    for rule in rules:
        matched = evaluate_condition(rule, context)

        rules_checked.append({
            "rule_id": rule.rule_id,
            "matched": matched,
            "action": rule.action,
            "priority": rule.priority,
        })

        if matched:
            matched_entry = {
                "rule_id": rule.rule_id,
                "reason_code": rule.reason_code,
                "owner": rule.owner,
                "action": rule.action,
            }
            rules_matched.append(matched_entry)

            # Update risk score
            rule_risk = _RULE_RISK_SCORES.get(rule.rule_id)
            if rule_risk is not None:
                if highest_risk_score is None or rule_risk > highest_risk_score:
                    highest_risk_score = rule_risk

            if rule.action == "REJECT":
                # First REJECT wins — stop immediately
                reject_reason = matched_entry
                break

            elif rule.action == "CHALLENGE":
                challenge_reasons.append(matched_entry)
                if highest_risk_score is None:
                    highest_risk_score = _DEFAULT_CHALLENGE_RISK

    if reject_reason:
        return EngineResult(
            decision="REJECT",
            allowed=False,
            reasons=[reject_reason],
            risk_score=highest_risk_score,
            rules_checked=rules_checked,
            rules_matched=rules_matched,
        )

    if challenge_reasons:
        return EngineResult(
            decision="CHALLENGE",
            allowed=True,  # CHALLENGE = allow but flag for review
            reasons=challenge_reasons,
            risk_score=highest_risk_score,
            rules_checked=rules_checked,
            rules_matched=rules_matched,
        )

    return EngineResult(
        decision="APPROVE",
        allowed=True,
        reasons=[],
        risk_score=None,
        rules_checked=rules_checked,
        rules_matched=rules_matched,
    )
