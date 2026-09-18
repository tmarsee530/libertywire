# Timeline return-state analytics

All state stays in browser `localStorage`; there is no account identifier. Events are guarded by `sessionStorage` so rerenders and browser refreshes in the same tab session do not double-fire.

- `timeline_return_visit`: once when a timeline loads with a prior meaningful visit; includes the durable timeline ID and current unseen count.
- `new_updates_available`: once when a returning visitor has at least one unseen durable update ID.
- `new_updates_seen`: once after an unseen update has been at least 55% visible for 1.2 seconds during a meaningful visit.
- `jump_to_new_updates`: once when the reader uses the catch-up jump control.
- `timeline_repeat_session`: once per returning timeline session, whether or not new updates exist.

A meaningful visit requires 10 visible seconds plus reader interaction, or 20 visible seconds without interaction. First visits establish a baseline only after that threshold. Returning visits mark individual new developments seen only after viewport exposure. Storage failures disable return state without affecting the timeline.
