# ADR 0009 — App UI language follows the device's system locale; no in-app switch, no stored account-level locale

## Status

Accepted (2026-09-06). Reverses `rooted-docs` PRD requirement A-07 and the "三語切換完整" acceptance item, and the "UI and Scripture language must match" rule (tracked for doc update separately, not part of this ADR).

## Context

The PRD currently requires an in-app 3-way language picker (an onboarding step plus a Settings switcher), kept consistent with Scripture language, backed by a `locale` column on `app.user_preferences` that syncs across a person's devices. Product now wants the UI language to always match the OS language of whichever device the app is running on, with no in-app override — Settings should deep-link to the OS's own per-app language screen instead of offering a picker.

A synced, account-level `locale` cannot represent "follow this device's system language": once a person has two devices set to different system languages, one stored value would force both to the same language, defeating the point of following the system. Keeping the column would misrepresent the decision.

## Decision

1. **Drop `app.user_preferences.locale`.** UI language is never stored account-side; it's derived from the device at runtime and is not an End-user-editable Preference.
2. **Bible Scripture language (`bible_version`) decouples from UI language** and stays an independently user-chosen, synced Preference — unchanged, already modeled since ADR 0004. The PRD's "UI and Scripture language must match" rule no longer applies.
3. **Where the backend needs a language for a specific piece of copy, it resolves it live, per touchpoint, never from a stored account preference:**
   - Synchronous flows (e.g. an OTP request) resolve language from that request's `Accept-Language` header, reusing the detector already built for the admin console (`portal/middlewares/core_request.py`).
   - Asynchronous push notifications resolve language from the target **Device**'s own last-known locale (a new field on Device, captured at registration/refresh) — the device that will actually show the notification, not the account.
4. **Settings keeps a read-only "Language" row** for discoverability, but it only deep-links to the OS's per-app language settings — there is no in-app picker anywhere in the product.

## Considered options

| Option | Rejected | Why |
| ------ | -------- | --- |
| Keep `locale` on `app.user_preferences`, just stop exposing a UI picker | Preference field survives, unused | Still misrepresents a per-device fact as a per-account one; next engineer would "fix" it by re-adding a picker |
| Move `locale` to `Device` and use it for everything, including OTP emails | Device-sourced locale for sync flows too | An OTP request already carries a live `Accept-Language` header from the requesting client — no need to round-trip through a stored Device row for something synchronous |

## Consequences

- `rooted-docs` PRD/sitemap need updating to remove the in-app switcher requirement and the UI/Scripture consistency rule (tracked separately).
- `Device` gains a `locale` field (implementation follow-up); push notification sends must read it instead of any End-user-level language.
- Agents must not reintroduce a synced `locale` preference on `app.user` — language is per-device, never per-account.
