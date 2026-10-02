#!/usr/bin/env python3
"""Suppress external promotion of timelines with high-confidence semantic defects.

The semantic audit remains non-mutating for newsroom state. This gate only
changes the derived distribution queue, so questionable timelines can remain
published for inspection while they are prevented from being amplified.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "timeline_semantic_audit.json"
QUEUE = ROOT / "data" / "distribution_candidates.json"


def main():
    if not AUDIT.exists() or not QUEUE.exists():
        raise SystemExit("semantic audit and distribution queue must exist before gating")

    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))

    blocked = {}
    for timeline_id, item in (audit.get("timelines") or {}).items():
        high = [finding for finding in item.get("findings", []) if finding.get("severity") == "high"]
        if high:
            blocked[str(timeline_id)] = sorted({str(finding.get("type") or "semantic_quality_failure") for finding in high})

    kept = []
    suppressed = list(queue.get("suppressed_semantic_quality") or [])
    for candidate in queue.get("candidates") or []:
        timeline_id = str(candidate.get("timeline_id") or "")
        reasons = blocked.get(timeline_id)
        if reasons:
            suppressed.append({
                "timeline_id": timeline_id,
                "title": candidate.get("title"),
                "reason": "semantic_quality_gate",
                "finding_types": reasons,
            })
            continue
        kept.append(candidate)

    queue["candidates"] = kept
    queue["candidate_count"] = len(kept)
    queue["semantic_quality_gate_enabled"] = True
    queue["semantic_quality_blocked_count"] = len(suppressed)
    queue["suppressed_semantic_quality"] = suppressed
    queue.setdefault("policy", {})["high_severity_semantic_findings_suppressed"] = True
    QUEUE.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Semantic distribution gate kept {len(kept)} candidates; blocked {len(suppressed)}")


if __name__ == "__main__":
    main()
