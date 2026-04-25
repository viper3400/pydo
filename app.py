"""
Simple todo.txt web application using Flask.
Follows Python best practices: separation of concerns, error handling, type hints.
"""

import os
import hmac
from pathlib import Path
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash

from todolib import TodoList, is_duration_context

# Configuration
BASE_DIR = Path(__file__).parent
TODOS_DIR = BASE_DIR / "data"
TODOS_FILE = TODOS_DIR / "todo.txt"

# Flask app setup
app = Flask(__name__, template_folder="templates")
app.config["ENV"] = "development"
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-production")
app.config["SESSION_COOKIE_NAME"] = (os.getenv("PYTODO_SESSION_COOKIE_NAME", "pytodo_session").strip()
                                     or "pytodo_session")
# Trust one reverse proxy hop for forwarded host/proto/prefix headers.
# This allows running behind path prefixes like /pydo via X-Forwarded-Prefix.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

AUTH_PASSWORD = os.getenv("PYTODO_PASSWORD", "")
AUTH_PASSWORD_HASH = os.getenv("PYTODO_PASSWORD_HASH", "")
AUTH_ENABLED = bool(AUTH_PASSWORD or AUTH_PASSWORD_HASH)
MAX_LOGIN_ATTEMPTS = 3
AUTH_ATTEMPTS_FILE = TODOS_DIR / ".auth_attempts"
AUTH_BLOCK_FILE = TODOS_DIR / ".auth_blocked"
app.config["AUTH_ENABLED"] = AUTH_ENABLED


def _get_app_version() -> str:
    """Resolve app version for UI display."""
    version = os.getenv("PYTODO_VERSION", "").strip()
    if version:
        return version

    version_file = BASE_DIR / "VERSION"
    if version_file.exists():
        try:
            file_version = version_file.read_text(encoding="utf-8").strip()
            if file_version:
                return file_version
        except Exception:
            return "-dev"

    return "-dev"


APP_VERSION = _get_app_version()
app.config["APP_VERSION"] = APP_VERSION


@app.context_processor
def inject_app_version():
    """Inject app version into all templates."""
    return {"app_version": APP_VERSION}


def _ensure_data_dir() -> None:
    TODOS_DIR.mkdir(parents=True, exist_ok=True)


