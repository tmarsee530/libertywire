# Rally Point News — Autonomous AI Work Backlog

This file is the persistent priority queue for high-value AI work. Work the highest-priority unfinished item that can be completed safely with current tools. Favor deterministic code/GitHub Actions for repetitive work and reserve agent capacity for editorial judgment, analytics, SEO, design and executive prioritization. Never deliberately exhaust usage or use separately billed APIs, paid services, contracts, account/security changes or new spending without owner approval.

## Current product model — September 20, 2026

Rally Point is currently a focused live news/timeline product: the homepage discovers and ranks important events, while canonical Live Timelines are the durable differentiated product for following one real-world event over time. Legacy Rally Briefs, Topics, Local Rally, Newsletter and Games files may remain in the repository, but they are retired product surfaces and must not be restored merely because the files exist. Sources/About/Privacy remain supporting trust/product pages. Any future return to a materially different publication model is an owner-level product decision.

## Current growth checkpoint — September 20, 2026

Rally Point remains in the first checkpoint: establish reliable indexing and genuine stranger acquisition. Last successfully measured settled 28-day GA4 view (Sept. 19 review): 53 sessions, 16 active users, 60.38% engagement rate and zero key events. Last successfully measured Search Console view was settled through Sept. 16 with 13 impressions and zero clicks, all on the homepage. Fresh analytics could not be retrieved Sept. 20 because the connected GSC Wizard subscription/trial is no longer active; do not treat the older figures as current. Diagnostic milestones remain approximately 100 genuine visits/day, then 1,000/day, then 10,000/day, while improving repeat use rather than chasing raw pageviews alone.

## Priority queue

1. **IN PROGRESS — Make canonical timelines exceptionally useful and trustworthy** — The timeline is the differentiated product: one real-world event should map to one canonical timeline that quickly answers what happened, what changed, how events unfolded, what is actually new, and where information came from. Sept. 20 production snapshot: 1,233 storylines, 40 multi-source/multi-family clusters, 7 breaking, 7 developing, 4 fast-path and 0 hot. Precision remains more important than inflating cluster counts. Continue eliminating duplicate canonical events and false merges while preserving material developments.
2. **IN PROGRESS — Improve source quality, diversity and corroboration** — Multi-family volume fell from the Sept. 19 reviewed snapshot (82) to 40 in the latest Sept. 20 production snapshot. Investigate whether this reflects the current news mix or overly conservative event identity after duplicate-control hardening. Do not loosen matching merely to restore a target count. A timeline should combine reports only when they describe the same causal real-world event.
3. **IN PROGRESS — Establish stranger acquisition for the current timeline model** — Keep homepage and canonical timeline metadata, crawlability, sitemap health, permanent URLs and internal discovery aligned to the timeline product. Do not restore retired Brief/article URLs as an SEO tactic. The next acquisition signal is sustained impressions followed by genuine search clicks into homepage/timeline surfaces.
4. **IN PROGRESS — Analytics-driven engagement and retention** — Last measured GA4 remains 53 sessions, 16 active users and 60.38% engagement. Fresh connected analytics are temporarily unavailable because GSC Wizard now requires an active subscription. Continue deterministic first-party event instrumentation and avoid making strategic claims from stale data.
5. **IN PROGRESS — Operating leverage and autonomous reliability** — Sept. 20 Fast Wire is actively self-renewing and the latest Pages deployment completed successfully. The fast loop had been producing repeated `Refresh live timelines` commits/deployments roughly every 4–5 minutes even when substantive state could be unchanged. Sept. 20: publication staging now restores tracked JSON when its only changes are volatile generation timestamps, reducing needless commits/deployments without slowing real news changes. Verify the next cycles actually suppress timestamp-only churn.
6. **IN PROGRESS — Homepage discovery quality** — The homepage should efficiently route readers into the strongest canonical timelines. Improve ranking, event hierarchy, freshness and scan speed; avoid allowing multiple cards/slots for the same event. Only genuinely hot events should receive exceptional visual emphasis.
7. **IN PROGRESS — Visual/UX optimization** — Improve mobile scanning, timeline comprehension, credibility and perceived speed only when there is a plausible retention/acquisition benefit. De-prioritize aesthetic churn.
8. **Revenue readiness** — Defer display ads, sponsorship and other monetization optimization until genuine audience and repeat usage justify it. Never manipulate impressions or clicks.

## Completed operating foundation

- **COMPLETED — Reduce unnecessary newsroom commits/deployments.** Sept. 20 adds timestamp-only JSON normalization to the publication stage; continue monitoring for other non-substantive churn sources.
- **COMPLETED — Use server-side storylines on the homepage.**
- **COMPLETED — Unify business intelligence around storylines.**
- **COMPLETED — Create persistent seven-day storyline history / “What changed?” data.**
- **COMPLETED — Align sitemap generation with the current live-news/timeline product.** Legacy Brief/topic/local/newsletter/game URLs remain excluded.
- **COMPLETED — Align homepage primary navigation with the current product.**
- **COMPLETED — Retire obsolete Rally Brief newsletter delivery automation.**

## Editorial product rule

Rally Point's defensibility should come from trustworthy event identity, permanent canonical timelines, selection/hierarchy, source transparency and useful compression of evolving news. Preserve source attribution and uncertainty. Never fabricate facts, quotes or sources, and never treat clustering as proof that multiple publishers independently verified a claim. Analytics may identify reader needs but never determine factual conclusions or political framing.

## Owner approval gates

Stop and ask only for new spending/contracts; paid API/service usage; account/security/permission changes; financially consequential commitments; fundamental identity/business-model changes; or high-risk original reporting that cannot safely be held or attributed.
