#!/usr/bin/env python3
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import feedparser
import requests

ROOT = Path(__file__).resolve().parents[1]
MARKETS = ROOT / "local_markets.json"
NEWS = ROOT / "data" / "news.json"
OUT = ROOT / "data" / "local_news.json"
MAX_PER_MARKET = 24
MAX_PER_STATE = 12
TIMEOUT = 20
UA = "RallyPointNews/1.0 (+https://rallypointnews.com/)"

US_STATES = [
    ("Alabama","AL"),("Alaska","AK"),("Arizona","AZ"),("Arkansas","AR"),("California","CA"),("Colorado","CO"),("Connecticut","CT"),("Delaware","DE"),("Florida","FL"),("Georgia","GA"),("Hawaii","HI"),("Idaho","ID"),("Illinois","IL"),("Indiana","IN"),("Iowa","IA"),("Kansas","KS"),("Kentucky","KY"),("Louisiana","LA"),("Maine","ME"),("Maryland","MD"),("Massachusetts","MA"),("Michigan","MI"),("Minnesota","MN"),("Mississippi","MS"),("Missouri","MO"),("Montana","MT"),("Nebraska","NE"),("Nevada","NV"),("New Hampshire","NH"),("New Jersey","NJ"),("New Mexico","NM"),("New York","NY"),("North Carolina","NC"),("North Dakota","ND"),("Ohio","OH"),("Oklahoma","OK"),("Oregon","OR"),("Pennsylvania","PA"),("Rhode Island","RI"),("South Carolina","SC"),("South Dakota","SD"),("Tennessee","TN"),("Texas","TX"),("Utah","UT"),("Vermont","VT"),("Virginia","VA"),("Washington","WA"),("West Virginia","WV"),("Wisconsin","WI"),("Wyoming","WY"),
]


def clean(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(text or ""))).strip()


def image_from_entry(entry):
    for key in ("media_content", "media_thumbnail"):
        rows = entry.get(key) or []
        if isinstance(rows, dict): rows = [rows]
        for row in rows:
            if isinstance(row, dict) and row.get("url"):
                return str(row["url"]).strip()
    for enclosure in entry.get("enclosures") or []:
        if not isinstance(enclosure, dict): continue
        url = enclosure.get("href") or enclosure.get("url")
        media_type = str(enclosure.get("type") or "")
        if url and (media_type.startswith("image/") or not media_type):
            return str(url).strip()
    image = entry.get("image")
    if isinstance(image, dict):
        url = image.get("href") or image.get("url")
        if url: return str(url).strip()
    raw = str(entry.get("summary") or entry.get("description") or "")
    match = re.search(r'<img[^>]+src=["\']([^"\']+)', raw, flags=re.I)
    return match.group(1).strip() if match else ""


def normalize_entry(entry, source, source_type):
    link = str(entry.get("link") or "").strip()
    title = clean(entry.get("title"))
    if not link or not title: return None
    return {
        "title": title,
        "link": link,
        "source": source,
        "source_type": source_type,
        "date": entry.get("published") or entry.get("updated") or "",
        "summary": clean(entry.get("summary") or entry.get("description") or "")[:500],
        "image": image_from_entry(entry),
    }


