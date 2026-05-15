"""Blueprint routes for the PyDo plugin."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from flask_plugin_pydo.forms import AddTodoForm, EditTodoForm, LineActionForm, LoginForm
from flask_plugin_pydo.services import (
    PydoService,
    PydoSettings,
    count_waiting_for,
    count_with_context,
    count_with_priority,
    count_with_project,
    external_link_href,
    format_date,
    format_due_date,
    is_duration_context,
    is_overdue,
)

blueprint = Blueprint(
    "pydo",
    __name__,
    url_prefix="/pydo",
    template_folder="templates",
    static_folder="static",
)


def get_service() -> PydoService:
    return PydoService(PydoSettings.from_current_app())


@blueprint.app_context_processor
def inject_plugin_template_context() -> dict[str, object]:
    settings = PydoSettings.from_current_app()
    return {
        "pydo_app_version": settings.app_version,
        "pydo_auth_enabled": settings.auth_enabled,
    }


@blueprint.before_request
def require_login():
    service = get_service()
    if not service.settings.auth_enabled:
        return None

    endpoint = request.endpoint or ""
    allowed_endpoints = {"pydo.login", "pydo.static"}
    if endpoint in allowed_endpoints:
        return None

    if not session.get("pydo_authenticated"):
        return redirect(url_for("pydo.login", next=service.build_safe_next_url(request)))

    return None


@blueprint.route("/login", methods=["GET", "POST"])
def login():
    service = get_service()
    if not service.settings.auth_enabled:
        return redirect(url_for("pydo.index"))

    if session.get("pydo_authenticated"):
        return redirect(url_for("pydo.index"))

    blocked = service.is_login_blocked()
    if not blocked and service.read_attempt_count() >= service.settings.max_login_attempts:
        service.reset_attempt_count()

    form = LoginForm.from_request(request)

    if request.method == "POST":
        if blocked:
            flash(
                "Login blocked after "
                f"{service.settings.max_login_attempts} failed attempts. "
                f"Delete {service.settings.auth_block_file} on the server to unlock.",
                "error",
            )
            return render_template("pydo/login.html", blocked=True, next_url=form.next_url, attempts_left=0)

        if service.verify_login_password(form.password):
            session["pydo_authenticated"] = True
            service.reset_attempt_count()
            if form.next_url and service.is_safe_next_url(form.next_url):
                return redirect(form.next_url)
            return redirect(url_for("pydo.index"))

        attempts = service.record_failed_login()
        if attempts >= service.settings.max_login_attempts:
            flash(
                "Too many failed attempts. Login is blocked. "
                f"Delete {service.settings.auth_block_file} on the server to unlock.",
                "error",
            )
            return render_template("pydo/login.html", blocked=True, next_url=form.next_url, attempts_left=0)

        attempts_left = service.settings.max_login_attempts - attempts
        flash(f"Invalid password. {attempts_left} attempt(s) left.", "error")
        return render_template(
            "pydo/login.html",
            blocked=False,
            next_url=form.next_url,
            attempts_left=attempts_left,
        )

    return render_template(
        "pydo/login.html",
        blocked=blocked,
        next_url=form.next_url,
        attempts_left=service.settings.max_login_attempts,
    )


@blueprint.route("/logout")
def logout():
    session.pop("pydo_authenticated", None)
    return redirect(url_for("pydo.login"))


@blueprint.route("/")
def index():
    service = get_service()
    todos = service.get_todos()
    filter_by = request.args.get("filter", "active")

    if filter_by == "completed":
        items = todos.get_completed()
        sidebar_scope = "completed"
    elif filter_by == "all":
        items = todos.todos
        sidebar_scope = request.args.get("scope", "active")
    else:
        items = service.sort_active_items(todos.get_active())
        sidebar_scope = "active"

    context = service.build_template_context(todos, items, filter_by, sidebar_scope=sidebar_scope)
    return render_template("pydo/index.html", **context)


@blueprint.route("/add", methods=["POST"])
def add_todo():
    form = AddTodoForm.from_request(request)
    if not form.text:
        return redirect(url_for("pydo.index"))

    service = get_service()
    service.get_todos().add(form.text, priority=form.priority)
    return redirect(url_for("pydo.index"))


@blueprint.route("/toggle/<int:index>", methods=["POST"])
def toggle_todo(index: int):
    form = LineActionForm.from_request(request)
    todos = get_service().get_todos()
    if form.line:
        todos.toggle_by_line(form.line)
    else:
        todos.toggle(index)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True})

    return redirect(request.referrer or url_for("pydo.index"))


@blueprint.route("/delete/<int:index>", methods=["POST"])
def delete_todo(index: int):
    form = LineActionForm.from_request(request)
    todos = get_service().get_todos()
    if form.line:
        todos.remove_by_line(form.line)
    else:
        todos.remove(index)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True})

    return redirect(request.referrer or url_for("pydo.index"))


@blueprint.route("/edit/<int:index>", methods=["POST"])
def edit_todo(index: int):
    form = EditTodoForm.from_request(request)
    if not form.text:
        return jsonify({"success": False, "error": "Text cannot be empty"}), 400

    todos = get_service().get_todos()
    updated = False

    if form.old_line:
        updated = todos.update_by_line(form.old_line, form.text, priority=form.priority, update_priority=True)
    elif 0 <= index < len(todos.todos):
        todos.todos[index].text = form.text
        todos.todos[index].priority = form.priority
        todos.save()
        updated = True

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if not updated:
            return jsonify({"success": False, "error": "Task not found"}), 404
        return jsonify({"success": True})

    return redirect(request.referrer or url_for("pydo.index"))


@blueprint.route("/tomorrow/<int:index>", methods=["POST"])
def postpone_due_tomorrow(index: int):
    del index
    form = LineActionForm.from_request(request)
    updated = get_service().get_todos().postpone_due_by_line(form.line, days=1) if form.line else False
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if not updated:
            return jsonify({"success": False, "error": "Task due date not found"}), 404
        return jsonify({"success": True})
    return redirect(request.referrer or url_for("pydo.index"))


@blueprint.route("/today/<int:index>", methods=["POST"])
def set_due_today(index: int):
    del index
    form = LineActionForm.from_request(request)
    service = get_service()
    updated = service.get_todos().set_due_by_line(form.line, service.today()) if form.line else False
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if not updated:
            return jsonify({"success": False, "error": "Task due date not found"}), 404
        return jsonify({"success": True})
    return redirect(request.referrer or url_for("pydo.index"))


@blueprint.route("/project/<project>")
def filter_project(project: str):
    service = get_service()
    todos = service.get_todos()
    sidebar_scope = request.args.get("scope", "active")
    items = [todo for todo in service.get_items_for_scope(todos, sidebar_scope) if project in todo.projects]
    return render_template(
        "pydo/index.html",
        **service.build_template_context(todos, items, "project", project, sidebar_scope=sidebar_scope),
    )


@blueprint.route("/main-project/<main_project>")
def filter_main_project(main_project: str):
    service = get_service()
    todos = service.get_todos()
    sidebar_scope = request.args.get("scope", "active")
    items = [todo for todo in service.get_items_for_scope(todos, sidebar_scope) if main_project in todo.main_projects]
    return render_template(
        "pydo/index.html",
        **service.build_template_context(todos, items, "main_project", main_project, sidebar_scope=sidebar_scope),
    )


@blueprint.route("/main-project/<main_project>/project/<project>")
def filter_main_project_child(main_project: str, project: str):
    service = get_service()
    todos = service.get_todos()
    sidebar_scope = request.args.get("scope", "active")
    items = [
        todo for todo in service.get_items_for_scope(todos, sidebar_scope)
        if main_project in todo.main_projects and project in todo.projects
    ]
    return render_template(
        "pydo/index.html",
        **service.build_template_context(
            todos,
            items,
            "main_project_child",
            {"main_project": main_project, "project": project},
            sidebar_scope=sidebar_scope,
        ),
    )


@blueprint.route("/main-project/<main_project>/no-subproject")
def filter_main_project_no_subproject(main_project: str):
    service = get_service()
    todos = service.get_todos()
    sidebar_scope = request.args.get("scope", "active")
    items = [
        todo for todo in service.get_items_for_scope(todos, sidebar_scope)
        if main_project in todo.main_projects and not todo.projects
    ]
    return render_template(
        "pydo/index.html",
        **service.build_template_context(
            todos,
            items,
            "main_project_no_subproject",
            main_project,
            sidebar_scope=sidebar_scope,
        ),
    )


@blueprint.route("/context/<context>")
def filter_context(context: str):
    service = get_service()
    todos = service.get_todos()
    sidebar_scope = request.args.get("scope", "active")
    items = [todo for todo in service.get_items_for_scope(todos, sidebar_scope) if context in todo.contexts]
    return render_template(
        "pydo/index.html",
        **service.build_template_context(todos, items, "context", context, sidebar_scope=sidebar_scope),
    )


@blueprint.route("/priority/<priority>")
def filter_priority(priority: str):
    service = get_service()
    todos = service.get_todos()
    sidebar_scope = request.args.get("scope", "active")
    normalized_priority = (priority or "").strip().upper()
    if normalized_priority not in {"A", "B", "C"}:
        return redirect(url_for("pydo.index", filter=sidebar_scope))

    items = [todo for todo in service.get_items_for_scope(todos, sidebar_scope) if todo.priority == normalized_priority]
    return render_template(
        "pydo/index.html",
        **service.build_template_context(
            todos,
            items,
            "priority",
            normalized_priority,
            sidebar_scope=sidebar_scope,
        ),
    )


@blueprint.route("/due/<date>")
def filter_due(date: str):
    service = get_service()
    todos = service.get_todos()
    items = [todo for todo in todos.todos if todo.custom_fields.get("due") == date and not todo.complete]
    return render_template(
        "pydo/index.html",
        **service.build_template_context(todos, items, "due", date, sidebar_scope="active"),
    )


@blueprint.route("/waiting")
def filter_waiting():
    service = get_service()
    todos = service.get_todos()
    sidebar_scope = request.args.get("scope", "active")
    items = [
        todo for todo in service.get_items_for_scope(todos, sidebar_scope)
        if "waiting" in todo.contexts or todo.custom_fields.get("waiting")
    ]
    return render_template(
        "pydo/index.html",
        **service.build_template_context(todos, items, "waiting", sidebar_scope=sidebar_scope),
    )


@blueprint.route("/waiting/<person>")
def filter_waiting_for(person: str):
    service = get_service()
    todos = service.get_todos()
    sidebar_scope = request.args.get("scope", "active")
    items = [
        todo for todo in service.get_items_for_scope(todos, sidebar_scope)
        if todo.custom_fields.get("waiting", "").lower() == person.lower()
    ]
    return render_template(
        "pydo/index.html",
        **service.build_template_context(todos, items, "waiting_for", person, sidebar_scope=sidebar_scope),
    )


@blueprint.app_errorhandler(404)
def not_found(error):
    del error
    return render_template("pydo/404.html"), 404


@blueprint.app_errorhandler(500)
def server_error(error):
    del error
    return render_template("pydo/500.html"), 500


blueprint.add_app_template_filter(count_with_project, "count_with_project")
blueprint.add_app_template_filter(count_with_context, "count_with_context")
blueprint.add_app_template_filter(count_waiting_for, "count_waiting_for")
blueprint.add_app_template_filter(count_with_priority, "count_with_priority")
blueprint.add_app_template_filter(is_duration_context, "is_duration_context")
blueprint.add_app_template_filter(format_date, "format_date")
blueprint.add_app_template_filter(format_due_date, "format_due_date")
blueprint.add_app_template_filter(external_link_href, "external_link_href")
blueprint.add_app_template_filter(lambda value: is_overdue(value, now_provider=get_service().settings.now_provider), "is_overdue")
