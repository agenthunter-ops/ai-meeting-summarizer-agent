def validate_action_items(action_items: list[dict], transcript_text: str) -> list[dict]:
    valid_items = []

    for action_item in action_items:
        normalized_item = normalize_action_item(action_item)

        if not normalized_item["task"]:
            continue

        if not _evidence_is_supported(normalized_item["evidence_quote"], transcript_text):
            continue

        valid_items.append(normalized_item)

    return valid_items


def validate_decisions(decisions: list[dict], transcript_text: str) -> list[dict]:
    valid_decisions = []

    for decision in decisions:
        decision_text = str(decision.get("decision", "")).strip()
        evidence_quote = str(decision.get("evidence_quote", "")).strip()

        if not decision_text:
            continue

        if not _evidence_is_supported(evidence_quote, transcript_text):
            continue

        valid_decisions.append(
            {
                "decision": decision_text,
                "evidence_quote": evidence_quote,
            }
        )

    return valid_decisions


def normalize_action_item(action_item: dict) -> dict:
    return {
        "owner": str(action_item.get("owner") or "Unassigned").strip() or "Unassigned",
        "task": str(action_item.get("task") or "").strip(),
        "due_date": str(action_item.get("due_date") or "Not specified").strip() or "Not specified",
        "priority": str(action_item.get("priority") or "medium").strip().lower() or "medium",
        "status": str(action_item.get("status") or "open").strip().lower() or "open",
        "evidence_quote": str(action_item.get("evidence_quote") or "").strip(),
        "confidence": _normalize_confidence(action_item.get("confidence")),
    }


def _evidence_is_supported(evidence_quote: str, transcript_text: str) -> bool:
    if not evidence_quote:
        return False

    return evidence_quote.lower() in transcript_text.lower()


def _normalize_confidence(confidence: object) -> float:
    if isinstance(confidence, int | float):
        return max(0.0, min(float(confidence), 1.0))

    confidence_text = str(confidence or "low").strip().lower()
    confidence_scores = {
        "high": 0.9,
        "medium": 0.6,
        "low": 0.3,
    }

    return confidence_scores.get(confidence_text, 0.3)
