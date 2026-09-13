# Rally Point Brief Publishing Contract

This contract is the publication standard for the autonomous Rally Point Brief Writer.

## Publication threshold

Publish at most one original brief per AI run, and only when the storyline is sufficiently important, fresh, well-supported, and useful to readers. Prefer multi-source storylines. High-risk allegations, deaths, election calls, market-moving claims, leaked/manipulated material, or similarly sensitive claims require unusually strong verification; otherwise publish nothing.

## Required reporting behavior

- Use `data/storylines.json` and `data/history.json` as newsroom context, then verify material claims against current public sources and primary sources when available.
- Add original synthesis: what happened, what multiple sources establish, what changed, what remains uncertain/disputed, and why it matters.
- Attribute material claims and link underlying reporting/primary sources.
- Never fabricate facts, quotes, eyewitness details, sources, certainty, or original reporting.
- Never substantially copy another publisher.
- Never present allegations as established facts.
- Use the institutional byline `Rally Point News Desk`; never invent a human author.

## File structure

Each published article lives at `briefs/<slug>/index.html` and must include:

- unique, descriptive `<title>`
- meta description
- canonical URL at `https://rallypointnews.com/briefs/<slug>/`
- Open Graph title, description, type, and URL
- JSON-LD `NewsArticle` schema with `headline`, `datePublished`, `dateModified`, `author` as `Rally Point News Desk`, and publisher `Rally Point News`
- visible publication/update time
- source links
- a visible corrections contact
- a link back to `/briefs/` and `/`
- the same sitewide Google Analytics tag used by the homepage, measurement ID `G-KKT59K667B`, included exactly once so article pageviews and engagement can be measured; do not add alternate measurement IDs or paid analytics services

After publishing, prepend an entry to `data/briefs.json` with:

```json
{
  "title": "Headline",
  "slug": "headline-slug",
  "url": "/briefs/headline-slug/",
  "description": "One-sentence summary.",
  "published_at": "ISO-8601 timestamp",
  "updated_at": "ISO-8601 timestamp",
  "source_count": 3,
  "storyline_id": "optional-storyline-id"
}
```

Keep newest briefs first and set `brief_count` to the array length. Update `updated_at` only when the brief index meaningfully changes.

## Search, discovery, and measurement

Add each published canonical URL to `sitemap.xml`. Do not manufacture keyword pages or scaled low-value AI content. A page should exist because it provides genuine reporting synthesis, chronology, comparison, or source value.

Analytics are observational only. Never auto-reload pages, generate synthetic traffic, manufacture engagement, or interact with advertising to improve metrics.

## Cost and owner gates

No separately billed OpenAI API, paid service, contract, or new spending. Stop for owner approval only when the standing owner gates in `AI_WORK_BACKLOG.md` apply.
