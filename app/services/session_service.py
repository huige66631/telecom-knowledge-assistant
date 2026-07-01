from __future__ import annotations

from app.core.exceptions import BadRequestError
from app.models.schemas import ConversationTurnResponse, SessionResponse
from app.models.session_memory import session_memory_store


class SessionService:
    """Expose session memory in an API-friendly format."""

    def get_session(self, session_id: str) -> SessionResponse:
        session = session_memory_store.get_session(session_id)
        if session is None:
            raise BadRequestError(f"Session '{session_id}' was not found.", error_code="session_not_found")

        return SessionResponse(
            session_id=session.session_id,
            memory_summary=session.summary,
            turns=[
                ConversationTurnResponse(role=turn.role, content=turn.content)
                for turn in session.turns
            ],
        )
