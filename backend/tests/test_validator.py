from app.services.validator import validate_action_items, validate_decisions


def test_validate_action_items_keeps_supported_item_and_defaults_missing_fields():
    transcript = "Neha: Abhishek, please create the POC by Friday."
    action_items = [
        {
            "task": "Create the POC.",
            "evidence_quote": "Abhishek, please create the POC by Friday.",
            "confidence": "high",
        }
    ]

    validated = validate_action_items(action_items, transcript)

    assert validated == [
        {
            "owner": "Unassigned",
            "task": "Create the POC.",
            "due_date": "Not specified",
            "priority": "medium",
            "status": "open",
            "evidence_quote": "Abhishek, please create the POC by Friday.",
            "confidence": 0.9,
        }
    ]


def test_validate_action_items_rejects_unsupported_evidence():
    transcript = "Neha: Abhishek, please create the POC by Friday."
    action_items = [
        {
            "owner": "Jeevan",
            "task": "Prepare a budget report.",
            "evidence_quote": "Jeevan, please prepare a budget report.",
        }
    ]

    assert validate_action_items(action_items, transcript) == []


def test_validate_decisions_requires_supported_evidence():
    transcript = "Abhishek: We should use API Management in front of Azure OpenAI."
    decisions = [
        {
            "decision": "Use API Management in front of Azure OpenAI.",
            "evidence_quote": "We should use API Management in front of Azure OpenAI.",
        },
        {
            "decision": "Use Redis for queues.",
            "evidence_quote": "We should use Redis for queues.",
        },
    ]

    validated = validate_decisions(decisions, transcript)

    assert validated == [
        {
            "decision": "Use API Management in front of Azure OpenAI.",
            "evidence_quote": "We should use API Management in front of Azure OpenAI.",
        }
    ]
