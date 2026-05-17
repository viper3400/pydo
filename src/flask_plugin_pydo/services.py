"""Business logic and runtime services for the PyDo plugin."""

from __future__ import annotations

import hmac
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from flask import Request, current_app
from werkzeug.security import check_password_hash

from flask_plugin_pydo.models import ProjectGroup, Todo
from flask_plugin_pydo.versioning import resolve_plugin_version


DateTimeProvider = Callable[[], datetime]


def is_duration_context(context: str) -> bool:
    normalized = context.strip().lower()
    return bool(re.fullmatch(r"\d+\s*min", normalized) or re.fullmatch(r"\d+", normalized))


@dataclass(slots=True)
class PydoSettings:
    todo_file: Path
    auth_password: str
    auth_password_hash: str
    auth_enabled: bool
    max_login_attempts: int
    auth_attempts_file: Path
    auth_block_file: Path
    app_version: str
    now_provider: DateTimeProvider

    @classmethod
    def from_current_app(cls) -> "PydoSettings":
        configured_file = current_app.config.get("PYDO_TODO_FILE")
        configured_dir = current_app.config.get("PYDO_DATA_DIR")

        if configured_file:
            todo_file = Path(str(configured_file))
            data_dir = todo_file.parent
        else:
            if configured_dir:
                data_dir = Path(str(configured_dir))
            else:
                data_dir = Path(current_app.instance_path) / "pydo"
            todo_file = data_dir / "todo.txt"

        auth_password = str(current_app.config.get("PYTODO_PASSWORD") or os.getenv("PYTODO_PASSWORD", ""))
        auth_password_hash = str(
            current_app.config.get("PYTODO_PASSWORD_HASH") or os.getenv("PYTODO_PASSWORD_HASH", "")
        )
        auth_enabled = bool(auth_password or auth_password_hash)
        now_provider = current_app.config.get("PYDO_NOW_PROVIDER") or datetime.now
        version = str(current_app.config.get("PYDO_VERSION", "")).strip() or resolve_plugin_version()

        return cls(
            todo_file=todo_file,
            auth_password=auth_password,
            auth_password_hash=auth_password_hash,
            auth_enabled=auth_enabled,
            max_login_attempts=int(current_app.config.get("PYDO_MAX_LOGIN_ATTEMPTS", 3)),
            auth_attempts_file=data_dir / ".auth_attempts",
            auth_block_file=data_dir / ".auth_blocked",
            app_version=version,
            now_provider=now_provider,
        )


