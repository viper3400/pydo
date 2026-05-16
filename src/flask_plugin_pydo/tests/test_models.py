from flask_plugin_pydo.models import Todo


def test_parse_priority_project_context_custom_fields():
    todo = Todo.from_line("(A) Call Bob +Work @phone due:2026-04-20 waiting:alice")

    assert todo is not None
    assert todo.priority == "A"
    assert "Work" in todo.projects
    assert "phone" in todo.contexts
    assert todo.custom_fields.get("due") == "2026-04-20"
    assert todo.custom_fields.get("waiting") == "alice"


def test_parse_main_project_without_creating_normal_project():
    line = "Build rollout ++ClientA +Migration"
    todo = Todo.from_line(line)

    assert todo is not None
    assert todo.main_projects == ["ClientA"]
    assert todo.projects == ["Migration"]
    assert todo.to_line() == line

    display = todo.get_display_text()
    assert "++ClientA" not in display
    assert "+Migration" not in display
    assert display == "Build rollout"


def test_main_project_without_child_project_is_supported():
    todo = Todo.from_line("Review roadmap ++ClientA")

    assert todo is not None
    assert todo.main_projects == ["ClientA"]
    assert todo.projects == []
    assert todo.get_display_text() == "Review roadmap"


def test_plus_inside_link_is_not_parsed_as_project():
    todo = Todo.from_line(
        "Review board link:https://confluence.cgm.ag/spaces/CHClientSolution/pages/2188031700/Program+Board+2026-04-27 +Work"
    )

    assert todo is not None
    assert todo.links == [
        "https://confluence.cgm.ag/spaces/CHClientSolution/pages/2188031700/Program+Board+2026-04-27"
    ]
    assert todo.projects == ["Work"]
    assert todo.main_projects == []

    display = todo.get_display_text()
    assert "Program+Board+2026-04-27" not in display
    assert "+Work" not in display


def test_display_text_filters_only_known_custom_fields():
    todo = Todo.from_line("Review docs due:2026-04-21 waiting:alex link:https://example.com ref:ABC-123 +Proj @desk")

    assert todo is not None
    display = todo.get_display_text()

    assert "due:2026-04-21" not in display
    assert "waiting:alex" not in display
    assert "link:https://example.com" not in display
    assert "ref:ABC-123" in display
    assert "+Proj" not in display
    assert "@desk" not in display


def test_parse_multiple_links_and_hide_them_in_display_text():
    todo = Todo.from_line(
        "Read docs link:https://example.com link:docs.python.org due:2026-04-21"
    )

    assert todo is not None
    assert todo.links == ["https://example.com", "docs.python.org"]
    assert todo.custom_fields["link"] == "docs.python.org"

    display = todo.get_display_text()
    assert "link:https://example.com" not in display
    assert "link:docs.python.org" not in display


def test_completed_with_priority_round_trips_without_duplicate_completion_prefix():
    line = "x 2026-04-22 (B) Prepare report due:2026-04-24 @office"
    todo = Todo.from_line(line)

    assert todo is not None
    assert todo.complete is True
    assert todo.priority == "B"
    assert todo.to_line() == line


def test_completed_without_priority_round_trip_stays_stable():
    line = "x 2026-04-22 Finish paperwork due:2026-04-25"
    todo = Todo.from_line(line)

    assert todo is not None
    assert todo.complete is True
    assert todo.priority is None
    assert todo.to_line() == line


def test_active_without_completion_marker_remains_unchanged():
    line = "(A) Prepare workshop due:2026-04-25 +SGF"
    todo = Todo.from_line(line)

    assert todo is not None
    assert todo.complete is False
    assert todo.to_line() == line
