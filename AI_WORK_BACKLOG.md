# Rally Point News — Autonomous AI Work Backlog

This file is the persistent priority queue for high-value AI work. Work the highest-priority unfinished item that can be completed safely with current tools. Favor deterministic code/GitHub Actions for repetitive work and reserve agent capacity for editorial judgment, analytics, SEO, design and executive prioritization. Never deliberately exhaust usage or use separately billed APIs, paid services, contracts, account/security changes or new spending without owner approval.

## Current product model — October 4, 2026

Rally Point is a focused live news/timeline product: the homepage discovers and ranks important events, while canonical Live Timelines are the durable differentiated product for following one real-world event over time. Legacy Rally Briefs, Topics, Local Rally, Newsletter and Games files may remain in the repository, but they are retired product surfaces and must not be restored merely because the files exist. Sources/About/Privacy remain supporting trust/product pages.

## Current growth checkpoint — October 4, 2026

Rally Point remains in checkpoint one: establish reliable indexing and genuine stranger acquisition. Last successfully measured settled 28-day GA4 view: 53 sessions, 16 active users, 60.38% engagement and zero key events. Last successfully measured Search Console view was settled through Sept. 16 with 13 impressions and zero clicks, all on the homepage. Fresh connected analytics remain blocked because the GSC Wizard subscription is inactive; do not spend to restore it without owner approval and do not treat older figures as current. Diagnostic milestones remain approximately 100 genuine visits/day, then 1,000/day, then 10,000/day, while improving repeat use and owned audience.

October 4 production baseline: `data/storylines.json` generated at 12:46 UTC contains 1,280 storylines, 41 multi-source/multi-family clusters (~3.2%), 10 breaking, 6 fast-path and 13 developing storylines. The latest observed Pages deployment and Fast Wire Watchdog succeeded. Multi-family corroboration remains at the Oct. 3 low rather than recovering. Treat this as a material editorial/business problem; do not raise it by weakening event identity.

## Flagship experiment

Reviewed publication scopes repair confirmed historical contamination without deleting raw history. Ten selected canonical events have stable titles, source-bound starting points, reasons to follow, questions to watch, limited reviewed repeat-fact compression and reader sharing. Distribution reads authoritative published state and prepares tagged draft X posts; automatic posting remains disabled. Timeline engagement, source opening, sharing and end-card exposure are instrumented alongside follows/return visits. Sitemap dates prefer actual published material timestamps.

## Priority queue

1. **IN PROGRESS — Establish stranger acquisition for the current timeline model.** Acquisition is the primary business proof. Keep homepage and canonical timeline metadata, crawlability, sitemap health, permanent URLs and internal discovery aligned to the timeline product. Sitemap discovery follows `published_timelines.json` as the authoritative timeline set. Do not restore retired Brief/article URLs as an SEO tactic. The next acquisition signal is sustained impressions followed by genuine search clicks into homepage/timeline surfaces. The canonical-timeline research queue is live and regenerates every cycle; Oct. 4 it produced 25 verified candidates and 100 research leads, so the research function is not idle.
2. **IN PROGRESS — Improve source quality, diversity and corroboration.** Oct. 4 remains only 41 multi-family clusters out of 1,280 (~3.2%). **Highest-value deterministic subtask:** make publisher-family normalization a single shared source of truth and use it in storyline construction as well as the research queue. Current code is inconsistent: `build_writer_queue.py` correctly collapses BBC section feeds, CBS News/Sports, NPR News/Culture, New York Post/Page Six and Stars and Stripes variants, while `build_storylines.py` still has a much smaller family map. Until this is aligned, `source_family_count`, multi-family KPIs and breadth-based ranking/confidence can overstate independent corroboration. After normalization, re-baseline genuine multi-family coverage and then audit false-negative same-event matches. Do not lower event-identity thresholds.
3. **IN PROGRESS — Make canonical timelines exceptionally useful and trustworthy.** One real-world event should map to one canonical timeline that quickly answers what happened, what changed, how events unfolded, what is actually new, and where information came from. Continue eliminating duplicate canonicals, false merges and event drift while preserving material developments and stable URLs.
4. **IN PROGRESS — Analytics-driven engagement and retention.** Fresh connected analytics remain unavailable without paid GSC Wizard access. Continue deterministic first-party event instrumentation and avoid strategic claims from stale data. When measured data returns, prioritize landing-page acquisition, return behavior, follows, newsletter/owned-audience conversion and source-opening behavior over raw pageviews.
5. **IN PROGRESS — Operating leverage and autonomous reliability.** Oct. 4 production is actively refreshing; latest observed Pages deployment and Fast Wire Watchdog succeeded. Continue watching failed/stale runs and non-substantive deployment churn. The timeline research queue is part of the autonomous fast loop and is non-blocking to core publication.
6. **IN PROGRESS — Homepage discovery quality.** The homepage should efficiently route readers into the strongest canonical timelines. Improve ranking, event hierarchy, freshness and scan speed; avoid multiple cards/slots for the same event.
7. **IN PROGRESS — Visual/UX optimization.** Improve mobile scanning, timeline comprehension, credibility and perceived speed only when there is a plausible retention/acquisition benefit. De-prioritize aesthetic churn.
8. **Revenue readiness.** Defer display ads, sponsorship and other monetization optimization until genuine audience and repeat usage justify it. Never manipulate impressions or clicks.

## Completed operating foundation

- **COMPLETED — Guard historical continuity against unrelated current events (October 2).** Historical ID reuse now requires every independently formed current claimant to pass the conservative current-event merge gate against each original claimant. Rejected matches keep deterministic current identities. Regression coverage includes known false-merge patterns and true continuity cases.
- **COMPLETED — Replace stale Brief writer queue with timeline research queue (October 3).** The queue no longer consults retired Briefs, normalizes known same-publisher section feeds, forbids automatic publication, requires fresh verification, prefers primary sources, and falls back to independent research leads when no multi-family candidate qualifies. Fast Wire regenerates and validates it each cycle.
- **COMPLETED — Reduce unnecessary newsroom commits/deployments.** Timestamp-only JSON normalization is in the publication stage.
- **COMPLETED — Use server-side storylines on the homepage.**
- **COMPLETED — Unify business intelligence around storylines.**
- **COMPLETED — Create persistent seven-day storyline history / “What changed?” data.**
- **COMPLETED — Align sitemap generation with the current live-news/timeline product.**
- **COMPLETED — Restrict timeline sitemap discovery to authoritative canonicals.**
- **COMPLETED — Align homepage primary navigation with the current product.**
- **COMPLETED — Retire obsolete Rally Brief newsletter delivery automation.**
- **COMPLETED — Require event identity before collapsing single-update canonical duplicates.**
- **COMPLETED — Preserve active canonical ownership during duplicate resolution.**

## Editorial product rule

Rally Point's defensibility should come from trustworthy event identity, permanent canonical timelines, selection/hierarchy, source transparency and useful compression of evolving news. Preserve source attribution and uncertainty. Never fabricate facts, quotes or sources, and never treat clustering as proof that multiple publishers independently verified a claim. Analytics may identify reader needs but never determine factual conclusions or political framing.

## Owner approval gates

Stop and ask only for new spending/contracts; paid API/service usage; account/security/permission changes; financially consequential commitments; fundamental identity/business-model changes; or high-risk original reporting that cannot safely be held or attributed.
