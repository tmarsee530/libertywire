#!/usr/bin/env python3
"""Build a small, neutral queue of Rally Point timelines worth promoting externally.

This does not post anywhere. It identifies only fresh, materially updated,
well-corroborated timelines so distribution can stay selective, measurable,
and free of duplicate promotion for the same underlying event.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "history.json"
MANIFEST = ROOT / "data" / "published_timelines.json"
OUT = ROOT / "data" / "distribution_candidates.json"
BASE = "https://rallypointnews.com"
MAX_AGE_HOURS = 12
MAX_CANDIDATES = 12

STOP = {
    "this","that","with","from","after","about","into","over","news","live",
    "latest","breaking","update","updates","report","reports","says","said",
    "the","and","for","are","was","were","has","have","had","will","would",
    "trump","president","white","house",
}


def parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def clean(value):
    return " ".join(str(value or "").split())


def title_tokens(value):
    return {
        token
        for token in re.findall(r"[a-z0-9']{3,}", clean(value).lower())
        if token not in STOP
    }


def same_event(left, right):
    """Conservative promotion-level dedupe.

    This does not merge newsroom timelines. It only prevents social distribution
    from pushing several URLs that plainly describe the same event.
    """
    a = title_tokens(left.get("title"))
    b = title_tokens(right.get("title"))
    if len(a) < 2 or len(b) < 2:
        return False
    overlap = len(a & b)
    containment = overlap / max(1, min(len(a), len(b)))
    jaccard = overlap / max(1, len(a | b))
    return overlap >= 3 and (containment >= 0.58 or jaccard >= 0.46)


def tracked_url(sid, source):
    query = urlencode({
        "utm_source": source,
        "utm_medium": "social",
        "utm_campaign": "live_timeline",
        "utm_content": sid,
    })
    return f"{BASE}/stories/{sid}/?{query}"


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

    needs_manual_review = bool(risk_flags and family_count < 4)
    if classification == "BREAKING":
        priority = "urgent"
    elif classification == "MAJOR DEVELOPMENT" or status == "hot":
        priority = "high"
    else:
        priority = "normal"

    title = clean(record.get("current_title") or "Developing story")
    summary = clean(current.get("summary"))
    canonical_url = f"{BASE}/stories/{sid}/"

    # Social copy should add information, not repeat the same sentence twice.
    copy = title
    if (
        summary
        and summary.lower() != title.lower()
        and summary.lower() not in title.lower()
        and title.lower() not in summary.lower()
    ):
        remaining = 220 - len(canonical_url)
        if remaining > len(title) + 12:
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

    x_url = tracked_url(sid, "x")
    facebook_url = tracked_url(sid, "facebook")

    return {
        "timeline_id": sid,
        "url": canonical_url,
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
        "x_url": x_url,
        "facebook_url": facebook_url,
        "suggested_post_x": f"{copy}\n\n{x_url}",
        "suggested_post_facebook": f"{copy}\n\nFollow the live timeline: {facebook_url}",
    }


def dedupe_events(items):
    """Keep the strongest promotion candidate for each apparent event."""
    selected = []
    suppressed = []
    for item in items:
        match = next((kept for kept in selected if same_event(item, kept)), None)
        if match:
            suppressed.append({
                "timeline_id": item["timeline_id"],
                "duplicate_of": match["timeline_id"],
                "title": item["title"],
                "reason": "same_event_distribution_dedupe",
            })
            continue
        selected.append(item)
    return selected, suppressed


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

    items, suppressed = dedupe_events(items)
    items = items[:MAX_CANDIDATES]

    payload = {
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "auto_post_enabled": False,
        "policy": {
            "purpose": "selective distribution of materially changed, well-corroborated live timelines",
            "minor_refreshes_suppressed": True,
            "context_only_suppressed": True,
            "same_event_duplicate_promotion_suppressed": True,
            "ideology_used_in_selection": False,
            "sensitive_claims_require_extra_corroboration": True,
            "measurable_social_links": True,
            "max_age_hours": MAX_AGE_HOURS,
        },
        "candidate_count": len(items),
        "suppressed_duplicate_count": len(suppressed),
        "candidates": items,
        "suppressed_duplicates": suppressed,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Built {len(items)} selective distribution candidates; suppressed {len(suppressed)} duplicate event promotions")


if __name__ == "__main__":
    main()
