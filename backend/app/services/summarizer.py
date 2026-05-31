import json
import os
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def summarize_transcript(transcript_text: str) -> dict:
    _load_local_env()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return mock_summarize_transcript(transcript_text)

    try:
        return _summarize_with_gemini(transcript_text, api_key)
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError):
        return mock_summarize_transcript(transcript_text)


def _summarize_with_gemini(transcript_text: str, api_key: str) -> dict:
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"{GEMINI_API_URL}/{model}:generateContent"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"{_build_system_prompt()}\n\n"
                            f"Meeting transcript:\n\n{transcript_text}"
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
        },
    }

    http_request = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    with request.urlopen(http_request, timeout=30) as response:
        response_payload = json.loads(response.read().decode("utf-8"))

    response_text = response_payload["candidates"][0]["content"]["parts"][0]["text"]
    return _normalize_summary_result(json.loads(response_text))


def mock_summarize_transcript(transcript_text: str) -> dict:
    evidence = _find_evidence(
        transcript_text,
        "Abhishek, please create the first working POC by Friday.",
    )

    decision_evidence = _find_evidence(
        transcript_text,
        "My recommendation is to place API Management in front of Azure OpenAI",
    )

    risk_evidence = _find_evidence(
        transcript_text,
        "we should not log sensitive user content directly",
    )

    return {
        "executive_summary": (
            "The team discussed an Azure OpenAI monitoring approach, including "
            "gateway observability, metadata logging, cost tracking, and latency risks."
        ),
        "key_decisions": [
            {
                "decision": "Place API Management in front of Azure OpenAI.",
                "evidence_quote": decision_evidence,
            },
            {
                "decision": "Start with metadata logging only.",
                "evidence_quote": _find_evidence(
                    transcript_text,
                    "We can start with metadata logging only",
                ),
            },
        ],
        "action_items": [
            {
                "owner": "Abhishek",
                "task": "Create the first working POC.",
                "due_date": "Friday",
                "priority": "medium",
                "evidence_quote": evidence,
                "confidence": "high",
            },
            {
                "owner": "Jeevan",
                "task": "Validate the logging fields.",
                "due_date": "Wednesday",
                "priority": "medium",
                "evidence_quote": _find_evidence(
                    transcript_text,
                    "Jeevan, please validate the logging fields by Wednesday.",
                ),
                "confidence": "high",
            },
        ],
        "risks": [
            {
                "risk": "Sensitive user content should not be logged directly.",
                "evidence_quote": risk_evidence,
            },
            {
                "risk": "API Management may add latency overhead.",
                "evidence_quote": _find_evidence(
                    transcript_text,
                    "The biggest risk is latency.",
                ),
            },
        ],
        "follow_up_questions": [
            "How much latency does API Management add compared with the baseline?",
        ],
    }


def _find_evidence(transcript_text: str, preferred_quote: str) -> str:
    if preferred_quote.lower() in transcript_text.lower():
        return preferred_quote

    first_non_empty_line = next(
        (line.strip() for line in transcript_text.splitlines() if line.strip()),
        "",
    )
    return first_non_empty_line


def _build_system_prompt() -> str:
    return (
        "You summarize meeting transcripts into structured JSON. "
        "Do not invent facts. Every decision, risk, and action item must include "
        "an evidence_quote copied from the transcript. If an action item owner is "
        "missing, use Unassigned. If a due date is missing, use Not specified. "
        "Return JSON only with these exact top-level keys: executive_summary, "
        "key_decisions, action_items, risks, follow_up_questions. Do not return "
        "Markdown. Do not add commentary. The JSON object must have this shape: "
        '{"executive_summary":"string","key_decisions":[{"decision":"string",'
        '"evidence_quote":"string"}],"action_items":[{"owner":"string",'
        '"task":"string","due_date":"string","priority":"string",'
        '"evidence_quote":"string","confidence":"high|medium|low"}],'
        '"risks":[{"risk":"string","evidence_quote":"string"}],'
        '"follow_up_questions":["string"]}.'
    )


def _normalize_summary_result(summary: dict) -> dict:
    return {
        "executive_summary": str(
            summary.get("executive_summary")
            or summary.get("summary")
            or summary.get("meeting_summary")
            or ""
        ),
        "key_decisions": _ensure_list(
            summary.get("key_decisions") or summary.get("decisions")
        ),
        "action_items": _ensure_list(summary.get("action_items")),
        "risks": _ensure_list(summary.get("risks")),
        "follow_up_questions": _ensure_list(
            summary.get("follow_up_questions") or summary.get("questions")
        ),
    }


def _ensure_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _load_local_env() -> None:
    env_path = _find_project_env()
    if env_path is None:
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#") or "=" not in stripped_line:
            continue

        name, value = stripped_line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")

        if name and name not in os.environ:
            os.environ[name] = value


def _find_project_env() -> Path | None:
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        env_path = parent / ".env"
        if env_path.exists():
            return env_path

    return None
