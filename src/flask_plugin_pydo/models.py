"""Typed data models for the PyDo plugin."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

HIDDEN_DISPLAY_CUSTOM_FIELDS = {"due", "waiting", "link"}


@dataclass(slots=True)
class Todo:
    """Represents a single todo.txt task."""

    text: str
    complete: bool = False
    priority: str | None = None
    creation_date: str | None = None
    completion_date: str | None = None
    main_projects: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    contexts: list[str] = field(default_factory=list)
    custom_fields: dict[str, str] = field(default_factory=dict)
    links: list[str] = field(default_factory=list)

    def _strip_leading_core_metadata(self, text: str) -> str:
        tokens = text.split()
        idx = 0
        consumed_completion = False
        consumed_priority = False
        consumed_creation_date = False

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
    def from_line(cls, line: str) -> Todo | None:
        if not line.strip():
            return None

        original_text = line
        todo = cls(text=original_text)

        if line.startswith("x "):
            todo.complete = True
            line = line[2:].strip()
            match = re.match(r"(\d{4}-\d{2}-\d{2})\s+", line)
            if match:
                todo.completion_date = match.group(1)
                line = line[len(match.group(1)):].strip()

        priority_match = re.match(r"^\(([A-Z])\)\s+", line)
        if priority_match:
            todo.priority = priority_match.group(1)
            line = line[len(priority_match.group(0)):].strip()

        date_match = re.match(r"^(\d{4}-\d{2}-\d{2})\s+", line)
        if date_match:
            todo.creation_date = date_match.group(1)
            line = line[len(date_match.group(0)):].strip()

        todo.main_projects = re.findall(r"(?<!\S)\+\+(\S+)", line)
        todo.projects = re.findall(r"(?<!\S)\+(?!\+)(\S+)", line)
        contexts = re.findall(r"(?<!\S)@(\S+)", line)
        todo.contexts = [context for context in contexts if not context.lower().startswith("due:")]

        custom_fields = re.findall(r"(?<!\S)(\w+):(\S+)", line)
        todo.custom_fields = {key: value for key, value in custom_fields}
        todo.links = [value for key, value in custom_fields if key.lower() == "link"]

        text_parts: list[str] = []
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
        parts: list[str] = []
        if self.complete:
            parts.append("x")
            if self.completion_date:
                parts.append(self.completion_date)
        if self.priority:
            parts.append(f"({self.priority})")
        if self.creation_date:
            parts.append(self.creation_date)
        parts.append(self._strip_leading_core_metadata(self.text))
        return " ".join(filter(None, parts))

    def get_edit_text(self) -> str:
        return self._strip_leading_core_metadata(self.text).strip()

    def get_display_text(self) -> str:
        text = self.get_edit_text()
        metadata_tokens = {f"++{project}" for project in self.main_projects}
        metadata_tokens.update(f"+{project}" for project in self.projects)
        metadata_tokens.update(f"@{context}" for context in self.contexts)
        metadata_tokens.update(
            f"{key}:{value}" if value else f"{key}:"
            for key, value in self.custom_fields.items()
            if key.lower() in HIDDEN_DISPLAY_CUSTOM_FIELDS
        )
        metadata_tokens.update(f"link:{link}" for link in self.links if link)
        filtered_tokens = [token for token in text.split() if token not in metadata_tokens]
        return " ".join(filtered_tokens)


@dataclass(slots=True)
class ProjectSummary:
    """Child project summary for sidebar rendering."""

    name: str
    count: int


@dataclass(slots=True)
class ProjectGroup:
    """Main project sidebar summary."""

    name: str
    count: int = 0
    projects: dict[str, int] = field(default_factory=dict)
    no_subproject_count: int = 0

    def to_template_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "count": self.count,
            "projects": [
                {"name": project, "count": count}
                for project, count in sorted(self.projects.items())
            ],
            "no_subproject_count": self.no_subproject_count,
        }
