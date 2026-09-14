# Rally Point Newsletter Operating System

## Objective
Rally Point News owns the newsletter experience on rallypointnews.com: acquisition, editorial production, web archives, analytics, and delivery. Kit is the authorized subscriber-storage and email-delivery backend. Substack is transitional rather than the permanent public signup experience.

## Native site foundation
- `/newsletter/` is the public newsletter home and signup destination.
- The Kit signup form is embedded on Rally Point News so subscriber information is handled by Kit rather than stored in the public GitHub repository.
- Homepage newsletter entry points route to the native Rally Point newsletter page.
- First-party analytics measure newsletter entry-point clicks and downstream site engagement where available.
- Newsletter editorial packages are built from `data/briefs.json`, `data/storylines.json`, and `data/history.json`; ChatGPT performs final editorial selection/synthesis only when warranted.
- Subscriber addresses, API credentials, and other private subscriber data must never be committed to the public repository.

## Authorized delivery backend — Kit
Kit is authorized on the free plan for subscriber storage, signup, unsubscribe/suppression handling, and broadcast delivery. The Kit V4 API credential is stored as the private GitHub Actions secret `KIT_API_KEY` and must never be written to repository files or logs.

Approved edition flow:
`Rally Brief Newsletter Editor -> data/newsletter_ready.json -> Rally Brief Delivery GitHub Action -> Kit broadcast -> subscribers`

The delivery action schedules a newly approved Kit broadcast only when an edition has a unique `edition_id` and `approved=true`. `data/newsletter_state.json` records sent/scheduled edition identifiers and the most recent Kit broadcast metadata to prevent duplicate sends. The workflow also has scheduled fallback checks in case the push-triggered delivery run is missed.

No paid Kit upgrade, separate email provider, or separately billed OpenAI API may be introduced without owner approval.

## Editorial contract
Product name: **The Rally Brief**.
Default cadence: morning edition, only when there is enough verified material to justify an edition.

Each edition should contain:
1. A concise subject line and preheader.
2. A short opening explaining the day's information picture without manufactured urgency.
3. The strongest original Rally Brief(s), linked to Rally Point News.
4. A compact multi-source developing-stories section when useful.
5. Direct attribution/links where needed.
6. A corrections/tips link once native newsroom intake exists.
7. A one-click unsubscribe mechanism supplied by Kit.

No filler. No fabricated facts, quotes, sourcing, urgency, or fake human authorship. Use **Rally Point News Desk** as the institutional editorial identity. Sensitive allegations, uncertain deaths, election calls, market-moving claims, or uncertain leaked/manipulated material require unusually strong verification or exclusion.

## Automation design
- GitHub Actions handles deterministic delivery, state tracking, archive/discovery work, and validation without AI/API spend.
- ChatGPT automation handles judgment-heavy story selection, synthesis, subject/preheader quality, and standards review.
- An edition is eligible for delivery only after the editorial automation explicitly marks it approved.
- Failed generation or insufficient newsworthiness means no send rather than a low-quality edition.
- Duplicate edition IDs must never be sent twice.
- Daily CEO reviews newsletter acquisition and engagement once measurable.

## Measurement
Primary funnel:
`homepage/newsletter CTA -> signup -> confirmed subscriber -> email open (when reliably available) -> click -> Rally Brief visit -> repeat visit`

Prioritize confirmed subscribers, click-through rate, Rally Brief sessions attributable to newsletter, and retention. Do not optimize around vanity opens alone because privacy protections can distort open-rate measurement.

## Migration from Substack
Do not silently copy subscriber addresses. When migration is appropriate, use an authorized export/import path that preserves consent and unsubscribe/suppression state. Keep Substack operational until the native Kit system is proven and existing subscribers have a safe migration path.

## Remaining owner gates
Owner approval remains required for paid-plan changes, new spending, sender-domain/DNS changes, new external providers, security/permission changes, or any migration of existing subscriber data that requires an account-level transfer or consent-sensitive operation. Routine editorial preparation and approved Kit delivery may proceed autonomously within the existing free setup.
