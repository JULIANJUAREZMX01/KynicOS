import pytest

from app.core.context import AgentContext
from app.cloud.sessions import SessionManager


@pytest.mark.asyncio
async def test_context_round_trip_preserves_state_files_and_metadata():
    ctx = AgentContext(session_id="s1", user_id="u1", channel="telegram")
    ctx.state["room_number"] = "1204"
    ctx.add_file("workspace/logic/photo.jpg")
    ctx.add_message("user", "hola", metadata={"source": "test"})

    payload = ctx.to_dict()
    assert payload["state"]["room_number"] == "1204"
    assert payload["files"] == ["workspace/logic/photo.jpg"]
    assert payload["messages"][0]["metadata"] == {"source": "test"}
    assert payload["messages"][0]["timestamp"]


@pytest.mark.asyncio
async def test_session_manager_restores_context(tmp_path):
    manager = SessionManager(str(tmp_path))
    ctx = AgentContext(session_id="s2", user_id="u2", channel="whatsapp")
    ctx.state.update({"room_number": "1204", "guest_name": "Ana"})
    ctx.add_file("workspace/logic/audio.mp3")
    ctx.add_message("user", "adios", metadata={"media": True})

    assert await manager.save_session(ctx)
    loaded = await manager.load_session("s2")

    assert loaded is not None
    assert loaded.state == ctx.state
    assert loaded.files == ctx.files
    assert loaded.messages[0].metadata == {"media": True}
    assert loaded.messages[0].timestamp == ctx.messages[0].timestamp
