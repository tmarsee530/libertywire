#!/usr/bin/env python3
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STORYLINES = ROOT / "data" / "storylines.json"
OUTPUT = ROOT / "data" / "headline_game.json"

CANDIDATES = [
    "court", "judge", "house", "senate", "votes", "voter", "trade", "storm",
    "plane", "press", "media", "union", "money", "stock", "banks", "rates",
    "peace", "troop", "naval", "china", "india", "japan", "russia", "crime",
    "trial", "order", "state", "local", "mayor", "party", "polls", "power",
    "water", "fires", "flood", "earth", "space", "health", "virus", "drugs",
    "labor", "jobs", "wages", "taxes", "funds", "roads", "school", "faith",
    "legal", "rules", "rights", "video", "radio", "chief", "staff", "watch"
]

# only five-letter candidates are eligible
CANDIDATES = [w for w in CANDIDATES if len(w) == 5]


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def today_eastern():
    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def tokenize(text):
    return re.findall(r"[a-z]+", (text or "").lower())


def select_puzzle(storylines):
    ranked = []
    for idx, story in enumerate(storylines):
        if story.get("risk_flags"):
            continue
        title = story.get("title") or ""
        tokens = set(tokenize(title))
        for word in CANDIDATES:
            if word in tokens:
                score = float(story.get("importance_score") or 0) + float(story.get("source_count") or 0) * 2 - idx * 0.02
                ranked.append((score, word, story))

    if ranked:
        ranked.sort(key=lambda item: (-item[0], item[1]))
        _, answer, story = ranked[0]
        return answer, story

    # deterministic fallback from today's date; keeps game available even on a quiet feed
    date_seed = sum(ord(ch) for ch in today_eastern())
    answer = CANDIDATES[date_seed % len(CANDIDATES)]
    story = next((s for s in storylines if not s.get("risk_flags")), {})
    return answer, story


def main():
    puzzle_date = today_eastern()
    existing = load_json(OUTPUT, {})
    if existing.get("puzzle_date") == puzzle_date and existing.get("answer"):
        print(f"Headline Five already locked for {puzzle_date}; keeping existing puzzle.")
        return

    payload = load_json(STORYLINES, {})
    storylines = payload.get("storylines") or []
    answer, story = select_puzzle(storylines)

    coverage = story.get("coverage") or []
    first_link = coverage[0].get("link") if coverage else None
    first_source = coverage[0].get("source") if coverage else None

    output = {
        "puzzle_date": puzzle_date,
        "answer": answer.upper(),
        "storyline_id": story.get("id"),
        "context_title": story.get("title") or "Today's news picture",
        "source_count": story.get("source_count") or 0,
        "source_name": first_source,
        "source_url": first_link,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(f"Built Headline Five for {puzzle_date}: {answer.upper()}")


if __name__ == "__main__":
    main()
