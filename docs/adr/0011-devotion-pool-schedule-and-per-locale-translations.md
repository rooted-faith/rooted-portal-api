# ADR 0011 — Devotion content is a pool scheduled onto dates, with one translation row per locale

## Status

Accepted (2026-09-08). Builds on ADR 0010, which established that a Daily lesson is identified by its calendar date.

## Context

ADR 0010 makes operations staff responsible for what every End user reads on a given day. That raises three questions the old series-based design never had to answer, because content and date were the same thing there (`lessons.day` inside a series):

- Where does content live before it has a date, and can the same piece be used again on a different date?
- Rooted's supported languages are rows in the existing system locale catalog (`public.system_locale`, seeded via `portal/cli/datas/locale_data.py`, manageable from the admin console), and translation lags authoring. What does a reader get on a day whose copy in their language isn't written yet?
- What happens on a date nobody scheduled?

The previous `rooted-docs` design answered the second with JSONB columns holding all locales in one row (`lessons.title`, `body`, `reflect`, `apply`, `pray`), which makes "which days are missing English?" an unindexable JSON scan.

## Decision

1. **Two concepts, not one.** A **Devotion** is one authored piece in the editorial pool — a verse reference plus reflection prompts, today's application and prayer — and exists with no date attached. A **Daily lesson** is a Devotion scheduled onto one calendar date. The schedule is its own table keyed uniquely by date.
2. **A Devotion is authored and scheduled as one whole.** The four parts are written together and move together; there is no separate pool of reflection prompts or prayers to mix and match. They are written to answer each other.
3. **One translation row per locale.** No JSONB multi-locale columns. This makes "which Devotions are missing a given language?" an ordinary indexed query, and lets per-locale editing permissions exist later.
4. **Translation completeness is a publishing gate, not a runtime fallback.** A Devotion moves `draft` → `ready` only when **every active locale in the system locale catalog** has a translation row. There is no read-time fallback to another language: operations is blocked in the admin console before the gap can ever reach a reader.
5. **The locale catalog is the single source of truth for which languages are required.** Devotion code holds no hardcoded language list. The admin console's existing multi-locale form (`TranslationTabsForm`) already renders one tab per catalog locale; the backend gate must check the same set, or activating a new language would silently produce publishable content that 404s for its readers.
6. **There is no designated base locale for a Devotion.** The concept only existed to name a fallback target, and there is no fallback — every active locale is required, so none is privileged. Which tab the console opens first is a UI convenience (`defaultLocaleId`), not a domain rule. The catalog's own `is_default` flag governs unrelated admin-console behaviour and is deliberately not consulted here.
7. **An unscheduled date is an error, never auto-filled.** `GET /devotion/today` returns 404 for a date with no scheduled Daily lesson. The admin console carries a forward-looking schedule calendar with unfilled dates flagged, plus a warning as the scheduled horizon runs short.
8. **Content status stays two-state (`draft` → `ready`).** No review or approval workflow in this iteration.

## Considered options

| Option | Rejected | Why |
| ------ | -------- | --- |
| One row per calendar date holding the content inline | Date is the content's identity | Cheapest today, but a piece could never be rescheduled or reused, and drafts would have to squat on a date before anyone knew when they'd run |
| JSONB column per field holding all locales | Multi-locale rows | Cannot answer "what is untranslated?" without scanning JSON; cannot grant an English editor write access to only the English text |
| Read-time fallback to another language when a locale is missing | Silent fallback | Ships an experience nobody chose to ship, and removes the pressure that gets the translation done. Blocking at publish makes the gap visible to the person who can fix it |
| Auto-fill an unscheduled date from unused pool content | Silent substitution | Turns a scheduling failure into an invisible one. Operations would never learn they had missed a day, and readers would get content chosen by a fallback rule rather than by a person |
| Full `draft → in_review → approved → scheduled → published` workflow | Review workflow | With a small operations team, an unstaffed approval gate degrades into a rubber stamp. A schedule calendar with red gaps prevents the actual failure mode. `approved_by` can be added later without reshaping the model |

## Consequences

- Operations cannot publish a Devotion until every active locale is written. This is deliberate friction and will be felt; the alternative is readers hitting 404s or silently reading a language they did not choose.
- **Activating a new locale in the catalog immediately raises the bar for every unpublished Devotion**, and leaves already-published ones incomplete for the new language. Deactivating is the escape hatch. This coupling is intentional — it is what stops the two sources of truth from drifting — but it means locale activation is a content-operations decision, not just a system setting.
- Because the schedule is separate, the same Devotion can be scheduled onto more than one date over time. **Lesson notes and Encounter days therefore key on the calendar date, never on the Devotion** — a person's writing belongs to their day, not to the content, and a rescheduled Devotion must not resurface someone's two-year-old notes.
- Scripture text is never copied into a Devotion or its translations. A Devotion holds a **Passage** reference; the text is resolved from the reader's chosen **Bible version** against `bible.verses` at read time.
- The read path needs a locale. It comes from the request's `Accept-Language` header, consistent with ADR 0009 — language follows the device, and the anonymous read path has no account to consult.
