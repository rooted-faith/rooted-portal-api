# ADR 0012 — Store the longest Encounter streak; recompute the current one on every read

## Status

Accepted (2026-09-08).

## Context

The Today screen shows a weekly rhythm bar plus two numbers: the End user's **current** consecutive-day streak and their **longest ever**. The obvious implementation stores both as counters on a per-user row and updates them when an Encounter day is recorded.

That is wrong for one of the two numbers, in a way that looks fine in every test.

A streak has two ways to change: it grows when someone records an encounter, and it **breaks when time passes and they don't**. The first is a write. The second is not — nothing calls the backend on the day a person stops. A stored `current_streak` of `10` stays `10` for the six months someone is away, and is served as truth to anyone who reads it without checking the date.

## Decision

1. **`longest_streak` is stored.** It only ever increases, and only during a write. A stored value is always correct.
2. **`current_streak` is stored as `(streak_length, last_encounter_date)` and validated at read.** On read, compare `last_encounter_date` against the reader's own local calendar date (BR-02, supplied by the client): if it is today or yesterday, the current streak is `streak_length`; otherwise it is `0`. The stored pair is a cache of a write, never an answer on its own.
3. **The weekly bar is drawn from data, not from these numbers.** `GET /api/v1/devotion/rhythm?date=YYYY-MM-DD` returns `currentStreak`, `longestStreak` and a list of recently completed dates. The client slices that list into weeks using the End user's `week_start` preference (`sunday` | `monday`, default `sunday`).
4. **Week start is an account Preference, not a device fact.** Unlike UI language (ADR 0009), which day a week begins on is a personal habit that should follow the person across devices.

## Considered options

| Option | Rejected | Why |
| ------ | -------- | --- |
| Store both counters, update on write | Naive denormalisation | Serves a stale `current_streak` for the entire duration of any absence — the exact case where the number matters and the exact case no test with a fixed clock will catch |
| Store nothing; derive both from the encounter dates | Full recomputation | Correct, but computing "longest ever" means scanning a user's whole history on every Today open, forever. `longest_streak` is the one value that denormalises safely |
| Nightly job that decays stale current streaks | Scheduled correction | Adds infrastructure to fix a problem that a date comparison at read solves for free, and leaves a window where the value is wrong |
| Server derives "today" from the server clock | Server-side date | Rooted's servers are in North America and BR-02 defines the day as the device's local date. A server-clock comparison would break streaks for users near midnight |

## Consequences

- Reading the current streak requires the caller's local date. Every endpoint that returns it takes a `date` parameter; there is no "just read the column" path, and there should not be one.
- The stored `streak_length` will be stale between an absence and the next sign of life. That is expected and safe — nothing reads it unvalidated. **Any future code that reads `streak_length` without comparing `last_encounter_date` to the reader's local date is a bug**, which is why this ADR exists.
- Neither number is ever exposed to other members. The shepherd's pastoral view shows engagement signals, never comparable streak counts.
