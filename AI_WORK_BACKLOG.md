# Rally Point News — Autonomous AI Work Backlog

This file is the persistent priority queue for high-value AI work. Work the highest-priority unfinished item that can be completed safely with current tools. Favor deterministic code/GitHub Actions for repetitive work and reserve agent capacity for editorial judgment, analytics, SEO, design and executive prioritization. Never deliberately exhaust usage or use separately billed APIs, paid services, contracts, account/security changes or new spending without owner approval.

## Current product model — September 17, 2026

Rally Point is currently a focused live news/link-ranking product: a strong homepage that identifies, ranks and groups important stories and gives readers useful multi-source headline context. Legacy Rally Briefs, Topics, Local Rally, Newsletter and Games files may remain in the repository, but they are retired product surfaces and must not be restored to primary navigation, sitemaps, growth strategy or autonomous production merely because the files exist. Sources/About/Privacy remain supporting trust/product pages. Any future return to a materially different publication model is an owner-level product decision.

## Current growth checkpoint — September 17, 2026

Rally Point remains in the first checkpoint: establish reliable indexing and genuine stranger acquisition. Latest settled 28-day GA4 view: 42 sessions and 16 active users, with 59.52% engagement and zero key events. Sessions remain below the preceding comparison window while engagement is materially stronger. Search Console is settled through Sept. 14 and now shows 15 impressions, zero clicks; all impressions are still on the homepage. This is a meaningful discovery increase from 7 impressions in the prior review, but not yet reliable stranger acquisition. Diagnostic milestones remain approximately 100 genuine visits/day, then 1,000/day, then 10,000/day, while improving repeat use rather than chasing raw pageviews alone.

## Priority queue

1. **IN PROGRESS — Make the homepage news product worth returning to** — The homepage is the core product and the only page currently receiving Google impressions. Improve story selection, ranking, headline hierarchy, freshness, scan speed and the usefulness of multi-source context. Prioritize changes that make Rally Point a better daily destination rather than creating additional product surfaces.
2. **IN PROGRESS — Improve source quality, diversity and corroboration** — Latest reviewed storyline intelligence contained 1,152 total clusters, 99 multi-source/multi-family storylines, 18 developing and 10 breaking. Do not optimize for raw cluster count. Reduce false merges, tangential grouping and publisher-family duplication while preserving breadth across major news categories. A cluster should help a reader understand one story, not merely collect headlines sharing a few words.
3. **IN PROGRESS — Establish stranger acquisition for the current homepage model** — Search Console has increased to 15 impressions but still zero clicks, all on the homepage. Keep homepage title/description, crawlability, canonical metadata, sitemap health and external discovery aligned to the current live-news product. Do not restore retired Brief/article URLs as an SEO tactic. The next acquisition signal is a sustained rise in impressions followed by genuine search clicks.
4. **IN PROGRESS — Analytics-driven engagement and retention** — Latest settled GA4: 42 sessions, 16 active users, 59.52% engagement rate and zero key events. Instrument meaningful homepage behavior where useful: outbound story clicks, depth/section interaction and repeat visits. Avoid overfitting the tiny sample. The immediate question is whether strangers arrive and find enough value to return.
5. **IN PROGRESS — Category breadth without homepage clutter** — Maintain broad enough source/story coverage that important politics, world, business, technology, culture/entertainment, science/health and major breaking stories can surface when warranted. Preserve clear page hierarchy; only genuinely hot headlines should receive red emphasis. Avoid repetitive subheadlines, but retain necessary words when removing them would make the subheadline unclear.
6. **IN PROGRESS — Operating leverage and autonomous reliability** — Keep the deterministic newsroom refresh/deployment loop reliable, inexpensive and low-maintenance. Detect failed or stale runs, prevent unnecessary commits, and ensure autonomous updates cannot silently reintroduce retired product architecture. Sept. 17: retired the obsolete Rally Brief Delivery workflow after it was still preparing legacy newsletters and failing against Kit with a 403; automatic triggers were removed so it can no longer consume runs or create legacy-product commits.
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
