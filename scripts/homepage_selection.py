"""Conservative filter for homepage prominence, not for canonical publication.

Sports betting products and shopping deal roundups are accessible from the
archive, but should not displace developing news on the homepage.
"""
from __future__ import annotations
import re

SPORTS = re.compile(r"\b(?:nfl|nba|nhl|mlb|ncaa|football|basketball|baseball|soccer|hockey|college sports|college football|sportsbook|fanduel|draftkings)\b", re.I)
FIXTURE = re.compile(r"\b[A-Za-z][\w'-]*(?:\s+[A-Za-z][\w'-]*){0,2}\s+vs\.?\s+[A-Za-z][\w'-]*(?:\s+[A-Za-z][\w'-]*){0,2}\b", re.I)
BETTING = re.compile(r"\b(?:odds|parlay|picks?|predictions?|best bets|bonus bets|promo code|sportsbook|betting|point spread|proven model|player props)\b", re.I)
SHOPPING = re.compile(r"\b(?:prime day|black friday deals|cyber monday deals|coupon codes?|discount codes?|shopping deals|laptop deals|flash sale|save up to \d+%)\b", re.I)


def homepage_eligible(title: str) -> bool:
    title = str(title or "").strip()
    if not title:
        return False
    return not (((SPORTS.search(title) or FIXTURE.search(title)) and BETTING.search(title)) or SHOPPING.search(title))

def published_publisher_count(entry: dict) -> int:
    """Count distinct named publishers in the actual published developments."""
    families = set()
    for development in (entry or {}).get("developments", []):
        for source in development.get("sources", []):
            name = str(source.get("source_family") or source.get("source") or "").strip().lower()
            if name:
                families.add(name)
    return len(families)


def homepage_quality(story: dict, published: dict, findings: list | None = None) -> float:
    """Prefer source-backed, coherent developing news to noisy raw clusters."""
    if not published:
        return float("-inf")
    score = float(story.get("importance_score") or 0)
    families = published_publisher_count(published)
    score += 2 * min(families, 5)
    if str(published.get("status") or "").lower() == "breaking":
        score += 2
    if any(f.get("severity") == "high" for f in (findings or [])):
        return float("-inf")
    if any(f.get("type") == "possible_cross_event_update" for f in (findings or [])):
        score -= 10
    return round(score, 3)
