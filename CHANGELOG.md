# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] - 2026-04-26

### Added
- Main project tags (`++MainProject`) with nested project sidebar grouping and filtering.

### Fixed
- Plus signs inside link URLs are no longer interpreted as project tags.

## [0.8.0] - 2026-04-25

### Added
- Duration context tags such as `@5min`, `@30min`, and numeric estimates like `@120` now use a distinct badge color.
- Duration contexts now appear in a dedicated "Duration Context" sidebar panel instead of the main context panel.
- Regression coverage for duration context detection and sidebar grouping.

## [0.7.1] - 2026-04-25

### Fixed
- Completed tasks with priorities now round-trip without duplicating or reordering completion metadata during repeated load/save cycles.

### Added
- Regression coverage for completed task serialization with and without priority metadata.

## [0.7.0] - 2026-04-22

### Added
- Due-date quick actions in task badges:
  - `Today →` for overdue tasks
  - `Tomorrow →` for tasks due today
- Regression coverage for due-date shift helpers and related Flask routes.

### Changed
- Task metadata layout in list rows is now clearer:
  - due/waiting badges on one line
  - project/context tags on a separate line

### Fixed
- Repeated due-date quick actions now work without manual page refresh by handling these actions through AJAX and in-place content refresh.


## [0.6.0] - 2026-04-21

### Added
- In-app delete confirmation modal with task preview (replacing plain browser confirm dialogs).
- Regression coverage for inline edit AJAX responses and completed->active reopen persistence.

### Changed
- Inline edit save now uses AJAX + in-place content refresh to avoid full-page reload jump/flicker.
- Delete action UI refreshed with a dedicated trash icon button and softer hover/focus styling.
- Agent and README documentation tightened and synced with current workflow behavior.

### Fixed
- Reopening completed tasks now reliably removes completion prefix metadata so tasks return to the active list after reload.

## [0.5.1] - 2026-04-21

### Changed
- Active-list section order refined so `Prioritized Tasks` (no due date) appears between `Due Today` and `Due This Week`.

### Fixed
- Ensured tasks with both due date and priority remain in due-date sections while non-due prioritized tasks are grouped separately in the intended position.

### Added
- Regression coverage for active-list ordering and grouping behavior in app tests.

## [0.5.0] - 2026-04-21

### Added
- Support for multiple `link:` metadata entries per task.
- Task links are now rendered as clickable entries below task labels (one link per line, opens in a new tab).

### Changed
- Active-list section ordering refined so non-due prioritized tasks appear after `Due This Week` and before `Other Due Dates`.
- Due+priority tasks now stay in due-date sections (instead of being split into prioritized-only sections).
- Task-row contrast improved for better readability (stronger borders, clearer hover state, and higher-contrast section backgrounds).

### Fixed
- Display metadata filtering now uses a known-key allowlist; unknown `key:value` tokens remain visible in task text.
- `Due This Week` no longer gets split when tasks have both due date and priority; ordering is by due date then priority.

## [0.4.0] - 2026-04-21

### Added
- Scoped sidebar filtering so project/context/priority/waiting filters follow the active tab (`Active` or `Completed`).
- Priority sidebar filtering via clickable priority entries.
- Visible "Current filter" indicator with a clear action above the task list.
- New app favicon and matching navbar brand icon.

### Changed
- Due-date badges now show weekday in calendar labels (for example `Tue, Apr 21, 2026`).
- Mobile layout improved with touch-friendly tabs, stacked add-task controls, and tighter task card spacing/alignment.
- README updated to document filtering scope behavior and explicit PyTodo extensions beyond base todo.txt.

### Fixed
- Toggling tasks in filtered/completed views now correctly targets the clicked entry.
- Active sidebar item hover/readability improved (no more low-contrast active hover text).
- Preserved `due:YYYY-MM-DD` metadata when completing tasks on matching calendar dates.

## [0.3.0] - 2026-04-20

### Added
- Inline-edit switch modal with save/cancel decision flow when unsaved changes exist.
- Modal preview for pending inline edit changes, including marked text and priority diffs.
- Main-list section counts in headers (for example `Overdue (3)`).

### Changed
- Main active-task grouping refined into distinct sections: Overdue, Due Today, Due This Week, Prioritized Tasks, Other Due Dates, and Other Tasks.
- Section styling in the main list now carries the due-state emphasis previously shown in duplicate sidebar panels.
- Main-list section headers were made larger, given more spacing, and enhanced with icons for prioritized and other due-date sections.
- Due/date duplicate panels were removed from the sidebar to avoid repeated information.
- Sidebar task snippets were updated to wrap across multiple lines instead of hard truncation.
- The `All` filter tab was removed from the UI.

## [0.2.1] - 2026-04-19

### Added
- Baseline automated test suite with `pytest` for core todo logic and Flask routes.
- GitHub Actions test workflow to run `pytest` and Python compile checks on pull requests.

### Changed
- Container publishing workflow now publishes only on version tags (`v*.*.*`) or manual dispatch.
- Dependabot commit message format aligned to conventional commit style (`chore(deps): ...`).
- Docs/agents guard now skips Dependabot PRs.

### Fixed
- Reverse-proxy login flow now preserves forwarded path prefixes (for example `/pydo`) after successful authentication.
- Session cookie name is now app-specific by default (`pytodo_session`) to avoid collisions with other apps on the same domain.

## [0.1.0] - 2026-04-19

### Added
- Initial public release of PyTodo with Flask UI and todo.txt file storage.
- Docker and Docker Compose runtime support.
- Optional password protection with failed-login lock file behavior.
