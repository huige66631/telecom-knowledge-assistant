from app.models.schemas import ChatResponse


def test_chat_response_supports_session_fields() -> None:
    payload = ChatResponse(
        answer="ok",
        route="answer",
        matched_chunks=2,
        session_id="session-1",
        memory_summary="user: test",
        rewritten_question="某型号交换机支持哪些管理协议？",
        rewrite_strategy="rule_context",
    )

    assert payload.session_id == "session-1"
    assert payload.memory_summary == "user: test"
    assert payload.rewritten_question == "某型号交换机支持哪些管理协议？"
    assert payload.rewrite_strategy == "rule_context"
