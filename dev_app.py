from flask import Flask
from flask_plugin_pydo.plugin import PLUGIN

app = Flask(__name__)
app.config.update(
    SECRET_KEY="dev-secret",
    PYDO_TODO_FILE="data/todo.txt",
)
app.register_blueprint(PLUGIN["blueprint"])