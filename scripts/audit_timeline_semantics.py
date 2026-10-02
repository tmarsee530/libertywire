#!/usr/bin/env python3
"""Audit published timeline state for semantic quality problems."""
from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from event_identity import compare
    from timeline_intelligence import commentary_only, fact_tokens
except ModuleNotFoundError:
    from scripts.event_identity import compare
    from scripts.timeline_intelligence import commentary_only, fact_tokens

ROOT = Path(__file__).resolve().parents[1]
STATE_INDEX = ROOT / "data" / "timeline_state_index.json"
REPORT = ROOT / "data" / "timeline_semantic_audit.json"


def _similarity(left, right):
    left, right = set(left), set(right)
    if not left or not right:
        return 0.0
    overlap = len(left & right)
    return max(overlap / max(1, len(left | right)), overlap / max(1, min(len(left), len(right))))


def _normalized(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().rstrip(".!?…").lower()


def audit_timeline(timeline_id, timeline):
    developments = timeline.get("developments") or []
    title = str(timeline.get("title") or "")
    current = str(timeline.get("currentStatus") or "")
    findings = []
    if developments:
        latest = developments[0]
        latest_label = str(latest.get("label") or "")
        if _normalized(current) != _normalized(latest_label):
            findings.append({"type":"current_status_mismatch","severity":"high","latest_update_id":latest.get("id"),"current_status":current,"latest_label":latest_label})
        if commentary_only(latest_label):
            findings.append({"type":"commentary_as_current_status","severity":"high","latest_update_id":latest.get("id"),"label":latest_label})
    for development in developments:
        label = str(development.get("label") or "")
        if not label or not title or _normalized(label) == _normalized(title):
            continue
        identity = compare(title, label)
        token_similarity = _similarity(fact_tokens(title), fact_tokens(label))
        # Low overlap is also evidence for review. Requiring a minimum matching
        # confidence hid the most obvious contamination (entirely unrelated
        # headlines). This audit flags uncertainty; it never deletes updates.
        if not identity.same_event and token_similarity < 0.42:
            findings.append({"type":"possible_cross_event_update","severity":"high" if identity.confidence >= 0.6 else "medium","update_id":development.get("id"),"label":label,"identity_reason":identity.reason,"identity_confidence":round(identity.confidence,3),"token_similarity":round(token_similarity,3)})
    for index, left in enumerate(developments):
        left_label = str(left.get("label") or "")
        left_tokens = fact_tokens(left_label)
        for right in developments[index + 1:]:
            right_label = str(right.get("label") or "")
            similarity = _similarity(left_tokens, fact_tokens(right_label))
            if similarity < 0.72:
                continue
            identity = compare(left_label, right_label)
            if identity.same_event:
                findings.append({"type":"possible_duplicate_development","severity":"medium","update_ids":[left.get("id"),right.get("id")],"labels":[left_label,right_label],"token_similarity":round(similarity,3),"identity_confidence":round(identity.confidence,3)})
    return findings


def build_report(payload):
    timelines = payload.get("timelines") or {}
    audited, counts = {}, {}
    for timeline_id, timeline in timelines.items():
        findings = audit_timeline(timeline_id, timeline)
        if findings:
            audited[timeline_id] = {"title":timeline.get("title"),"url":timeline.get("url"),"findings":findings}
            for finding in findings:
                counts[finding["type"]] = counts.get(finding["type"], 0) + 1
    high = sum(1 for item in audited.values() for finding in item["findings"] if finding["severity"] == "high")
    medium = sum(1 for item in audited.values() for finding in item["findings"] if finding["severity"] == "medium")
    return {"generated_from":payload.get("generated_at"),"schema_version":1,"timeline_count":len(timelines),"timelines_with_findings":len(audited),"high_severity_findings":high,"medium_severity_findings":medium,"finding_counts":counts,"status":"REVIEW" if high else "HEALTHY","timelines":audited}


def main():
    payload = json.loads(STATE_INDEX.read_text())
    report = build_report(payload)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("timeline_count","timelines_with_findings","high_severity_findings","medium_severity_findings","status")}, indent=2))


if __name__ == "__main__":
    main()
