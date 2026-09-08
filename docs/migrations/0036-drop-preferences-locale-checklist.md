# Human Alembic checklist — drop `app.user_preferences.locale` (#36 / ADR 0009)

Agents must **not** add, modify, or delete files under `alembic/versions/`. The ORM change is on the feature branch; this delta still needs a human-authored revision.

## Status

**Pending.** ORM, domain entity, provisioning command, and repository no longer reference the column; the database still has it.

## Goal

Drop the account-level `locale` column from `app.user_preferences`. UI language follows each Device's system locale (ADR 0009) and is never a synced account Preference.

## Suggested steps

1. **Autogenerate** after the ORM change is on the branch:
   - `uv run alembic revision --autogenerate -m "drop_user_preferences_locale"`
2. **Review the revision** for exactly one change:
   - `op.drop_column("user_preferences", "locale", schema="app")`
   - Nothing else on `app.user_preferences` (`display_name`, `theme`, `font_scale`, `bible_version`, `stage`, `reminder_time`, `reminder_enabled` all stay)
3. **Downgrade** should re-add the column as `sa.String(10)`, `nullable=False`, `server_default="zh-Hant"`.
4. **Apply locally:** `uv run alembic upgrade head`
5. **Smoke:** OTP verify and Google sign-in still provision Preferences for a brand-new email.

## Out of scope

- `bible_version` (an independently user-chosen, synced Preference — unchanged, ADR 0009 §2)
- `auth.user.preferred_locale_id` (Admin console locale, unrelated to App UI language)
