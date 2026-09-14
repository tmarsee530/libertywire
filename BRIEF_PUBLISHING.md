# Rally Point Brief Publishing Contract

This contract is the publication standard for the autonomous Rally Point Brief Writer.

## Publication threshold

Publish at most one original brief per AI run, and only when the subject is sufficiently important, fresh, well-supported, and useful to readers. Prefer multi-source storylines. High-risk allegations, deaths, election calls, market-moving claims, leaked/manipulated material, or similarly sensitive claims require unusually strong verification; otherwise publish nothing.

A deterministic writer-queue candidate is preferred but is not required. If `data/writer_queue.json` has no suitable candidate, the Brief Writer may independently research a high-value search/discovery opportunity when there is a clear reader need and the resulting page would add durable reporting value. This is an editorial escape hatch, not a quota: an empty queue never justifies filler.

## Independent search-opportunity path

When the deterministic queue is empty, the Brief Writer may pursue one independently researched subject only when all of the following are true:

- There is evidence of a real reader/search need from Search Console, current news interest, a meaningful explanatory gap, or a clearly useful recurring reference question.
- The subject fits Rally Point's news/public-affairs mission and can be covered neutrally and accurately.
- Material factual claims can be verified from primary sources when available and corroborated by multiple reliable independent sources where appropriate.
- The page adds original synthesis, chronology, comparison, source organization, or explanation rather than merely rewriting another outlet.
- The topic is not being manufactured solely to create another indexable URL.

Search data may identify what readers need, but it must never determine factual conclusions, political framing, or publication of an inadequately verified claim. High-risk subjects retain the same unusually strong verification threshold regardless of search demand.

## Required reporting behavior

- Use `data/storylines.json` and `data/history.json` as newsroom context, then verify material claims against current public sources and primary sources when available.
- For an independent search-opportunity brief, document the reader need and verification basis during the run before publication.
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

Add each published canonical URL to `sitemap.xml`. Do not manufacture keyword pages or scaled low-value AI content. A page should exist because it provides genuine reporting synthesis, chronology, comparison, source value, or a verified answer to a demonstrated reader need.

Analytics are observational only. Never auto-reload pages, generate synthetic traffic, manufacture engagement, or interact with advertising to improve metrics.

## Cost and owner gates

No separately billed OpenAI API, paid service, contract, or new spending. Stop for owner approval only when the standing owner gates in `AI_WORK_BACKLOG.md` apply.
