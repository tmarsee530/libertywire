#!/usr/bin/env python3
"""Add crawlable related-story links to every published Rally Brief."""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "briefs.json"
START = "<!-- RALLY_RELATED_START -->"
END = "<!-- RALLY_RELATED_END -->"
STOP = {"the","and","for","from","with","what","why","how","did","does","after","new","mean","means","about","into","that","this","their","will","was","were","are","has","have","its","his","her","who","when","where","nearly"}


def tokens(text):
    return {w for w in re.findall(r"[a-z0-9]+", str(text or "").lower()) if len(w) > 2 and w not in STOP}


def related(current, briefs, limit=3):
    a = tokens(f"{current.get('title','')} {current.get('description','')}")
    scored = []
    for other in briefs:
        if other is current or other.get("url") == current.get("url"):
            continue
        b = tokens(f"{other.get('title','')} {other.get('description','')}")
        overlap = len(a & b)
        score = overlap * 4 + len(a & b) / max(1, len(a | b))
        scored.append((score, other.get("published_at", ""), other))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    # Even when vocabulary overlap is low, recent internal links are better than an orphaned page.
    return [x[2] for x in scored[:limit]]


def block(items):
    links = "".join(
        f'<li><a href="{escape(str(b.get("url") or "/briefs/"), quote=True)}">{escape(str(b.get("title") or "Rally Brief"))}</a></li>'
        for b in items
    )
    return f'{START}<section class="related" aria-labelledby="related-heading"><h2 id="related-heading">Related Rally Briefs</h2><ul>{links}</ul></section>{END}'


def main():
    if not DATA.exists():
        print("No briefs metadata found")
        return
    briefs = json.loads(DATA.read_text(encoding="utf-8")).get("briefs", [])
    changed = 0
    for current in briefs:
        url = str(current.get("url") or "")
        m = re.search(r"/briefs/([^/]+)/?", url)
        if not m:
            continue
        path = ROOT / "briefs" / m.group(1) / "index.html"
        if not path.exists():
            continue
        page = path.read_text(encoding="utf-8")
        rendered = block(related(current, briefs))
        pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
        if pattern.search(page):
            updated = pattern.sub(rendered, page, count=1)
        else:
            marker = '<p class="corrections">'
            if marker not in page:
                continue
            updated = page.replace(marker, rendered + marker, 1)
        # Related links inherit existing article typography; add only spacing/list treatment.
        if ".related{" not in updated:
            updated = updated.replace(".corrections{", ".related{border-top:1px solid var(--rule);margin-top:34px;padding-top:20px}.related h2{margin-top:0}.related li{margin:9px 0}.corrections{", 1)
        if updated != page:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"Updated related links on {changed} Brief pages")


if __name__ == "__main__":
    main()
