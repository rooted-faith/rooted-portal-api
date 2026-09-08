# Human Alembic checklist — add `app.user.reonboarding_requested_at` (#38 / ADR 0008)

Agents must **not** add, modify, or delete files under `alembic/versions/`. The ORM change is on the feature branch; this delta still needs a human-authored revision.

## Status

**Pending.** `AppUser`, the End user entity, the repository, both endpoints, and the member login/profile response all carry the flag; the database does not yet.

## Goal

Let an Admin flag one End user as needing to replay onboarding, and let the client clear the flag once the replay is done.

## Suggested steps

1. **Autogenerate** after the ORM change is on the branch:
   - `uv run alembic revision --autogenerate -m "add_app_user_reonboarding_requested_at"`
2. **Review the revision** for exactly one change:
   - `op.add_column("user", sa.Column("reonboarding_requested_at", sa.DateTime(timezone=True), nullable=True), schema="app")`
   - **Nullable, no server default** — null means "nothing pending", which is the correct state for every existing row.
3. **Apply locally:** `uv run alembic upgrade head`
4. **Smoke:** `POST /admin/api/v1/end-user/{end_user_id}/reonboarding` sets it, the member login response returns `reonboardingRequestedAt`, and `POST /api/v1/users/me/reonboarding/acknowledge` clears it.

## Also needs re-running (not Alembic)

`uv run python -m portal.cli.main` RBAC seed — the new `support:end_user` leaf resource and its permissions must exist before any non-superuser role can be granted `support:end_user:update`.

## Out of scope

- Ordinary first-time onboarding state, which stays local per-step client state and is never synced (ADR 0008)
