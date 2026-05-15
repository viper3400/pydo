# AGENTS.md

Guidance for AI/code agents working in this repository.

## 1. Scope

- Flask plugin package with file-backed todo state.
- Core split:
  - `src/flask_plugin_pydo/routes.py`: blueprint routes and request handling.
  - `src/flask_plugin_pydo/services.py`: runtime service layer and todo operations.
  - `src/flask_plugin_pydo/models.py`: parsing and serialization models.
  - `src/flask_plugin_pydo/forms.py`: request parsing helpers.
  - `src/flask_plugin_pydo/templates/`, `src/flask_plugin_pydo/static/`: plugin presentation assets.

Prefer minimal, reversible changes.

## 2. Architecture Contracts

- Keep controller flow in `routes.py`; keep business logic in `services.py` and parsing/model rules in `models.py`.
- Use stable task identity for mutations from filtered/sorted UI (line-based, not visible index).
- Keep active-list sort/group behavior aligned between `services.py` and `templates/pydo/index.html`.
- Keep task-row metadata layout stable: due/waiting row separate from project/context tags row.
- Preserve project hierarchy semantics:
  - `++MainProject` is parsed as a main project, not as a normal `+Project`.
  - `+Project` remains the normal project tag.
  - Sidebar main-project filters aggregate all tasks tagged with `++MainProject`.
  - Main-project child filters require both `++MainProject` and `+Project`.
  - Main-project tasks without child projects remain available under "No subproject".
- Preserve current active section order:
  `Overdue -> Due Today -> Prioritized (no due) -> Due This Week -> Other Due Dates -> Other Tasks`.
- Due+priority tasks must remain in due-date sections.
- Due quick actions must be line-targeted and reliable across repeated clicks (`Today` for overdue, `Tomorrow` for due-today).
- Hidden display metadata is allowlist-based (`due`, `waiting`, `link`); unknown `key:value` stays visible unless explicitly added.

## 3. Security

- Never commit secrets or plaintext passwords.
- Preserve plugin auth/session compatibility:
  - `PYTODO_PASSWORD` or `PYTODO_PASSWORD_HASH`
  - `SECRET_KEY`
  - `PYTODO_SESSION_COOKIE_NAME` (defaults to `pytodo_session`)
- Preserve login gate, failed-attempt accounting, and lock-file flow unless explicitly requested otherwise.
- Plugin host config keys include:
  - `PYDO_TODO_FILE`
  - `PYDO_DATA_DIR`
  - `PYDO_VERSION`
  - `PYDO_NOW_PROVIDER`
  - `PYDO_MAX_LOGIN_ATTEMPTS`

## 4. Data Safety

- Treat todo storage as user data; do not delete or overwrite the configured todo file unless explicitly requested.
- Avoid destructive git/file operations.

## 5. Validation

- Prefer `pytest`; always run lightweight compile checks:
  - `pytest -q`
  - `python3 -m py_compile src/flask_plugin_pydo/*.py`
- For list mutations (toggle/edit/delete), verify active/completed and filtered views.
- For UI behavior changes, include manual host-app verification notes for `/pydo/`.

## 6. Dependencies/Deploy

- Do not introduce heavy new dependencies unless necessary.
- Keep plugin integration and auth docs copy-paste friendly.
- Keep reverse-proxy compatibility for path-prefix deployments (for example `/pydo`) by preserving forwarded-prefix behavior.
- Plugin package releases use tags named `plugin-pydo-vX.Y.Z` and build from repo root.

## 7. Commits

- Use conventional messages (`feat`, `fix`, `docs`, `refactor`) with concise, specific subjects.

## 8. README Sync

- Update `README.md` in the same change when setup/config/auth or user-visible workflow changes.
- If intentionally skipped, include `[docs-skip]` in PR title/body with a short reason.

## 9. Governance Sync

- If governance-relevant files change (`pyproject.toml`, `src/flask_plugin_pydo/*.py`, `src/flask_plugin_pydo/templates/**`, `src/flask_plugin_pydo/static/**`, or `.github/workflows/*`), update `AGENTS.md` in the same change.
- If intentionally skipped, include `[agents-skip]` in PR title/body with a short reason.
- PRs opened by `dependabot[bot]` are exempt from README/AGENTS guard requirements in `.github/workflows/readme-guard.yml`.
