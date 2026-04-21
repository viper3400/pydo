import app as app_module
from datetime import datetime, timedelta

from todolib import Todo


def test_add_route_persists_todo(client, test_paths):
    _, todo_file = test_paths

    response = client.post("/add", data={"text": "Write tests", "priority": "A"})

    assert response.status_code == 302
    content = todo_file.read_text(encoding="utf-8")
    assert "(A) Write tests" in content


def test_login_gate_redirects_when_enabled(client, monkeypatch):
    monkeypatch.setattr(app_module, "AUTH_ENABLED", True)

    response = client.get("/")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_redirect_preserves_forwarded_prefix(client, monkeypatch):
    monkeypatch.setattr(app_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(app_module, "_verify_login_password", lambda _: True)

    response = client.get("/", headers={"X-Forwarded-Prefix": "/pydo"})
    assert response.status_code == 302
    assert "/pydo/login" in response.headers["Location"]
    assert "next=/pydo/" in response.headers["Location"]

    login_response = client.post(
        "/login",
        data={"password": "ok", "next": "/pydo/"},
        headers={"X-Forwarded-Prefix": "/pydo"},
    )
    assert login_response.status_code == 302
    assert login_response.headers["Location"].endswith("/pydo/")


def test_login_sets_non_generic_session_cookie_name(client, monkeypatch):
    monkeypatch.setattr(app_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(app_module, "_verify_login_password", lambda _: True)

    response = client.post("/login", data={"password": "ok", "next": "/"})

    assert response.status_code == 302
    cookie_name = app_module.app.config["SESSION_COOKIE_NAME"]
    assert cookie_name == "pytodo_session"
    set_cookie_headers = response.headers.getlist("Set-Cookie")
    assert any(header.startswith(f"{cookie_name}=") for header in set_cookie_headers)


def test_sort_active_items_places_prioritized_no_due_before_due_this_week():
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    in_three_days = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    in_ten_days = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")

    items = [
        Todo.from_line(f"t_today due:{today}"),
        Todo.from_line("(B) t_prio"),
        Todo.from_line(f"(B) t_week_b due:{in_three_days}"),
        Todo.from_line(f"(A) t_week_a due:{in_three_days}"),
        Todo.from_line(f"t_week_soon due:{tomorrow}"),
        Todo.from_line(f"(A) t_later_a due:{in_ten_days}"),
    ]

    sorted_items = app_module.sort_active_items(items)
    sorted_names = [todo.get_edit_text().split()[0] for todo in sorted_items]

    assert sorted_names == [
        "t_today",
        "t_prio",
        "t_week_soon",
        "t_week_a",
        "t_week_b",
        "t_later_a",
    ]


def test_active_view_sections_show_prioritized_before_due_this_week(client, test_paths):
    _, todo_file = test_paths
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    in_two_days = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

    todo_file.write_text(
        "\n".join(
            [
                f"today_task due:{today}",
                "(A) prio_no_due",
                f"(B) due_with_prio due:{in_two_days}",
                f"due_no_prio due:{tomorrow}",
            ]
        ) + "\n",
        encoding="utf-8",
    )

    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    idx_due_today = html.find("📍 Due Today")
    idx_priority = html.find("⚡ Prioritized Tasks")
    idx_due_soon = html.find("📅 Due This Week")

    assert idx_due_today != -1
    assert idx_priority != -1
    assert idx_due_soon != -1
    assert idx_due_today < idx_priority < idx_due_soon

    assert "⚡ Prioritized Tasks (1)" in html
    assert "📅 Due This Week (2)" in html
