from datetime import datetime

from flask import Flask
import pytest

from flask_plugin_pydo.plugin import PLUGIN
from flask_plugin_pydo.services import Todo, TodoList, is_duration_context


@pytest.fixture
def app(tmp_path):
    host_app = Flask(__name__)
    host_app.config.update(
        SECRET_KEY="test-secret",
        TESTING=True,
        PYDO_TODO_FILE=str(tmp_path / "todo.txt"),
        PYDO_NOW_PROVIDER=lambda: datetime(2026, 4, 22, 9, 0, 0),
    )
    host_app.register_blueprint(PLUGIN["blueprint"])
    return host_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def todo_file(app):
    return app.config["PYDO_TODO_FILE"]


def read_todo_file(todo_file):
    return open(todo_file, "r", encoding="utf-8").read()


def write_todo_file(todo_file, content: str):
    with open(todo_file, "w", encoding="utf-8") as file_obj:
        file_obj.write(content)


def test_add_route_persists_todo(client, todo_file):
    response = client.post("/pydo/add", data={"text": "Write tests", "priority": "A"})
    assert response.status_code == 302
    assert "(A) Write tests" in read_todo_file(todo_file)


def test_sort_active_items_places_prioritized_no_due_before_due_this_week(app):
    now_provider = app.config["PYDO_NOW_PROVIDER"]
    todos = TodoList(app.config["PYDO_TODO_FILE"], now_provider=now_provider)
    todos.todos = [
        Todo.from_line("t_today due:2026-04-22"),
        Todo.from_line("(B) t_prio"),
        Todo.from_line("(B) t_week_b due:2026-04-25"),
        Todo.from_line("(A) t_week_a due:2026-04-25"),
        Todo.from_line("t_week_soon due:2026-04-23"),
        Todo.from_line("(A) t_later_a due:2026-05-02"),
    ]
    sorted_items = sorted(
        [todo for todo in todos.todos if todo is not None],
        key=lambda item: (0, item.to_line()),
    )
    del sorted_items

    from flask_plugin_pydo.routes import get_service

    with app.app_context():
        service = get_service()
        sorted_active = service.sort_active_items([todo for todo in todos.todos if todo is not None])

    assert [todo.get_edit_text().split()[0] for todo in sorted_active] == [
        "t_today",
        "t_prio",
        "t_week_soon",
        "t_week_a",
        "t_week_b",
        "t_later_a",
    ]


