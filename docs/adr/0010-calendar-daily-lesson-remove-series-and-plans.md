# ADR 0010 — Today is a calendar Daily lesson; Series and Plan enrollment are removed

## Status

Accepted (2026-09-08). Supersedes the Series/Plan portions of ADR 0004's devotion scope. Formalises the `rooted-docs` PRD phase-1 override of 2026-08-27 ([rooted-docs#5](https://github.com/rooted-faith/rooted-docs/issues/5)) as an engineering decision, and extends it by removing the concepts outright rather than deferring them.

## Context

Rooted's devotion model was built around **Series** (an ordered course) and **Plan enrollment** (a user's commitment to walk one from a start date). The day's content was resolved client-side as `startedOn + N days` against a bundled catalog. `rooted-docs` still carries the full design — `series`, `lessons`, `plan_enrollments` tables, six `/devotion` endpoints — and `rooted_flutter` still ships `lib/features/plans/` with a `PlansBloc` wired into the Today screen and a `seriesId` on its `DailyLesson` model.

The PRD already overrode the *product* scope in August: phase 1 has no series or plans, and Today is a single calendar daily lesson. But the *model* was left in place as "Future", which means every new piece of devotion work still has to answer "does this go through a series?" — and the client still owns the decision of which content a person sees on a given day.

Product now also wants the day's content decided entirely by backend and operations staff. That is incompatible with keeping enrollment as the resolution mechanism, even a dormant one.

## Decision

1. **A Daily lesson is identified by its calendar date.** One date, one lesson, the same for every End user. There is no per-user content path.
2. **The backend resolves it, not the client.** `GET /api/v1/devotion/today?date=YYYY-MM-DD` — the client supplies its own local calendar date (BR-02: the device's local date, never server or a fixed Asia/Taipei). The client no longer carries a content catalog.
3. **Series and Plan enrollment are deleted, not deferred.** Removed from `CONTEXT.md`, from `rooted-docs` `database-design.md` (`series`, `lessons`, `plan_enrollments`) and `api-specification.md` (`/devotion/series`, `/devotion/series/{id}`, `/devotion/lessons/{lesson_id}`, `POST /devotion/enrollments`, `PATCH /devotion/enrollments/{series_id}`), and from `rooted_flutter` (`lib/features/plans/`, the `/plans` route, `DailyLesson.seriesId`).
4. **The Scripture for a day is one verse**, held as a **Passage** reference (`passage_start` / `passage_end` in `bible.verses`' `'JHN.3.16'` form) rather than a chapter or stored text. Stored as a range so it can widen to two or three verses later without a migration; operations fills a single verse by default.
5. **Signed-out End users see the verse only.** Reflection prompts, today's application and prayer are not in the anonymous response at all — `GET /devotion/today` returns the verse plus a `locked` list naming the withheld sections, so the client renders the sign-in invitation without ever holding the content.
6. **Recording completion is an Encounter day, not "Amen".** `POST /api/v1/devotion/encounters` replaces `POST /api/v1/devotion/amen`. Product copy stays 「今日已與主相遇」.

## Considered options

| Option | Rejected | Why |
| ------ | -------- | --- |
| Keep Series/Plan tables, mark "Future", ship the calendar path alongside | Dormant model retained | A dormant second content path still has to be reasoned about on every change, and its presence invites re-resolving Today through enrollment. The PRD already said phase 1 doesn't have it; the schema should say so too |
| Keep a single implicit "default series" so `seriesId` stays non-null | Fake series | Encodes a course that doesn't exist; the next engineer would build a series picker on top of it |
| Return the full lesson to anonymous callers and blur it client-side | Client-side gate only | Once everything but the verse is gated, the whole day's authored content would ride the wire for any unauthenticated caller. The sign-in invitation would be a door with no wall behind it |
| Server derives "today" from a device timezone the client sends | Timezone round-trip | The client already knows its local date; making the server re-derive it adds DST and travel edge cases for no gain (BR-02) |

## Consequences

- The `rooted-docs` PRD needs updating for the "Amen" → "Encounter" rename, the signed-out gate, and the weekly rhythm bar. **Tracked as a separate `rooted-docs` issue**, not part of this ADR; until it lands the PRD and this ADR disagree on those three points and the ADR wins.
- `rooted_flutter`'s `CONTEXT.md` currently states anonymous reads work identically to signed-in reads (`CONTEXT.md` End user; `devotion_repository.dart`). That is now false for everything but the verse and must be corrected when the client work happens.
- Nothing in `rooted-core-api` implements devotion yet — no models, no endpoints — so this removes documentation and client code, not backend code. The cost of this decision is paid almost entirely in `rooted_flutter`.
- Reversing this means reintroducing per-user content resolution, which touches the content schema, the API surface and the client. Genuinely expensive; that is why it is written down.
