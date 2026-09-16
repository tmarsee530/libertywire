#!/usr/bin/env python3
"""Build a controlled publication queue from verified-story candidates.

This stage deliberately does NOT write article prose or publish Briefs. It creates the
contract a later verifier/writer must satisfy before a candidate may become a permanent
Rally Point report. Keeping this deterministic prevents unverified political/current-news
claims from being auto-published merely because they entered the writer queue.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WRITER_QUEUE = DATA / "writer_queue.json"
BRIEFS = DATA / "briefs.json"
OUT = DATA / "publication_queue.json"


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def main() -> None:
    writer = load(WRITER_QUEUE, {"candidates": []})
    briefs = load(BRIEFS, {"briefs": []})
    published_storylines = {
        str(b.get("storyline_id")) for b in briefs.get("briefs", []) if b.get("storyline_id")
    }

    items = []
    for candidate in writer.get("candidates", []):
        sid = str(candidate.get("storyline_id") or "").strip()
        if not sid or sid in published_storylines:
            continue
        if candidate.get("risk_flags"):
            continue
        if int(candidate.get("source_count") or 0) < 2:
            continue
        if int(candidate.get("source_family_count") or 0) < 2:
            continue

        items.append({
            "storyline_id": sid,
            "title": candidate.get("title", ""),
            "status": "needs_verification",
            "priority_score": candidate.get("priority_score"),
            "importance_score": candidate.get("importance_score"),
            "source_count": candidate.get("source_count"),
            "source_family_count": candidate.get("source_family_count"),
            "source_families": candidate.get("source_families", []),
            "coverage": candidate.get("coverage", []),
            "publication_gate": {
                "fresh_source_check": False,
                "material_claims_verified": False,
                "disputed_claims_attributed": False,
                "allegations_distinguished_from_facts": False,
                "material_uncertainty_stated": False,
                "source_links_preserved": False,
                "image_rights_or_provenance_verified": False,
                "ready_to_publish": False
            },
            "required_brief_metadata": {
                "storyline_id": sid,
                "importance_score": candidate.get("importance_score"),
                "source_count": candidate.get("source_count"),
                "source_families": candidate.get("source_families", []),
                "image_url": None,
                "image_alt": None,
                "image_credit": None,
                "image_source_url": None,
                "image_provenance": None,
                "image_type": None
            },
            "note": "Verification queue only. Do not publish until every publication_gate field is true."
        })

    items.sort(key=lambda x: (float(x.get("importance_score") or 0), float(x.get("priority_score") or 0)), reverse=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "policy": {
            "automatic_publication": False,
            "purpose": "Bridge discovery to verified original reporting without treating queue admission as factual verification.",
            "image_required": True,
            "ordering": "editorial importance first; queue priority second"
        },
        "candidate_count": len(items),
        "candidates": items
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Built controlled publication queue with {len(items)} candidate(s)")


if __name__ == "__main__":
    main()
