# Rally Point News — Autonomous AI Work Backlog

This file is the persistent priority queue for high-value AI work. Work the highest-priority unfinished item that can be completed safely with current tools. Favor deterministic code/GitHub Actions for repetitive work and reserve agent capacity for editorial judgment, analytics, SEO, design and executive prioritization. Never deliberately exhaust usage or use separately billed APIs, paid services, contracts, account/security changes or new spending without owner approval.

## Current product model — September 19, 2026

Rally Point is currently a focused live news/link-ranking product: a strong homepage that identifies, ranks and groups important stories and gives readers useful multi-source headline context. Legacy Rally Briefs, Topics, Local Rally, Newsletter and Games files may remain in the repository, but they are retired product surfaces and must not be restored to primary navigation, sitemaps, growth strategy or autonomous production merely because the files exist. Sources/About/Privacy remain supporting trust/product pages. Any future return to a materially different publication model is an owner-level product decision.

## Current growth checkpoint — September 19, 2026

Rally Point remains in the first checkpoint: establish reliable indexing and genuine stranger acquisition. Latest settled 28-day GA4 view: 53 sessions, 16 active users, 60.38% engagement rate and zero key events. Sessions increased by 5 versus the preceding comparison window and engagement remains materially stronger, but active users declined by 12, so this is not yet evidence of durable audience growth. Search Console is settled through Sept. 16 and shows 13 impressions, zero clicks; all impressions remain on the homepage. Diagnostic milestones remain approximately 100 genuine visits/day, then 1,000/day, then 10,000/day, while improving repeat use rather than chasing raw pageviews alone.

## Priority queue

1. **IN PROGRESS — Make the homepage news product worth returning to** — The homepage is the core product and the only page receiving Google impressions. Improve story selection, ranking, headline hierarchy, freshness, scan speed and useful multi-source context. Sept. 19: added a conservative deterministic second-pass duplicate-cluster merge requiring strong lexical overlap, at least three shared substantive tokens and shared named anchors when both clusters expose them. This targets duplicate top-story slots without lowering corroboration standards. Next: verify production output after autonomous regeneration and tune only from observed false merges/splits.
2. **IN PROGRESS — Improve source quality, diversity and corroboration** — Sept. 19 pre-change snapshot: 1,220 storylines, 82 multi-source/multi-family clusters, 19 breaking, 26 developing and 4 hot. Multi-family volume is adequate enough to prioritize precision over raw cluster count. Continue reducing false merges, duplicate clusters, tangential grouping and publisher-family duplication while preserving breadth. A cluster should help a reader understand one event, not merely collect related headlines.
3. **IN PROGRESS — Establish stranger acquisition for the current homepage model** — Search Console settled through Sept. 16 shows 13 impressions and zero clicks, all on the homepage. Keep title/description, crawlability, canonical metadata, sitemap health and external discovery aligned to the live-news product. Do not restore retired Brief/article URLs as an SEO tactic. The next acquisition signal is sustained impression growth followed by genuine search clicks.
4. **IN PROGRESS — Analytics-driven engagement and retention** — Latest settled GA4: 53 sessions, 16 active users, 60.38% engagement and zero key events. Sessions rose while active users fell, consistent with more repeat activity from a very small audience rather than broad acquisition. Instrument meaningful homepage behavior where useful and avoid overfitting this sample.
5. **IN PROGRESS — Category breadth without homepage clutter** — Maintain broad enough source/story coverage that important politics, world, business, technology, culture/entertainment, science/health and major breaking stories can surface when warranted. Preserve clear page hierarchy; only genuinely hot headlines should receive red emphasis. Avoid repetitive subheadlines, but retain necessary words when removing them would make the subheadline unclear.
6. **IN PROGRESS — Operating leverage and autonomous reliability** — Fast Wire is actively self-renewing on Sept. 19 and recent Pages deployment completed successfully. Keep the deterministic refresh/deployment loop reliable, inexpensive and low-maintenance; detect failed or stale runs and prevent autonomous updates from reintroducing retired product architecture.
7. **IN PROGRESS — Visual/UX optimization** — Improve mobile scanning, information density, credibility and perceived speed only when there is a plausible retention/acquisition benefit. De-prioritize aesthetic churn.
8. **Revenue readiness** — Defer display ads, sponsorship and other monetization optimization until genuine audience and repeat usage justify it. Never manipulate impressions or clicks.

## Completed operating foundation

- **COMPLETED — Reduce unnecessary newsroom commits/deployments.**
- **COMPLETED — Use server-side storylines on the homepage.**
- **COMPLETED — Unify business intelligence around storylines.**
- **COMPLETED — Create persistent seven-day storyline history / “What changed?” data.**
- **COMPLETED — Align sitemap generation with the current live-news product.** Legacy Brief/topic/local/newsletter/game URLs remain excluded.
- **COMPLETED — Align homepage primary navigation with the current product.** Top Stories, The Wire, Sources and About are the active navigation surfaces; retired product links are not automatically reintroduced.
- **COMPLETED — Retire obsolete Rally Brief newsletter delivery automation.** The legacy workflow has no scheduled or push triggers under the current product model.

## Editorial product rule

Rally Point's present differentiation should come from selection, hierarchy, breadth and useful multi-source context on the live homepage. Preserve source attribution and uncertainty. Never fabricate facts, quotes or sources, and never treat clustering as proof that multiple publishers independently verified a claim. Analytics may identify reader needs but never determine factual conclusions or political framing.

## Owner approval gates

Stop and ask only for new spending/contracts; paid API/service usage; account/security/permission changes; financially consequential commitments; fundamental identity/business-model changes; or high-risk original reporting that cannot safely be held or attributed.
