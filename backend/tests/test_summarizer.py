from app.services import summarizer


def test_summarize_transcript_uses_mock_when_gemini_key_is_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(summarizer, "_find_project_env", lambda: None)

    result = summarizer.summarize_transcript(
        "Neha: Abhishek, please create the first working POC by Friday."
    )

    assert result["executive_summary"]
    assert result["action_items"][0]["owner"] == "Abhishek"
    assert result["action_items"][0]["confidence"] == "high"


def test_normalize_summary_result_provides_expected_top_level_keys():
    result = summarizer._normalize_summary_result(
        {
            "summary": "Short summary.",
            "decisions": [{"decision": "Ship MVP.", "evidence_quote": "Ship MVP."}],
            "action_items": "not a list",
        }
    )

    assert result == {
        "executive_summary": "Short summary.",
        "key_decisions": [{"decision": "Ship MVP.", "evidence_quote": "Ship MVP."}],
        "action_items": [],
        "risks": [],
        "follow_up_questions": [],
    }