def fetch_feed(feed):
    try:
        r = requests.get(feed["url"], headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        parsed = feedparser.parse(r.content)
        return [x for x in (normalize_entry(e, feed["name"], feed.get("type", "local")) for e in parsed.entries[:40]) if x]
    except Exception as e:
        print(f"Local feed failed: {feed['name']}: {e}")
        return []


def fetch_google_state(state_name, state_code):
    url = f"https://news.google.com/rss/headlines/section/geo/{quote(state_name)}?hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        parsed = feedparser.parse(r.content)
        stories = []
        for entry in parsed.entries[:MAX_PER_STATE]:
            source = entry.get("source") or {}
            source_name = source.get("title") if isinstance(source, dict) else ""
            title = clean(entry.get("title"))
            if source_name and title.endswith(f" - {source_name}"):
                title = title[:-(len(source_name)+3)].rstrip()
            if not title or not entry.get("link"): continue
            stories.append({
                "title": title,
                "link": str(entry.get("link") or "").strip(),
                "source": source_name or "Google News",
                "source_type": "state_fallback",
                "date": entry.get("published") or entry.get("updated") or "",
                "summary": "",
                "image": image_from_entry(entry),
            })
        return stories
    except Exception as e:
        print(f"State fallback failed: {state_name}: {e}")
        return []


def market_terms(market):
    return [str(x).lower() for x in market.get("keywords", []) if str(x).strip()]


def is_market_relevant(item, market):
    hay = f"{item.get('title','')} {item.get('summary','')}".lower()
    return any(term in hay for term in market_terms(market))


def national_matches(market):
    if not NEWS.exists(): return []
    try: payload = json.loads(NEWS.read_text())
    except Exception: return []
    terms = market_terms(market); matched = []
    for story in payload.get("stories", []):
        hay = f"{story.get('title','')} {story.get('description','')}".lower()
        if not any(term in hay for term in terms): continue
        matched.append({
            "title": story.get("title"), "link": story.get("link"), "source": story.get("source"),
            "source_type": "rally_point_source", "date": story.get("date"),
            "summary": story.get("description", "")[:500], "image": story.get("image") or "",
        })
    return matched


def dedupe(items):
    seen = set(); out = []
    for item in items:
        key = (item.get("link") or "").split("#")[0]
        if not key or key in seen: continue
        seen.add(key); out.append(item)
    return out


def main():
    config = json.loads(MARKETS.read_text())
    markets_out = []
    for market in config.get("markets", []):
        local = []; rejected = 0; fetched_total = 0; feed_health = []
        for feed in market.get("feeds", []):
            fetched = fetch_feed(feed)
            relevant = [item for item in fetched if is_market_relevant(item, market)]
            rejected_here = len(fetched) - len(relevant)
            fetched_total += len(fetched); rejected += rejected_here; local.extend(relevant)
            feed_health.append({"source":feed["name"],"fetched":len(fetched),"kept":len(relevant),"rejected":rejected_here})
        shared = national_matches(market)
        items = dedupe(shared + local)[:MAX_PER_MARKET]
        markets_out.append({
            "id":market["id"],"city":market["city"],"region":market["region"],"region_code":market["region_code"],
            "label":market["label"],"aliases":market.get("aliases",[]),"story_count":len(items),
            "quality":{"local_feed_items_fetched":fetched_total,"local_feed_items_kept":len(local),"syndicated_or_nonlocal_rejected":rejected,"shared_news_matches":len(shared),"stories_with_images":sum(1 for item in items if item.get("image")),"feed_health":feed_health},
            "stories":items,
        })
        print(f"{market['id']}: kept {len(items)} market-relevant stories; rejected {rejected} syndicated/nonlocal feed items")

    states_out = []
    for state_name, state_code in US_STATES:
        stories = fetch_google_state(state_name, state_code)
        states_out.append({"region":state_name,"region_code":state_code,"label":state_name,"story_count":len(stories),"stories":stories})
        print(f"state-{state_code.lower()}: {len(stories)} fallback stories")

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "markets": markets_out,
        "states": states_out,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    old = None
    if OUT.exists():
        try: old = json.loads(OUT.read_text())
        except Exception: pass
    comparable_old = dict(old or {}); comparable_old.pop("generated_at", None)
    comparable_new = dict(payload); comparable_new.pop("generated_at", None)
    if comparable_old == comparable_new:
        print("Local Rally data unchanged"); return
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Built Local Rally data for {len(markets_out)} metro market(s) and {len(states_out)} state fallback market(s)")


if __name__ == "__main__": main()
