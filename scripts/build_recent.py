#!/usr/bin/env python3
"""Build a durable recent-headlines page from Rally Point's attributed news dataset."""
from pathlib import Path
import html,json
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/"data/news.json").read_text(encoding="utf-8"))
stories=[x for x in data.get("stories",[]) if x.get("title") and x.get("link")][:150]
def e(v): return html.escape(str(v or ""),quote=True)
def when(v):
    try:
        d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return d.strftime("%b %-d, %Y · %-I:%M %p UTC")
    except Exception:return ""
rows="".join(f'<article><h2><a href="{e(x["link"])}" rel="noopener">{e(x["title"])}</a></h2><div class="meta">{e(x.get("source"))} · {e(when(x.get("date")))}</div></article>' for x in stories)
page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Recent Headlines — Rally Point News</title><meta name="description" content="The latest headlines monitored by Rally Point News, with direct links to the original publishers."><link rel="canonical" href="https://rallypointnews.com/recent/"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><meta property="og:type" content="website"><meta property="og:site_name" content="Rally Point News"><meta property="og:title" content="Recent Headlines — Rally Point News"><meta property="og:description" content="The latest headlines monitored by Rally Point News, with direct links to the original publishers."><meta property="og:url" content="https://rallypointnews.com/recent/"><style>body{{margin:0;color:#111;background:#fff;font-family:Georgia,"Times New Roman",serif}}header,main,footer{{max-width:900px;margin:auto;padding:18px 14px}}header{{border-bottom:3px double #111;text-align:center}}h1{{font-size:clamp(32px,6vw,52px);margin:4px 0}}header p{{color:#555}}nav{{font:700 9px Arial,sans-serif;text-transform:uppercase;display:flex;justify-content:center;gap:22px;flex-wrap:wrap}}nav a{{color:#111;text-decoration:none}}article{{padding:12px 0;border-bottom:1px solid #ccc}}h2{{font-size:20px;line-height:1.08;margin:0 0 4px}}h2 a{{color:#111;text-decoration:none}}h2 a:hover{{text-decoration:underline}}.meta{{font:700 8px Arial,sans-serif;text-transform:uppercase;color:#666}}footer{{border-top:3px double #111;font:11px Arial,sans-serif;color:#555}}@media(max-width:520px){{h2{{font-size:18px}}}}</style><script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebPage","name":"Recent Headlines — Rally Point News","url":"https://rallypointnews.com/recent/","isPartOf":{{"@id":"https://rallypointnews.com/#website"}}}}</script></head><body><header><div>Rally Point News</div><h1>Recent Headlines</h1><p>A chronological view of the latest headlines in the Rally Point news radar. Links go directly to the original publishers.</p><nav><a href="/">Top Stories</a><a href="/#grid">The Wire</a><a href="/recent/">Recent</a><a href="/sources/">Sources</a><a href="/about/">About</a></nav></header><main>{rows}</main><footer>Updated from the newsroom dataset: {e(data.get("generated_at"))} · <a href="/privacy/">Privacy</a></footer></body></html>'''
out=ROOT/"recent"/"index.html";out.parent.mkdir(exist_ok=True);out.write_text(page,encoding="utf-8")
print(f"Built recent-headlines page with {len(stories)} attributed links.")
