# Rally Point News — Autonomous AI Work Backlog

This file is the persistent priority queue for high-value AI work. It exists so Rally Point can use available ChatGPT/agent capacity efficiently without requiring the owner to continually say “continue.”

## Operating rule

Work the highest-priority unfinished item that can be completed safely with currently available tools. Favor deterministic code and GitHub Actions for repetitive work. Reserve ChatGPT/agent capacity for judgment-heavy tasks such as editorial synthesis, design review, SEO strategy, analytics interpretation, experimentation, and executive prioritization.

Do not attempt to deliberately exhaust a usage allowance. Use available capacity aggressively but conservatively, leaving headroom for failures and owner interaction. Never use a separately billed OpenAI API, paid service, contract, account/security change, or new spending without owner approval.

When an item is completed, mark it complete and add the next evidence-based priority. If analytics become available, reorder the backlog according to measured audience/revenue impact rather than intuition.

## Priority queue

1. **COMPLETED — Reduce unnecessary newsroom commits/deployments** — Storyline and operations snapshots now avoid rewrites when only timestamps/continuous age change, operations tracks a meaningful freshness bucket, and the workflow uses `git status --porcelain` so changed or untracked operating datasets are detected robustly.
2. **COMPLETED — Use server-side storylines on the homepage** — The homepage now reads `data/storylines.json` as a progressive enhancement, promotes a multi-source lead storyline, shows newsroom storyline metrics and multi-source proof, decorates matching wire cards, and preserves the existing client-side newsroom as a fallback.
3. **COMPLETED — Unify business intelligence around storylines** — The business manager now consumes `data/storylines.json` directly for executive ranking, multi-source/developing counts, and editorial risk rather than recomputing a weaker second clustering model.
4. **COMPLETED — Create persistent storyline history / “What changed?” data** — A bounded seven-day history layer now tracks first/last seen, source growth, title evolution, coverage additions, status, and risk context while avoiding no-op rewrites.
5. **COMPLETED — Harden article publishing infrastructure** — Added `/briefs/` discovery, `data/briefs.json`, a strict autonomous publishing contract, canonical/structured-data requirements, crawler guidance, and a sitemap foundation for safe original briefs.
6. **IN PROGRESS — Visual/UX optimization** — The first visible editorial redesign is installed: stronger masthead/lead hierarchy, flatter news-card styling, multi-source proof, newsroom navigation, improved mobile behavior, tighter newsletter treatment, and automatic Rally Brief surfacing. Continue optimizing accessibility, perceived speed, scannability, credibility, and placement using measured behavior when analytics become available.
7. **IN PROGRESS — SEO/discovery improvements** — Canonical homepage metadata, Open Graph/Twitter metadata, Organization/WebSite JSON-LD, robots guidance, sitemap foundation, and updated product positioning are installed. Continue with measured search-query/CTR improvements and article-level discovery as original briefs accumulate; avoid scaled low-value AI pages.
8. **Analytics-driven optimization** — When Windsor.ai/GA/Search Console data is callable, measure sessions, landing pages, acquisition sources, engagement, newsletter conversion, search queries, CTR, and rankings. Use those metrics to reorder this backlog and choose experiments.
9. **Newsletter growth loop** — Improve newsletter calls-to-action and develop a concise Rally Brief product once audience behavior supports it.
10. **Revenue readiness** — Evaluate display advertising, direct sponsorship, newsletter sponsorship, and eventual premium intelligence only after traffic and engagement data justify the move. Never manipulate impressions/clicks.

## Editorial product rule

The site should evolve from an aggregator into a differentiated publication. The preferred value-add is multi-source synthesis: what happened, what multiple sources establish, what remains uncertain, what changed, and why it matters. Never fabricate facts, quotes, sources, certainty, or human reporting.

## Owner approval gates

Stop and ask only for: new spending or contracts; paid API/service usage; account/security/permission changes; financially consequential commitments; fundamental identity/business-model changes; or high-risk original reporting that cannot safely be held or attributed.
