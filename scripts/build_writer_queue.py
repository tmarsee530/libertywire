#!/usr/bin/env python3
"""Select a small deterministic queue of storylines for the AI newsroom writer."""
from __future__ import annotations
import json
import re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STORYLINES=ROOT/'data'/'storylines.json';HISTORY=ROOT/'data'/'history.json';BRIEFS=ROOT/'data'/'briefs.json';OUT=ROOT/'data'/'writer_queue.json'
MAX_CANDIDATES=8
MIN_SOURCES=3
MIN_SOURCE_FAMILIES=2
STOP={'a','an','and','are','as','at','be','been','but','by','for','from','has','have','he','her','his','in','into','is','it','its','new','of','on','or','says','she','that','the','their','this','to','us','u','s','was','were','will','with'}
# Similar outlets are deliberately grouped. A cluster repeated by several outlets in
# one editorial ecosystem is useful discovery evidence, but not independent enough
# by itself for unattended original synthesis.
SOURCE_FAMILIES={
 'Breitbart':'right-commentary','Daily Caller':'right-commentary','Daily Wire':'right-commentary','Hot Air':'right-commentary','National Pulse':'right-commentary','RedState':'right-commentary','WND':'right-commentary',
 'Associated Press':'wire','AP':'wire','Reuters':'wire','NPR':'public-media','CBS News':'broadcast','ABC News':'broadcast','NBC News':'broadcast','CNN':'cable','Fox News':'cable','New York Times':'national-newspaper','Washington Post':'national-newspaper','Axios':'digital-national','Politico':'digital-national',
}
def substantive(payload):return {k:v for k,v in payload.items() if k!='generated_at'}
def tokens(text):return {w for w in re.findall(r"[a-z0-9]+",str(text or '').lower()) if len(w)>2 and w not in STOP}
def family(source):return SOURCE_FAMILIES.get(str(source or '').strip(),str(source or '').strip().lower() or 'unknown')
def source_families(storyline):return sorted({family(x) for x in storyline.get('sources',[]) if x})
def already_published(storyline,published_ids,published_docs):
    sid=storyline.get('id')
    if sid and sid in published_ids:return True
    title_tokens=tokens(storyline.get('title'))
    if len(title_tokens)<3:return False
    for doc_tokens in published_docs:
        overlap=len(title_tokens & doc_tokens)
        if overlap>=3 and overlap/max(1,min(len(title_tokens),len(doc_tokens)))>=0.45:return True
    return False

def main():
    data=json.loads(STORYLINES.read_text());history={};published_ids=set();published_docs=[]
    if HISTORY.exists():
        try:history={x.get('id'):x for x in json.loads(HISTORY.read_text()).get('storylines',[]) if x.get('id')}
        except (json.JSONDecodeError,OSError):history={}
    if BRIEFS.exists():
        try:
            briefs=json.loads(BRIEFS.read_text()).get('briefs',[])
            published_ids={b.get('storyline_id') for b in briefs if b.get('storyline_id')}
            published_docs=[tokens(f"{b.get('title','')} {b.get('description','')}") for b in briefs]
        except (json.JSONDecodeError,OSError):published_ids=set();published_docs=[]
    candidates=[]
    for s in data.get('storylines',[]):
        source_count=int(s.get('source_count') or 0);flags=set(s.get('risk_flags') or []);score=float(s.get('importance_score') or 0);families=source_families(s)
        if source_count<MIN_SOURCES:continue
        # Three headlines are not necessarily three independent confirmations.
        # Require coverage spanning at least two source families before a storyline
        # can enter the unattended AI-newsroom queue.
        if len(families)<MIN_SOURCE_FAMILIES:continue
        if flags:continue
        if already_published(s,published_ids,published_docs):continue
        h=history.get(s.get('id'),{});growth=max(0,source_count-int(h.get('initial_source_count') or source_count))
        diversity_bonus=min(len(families),4)*1.5
        priority=round(score+min(source_count,5)*1.25+min(growth,3)*1.25+diversity_bonus,2)
        candidates.append({'storyline_id':s.get('id'),'title':s.get('title'),'priority_score':priority,'importance_score':score,'source_count':source_count,'source_family_count':len(families),'source_families':families,'sources':s.get('sources',[]),'status':s.get('status'),'risk_flags':[],'coverage':s.get('coverage',[])[:6],'history':{'first_seen':h.get('first_seen'),'last_seen':h.get('last_seen'),'max_source_count':h.get('max_source_count'),'source_growth':growth},'publication_requirements':{'fresh_verification':True,'attribute_disputed_claims':True,'distinguish_allegations_from_established_facts':True,'preserve_source_links':True,'state_material_uncertainty':True},'reason':'three-plus-source, multi-family, lower-risk candidate; requires fresh verification before publication'})
    candidates.sort(key=lambda x:(x['priority_score'],x['source_family_count'],x['source_count']),reverse=True)
    payload={'generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'policy':{'minimum_sources':MIN_SOURCES,'minimum_source_families':MIN_SOURCE_FAMILIES,'risk_flagged_storylines_allowed':False,'fresh_verification_required':True},'candidate_count':min(len(candidates),MAX_CANDIDATES),'candidates':candidates[:MAX_CANDIDATES]}
    if OUT.exists():
        try:
            old=json.loads(OUT.read_text())
            if substantive(old)==substantive(payload):
                print(f"Writer queue unchanged; {payload['candidate_count']} candidates")
                return
        except (json.JSONDecodeError,OSError):pass
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n');print(f"Built writer queue with {payload['candidate_count']} candidates")
if __name__=='__main__':main()
