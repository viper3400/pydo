from flask import Flask

from flask_plugin_pydo.plugin import PLUGIN


def test_plugin_metadata_integrity():
    assert PLUGIN["id"] == "pydo"
    assert PLUGIN["name"] == "PyDo"
    assert isinstance(PLUGIN["version"], str)
    assert PLUGIN["version"]
    assert PLUGIN["menu_entry"]["path"] == "/pydo/"
    assert PLUGIN["blueprint"].name == "pydo"
    assert PLUGIN["blueprint"].url_prefix == "/pydo"


def test_blueprint_registration():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret"
    app.register_blueprint(PLUGIN["blueprint"])

    rules = {rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("pydo.")}
    assert "/pydo/" in rules
    assert "/pydo/add" in rules
    assert "/pydo/login" in rules


def test_app_factory_integration(tmp_path):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="test-secret",
        TESTING=True,
        PYDO_TODO_FILE=str(tmp_path / "todo.txt"),
    )
    app.register_blueprint(PLUGIN["blueprint"])

    client = app.test_client()
    response = client.get("/pydo/")

    assert response.status_code == 200
    assert "Add New Task" in response.get_data(as_text=True)
