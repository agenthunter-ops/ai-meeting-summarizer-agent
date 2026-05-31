import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client(monkeypatch):
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def fake_summarize_transcript(transcript_text):
        return {
            "executive_summary": "The team agreed on the POC plan.",
            "key_decisions": [
                {
                    "decision": "Create the POC.",
                    "evidence_quote": "Abhishek, please create the POC by Friday.",
                }
            ],
            "action_items": [
                {
                    "owner": "Abhishek",
                    "task": "Create the POC.",
                    "due_date": "Friday",
                    "priority": "medium",
                    "evidence_quote": "Abhishek, please create the POC by Friday.",
                    "confidence": "high",
                }
            ],
            "risks": [],
            "follow_up_questions": [],
        }

    monkeypatch.setattr("app.main.summarize_transcript", fake_summarize_transcript)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def create_sample_meeting(client):
    response = client.post(
        "/meetings",
        json={
            "title": "Smart Docs Weekly Sync",
            "participants": "Neha, Abhishek",
            "transcript_text": (
                "Neha: Abhishek, please create the POC by Friday. "
                "Abhishek: I will do it."
            ),
        },
    )
    assert response.status_code == 200
    return response.json()


def test_create_meeting_returns_summary_and_validated_action_items(client):
    meeting = create_sample_meeting(client)

    assert meeting["title"] == "Smart Docs Weekly Sync"
    assert meeting["status"] == "completed"
    assert meeting["summary"]["executive_summary"] == "The team agreed on the POC plan."
    assert meeting["summary"]["key_decisions"][0]["decision"] == "Create the POC."
    assert meeting["action_items"][0]["owner"] == "Abhishek"
    assert meeting["action_items"][0]["confidence"] == 0.9


def test_get_meetings_and_get_meeting_detail(client):
    created = create_sample_meeting(client)

    list_response = client.get("/meetings")
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == created["id"]

    detail_response = client.get(f"/meetings/{created['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["title"] == "Smart Docs Weekly Sync"


def test_update_action_item_status(client):
    created = create_sample_meeting(client)
    action_item_id = created["action_items"][0]["id"]

    response = client.patch(
        f"/action-items/{action_item_id}",
        json={"status": "done"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "done"


def test_update_action_item_rejects_invalid_status(client):
    created = create_sample_meeting(client)
    action_item_id = created["action_items"][0]["id"]

    response = client.patch(
        f"/action-items/{action_item_id}",
        json={"status": "closed"},
    )

    assert response.status_code == 400


def test_get_meeting_action_items_can_filter_by_owner(client):
    created = create_sample_meeting(client)

    all_response = client.get(f"/meetings/{created['id']}/action-items")
    assert all_response.status_code == 200
    assert len(all_response.json()) == 1

    owner_response = client.get(
        f"/meetings/{created['id']}/action-items",
        params={"owner": "Abhishek"},
    )
    assert owner_response.status_code == 200
    assert len(owner_response.json()) == 1
    assert owner_response.json()[0]["owner"] == "Abhishek"

    missing_owner_response = client.get(
        f"/meetings/{created['id']}/action-items",
        params={"owner": "Jeevan"},
    )
    assert missing_owner_response.status_code == 200
    assert missing_owner_response.json() == []


def test_export_meeting_returns_markdown(client):
    created = create_sample_meeting(client)

    response = client.get(f"/meetings/{created['id']}/export")

    assert response.status_code == 200
    assert response.json()["meeting_id"] == created["id"]
    assert "# Smart Docs Weekly Sync" in response.json()["markdown"]
    assert "Abhishek, please create the POC by Friday." in response.json()["markdown"]


def test_get_unknown_meeting_returns_404(client):
    response = client.get("/meetings/999")

    assert response.status_code == 404


def test_recording_completed_webhook_creates_meeting(client):
    response = client.post(
        "/webhooks/recording-completed",
        json={
            "title": "Simulated Zoom Recording",
            "source_platform": "zoom",
            "recording_url": "https://example.com/recording.mp4",
            "transcript_text": (
                "Neha: Abhishek, please create the POC by Friday. "
                "Abhishek: I will do it."
            ),
        },
    )

    assert response.status_code == 200
    meeting = response.json()
    assert meeting["title"] == "Simulated Zoom Recording"
    assert meeting["source_type"] == "webhook:zoom"
    assert meeting["status"] == "completed"
    assert meeting["action_items"][0]["owner"] == "Abhishek"