def test_active_view_sections_show_prioritized_before_due_this_week(client, todo_file):
    write_todo_file(
        todo_file,
        "\n".join(
            [
                "today_task due:2026-04-22",
                "(A) prio_no_due",
                "(B) due_with_prio due:2026-04-24",
                "due_no_prio due:2026-04-23",
            ]
        ) + "\n",
    )

    response = client.get("/pydo/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert html.find("📍 Due Today") < html.find("⚡ Prioritized Tasks") < html.find("📅 Due This Week")
    assert "⚡ Prioritized Tasks (1)" in html
    assert "📅 Due This Week (2)" in html


def test_duration_contexts_are_split_from_main_context_panel(client, todo_file):
    write_todo_file(todo_file, "Call customer @phone @30min\nReview contract @120 min\n")

    response = client.get("/pydo/")
    html = response.get_data(as_text=True)

    contexts_panel = html[html.find("🏷️ Contexts"):html.find("⏱️ Duration Context")]
    duration_panel = html[html.find("⏱️ Duration Context"):html.find("⚡ Priorities")]

    assert "@phone" in contexts_panel
    assert "@30min" not in contexts_panel
    assert "@120" not in contexts_panel
    assert "@30min" in duration_panel
    assert "@120" in duration_panel
    assert "duration-context-tag" in html


def test_project_sidebar_groups_main_projects(client, todo_file):
    write_todo_file(
        todo_file,
        "\n".join(
            [
                "Plan migration ++ClientA +Migration",
                "Handle support ++ClientA +Support",
                "Review roadmap ++ClientA",
                "Buy milk +Personal",
            ]
        ) + "\n",
    )

    response = client.get("/pydo/")
    html = response.get_data(as_text=True)

    assert "++ClientA" in html
    assert "/pydo/main-project/ClientA" in html
    assert "/pydo/main-project/ClientA/project/Migration" in html
    assert "/pydo/main-project/ClientA/project/Support" in html
    assert "/pydo/main-project/ClientA/no-subproject" in html
    assert "No subproject" in html
    assert "+Personal" in html


def test_main_project_filters_include_expected_tasks(client, todo_file):
    write_todo_file(
        todo_file,
        "\n".join(
            [
                "Plan migration ++ClientA +Migration",
                "Handle support ++ClientA +Support",
                "Review roadmap ++ClientA",
                "Buy milk +Personal",
            ]
        ) + "\n",
    )

    main_html = client.get("/pydo/main-project/ClientA").get_data(as_text=True)
    child_html = client.get("/pydo/main-project/ClientA/project/Migration").get_data(as_text=True)
    no_child_html = client.get("/pydo/main-project/ClientA/no-subproject").get_data(as_text=True)

    assert "Plan migration" in main_html
    assert "Handle support" in main_html
    assert "Review roadmap" in main_html
    assert "Buy milk" not in main_html

    assert "Plan migration" in child_html
    assert "Handle support" not in child_html
    assert "Review roadmap" not in child_html

    assert "Review roadmap" in no_child_html
    assert "Plan migration" not in no_child_html
    assert "Handle support" not in no_child_html


def test_edit_route_ajax_updates_task_without_redirect(client, todo_file):
    write_todo_file(todo_file, "(B) Original task\n")

    response = client.post(
        "/pydo/edit/0",
        data={"line": "(B) Original task", "text": "Updated task", "priority": "A"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert "(A) Updated task" in read_todo_file(todo_file)


def test_edit_route_ajax_returns_404_when_task_not_found(client, todo_file):
    write_todo_file(todo_file, "(B) Existing task\n")

    response = client.post(
        "/pydo/edit/0",
        data={"line": "(B) Missing task", "text": "Updated task", "priority": "A"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False
    assert "not found" in payload["error"].lower()


def test_tomorrow_route_postpones_due_date(client, todo_file):
    write_todo_file(todo_file, "Call vendor due:2026-04-22\n")

    response = client.post("/pydo/tomorrow/0", data={"line": "Call vendor due:2026-04-22"})

    assert response.status_code == 302
    assert "due:2026-04-23" in read_todo_file(todo_file)


def test_today_route_sets_due_date_to_today(client, todo_file):
    write_todo_file(todo_file, "Call vendor due:2026-04-20\n")

    response = client.post("/pydo/today/0", data={"line": "Call vendor due:2026-04-20"})

    assert response.status_code == 302
    assert "due:2026-04-22" in read_todo_file(todo_file)


def test_login_gate_redirects_when_enabled(tmp_path):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="test-secret",
        TESTING=True,
        PYDO_TODO_FILE=str(tmp_path / "todo.txt"),
        PYTODO_PASSWORD="secret",
    )
    app.register_blueprint(PLUGIN["blueprint"])
    client = app.test_client()

    response = client.get("/pydo/")

    assert response.status_code == 302
    assert "/pydo/login" in response.headers["Location"]


def test_login_redirect_preserves_forwarded_prefix(tmp_path):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="test-secret",
        TESTING=True,
        PYDO_TODO_FILE=str(tmp_path / "todo.txt"),
        PYTODO_PASSWORD="secret",
    )
    app.register_blueprint(PLUGIN["blueprint"])
    client = app.test_client()

    response = client.get("/pydo/", headers={"X-Forwarded-Prefix": "/host"})
    assert response.status_code == 302
    assert "/pydo/login" in response.headers["Location"]


def test_duration_context_detection():
    assert is_duration_context("5min")
    assert is_duration_context("30min")
    assert is_duration_context("120")
    assert not is_duration_context("phone")
    assert not is_duration_context("bug30")
