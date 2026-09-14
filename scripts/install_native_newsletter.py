#!/usr/bin/env python3
from pathlib import Path
import re

p=Path(__file__).resolve().parents[1]/'index.html'
s=p.read_text()
card='''<div class="newsletter-card" id="briefing"><h2>Get The Rally Brief</h2><p>A concise email built around the strongest verified stories, original Rally Briefs, and source links you can inspect.</p><a class="newsletter-native-cta" data-rp-event="newsletter_signup_cta_click" href="newsletter/">Subscribe free to The Rally Brief →</a><p class="newsletter-note">Free to subscribe. Unsubscribe anytime.</p></div>'''
ns,count=re.subn(r'<div class="newsletter-card"[^>]*>.*?</div>',card,s,count=1,flags=re.S)
ns=ns.replace('<a href="#briefing">Newsletter</a>','<a href="newsletter/" data-rp-event="newsletter_nav_click">Newsletter</a>')
if ns!=s:
    p.write_text(ns)
    print('Installed native Rally Brief newsletter entry points')
else:
    print('Native Rally Brief newsletter entry points already installed')
