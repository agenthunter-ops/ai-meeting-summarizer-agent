import json
from typing import Any


# Builds a Markdown export string from a meeting, optional summary, and action items.
def export_meeting_markdown(meeting: Any, summary: Any, action_items: list[Any]) -> str:
    # Collects each Markdown line before joining them into one export string.
    lines = [
        # Adds the meeting title as the top-level Markdown heading.
        f"# {meeting.title}",
        # Adds a blank line for readable Markdown spacing.
        "",
        # Starts the executive summary section in the Markdown export.
        "## Executive Summary",
        # Adds the summary text or a fallback message, cleaned for safe one-line Markdown.
        _safe_text(summary.executive_summary if summary else "No summary available."),
        # Adds a blank line before the next Markdown section.
        "",
        # Starts the key decisions section in the Markdown export.
        "## Key Decisions",
        # Inserts formatted decision and evidence lines into the main Markdown list.
        *_format_evidence_items(
            # Converts stored decisions JSON text into a Python list, or uses an empty list.
            _load_json_list(summary.key_decisions_json if summary else "[]"),
            # Tells the formatter to read each item's main text from the "decision" key.
            "decision",
        ),
        "",
        "## Risks",
        *_format_evidence_items(
            _load_json_list(summary.risks_json if summary else "[]"),
            "risk",
        ),
        "",
        "## Follow-Up Questions",
        *_format_plain_list(
            _load_json_list(summary.follow_up_questions_json if summary else "[]")
        ),
        "",
        "## Action Items",
        "| Owner | Task | Due Date | Priority | Status | Confidence |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for item in action_items:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_text(item.owner),
                    _table_text(item.task),
                    _table_text(item.due_date),
                    _table_text(item.priority),
                    _table_text(item.status),
                    _table_text(str(item.confidence)),
                ]
            )
            + " |"
        )
        lines.append(f"> Evidence: {_safe_text(item.evidence_quote)}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


# Parses JSON text and returns a list, falling back safely when parsing fails.
def _load_json_list(raw_json: str) -> list:
    # Attempts JSON parsing so invalid JSON can be handled instead of crashing export.
    try:
        # Converts the JSON string from the database into Python data.
        loaded = json.loads(raw_json)
    # If the stored text is not valid JSON, return a safe empty list.
    except json.JSONDecodeError:
        # Falls back to no items instead of failing the whole Markdown export.
        return []

    # Returns parsed data only when it is a list; otherwise uses an empty list.
    return loaded if isinstance(loaded, list) else []


# Formats decision-like or risk-like items with their evidence quotes as Markdown lines.
def _format_evidence_items(items: list, text_key: str) -> list[str]:
    # Shows a clear fallback when the section has no decision or risk items.
    if not items:
        # Returns a readable Markdown bullet instead of leaving the section blank.
        return ["- None recorded."]

    # Collects formatted Markdown lines for each valid evidence-backed item.
    lines = []
    # Processes each decision or risk item one at a time.
    for item in items:
        # Skips malformed entries that are not dictionary-shaped.
        if not isinstance(item, dict):
            # Moves on to the next item without trying to format invalid data.
            continue

        # Reads and cleans the item's main decision or risk text.
        text = _safe_text(item.get(text_key, ""))
        evidence = _safe_text(item.get("evidence_quote", ""))
        if not text:
            continue

        lines.append(f"- {text}")
        if evidence:
            lines.append(f"  Evidence: {evidence}")

    return lines or ["- None recorded."]


def _format_plain_list(items: list) -> list[str]:
    lines = [f"- {_safe_text(item)}" for item in items if _safe_text(item)]
    return lines or ["- None recorded."]


# Converts any value into clean single-line text for Markdown output.
def _safe_text(value: object) -> str:
    # Handles missing values, removes line breaks, and trims outer whitespace.
    return str(value or "").replace("\n", " ").strip()


def _table_text(value: object) -> str:
    return _safe_text(value).replace("|", "\\|")
