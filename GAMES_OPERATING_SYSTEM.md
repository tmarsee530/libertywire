# Rally Point Games Operating System

## Objective
Rally Point Games exists to create a repeat-visit habit that feeds readers back into Rally Point journalism. Games should be quick, fair, mobile-first, shareable without spoilers, and tied to verified current-news context rather than being generic distractions.

## Launch product: Headline Five
Headline Five is a daily five-letter news-word game. The answer is selected deterministically from a curated vocabulary of news-relevant words that appear in the current Rally Point storyline set. Players receive six guesses and familiar letter-position feedback, but the visual design, name, copy, scoring, and news integration are original to Rally Point.

After a solve or loss, the game reveals why the word matters today and routes the player to relevant Rally Point coverage or source reporting. A local-device streak and spoiler-free share result encourage return visits without requiring accounts or storing player PII.

## Product principles
- One stable puzzle per Eastern calendar day. Regeneration during the day must not change the answer.
- No paid API or AI call is required to build the daily puzzle.
- Candidate answers come only from a curated five-letter vocabulary and current low-risk storyline text.
- Risk-flagged storylines are excluded from puzzle generation.
- The game never fabricates a headline, quote, event, or source.
- The answer is not exposed in page HTML before play; it is fetched from the generated game-data endpoint. This deters casual spoilers but is not treated as a security boundary.
- Streaks and completion state live in browser localStorage.
- Share text contains result squares but not the answer.
- Every finished game offers a path back into the day's reporting.

## Engagement funnel
`homepage / direct -> Games -> Headline Five -> completion -> Why this matters -> Rally Brief / source coverage -> return tomorrow`

Track page views, game starts, completions, wins, shares, and journalism click-throughs with the site's existing analytics layer. Do not collect unnecessary personal information.

## Next games after validation
1. Rally Crossword — a small daily current-events mini crossword.
2. Daily Five — five verified current-events questions.
3. What Happened First? — order recent developments chronologically.

Do not expand the catalog until Headline Five demonstrates repeat use or meaningful completion/click-through behavior.
