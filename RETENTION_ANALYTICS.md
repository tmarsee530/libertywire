# Timeline return-state analytics

All state stays in browser `localStorage`; there is no account identifier. Events are guarded by `sessionStorage` so rerenders and browser refreshes in the same tab session do not double-fire.

- `timeline_return_visit`: once when a timeline loads with a prior meaningful visit; includes the durable timeline ID and current unseen count.
- `new_updates_available`: once when a returning visitor has at least one unseen durable update ID.
- `new_updates_seen`: once after an unseen update has been at least 55% visible for 1.2 seconds during a meaningful visit.
- `jump_to_new_updates`: once when the reader uses the catch-up jump control.
- `timeline_repeat_session`: once per returning timeline session, whether or not new updates exist.

A meaningful visit requires 10 visible seconds plus reader interaction, or 20 visible seconds without interaction. First visits establish a baseline only after that threshold. Returning visits mark individual new developments seen only after viewport exposure. Storage failures disable return state without affecting the timeline.

## Intentional follow events

Follow state uses a separate `rp-follows-v1` record. Viewing or reading a timeline never creates a follow.

- `story_follow`: each successful, explicit press of **Follow this story**; never from rendering or state restoration.
- `story_unfollow`: each successful, explicit unfollow from a timeline or Your Stories.
- `following_view`: once per tab session when `/following/` renders; includes the followed-story count.
- `followed_story_open`: only when a reader activates a followed-story link on `/following/`.
- `followed_story_new_updates_available`: once per followed timeline per tab session when Your Stories finds durable material update IDs absent from read state.

Action events cannot be caused by rerendering. Availability/view events use `sessionStorage` guards. Follow data contains no account or personal identifier.

## Priority 4B prerequisites (not implemented)

Notification delivery should add an opt-in identity and channel layer outside this local record: verified email destinations, Web Push subscriptions and keys, server-side cross-device follow records, consent timestamps, unsubscribe controls, delivery/retry logs, and optional account linking. A notification candidate must reference a new durable material update ID; reclassification, added corroboration, regenerated wording, and timestamp-only changes must never enqueue delivery. The local schema already records the canonical timeline ID, follow time, last known update ID, and last known activity so it can be imported without rewriting timeline/read state.
