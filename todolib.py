"""
Todo.txt file format parser and manager.
Follows the standard todo.txt specification: https://github.com/todotxt/todo.txt
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

HIDDEN_DISPLAY_CUSTOM_FIELDS = {"due", "waiting", "link"}


def is_duration_context(context: str) -> bool:
    """Return whether a context tag represents a duration estimate."""
    normalized = context.strip().lower()
    return bool(re.fullmatch(r"\d+\s*min", normalized) or re.fullmatch(r"\d+", normalized))


@dataclass
class Todo:
    """Represents a single todo item."""

    text: str
    complete: bool = False
    priority: Optional[str] = None
    creation_date: Optional[str] = None
    completion_date: Optional[str] = None
    projects: List[str] = field(default_factory=list)
    contexts: List[str] = field(default_factory=list)
    custom_fields: dict = field(default_factory=dict)
    links: List[str] = field(default_factory=list)

    def _strip_leading_core_metadata(self, text: str) -> str:
        """Strip only leading todo core metadata tokens from a line."""
        tokens = text.split()
        idx = 0
        consumed_completion = False
        consumed_priority = False
        consumed_creation_date = False

        # Strip only known leading metadata tokens, tolerating legacy reordered
        # prefixes like "(A) x YYYY-MM-DD ..." for completed tasks.
        while idx < len(tokens):
            token = tokens[idx]

            if self.complete and not consumed_completion and token == "x":
                consumed_completion = True
                idx += 1
                if self.completion_date and idx < len(tokens) and tokens[idx] == self.completion_date:
                    idx += 1
                continue

            if self.priority and not consumed_priority and token == f"({self.priority})":
                consumed_priority = True
                idx += 1
                continue

            if self.creation_date and not consumed_creation_date and token == self.creation_date:
                consumed_creation_date = True
                idx += 1
                continue

            break

        return " ".join(tokens[idx:])

    @classmethod
    def from_line(cls, line: str) -> "Todo":
        """Parse a single todo.txt line into a Todo object."""
        if not line.strip():
            return None

        original_text = line
        todo = cls(text=original_text)

        # Check if complete (starts with 'x ')
        if line.startswith("x "):
            todo.complete = True
            line = line[2:].strip()

            # Extract completion date if present (YYYY-MM-DD format)
            match = re.match(r"(\d{4}-\d{2}-\d{2})\s+", line)
            if match:
                todo.completion_date = match.group(1)
                line = line[len(match.group(1)):].strip()

        # Extract priority (A-Z) at the start if present
        priority_match = re.match(r"^\(([A-Z])\)\s+", line)
        if priority_match:
            todo.priority = priority_match.group(1)
            line = line[len(priority_match.group(0)):].strip()

        # Extract creation date if present (YYYY-MM-DD format)
        date_match = re.match(r"^(\d{4}-\d{2}-\d{2})\s+", line)
        if date_match:
            todo.creation_date = date_match.group(1)
            line = line[len(date_match.group(0)):].strip()

        # Extract token-level projects (+ProjectName)
        projects = re.findall(r"(?<!\S)\+(\S+)", line)
        todo.projects = projects

        # Extract token-level contexts (@context), but skip due markers like @due:YYYY-MM-DD
        contexts = re.findall(r"(?<!\S)@(\S+)", line)
        todo.contexts = [context for context in contexts if not context.lower().startswith("due:")]

        # Extract token-level custom fields (key:value)
        custom_fields = re.findall(r"(?<!\S)(\w+):(\S+)", line)
        todo.custom_fields = {k: v for k, v in custom_fields}
        todo.links = [value for key, value in custom_fields if key.lower() == "link"]

        # Store parsed text in canonical core-metadata order.
        text_parts = []
        if todo.complete:
            text_parts.append("x")
            if todo.completion_date:
                text_parts.append(todo.completion_date)
        if todo.priority:
            text_parts.append(f"({todo.priority})")
        if todo.creation_date:
            text_parts.append(todo.creation_date)
        text_parts.append(line)
        todo.text = " ".join(part for part in text_parts if part)

        return todo

    def to_line(self) -> str:
        """Convert Todo object back to todo.txt format line."""
        parts = []

        if self.complete:
            parts.append("x")
            if self.completion_date:
                parts.append(self.completion_date)

        if self.priority:
            parts.append(f"({self.priority})")

        if self.creation_date:
            parts.append(self.creation_date)

        # Reconstruct the task text without removing date fragments inside fields like due:YYYY-MM-DD.
        task_text = self._strip_leading_core_metadata(self.text)

        parts.append(task_text)
        return " ".join(filter(None, parts))

    def get_display_text(self) -> str:
        """Get simplified text for display (stripped of metadata)."""
        text = self.get_edit_text()

        # Hide todo.txt-style metadata in display mode using exact token matches
        # from parsed metadata, so plain words in the task text are not removed.
        metadata_tokens = {f"+{project}" for project in self.projects}
        metadata_tokens.update(f"@{context}" for context in self.contexts)
        metadata_tokens.update(
            f"{key}:{value}" if value else f"{key}:"
            for key, value in self.custom_fields.items()
            if key.lower() in HIDDEN_DISPLAY_CUSTOM_FIELDS
        )
        metadata_tokens.update(f"link:{link}" for link in self.links if link)

        filtered_tokens = [token for token in text.split() if token not in metadata_tokens]
        return " ".join(filtered_tokens)

    def get_edit_text(self) -> str:
        """Get editable task text (stripped of core metadata, keeps task markers)."""
        return self._strip_leading_core_metadata(self.text).strip()


class TodoList:
    """Manager for a todo.txt file."""

    def __init__(self, filepath: Path):
        self.filepath = Path(filepath)
        self.todos: List[Todo] = []
        self.load()

    def load(self) -> None:
        """Load todos from the file."""
        self.todos = []
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.filepath.touch()
            return

        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if line.strip():
                    todo = Todo.from_line(line)
                    if todo:
                        self.todos.append(todo)

    def save(self) -> None:
        """Save todos to the file."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            for todo in self.todos:
                f.write(todo.to_line() + "\n")

    def add(self, text: str, priority: Optional[str] = None) -> Todo:
        """Add a new todo."""
        todo = Todo(text=text, priority=priority)
        self.todos.append(todo)
        self.save()
        return todo

    def toggle(self, index: int) -> None:
        """Toggle a todo's completion status."""
        if 0 <= index < len(self.todos):
            todo = self.todos[index]
            todo.complete = not todo.complete
            if todo.complete:
                todo.completion_date = datetime.now().strftime("%Y-%m-%d")
            else:
                # Remove completion prefix so reopened tasks are serialized as active.
                todo.text = re.sub(r"^x(?:\s+\d{4}-\d{2}-\d{2})?\s+", "", todo.text).strip()
                todo.completion_date = None
            self.save()

    def toggle_by_line(self, line: str) -> None:
        """Toggle a todo by its original line content."""
        for i, todo in enumerate(self.todos):
            if todo.to_line() == line:
                self.toggle(i)
                return

    def remove(self, index: int) -> None:
        """Remove a todo."""
        if 0 <= index < len(self.todos):
            self.todos.pop(index)
            self.save()

    def remove_by_line(self, line: str) -> None:
        """Remove a todo by its original line content."""
        for i, todo in enumerate(self.todos):
            if todo.to_line() == line:
                self.remove(i)
                return

    def update_by_line(
        self,
        old_line: str,
        new_text: str,
        priority: Optional[str] = None,
        update_priority: bool = False,
    ) -> bool:
        """Update a todo by its original line content."""
        for i, todo in enumerate(self.todos):
            if todo.to_line() == old_line:
                # Keep task text clean if user typed a leading (A)/(B)/(C) while using the priority selector.
                todo.text = re.sub(r"^\([A-Z]\)\s+", "", new_text).strip()
                if update_priority:
                    todo.priority = priority
                self.save()
                return True
        return False

    def postpone_due_by_line(self, line: str, days: int = 1) -> bool:
        """Move an existing due date forward by N days for a specific task line."""
        for todo in self.todos:
            if todo.to_line() == line:
                due_value = todo.custom_fields.get("due")
                if not due_value:
                    return False
                try:
                    next_due = (datetime.strptime(due_value, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")
                except ValueError:
                    return False

                old_token = f"due:{due_value}"
                new_token = f"due:{next_due}"
                tokens = todo.text.split()
                replaced = False
                for i, token in enumerate(tokens):
                    if token == old_token:
                        tokens[i] = new_token
                        replaced = True
                        break

                if not replaced:
                    return False

                todo.text = " ".join(tokens)
                todo.custom_fields["due"] = next_due
                self.save()
                return True
        return False

    def set_due_by_line(self, line: str, due_date: str) -> bool:
        """Set an existing due date to a specific YYYY-MM-DD value for a task line."""
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            return False

        for todo in self.todos:
            if todo.to_line() == line:
                due_value = todo.custom_fields.get("due")
                if not due_value:
                    return False

                old_token = f"due:{due_value}"
                new_token = f"due:{due_date}"
                tokens = todo.text.split()
                replaced = False
                for i, token in enumerate(tokens):
                    if token == old_token:
                        tokens[i] = new_token
                        replaced = True
                        break

                if not replaced:
                    return False

                todo.text = " ".join(tokens)
                todo.custom_fields["due"] = due_date
                self.save()
                return True
        return False

    def get_by_project(self, project: str) -> List[Todo]:
        """Filter todos by project."""
        return [t for t in self.todos if project in t.projects]

    def get_by_context(self, context: str) -> List[Todo]:
        """Filter todos by context."""
        return [t for t in self.todos if context in t.contexts]

    def get_active(self) -> List[Todo]:
        """Get all incomplete todos."""
        return [t for t in self.todos if not t.complete]

    def get_completed(self) -> List[Todo]:
        """Get all completed todos."""
        return [t for t in self.todos if t.complete]

    def get_priorities(self) -> List[str]:
        """Get all unique priorities."""
        return sorted(set(t.priority for t in self.todos if t.priority))

    def get_projects(self) -> List[str]:
        """Get all unique projects."""
        projects = set()
        for t in self.todos:
            projects.update(t.projects)
        return sorted(projects)

    def get_contexts(self) -> List[str]:
        """Get all unique contexts."""
        contexts = set()
        for t in self.todos:
            contexts.update(t.contexts)
        return sorted(contexts)

    def get_due_dates(self) -> dict:
        """Get all todos grouped by due date. Returns dict with date as key."""
        from datetime import datetime
        dues = {}
        for t in self.todos:
            if t.custom_fields.get('due'):
                due_date = t.custom_fields['due']
                if due_date not in dues:
                    dues[due_date] = []
                dues[due_date].append(t)
        return dict(sorted(dues.items()))

    def get_overdue(self) -> List[Todo]:
        """Get todos that are overdue (past due date and not complete)."""
        from datetime import datetime
        overdue = []
        today = datetime.now().strftime("%Y-%m-%d")
        for t in self.todos:
            if not t.complete and t.custom_fields.get('due'):
                if t.custom_fields['due'] < today:
                    overdue.append(t)
        return overdue

    def get_due_soon(self, days=7) -> List[Todo]:
        """Get todos due within N days."""
        from datetime import datetime, timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        due_soon = []
        for t in self.todos:
            if not t.complete and t.custom_fields.get('due'):
                due_date = t.custom_fields['due']
                if today <= due_date <= (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d"):
                    due_soon.append(t)
        return sorted(due_soon, key=lambda x: x.custom_fields['due'])

    def get_waiting(self) -> List[Todo]:
        """Get all tasks marked as waiting (has @waiting context or waiting: field)."""
        waiting = []
        for t in self.todos:
            if not t.complete and ('waiting' in t.contexts or t.custom_fields.get('waiting')):
                waiting.append(t)
        return waiting

    def get_waiting_for_person(self, person: str) -> List[Todo]:
        """Get tasks waiting for a specific person."""
        waiting = []
        for t in self.todos:
            if not t.complete and t.custom_fields.get('waiting', '').lower() == person.lower():
                waiting.append(t)
        return waiting

    def get_people_waiting_for(self) -> List[str]:
        """Get all unique people we're waiting for."""
        people = set()
        for t in self.todos:
            if t.custom_fields.get('waiting'):
                people.add(t.custom_fields['waiting'])
        return sorted(people)
