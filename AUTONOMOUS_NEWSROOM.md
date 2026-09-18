# Rally Point Autonomous Newsroom

## Operating constraint

Rally Point should not require a separately billed OpenAI API account for its normal operation. Deterministic automation should do continuous, repetitive work. ChatGPT/Astra tasks can be used for periodic editorial judgment and business analysis within the owner's existing ChatGPT plan limits.

## Current architecture

- Static GitHub Pages site.
- GitHub Actions ingests publisher RSS/Atom feeds every five minutes.
- The deterministic editorial engine clusters, ranks, deduplicates, and preserves developing-story history.
- Multi-source stories receive stable, source-backed live timeline pages under `/stories/`.
- The server-rendered homepage and timeline archive remain usable and crawlable without JavaScript.
- Google Analytics, AdSense metadata, and a Substack signup are already present.

## Operating architecture

### Layer 1 — Always-on deterministic newsroom
Runs without AI tokens.

- Source registry (`feeds.json`)
- Feed health monitoring
- Feed ingestion/cache
- Deduplication
- Basic event clustering
- Freshness scoring
- Site generation/deployment
- Error logging

### Layer 2 — ChatGPT/Astra editorial loop
Runs periodically rather than continuously.

- Review important developing clusters
- Improve event grouping when heuristics are uncertain
- Produce original, attributed Rally Point briefs when appropriate
- Flag contradictory or weak sourcing
- Recommend homepage/editorial changes
- Review traffic and revenue performance

### Layer 3 — Owner safeguards

AI automation must never:

- fabricate facts, quotations, sources, or attribution;
- copy substantial portions of publisher articles;
- publish unsupported allegations as fact;
- create fake human bylines;
- manipulate advertising impressions or clicks;
- purchase services or incur new paid API usage without owner approval.

## Build sequence

1. Centralize source configuration and health monitoring. (Started.)
2. Move feed collection out of each visitor's browser into a shared generated dataset.
3. Make the frontend consume that shared dataset with a graceful fallback.
4. Improve deterministic clustering and scoring.
5. Add persistent storyline/history data. (Complete.)
6. Publish finite, chronological, source-backed live timelines. (Complete.)
7. Add optional scheduled ChatGPT editorial review within available account task limits.
8. Add analytics/business review and owner report.
9. Add original briefing pages only after sourcing/copyright/quality gates are implemented.

## Token strategy

The site itself should remain functional if ChatGPT is unavailable or account usage is temporarily exhausted. Continuous work belongs in GitHub Actions/static code; AI is reserved for work where reasoning adds material value.
