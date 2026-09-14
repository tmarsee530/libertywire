# Rally Point Newsletter Operating System

## Objective
Rally Point News will own the newsletter experience on rallypointnews.com: acquisition, editorial production, web archives, analytics, and eventually delivery. Substack is transitional rather than the permanent public signup experience.

## Phase 1 — Native site foundation (safe, no new spending)
- Replace the public Substack iframe with a Rally Point-branded newsletter signup interface once a subscriber backend is authorized.
- Add `/newsletter/` as the public newsletter home/archive.
- Add first-party analytics events for newsletter CTA views/clicks and successful signup once the backend exists.
- Generate newsletter drafts deterministically from `data/briefs.json`, `data/storylines.json`, and `data/history.json`; AI performs final editorial selection/synthesis only when warranted.
- Keep all subscriber addresses out of the public GitHub repository and generated site files.

## Phase 2 — Subscriber backend and delivery (OWNER GATE)
A static GitHub Pages site cannot safely receive/store email addresses or send compliant bulk email by itself. Before enabling live signup, select and authorize a reputable email provider/backend with:
- API/form endpoint suitable for a static site;
- double opt-in where appropriate;
- unsubscribe and suppression-list handling;
- bounce/complaint handling;
- exportability of the subscriber list;
- no separately billed service or paid plan without owner approval;
- secrets stored outside the public repository.

Do not collect addresses until this backend is actually connected. Never commit subscriber PII or provider credentials to GitHub.

## Editorial contract
Working product name: **The Rally Brief**.
Default cadence: morning edition, only when there is enough verified material to justify an edition.

Each edition should contain:
1. A concise subject line and preheader.
2. A short opening explaining the day's information picture without manufactured urgency.
3. The strongest original Rally Brief(s), linked to Rally Point News.
4. A compact multi-source developing-stories section when useful.
5. Direct attribution/links where needed.
6. A corrections/tips link once native newsroom intake exists.
7. A one-click unsubscribe mechanism supplied by the delivery provider.

No filler. No fabricated facts, quotes, sourcing, urgency, or fake human authorship. Use **Rally Point News Desk** as the institutional editorial identity. Sensitive allegations, uncertain deaths, election calls, market-moving claims, or uncertain leaked/manipulated material require unusually strong verification or exclusion.

## Automation design
- GitHub Actions handles deterministic assembly, archive generation, and validation without AI/API spend.
- ChatGPT automation handles judgment-heavy story selection, synthesis, subject/preheader quality, and standards review.
- Sending is enabled only after the subscriber/delivery provider is authorized and tested.
- Failed generation or insufficient newsworthiness means no send rather than a low-quality edition.
- Daily CEO reviews newsletter acquisition and engagement once measurable.

## Measurement
Primary funnel:
`homepage/newsletter CTA -> signup -> confirmed subscriber -> email open (when reliably available) -> click -> Rally Brief visit -> repeat visit`

Prioritize confirmed subscribers, click-through rate, Rally Brief sessions attributable to newsletter, and retention. Do not optimize around vanity opens alone because privacy protections can distort open-rate measurement.

## Migration from Substack
Do not silently copy subscriber addresses. When migration is appropriate, use an authorized export/import path that preserves consent and unsubscribe/suppression state. Keep Substack operational until the native system is tested and existing subscribers have a safe migration path.

## Current owner gate
The next irreversible/external step is choosing and authorizing the subscriber-storage/email-delivery provider. This may create an external account relationship or future cost, so it requires owner approval. All site-side and editorial preparation that does not collect PII or incur cost may proceed autonomously.
