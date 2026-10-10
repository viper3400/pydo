from datetime import datetime

from fastapi.testclient import TestClient

from flask_plugin_pydo.routes import create_app


def make_client(tmp_path, **settings):
    values = {
        "PYDO_TODO_FILE": str(tmp_path / "todo.txt"),
        "PYDO_NOW_PROVIDER": lambda: datetime(2026, 4, 22, 9),
        "SECRET_KEY": "test-secret",
    }
    values.update(settings)
    return TestClient(create_app(values))


def test_add_and_line_targeted_edit(tmp_path):
    client = make_client(tmp_path)
    assert (
        client.post(
            "/add",
            data={"text": "Write tests", "priority": "A"},
            follow_redirects=False,
        ).status_code
        == 302
    )
    assert "(A) Write tests" in (tmp_path / "todo.txt").read_text()
    result = client.post(
        "/edit/0",
        data={"line": "(A) Write tests", "text": "Updated", "priority": "B"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert result.json() == {"success": True}
    assert "(B) Updated" in (tmp_path / "todo.txt").read_text()


def test_render_and_static_assets(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/")
    assert response.status_code == 200
    assert "Add New Task" in response.text
    assert client.get("/static/js/app.js").status_code == 200


def test_active_section_order_and_due_priority_placement(tmp_path):
    client = make_client(tmp_path)
    (tmp_path / "todo.txt").write_text(
        "today_task due:2026-04-22\n(A) prio_no_due\n(B) due_with_prio due:2026-04-24\n"
    )
    html = client.get("/").text
    assert html.index("📍 Due Today") < html.index("⚡ Prioritized Tasks")
    assert "due_with_prio" in html
    assert "📅 Due This Week (1)" in html


def test_main_project_and_child_project_filters(tmp_path):
    client = make_client(tmp_path)
    (tmp_path / "todo.txt").write_text(
        "Child task ++Client +Migration\nParent only ++Client\nOther +Personal\n"
    )
    main = client.get("/main-project/Client").text
    child = client.get("/main-project/Client/project/Migration").text
    parent = client.get("/main-project/Client/no-subproject").text
    assert "Child task" in main and "Parent only" in main and "Other" not in main
    assert "Child task" in child and "Parent only" not in child
    assert "Parent only" in parent and "Child task" not in parent


def test_tomorrow_action_and_footer_about_link(tmp_path):
    client = make_client(tmp_path)
    (tmp_path / "todo.txt").write_text("Call vendor due:2026-04-22\n")
    client.post("/tomorrow/0", data={"line": "Call vendor due:2026-04-22"})
    assert "due:2026-04-23" in (tmp_path / "todo.txt").read_text()
    page = client.get("/").text
    assert 'href="/about"' in page


def test_auth_and_secure_next_redirect(tmp_path):
    client = make_client(
        tmp_path,
        PYTODO_PASSWORD="secret",
        PYTODO_SESSION_COOKIE_NAME="custom_session",
    )
    assert client.get("/", follow_redirects=False).headers["location"].startswith("/login?")
    bad = client.post("/login", data={"password": "wrong", "next": "//evil.test"})
    assert bad.status_code == 200
    ok = client.post(
        "/login",
        data={"password": "secret", "next": "//evil.test"},
        follow_redirects=False,
    )
    assert ok.headers["location"] == "/"
    cookie = ok.headers["set-cookie"]
    assert cookie.startswith("custom_session=")
    assert "httponly" in cookie.lower() and "samesite=lax" in cookie.lower()
    assert client.get("/").status_code == 200


def test_login_block_after_configured_failures(tmp_path):
    client = make_client(tmp_path, PYTODO_PASSWORD="secret", PYDO_MAX_LOGIN_ATTEMPTS=2)
    client.post("/login", data={"password": "wrong"})
    client.post("/login", data={"password": "wrong"})
    assert (tmp_path / ".auth_blocked").exists()
    assert "blocked" in client.get("/login").text.lower()


def test_mounted_host_prefix_and_mutation(tmp_path):
    from fastapi import FastAPI

    host = FastAPI()
    host.mount(
        "/pydo",
        create_app({"PYDO_TODO_FILE": str(tmp_path / "todo.txt"), "SECRET_KEY": "secret"}),
    )
    client = TestClient(host)
    response = client.get("/pydo/")
    assert response.status_code == 200
    assert "/pydo/static/css/style.css" in response.text
    client.post("/pydo/add", data={"text": "Mount works"})
    assert "Mount works" in (tmp_path / "todo.txt").read_text()


def test_due_action_repeat_safe(tmp_path):
    client = make_client(tmp_path)
    (tmp_path / "todo.txt").write_text("Call vendor due:2026-04-20\n")
    client.post("/today/0", data={"line": "Call vendor due:2026-04-20"})
    assert "due:2026-04-22" in (tmp_path / "todo.txt").read_text()


def test_invalid_auth_configuration_requires_secret(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app({"PYDO_TODO_FILE": str(tmp_path / "todo.txt"), "PYTODO_PASSWORD": "secret"})
