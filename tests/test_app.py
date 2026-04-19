import app as app_module


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
