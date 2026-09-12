#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'index.html'
s=p.read_text()
css='<link rel="stylesheet" href="assets/homepage-v2.css?v=4">'
js='<script src="assets/homepage-v2.js?v=4" defer></script>'
changed=False
for old in (
    '<link rel="stylesheet" href="assets/homepage-v2.css">',
    '<link rel="stylesheet" href="assets/homepage-v2.css?v=1">',
    '<link rel="stylesheet" href="assets/homepage-v2.css?v=2">',
    '<link rel="stylesheet" href="assets/homepage-v2.css?v=3">',
):
    if old in s:
        s=s.replace(old,css);changed=True
for old in (
    '<script src="assets/homepage-v2.js" defer></script>',
    '<script src="assets/homepage-v2.js?v=1" defer></script>',
    '<script src="assets/homepage-v2.js?v=2" defer></script>',
    '<script src="assets/homepage-v2.js?v=3" defer></script>',
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
if 'AUTO-CHECKS EVERY 60 SECONDS' in s:
    s=s.replace('AUTO-CHECKS EVERY 60 SECONDS','WIRE CHECKS EVERY 60 SECONDS');changed=True
if changed:p.write_text(s);print('Installed homepage v2 presentation layer')
else:print('Homepage v2 already installed')
