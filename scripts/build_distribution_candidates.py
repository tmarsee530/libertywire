#!/usr/bin/env python3
"""Build a small, neutral queue of Rally Point timelines worth promoting externally.

This does not post anywhere. It identifies only fresh, materially updated,
well-corroborated timelines so distribution can stay selective.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "history.json"
MANIFEST = ROOT / "data" / "published_timelines.json"
OUT = ROOT / "data" / "distribution_candidates.json"
BASE = "https://rallypointnews.com"
MAX_AGE_HOURS = 12
MAX_CANDIDATES = 12


def parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def clean(value):
    return " ".join(str(value or "").split())


def candidate(record, now):
    sid = str(record.get("id") or "")
    if not sid:
        return None

    updated = parse_dt(record.get("last_seen"))
    if not updated:
        return None

    age_hours = max(0.0, (now - updated).total_seconds() / 3600)
    if age_hours > MAX_AGE_HOURS:
        return None

    current = record.get("current_status") or {}
    classification = clean(current.get("classification") or "UPDATE").upper()
    status = clean(record.get("status") or "").lower()
    family_count = int(record.get("current_source_family_count", 0) or 0)
    material_count = int(record.get("material_update_count", 0) or 0)
    risk_flags = list(record.get("risk_flags") or [])

    # Promotion is intentionally stricter than publication.
    # Minor/context-only changes never enter the distribution queue.
    eligible = (
        family_count >= 3
        and material_count >= 2
        and (
            classification in {"BREAKING", "MAJOR DEVELOPMENT"}
            or status in {"breaking", "hot"}
            or (classification == "UPDATE" and family_count >= 4 and material_count >= 3)
        )
    )
    if not eligible:
        return None

    # Sensitive claims need extra corroboration before a candidate is marked ready.
    needs_manual_review = bool(risk_flags and family_count < 4)
    if classification == "BREAKING":
        priority = "urgent"
    elif classification == "MAJOR DEVELOPMENT" or status == "hot":
        priority = "high"
    else:
        priority = "normal"

    title = clean(record.get("current_title") or "Developing story")
    summary = clean(current.get("summary"))
    url = f"{BASE}/stories/{sid}/"
    copy = title
    if summary and summary.lower() not in title.lower():
        remaining = 220 - len(url)
        if remaining > len(title) + 6:
            copy = f"{title} — {summary}"
    if len(copy) > 220:
        copy = copy[:217].rstrip() + "…"

    reasons = []
    if classification in {"BREAKING", "MAJOR DEVELOPMENT"}:
        reasons.append(classification.lower().replace(" ", "_"))
    if family_count >= 4:
        reasons.append("broad_independent_coverage")
    if status in {"breaking", "hot"}:
        reasons.append(f"status_{status}")

    return {
        "timeline_id": sid,
        "url": url,
        "title": title,
        "current_summary": summary,
        "classification": classification,
        "status": status,
        "priority": priority,
        "updated_at": record.get("last_seen"),
        "age_hours": round(age_hours, 2),
        "source_family_count": family_count,
        "material_update_count": material_count,
        "promotion_ready": not needs_manual_review,
        "needs_manual_review": needs_manual_review,
        "risk_flags": risk_flags,
        "reason_codes": reasons,
        "suggested_post": f"{copy}\n\n{url}",
    }


def main():
    now = datetime.now(timezone.utc)
    history = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {"storylines": []}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"ids": []}
    published = {str(x) for x in manifest.get("ids", [])}

    items = []
    for record in history.get("storylines", []):
        if str(record.get("id")) not in published:
            continue
        item = candidate(record, now)
        if item:
            items.append(item)

    order = {"urgent": 3, "high": 2, "normal": 1}
    items.sort(
        key=lambda x: (
            order.get(x["priority"], 0),
            x["source_family_count"],
            x["material_update_count"],
            x["updated_at"] or "",
        ),
        reverse=True,
    )
    items = items[:MAX_CANDIDATES]

    payload = {
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "auto_post_enabled": False,
        "policy": {
            "purpose": "selective distribution of materially changed, well-corroborated live timelines",
            "minor_refreshes_suppressed": True,
            "context_only_suppressed": True,
            "ideology_used_in_selection": False,
            "sensitive_claims_require_extra_corroboration": True,
            "max_age_hours": MAX_AGE_HOURS,
        },
        "candidate_count": len(items),
        "candidates": items,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Built {len(items)} selective distribution candidates")


if __name__ == "__main__":
    main()
