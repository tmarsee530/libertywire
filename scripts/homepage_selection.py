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