def _read_attempt_count() -> int:
    try:
        return int(AUTH_ATTEMPTS_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return 0


def _write_attempt_count(count: int) -> None:
    _ensure_data_dir()
    AUTH_ATTEMPTS_FILE.write_text(str(count), encoding="utf-8")


def _reset_attempt_count() -> None:
    if AUTH_ATTEMPTS_FILE.exists():
        AUTH_ATTEMPTS_FILE.unlink()


def is_login_blocked() -> bool:
    return AUTH_BLOCK_FILE.exists()


def _block_login() -> None:
    _ensure_data_dir()
    AUTH_BLOCK_FILE.write_text("blocked", encoding="utf-8")


def _record_failed_login() -> int:
    count = _read_attempt_count() + 1
    _write_attempt_count(count)
    if count >= MAX_LOGIN_ATTEMPTS:
        _block_login()
    return count


def _verify_login_password(candidate: str) -> bool:
    if AUTH_PASSWORD_HASH:
        normalized_hash = AUTH_PASSWORD_HASH.strip()
        # Accept accidentally duplicated prefixes like "scrypt:scrypt:..."
        if normalized_hash.startswith("scrypt:scrypt:"):
            normalized_hash = normalized_hash.replace("scrypt:scrypt:", "scrypt:", 1)
        try:
            return check_password_hash(normalized_hash, candidate)
        except ValueError:
            app.logger.error("Invalid PYTODO_PASSWORD_HASH format.")
            return False
    if AUTH_PASSWORD:
        return hmac.compare_digest(AUTH_PASSWORD, candidate)
    return False


def _is_safe_next_url(target: str) -> bool:
    parsed = urlparse(target)
    return parsed.scheme == "" and parsed.netloc == ""


def _build_safe_next_url() -> str:
    """Build a relative post-login target that preserves reverse-proxy prefix."""
    full_path = request.full_path
    if full_path.endswith("?"):
        full_path = full_path[:-1]

    script_root = request.script_root or ""
    next_url = f"{script_root}{full_path}" if script_root else full_path
    return next_url or "/"


@app.before_request
def require_login():
    """Require login for all routes when password protection is enabled."""
    if not AUTH_ENABLED:
        return None

    endpoint = request.endpoint or ""
    allowed_endpoints = {"login", "static"}
    if endpoint in allowed_endpoints:
        return None

    if not session.get("authenticated"):
        return redirect(url_for("login", next=_build_safe_next_url()))

    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    """Password login page."""
    if not AUTH_ENABLED:
        return redirect(url_for("index"))

    if session.get("authenticated"):
        return redirect(url_for("index"))

    blocked = is_login_blocked()
    if not blocked and _read_attempt_count() >= MAX_LOGIN_ATTEMPTS:
        _reset_attempt_count()
    if request.method == "POST":
        next_url = (request.form.get("next") or "").strip()

        if blocked:
            flash(
                f"Login blocked after {MAX_LOGIN_ATTEMPTS} failed attempts. "
                f"Delete {AUTH_BLOCK_FILE} on the server to unlock.",
                "error",
            )
            return render_template("login.html", blocked=True, next_url=next_url, attempts_left=0)

        password = request.form.get("password", "")
        if _verify_login_password(password):
            session["authenticated"] = True
            _reset_attempt_count()

            if next_url and _is_safe_next_url(next_url):
                return redirect(next_url)
            return redirect(url_for("index"))

        attempts = _record_failed_login()
        if attempts >= MAX_LOGIN_ATTEMPTS:
            flash(
                f"Too many failed attempts. Login is blocked. Delete {AUTH_BLOCK_FILE} on the server to unlock.",
                "error",
            )
            return render_template("login.html", blocked=True, next_url=next_url, attempts_left=0)

        attempts_left = MAX_LOGIN_ATTEMPTS - attempts
        flash(f"Invalid password. {attempts_left} attempt(s) left.", "error")
        return render_template("login.html", blocked=False, next_url=next_url, attempts_left=attempts_left)

    next_url = (request.args.get("next") or "").strip()
    return render_template("login.html", blocked=blocked, next_url=next_url, attempts_left=MAX_LOGIN_ATTEMPTS)


@app.route("/logout")
def logout():
    """Clear login session."""
    session.clear()
    return redirect(url_for("login"))


def get_todos():
    """Get the current TodoList instance."""
    return TodoList(TODOS_FILE)


def sort_active_items(items):
    """Sort active tasks for display by due-date buckets, then priority/no-date tasks."""
    from datetime import datetime, timedelta

    today = datetime.now().strftime("%Y-%m-%d")
    week_end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    def sort_key(todo):
        due = todo.custom_fields.get("due")
        priority = todo.priority or "ZZ"

        if due and due < today:
            # Overdue first, oldest overdue first.
            return (0, due, priority)
        if due == today:
            # Then tasks due today, with priority as tie-breaker.
            return (1, priority, due)
        if todo.priority and not due:
            # Then prioritized tasks that have no due date.
            return (2, priority, "9999-12-31")
        if due and due <= week_end:
            # Keep all due-this-week tasks together, sorted by date then priority.
            return (3, due, priority)
        if due:
            # Then all other due dates, sorted by date then priority.
            return (4, due, priority)
        # Finally everything without due date/priority.
        return (5, "9999-12-31", priority)

    return sorted(items, key=sort_key)


def _normalize_sidebar_scope(scope: str) -> str:
    """Normalize sidebar scope to active/completed."""
    normalized = (scope or "active").strip().lower()
    if normalized in {"active", "completed"}:
        return normalized
    return "active"


def _get_items_for_scope(todos, scope: str):
    """Return tasks for the given scope."""
    if _normalize_sidebar_scope(scope) == "completed":
        return todos.get_completed()
    return todos.get_active()


def get_template_context(todos, items, filter_by="active", filter_value=None, sidebar_scope="active"):
    """Build the template context with all necessary data."""
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    active_items = todos.get_active()
    scoped_items = _get_items_for_scope(todos, sidebar_scope)
    normalized_scope = _normalize_sidebar_scope(sidebar_scope)
    scoped_projects = sorted({project for todo in scoped_items for project in todo.projects})
    scoped_context_values = {context for todo in scoped_items for context in todo.contexts}
    scoped_contexts = sorted(
        context for context in scoped_context_values
        if not is_duration_context(context)
    )
    scoped_duration_contexts = sorted(
        context for context in scoped_context_values
        if is_duration_context(context)
    )
    scoped_priorities = sorted({todo.priority for todo in scoped_items if todo.priority})
    waiting_tasks = [
        todo for todo in scoped_items
        if 'waiting' in todo.contexts or todo.custom_fields.get('waiting')
    ]
    scoped_waiting_for_people = sorted({
        todo.custom_fields.get("waiting")
        for todo in scoped_items
        if todo.custom_fields.get("waiting")
    })
    due_today = [
        todo for todo in active_items
        if todo.custom_fields.get("due") == today
    ]
    due_soon = [
        todo for todo in todos.get_due_soon()
        if todo.custom_fields.get("due") != today
    ]

    return {
        "todos": items,
        "sidebar_todos": scoped_items,
        "sidebar_scope": normalized_scope,
        "today": today,
        "projects": scoped_projects,
        "contexts": scoped_contexts,
        "duration_contexts": scoped_duration_contexts,
        "priorities": scoped_priorities,
        "overdue": todos.get_overdue(),
        "due_today": due_today,
        "due_soon": due_soon,
        "waiting_tasks": waiting_tasks,
        "waiting_for_people": scoped_waiting_for_people,
        "filter_by": filter_by,
        "filter_value": filter_value,
        "total_active": len(todos.get_active()),
        "total_completed": len(todos.get_completed()),
    }


@app.route("/")
def index():
    """Display the main todo list."""
    todos = get_todos()
    filter_by = request.args.get("filter", "active")

    if filter_by == "completed":
        items = todos.get_completed()
        sidebar_scope = "completed"
    elif filter_by == "all":
        items = todos.todos
        sidebar_scope = request.args.get("scope", "active")
    else:  # active (default)
        items = sort_active_items(todos.get_active())
        sidebar_scope = "active"

    context = get_template_context(todos, items, filter_by, sidebar_scope=sidebar_scope)
    return render_template("index.html", **context)


@app.route("/add", methods=["POST"])
def add_todo():
    """Add a new todo."""
    text = request.form.get("text", "").strip()
    priority = request.form.get("priority", "").strip() or None

    if not text:
        return redirect(url_for("index"))

    todos = get_todos()
    todos.add(text, priority=priority)

    return redirect(url_for("index"))


@app.route("/toggle/<int:index>", methods=["POST"])
def toggle_todo(index):
    """Toggle a todo's completion status."""
    line = request.form.get("line", "").strip()
    todos = get_todos()

    if line:
        todos.toggle_by_line(line)
    else:
        todos.toggle(index)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True})

    return redirect(request.referrer or url_for("index"))


