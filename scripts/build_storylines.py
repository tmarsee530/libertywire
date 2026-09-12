#!/usr/bin/env python3
"""Build deterministic, persistent storyline intelligence without paid AI calls."""
from __future__ import annotations
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];NEWS=ROOT/'data'/'news.json';OUT=ROOT/'data'/'storylines.json'
STOP={'this','that','with','from','have','will','into','after','over','about','says','said','amid','their','they','what','when','where','which','while','could','would','should','more','than','news','report','reports','live','update','updates'}
IMPACT=('supreme court','congress','senate','house','president','white house','governor','election','war','economy','inflation','jobs','federal reserve','shutdown','border','tariff','court')
RISK=('accused','alleged','arrested','indicted','charged','dead','dies','killed','election called','projected winner','bankruptcy','insider trading','fraud')
def tokens(title):return {x for x in re.findall(r"[a-z0-9']{4,}",(title or '').lower()) if x not in STOP}
def sim(a,b):
    if not a or not b:return 0
    return len(a&b)/max(1,min(len(a),len(b)))
def cluster(stories):
    groups=[]
    for s in stories:
        t=tokens(s.get('title'));best=None;best_score=0
        for g in groups:
            if s.get('source') in g['sources']:continue
            score=sim(t,g['tokens'])
            if score>best_score:best,best_score=g,score
        if best and best_score>=.42:
            best['stories'].append(s);best['sources'].add(s.get('source'));best['tokens']|=t
        else:groups.append({'stories':[s],'sources':{s.get('source')},'tokens':set(t)})
    return groups
def main():
    news=json.loads(NEWS.read_text());now=datetime.now(timezone.utc);out=[]
    for g in cluster(news.get('stories',[])):
        ss=sorted(g['stories'],key=lambda s:s.get('published_epoch') or 0,reverse=True);lead=ss[0];title=lead.get('title','');lower=title.lower();sources=sorted(x for x in g['sources'] if x)
        newest=max((s.get('published_epoch') or 0 for s in ss),default=0);age=(now.timestamp()-newest)/60 if newest else 10**9
        impact=sum(1 for x in IMPACT if x in lower);risk=[x for x in RISK if x in lower]
        score=round(len(sources)*4+impact*2+max(0,240-age)/240,2)
        identity=' '.join(sorted(g['tokens']))[:300] or title.lower();sid=hashlib.sha1(identity.encode()).hexdigest()[:12]
        out.append({'id':sid,'title':title,'importance_score':score,'source_count':len(sources),'sources':sources,'newest_epoch':newest,'newest_date':lead.get('date'),'risk_flags':risk,'status':'developing' if len(sources)>=3 and age<=90 else 'active','coverage':[{'source':s.get('source'),'title':s.get('title'),'link':s.get('link'),'date':s.get('date')} for s in ss[:8]]})
    out.sort(key=lambda x:x['importance_score'],reverse=True)
    payload={'generated_at':now.isoformat().replace('+00:00','Z'),'storyline_count':len(out),'multi_source_count':sum(1 for x in out if x['source_count']>=2),'developing_count':sum(1 for x in out if x['status']=='developing'),'storylines':out[:500]}
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n');print(f"Built {len(out)} storylines; {payload['multi_source_count']} multi-source; {payload['developing_count']} developing")
if __name__=='__main__':main()
