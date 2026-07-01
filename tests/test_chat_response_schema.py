from app.models.schemas import ChatResponse


def test_chat_response_supports_session_fields() -> None:
    payload = ChatResponse(
        answer="ok",
        route="answer",
        matched_chunks=2,
        session_id="session-1",
        memory_summary="user: test",
    )

    assert payload.session_id == "session-1"
    assert payload.memory_summary == "user: test"
