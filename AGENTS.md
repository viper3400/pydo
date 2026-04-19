# AGENTS.md

Guidance for AI/code agents working in this repository.

## 1. Purpose and Scope

- App type: single-user Flask web app for `todo.txt` task management.
- Data model: file-backed (`data/todo.txt`), no database.
- Core modules:
  - `app.py`: web routes, auth gate, rendering, request handling.
  - `todolib.py`: todo parsing, serialization, and query logic.
  - `templates/`, `static/`: UI.

Keep changes minimal, targeted, and reversible.

## 2. Architecture Rules

- Keep todo parsing/business logic in `todolib.py`.
- Keep Flask route/controller behavior in `app.py`.
- Avoid adding cross-cutting logic directly in templates.
- Prefer extending existing helpers over duplicating logic.

## 3. Security Rules (Important)

- Never commit secrets or plaintext passwords.
- Password protection is env-driven:
  - `PYTODO_PASSWORD` or `PYTODO_PASSWORD_HASH`
  - `SECRET_KEY`
- If auth behavior is changed, preserve:
  - global login gate (`before_request` style),
  - brute-force lock file flow (`data/.auth_blocked`),
  - failed attempts accounting.
- Do not weaken auth/session protections or remove lock behavior unless explicitly requested.

## 4. File/Data Safety

- `data/` is runtime state. Treat it as user data.
- Do not delete or overwrite `data/todo.txt` unless task explicitly requires it.
- Avoid destructive git/file operations.

## 5. Coding Conventions

- Python:
  - Keep functions small and focused.
  - Preserve existing style and naming.
  - Add/keep docstrings where meaningful.
  - Avoid broad `except:` unless intentional and safe.
- Templates/CSS/JS:
  - Reuse existing Bootstrap-oriented patterns.
  - Keep UI changes consistent with current structure.
  - Favor small, explicit template changes over large rewrites.

## 6. Change Workflow

When implementing changes:

1. Inspect relevant files first (`app.py`, `todolib.py`, template/static files).
2. Implement minimal patch.
3. Run quick validations:
   - `python3 -m py_compile app.py todolib.py`
4. Summarize:
   - what changed,
   - why,
   - any limitations or manual verification needed.

## 7. Testing Expectations

- There is no formal test suite yet.
- For logic changes, perform at least lightweight runtime/syntax checks.
- For UI changes, mention what should be manually verified in browser.

## 8. Dependency and Deployment Guardrails

- Do not introduce heavy new dependencies unless necessary.
- Keep app runnable with current lightweight setup.
- If deployment/auth docs are updated, keep README instructions copy/paste friendly.
- Container publishing is automated by `.github/workflows/container-publish.yml`; keep image tagging behavior (`latest`, branch, `sha-*`, semver tags) consistent unless explicitly asked to change it.

## 9. Preferred Commit Message Style

- Conventional style:
  - `feat: ...`
  - `fix: ...`
  - `docs: ...`
  - `refactor: ...`
- Keep subject concise and specific to user-visible behavior or code area.

## 10. README Sync Policy

- Update `README.md` in the same change whenever any of these are modified:
  - setup/install/run steps,
  - environment variables or config,
  - auth/security behavior,
  - user-visible features or workflows.
- If README changes are intentionally skipped, include `[docs-skip]` in PR title or PR body with a short reason.
- When unsure, update `README.md`.
