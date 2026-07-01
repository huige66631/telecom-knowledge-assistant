from pathlib import Path

from app.models.session_memory import SessionMemoryStore


def test_session_memory_store_keeps_recent_turns_and_summary(tmp_path: Path) -> None:
    storage_path = tmp_path / "session_memory_1.db"
    store = SessionMemoryStore(max_turns=3, storage_path=str(storage_path))
    session = store.get_or_create(None)

    store.append_turn(session.session_id, "user", "first question")
    store.append_turn(session.session_id, "assistant", "first answer")
    store.append_turn(session.session_id, "user", "second question")
    updated = store.append_turn(session.session_id, "assistant", "second answer")

    assert len(updated.turns) == 3
    assert updated.turns[0].content == "first answer"
    assert "second question" in updated.summary


def test_session_memory_store_can_lookup_session(tmp_path: Path) -> None:
    storage_path = tmp_path / "session_memory_2.db"
    store = SessionMemoryStore(max_turns=4, storage_path=str(storage_path))
    session = store.get_or_create(None)
    store.append_turn(session.session_id, "user", "hello")

    looked_up = store.get_session(session.session_id)

    assert looked_up is not None
    assert looked_up.session_id == session.session_id


def test_session_memory_store_persists_to_disk(tmp_path: Path) -> None:
    storage_path = tmp_path / "session_memory_3.db"
    store = SessionMemoryStore(max_turns=4, storage_path=str(storage_path))
    session = store.get_or_create("session-persist")
    store.append_turn(session.session_id, "user", "first persisted question")
    store.append_turn(session.session_id, "assistant", "first persisted answer")

    reloaded_store = SessionMemoryStore(max_turns=4, storage_path=str(storage_path))
    reloaded = reloaded_store.get_session("session-persist")

    assert reloaded is not None
    assert len(reloaded.turns) == 2
    assert reloaded.turns[1].content == "first persisted answer"
