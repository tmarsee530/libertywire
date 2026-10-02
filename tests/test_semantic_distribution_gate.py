import json

from scripts import apply_semantic_distribution_gate as gate
from scripts.publish_email_events import blocked_timelines


def test_blocked_timelines_only_uses_high_severity():
    audit = {"timelines": {
        "bad": {"findings": [{"severity": "high", "type": "possible_cross_event_update"}]},
        "review": {"findings": [{"severity": "medium", "type": "possible_duplicate_development"}]},
    }}
    assert blocked_timelines(audit) == {"bad"}


def test_distribution_gate_removes_high_severity_candidate(tmp_path, monkeypatch):
    audit_path = tmp_path / "audit.json"
    queue_path = tmp_path / "queue.json"
    audit_path.write_text(json.dumps({"timelines": {
        "bad": {"findings": [{"severity": "high", "type": "commentary_as_current_status"}]}
    }}))
    queue_path.write_text(json.dumps({
        "policy": {},
        "candidate_count": 2,
        "candidates": [
            {"timeline_id": "good", "title": "Good"},
            {"timeline_id": "bad", "title": "Bad"},
        ],
    }))
    monkeypatch.setattr(gate, "AUDIT", audit_path)
    monkeypatch.setattr(gate, "QUEUE", queue_path)
    gate.main()
    result = json.loads(queue_path.read_text())
    assert [item["timeline_id"] for item in result["candidates"]] == ["good"]
    assert result["semantic_quality_blocked_count"] == 1
    assert result["policy"]["high_severity_semantic_findings_suppressed"] is True
