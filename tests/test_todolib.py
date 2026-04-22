from todolib import Todo, TodoList


def test_parse_priority_project_context_custom_fields():
    todo = Todo.from_line("(A) Call Bob +Work @phone due:2026-04-20 waiting:alice")

    assert todo is not None
    assert todo.priority == "A"
    assert "Work" in todo.projects
    assert "phone" in todo.contexts
    assert todo.custom_fields.get("due") == "2026-04-20"
    assert todo.custom_fields.get("waiting") == "alice"


def test_todolist_add_toggle_remove(tmp_path):
    todo_file = tmp_path / "todo.txt"
    todos = TodoList(todo_file)

    todos.add("Buy milk", priority="B")
    assert len(todos.todos) == 1
    assert todos.todos[0].priority == "B"

    todos.toggle(0)
    assert todos.todos[0].complete is True
    assert todos.todos[0].completion_date is not None

    todos.toggle(0)
    assert todos.todos[0].complete is False
    assert todos.todos[0].completion_date is None
    assert not todos.todos[0].to_line().startswith("x ")

    # Reload from disk to ensure reopened task persists as active.
    reloaded = TodoList(todo_file)
    assert len(reloaded.get_active()) == 1
    assert len(reloaded.get_completed()) == 0

    todos.remove(0)
    assert len(todos.todos) == 0


def test_display_text_filters_only_known_custom_fields():
    todo = Todo.from_line("Review docs due:2026-04-21 waiting:alex link:https://example.com ref:ABC-123 +Proj @desk")

    assert todo is not None
    display = todo.get_display_text()

    assert "due:2026-04-21" not in display
    assert "waiting:alex" not in display
    assert "link:https://example.com" not in display
    assert "ref:ABC-123" in display
    assert "+Proj" not in display
    assert "@desk" not in display


def test_parse_multiple_links_and_hide_them_in_display_text():
    todo = Todo.from_line(
        "Read docs link:https://example.com link:docs.python.org due:2026-04-21"
    )

    assert todo is not None
    assert todo.links == ["https://example.com", "docs.python.org"]
    assert "link" in todo.custom_fields
    assert todo.custom_fields["link"] == "docs.python.org"

    display = todo.get_display_text()
    assert "link:https://example.com" not in display
    assert "link:docs.python.org" not in display


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
