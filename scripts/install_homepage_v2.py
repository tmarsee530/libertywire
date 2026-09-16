#!/usr/bin/env python3
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1];p=root/'index.html';s=p.read_text();changed=False
css='<link rel="stylesheet" href="assets/homepage-v2.css?v=9">';js='<script src="assets/homepage-v2.js?v=9" defer></script>'
ns=re.sub(r'<link rel="stylesheet" href="assets/homepage-v2\.css(?:\?v=\d+)?">',css,s)
if ns!=s:s=ns;changed=True
ns=re.sub(r'<script src="assets/homepage-v2\.js(?:\?v=\d+)?" defer></script>',js,s)
if ns!=s:s=ns;changed=True
if css not in s:s=s.replace('</head>',css+'\n</head>',1);changed=True
if js not in s:s=s.replace('</body>',js+'\n</body>',1);changed=True
if '<a class="skip-link" href="#main-content">Skip to main content</a>' not in s:s=s.replace('<body>','<body>\n<a class="skip-link" href="#main-content">Skip to main content</a>',1);changed=True
if '<main>' in s:s=s.replace('<main>','<main id="main-content">',1);changed=True
for a,b in {
 'Rally Point News — AI-Native Multi-Source Newsroom':'Rally Point News — Top Stories & The Wire',
 'Rally Point News — Top Stories, Rally Briefs & Live Headlines':'Rally Point News — Top Stories & The Wire',
 'Original multi-source reporting synthesized by the Rally Point News AI newsroom, with sources and uncertainty kept visible.':'Top stories and a fast, continuously updated wire of headlines from across the news landscape.',
 'Top stories ranked by importance, original source-based Rally Briefs, and live headlines from across the news landscape.':'Top stories and a fast, continuously updated wire of headlines from across the news landscape.'
}.items():
 if a in s:s=s.replace(a,b);changed=True
# The front page is deliberately stripped to the two core Drudge-like surfaces.
nav='''<!-- RALLY_POINT_CORE_NAV_START -->
<nav class="newsroom-nav newsroom-nav-core" aria-label="Rally Point sections"><a href="#lead">Top Stories</a><a href="#grid">The Wire</a></nav>
<!-- RALLY_POINT_CORE_NAV_END -->'''
m=re.search(r'<!-- RALLY_POINT_CORE_NAV_START -->.*?<!-- RALLY_POINT_CORE_NAV_END -->',s,re.S)
if m:
 if m.group()!=nav:s=s[:m.start()]+nav+s[m.end():];changed=True
elif '</header>' in s:s=s.replace('</header>','</header>\n'+nav,1);changed=True
# Remove report/archive promotional blocks and methodology chrome from the front page.
for pattern in [r'\n?<!-- RALLY_POINT_METHOD_NOTE_START -->.*?<!-- RALLY_POINT_METHOD_NOTE_END -->\n?',r'\n?<!-- RALLY_POINT_AI_NEWSROOM_START -->.*?<!-- RALLY_POINT_AI_NEWSROOM_END -->\n?',r'\n?<!-- RALLY_POINT_LATEST_BRIEF_START -->.*?<!-- RALLY_POINT_LATEST_BRIEF_END -->\n?']:
 ns=re.sub(pattern,'\n',s,flags=re.S)
 if ns!=s:s=ns;changed=True
for old in ('Rally Wire','Source Monitor'):
 if f'<div class="section-label"><span>{old}</span>' in s:s=s.replace(f'<div class="section-label"><span>{old}</span>','<div class="section-label"><span>The Wire</span>',1);changed=True
ns=re.sub(r'<span>The Wire</span><small>.*?</small>','<span>The Wire</span><small>Headlines from across the news landscape</small>',s,count=1,flags=re.S)
if ns!=s:s=ns;changed=True
if changed:p.write_text(s);print('Installed stripped-down Top Stories + The Wire homepage')
else:print('Top Stories + The Wire homepage already installed')
