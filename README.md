# PyTodo - A Simple Todo.txt Web App

A lightweight, Python-based web application for managing tasks using the [todo.txt](https://github.com/todotxt/todo.txt) format.

## Features

- ✅ **Full todo.txt Support**: Parse and manage tasks in standard todo.txt format
- 📝 **Simple Web Interface**: Clean, responsive UI built with Bootstrap 5
- 🏷️ **Organize Tasks**: Support for priorities (A-Z), projects (+ProjectName), and contexts (@context)
- 📊 **Smart Filtering**: View tasks by status, project, or context
- ⏳ **Waiting Workflow**: Track blocked tasks with `@waiting` and `waiting:<person>`
- ⚡ **Lightweight**: No database required—uses plain text files
- 🎨 **Modern Design**: Responsive design that works on desktop and mobile

## Installation

### 1. Clone or navigate to the project directory

```bash
cd pytodo
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Start the server

```bash
python app.py
```

The app will be available at `http://127.0.0.1:5000`

### Run with Docker (macOS + Ubuntu/Synology)

Build the image:

```bash
docker build -t pydo:latest .
```

Run the container with persistent data:

```bash
docker run -d \
  --name pydo \
  -p 5000:5000 \
  -e SECRET_KEY='replace-with-a-random-long-secret' \
  -e PYTODO_PASSWORD_HASH='paste-generated-hash-here' \
  -e PYTODO_VERSION='1.0.0' \
  -v "$(pwd)/data:/app/data" \
  --restart unless-stopped \
  pydo:latest
```

Open: `http://127.0.0.1:5000`

Or run with Docker Compose (uses `docker-compose.yml`):

```bash
docker compose up -d
```

Compose file highlights:
- publishes `8080 -> 5000`
- includes example `SECRET_KEY` and `PYTODO_PASSWORD_HASH`
- supports optional `PYTODO_VERSION` shown in the app footer
- mounts `./data` to `/app/data` for persistent tasks and auth lock files
- runs as a configurable UID/GID via `PYDO_UID`/`PYDO_GID` (defaults to `0:0` for bind-mount write compatibility)

Synology (example host path):

```bash
-v /volume1/docker/pydo/data:/app/data
```

Notes:
- The container runs Linux, but works the same from Docker Desktop on macOS and Docker on Ubuntu/Synology.
- Keep `/app/data` mounted so `todo.txt` and auth lock files survive container restarts.
- If your host files are owned by another user/group, set `PYDO_UID` and `PYDO_GID` in your shell or compose `.env` before `docker compose up -d`.

### Docker Volume Permission Troubleshooting

If you see `PermissionError: [Errno 13]` for `/app/data/todo.txt`, the bind-mounted file is not writable by the container user.

Check ownership and mode on host:

```bash
ls -l ./data/todo.txt
```

With this repository's `docker-compose.yml`, container user defaults to `0:0` (root) for compatibility.  
If you prefer non-root runtime, set matching host UID/GID:

```bash
export PYDO_UID="$(id -u)"
export PYDO_GID="$(id -g)"
docker compose up -d
```

### Reverse Proxy Under A Path Prefix (Example: `/pydo/`)

If you cannot use a dedicated subdomain, proxy PyTodo under a prefix and forward the prefix header:

```nginx
location = /pydo {
  return 301 /pydo/;
}

location /pydo/ {
  proxy_pass http://127.0.0.1:8080/;
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_set_header X-Forwarded-Prefix /pydo;
}
```

PyTodo uses forwarded prefix headers to generate correct links/redirects when mounted under `/pydo/`.

### Build And Publish Container With GitHub Actions (GHCR)

This repository includes a workflow at `.github/workflows/container-publish.yml` that:
- builds on pull requests to `main` (build only, no push)
- builds and publishes on pushes to `main`
- builds and publishes on version tags like `v1.2.3`
- passes the resolved version to the image as `PYTODO_VERSION`, so the app footer reflects the image version

Published image:

```bash
ghcr.io/<owner>/<repo>
```

Tag behavior:
- `latest`: updated from the default branch
- `main`: updated from `main` branch pushes
- `sha-<commit>`: immutable commit-based tag
- `vX.Y.Z`: full version tag when you push a matching git tag
- `X.Y`: rolling minor tag for semver releases (for example `1.2`)

Create and push a release tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

### Optional: Password Protection (Single User)

Set one of these environment variables before starting the app:

```bash
export PYTODO_PASSWORD='your-strong-password'
# OR (preferred)
export PYTODO_PASSWORD_HASH='pbkdf2:sha256:...'
```

Generate a password hash on macOS:

```bash
python3 - <<'PY'
from getpass import getpass
from werkzeug.security import generate_password_hash
pw = getpass("Password: ")
print(generate_password_hash(pw))
PY
```

Then export it:

```bash
export PYTODO_PASSWORD_HASH='paste-generated-hash-here'
```

Optional but strongly recommended:

```bash
export SECRET_KEY='replace-with-a-random-long-secret'
```

Optional app version label shown in the footer:

```bash
export PYTODO_VERSION='1.0.0'
```

If `PYTODO_VERSION` is unset, the app falls back to a local `VERSION` file, then `dev`.

Behavior:
- All app routes require login when password protection is enabled.
- After 3 failed login attempts, the app creates `data/.auth_blocked`.
- While `data/.auth_blocked` exists, login stays blocked.
- To unlock, delete `data/.auth_blocked` on the server.

### Todo.txt Format Basics

#### Incomplete Tasks
```
Buy groceries
(A) Finish project proposal
(B) 2026-04-16 Call the dentist
Research +ProjectX @phone
```

#### Complete Tasks
```
x Bought milk
x 2026-04-16 2026-04-15 Sent report +ProjectY
```

#### Format Rules

**Priority** (optional): `(A-Z)` at the start of the line
- Example: `(A) High priority task`

**Creation Date** (optional): `YYYY-MM-DD` after priority
- Example: `(A) 2026-04-16 Task with date`

**Completion**: Start with `x ` followed by optional `YYYY-MM-DD` date
- Example: `x 2026-04-16 Completed task`

**Projects**: `+ProjectName` anywhere in the task
- Example: `Work on +ProjectX design`

**Contexts**: `@context` anywhere in the task
- Example: `Call +john @phone`

**Custom Fields**: `key:value` anywhere in the task
- Example: `Fix bug due:2026-04-20 @bug`

## Project Extensions (Not Default todo.txt Spec)

This app supports a few practical extensions that are not part of the default todo.txt specification.

### Waiting Features

- `@waiting`: Marks a task as waiting/blocked
- `waiting:<person>`: Marks who you are waiting on

Examples:
```
Follow up on contract @waiting +Legal
Prepare release notes waiting:Alex +Platform
```

In the UI, you can:
- View all waiting tasks via the Waiting filter
- View tasks waiting on a specific person via `waiting:<person>`

## Project Structure

```
pytodo/
├── app.py              # Flask application
├── todolib.py          # Todo.txt parsing and management
├── requirements.txt    # Python dependencies
├── templates/          # Jinja2 HTML templates
│   ├── base.html       # Base template
│   ├── index.html      # Main page
│   ├── 404.html        # 404 error page
│   └── 500.html        # 500 error page
├── static/             # CSS and JavaScript
│   ├── style.css       # Custom styles
│   └── app.js          # Client-side logic
└── data/               # Data directory (auto-created)
    └── todo.txt        # Your todo file
```

## Development

The app follows Python best practices:

- **Type Hints**: Clear type annotations for better IDE support
- **Separation of Concerns**: Parsing logic separated from web logic
- **Error Handling**: Proper error pages and exception handling
- **Code Organization**: Modular design with clear responsibilities
- **Documentation**: Docstrings and inline comments

### Key Components

**todolib.py**
- `Todo`: Represents a single task
- `TodoList`: Manages reading/writing and querying tasks

**app.py**
- Flask routes for viewing and managing tasks
- Data persistence and filtering

## Keyboard Shortcuts

- **Ctrl/Cmd + K**: Focus on add todo input (future enhancement)

## License

MIT

## References

- [todo.txt Format Specification](https://github.com/todotxt/todo.txt)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Bootstrap 5 Documentation](https://getbootstrap.com/)
