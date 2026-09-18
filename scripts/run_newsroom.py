#!/usr/bin/env python3
"""Run Rally Point's live-news pipeline with retries, health telemetry, and recovery.

The runner deliberately preserves last-known-good artifacts when a stage fails. It
records the failure, continues stages that can safely use those artifacts, publishes
an operator dashboard, and lets the workflow fail only after diagnostics are saved.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HEALTH = DATA / "newsroom_health.json"
DEAD_LETTERS = DATA / "newsroom_dead_letters.json"
FAST_PATH = DATA / "breaking_fast_path.json"
DASHBOARD = ROOT / "health" / "index.html"
MAX_DEAD_LETTERS = 100

STAGES = [
    ("ingestion", "Source ingestion", "scripts/fetch_news.py", "data/news.json"),
    ("fast_path", "Breaking-news fast path", "scripts/build_breaking_fast_path.py", "data/breaking_fast_path.json"),
    ("clustering", "Story clustering", "scripts/build_storylines.py", "data/storylines.json"),
    ("history", "Timeline history", "scripts/build_history.py", "data/history.json"),
    ("publication", "Timeline publication", "scripts/build_timelines.py", "data/published_timelines.json"),
    ("homepage", "Homepage refresh", "scripts/install_homepage_v2.py", "index.html"),
    ("metadata", "Discovery metadata", "scripts/install_discovery_metadata.py", "index.html"),
    ("recent", "Recent-headlines page", "scripts/build_recent.py", "recent/index.html"),
    ("sitemap", "Sitemap refresh", "scripts/build_sitemaps.py", "sitemap.xml"),
]


def now():
    return datetime.now(timezone.utc)


def iso(value=None):
    return (value or now()).isoformat().replace("+00:00", "Z")


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def age_minutes(value):
    dt = parse_dt(value)
    return round(max(0, (now() - dt).total_seconds() / 60), 1) if dt else None


def run_stage(key, label, script, expected, previous):
    prior = (previous.get("stages") or {}).get(key, {})
    attempts = 3
    started = time.monotonic()
    errors = []
    output = ""
    for attempt in range(1, attempts + 1):
        proc = subprocess.run(
            [sys.executable, script], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        output = (proc.stdout or "").strip()[-3000:]
        if proc.returncode == 0 and (ROOT / expected).exists():
            recovered = attempt > 1 or int(prior.get("consecutive_failures", 0) or 0) > 0
            return {
                "label": label, "status": "RECOVERED" if recovered else "HEALTHY",
                "attempts": attempt, "duration_seconds": round(time.monotonic() - started, 2),
                "completed_at": iso(), "consecutive_failures": 0,
                "artifact": expected, "message": output.splitlines()[-1] if output else "completed",
            }, None
        errors.append(output or f"exit code {proc.returncode}; expected {expected}")
        if attempt < attempts:
            time.sleep(2 ** attempt)
    consecutive = int(prior.get("consecutive_failures", 0) or 0) + 1
    artifact_exists = (ROOT / expected).exists()
    failure = {
        "stage": key, "label": label, "failed_at": iso(), "attempts": attempts,
        "consecutive_failures": consecutive, "recoverable": artifact_exists,
        "artifact_preserved": expected if artifact_exists else None,
        "error": errors[-1][-1200:],
    }
    return {
        "label": label, "status": "FAILED", "attempts": attempts,
        "duration_seconds": round(time.monotonic() - started, 2), "completed_at": iso(),
        "consecutive_failures": consecutive, "artifact": expected,
        "fallback": "last-known-good" if artifact_exists else "unavailable",
        "message": errors[-1][-600:],
    }, failure


def build_signals(stage_results, cycle_started, previous):
    news = load(DATA / "news.json", {})
    storylines = load(DATA / "storylines.json", {})
    history = load(DATA / "history.json", {})
    manifest = load(DATA / "published_timelines.json", {})
    fast_path = load(FAST_PATH, {})
    writer = load(DATA / "writer_queue.json", {})
    newsletter = load(DATA / "newsletter_state.json", {})
    healthy = int(news.get("healthy_source_count", 0) or 0)
    total = int(news.get("source_count", 0) or 0)
    failures = news.get("failed_sources") or []
    failure_pct = round((len(failures) / total) * 100, 1) if total else 100.0
    current = storylines.get("storylines") or []
    story_dates = [parse_dt(x.get("newest_date")) for x in current]
    newest_story = max((x for x in story_dates if x is not None), default=None)
    newest_story = newest_story if newest_story and newest_story <= now() else now()
    records = history.get("storylines") or []
    timeline_dates = [parse_dt(x.get("last_seen")) for x in records]
    newest_timeline = max((x for x in timeline_dates if x is not None), default=None)
    newest_timeline = newest_timeline if newest_timeline and newest_timeline <= now() else now()
    active_queue = False  # legacy writer queue is retained but not part of the live timeline product
    fast_candidates = [x for x in fast_path.get("candidates", []) if x.get("eligible")]
    published_ids = set(manifest.get("ids") or [])
    link_story_ids = {}
    for item in current:
        for coverage in item.get("coverage") or []:
            if coverage.get("link"):
                link_story_ids[coverage["link"]] = item.get("id")
    published_fast = []
    publication_latencies = []
    published_at = parse_dt(manifest.get("generated_at"))
    current_by_id = {x.get("id"): x for x in current if x.get("id")}
    history_by_id = {x.get("id"): x for x in records if x.get("id")}
    outcomes = []
    for candidate in fast_candidates:
        links = candidate.get("corroborating_links", [])
        story_id = next((link_story_ids.get(link) for link in links if link_story_ids.get(link) in published_ids), None)
        if story_id:
            candidate["published_storyline_id"] = story_id
            candidate["published_at"] = manifest.get("generated_at")
            published_fast.append(candidate)
            detected = parse_dt(candidate.get("detected_at"))
            if detected and published_at:
                latency = max(0, (published_at - detected).total_seconds())
                candidate["detection_to_publication_latency_seconds"] = round(latency, 1)
                publication_latencies.append(latency)
            outcomes.append({"candidate_id": candidate.get("id"), "status": "published", "storyline_id": story_id})
            continue

        # Publication requires multiple *material developments*, not merely
        # several publishers repeating one fact. Resolve the candidate's lead
        # report to its actual storyline before deciding whether this is a miss.
        primary_story_id = link_story_ids.get(candidate.get("primary_source_link"))
        target_id = primary_story_id or candidate.get("matched_storyline_id")
        target = history_by_id.get(target_id) or current_by_id.get(target_id) or {}
        material_count = int(target.get("material_update_count", 0) or 0)
        family_count = int(target.get("max_source_family_count", target.get("source_family_count", 0)) or 0)
        coverage_count = len(target.get("coverage") or [])
        if target and (material_count < 2 or family_count < 3 or coverage_count < 3):
            reasons = []
            if material_count < 2: reasons.append("insufficient_material_developments")
            if family_count < 3: reasons.append("insufficient_independent_sources")
            if coverage_count < 3: reasons.append("insufficient_coverage")
            outcomes.append({
                "candidate_id": candidate.get("id"), "status": "editorially_suppressed",
                "storyline_id": target_id, "reason": ",".join(reasons),
            })
        elif target:
            outcomes.append({
                "candidate_id": candidate.get("id"), "status": "missed",
                "storyline_id": target_id, "reason": "publication_threshold_met_but_not_published",
            })
        else:
            outcomes.append({
                "candidate_id": candidate.get("id"), "status": "deferred",
                "storyline_id": None, "reason": "not_yet_resolved_to_a_storyline",
            })
    fast_metrics = dict(fast_path.get("metrics") or {})
    outcome_counts = {name: sum(x["status"] == name for x in outcomes) for name in ("published", "editorially_suppressed", "deferred", "missed")}
    accountable = outcome_counts["published"] + outcome_counts["missed"]
    fast_metrics["published_fast_path_events"] = len(published_fast)
    fast_metrics["high_urgency_capture_pct"] = round(outcome_counts["published"] / accountable * 100, 2) if accountable else 100.0 if fast_candidates else None
    fast_metrics["publication_outcomes"] = outcome_counts
    fast_metrics["true_missed_fast_path_events"] = outcome_counts["missed"]
    fast_path["publication_outcomes"] = outcomes
    fast_metrics["detection_to_publication_latency_seconds"] = round(sorted(publication_latencies)[len(publication_latencies) // 2], 1) if publication_latencies else None
    if fast_path:
        fast_path["metrics"] = fast_metrics
        FAST_PATH.write_text(json.dumps(fast_path, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "cycle": {
            "started_at": iso(cycle_started), "completed_at": iso(),
            "duration_seconds": round((now() - cycle_started).total_seconds(), 2),
            "previous_completed_at": previous.get("cycle", {}).get("completed_at"),
        },
        "ingestion": {
            "last_successful_run": news.get("generated_at"),
            "age_minutes": age_minutes(news.get("generated_at")),
            "configured_sources": total, "successful_sources": healthy,
            "failed_sources": len(failures), "source_failure_pct": failure_pct,
            "failed_source_details": failures[:20], "stories_available": int(news.get("story_count", 0) or 0),
        },
        "content": {
            "last_story_created": iso(newest_story) if newest_story else None,
            "last_story_age_minutes": age_minutes(iso(newest_story)) if newest_story else None,
            "last_timeline_update": iso(newest_timeline) if newest_timeline else None,
            "last_timeline_age_minutes": age_minutes(iso(newest_timeline)) if newest_timeline else None,
            "published_timelines": int(manifest.get("count", 0) or 0),
            "manifest_updated_at": manifest.get("generated_at"),
        },
        "fast_path": fast_metrics,
        "queue": {
            "active": active_queue, "backlog": int(writer.get("candidate_count", 0) or 0) if active_queue else 0,
            "oldest_item_age_minutes": None, "note": "Legacy article-writer queue is inactive; live timelines publish directly.",
        },
        "ai_processing": {"enabled": False, "failures": 0, "note": "Core live pipeline is deterministic and uses no paid AI API."},
        "distribution": {
            "last_job_at": newsletter.get("updated_at"),
            "last_job_status": (newsletter.get("last_broadcast") or {}).get("status") or "NOT_CONFIGURED",
            "affects_core_health": False,
        },
        "stages": stage_results,
    }


def classify(signals):
    alerts = []
    ingestion = signals["ingestion"]
    stages = signals["stages"]
    age = ingestion.get("age_minutes")
    if age is None or age > 15:
        alerts.append(("CRITICAL", "INGESTION_STALE", f"No successful ingestion cycle for {age if age is not None else 'unknown'} minutes."))
    elif age > 10:
        alerts.append(("WARNING", "INGESTION_DELAYED", f"Last successful ingestion is {age} minutes old."))
    if ingestion["successful_sources"] == 0:
        alerts.append(("CRITICAL", "NO_SOURCES", "No source was processed successfully."))
    pct = ingestion["source_failure_pct"]
    if pct >= 50:
        alerts.append(("CRITICAL", "SOURCE_FAILURE_SPIKE", f"{pct}% of configured sources failed."))
    elif pct >= 20:
        alerts.append(("WARNING", "SOURCE_FAILURE_ELEVATED", f"{pct}% of configured sources failed."))
    for key, result in stages.items():
        if result.get("status") == "FAILED":
            severity = "CRITICAL" if key in {"ingestion", "publication", "homepage", "sitemap"} or result.get("consecutive_failures", 0) >= 2 else "WARNING"
            alerts.append((severity, f"STAGE_{key.upper()}_FAILED", f"{result['label']} failed after {result['attempts']} attempts; fallback: {result.get('fallback')}."))
        elif result.get("status") == "RECOVERED":
            alerts.append(("INFO", f"STAGE_{key.upper()}_RECOVERED", f"{result['label']} recovered automatically."))
    story_age = signals["content"].get("last_story_age_minutes")
    if story_age is not None and story_age > 120:
        alerts.append(("WARNING", "NO_MEANINGFUL_UPDATE", f"No current storyline update detected for {story_age} minutes."))
    fast = signals.get("fast_path") or {}
    if fast.get("true_missed_fast_path_events", 0):
        alerts.append(("WARNING", "FAST_PATH_PUBLICATION_GAP", f"{fast['true_missed_fast_path_events']} eligible fast-path event(s) met editorial publication standards but did not reach a timeline this cycle."))
    state = "CRITICAL" if any(x[0] == "CRITICAL" for x in alerts) else "DEGRADED" if any(x[0] == "WARNING" for x in alerts) else "HEALTHY"
    return state, [{"severity": a, "code": b, "message": c} for a, b, c in alerts]


def render_dashboard(payload, dead_letters):
    esc = lambda x: html.escape(str(x if x is not None else "—"))
    state = payload["state"]
    metrics = payload["ingestion"] | payload["content"]
    cards = [
        ("Last ingestion", f"{metrics.get('age_minutes')} min ago"),
        ("Sources", f"{metrics.get('successful_sources')}/{metrics.get('configured_sources')} healthy"),
        ("Source failures", f"{metrics.get('source_failure_pct')}%"),
        ("Published timelines", metrics.get("published_timelines")),
        ("Fast-path events", payload.get("fast_path", {}).get("fast_path_events", 0)),
        ("Fast-path capture", f"{payload.get('fast_path', {}).get('high_urgency_capture_pct')}%" if payload.get("fast_path", {}).get("high_urgency_capture_pct") is not None else "—"),
        ("Last timeline update", f"{metrics.get('last_timeline_age_minutes')} min ago"),
        ("Queue backlog", payload["queue"].get("backlog")),
    ]
    stage_rows = "".join(f"<tr><td>{esc(v['label'])}</td><td><b class='{v['status'].lower()}'>{esc(v['status'])}</b></td><td>{esc(v.get('attempts'))}</td><td>{esc(v.get('duration_seconds'))}s</td><td>{esc(v.get('message'))}</td></tr>" for v in payload["stages"].values())
    alert_rows = "".join(f"<li class='{x['severity'].lower()}'><b>{esc(x['severity'])} · {esc(x['code'])}</b><span>{esc(x['message'])}</span></li>" for x in payload["alerts"]) or "<li><b>No active alerts</b><span>All monitored core signals are within thresholds.</span></li>"
    dlq_rows = "".join(f"<tr><td>{esc(x.get('failed_at'))}</td><td>{esc(x.get('label'))}</td><td>{esc(x.get('consecutive_failures'))}</td><td>{esc(x.get('error'))}</td></tr>" for x in reversed(dead_letters[-12:])) or "<tr><td colspan='4'>No dead-lettered stage failures.</td></tr>"
    card_html = "".join(f"<div><span>{esc(k)}</span><strong>{esc(v)}</strong></div>" for k, v in cards)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Newsroom Health · Rally Point News</title><style>:root{{--ink:#12213a;--muted:#667085;--line:#d9e0ea;--ok:#087443;--warn:#9a6700;--bad:#b42318}}*{{box-sizing:border-box}}body{{margin:0;background:#f5f7fa;color:var(--ink);font:14px/1.45 Arial,sans-serif}}main{{max-width:1160px;margin:auto;padding:28px 16px 60px}}header{{display:flex;justify-content:space-between;gap:20px;align-items:end;border-bottom:3px solid var(--ink);padding-bottom:16px}}h1{{margin:0;font:700 clamp(28px,5vw,48px)/1 Georgia,serif}}.state{{padding:8px 12px;border-radius:999px;color:#fff;background:{'#087443' if state=='HEALTHY' else '#9a6700' if state=='DEGRADED' else '#b42318'};font-weight:800}}.meta{{color:var(--muted);margin:8px 0 0}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:20px 0}}.cards div{{background:#fff;border:1px solid var(--line);padding:15px;border-radius:8px}}.cards span{{display:block;color:var(--muted);font-size:12px;text-transform:uppercase}}.cards strong{{font-size:20px}}section{{background:#fff;border:1px solid var(--line);border-radius:8px;margin:14px 0;padding:18px}}h2{{margin:0 0 12px;font:700 22px Georgia,serif}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:9px;border-bottom:1px solid var(--line);vertical-align:top}}td:last-child{{max-width:430px;overflow-wrap:anywhere}}ul{{list-style:none;padding:0;margin:0}}li{{display:grid;gap:3px;padding:10px;border-bottom:1px solid var(--line)}}li span{{color:var(--muted)}}.healthy,.recovered{{color:var(--ok)}}.warning{{color:var(--warn)}}.critical,.failed{{color:var(--bad)}}footer{{color:var(--muted);font-size:12px;margin-top:16px}}@media(max-width:760px){{header{{align-items:start;flex-direction:column}}.cards{{grid-template-columns:1fr 1fr}}table{{display:block;overflow:auto}}}}@media(max-width:430px){{.cards{{grid-template-columns:1fr}}}}</style></head><body><main><header><div><h1>Newsroom Health</h1><p class="meta">Rally Point News · operational dashboard · unindexed</p></div><div class="state">{esc(state)}</div></header><p class="meta">Cycle completed {esc(payload['cycle']['completed_at'])} · {esc(payload['cycle']['duration_seconds'])} seconds</p><div class="cards">{card_html}</div><section><h2>Active alerts</h2><ul>{alert_rows}</ul></section><section><h2>Pipeline stages</h2><table><thead><tr><th>Stage</th><th>Status</th><th>Attempts</th><th>Time</th><th>Detail</th></tr></thead><tbody>{stage_rows}</tbody></table></section><section><h2>Recent dead letters</h2><table><thead><tr><th>Time</th><th>Stage</th><th>Consecutive</th><th>Error</th></tr></thead><tbody>{dlq_rows}</tbody></table></section><footer>HEALTHY means all core signals are within thresholds. DEGRADED means the newsroom is operating with warnings. CRITICAL means freshness or a core publication stage is failing.</footer></main></body></html>'''


def emit_actions(payload):
    for alert in payload["alerts"]:
        command = "error" if alert["severity"] == "CRITICAL" else "warning" if alert["severity"] == "WARNING" else "notice"
        print(f"::{command} title={alert['code']}::{alert['message']}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"## Newsroom health: {payload['state']}\n\n")
            f.write(f"- Sources: {payload['ingestion']['successful_sources']}/{payload['ingestion']['configured_sources']}\n")
            f.write(f"- Ingestion age: {payload['ingestion']['age_minutes']} minutes\n")
            f.write(f"- Published timelines: {payload['content']['published_timelines']}\n")
            f.write(f"- Fast-path events: {payload.get('fast_path', {}).get('fast_path_events', 0)}\n")
            f.write(f"- Fast-path capture: {payload.get('fast_path', {}).get('high_urgency_capture_pct')}%\n")
            for alert in payload["alerts"]:
                f.write(f"- **{alert['severity']} {alert['code']}** — {alert['message']}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("fast", "maintenance"), default="fast")
    parser.add_argument("--assert-healthy", action="store_true")
    args = parser.parse_args()
    if args.assert_healthy:
        payload = load(HEALTH, {})
        if payload.get("state") not in {"HEALTHY", "DEGRADED", "CRITICAL"}:
            raise SystemExit("Newsroom health report is missing or invalid.")
        if payload.get("state") == "CRITICAL":
            raise SystemExit("Newsroom health is CRITICAL; see /health/ and workflow summary for the failing stage.")
        print(f"Newsroom health gate passed: {payload.get('state', 'UNKNOWN')}")
        return
    cycle_started = now()
    previous = load(HEALTH, {})
    dead = load(DEAD_LETTERS, {"dead_letters": []}).get("dead_letters", [])
    results = {}
    for key, label, script, expected in STAGES:
        result, failure = run_stage(key, label, script, expected, previous)
        results[key] = result
        if failure:
            dead.append(failure)
    dead = dead[-MAX_DEAD_LETTERS:]
    payload = build_signals(results, cycle_started, previous)
    payload["mode"] = args.mode
    payload["state"], payload["alerts"] = classify(payload)
    payload["dead_letter_count"] = len(dead)
    payload["thresholds"] = {"ingestion_warning_minutes": 10, "ingestion_critical_minutes": 15, "source_warning_pct": 20, "source_critical_pct": 50, "meaningful_update_warning_minutes": 120}
    HEALTH.parent.mkdir(parents=True, exist_ok=True)
    HEALTH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    DEAD_LETTERS.write_text(json.dumps({"updated_at": iso(), "max_entries": MAX_DEAD_LETTERS, "dead_letters": dead}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text(render_dashboard(payload, dead), encoding="utf-8")
    emit_actions(payload)
    print(f"Newsroom pipeline completed: {payload['state']}; {len(payload['alerts'])} alert(s); {len(dead)} dead letter(s).")


if __name__ == "__main__":
    main()
