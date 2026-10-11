import importlib.util

import pytest


@pytest.mark.skipif(
    importlib.util.find_spec("tool_host") is None,
    reason="FeedVanta host contract is not installed",
)
def test_plugin_export_uses_feedvanta_contract():
    from tool_host.plugins import Plugin

    from flask_plugin_pydo.plugin import PLUGIN

    assert isinstance(PLUGIN, Plugin)
    assert (PLUGIN.id, PLUGIN.name, PLUGIN.path) == ("pydo", "PyDo", "/pydo")
    assert PLUGIN.app_factory().state.pydo_settings.todo_file


@pytest.mark.skipif(
    importlib.util.find_spec("tool_host") is None,
    reason="FeedVanta host contract is not installed",
)
def test_feedvanta_discovers_and_mounts_plugin(tmp_path):
    from fastapi.testclient import TestClient
    from tool_host.app import create_app
    from tool_host.plugins import Plugin

    from flask_plugin_pydo.plugin import PLUGIN

    plugin = Plugin(
        PLUGIN.id,
        PLUGIN.name,
        PLUGIN.description,
        PLUGIN.version,
        PLUGIN.path,
        lambda: PLUGIN.app_factory(
            {"PYDO_TODO_FILE": str(tmp_path / "todo.txt"), "SECRET_KEY": "host-test"}
        ),
    )
    client = TestClient(create_app([plugin]))
    page = client.get("/pydo/")
    assert page.status_code == 200
    assert "/pydo/static/css/style.css" in page.text
    assert 'href="/about"' in page.text
    assert client.get("/pydo/static/js/app.js").status_code == 200
    proxied = client.get("/pydo/", headers={"X-Forwarded-Prefix": "/suburl"})
    assert proxied.status_code == 200
    assert "/suburl/pydo/static/css/style.css" in proxied.text
    assert 'href="/suburl/about"' in proxied.text


@pytest.mark.skipif(
    importlib.util.find_spec("tool_host") is None,
    reason="FeedVanta host contract is not installed",
)
def test_auth_login_works_with_host_forwarded_prefix(tmp_path):
    from fastapi.testclient import TestClient
    from tool_host.app import create_app
    from tool_host.plugins import Plugin

    from flask_plugin_pydo.plugin import PLUGIN

    plugin = Plugin(
        PLUGIN.id,
        PLUGIN.name,
        PLUGIN.description,
        PLUGIN.version,
        PLUGIN.path,
        lambda: PLUGIN.app_factory(
            {
                "PYDO_TODO_FILE": str(tmp_path / "todo.txt"),
                "SECRET_KEY": "host-test",
                "PYTODO_PASSWORD": "correct-password",
            }
        ),
    )
    client = TestClient(create_app([plugin]))

    login_page = client.get(
        "/pydo/login", headers={"X-Forwarded-Prefix": "/pyhost"}, follow_redirects=False
    )
    assert login_page.status_code == 200

    response = client.post(
        "/pydo/login",
        headers={"X-Forwarded-Prefix": "/pyhost"},
        data={"password": "correct-password", "next": "/pyhost/pydo/"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/pyhost/pydo/"
