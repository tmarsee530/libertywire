#!/usr/bin/env python3
"""Select a small deterministic queue of storylines for the AI brief writer."""
from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STORYLINES=ROOT/'data'/'storylines.json';HISTORY=ROOT/'data'/'history.json';OUT=ROOT/'data'/'writer_queue.json'
MAX_CANDIDATES=8

def substantive(payload):return {k:v for k,v in payload.items() if k!='generated_at'}

def main():
    data=json.loads(STORYLINES.read_text());history={}
    if HISTORY.exists():
        try:history={x.get('id'):x for x in json.loads(HISTORY.read_text()).get('storylines',[]) if x.get('id')}
        except (json.JSONDecodeError,OSError):history={}
    candidates=[]
    for s in data.get('storylines',[]):
        source_count=int(s.get('source_count') or 0);flags=set(s.get('risk_flags') or []);score=float(s.get('importance_score') or 0)
        if source_count<2:continue
        # Risk flags identify stories that require unusually strong human/editorial judgment.
        # Keep them out of the unattended publication queue entirely; the public wire can
        # still show attributed coverage, but autonomous original synthesis must be safer.
        if flags:continue
        h=history.get(s.get('id'),{});growth=max(0,source_count-int(h.get('initial_source_count') or source_count))
        priority=round(score+min(source_count,5)*1.5+min(growth,3)*1.25,2)
        candidates.append({'storyline_id':s.get('id'),'title':s.get('title'),'priority_score':priority,'importance_score':score,'source_count':source_count,'sources':s.get('sources',[]),'status':s.get('status'),'risk_flags':[],'coverage':s.get('coverage',[])[:6],'history':{'first_seen':h.get('first_seen'),'last_seen':h.get('last_seen'),'max_source_count':h.get('max_source_count'),'source_growth':growth},'reason':'multi-source, lower-risk ranked candidate; requires fresh verification before publication'})
    candidates.sort(key=lambda x:(x['priority_score'],x['source_count']),reverse=True)
    payload={'generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'candidate_count':min(len(candidates),MAX_CANDIDATES),'candidates':candidates[:MAX_CANDIDATES]}
    if OUT.exists():
        try:
            old=json.loads(OUT.read_text())
            if substantive(old)==substantive(payload):
                print(f"Writer queue unchanged; {payload['candidate_count']} candidates")
                return
        except (json.JSONDecodeError,OSError):pass
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n');print(f"Built writer queue with {payload['candidate_count']} candidates")
if __name__=='__main__':main()
