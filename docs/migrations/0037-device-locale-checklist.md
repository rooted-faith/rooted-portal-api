# Human Alembic checklist — add `push.device.locale` (#37 / ADR 0009)

Agents must **not** add, modify, or delete files under `alembic/versions/`. The ORM change is on the feature branch; this delta still needs a human-authored revision.

## Status

**Pending.** `PushDevice`, the Device entity, the repository, and the registration endpoint all carry `locale`; the database does not yet.

## Goal

Give each Device its own last-known system locale, so push copy is composed in the language that specific install is set to instead of one language for the whole account.

## Suggested steps

1. **Autogenerate** after the ORM change is on the branch:
   - `uv run alembic revision --autogenerate -m "add_push_device_locale"`
2. **Review the revision** for exactly one change:
   - `op.add_column("device", sa.Column("locale", sa.String(20), nullable=True), schema="push")`
   - **Nullable, no server default** — devices registered before the client started sending a locale legitimately have none, and `PushService.notify` falls back to the default copy for them.
3. **Apply locally:** `uv run alembic upgrade head`
4. **Smoke:** `PUT /api/v1/push/devices/{device_key}` with and without `locale` in the body; re-registering the same `device_key` with a different locale overwrites it.

## Out of scope

- Backfilling a locale onto existing Device rows (there is no per-device value to backfill from — the client sends one on its next registration call)
- Any account-level locale (dropped in #36)
