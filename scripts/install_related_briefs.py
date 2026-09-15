#!/usr/bin/env python3
"""Add crawlable discovery links and structured breadcrumbs to every published Rally Brief."""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "briefs.json"
START = "<!-- RALLY_RELATED_START -->"
END = "<!-- RALLY_RELATED_END -->"
DISCOVERY_START = "<!-- RALLY_BRIEF_DISCOVERY_START -->"
DISCOVERY_END = "<!-- RALLY_BRIEF_DISCOVERY_END -->"
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
    return [x[2] for x in scored[:limit]]


def block(items):
    links = "".join(
        f'<li><a href="{escape(str(b.get("url") or "/briefs/"), quote=True)}">{escape(str(b.get("title") or "Rally Brief"))}</a></li>'
        for b in items
    )
    return f'{START}<section class="related" aria-labelledby="related-heading"><h2 id="related-heading">Related Rally Briefs</h2><ul>{links}</ul><p class="related-more"><a href="/topics/">Explore topics</a> · <a href="/briefs/">All Rally Briefs</a></p></section>{END}'


def discovery_block(current):
    title = str(current.get("title") or "Rally Brief")
    url = str(current.get("url") or "/briefs/")
    canonical = url if url.startswith("http") else "https://rallypointnews.com/" + url.lstrip("/")
    schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type":"ListItem","position":1,"name":"Rally Point News","item":"https://rallypointnews.com/"},
            {"@type":"ListItem","position":2,"name":"Rally Briefs","item":"https://rallypointnews.com/briefs/"},
            {"@type":"ListItem","position":3,"name":title,"item":canonical},
        ],
    }
    schema_json = json.dumps(schema, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'{DISCOVERY_START}<script type="application/ld+json">{schema_json}</script>{DISCOVERY_END}'


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
        updated = page

        rendered = block(related(current, briefs))
        pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
        if pattern.search(updated):
            updated = pattern.sub(rendered, updated, count=1)
        else:
            marker = '<p class="corrections">'
            if marker in updated:
                updated = updated.replace(marker, rendered + marker, 1)

        discovery = discovery_block(current)
        dpattern = re.compile(re.escape(DISCOVERY_START) + r".*?" + re.escape(DISCOVERY_END), re.S)
        if dpattern.search(updated):
            updated = dpattern.sub(discovery, updated, count=1)
        elif "</head>" in updated:
            updated = updated.replace("</head>", discovery + "</head>", 1)

        # RSS autodiscovery makes each durable article page advertise the site's publication feed.
        rss = '<link rel="alternate" type="application/rss+xml" title="Rally Point News — Rally Briefs" href="/feed.xml">'
        if 'type="application/rss+xml"' not in updated and "</head>" in updated:
            updated = updated.replace("</head>", rss + "</head>", 1)

        if ".related{" not in updated:
            updated = updated.replace(".corrections{", ".related{border-top:1px solid var(--rule);margin-top:34px;padding-top:20px}.related h2{margin-top:0}.related li{margin:9px 0}.related-more{font-size:14px;margin-top:16px}.corrections{", 1)
        elif ".related-more{" not in updated:
            updated = updated.replace(".related li{margin:9px 0}", ".related li{margin:9px 0}.related-more{font-size:14px;margin-top:16px}", 1)

        if updated != page:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"Updated discovery metadata and related links on {changed} Brief pages")


if __name__ == "__main__":
    main()
