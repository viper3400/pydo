"""FastAPI application factory and PyDo HTTP routes."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, urlencode, urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from flask_plugin_pydo.forms import normalize_priority
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

PACKAGE = Path(__file__).parent


def create_app(settings: PydoSettings | dict | None = None) -> FastAPI:
    configured = settings if isinstance(settings, PydoSettings) else PydoSettings.from_env(settings)
    if configured.auth_enabled and not configured.secret_key:
        raise ValueError("SECRET_KEY is required when PyDo authentication is enabled")
    app = FastAPI(title="PyDo")
    app.state.pydo_settings = configured
    template_engine = Jinja2Templates(directory=str(PACKAGE / "templates"))
    template_engine.env.filters.update(
        {
            "count_with_project": count_with_project,
            "count_with_context": count_with_context,
            "count_waiting_for": count_waiting_for,
            "count_with_priority": count_with_priority,
            "is_duration_context": is_duration_context,
            "format_date": format_date,
            "format_due_date": format_due_date,
            "external_link_href": external_link_href,
            "is_overdue": lambda value: is_overdue(value, configured.now_provider),
        }
    )
    app.mount("/static", StaticFiles(directory=str(PACKAGE / "static")), name="pydo.static")

    def service() -> PydoService:
        return PydoService(configured)

    def local_url(request: Request, path: str) -> str:
        return request.scope.get("root_path", "").rstrip("/") + path

    def safe_referrer(request: Request) -> str:
        fallback = local_url(request, "/")
        value = request.headers.get("referer", "")
        parsed = urlparse(value)
        if parsed.scheme or parsed.netloc:
            if parsed.netloc != request.url.netloc or parsed.scheme not in {
                "http",
                "https",
            }:
                return fallback
            value = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        prefix = request.scope.get("root_path", "").rstrip("/")
        if (
            value.startswith("/")
            and not value.startswith("//")
            and (not prefix or value == prefix or value.startswith(prefix + "/"))
        ):
            return value
        return fallback

    def about_url(request: Request) -> str:
        root_path = request.scope.get("root_path", "").rstrip("/")
        proxy_prefix = root_path[: -len("/pydo")] if root_path.endswith("/pydo") else root_path
        return proxy_prefix + "/about"

    def render(request: Request, page: str, **context):
        flashes = request.session.pop("_flashes", []) if "session" in request.scope else []
        paths = {
            "pydo.index": "/",
            "pydo.add_todo": "/add",
            "pydo.toggle_todo": "/toggle/{index}",
            "pydo.delete_todo": "/delete/{index}",
            "pydo.edit_todo": "/edit/{index}",
            "pydo.set_due_today": "/today/{index}",
            "pydo.postpone_due_tomorrow": "/tomorrow/{index}",
            "pydo.login": "/login",
            "pydo.logout": "/logout",
            "pydo.static": "/static/{filename}",
            "pydo.filter_project": "/project/{project}",
            "pydo.filter_main_project": "/main-project/{main_project}",
            "pydo.filter_main_project_child": "/main-project/{main_project}/project/{project}",
            "pydo.filter_main_project_no_subproject": "/main-project/{main_project}/no-subproject",
            "pydo.filter_context": "/context/{context}",
            "pydo.filter_priority": "/priority/{priority}",
            "pydo.filter_due": "/due/{date}",
            "pydo.filter_waiting": "/waiting",
            "pydo.filter_waiting_for": "/waiting/{person}",
        }

        def url_for(endpoint, **values):
            path = paths.get(endpoint, "/")
            for key, value in values.items():
                if "{" + key + "}" in path:
                    encoded = (
                        quote(str(value), safe="/")
                        if key == "filename"
                        else quote(str(value), safe="")
                    )
                    path = path.replace("{" + key + "}", encoded)
            query = {
                k: v for k, v in values.items() if "{" + k + "}" not in paths.get(endpoint, "")
            }
            return (
                request.scope.get("root_path", "").rstrip("/")
                + path
                + (("?" + urlencode(query)) if query else "")
            )

        context.update(
            request=request,
            pydo_app_version=configured.app_version,
            pydo_auth_enabled=configured.auth_enabled,
            pydo_about_url=about_url(request),
            flashes=flashes,
            session=request.session if "session" in request.scope else {},
            get_flashed_messages=lambda with_categories=True: (
                flashes if with_categories else [m for _, m in flashes]
            ),
            url_for=url_for,
            is_overdue=lambda value: is_overdue(value, configured.now_provider),
        )
        return template_engine.TemplateResponse(
            request=request, name=f"pydo/{page}.html", context=context
        )

    @app.middleware("http")
    async def login_gate(request: Request, call_next):
        # Starlette preserves the full path in scope["path"] when mounting an
        # app; root_path carries the proxy and mount prefix. Strip it before
        # checking app-local public routes such as /login and /static.
        path = request.url.path
        root_path = request.scope.get("root_path", "").rstrip("/")
        if root_path and (path == root_path or path.startswith(root_path + "/")):
            path = path[len(root_path) :] or "/"
        if (
            configured.auth_enabled
            and path not in {"/login", "/static"}
            and not path.startswith("/static/")
            and not request.session.get("pydo_authenticated")
        ):
            target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
            return RedirectResponse(
                local_url(request, "/login") + "?" + urlencode({"next": target}),
                status_code=302,
            )
        return await call_next(request)

    if configured.secret_key:
        app.add_middleware(
            SessionMiddleware,
            secret_key=configured.secret_key,
            session_cookie=configured.session_cookie_name,
            same_site="lax",
            https_only=False,
        )

    @app.get("/login", name="pydo.login")
    async def login_get(request: Request, next: str = ""):
        if not configured.auth_enabled:
            return RedirectResponse(local_url(request, "/"), status_code=302)
        svc = service()
        return render(
            request,
            "login",
            blocked=svc.is_login_blocked(),
            next_url=next,
            attempts_left=max(0, configured.max_login_attempts - svc.read_attempt_count()),
            max_login_attempts=configured.max_login_attempts,
            auth_block_file=str(configured.auth_block_file),
        )

    @app.post("/login", name="pydo.login_post")
    async def login_post(request: Request):
        form = await request.form()
        svc = service()
        next_url = str(form.get("next", ""))
        blocked = svc.is_login_blocked()
        if not blocked and svc.read_attempt_count() >= configured.max_login_attempts:
            svc.reset_attempt_count()
        if not blocked and svc.verify_login_password(str(form.get("password", ""))):
            request.session["pydo_authenticated"] = True
            svc.reset_attempt_count()
            target = (
                next_url
                if svc.is_safe_next_url(next_url)
                and next_url.startswith("/")
                and not next_url.startswith("//")
                else local_url(request, "/")
            )
            return RedirectResponse(target, status_code=302)
        attempts = svc.record_failed_login() if not blocked else configured.max_login_attempts
        blocked = blocked or attempts >= configured.max_login_attempts
        request.session["_flashes"] = [
            (
                "error",
                "Login is blocked after too many failed attempts."
                if blocked
                else f"Invalid password. {configured.max_login_attempts - attempts} attempt(s) left.",
            )
        ]
        return render(
            request,
            "login",
            blocked=blocked,
            next_url=next_url,
            attempts_left=max(0, configured.max_login_attempts - attempts),
            max_login_attempts=configured.max_login_attempts,
            auth_block_file=str(configured.auth_block_file),
        )

    @app.get("/logout", name="pydo.logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse(local_url(request, "/login"), status_code=302)

    def render_index(
        request,
        items,
        todos,
        filter_by="active",
        filter_value=None,
        sidebar_scope="active",
    ):
        return render(
            request,
            "index",
            **service().build_template_context(
                todos, items, filter_by, filter_value, sidebar_scope
            ),
        )

    @app.get("/", name="pydo.index")
    async def index(request: Request, filter: str = "active", scope: str = "active"):
        svc, todos = service(), service().get_todos()
        items = (
            todos.get_completed()
            if filter == "completed"
            else todos.todos
            if filter == "all"
            else svc.sort_active_items(todos.get_active())
        )
        return render_index(
            request,
            items,
            todos,
            filter,
            sidebar_scope=scope
            if filter == "all"
            else filter
            if filter == "completed"
            else "active",
        )

    @app.post("/add", name="pydo.add_todo")
    async def add_todo(request: Request):
        form = await request.form()
        text = str(form.get("text", "")).strip()
        if text:
            service().get_todos().add(text, normalize_priority(str(form.get("priority", ""))))
        return RedirectResponse(local_url(request, "/"), status_code=302)

    async def mutation(request: Request, action: str, index: int):
        form = await request.form()
        todos = service().get_todos()
        line = str(form.get("line", "")).strip()
        if action == "toggle":
            todos.toggle_by_line(line) if line else todos.toggle(index)
            success, error = True, ""
        elif action == "delete":
            todos.remove_by_line(line) if line else todos.remove(index)
            success, error = True, ""
        elif action == "edit":
            text = str(form.get("text", "")).strip()
            if not text:
                success, error = False, "Text cannot be empty"
            elif line:
                success, error = (
                    todos.update_by_line(
                        line,
                        text,
                        normalize_priority(str(form.get("priority", ""))),
                        True,
                    ),
                    "Task not found",
                )
            elif 0 <= index < len(todos.todos):
                todos.todos[index].text = text
                todos.todos[index].priority = normalize_priority(str(form.get("priority", "")))
                todos.save()
                success, error = True, ""
            else:
                success, error = False, "Task not found"
        elif action in {"today", "tomorrow"}:
            success = (
                todos.set_due_by_line(line, service().today())
                if action == "today" and line
                else todos.postpone_due_by_line(line, 1)
                if line
                else False
            )
            error = "Task due date not found"
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse(
                {"success": success, **({"error": error} if not success else {})},
                status_code=400 if error == "Text cannot be empty" else 404 if not success else 200,
            )
        return RedirectResponse(safe_referrer(request), status_code=302)

    for action in ("toggle", "delete", "edit", "today", "tomorrow"):

        async def endpoint(request: Request, index: int, _action=action):
            return await mutation(request, _action, index)

        app.add_api_route(
            f"/{action}/{{index}}",
            endpoint,
            methods=["POST"],
            name=f"pydo.{action}_todo",
        )

    @app.get("/project/{project}", name="pydo.filter_project")
    async def project(request: Request, project: str, scope: str = "active"):
        svc = service()
        todos = svc.get_todos()
        items = [t for t in svc.get_items_for_scope(todos, scope) if project in t.projects]
        return render_index(request, items, todos, "project", project, scope)

    @app.get("/main-project/{main_project}", name="pydo.filter_main_project")
    async def main_project(request: Request, main_project: str, scope: str = "active"):
        svc = service()
        todos = svc.get_todos()
        items = [
            t for t in svc.get_items_for_scope(todos, scope) if main_project in t.main_projects
        ]
        return render_index(request, items, todos, "main_project", main_project, scope)

    @app.get(
        "/main-project/{main_project}/project/{project}",
        name="pydo.filter_main_project_child",
    )
    async def child(request: Request, main_project: str, project: str, scope: str = "active"):
        svc = service()
        todos = svc.get_todos()
        items = [
            t
            for t in svc.get_items_for_scope(todos, scope)
            if main_project in t.main_projects and project in t.projects
        ]
        return render_index(
            request,
            items,
            todos,
            "main_project_child",
            {"main_project": main_project, "project": project},
            scope,
        )

    @app.get(
        "/main-project/{main_project}/no-subproject",
        name="pydo.filter_main_project_no_subproject",
    )
    async def no_child(request: Request, main_project: str, scope: str = "active"):
        svc = service()
        todos = svc.get_todos()
        items = [
            t
            for t in svc.get_items_for_scope(todos, scope)
            if main_project in t.main_projects and not t.projects
        ]
        return render_index(
            request, items, todos, "main_project_no_subproject", main_project, scope
        )

    @app.get("/context/{context}", name="pydo.filter_context")
    async def context(request: Request, context: str, scope: str = "active"):
        svc = service()
        todos = svc.get_todos()
        items = [t for t in svc.get_items_for_scope(todos, scope) if context in t.contexts]
        return render_index(request, items, todos, "context", context, scope)

    @app.get("/priority/{priority}", name="pydo.filter_priority")
    async def priority(request: Request, priority: str, scope: str = "active"):
        svc = service()
        todos = svc.get_todos()
        p = priority.upper()
        if p not in {"A", "B", "C"}:
            return RedirectResponse(
                local_url(request, "/") + "?" + urlencode({"filter": scope}),
                status_code=302,
            )
        return render_index(
            request,
            [t for t in svc.get_items_for_scope(todos, scope) if t.priority == p],
            todos,
            "priority",
            p,
            scope,
        )

    @app.get("/due/{date}", name="pydo.filter_due")
    async def due(request: Request, date: str):
        svc = service()
        todos = svc.get_todos()
        return render_index(
            request,
            [t for t in todos.todos if t.custom_fields.get("due") == date and not t.complete],
            todos,
            "due",
            date,
        )

    @app.get("/waiting", name="pydo.filter_waiting")
    async def waiting(request: Request, scope: str = "active"):
        svc = service()
        todos = svc.get_todos()
        return render_index(
            request,
            [
                t
                for t in svc.get_items_for_scope(todos, scope)
                if "waiting" in t.contexts or t.custom_fields.get("waiting")
            ],
            todos,
            "waiting",
            None,
            scope,
        )

    @app.get("/waiting/{person}", name="pydo.filter_waiting_for")
    async def waiting_person(request: Request, person: str, scope: str = "active"):
        svc = service()
        todos = svc.get_todos()
        return render_index(
            request,
            [
                t
                for t in svc.get_items_for_scope(todos, scope)
                if t.custom_fields.get("waiting", "").lower() == person.lower()
            ],
            todos,
            "waiting_for",
            person,
            scope,
        )

    @app.exception_handler(404)
    async def not_found(request: Request, exc):
        response = render(request, "404")
        response.status_code = 404
        return response

    @app.exception_handler(500)
    async def server_error(request: Request, exc):
        response = render(request, "500")
        response.status_code = 500
        return response

    return app
