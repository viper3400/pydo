# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
