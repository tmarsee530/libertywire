#!/usr/bin/env python3
"""Maintain a bounded deterministic history of Rally Point storylines."""
from __future__ import annotations
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STORYLINES=ROOT/"data"/"storylines.json";OUT=ROOT/"data"/"history.json"
MAX_ENTRIES=1000;RETENTION_DAYS=30;MAX_TITLES=16;MAX_COVERAGE=40

def parse_dt(value):
    if not value:return None
    try:return datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:return None

def coverage_key(item):return (item.get("source") or "",item.get("link") or "")
def clamp_dt(value,now):
    dt=parse_dt(value)
    if not dt:return None
    # Bad publisher timestamps can otherwise pin a storyline in the future and
    # distort Winno-style ordering/retention. Allow only a small clock skew.
    return now if dt>now+timedelta(minutes=10) else dt
def substantive(payload):return {k:v for k,v in payload.items() if k!="generated_at"}

def main():
    now=datetime.now(timezone.utc);cutoff=now-timedelta(days=RETENTION_DAYS)
    current=json.loads(STORYLINES.read_text()) if STORYLINES.exists() else {"storylines":[]}
    old={"storylines":[]}
    if OUT.exists():
        try:old=json.loads(OUT.read_text())
        except (json.JSONDecodeError,OSError):pass
    prior={x.get("id"):x for x in old.get("storylines",[]) if x.get("id")}
    merged=[]
    for item in current.get("storylines",[]):
        sid=item.get("id")
        if not sid:continue
        prev=prior.get(sid,{})
        titles=list(prev.get("title_history",[]));title=item.get("title") or ""
        if title and title not in titles:titles.append(title)
        titles=titles[-MAX_TITLES:]
        prior_cov={coverage_key(x):x for x in prev.get("coverage",[]) if coverage_key(x)!=("","")}
        additions=[]
        for cov in item.get("coverage",[]):
            key=coverage_key(cov)
            if key==("",""):continue
            if key not in prior_cov:additions.append(cov)
            prior_cov[key]=cov
        normalized_cov=[]
        for cov in prior_cov.values():
            safe=clamp_dt(cov.get("date"),now)
            normalized_cov.append({**cov,"date":(safe or now).isoformat().replace("+00:00","Z")})
        coverage=sorted(normalized_cov,key=lambda x:x.get("date") or "",reverse=True)[:MAX_COVERAGE]
        sources=sorted(set(prev.get("sources",[]))|set(item.get("sources",[])))
        raw_newest=item.get("newest_date") or prev.get("last_seen")
        safe_newest=clamp_dt(raw_newest,now)
        newest=(safe_newest or now).isoformat().replace("+00:00","Z")
        changes=[]
        for change in prev.get("changes",[]):
            safe_at=clamp_dt(change.get("at"),now)
            added=[]
            for x in change.get("coverage_added",[]):
                safe_date=clamp_dt(x.get("date"),now)
                added.append({**x,"date":(safe_date or now).isoformat().replace("+00:00","Z")})
            changes.append({**change,"at":(safe_at or now).isoformat().replace("+00:00","Z"),"coverage_added":added})
        if additions or set(item.get("sources",[]))-set(prev.get("current_sources",[])) or (prev and title!=prev.get("current_title")):
            changes.append({"at":newest,"source_count":item.get("source_count",0),"new_sources":sorted(set(item.get("sources",[]))-set(prev.get("current_sources",[]))),"coverage_added":[{"source":x.get("source"),"title":x.get("title"),"link":x.get("link"),"date":((clamp_dt(x.get("date"),now) or now).isoformat().replace("+00:00","Z"))} for x in additions[:8]]})
        record={"id":sid,"current_title":title,"title_history":titles,"first_seen":prev.get("first_seen") or now.isoformat().replace("+00:00","Z"),"last_seen":newest,"max_source_count":max(prev.get("max_source_count",0),item.get("source_count",0)),"current_source_count":item.get("source_count",0),"max_source_family_count":max(prev.get("max_source_family_count",0),item.get("source_family_count",0)),"current_source_family_count":item.get("source_family_count",0),"current_sources":sorted(item.get("sources",[])),"sources":sources,"status":item.get("status","active"),"risk_flags":item.get("risk_flags",[]),"coverage":coverage,"changes":changes[-20:]}
        merged.append(record)
    active_ids={x.get("id") for x in current.get("storylines",[])}
    for sid,record in prior.items():
        if sid in active_ids:continue
        last=parse_dt(record.get("last_seen"))
        if last and last>=cutoff:merged.append(record)
    merged.sort(key=lambda x:parse_dt(x.get("last_seen")) or datetime.min.replace(tzinfo=timezone.utc),reverse=True)
    merged=merged[:MAX_ENTRIES]
    payload={"generated_at":now.isoformat().replace("+00:00","Z"),"retention_days":RETENTION_DAYS,"storyline_count":len(merged),"storylines":merged}
    if OUT.exists():
        try:
            if substantive(old)==substantive(payload):
                print(f"History unchanged; {len(merged)} retained storylines")
                return
        except Exception:pass
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n")
    print(f"History updated; {len(merged)} retained storylines")
if __name__=="__main__":main()
