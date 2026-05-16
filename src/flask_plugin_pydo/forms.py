"""Request parsing helpers for the PyDo plugin."""

from __future__ import annotations

from dataclasses import dataclass

from flask import Request


def normalize_priority(value: str | None) -> str | None:
    normalized = (value or "").strip().upper()
    return normalized or None


@dataclass(slots=True)
class AddTodoForm:
    text: str
    priority: str | None

    @classmethod
    def from_request(cls, request: Request) -> "AddTodoForm":
        return cls(
            text=(request.form.get("text") or "").strip(),
            priority=normalize_priority(request.form.get("priority")),
        )


@dataclass(slots=True)
class EditTodoForm:
    old_line: str
    text: str
    priority: str | None

    @classmethod
    def from_request(cls, request: Request) -> "EditTodoForm":
        return cls(
            old_line=(request.form.get("line") or "").strip(),
            text=(request.form.get("text") or "").strip(),
            priority=normalize_priority(request.form.get("priority")),
        )


@dataclass(slots=True)
class LineActionForm:
    line: str

    @classmethod
    def from_request(cls, request: Request) -> "LineActionForm":
        return cls(line=(request.form.get("line") or "").strip())


@dataclass(slots=True)
class LoginForm:
    password: str
    next_url: str

    @classmethod
    def from_request(cls, request: Request) -> "LoginForm":
        next_url = request.form.get("next", "") if request.method == "POST" else request.args.get("next", "")
        return cls(
            password=request.form.get("password", ""),
            next_url=(next_url or "").strip(),
        )
