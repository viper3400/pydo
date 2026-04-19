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

    todos.remove(0)
    assert len(todos.todos) == 0
