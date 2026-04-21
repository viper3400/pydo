# AGENTS.md

Guidance for AI/code agents working in this repository.

## 1. Scope

- Single-user Flask app with file-backed state (`data/todo.txt`).
- Core split:
  - `app.py`: routing, request handling, auth/session.
  - `todolib.py`: parsing, serialization, query/update logic.
  - `templates/`, `static/`: presentation and client behavior.

Prefer minimal, reversible changes.

## 2. Architecture Contracts

- Keep business logic in `todolib.py`; keep controller flow in `app.py`.
- Use stable task identity for mutations from filtered/sorted UI (line-based, not visible index).
- Keep active-list sort/group behavior aligned between `app.py` and `templates/index.html`.
- Preserve current active section order:
  `Overdue -> Due Today -> Prioritized (no due) -> Due This Week -> Other Due Dates -> Other Tasks`.
- Due+priority tasks must remain in due-date sections.
- Hidden display metadata is allowlist-based (`due`, `waiting`, `link`); unknown `key:value` stays visible unless explicitly added.

## 3. Security

- Never commit secrets or plaintext passwords.
- Auth/session settings are env-driven:
  - `PYTODO_PASSWORD` or `PYTODO_PASSWORD_HASH`
  - `SECRET_KEY`
  - `PYTODO_SESSION_COOKIE_NAME` (defaults to `pytodo_session`)
- Preserve login gate, failed-attempt accounting, and lock-file flow (`data/.auth_blocked`) unless explicitly requested otherwise.

## 4. Data Safety

- Treat `data/` as user data; do not delete/overwrite `data/todo.txt` unless explicitly requested.
- Avoid destructive git/file operations.

## 5. Validation

- Prefer `pytest`; always run lightweight compile checks:
  - `pytest -q`
  - `python3 -m py_compile app.py todolib.py`
- For list mutations (toggle/edit/delete), verify active/completed and filtered views.
- For UI behavior changes, include manual browser verification notes.

## 6. Dependencies/Deploy

- Do not introduce heavy new dependencies unless necessary.
- Keep deployment/auth docs copy-paste friendly.
- Keep reverse-proxy compatibility for path-prefix deployments (for example `/pydo`) by preserving forwarded-prefix behavior.

## 7. Commits

- Use conventional messages (`feat`, `fix`, `docs`, `refactor`) with concise, specific subjects.

## 8. README Sync

- Update `README.md` in the same change when setup/config/auth or user-visible workflow changes.
- If intentionally skipped, include `[docs-skip]` in PR title/body with a short reason.

## 9. Governance Sync

- If `.github/workflows/*` changes, update `AGENTS.md` in the same change.
- If intentionally skipped, include `[agents-skip]` in PR title/body with a short reason.
- PRs opened by `dependabot[bot]` are exempt from README/AGENTS guard requirements in `.github/workflows/readme-guard.yml`.
