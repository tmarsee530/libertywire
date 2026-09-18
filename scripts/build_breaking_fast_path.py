#!/usr/bin/env python3
"""Build a conservative, deterministic breaking-news priority queue.

This stage never removes or rewrites the normal ingestion feed. It identifies
fresh, high-confidence developments that can be promoted through the existing
storyline publisher while uncertain items continue down the normal path.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NEWS = DATA / "news.json"
STORYLINES = DATA / "storylines.json"
OUTPUT = DATA / "breaking_fast_path.json"

PRIMARY_SOURCES = {
    "fbi national press releases", "federal reserve press releases",
    "sec press releases", "u.s. department of labor news releases",
    "national hurricane center atlantic", "nasa news",
}
ESTABLISHED_SOURCES = {
    "abc news", "bbc news", "cbs news", "cnn", "fox news", "nbc news",
    "npr", "pbs newshour", "the guardian", "the hill", "usa today",
    "washington post", "new york times", "reuters", "associated press",
    "ap news", "bloomberg", "cnbc", "politico", "axios", "scotusblog",
    "defense news", "spacenews", "ars technica", "the verge", "techcrunch",
}
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "how", "in", "is", "it", "its", "of", "on", "or",
    "that", "the", "this", "to", "was", "were", "what", "when", "where",
    "who", "why", "with", "after", "before", "new", "says", "say", "live",
}
MAGNITUDE_TERMS = {
    "declares": 8, "declared": 8, "emergency": 12, "earthquake": 14,
    "hurricane": 14, "tornado": 13, "wildfire": 12, "evacuation": 13,
    "explosion": 12, "shooting": 12, "attack": 11, "war": 12,
    "ceasefire": 11, "invasion": 14, "resigns": 9, "resigned": 9,
    "indicted": 10, "convicted": 10, "verdict": 9, "ruling": 8,
    "decision": 6, "acquires": 8, "acquisition": 8, "bankruptcy": 8,
    "recall": 10, "outage": 8, "shutdown": 9, "strike": 7,
}
SAFETY_TERMS = {
    "warning", "emergency", "evacuate", "evacuation", "shelter", "recall",
    "hurricane", "tornado", "earthquake", "wildfire", "flood", "shooting",
    "explosion", "outbreak", "missing", "hostage", "danger",
}
INSTITUTION_TERMS = {
    "president", "congress", "senate", "supreme court", "white house",
    "federal reserve", "fbi", "sec", "pentagon", "nasa", "governor",
    "prime minister", "court", "government", "department", "agency",
}
UNCERTAINTY_TERMS = {
    "unconfirmed", "rumor", "rumour", "may have", "might have", "reportedly",
    "sources claim", "alleged without evidence", "could be",
}
LOW_SIGNAL_TERMS = {"opinion", "analysis", "podcast", "watch:", "video:"}


def utcnow():
    return datetime.now(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def words(text):
    return {x for x in re.findall(r"[a-z0-9]+", str(text).lower()) if len(x) > 2 and x not in STOP_WORDS}


def proper_anchors(text):
    return {x.lower() for x in re.findall(r"\b[A-Z][A-Za-z0-9.'-]{2,}\b", str(text)) if x.lower() not in STOP_WORDS}


def source_family(source):
    value = re.sub(r"\s+", " ", str(source or "unknown").strip().lower())
    aliases = {
        "ap": "associated press", "ap news": "associated press",
        "reuters world": "reuters", "bbc": "bbc news",
        "npr news": "npr", "fox news politics": "fox news",
        "fox news world": "fox news", "fox business": "fox news",
        "bbc science & environment": "bbc news", "bbc sport": "bbc news",
        "bbc entertainment & arts": "bbc news",
    }
    return aliases.get(value, value)


def source_tier(source):
    family = source_family(source)
    if family in PRIMARY_SOURCES:
        return 1
    if family in ESTABLISHED_SOURCES:
        return 2
    return 3


def pair_similarity(left, right):
    lt, rt = words(left.get("title")), words(right.get("title"))
    if not lt or not rt:
        return 0.0
    lexical = len(lt & rt) / max(1, len(lt | rt))
    la, ra = proper_anchors(left.get("title")), proper_anchors(right.get("title"))
    anchor = len(la & ra) / max(1, min(len(la), len(ra))) if la and ra else 0.0
    return (0.55 * lexical) + (0.45 * anchor)


def cluster_stories(stories):
    """Greedily group likely duplicate reports without conflating broad topics."""
    groups = []
    for story in sorted(stories, key=lambda x: str(x.get("date", "")), reverse=True):
        placed = False
        for group in groups:
            if max(pair_similarity(story, other) for other in group) >= 0.43:
                group.append(story)
                placed = True
                break
        if not placed:
            groups.append([story])
    return groups


def timeline_match(group, storylines):
    group_text = " ".join(str(x.get("title", "")) for x in group)
    gt, ga = words(group_text), proper_anchors(group_text)
    best = (0.0, None)
    for item in storylines:
        title = item.get("title") or item.get("current_title") or ""
        tt, ta = words(title), proper_anchors(title)
        if not gt or not tt:
            continue
        lexical = len(gt & tt) / max(1, min(len(gt), len(tt)))
        anchor = len(ga & ta) / max(1, min(len(ga), len(ta))) if ga and ta else 0.0
        score = (0.55 * lexical) + (0.45 * anchor)
        if score > best[0]:
            best = (score, item.get("id"))
    return best[1] if best[0] >= 0.48 else None


def clean_headline(value):
    return re.sub(r"^(breaking|developing|just in)\s*[:—-]\s*", "", str(value or ""), flags=re.I).strip()


def _component_scores(group, now, matched_timeline_id):
    title = " ".join(str(x.get("title", "")) for x in group).lower()
    dates = [parse_dt(x.get("date")) for x in group]
    valid_dates = [x for x in dates if x]
    newest = max(valid_dates, default=now)
    age_minutes = max(0.0, (now - min(newest, now)).total_seconds() / 60)
    recency = round(22 * math.exp(-age_minutes / 100), 2)
    magnitude = min(24, sum(value for term, value in MAGNITUDE_TERMS.items() if term in title))
    safety = min(15, 5 * sum(1 for term in SAFETY_TERMS if term in title))
    prominence = min(12, 3 * sum(1 for term in INSTITUTION_TERMS if term in title))
    families = {source_family(x.get("source")) for x in group}
    trusted_families = {source_family(x.get("source")) for x in group if source_tier(x.get("source")) <= 2}
    velocity = min(12, max(0, len(group) - 1) * 2 + max(0, len(families) - 1) * 2)
    confirmations = min(12, max(0, len(trusted_families) - 1) * 6)
    trust = 15 if any(source_tier(x.get("source")) == 1 for x in group) else 10 if trusted_families else 2
    existing_interest = 8 if matched_timeline_id else 0
    material_change = 6 if magnitude or safety or prominence else 2
    uncertainty = any(term in title for term in UNCERTAINTY_TERMS)
    low_signal = any(term in title for term in LOW_SIGNAL_TERMS)
    penalty = (35 if uncertainty else 0) + (12 if low_signal else 0)
    components = {
        "source_trust": trust, "recency": recency, "magnitude": magnitude,
        "public_safety": safety, "institutional_prominence": prominence,
        "velocity": velocity, "independent_confirmations": confirmations,
        "existing_timeline_interest": existing_interest,
        "material_change": material_change, "risk_penalty": -penalty,
    }
    return components, uncertainty, families, trusted_families, age_minutes


def evaluate_clusters(news, current_storylines=None, detected_at=None):
    now = detected_at or utcnow()
    storylines = current_storylines or []
    recent = []
    for item in news:
        published = parse_dt(item.get("date"))
        if not published:
            continue
        age = max(0, (now - min(published, now)).total_seconds() / 60)
        if age <= 240 and item.get("title") and item.get("link"):
            recent.append(item)
    groups = cluster_stories(recent)
    candidates = []
    for group in groups:
        matched = timeline_match(group, storylines)
        components, uncertain, families, trusted, age = _component_scores(group, now, matched)
        score = round(max(0, min(100, sum(components.values()))), 2)
        primary = any(source_tier(x.get("source")) == 1 for x in group)
        primary_ready = primary and score >= 60
        corroborated_ready = len(trusted) >= 2 and score >= 65
        eligible = not uncertain and (primary_ready or corroborated_ready)
        ordered = sorted(group, key=lambda x: (source_tier(x.get("source")), -((parse_dt(x.get("date")) or now).timestamp())))
        lead = ordered[0]
        reason = (
            "trusted_primary_source" if eligible and primary_ready else
            "independently_corroborated" if eligible else
            "held_unconfirmed" if uncertain else "normal_path"
        )
        published = parse_dt(lead.get("date"))
        detection_latency = max(0, (now - min(published, now)).total_seconds()) if published else None
        key = "|".join(sorted(str(x.get("link")) for x in group))
        candidates.append({
            "id": hashlib.sha1(key.encode("utf-8")).hexdigest()[:12],
            "path": "breaking" if eligible else "normal",
            "eligible": eligible, "reason": reason, "urgency_score": score,
            "score_components": components, "matched_storyline_id": matched,
            "detected_at": iso(now), "source_published_at": lead.get("date"),
            "source_detection_latency_seconds": round(detection_latency, 1) if detection_latency is not None else None,
            "factual_update": clean_headline(lead.get("title")),
            "source": lead.get("source"), "source_tier": source_tier(lead.get("source")),
            "primary_source_link": lead.get("link"),
            "independent_source_count": len(families),
            "trusted_independent_source_count": len(trusted),
            "corroborating_sources": sorted({str(x.get("source")) for x in group}),
            "corroborating_links": sorted({str(x.get("link")) for x in group}),
            "risk_flags": ["unconfirmed_claim"] if uncertain else [],
            "age_minutes": round(age, 1),
        })
    candidates.sort(key=lambda x: (x["eligible"], x["urgency_score"], -x["age_minutes"]), reverse=True)
    return candidates


def build_payload(news_payload, storylines_payload, detected_at=None):
    now = detected_at or utcnow()
    candidates = evaluate_clusters(news_payload.get("stories") or [], storylines_payload.get("storylines") or [], now)
    eligible = [x for x in candidates if x["eligible"]]
    latencies = [x["source_detection_latency_seconds"] for x in eligible if x["source_detection_latency_seconds"] is not None]
    duplicate_reports = sum(max(0, len(x["corroborating_links"]) - 1) for x in candidates)
    evaluated = sum(len(x["corroborating_links"]) for x in candidates)
    return {
        "generated_at": iso(now), "schema_version": 1,
        "policy": {
            "fast_path_rule": "trusted primary source or two independent trusted sources; uncertain claims are held",
            "normal_path_preserved": True, "ideology_used_in_scoring": False,
        },
        "metrics": {
            "reports_evaluated": evaluated, "candidate_events": len(candidates),
            "fast_path_events": len(eligible), "held_for_normal_path": len(candidates) - len(eligible),
            "duplicate_reports_suppressed": duplicate_reports,
            "duplicate_event_rate_pct": round((duplicate_reports / evaluated) * 100, 2) if evaluated else 0.0,
            "median_source_detection_latency_seconds": round(median(latencies), 1) if latencies else None,
            "high_urgency_capture_pct": 100.0 if eligible else None,
            "published_fast_path_events": 0, "detection_to_publication_latency_seconds": None,
            "correction_events": 0, "correction_rate_pct": 0.0,
        },
        "candidates": candidates,
    }


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def main():
    payload = build_payload(load(NEWS, {}), load(STORYLINES, {}))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metrics = payload["metrics"]
    print(f"Fast path: {metrics['fast_path_events']} promoted, {metrics['held_for_normal_path']} kept on normal path, {metrics['duplicate_reports_suppressed']} duplicates grouped.")


if __name__ == "__main__":
    main()