class TodoList:
    """Manager for a todo.txt file."""

    def __init__(self, filepath: Path, now_provider: DateTimeProvider | None = None) -> None:
        self.filepath = Path(filepath)
        self.now_provider = now_provider or datetime.now
        self.todos: list[Todo] = []
        self.load()

    def load(self) -> None:
        self.todos = []
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.filepath.touch()
            return

        with self.filepath.open("r", encoding="utf-8") as file_obj:
            for line in file_obj:
                todo = Todo.from_line(line.rstrip("\n"))
                if todo:
                    self.todos.append(todo)

    def save(self) -> None:
        with self.filepath.open("w", encoding="utf-8") as file_obj:
            for todo in self.todos:
                file_obj.write(todo.to_line() + "\n")

    def add(self, text: str, priority: str | None = None) -> Todo:
        todo = Todo(text=text, priority=priority)
        self.todos.append(todo)
        self.save()
        return todo

    def toggle(self, index: int) -> None:
        if 0 <= index < len(self.todos):
            todo = self.todos[index]
            todo.complete = not todo.complete
            if todo.complete:
                todo.completion_date = self.now_provider().strftime("%Y-%m-%d")
            else:
                todo.text = re.sub(r"^x(?:\s+\d{4}-\d{2}-\d{2})?\s+", "", todo.text).strip()
                todo.completion_date = None
            self.save()

    def toggle_by_line(self, line: str) -> None:
        for index, todo in enumerate(self.todos):
            if todo.to_line() == line:
                self.toggle(index)
                return

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.todos):
            self.todos.pop(index)
            self.save()

    def remove_by_line(self, line: str) -> None:
        for index, todo in enumerate(self.todos):
            if todo.to_line() == line:
                self.remove(index)
                return

    def update_by_line(
        self,
        old_line: str,
        new_text: str,
        priority: str | None = None,
        update_priority: bool = False,
    ) -> bool:
        for todo in self.todos:
            if todo.to_line() == old_line:
                todo.text = re.sub(r"^\([A-Z]\)\s+", "", new_text).strip()
                if update_priority:
                    todo.priority = priority
                self.save()
                return True
        return False

    def _replace_due(self, old_line: str, next_due: str) -> bool:
        for todo in self.todos:
            if todo.to_line() == old_line and todo.custom_fields.get("due"):
                todo.text = re.sub(r"(?<!\S)due:\S+", f"due:{next_due}", todo.to_line(), count=1)
                updated = Todo.from_line(todo.text)
                if updated is None:
                    return False
                todo.text = updated.text
                todo.complete = updated.complete
                todo.priority = updated.priority
                todo.creation_date = updated.creation_date
                todo.completion_date = updated.completion_date
                todo.main_projects = updated.main_projects
                todo.projects = updated.projects
                todo.contexts = updated.contexts
                todo.custom_fields = updated.custom_fields
                todo.links = updated.links
                self.save()
                return True
        return False

    def postpone_due_by_line(self, line: str, days: int) -> bool:
        for todo in self.todos:
            if todo.to_line() == line:
                due = todo.custom_fields.get("due")
                if not due:
                    return False
                next_due = (datetime.strptime(due, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")
                return self._replace_due(line, next_due)
        return False

    def set_due_by_line(self, line: str, due_date: str) -> bool:
        return self._replace_due(line, due_date)

    def get_active(self) -> list[Todo]:
        return [todo for todo in self.todos if not todo.complete]

    def get_completed(self) -> list[Todo]:
        return [todo for todo in self.todos if todo.complete]

    def get_overdue(self) -> list[Todo]:
        today = self.now_provider().strftime("%Y-%m-%d")
        return [todo for todo in self.get_active() if (due := todo.custom_fields.get("due")) and due < today]

    def get_due_soon(self) -> list[Todo]:
        today = self.now_provider().strftime("%Y-%m-%d")
        week_end = (self.now_provider() + timedelta(days=7)).strftime("%Y-%m-%d")
        return [
            todo for todo in self.get_active()
            if (due := todo.custom_fields.get("due")) and today <= due <= week_end
        ]


class PydoService:
    """Application-facing service layer."""

    def __init__(self, settings: PydoSettings) -> None:
        self.settings = settings

    def now(self) -> datetime:
        return self.settings.now_provider()

    def today(self) -> str:
        return self.now().strftime("%Y-%m-%d")

    def week_end(self) -> str:
        return (self.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    def get_todos(self) -> TodoList:
        return TodoList(self.settings.todo_file, now_provider=self.settings.now_provider)

    def ensure_data_dir(self) -> None:
        self.settings.todo_file.parent.mkdir(parents=True, exist_ok=True)

    def read_attempt_count(self) -> int:
        try:
            return int(self.settings.auth_attempts_file.read_text(encoding="utf-8").strip())
        except Exception:
            return 0

    def write_attempt_count(self, count: int) -> None:
        self.ensure_data_dir()
        self.settings.auth_attempts_file.write_text(str(count), encoding="utf-8")

    def reset_attempt_count(self) -> None:
        if self.settings.auth_attempts_file.exists():
            self.settings.auth_attempts_file.unlink()

    def is_login_blocked(self) -> bool:
        return self.settings.auth_block_file.exists()

    def block_login(self) -> None:
        self.ensure_data_dir()
        self.settings.auth_block_file.write_text("blocked", encoding="utf-8")

    def record_failed_login(self) -> int:
        count = self.read_attempt_count() + 1
        self.write_attempt_count(count)
        if count >= self.settings.max_login_attempts:
            self.block_login()
        return count

    def verify_login_password(self, candidate: str) -> bool:
        if self.settings.auth_password_hash:
            normalized_hash = self.settings.auth_password_hash.strip()
            if normalized_hash.startswith("scrypt:scrypt:"):
                normalized_hash = normalized_hash.replace("scrypt:scrypt:", "scrypt:", 1)
            try:
                return check_password_hash(normalized_hash, candidate)
            except ValueError:
                current_app.logger.error("Invalid PYTODO_PASSWORD_HASH format.")
                return False
        if self.settings.auth_password:
            return hmac.compare_digest(self.settings.auth_password, candidate)
        return False

    def is_safe_next_url(self, target: str) -> bool:
        parsed = urlparse(target)
        return parsed.scheme == "" and parsed.netloc == ""

    def build_safe_next_url(self, request: Request) -> str:
        full_path = request.full_path
        if full_path.endswith("?"):
            full_path = full_path[:-1]
        script_root = request.script_root or ""
        next_url = f"{script_root}{full_path}" if script_root else full_path
        return next_url or "/"

    def sort_active_items(self, items: list[Todo]) -> list[Todo]:
        today = self.today()
        week_end = self.week_end()

        def sort_key(todo: Todo) -> tuple[object, ...]:
            due = todo.custom_fields.get("due")
            priority = todo.priority or "ZZ"
            if due and due < today:
                return (0, due, priority)
            if due == today:
                return (1, priority, due)
            if todo.priority and not due:
                return (2, priority, "9999-12-31")
            if due and due <= week_end:
                return (3, due, priority)
            if due:
                return (4, due, priority)
            return (5, "9999-12-31", priority)

        return sorted(items, key=sort_key)

    def normalize_sidebar_scope(self, scope: str) -> str:
        normalized = (scope or "active").strip().lower()
        if normalized in {"active", "completed"}:
            return normalized
        return "active"

    def get_items_for_scope(self, todos: TodoList, scope: str) -> list[Todo]:
        if self.normalize_sidebar_scope(scope) == "completed":
            return todos.get_completed()
        return todos.get_active()

    def build_project_hierarchy(self, items: list[Todo]) -> dict[str, list[dict[str, object]] | list[str]]:
        groups: dict[str, ProjectGroup] = {}
        ungrouped_projects: set[str] = set()

        for todo in items:
            if todo.main_projects:
                for main_project in todo.main_projects:
                    group = groups.setdefault(main_project, ProjectGroup(name=main_project))
                    group.count += 1
                    if todo.projects:
                        for project in todo.projects:
                            group.projects[project] = group.projects.get(project, 0) + 1
                    else:
                        group.no_subproject_count += 1
            else:
                ungrouped_projects.update(todo.projects)

        return {
            "groups": [group.to_template_dict() for _, group in sorted(groups.items())],
            "ungrouped_projects": sorted(ungrouped_projects),
        }

    def build_template_context(
        self,
        todos: TodoList,
        items: list[Todo],
        filter_by: str = "active",
        filter_value: object = None,
        sidebar_scope: str = "active",
    ) -> dict[str, object]:
        today = self.today()
        active_items = todos.get_active()
        scoped_items = self.get_items_for_scope(todos, sidebar_scope)
        normalized_scope = self.normalize_sidebar_scope(sidebar_scope)
        project_hierarchy = self.build_project_hierarchy(scoped_items)
        scoped_context_values = {context for todo in scoped_items for context in todo.contexts}
        scoped_contexts = sorted(context for context in scoped_context_values if not is_duration_context(context))
        scoped_duration_contexts = sorted(context for context in scoped_context_values if is_duration_context(context))
        scoped_priorities = sorted({todo.priority for todo in scoped_items if todo.priority})
        waiting_tasks = [
            todo for todo in scoped_items
            if "waiting" in todo.contexts or todo.custom_fields.get("waiting")
        ]
        waiting_for_people = sorted({
            todo.custom_fields.get("waiting")
            for todo in scoped_items
            if todo.custom_fields.get("waiting")
        })
        due_today = [todo for todo in active_items if todo.custom_fields.get("due") == today]
        due_soon = [todo for todo in todos.get_due_soon() if todo.custom_fields.get("due") != today]

        return {
            "todos": items,
            "sidebar_todos": scoped_items,
            "sidebar_scope": normalized_scope,
            "today": today,
            "project_hierarchy": project_hierarchy,
            "projects": project_hierarchy["ungrouped_projects"],
            "contexts": scoped_contexts,
            "duration_contexts": scoped_duration_contexts,
            "priorities": scoped_priorities,
            "overdue": todos.get_overdue(),
            "due_today": due_today,
            "due_soon": due_soon,
            "waiting_tasks": waiting_tasks,
            "waiting_for_people": waiting_for_people,
            "filter_by": filter_by,
            "filter_value": filter_value,
            "total_active": len(todos.get_active()),
            "total_completed": len(todos.get_completed()),
            "app_version": self.settings.app_version,
            "auth_enabled": self.settings.auth_enabled,
            "auth_block_file": str(self.settings.auth_block_file),
            "max_login_attempts": self.settings.max_login_attempts,
        }


def count_with_project(todos: list[Todo], project: str) -> int:
    return len([todo for todo in todos if project in todo.projects])


def count_with_context(todos: list[Todo], context: str) -> int:
    return len([todo for todo in todos if context in todo.contexts])


def count_waiting_for(todos: list[Todo], person: str) -> int:
    return len([todo for todo in todos if todo.custom_fields.get("waiting", "").lower() == person.lower()])


def count_with_priority(todos: list[Todo], priority: str) -> int:
    return len([todo for todo in todos if todo.priority == priority])


def format_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d, %Y")
    except Exception:
        return date_str


def format_due_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%a, %b %d, %Y")
    except Exception:
        return date_str


def external_link_href(link_value: str) -> str:
    value = (link_value or "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return value
    if parsed.scheme:
        return ""
    return f"https://{value}"


def is_overdue(date_str: str, now_provider: DateTimeProvider | None = None) -> bool:
    try:
        provider = now_provider or datetime.now
        return date_str < provider().strftime("%Y-%m-%d")
    except Exception:
        return False
