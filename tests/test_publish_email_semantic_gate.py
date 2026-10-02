from datetime import datetime, timezone

from scripts.publish_email_events import eligible_events


def test_email_events_skip_high_severity_timeline():
    history = {
        "storylines": [
            {
                "id": "bad",
                "current_title": "Contaminated event",
                "updates": [
                    {
                        "id": "update-1",
                        "date": "2026-10-02T12:00:00Z",
                        "classification": "BREAKING",
                        "label": "A material development occurred",
                    }
                ],
            }
        ]
    }
    manifest = {"ids": ["bad"]}
    audit = {
        "timelines": {
            "bad": {
                "findings": [
                    {"severity": "high", "type": "possible_cross_event_update"}
                ]
            }
        }
    }
    now = datetime(2026, 10, 2, 16, 0, tzinfo=timezone.utc)
    assert eligible_events(history, manifest, now=now, semantic_audit=audit) == []


def test_email_events_keep_clean_timeline():
    history = {
        "storylines": [
            {
                "id": "good",
                "current_title": "Clean event",
                "updates": [
                    {
                        "id": "update-1",
                        "date": "2026-10-02T12:00:00Z",
                        "classification": "BREAKING",
                        "label": "A material development occurred",
                    }
                ],
            }
        ]
    }
    manifest = {"ids": ["good"]}
    now = datetime(2026, 10, 2, 16, 0, tzinfo=timezone.utc)
    events = eligible_events(history, manifest, now=now, semantic_audit={"timelines": {}})
    assert [event["timeline_id"] for event in events] == ["good"]
