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
