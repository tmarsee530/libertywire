#!/usr/bin/env python3
"""Conservative, explainable event identity for Rally Point timelines.

The matcher intentionally answers a narrower question than topic similarity:
do two headlines describe the same causal real-world event?  Precision is more
important than recall because a false merge damages the permanent timeline.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache


GENERIC_ANCHORS = {
    "a", "an", "the", "breaking", "developing", "exclusive", "live", "new",
    "latest", "report", "reports", "update", "updates", "watch", "use", "get",
    "code", "promo", "review", "today", "saturday", "sunday", "monday",
    "tuesday", "wednesday", "thursday", "friday", "white", "house", "court",
    "federal", "government", "president", "official", "officials", "state",
    "states", "american", "news",
}
GENERIC_TOKENS = GENERIC_ANCHORS | {
    "after", "amid", "about", "with", "from", "into", "over", "their", "they",
    "says", "said", "will", "would", "could", "more", "than", "story", "video",
    "photo", "photos", "analysis", "opinion", "explains", "reacts", "reaction",
}

WORD_ALIASES = {
    "artificial intelligence": "ai",
    "united states": "us",
    "hospitalisation": "hospitalize",
    "hospitalization": "hospitalize",
    "hospitalised": "hospitalize",
    "hospitalized": "hospitalize",
    "intercepted": "intercept",
    "intercepts": "intercept",
    "elections": "election",
    "bills": "law",
    "laws": "law",
    "reporters": "journalist",
    "journalists": "journalist",
    "barred": "ban",
    "banned": "ban",
    "banning": "ban",
}

ACTION_PATTERNS = {
    "access_ban": (r"\bban(?:s|ned)?\b", r"\bbar(?:s|red)?\b", r"denied access", r"blocks? .*entry", r"badges? revoked", r"turns? away"),
    "agreement": (r"\bdeal\b", r"\bagreement\b", r"\bpact\b", r"reaches? accord", r"strikes? .*deal"),
    "attack": (r"\battack(?:s|ed)?\b", r"\bstrike(?:s|n)?\b", r"\bbomb(?:s|ed|ing)?\b", r"\bshoot(?:s|ing)?\b"),
    "arrest_charge": (r"\barrest(?:s|ed)?\b", r"\bcharg(?:e|es|ed)\b", r"\bindict(?:s|ed|ment)?\b"),
    "court_ruling": (r"court .*\brul", r"judge .*\brul", r"\bverdict\b", r"\border(?:s|ed)?\b", r"\boverturn(?:s|ed)?\b"),
    "death_injury": (r"\bdies?\b", r"\bdead\b", r"\bkilled\b", r"\binjur(?:y|ies|ed)\b", r"\bcasualt(?:y|ies)\b"),
    "evacuation": (r"\bevacuat", r"shelter.in.place", r"\bclosure\b", r"\bclosed\b"),
    "investigation": (r"\binvestigat", r"\binquiry\b", r"\bprobe\b"),
    "lawsuit": (r"\blawsuit\b", r"\bsues?\b", r"\bfile[sd]? suit\b", r"legal action"),
    "launch_creation": (r"\blaunch(?:es|ed)?\b", r"\bcreates?\b", r"\bforms?\b", r"\bappoint(?:s|ed)?\b"),
    "purchase_sale": (r"\bbuy(?:s|ing)?\b", r"\bpurchas(?:e|es|ed)\b", r"\bsale\b", r"\bacquir(?:e|es|ed)\b"),
    "resignation": (r"\bresign(?:s|ed)?\b", r"steps? down", r"\bwithdraw(?:s|n|drew)?\b"),
    "revision": (r"\brevis(?:e|es|ed|ion)\b", r"\bcorrect(?:s|ed|ion)\b", r"updated .*count", r"now (?:says|reports)"),
    "suspension": (r"\bsuspend(?:s|ed)?\b", r"\bpause(?:s|d)?\b", r"\bhalt(?:s|ed)?\b"),
    "law_enactment": (r"\bsigns? (?:a |the )?(?:bill|law)", r"\benacts?\b", r"\bpasses? (?:a |the )?(?:bill|law)"),
    "interception": (r"\bintercept(?:s|ed|ion)?\b", r"restricted airspace"),
    "hospitalization": (r"\bhospitali[sz](?:e|ed|ation)\b", r"remains? in (?:the )?hospital"),
}
CAUSAL_PATTERNS = (r"\bafter\b", r"\bfollowing\b", r"\bresulting from\b", r"\bover the\b", r"\bstemming from\b", r"\bin response to\b")


def _normalized(value):
    low = str(value or "").lower().replace("’", "'")
    for phrase, replacement in WORD_ALIASES.items():
        low = re.sub(rf"\b{re.escape(phrase)}\b", replacement, low)
    return low


def _words(value):
    return {WORD_ALIASES.get(word, word) for word in re.findall(r"[a-z0-9']{2,}", _normalized(value)) if word not in {"a", "an", "of", "to", "in", "on", "at", "by", "as", "is", "it"}}


def anchors(value):
    text = str(value or "")
    words = re.findall(r"\b[A-Z][A-Za-z0-9'’-]{2,}\b", text)
    words += [word for word in re.findall(r"\b[A-Z]{2,5}\b", text) if word not in {"US", "UK", "EU"}]
    return {word.lower().replace("’", "'") for word in words if word.lower() not in GENERIC_ANCHORS}


def actions(value):
    low = " ".join(_normalized(value).split())
    return {name for name, patterns in ACTION_PATTERNS.items() if any(re.search(pattern, low) for pattern in patterns)}


def specifics(value):
    return _words(value) - GENERIC_TOKENS - {part for pats in ACTION_PATTERNS.values() for pattern in pats for part in re.findall(r"[a-z]{3,}", pattern)}


@dataclass(frozen=True)
class EventMatch:
    same_event: bool
    confidence: float
    reason: str
    shared_anchors: tuple[str, ...] = ()
    shared_actions: tuple[str, ...] = ()
    shared_specifics: tuple[str, ...] = ()


@lru_cache(maxsize=50000)
def compare(left, right):
    """Return a conservative event-level match with an inspectable reason."""
    la, ra = anchors(left), anchors(right)
    lac, rac = actions(left), actions(right)
    ls, rs = specifics(left), specifics(right)
    shared_a, shared_ac, shared_s = la & ra, lac & rac, ls & rs
    all_words_left, all_words_right = _words(left) - GENERIC_TOKENS, _words(right) - GENERIC_TOKENS
    overlap = len(all_words_left & all_words_right)
    lexical = max(
        overlap / max(1, min(len(all_words_left), len(all_words_right))),
        overlap / max(1, len(all_words_left | all_words_right)),
    )
    causal = any(re.search(pattern, str(left or "").lower()) or re.search(pattern, str(right or "").lower()) for pattern in CAUSAL_PATTERNS)

    # Known actions that disagree are strong evidence of separate events unless
    # a headline explicitly states a causal follow-up and preserves the event object.
    if lac and rac and not shared_ac and not (causal and shared_a and len(shared_s) >= 2):
        return EventMatch(False, round(lexical, 3), "different_actions", tuple(sorted(shared_a)), (), tuple(sorted(shared_s)))
    if shared_ac and shared_a and (shared_s or lexical >= .46):
        confidence = min(.99, .66 + .08 * len(shared_ac) + .05 * min(3, len(shared_a)) + .04 * min(3, len(shared_s)))
        return EventMatch(True, round(confidence, 3), "shared_event_frame", tuple(sorted(shared_a)), tuple(sorted(shared_ac)), tuple(sorted(shared_s)))
    if causal and shared_a and len(shared_s) >= 2:
        return EventMatch(True, .78, "causal_continuity", tuple(sorted(shared_a)), tuple(sorted(shared_ac)), tuple(sorted(shared_s)))
    # Some precise event frames have no verb in one headline. Require multiple
    # named anchors and several shared specifics so a person/topic match alone
    # can never satisfy this path.
    if len(shared_a) >= 2 and len(shared_s) >= 4 and lexical >= .48:
        return EventMatch(True, round(min(.88, .68 + lexical * .2), 3), "shared_distinctive_frame", tuple(sorted(shared_a)), tuple(sorted(shared_ac)), tuple(sorted(shared_s)))
    if lexical >= .72 and shared_a and len(shared_s) >= 2:
        return EventMatch(True, round(min(.9, lexical), 3), "strong_paraphrase", tuple(sorted(shared_a)), tuple(sorted(shared_ac)), tuple(sorted(shared_s)))
    return EventMatch(False, round(lexical, 3), "insufficient_event_evidence", tuple(sorted(shared_a)), tuple(sorted(shared_ac)), tuple(sorted(shared_s)))


def best_match(current_titles, prior_titles):
    best = EventMatch(False, 0.0, "no_candidate")
    for current in filter(None, current_titles):
        for prior in filter(None, prior_titles):
            candidate = compare(current, prior)
            if candidate.confidence > best.confidence:
                best = candidate
    return best
