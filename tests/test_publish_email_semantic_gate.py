from scripts.publish_email_events import eligible_events


def test_email_events_skip_high_severity_timeline():
    history = {"storylines": []}
    manifest = {"ids": ["bad"]}
    audit = {"timelines": {"bad": {"findings": [{"severity": "high", "type": "possible_cross_event_update"}]}}}
    assert eligible_events(history, manifest, semantic_audit=audit) == []
