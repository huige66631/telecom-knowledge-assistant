from app.models.session_memory import session_memory_store
from app.services.session_service import SessionService


def test_session_service_returns_turns() -> None:
    session = session_memory_store.get_or_create("session-test-service")
    session_memory_store.append_turn(session.session_id, "user", "第一问")
    session_memory_store.append_turn(session.session_id, "assistant", "第一答")

    service = SessionService()
    response = service.get_session(session.session_id)

    assert response.session_id == session.session_id
    assert len(response.turns) >= 2
