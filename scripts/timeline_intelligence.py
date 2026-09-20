#!/usr/bin/env python3
"""Deterministic timeline modeling for concise, source-backed live stories.

The module is intentionally independent of the publisher and history scripts so
legacy records can be upgraded in place without changing durable story IDs.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SCHEMA_VERSION = 2
TRACKING_QUERY_KEYS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "ocid", "ref", "ref_src",
    "source", "cmpid", "output",
}
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but",
    "by", "for", "from", "had", "has", "have", "he", "her", "his", "how",
    "in", "into", "is", "it", "its", "more", "new", "news", "of", "on",
    "or", "our", "report", "reports", "said", "says", "she", "that", "the",
    "their", "they", "this", "to", "update", "updates", "was", "were",
    "what", "when", "where", "which", "while", "who", "why", "will", "with",
    "after", "before", "about", "amid", "latest", "live", "exclusive",
    "video", "photo", "photos", "watch", "developing", "story",
}
HYPE_WORDS = {
    "bombshell", "chaos", "crushing", "destroys", "devastating", "explosive",
    "humiliating", "meltdown", "nightmare", "shocking", "slams", "stunning",
}
LOW_SIGNAL_PHRASES = {
    "analysis:", "expert weighs in", "morning greatness", "opinion:",
    "six degrees of", "what to know", "weekly quiz", "why ", "please shut up",
    "goes rogue", "roasted", "ongoing circus",
}
STATE_TERMS = {
    "approves", "approved", "arrests", "arrested", "blocks", "blocked",
    "cancels", "canceled", "cancelled", "certifies", "certified", "charges",
    "charged", "confirms", "confirmed", "convicts", "convicted", "declares",
    "declared", "delays", "delayed", "dies", "died", "dismisses", "dismissed",
    "evacuates", "evacuated", "fails", "failed", "files", "filed", "indicts",
    "indicted", "launches", "launched", "lifts", "lifted", "orders", "ordered",
    "overturns", "overturned", "passes", "passed", "rejects", "rejected",
    "releases", "released", "resigns", "resigned", "rules", "ruled", "settles",
    "settled", "strikes", "struck", "suspends", "suspended", "withdraws",
    "withdrew", "wins", "won", "loses", "lost",
}
MAJOR_TERMS = STATE_TERMS | {
    "attack", "ceasefire", "crash", "earthquake", "emergency", "evacuation",
    "explosion", "fatalities", "hurricane", "killed", "outage", "recall",
    "shutdown", "tornado", "verdict", "wildfire",
}
CONCEPT_PATTERNS = {
    "close": (" close", " closes", " closed", "closing", "shut down", "shutdown"),
    "demolish": ("demolish", "tear down", "torn down", "ripped down", "bulldozer", "wrecking ball"),
    "speak": ("speaks", "speaking", "breaks silence", "statement", "interview"),
    "rule": ("court rules", "judge rules", "ruling", "verdict"),
    "order": (" orders", " ordered"),
    "charge": (" charges", " charged", "indicts", "indicted"),
    "confirm": (" confirms", " confirmed"),
    "resign": (" resigns", " resigned", "steps down"),
    "launch": (" launches", " launched"),
    "evacuate": ("evacuat",),
    "delay": (" delays", " delayed", "postpon"),
    "approve": (" approves", " approved", "passes", " passed"),
    "reject": (" rejects", " rejected", "blocks", " blocked", " bars", " barred", "denied access", "denied entry"),
    "suspend": (" suspends", " suspended"),
    "settle": (" settles", " settled"),
    "access_decision": ("bans ", "ban on ", "to ban ", "announces ban", "banning ", "will bar ", "he'll bar ", "trump bars "),
    "access_enforcement": ("denied access", "denied white house access", "denied from white house", "blocked from access", "blocks ", " bars ", "turned away", "credentials revoked", "badge did not work", "barred from"),
    "agreement": (" agreement", " deal", " pact", "reaches deal", "struck deal"),
    "creation": (" creates ", " creating ", " will create", " form ", " will form", "appoint ", "appointing ", "ai force"),
}
SOURCE_FAMILY_ALIASES = {
    "fox news politics": "fox", "fox news world": "fox", "fox business": "fox", "fox news": "fox",
    "national review the corner": "national-review", "national review": "national-review",
    "associated press": "ap", "ap": "ap", "npr news": "npr", "npr": "npr",
    "realclearpolitics": "realclear", "realclearpolicy": "realclear", "realclearworld": "realclear",
    "realcleardefense": "realclear", "daily signal": "daily-signal", "the daily signal": "daily-signal",
}
REACTION_PATTERNS = (
    "analysis:", "commentary:", "opinion:", "reacts to", "reaction to", "weighs in",
    "rips ", "slams ", "defends ", "praises ", "condemns ", "what it means",
    "week in review", "week in pictures", "talk about", "expert says",
    "calls ", "responds to", "says it would", "shows lead with", "avoids news of", "welcomes ",
    "expresses optimism", "victory lap", "what it means",
    ": expert", "expert:",
)
CORRECTION_PATTERNS = ("corrects", "corrected", "correction", "revise", "revises", "revised", "updated count", "now reports", "now says")


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def canonical_link(value):
    """Collapse tracking variants without changing the public source URL."""
    try:
        parts = urlsplit(str(value or ""))
        query = [
            (key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
        ]
        path = parts.path.rstrip("/") or "/"
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower().removeprefix("www."), path, urlencode(sorted(query)), ""))
    except (TypeError, ValueError):
        return str(value or "")


def fact_tokens(value):
    raw = re.findall(r"[a-z']+|\d+(?:[.,]\d+)?", clean_text(value).lower())
    return {token for token in raw if (any(char.isdigit() for char in token) or len(token) >= 3) and token not in STOP_WORDS and token not in HYPE_WORDS}


def proper_anchors(value):
    generic = {"A", "An", "And", "Breaking", "Developing", "Exclusive", "Live", "New", "The", "This", "Update"}
    return {token.lower() for token in re.findall(r"\b[A-Z][A-Za-z0-9'’-]{2,}\b", clean_text(value)) if token not in generic}


def state_concepts(value):
    low = " " + clean_text(value).lower()
    concepts = {name for name, patterns in CONCEPT_PATTERNS.items() if any(pattern in low for pattern in patterns)}
    return concepts or (fact_tokens(value) & STATE_TERMS)


def low_signal(value):
    text = clean_text(value); low = text.lower()
    return text.endswith("?") or any(phrase in low for phrase in LOW_SIGNAL_PHRASES)


def commentary_only(value):
    low = clean_text(value).lower()
    return any(phrase in low for phrase in REACTION_PATTERNS)


def source_family(value):
    clean = clean_text(value).lower()
    return SOURCE_FAMILY_ALIASES.get(clean, clean or "unknown")


def _clauses(title):
    parts = [
        part.strip(" -–—:;,.")
        for part in re.split(r"\s*(?:[|;]|\s[—–-]\s|:\s+|[.!?]\s+)\s*", clean_text(title))
        if part.strip()
    ]
    return parts or [clean_text(title)]


def _numbers(tokens):
    return {token for token in tokens if any(char.isdigit() for char in token)}


def _similarity(left, right):
    if not left or not right:
        return 0.0
    overlap = len(left & right)
    return max(overlap / max(1, len(left | right)), overlap / max(1, min(len(left), len(right))))


def _best_label(title, seen):
    title = re.sub(r"^(breaking|developing|exclusive|live updates?)\s*[:—-]\s*", "", clean_text(title), flags=re.I)
    if not title:
        return ""
    words = title.split()
    return title if len(words) <= 22 else " ".join(words[:22]).rstrip(" ,;:") + "…"


def _source_entry(item, role="primary", independent=True):
    return {
        "source": clean_text(item.get("source")) or "Original source",
        "link": str(item.get("link") or ""),
        "date": item.get("date"),
        "title": clean_text(item.get("title")),
        "role": role,
        "source_family": source_family(item.get("source")),
        "independent": bool(independent),
    }


def durable_update_id(item):
    """Identify a material development independently of labels/classes/sources."""
    stable = canonical_link(item.get("link"))
    if not stable:
        stable = " ".join(sorted(fact_tokens(item.get("title"))))
    return hashlib.sha1(stable.encode("utf-8")).hexdigest()[:16]


def _merge_source(update, item):
    incoming_tokens = fact_tokens(item.get("title"))
    primary_tokens = fact_tokens(update.get("source_title"))
    same_family = source_family(item.get("source")) in {source_family(x.get("source")) for x in update.get("sources", [])}
    # Near-verbatim copy is not independent corroboration. An explicit claim
    # that the second newsroom independently confirmed it is the conservative
    # exception; generic attribution such as "officials say" is not.
    explicit_confirmation = any(word in clean_text(item.get("title")).lower() for word in ("confirmed", "independently confirms", "independently verified"))
    likely_republication = _similarity(incoming_tokens, primary_tokens) >= .88 and not explicit_confirmation
    independent = not same_family and not likely_republication
    incoming = _source_entry(item, "corroborating" if independent else "republication", independent)
    key = (incoming["source"].lower(), canonical_link(incoming["link"]))
    existing = {(x.get("source", "").lower(), canonical_link(x.get("link"))) for x in update["sources"]}
    if key not in existing:
        update["sources"].append(incoming)


def classify_update(label, record_status, newest=False, oldest=False):
    tokens = fact_tokens(label)
    low = clean_text(label).lower()
    is_major = bool(tokens & MAJOR_TERMS or _numbers(tokens) or state_concepts(label) or any(term in low for term in ("supreme court", "white house", "federal reserve")))
    if newest and str(record_status or "").lower() == "breaking" and is_major:
        return "BREAKING"
    if is_major:
        return "MAJOR DEVELOPMENT"
    if oldest:
        return "CONTEXT"
    return "UPDATE"


def meaningful_updates(coverage, record_status="developing"):
    """Return distinct material developments in chronological order.

    Near-identical reports are grouped as corroborating sources. A later report
    becomes a new update only when it introduces a state change, a number, or a
    sufficiently large set of non-generic facts.
    """
    ordered = sorted(
        [item for item in coverage if item.get("title") and item.get("link")],
        key=lambda item: (parse_dt(item.get("date")), clean_text(item.get("source"))),
    )
    updates = []
    seen = set()
    url_index = {}
    for item in ordered:
        title = clean_text(item.get("title"))
        if low_signal(title):
            continue
        tokens = fact_tokens(title)
        if not tokens:
            continue
        url_key = canonical_link(item.get("link"))
        if url_key and url_key in url_index:
            _merge_source(updates[url_index[url_key]], item)
            continue
        novel = tokens - seen
        decisive = (novel & STATE_TERMS) | _numbers(novel)
        major_novel = novel & (MAJOR_TERMS - STATE_TERMS)
        concepts = state_concepts(title)
        anchors = proper_anchors(title)
        prior_concepts = set().union(*(set(update.get("state_concepts") or []) for update in updates)) if updates else set()
        prior_anchors = set().union(*(set(update.get("anchors") or []) for update in updates)) if updates else set()
        novel_concepts = concepts - prior_concepts
        if "confirm" in novel_concepts and concepts & prior_concepts:
            novel_concepts.discard("confirm")
        novel_anchors = anchors - prior_anchors
        closest_index = None
        closest_similarity = 0.0
        for index, update in enumerate(updates):
            similarity = _similarity(tokens, set(update["fact_tokens"]))
            if similarity > closest_similarity:
                closest_index, closest_similarity = index, similarity
        same_event_index = next((index for index, update in enumerate(updates) if concepts and concepts & set(update.get("state_concepts") or []) and anchors & set(update.get("anchors") or [])), None)
        revision_index = None
        current_numbers = _numbers(tokens)
        if current_numbers:
            for index, update in enumerate(updates):
                prior_tokens = set(update.get("fact_tokens") or [])
                prior_numbers = _numbers(prior_tokens)
                shared_non_numbers = (tokens - current_numbers) & (prior_tokens - prior_numbers)
                related_state = concepts & set(update.get("state_concepts") or [])
                related_anchor = anchors & set(update.get("anchors") or [])
                if prior_numbers and current_numbers != prior_numbers and related_anchor and len(shared_non_numbers) >= 2 and (related_state or _similarity(tokens-current_numbers, prior_tokens-prior_numbers) >= .4):
                    revision_index = index
                    break
        narrative_change = bool(
            len(novel) >= 4
            and len(novel) / max(1, len(tokens)) >= 0.42
            and (novel_anchors or len(novel) >= 5)
        )
        commentary = commentary_only(title)
        if commentary and not updates:
            continue
        material = not updates or revision_index is not None or bool(decisive or major_novel or novel_concepts) or (narrative_change and not commentary)
        duplicate_event = same_event_index is not None and not (novel_concepts or major_novel or _numbers(novel))
        if duplicate_event:
            closest_index = same_event_index
        if updates and commentary:
            # Reactions and opinion are neither chronology nor corroboration.
            continue
        if updates and revision_index is None and (not material or duplicate_event or (closest_similarity >= 0.62 and not (decisive or major_novel or novel_concepts))):
            if closest_index is not None:
                _merge_source(updates[closest_index], item)
                if url_key:
                    url_index[url_key] = closest_index
            continue
        label = _best_label(title, seen)
        label_tokens = fact_tokens(label)
        if updates and len(label_tokens - seen) < 2 and not ((label_tokens - seen) & STATE_TERMS) and not _numbers(label_tokens - seen) and not novel_concepts:
            if closest_index is not None:
                _merge_source(updates[closest_index], item)
            continue
        basis = [
            name for name, active in (
                ("initial_report", not updates),
                ("state_change", bool(decisive or novel_concepts)),
                ("major_fact", bool(major_novel)),
                ("new_named_actor", bool(novel_anchors)),
                ("substantive_new_detail", narrative_change),
            ) if active
        ]
        update = {
            "id": durable_update_id(item),
            "label": label,
            "classification": "UPDATE",
            "date": item.get("date"),
            "published_at": item.get("date"),
            "time_basis": "source_published_at",
            "source": clean_text(item.get("source")) or "Original source",
            "link": str(item.get("link") or ""),
            "source_title": title,
            "sources": [_source_entry(item)],
            "material_basis": basis,
            "fact_tokens": sorted(tokens),
            "state_concepts": sorted(concepts),
            "anchors": sorted(anchors),
        }
        if revision_index is not None:
            update["revision_kind"] = "correction" if any(term in title.lower() for term in CORRECTION_PATTERNS) else "numerical_revision"
            update["supersedes_update_id"] = updates[revision_index].get("id")
        updates.append(update)
        if url_key:
            url_index[url_key] = len(updates) - 1
        seen |= tokens
    for index, update in enumerate(updates):
        update["classification"] = "CORRECTION" if update.get("revision_kind") == "correction" else ("REVISION" if update.get("revision_kind") else classify_update(update["label"], record_status,newest=index == len(updates) - 1,oldest=index == 0))
        update["source_count"] = len(update.get("sources") or [])
        update["independent_source_count"] = len({source_family(x.get("source")) for x in update.get("sources") or [] if x.get("independent", True)})
        update["corroborated"] = update["independent_source_count"] > 1
    return updates


def current_status(updates):
    if not updates:
        return {
            "summary": "No material development has been confirmed yet.",
            "as_of": None, "source": None, "link": None, "classification": "STATUS",
        }
    latest = updates[-1]
    summary = clean_text(latest.get("label"))
    if summary and summary[-1:] not in ".!?…":
        summary += "."
    return {
        "summary": summary,
        "as_of": latest.get("date"),
        "source": latest.get("source"),
        "link": latest.get("link"),
        "classification": latest.get("classification"),
        "source_count": latest.get("source_count", len(latest.get("sources") or [])),
        "independent_source_count": latest.get("independent_source_count", 1),
        "corroborated": bool(latest.get("corroborated")),
    }


def build_timeline_model(record):
    updates = meaningful_updates(record.get("coverage") or [], record.get("status"))
    return {
        "timeline_schema_version": SCHEMA_VERSION,
        "current_status": current_status(updates),
        "material_update_count": len(updates),
        "updates": updates,
    }


def serializable_model(record):
    """Return the model without internal token vectors used during selection."""
    model = build_timeline_model(record)
    model["updates"] = [
        {key: value for key, value in update.items() if key not in {"fact_tokens", "state_concepts", "anchors"}}
        for update in model["updates"]
    ]
    return model
