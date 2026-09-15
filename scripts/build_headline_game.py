#!/usr/bin/env python3
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
STORYLINES=ROOT/'data'/'storylines.json';BRIEFS=ROOT/'data'/'briefs.json';OUTPUT=ROOT/'data'/'headline_game.json'
CANDIDATES=['court','judge','house','votes','voter','trade','storm','plane','crash','press','media','union','money','stock','banks','rates','peace','troop','naval','china','india','japan','crime','trial','order','state','local','mayor','party','polls','power','water','fires','flood','earth','space','virus','drugs','labor','wages','taxes','funds','roads','faith','legal','rules','rights','video','radio','chief','staff','watch']
CANDIDATES=[w for w in CANDIDATES if len(w)==5]
STOP={'the','and','for','with','from','into','after','over','says','said','news','today'}

def load_json(path,default):
    if not path.exists():return default
    return json.loads(path.read_text())
def today_eastern():return datetime.now(ZoneInfo('America/New_York')).date().isoformat()
def tokenize(text):return re.findall(r'[a-z]+',(text or '').lower())
def meaningful(text):return {t for t in tokenize(text) if len(t)>=4 and t not in STOP}

def select_puzzle(storylines,excluded_answers=None):
    excluded={w.lower() for w in (excluded_answers or set()) if w};ranked=[]
    for idx,story in enumerate(storylines):
        if story.get('risk_flags'):continue
        tokens=set(tokenize(story.get('title') or ''))
        for word in CANDIDATES:
            if word in excluded:continue
            if word in tokens:
                score=float(story.get('importance_score') or 0)+float(story.get('source_count') or 0)*2-idx*.02
                ranked.append((score,word,story))
    if ranked:
        ranked.sort(key=lambda x:(-x[0],x[1]));_,answer,story=ranked[0];return answer,story
    available=[w for w in CANDIDATES if w not in excluded] or CANDIDATES
    seed=sum(ord(ch) for ch in today_eastern());answer=available[seed%len(available)];story=next((s for s in storylines if not s.get('risk_flags')),{});return answer,story

def related_brief(story):
    briefs=load_json(BRIEFS,{}).get('briefs') or [];sid=story.get('id');exact=next((b for b in briefs if sid and b.get('storyline_id')==sid),None)
    if exact:return exact
    st=meaningful(story.get('title') or '');ranked=[]
    for b in briefs:
        overlap=len(st & meaningful((b.get('title') or '')+' '+(b.get('description') or '')))
        if overlap>=2:ranked.append((overlap,b))
    return max(ranked,key=lambda x:x[0])[1] if ranked else None

def masked_title(title,answer):
    # Keep the news connection recognizable without producing awkward text such as
    # "Supreme the answer". The blank itself becomes a useful semantic clue.
    return re.sub(r'\b'+re.escape(answer)+r'\b','_____',title,flags=re.I)

def make_clues(answer,story):
    title=story.get('title') or "Today's news picture";count=int(story.get('source_count') or 0)
    first=answer[0].upper();last=answer[-1].upper();vowels=sum(ch in 'aeiou' for ch in answer.lower())
    middle=answer[1:-1].upper() if len(answer)>2 else answer.upper()
    clue1='It is a five-letter word connected to one of today’s significant news stories.'
    if count>1:clue1=f'It is a five-letter word tied to a storyline Rally Point is seeing across {count} publishers.'
    clue2='Complete the news signal: '+masked_title(title,answer)
    clue3=f'The word contains {vowels} vowel'+('' if vowels==1 else 's')+f' and begins with {first}.'
    clue4=f'It begins with {first}, ends with {last}, and its second letter is {answer[1].upper()}.'
    clue5=f'Final clue: {first} {middle} {last}. Put the letters together.'
    return [clue1,clue2,clue3,clue4,clue5]

def main():
    date=today_eastern();existing=load_json(OUTPUT,{});storylines=load_json(STORYLINES,{}).get('storylines') or []
    if existing.get('puzzle_date')==date and existing.get('answer'):
        answer=existing['answer'].lower();story=next((s for s in storylines if s.get('id')==existing.get('storyline_id')),None)
        if not story:story={'id':existing.get('storyline_id'),'title':existing.get('context_title'),'source_count':existing.get('source_count'),'sources':existing.get('sources') or [],'coverage':[{'source':existing.get('source_name'),'link':existing.get('source_url')}]}
    else:
        previous_answer=(existing.get('answer') or '').lower() if existing.get('puzzle_date') else ''
        answer,story=select_puzzle(storylines,{previous_answer} if previous_answer else set())
    coverage=story.get('coverage') or [];brief=related_brief(story)
    output={'puzzle_date':date,'answer':answer.upper(),'storyline_id':story.get('id'),'context_title':story.get('title') or "Today's news picture",'source_count':story.get('source_count') or 0,'sources':story.get('sources') or [],'source_name':coverage[0].get('source') if coverage else None,'source_url':coverage[0].get('link') if coverage else None,'rally_url':(brief or {}).get('url') or '/','rally_title':(brief or {}).get('title') or "Back to today's Rally Point news",'clues':make_clues(answer,story),'generated_at':datetime.utcnow().replace(microsecond=0).isoformat()+'Z'}
    if output!=existing:
        OUTPUT.write_text(json.dumps(output,indent=2)+'\n');print(f'Built/refreshed Headline Five news deduction for {date}: {answer.upper()}')
    else:print(f'Headline Five unchanged for {date}.')
if __name__=='__main__':main()
