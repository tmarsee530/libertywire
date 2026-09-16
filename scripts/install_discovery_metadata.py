#!/usr/bin/env python3
from pathlib import Path
import re

p=Path(__file__).resolve().parents[1]/'index.html'
s=p.read_text()
start='<!-- RALLY_POINT_DISCOVERY_START -->'
end='<!-- RALLY_POINT_DISCOVERY_END -->'
title='Rally Point News — Conservative News & Breaking Headlines'
description='Conservative news and breaking headlines from dozens of sources, organized by developing story and updated throughout the day.'
block=f'''<!-- RALLY_POINT_DISCOVERY_START -->
<link rel="canonical" href="https://rallypointnews.com/">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<meta name="googlebot" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta name="application-name" content="Rally Point News">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Rally Point News">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="https://rallypointnews.com/">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<script type="application/ld+json">{{"@context":"https://schema.org","@graph":[{{"@type":"Organization","@id":"https://rallypointnews.com/#organization","name":"Rally Point News","url":"https://rallypointnews.com/"}},{{"@type":"WebSite","@id":"https://rallypointnews.com/#website","url":"https://rallypointnews.com/","name":"Rally Point News","alternateName":"Rally Point","publisher":{{"@id":"https://rallypointnews.com/#organization"}},"description":"{description}","inLanguage":"en-US"}}]}}</script>
<!-- RALLY_POINT_DISCOVERY_END -->'''
changed=False
ns=re.sub(r'<title>.*?</title>',f'<title>{title}</title>',s,count=1,flags=re.S)
if ns!=s:s=ns;changed=True
ns=re.sub(r'<meta name="description" content="[^"]*">',f'<meta name="description" content="{description}">',s,count=1)
if ns!=s:s=ns;changed=True
if start in s and end in s:
    before=s.split(start,1)[0];after=s.split(end,1)[1];merged=before+block+after
    if merged!=s:s=merged;changed=True
else:
    s=s.replace('</head>',block+'\n</head>',1);changed=True
if changed:p.write_text(s);print('Installed current Rally Point search identity metadata')
else:print('Discovery metadata already current')
