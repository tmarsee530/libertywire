#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
from html import escape
import json
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'briefs' / 'index.html'
DATA = ROOT / 'data' / 'briefs.json'

START = '<!-- RALLY_BRIEFS_STATIC_START -->'
END = '<!-- RALLY_BRIEFS_STATIC_END -->'


def fmt_date(value):
    if not value:
        return ''
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.strftime('%B %-d, %Y')
    except Exception:
        return ''


def build_html(briefs):
    cards = []
    for b in briefs:
        title = escape(str(b.get('title') or 'Rally Brief'))
        url = escape(str(b.get('url') or '#'), quote=True)
        desc = escape(str(b.get('description') or ''))
        date = fmt_date(b.get('published_at'))
        sources = b.get('source_count')
        meta = ['<span class="label">Rally Brief</span>']
        if date:
            meta.append(escape(date))
        if sources:
            meta.append(f'{int(sources)} sources')
        meta_html = ' · '.join(meta)
        cards.append(
            f'<article class="brief"><div class="meta">{meta_html}</div>'
            f'<h3><a href="{url}">{title}</a></h3>'
            + (f'<p>{desc}</p>' if desc else '')
            + '</article>'
        )
    if not cards:
        return '<p class="empty">No Rally Point Briefs have been published yet.</p>'
    return ''.join(cards)


def main():
    page = INDEX.read_text()
    data = json.loads(DATA.read_text()) if DATA.exists() else {'briefs': []}
    briefs = data.get('briefs') if isinstance(data, dict) else []
    if not isinstance(briefs, list):
        briefs = []
    rendered = f'{START}{build_html(briefs)}{END}'

    pattern = re.compile(re.escape(START) + r'.*?' + re.escape(END), re.S)
    if pattern.search(page):
        updated = pattern.sub(rendered, page, count=1)
    else:
        target = '<section id="briefList" aria-live="polite"><p class="empty">Loading Rally Briefs…</p></section>'
        replacement = f'<section id="briefList" aria-live="polite">{rendered}</section>'
        if target not in page:
            raise SystemExit('Could not locate briefList section in briefs/index.html')
        updated = page.replace(target, replacement, 1)

    # Keep the JS enhancement, but do not force a placeholder before fetch completes.
    updated = updated.replace("const list=document.getElementById('briefList');try{", "const list=document.getElementById('briefList');try{")

    if updated != page:
        INDEX.write_text(updated)
        print(f'Rendered {len(briefs)} published Brief links into briefs/index.html')
    else:
        print('Brief index static links already current')


if __name__ == '__main__':
    main()