@app.route("/delete/<int:index>", methods=["POST"])
def delete_todo(index):
    """Delete a todo."""
    line = request.form.get("line", "").strip()
    todos = get_todos()

    if line:
        todos.remove_by_line(line)
    else:
        todos.remove(index)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True})

    return redirect(request.referrer or url_for("index"))


@app.route("/edit/<int:index>", methods=["POST"])
def edit_todo(index):
    """Edit a todo's text."""
    old_line = request.form.get("line", "").strip()
    new_text = request.form.get("text", "").strip()
    new_priority = request.form.get("priority", "").strip() or None

    if not new_text:
        return jsonify({"success": False, "error": "Text cannot be empty"}), 400

    todos = get_todos()
    updated = False
    if old_line:
        updated = todos.update_by_line(old_line, new_text, priority=new_priority, update_priority=True)
    elif 0 <= index < len(todos.todos):
        todos.todos[index].text = new_text
        todos.todos[index].priority = new_priority
        todos.save()
        updated = True

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if not updated:
            return jsonify({"success": False, "error": "Task not found"}), 404
        return jsonify({"success": True})

    if not updated:
        return redirect(request.referrer or url_for("index"))

    return redirect(request.referrer or url_for("index"))


@app.route("/tomorrow/<int:index>", methods=["POST"])
def postpone_due_tomorrow(index):
    """Move a task due date forward by one day."""
    line = request.form.get("line", "").strip()
    todos = get_todos()
    updated = False

    if line:
        updated = todos.postpone_due_by_line(line, days=1)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if not updated:
            return jsonify({"success": False, "error": "Task due date not found"}), 404
        return jsonify({"success": True})

    return redirect(request.referrer or url_for("index"))


@app.route("/today/<int:index>", methods=["POST"])
def set_due_today(index):
    """Set a task due date to today."""
    from datetime import datetime

    line = request.form.get("line", "").strip()
    todos = get_todos()
    updated = False

    if line:
        updated = todos.set_due_by_line(line, datetime.now().strftime("%Y-%m-%d"))

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if not updated:
            return jsonify({"success": False, "error": "Task due date not found"}), 404
        return jsonify({"success": True})

    return redirect(request.referrer or url_for("index"))


@app.route("/project/<project>")
def filter_project(project):
    """Show todos for a specific project."""
    todos = get_todos()
    sidebar_scope = request.args.get("scope", "active")
    items = [t for t in _get_items_for_scope(todos, sidebar_scope) if project in t.projects]
    context = get_template_context(todos, items, "project", project, sidebar_scope=sidebar_scope)
    return render_template("index.html", **context)


