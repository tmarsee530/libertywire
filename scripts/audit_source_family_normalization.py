#!/usr/bin/env python3
"""Audit published storyline source-family labels against the shared normalization map.

Read-only diagnostic: this never changes clustering or publication thresholds. It exposes
where storyline construction still disagrees with the canonical publisher-family map so
corroboration KPIs cannot silently overstate independent reporting.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

try:
    from source_families import family
except ModuleNotFoundError:
    from scripts.source_families import family

ROOT = Path(__file__).resolve().parents[1]
STORYLINES = ROOT / "data" / "storylines.json"
OUT = ROOT / "data" / "source_family_audit.json"


def main() -> None:
    payload = json.loads(STORYLINES.read_text(encoding="utf-8"))
    mismatches = []
    affected_storylines = set()
    corrected_multi_family = 0
    observed_multi_family = 0

    for storyline in payload.get("storylines", []):
        sid = str(storyline.get("id") or "")
        coverage = storyline.get("coverage", [])
        observed = {str(x.get("source_family") or "") for x in coverage if x.get("source_family")}
        corrected = {family(x.get("source")) for x in coverage if x.get("source")}
        if len(observed) >= 2:
            observed_multi_family += 1
        if len(corrected) >= 2:
            corrected_multi_family += 1
        for item in coverage:
            source = item.get("source")
            if not source:
                continue
            current = str(item.get("source_family") or "")
            expected = family(source)
            if current != expected:
                affected_storylines.add(sid)
                mismatches.append({"storyline_id": sid, "source": source, "current_family": current, "expected_family": expected})

    counts = Counter(x["source"] for x in mismatches)
    report = {
        "storylines_checked": len(payload.get("storylines", [])),
        "affected_storyline_count": len(affected_storylines),
        "mismatch_count": len(mismatches),
        "observed_multi_family_in_published_slice": observed_multi_family,
        "corrected_multi_family_in_published_slice": corrected_multi_family,
        "top_mismatched_sources": counts.most_common(20),
        "mismatches": mismatches[:200],
        "note": "Diagnostic only. Shared normalization must be consumed by storyline construction before corrected counts become production KPIs.",
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Publisher-family audit: {len(mismatches)} mismatches across {len(affected_storylines)} storylines; published-slice multi-family {observed_multi_family} -> {corrected_multi_family}")


if __name__ == "__main__":
    main()
