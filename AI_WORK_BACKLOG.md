# Rally Point News — Autonomous AI Work Backlog

This file is the persistent priority queue for high-value AI work. Work the highest-priority unfinished item that can be completed safely with current tools. Favor deterministic code/GitHub Actions for repetitive work and reserve agent capacity for editorial judgment, analytics, SEO, design and executive prioritization. Never deliberately exhaust usage or use separately billed APIs, paid services, contracts, account/security changes or new spending without owner approval.

## Current product model — October 2, 2026

Rally Point is a focused live news/timeline product: the homepage discovers and ranks important events, while canonical Live Timelines are the durable differentiated product for following one real-world event over time. Legacy Rally Briefs, Topics, Local Rally, Newsletter and Games files may remain in the repository, but they are retired product surfaces and must not be restored merely because the files exist. Sources/About/Privacy remain supporting trust/product pages. Any future return to a materially different publication model is an owner-level product decision.

## Current growth checkpoint — October 2, 2026

Rally Point remains in the first checkpoint: establish reliable indexing and genuine stranger acquisition. Last successfully measured settled 28-day GA4 view (Sept. 19 review): 53 sessions, 16 active users, 60.38% engagement rate and zero key events. Last successfully measured Search Console view was settled through Sept. 16 with 13 impressions and zero clicks, all on the homepage. A fresh GA4 request on Sept. 30 was blocked because the GSC Wizard trial/subscription is inactive; do not spend to restore it without owner approval and do not treat older figures as current. Diagnostic milestones remain approximately 100 genuine visits/day, then 1,000/day, then 10,000/day, while improving repeat use rather than chasing raw pageviews alone.

October 2 production baseline: `data/storylines.json` generated at 12:21 UTC contains 1,225 storylines, 55 multi-source/multi-family clusters (~4.5%), 18 breaking, 11 fast-path and 21 developing storylines. The latest observed Pages deployment completed successfully and Fast Wire continued running. Multi-family corroboration has fallen from the Oct. 1 snapshot (68/1,203, ~5.7%) and remains a material editorial/business constraint; do not raise it by weakening event identity.

The legacy deterministic `data/writer_queue.json` is stale (last generated Sept. 16) and its Brief-oriented publication path is retired. Do not mistake it for an active acquisition engine. Search-opportunity publishing for the current timeline product needs an explicit independent-research path when deterministic event candidates are insufficient, with fresh verification and the same attribution/uncertainty standards.

## Priority queue

1. **IN PROGRESS — Prevent historical continuity from merging unrelated current events** — Code review confirms `history_match()` can assign the same historical canonical ID to independently formed current clusters, after which `merge_current_ids()` combines them solely because their IDs match. This can contaminate permanent timelines even though first-pass clustering is conservative. Highest-value next code change: before merging two current items with the same inherited historical ID, require fresh current-to-current event-identity confirmation at the existing conservative threshold; otherwise retain a separate deterministic current identity. Verify against observed contamination cases before marking complete. Do not loosen publication standards. Current connector can replace whole files but does not expose a safe patch operation for the 22KB production script; do not risk reconstructing/truncating production code merely to force a write.
2. **IN PROGRESS — Establish stranger acquisition for the current timeline model** — Acquisition is the primary business proof immediately behind the event-purity blocker. Keep homepage and canonical timeline metadata, crawlability, sitemap health, permanent URLs and internal discovery aligned to the timeline product. Sitemap discovery follows `published_timelines.json` as the authoritative timeline set. Do not restore retired Brief/article URLs as an SEO tactic. Build a current-product search-opportunity path that can identify independently researched, high-value queries/events even when deterministic writer candidates are empty or stale; require strong fresh verification before publication and route successful work into canonical timeline surfaces rather than reviving retired Briefs. The next acquisition signal is sustained impressions followed by genuine search clicks into homepage/timeline surfaces.
3. **IN PROGRESS — Make canonical timelines exceptionally useful and trustworthy** — One real-world event should map to one canonical timeline that quickly answers what happened, what changed, how events unfolded, what is actually new, and where information came from. Continue eliminating duplicate canonicals, false merges and event drift while preserving material developments and stable URLs.
4. **IN PROGRESS — Improve source quality, diversity and corroboration** — Oct. 2 snapshot contains 1,225 storylines and 55 multi-family clusters (~4.5%), down from 68/1,203 (~5.7%) on Oct. 1. This remains a material product/business constraint. Do not lower event-identity thresholds to raise the number. Audit publisher-family normalization, syndication/republication and false-negative same-event matches so the metric reflects genuinely independent corroboration rather than feed labels.
5. **IN PROGRESS — Analytics-driven engagement and retention** — Last measured GA4 remains 53 sessions, 16 active users and 60.38% engagement. Fresh connected analytics remain unavailable without a paid GSC Wizard subscription. Continue deterministic first-party event instrumentation and avoid strategic claims from stale data.
6. **IN PROGRESS — Operating leverage and autonomous reliability** — Oct. 2 production is actively refreshing; latest observed Pages deployment succeeded and Fast Wire continued running. Continue watching failed/stale runs and non-substantive deployment churn.
7. **IN PROGRESS — Homepage discovery quality** — The homepage should efficiently route readers into the strongest canonical timelines. Improve ranking, event hierarchy, freshness and scan speed; avoid allowing multiple cards/slots for the same event. Only genuinely hot events should receive exceptional visual emphasis.
8. **IN PROGRESS — Visual/UX optimization** — Improve mobile scanning, timeline comprehension, credibility and perceived speed only when there is a plausible retention/acquisition benefit. De-prioritize aesthetic churn.
9. **Revenue readiness** — Defer display ads, sponsorship and other monetization optimization until genuine audience and repeat usage justify it. Never manipulate impressions or clicks.

## Completed operating foundation

- **COMPLETED — Reduce unnecessary newsroom commits/deployments.** Timestamp-only JSON normalization is in the publication stage; continue monitoring for other non-substantive churn sources.
- **COMPLETED — Use server-side storylines on the homepage.**
- **COMPLETED — Unify business intelligence around storylines.**
- **COMPLETED — Create persistent seven-day storyline history / “What changed?” data.**
- **COMPLETED — Align sitemap generation with the current live-news/timeline product.** Legacy Brief/topic/local/newsletter/game URLs remain excluded.
- **COMPLETED — Restrict timeline sitemap discovery to authoritative canonicals.** Historical/superseded story directories can remain for continuity but are no longer advertised to crawlers as competing canonical product pages.
- **COMPLETED — Align homepage primary navigation with the current product.**
- **COMPLETED — Retire obsolete Rally Brief newsletter delivery automation.**
- **COMPLETED — Require event identity before collapsing single-update canonical duplicates.** Shared-update leakage alone can no longer merge two otherwise unrelated one-update timelines.
- **COMPLETED — Preserve active canonical ownership during duplicate resolution.** A historical retained record with greater source breadth can no longer displace the current event's canonical URL solely because of historical accumulation.

## Editorial product rule

Rally Point's defensibility should come from trustworthy event identity, permanent canonical timelines, selection/hierarchy, source transparency and useful compression of evolving news. Preserve source attribution and uncertainty. Never fabricate facts, quotes or sources, and never treat clustering as proof that multiple publishers independently verified a claim. Analytics may identify reader needs but never determine factual conclusions or political framing.

## Owner approval gates

Stop and ask only for new spending/contracts; paid API/service usage; account/security/permission changes; financially consequential commitments; fundamental identity/business-model changes; or high-risk original reporting that cannot safely be held or attributed.
