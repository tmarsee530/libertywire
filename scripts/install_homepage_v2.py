#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'index.html'
s=p.read_text()
css='<link rel="stylesheet" href="assets/homepage-v2.css">'
js='<script src="assets/homepage-v2.js" defer></script>'
changed=False
if css not in s:
    s=s.replace('</head>',css+'\n</head>',1);changed=True
if js not in s:
    s=s.replace('</body>',js+'\n</body>',1);changed=True
if 'Breaking News, Every Minute' in s:
    s=s.replace('RALLY POINT NEWS — Breaking News, Every Minute','RALLY POINT NEWS — Multi-Source News Intelligence');changed=True
if 'AUTO-CHECKS EVERY 60 SECONDS' in s:
    s=s.replace('AUTO-CHECKS EVERY 60 SECONDS','WIRE CHECKS EVERY 60 SECONDS');changed=True
if changed:p.write_text(s);print('Installed homepage v2 presentation layer')
else:print('Homepage v2 already installed')
