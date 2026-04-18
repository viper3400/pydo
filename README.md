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
  -v "$(pwd)/data:/app/data" \
  --restart unless-stopped \
  pydo:latest
```

Open: `http://127.0.0.1:5000`

Synology (example host path):

```bash
-v /volume1/docker/pydo/data:/app/data
```

Notes:
- The container runs Linux, but works the same from Docker Desktop on macOS and Docker on Ubuntu/Synology.
- Keep `/app/data` mounted so `todo.txt` and auth lock files survive container restarts.

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
