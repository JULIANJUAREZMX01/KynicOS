from app.core.context import AgentContext
from app.core.skill_engine import IMMUTABLE_SKILLS, _normalize_skill_name, _validate_skill_code


def test_room_and_guest_properties_are_persisted_in_state():
    ctx = AgentContext(session_id="s1", user_id="u1", channel="test")
    ctx.room_number = "1204"
    ctx.guest_name = "Ana"

    assert ctx.state["room_number"] == "1204"
    assert ctx.state["guest_name"] == "Ana"
    assert ctx.room_number == "1204"
    assert ctx.guest_name == "Ana"


def test_room_and_guest_properties_remove_values_when_set_to_none():
    ctx = AgentContext(session_id="s1", user_id="u1", channel="test")
    ctx.state.update({"room_number": "1204", "guest_name": "Ana"})

    ctx.room_number = None
    ctx.guest_name = None

    assert "room_number" not in ctx.state
    assert "guest_name" not in ctx.state


def test_immutable_registry_contains_only_current_core_names():
    expected = {
        "hvac_triage",
        "mueve_cancun",
        "last30days",
        "memory_manager",
        "skill_builder",
        "web_research",
    }
    assert IMMUTABLE_SKILLS == expected


def test_generated_skill_validation_rejects_dangerous_imports():
    assert not _validate_skill_code("import os\ndef run():\n    return os.getcwd()")
    assert _validate_skill_code("def run():\n    return 'ok'")


def test_skill_name_normalization_is_deterministic():
    assert _normalize_skill_name(" My New Skill ") == "my_new_skill"
    assert _normalize_skill_name("123bad") == ""
