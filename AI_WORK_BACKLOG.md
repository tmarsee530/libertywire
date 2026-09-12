# Rally Point News — Autonomous AI Work Backlog

This file is the persistent priority queue for high-value AI work. It exists so Rally Point can use available ChatGPT/agent capacity efficiently without requiring the owner to continually say “continue.”

## Operating rule

Work the highest-priority unfinished item that can be completed safely with currently available tools. Favor deterministic code and GitHub Actions for repetitive work. Reserve ChatGPT/agent capacity for judgment-heavy tasks such as editorial synthesis, design review, SEO strategy, analytics interpretation, experimentation, and executive prioritization.

Do not attempt to deliberately exhaust a usage allowance. Use available capacity aggressively but conservatively, leaving headroom for failures and owner interaction. Never use a separately billed OpenAI API, paid service, contract, account/security change, or new spending without owner approval.

When an item is completed, mark it complete and add the next evidence-based priority. If analytics become available, reorder the backlog according to measured audience/revenue impact rather than intuition.

## Priority queue

1. **COMPLETED — Reduce unnecessary newsroom commits/deployments** — Storyline and operations snapshots now avoid rewrites when only timestamps/continuous age change, operations tracks a meaningful freshness bucket, and the workflow uses `git status --porcelain` so changed or untracked operating datasets are detected robustly.
2. **Use server-side storylines on the homepage** — Read `data/storylines.json` for ranking/grouping when healthy and fall back to existing client-side clustering when unavailable. Improve headline hierarchy and source transparency without exposing internal risk/operations data.
3. **COMPLETED — Unify business intelligence around storylines** — The business manager now consumes `data/storylines.json` directly for executive ranking, multi-source/developing counts, and editorial risk rather than recomputing a weaker second clustering model.
4. **Create persistent storyline history / “What changed?” data** — Track first seen, last seen, source growth, coverage additions, and capped history with pruning. This should become the factual substrate for differentiated article and timeline products.
5. **Harden article publishing infrastructure** — Add a clean article template, article index/discovery mechanism, canonical metadata, structured data where appropriate, and sitemap/robots support so the Brief Writer can publish safely without hand-editing the homepage.
6. **Visual/UX optimization** — Continuously improve typography, spacing, mobile behavior, accessibility, perceived speed, headline scannability, credibility, newsletter placement, and monetization placement. Prefer simple, fast, non-deceptive design.
7. **SEO/discovery improvements** — Improve title/meta/canonical/OG/schema and search discovery. Avoid scaled low-value AI pages. Publish only pages that add real synthesis, timeline, comparison, or source value.
8. **Analytics-driven optimization** — When Windsor.ai/GA/Search Console data is callable, measure sessions, landing pages, acquisition sources, engagement, newsletter conversion, search queries, CTR, and rankings. Use those metrics to reorder this backlog and choose experiments.
9. **Newsletter growth loop** — Improve newsletter calls-to-action and develop a concise Rally Brief product once audience behavior supports it.
10. **Revenue readiness** — Evaluate display advertising, direct sponsorship, newsletter sponsorship, and eventual premium intelligence only after traffic and engagement data justify the move. Never manipulate impressions/clicks.

## Editorial product rule

The site should evolve from an aggregator into a differentiated publication. The preferred value-add is multi-source synthesis: what happened, what multiple sources establish, what remains uncertain, what changed, and why it matters. Never fabricate facts, quotes, sources, certainty, or human reporting.

## Owner approval gates

Stop and ask only for: new spending or contracts; paid API/service usage; account/security/permission changes; financially consequential commitments; fundamental identity/business-model changes; or high-risk original reporting that cannot safely be held or attributed.