@app.route("/context/<context>")
def filter_context(context):
    """Show todos for a specific context."""
    todos = get_todos()
    sidebar_scope = request.args.get("scope", "active")
    items = [t for t in _get_items_for_scope(todos, sidebar_scope) if context in t.contexts]
    context_dict = get_template_context(todos, items, "context", context, sidebar_scope=sidebar_scope)
    return render_template("index.html", **context_dict)


@app.route("/priority/<priority>")
def filter_priority(priority):
    """Show todos for a specific priority."""
    todos = get_todos()
    sidebar_scope = request.args.get("scope", "active")
    normalized_priority = (priority or "").strip().upper()
    if normalized_priority not in {"A", "B", "C"}:
        return redirect(url_for("index", filter=sidebar_scope))

    items = [t for t in _get_items_for_scope(todos, sidebar_scope) if t.priority == normalized_priority]
    context = get_template_context(
        todos,
        items,
        "priority",
        normalized_priority,
        sidebar_scope=sidebar_scope,
    )
    return render_template("index.html", **context)


@app.route("/due/<date>")
def filter_due(date):
    """Show todos due on a specific date."""
    todos = get_todos()
    items = [t for t in todos.todos if t.custom_fields.get('due') == date and not t.complete]
    context = get_template_context(todos, items, "due", date, sidebar_scope="active")
    return render_template("index.html", **context)


@app.route("/waiting")
def filter_waiting():
    """Show all waiting tasks."""
    todos = get_todos()
    sidebar_scope = request.args.get("scope", "active")
    items = [
        t for t in _get_items_for_scope(todos, sidebar_scope)
        if 'waiting' in t.contexts or t.custom_fields.get('waiting')
    ]
    context = get_template_context(todos, items, "waiting", sidebar_scope=sidebar_scope)
    return render_template("index.html", **context)


@app.route("/waiting/<person>")
def filter_waiting_for(person):
    """Show tasks waiting for a specific person."""
    todos = get_todos()
    sidebar_scope = request.args.get("scope", "active")
    items = [
        t for t in _get_items_for_scope(todos, sidebar_scope)
        if t.custom_fields.get('waiting', '').lower() == person.lower()
    ]
    context = get_template_context(todos, items, "waiting_for", person, sidebar_scope=sidebar_scope)
    return render_template("index.html", **context)


@app.template_filter('count_with_project')
def count_with_project(todos, project):
    """Count todos that have a specific project."""
    return len([t for t in todos if project in t.projects])


@app.template_filter('count_with_context')
def count_with_context(todos, context):
    """Count todos that have a specific context."""
    return len([t for t in todos if context in t.contexts])


@app.template_filter('is_duration_context')
def is_duration_context_filter(context):
    """Return whether a context tag should be styled as a duration."""
    return is_duration_context(context)


@app.template_filter('count_waiting_for')
def count_waiting_for(todos, person):
    """Count todos waiting for a specific person."""
    return len([t for t in todos if t.custom_fields.get('waiting', '').lower() == person.lower()])


@app.template_filter('count_with_priority')
def count_with_priority(todos, priority):
    """Count todos that have a specific priority."""
    return len([t for t in todos if t.priority == priority])


@app.template_filter('format_date')
def format_date(date_str):
    """Format date string for display (YYYY-MM-DD -> readable format)."""
    from datetime import datetime
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%b %d, %Y")
    except:
        return date_str


@app.template_filter('format_due_date')
def format_due_date(date_str):
    """Format due date with weekday for calendar-style display."""
    from datetime import datetime
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%a, %b %d, %Y")
    except:
        return date_str


@app.template_filter('external_link_href')
def external_link_href(link_value):
    """Normalize link custom-field values to safe external HTTP(S) URLs."""
    value = (link_value or "").strip()
    if not value:
        return ""

    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return value
    if parsed.scheme:
        # Reject non-web schemes (e.g. javascript:, data:, file:).
        return ""
    return f"https://{value}"


@app.template_filter('is_overdue')
def is_overdue(date_str):
    """Check if date is overdue (in the past)."""
    from datetime import datetime
    try:
        return date_str < datetime.now().strftime("%Y-%m-%d")
    except:
        return False


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template("500.html"), 500


if __name__ == "__main__":
    # Create data directory if it doesn't exist
    TODOS_DIR.mkdir(parents=True, exist_ok=True)

    # Run the app
    app.run(debug=True, host="127.0.0.1", port=5000)
