#!/usr/bin/env python3
from pathlib import Path
import json
import re
from html import escape

root=Path(__file__).resolve().parents[1]
p=root/'index.html'
s=p.read_text()
css='<link rel="stylesheet" href="assets/homepage-v2.css?v=6">'
js='<script src="assets/homepage-v2.js?v=6" defer></script>'
changed=False

for old in (
    '<link rel="stylesheet" href="assets/homepage-v2.css">',
    '<link rel="stylesheet" href="assets/homepage-v2.css?v=1">',
    '<link rel="stylesheet" href="assets/homepage-v2.css?v=2">',
    '<link rel="stylesheet" href="assets/homepage-v2.css?v=3">',
    '<link rel="stylesheet" href="assets/homepage-v2.css?v=4">',
    '<link rel="stylesheet" href="assets/homepage-v2.css?v=5">',
):
    if old in s:
        s=s.replace(old,css);changed=True
for old in (
    '<script src="assets/homepage-v2.js" defer></script>',
    '<script src="assets/homepage-v2.js?v=1" defer></script>',
    '<script src="assets/homepage-v2.js?v=2" defer></script>',
    '<script src="assets/homepage-v2.js?v=3" defer></script>',
    '<script src="assets/homepage-v2.js?v=4" defer></script>',
    '<script src="assets/homepage-v2.js?v=5" defer></script>',
):
    if old in s:
        s=s.replace(old,js);changed=True
if css not in s:
    s=s.replace('</head>',css+'\n</head>',1);changed=True
if js not in s:
    s=s.replace('</body>',js+'\n</body>',1);changed=True
if '<a class="skip-link" href="#main-content">Skip to main content</a>' not in s:
    s=s.replace('<body>','<body>\n<a class="skip-link" href="#main-content">Skip to main content</a>',1);changed=True
if '<main>' in s:
    s=s.replace('<main>','<main id="main-content">',1);changed=True
if 'Breaking News, Every Minute' in s:
    s=s.replace('RALLY POINT NEWS — Breaking News, Every Minute','RALLY POINT NEWS — Multi-Source News Intelligence');changed=True
if 'MAX_DATASET_AGE_MIN=45' in s:
    s=s.replace('MAX_DATASET_AGE_MIN=45','MAX_DATASET_AGE_MIN=180');changed=True
if 'The shared newsroom is unavailable, so Rally Point is using its backup live-feed system.' in s:
    s=s.replace('The shared newsroom is unavailable, so Rally Point is using its backup live-feed system.','The newsroom refresh is delayed. Rally Point is temporarily using its backup wire.');changed=True
if 'WIRE CHECKS EVERY 60 SECONDS' in s:
    s=s.replace('WIRE CHECKS EVERY 60 SECONDS','PAGE CHECKS FOR UPDATES EVERY 60 SECONDS');changed=True
if 'AUTO-CHECKS EVERY 60 SECONDS' in s:
    s=s.replace('AUTO-CHECKS EVERY 60 SECONDS','PAGE CHECKS FOR UPDATES EVERY 60 SECONDS');changed=True

ns=re.sub(r'<div class="tone-index"[^>]*>.*?</div>','',s,count=1,flags=re.S)
if ns!=s:
    s=ns;changed=True

old_newsletter='<div class="newsletter-card"><h2>Get The Briefing</h2><p>Five stories. One take. Every morning.</p><iframe src="https://rallypointnews.substack.com/embed" width="100%" height="140" style="border:none;background:transparent;" frameborder="0" scrolling="no"></iframe></div>'
new_newsletter='<div class="newsletter-card"><h2>Get the Rally Brief</h2><p>A concise morning email built around the stories that matter most, with links back to the reporting behind them.</p><iframe title="Subscribe to the Rally Point News newsletter" src="https://rallypointnews.substack.com/embed" width="100%" height="140" style="border:none;background:transparent;" frameborder="0" scrolling="no"></iframe><p class="newsletter-note">Free to subscribe. Unsubscribe anytime.</p></div>'
if old_newsletter in s:
    s=s.replace(old_newsletter,new_newsletter);changed=True
elif 'title="Subscribe to the Rally Point News newsletter"' not in s and 'https://rallypointnews.substack.com/embed' in s:
    s=s.replace('<iframe src="https://rallypointnews.substack.com/embed"','<iframe title="Subscribe to the Rally Point News newsletter" src="https://rallypointnews.substack.com/embed"');changed=True

# Core navigation and latest original Brief are rendered into the HTML itself so
# they remain visible and crawlable even when the enhancement script fails.
nav='''<!-- RALLY_POINT_CORE_NAV_START -->
<nav class="newsroom-nav newsroom-nav-core" aria-label="Rally Point sections"><a href="#lead-wrap">Top Story</a><a href="#grid">The Wire</a><a href="briefs/">Rally Briefs</a><a href="games/" data-rp-event="games_nav_click">Games</a><a href="sources/">Sources</a><a href="newsletter/" data-rp-event="newsletter_nav_click">Newsletter</a></nav>
<!-- RALLY_POINT_CORE_NAV_END -->'''
existing_nav=re.search(r'<!-- RALLY_POINT_CORE_NAV_START -->.*?<!-- RALLY_POINT_CORE_NAV_END -->',s,flags=re.S)
if existing_nav:
    if existing_nav.group(0)!=nav:
        s=s[:existing_nav.start()]+nav+s[existing_nav.end():]
        changed=True
else:
    anchor='</header>'
    if anchor in s:
        s=s.replace(anchor,anchor+'\n'+nav,1);changed=True

briefs_path=root/'data'/'briefs.json'
if briefs_path.exists():
    try:
        latest=(json.loads(briefs_path.read_text()).get('briefs') or [])[0]
    except (json.JSONDecodeError,IndexError,TypeError):
        latest=None
    if latest:
        title=escape(str(latest.get('title') or 'Read the latest Rally Brief'))
        url=escape(str(latest.get('url') or '/briefs/'),quote=True)
        description=escape(str(latest.get('description') or 'Original context and synthesis from the Rally Point News Desk.'))
        brief=f'''<!-- RALLY_POINT_LATEST_BRIEF_START -->
<aside class="latest-brief latest-brief-core" aria-label="Latest Rally Brief"><div class="brief-eyebrow">Latest Rally Brief</div><div class="brief-copy"><a class="brief-title" href="{url}">{title}</a><div class="brief-dek">{description}</div><a class="brief-cta" href="{url}">Read the Brief →</a></div></aside>
<!-- RALLY_POINT_LATEST_BRIEF_END -->'''
        existing=re.search(r'<!-- RALLY_POINT_LATEST_BRIEF_START -->.*?<!-- RALLY_POINT_LATEST_BRIEF_END -->',s,flags=re.S)
        if existing:
            if existing.group(0)!=brief:
                s=s[:existing.start()]+brief+s[existing.end():];changed=True
        else:
            marker='<div class="section-label"><span>The Wire</span>'
            if marker in s:
                s=s.replace(marker,brief+'\n'+marker,1);changed=True

if changed:
    p.write_text(s)
    print('Installed homepage v2 presentation layer with server-rendered navigation and latest Brief')
else:
    print('Homepage v2 already installed')
