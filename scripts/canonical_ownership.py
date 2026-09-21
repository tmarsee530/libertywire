#!/usr/bin/env python3
"""Deterministic canonical ownership for current Rally Point timelines.

History is intentionally retained.  This module decides which retained record
is authoritative in the current publication and assigns every durable material
update to exactly one published owner.  It never deletes or redirects history.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

try:
    from event_identity import compare as compare_events, content_kinds
    from timeline_intelligence import commentary_only, current_status
except ModuleNotFoundError:
    from scripts.event_identity import compare as compare_events, content_kinds
    from scripts.timeline_intelligence import commentary_only, current_status


def parse_dt(value):
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.max.replace(tzinfo=timezone.utc)


def update_ids(record):
    return frozenset(str(item.get("id")) for item in record.get("updates", []) if item.get("id"))


def event_titles(record):
    values = [record.get("current_title"), (record.get("current_status") or {}).get("summary")]
    values.extend(item.get("label") for item in record.get("updates", []))
    return [str(value) for value in values if value]


def identity_evidence(left, right):
    matches = [compare_events(a, b) for a in event_titles(left)[:4] for b in event_titles(right)[:4]]
    return max(matches, key=lambda item: item.confidence) if matches else compare_events("", "")


def duplicate_evidence(left, right):
    """Return high-confidence current-duplicate evidence, or None.

    Multiple identical durable updates are strong deterministic evidence. A
    single shared update is not: legacy leakage can place one update in two
    otherwise unrelated timelines. Single-update duplicates therefore require
    positive event-identity evidence before canonical ownership is collapsed.
    A near-identical set likewise requires a strong event-frame match.
    """
    left_ids, right_ids = update_ids(left), update_ids(right)
    if not left_ids or not right_ids:
        return None
    overlap = len(left_ids & right_ids)
    coefficient = overlap / max(1, min(len(left_ids), len(right_ids)))
    union_ratio = overlap / max(1, len(left_ids | right_ids))
    match = identity_evidence(left, right)
    if left_ids == right_ids:
        if overlap >= 2 or (match.same_event and match.confidence >= .70):
            return {"reason": "identical_material_update_set", "overlap": overlap, "overlap_coefficient": 1.0, "event_confidence": match.confidence}
        return None
    if overlap >= 2 and coefficient >= .80 and union_ratio >= .60 and match.same_event and match.confidence >= .78:
        return {"reason": "near_identical_material_update_set", "overlap": overlap, "overlap_coefficient": round(coefficient, 3), "event_confidence": match.confidence}
    return None


def owner_rank(record, current_ids):
    """Rank established ownership without using generation recency.

    An active continuity signal wins first, followed by established source
    breadth and the earliest durable first_seen.  The ID is the final stable
    tie-breaker.
    """
    first = parse_dt(record.get("first_seen"))
    first_rank = -first.timestamp() if first.year < 9999 else float("-inf")
    return (
        int(record.get("max_source_family_count", 0) or 0),
        int(record.get("max_source_count", 0) or 0),
        first_rank,
        int(record.get("id") in current_ids),
        str(record.get("id") or ""),
    )


def canonical_groups(records, current_ids):
    """Return deterministic duplicate groups that touch current publication."""
    by_id = {str(item.get("id")): item for item in records if item.get("id")}
    ids = list(by_id)
    parent = {sid: sid for sid in ids}
    evidence = {}

    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left, right):
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)

    owners = defaultdict(set)
    for sid, record in by_id.items():
        for update_id in update_ids(record):
            owners[update_id].add(sid)
    pairs = {tuple(sorted((left, right))) for group in owners.values() for left in group for right in group if left < right}
    for left, right in sorted(pairs):
        if left not in current_ids and right not in current_ids:
            continue
        result = duplicate_evidence(by_id[left], by_id[right])
        if result:
            evidence[(left, right)] = result
            union(left, right)

    grouped = defaultdict(list)
    for sid in ids:
        grouped[find(sid)].append(sid)
    result = []
    for members in grouped.values():
        if len(members) < 2:
            continue
        owner = max((by_id[sid] for sid in members), key=lambda item: owner_rank(item, current_ids))
        pair_evidence = [value for pair, value in evidence.items() if set(pair) <= set(members)]
        result.append({
            "owner_id": str(owner["id"]),
            "timeline_ids": sorted(members),
            "suppressed_ids": sorted(set(members) - {str(owner["id"])}),
            "reason": "identical_material_update_set" if any(x["reason"] == "identical_material_update_set" for x in pair_evidence) else "near_identical_material_update_set",
            "evidence": pair_evidence,
        })
    return sorted(result, key=lambda item: item["owner_id"])


def ownership_map(records, current_ids):
    aliases = {}
    groups = canonical_groups(records, current_ids)
    for group in groups:
        for sid in group["suppressed_ids"]:
            aliases[sid] = group["owner_id"]
    return aliases, groups


def update_owner(record, update, current_ids):
    label = str(update.get("label") or update.get("source_title") or "")
    matches = [compare_events(label, title) for title in event_titles(record)[:4]]
    match = max(matches, key=lambda item: item.confidence) if matches else compare_events("", "")
    other_updates = [item for item in record.get("updates", []) if item.get("id") != update.get("id")]
    coherent = sum(bool(compare_events(label, str(item.get("label") or "")).same_event) for item in other_updates)
    rank = owner_rank(record, current_ids)
    return (int(match.same_event), round(match.confidence, 3), coherent, *rank)


def enforce_unique_updates(records, current_ids):
    """Return publication copies with exactly one owner per update ID."""
    copies = [{**record, "updates": [dict(item) for item in record.get("updates", [])]} for record in records]
    purity_decisions = []
    for record in copies:
        record_kinds = content_kinds(record.get("current_title"))
        kept = []
        for update in record.get("updates", []):
            label = str(update.get("label") or update.get("source_title") or "")
            update_kinds = content_kinds(label)
            reason = None
            if commentary_only(label):
                reason = "reaction_or_commentary"
            elif record_kinds and update_kinds and record_kinds.isdisjoint(update_kinds):
                reason = "incompatible_content_kind"
            if reason:
                purity_decisions.append({"timeline_id": str(record.get("id")), "material_update_id": str(update.get("id")), "reason": reason})
            else:
                kept.append(update)
        anchor = str(record.get("current_title") or (record.get("current_status") or {}).get("summary") or "")
        anchor_updates = [item for item in kept if compare_events(anchor, str(item.get("label") or item.get("source_title") or "")).same_event]
        if anchor and anchor_updates:
            coherent = []
            for update in kept:
                label = str(update.get("label") or update.get("source_title") or "")
                match = compare_events(anchor, label)
                if match.same_event or match.confidence < .30:
                    coherent.append(update)
                    continue
                purity_decisions.append({
                    "timeline_id": str(record.get("id")),
                    "material_update_id": str(update.get("id")),
                    "reason": "event_identity_mismatch",
                    "identity_reason": match.reason,
                    "identity_confidence": match.confidence,
                })
            if coherent:
                kept = coherent
        if kept:
            record["updates"] = kept
    claims = defaultdict(list)
    for record in copies:
        for update in record.get("updates", []):
            if update.get("id"):
                claims[str(update["id"])].append((record, update))
    decisions = []
    for update_id, candidates in sorted(claims.items()):
        if len(candidates) < 2:
            continue
        owner_record, _ = max(candidates, key=lambda pair: update_owner(pair[0], pair[1], current_ids))
        owner_id = str(owner_record.get("id"))
        removed = []
        for record, _update in candidates:
            if str(record.get("id")) == owner_id:
                continue
            record["updates"] = [item for item in record.get("updates", []) if str(item.get("id")) != update_id]
            removed.append(str(record.get("id")))
        decisions.append({"material_update_id": update_id, "owner_id": owner_id, "removed_from": sorted(removed), "reason": "strongest_event_coherence"})
    for record in copies:
        record["material_update_count"] = len(record.get("updates", []))
        record["current_status"] = current_status(record.get("updates", []))
    return copies, decisions, purity_decisions


def violations(records):
    owners = defaultdict(list)
    sets = defaultdict(list)
    for record in records:
        sid = str(record.get("id"))
        ids = update_ids(record)
        if ids:
            sets[tuple(sorted(ids))].append(sid)
        for update_id in ids:
            owners[update_id].append(sid)
    return {
        "shared_material_update_ids": {key: sorted(value) for key, value in owners.items() if len(value) > 1},
        "identical_material_update_sets": [sorted(value) for value in sets.values() if len(value) > 1],
    }
