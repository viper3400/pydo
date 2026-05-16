from datetime import datetime

from flask_plugin_pydo.services import TodoList, is_duration_context


def test_duration_context_detection():
    assert is_duration_context("5min")
    assert is_duration_context("30min")
    assert is_duration_context("120")
    assert not is_duration_context("phone")
    assert not is_duration_context("bug30")


def test_todolist_add_toggle_remove(tmp_path):
    todo_file = tmp_path / "todo.txt"
    todos = TodoList(todo_file, now_provider=lambda: datetime(2026, 4, 22, 9, 0, 0))

    todos.add("Buy milk", priority="B")
    assert len(todos.todos) == 1
    assert todos.todos[0].priority == "B"

    todos.toggle(0)
    assert todos.todos[0].complete is True
    assert todos.todos[0].completion_date == "2026-04-22"

    todos.toggle(0)
    assert todos.todos[0].complete is False
    assert todos.todos[0].completion_date is None
    assert not todos.todos[0].to_line().startswith("x ")

    reloaded = TodoList(todo_file)
    assert len(reloaded.get_active()) == 1
    assert len(reloaded.get_completed()) == 0

    todos.remove(0)
    assert len(todos.todos) == 0


def test_completed_with_priority_repeated_load_save_is_stable(tmp_path):
    todo_file = tmp_path / "todo.txt"
    original = "x 2026-04-22 (A) Send summary @PeopleMgmt due:2026-04-24"
    todo_file.write_text(original + "\n", encoding="utf-8")

    todos = TodoList(todo_file)
    todos.save()

    first_save = todo_file.read_text(encoding="utf-8").strip()
    assert first_save == original

    reloaded = TodoList(todo_file)
    reloaded.save()

    second_save = todo_file.read_text(encoding="utf-8").strip()
    assert second_save == original


def test_postpone_due_by_line_moves_due_date_forward(tmp_path):
    todo_file = tmp_path / "todo.txt"
    todo_file.write_text("Task due:2026-04-22 +Proj\n", encoding="utf-8")
    todos = TodoList(todo_file)

    updated = todos.postpone_due_by_line("Task due:2026-04-22 +Proj", days=1)

    assert updated is True
    stored = todo_file.read_text(encoding="utf-8")
    assert "due:2026-04-23" in stored
    assert "due:2026-04-22" not in stored


def test_set_due_by_line_replaces_due_date(tmp_path):
    todo_file = tmp_path / "todo.txt"
    todo_file.write_text("Task due:2026-04-20 +Proj\n", encoding="utf-8")
    todos = TodoList(todo_file)

    updated = todos.set_due_by_line("Task due:2026-04-20 +Proj", due_date="2026-04-22")

    assert updated is True
    stored = todo_file.read_text(encoding="utf-8")
    assert "due:2026-04-22" in stored
    assert "due:2026-04-20" not in stored
