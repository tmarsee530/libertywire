#!/usr/bin/env python3
from pathlib import Path

p=Path(__file__).resolve().parents[1]/'index.html'
s=p.read_text()
start='<!-- RALLY_POINT_DISCOVERY_START -->'
end='<!-- RALLY_POINT_DISCOVERY_END -->'
description='Track developing stories across dozens of news sources with multi-source storyline intelligence and original Rally Briefs.'
block=f'''<!-- RALLY_POINT_DISCOVERY_START -->
<link rel="canonical" href="https://rallypointnews.com/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Rally Point News">
<meta property="og:title" content="Rally Point News — Multi-Source News Intelligence">
<meta property="og:description" content="{description}">
<meta property="og:url" content="https://rallypointnews.com/">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="Rally Point News — Multi-Source News Intelligence">
<meta name="twitter:description" content="{description}">
<script type="application/ld+json">{{"@context":"https://schema.org","@graph":[{{"@type":"Organization","@id":"https://rallypointnews.com/#organization","name":"Rally Point News","url":"https://rallypointnews.com/"}},{{"@type":"WebSite","@id":"https://rallypointnews.com/#website","url":"https://rallypointnews.com/","name":"Rally Point News","publisher":{{"@id":"https://rallypointnews.com/#organization"}},"description":"Multi-source news intelligence and original Rally Briefs."}}]}}</script>
<!-- RALLY_POINT_DISCOVERY_END -->'''
changed=False
old='<meta name="description" content="Rally Point News — a real-time conservative news aggregator pulling from 31 sources.">'
new=f'<meta name="description" content="{description}">'
if old in s:
    s=s.replace(old,new,1);changed=True
if start in s and end in s:
    before=s.split(start,1)[0]
    after=s.split(end,1)[1]
    merged=before+block+after
    if merged!=s:
        s=merged;changed=True
else:
    s=s.replace('</head>',block+'\n</head>',1);changed=True
if changed:
    p.write_text(s)
    print('Installed discovery metadata')
else:
    print('Discovery metadata already current')
