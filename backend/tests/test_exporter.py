from types import SimpleNamespace

from app.services.exporter import export_meeting_markdown


def test_export_meeting_markdown_includes_summary_action_items_and_evidence():
    meeting = SimpleNamespace(title="Smart Docs Weekly Sync")
    summary = SimpleNamespace(
        executive_summary="The team discussed gateway monitoring.",
        key_decisions_json=(
            '[{"decision": "Use API Management.", '
            '"evidence_quote": "place API Management in front of Azure OpenAI"}]'
        ),
        risks_json=(
            '[{"risk": "Latency overhead.", '
            '"evidence_quote": "The biggest risk is latency."}]'
        ),
        follow_up_questions_json='["How much latency does the gateway add?"]',
    )
    action_items = [
        SimpleNamespace(
            owner="Abhishek",
            task="Create the POC.",
            due_date="Friday",
            priority="medium",
            status="open",
            confidence=0.9,
            evidence_quote="Abhishek, please create the first working POC by Friday.",
        )
    ]

    markdown = export_meeting_markdown(meeting, summary, action_items)

    assert "# Smart Docs Weekly Sync" in markdown
    assert "The team discussed gateway monitoring." in markdown
    assert "Use API Management." in markdown
    assert "Latency overhead." in markdown
    assert "| Abhishek | Create the POC. | Friday | medium | open | 0.9 |" in markdown
    assert "Evidence: Abhishek, please create the first working POC by Friday." in markdown
