#!/usr/bin/env python3
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STORYLINES = ROOT / "data" / "storylines.json"
BRIEFS = ROOT / "data" / "briefs.json"
OUTPUT = ROOT / "data" / "headline_game.json"

CANDIDATES = [
    "court", "judge", "house", "votes", "voter", "trade", "storm",
    "plane", "press", "media", "union", "money", "stock", "banks", "rates",
    "peace", "troop", "naval", "china", "india", "japan", "crime",
    "trial", "order", "state", "local", "mayor", "party", "polls", "power",
    "water", "fires", "flood", "earth", "space", "virus", "drugs",
    "labor", "wages", "taxes", "funds", "roads", "faith",
    "legal", "rules", "rights", "video", "radio", "chief", "staff", "watch"
]
CANDIDATES = [w for w in CANDIDATES if len(w) == 5]
STOP = {"the","and","for","with","from","into","after","over","says","said","news","today"}


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def today_eastern():
    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def tokenize(text):
    return re.findall(r"[a-z]+", (text or "").lower())


def meaningful(text):
    return {t for t in tokenize(text) if len(t) >= 4 and t not in STOP}


def select_puzzle(storylines):
    ranked = []
    for idx, story in enumerate(storylines):
        if story.get("risk_flags"):
            continue
        tokens = set(tokenize(story.get("title") or ""))
        for word in CANDIDATES:
            if word in tokens:
                score = float(story.get("importance_score") or 0) + float(story.get("source_count") or 0) * 2 - idx * 0.02
                ranked.append((score, word, story))
    if ranked:
        ranked.sort(key=lambda item: (-item[0], item[1]))
        _, answer, story = ranked[0]
        return answer, story

    date_seed = sum(ord(ch) for ch in today_eastern())
    answer = CANDIDATES[date_seed % len(CANDIDATES)]
    story = next((s for s in storylines if not s.get("risk_flags")), {})
    return answer, story


def related_brief(story):
    briefs = load_json(BRIEFS, {}).get("briefs") or []
    storyline_id = story.get("id")
    exact = next((b for b in briefs if storyline_id and b.get("storyline_id") == storyline_id), None)
    if exact:
        return exact
    story_tokens = meaningful(story.get("title") or "")
    ranked = []
    for b in briefs:
        overlap = len(story_tokens & meaningful((b.get("title") or "") + " " + (b.get("description") or "")))
        if overlap >= 2:
            ranked.append((overlap, b))
    return max(ranked, key=lambda x: x[0])[1] if ranked else None


def main():
    puzzle_date = today_eastern()
    existing = load_json(OUTPUT, {})
    payload = load_json(STORYLINES, {})
    storylines = payload.get("storylines") or []

    if existing.get("puzzle_date") == puzzle_date and existing.get("answer"):
        answer = existing["answer"].lower()
        story = next((s for s in storylines if s.get("id") == existing.get("storyline_id")), None)
        if not story:
            story = {
                "id": existing.get("storyline_id"),
                "title": existing.get("context_title"),
                "source_count": existing.get("source_count"),
                "coverage": [{"source": existing.get("source_name"), "link": existing.get("source_url")}]
            }
    else:
        answer, story = select_puzzle(storylines)

    coverage = story.get("coverage") or []
    first_link = coverage[0].get("link") if coverage else None
    first_source = coverage[0].get("source") if coverage else None
    brief = related_brief(story)

    output = {
        "puzzle_date": puzzle_date,
        "answer": answer.upper(),
        "storyline_id": story.get("id"),
        "context_title": story.get("title") or "Today's news picture",
        "source_count": story.get("source_count") or 0,
        "source_name": first_source,
        "source_url": first_link,
        "rally_url": (brief or {}).get("url") or "/",
        "rally_title": (brief or {}).get("title") or "Back to today's Rally Point news",
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    }
    if output != existing:
        OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
        print(f"Built/refreshed Headline Five for {puzzle_date}: {answer.upper()}")
    else:
        print(f"Headline Five unchanged for {puzzle_date}.")


if __name__ == "__main__":
    main()
