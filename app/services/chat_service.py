from app.agent.graph import KnowledgeAgentGraph
from app.core.logging import get_logger
from app.models.schemas import ChatRequest, ChatResponse
from app.models.session_memory import session_memory_store
from app.services.citation_service import CitationService


class ChatService:
    """Stage-four chat service with KB-first routing and session memory."""

    def __init__(self) -> None:
        self._agent: KnowledgeAgentGraph | None = None
        self.citation_service = CitationService()
        self.logger = get_logger(__name__)

    @property
    def agent(self) -> KnowledgeAgentGraph:
        if self._agent is None:
            self._agent = KnowledgeAgentGraph()
        return self._agent

    def reply(self, request: ChatRequest) -> ChatResponse:
        session = session_memory_store.get_or_create(request.session_id)
        self.logger.info("Handling chat request for session '%s'.", session.session_id)
        recent_turns = [
            {"role": turn.role, "content": turn.content}
            for turn in session.turns
        ]
        state = self.agent.invoke_with_context(
            question=request.question,
            conversation_summary=session.summary,
            recent_turns=recent_turns,
        )
        matches = state.get("matches", [])
        citations = self.citation_service.build_citations(matches)
        answer = state.get("answer", "系统暂时没有生成结果。")

        session_memory_store.append_turn(session.session_id, "user", request.question)
        session = session_memory_store.append_turn(session.session_id, "assistant", answer)
        self.logger.info(
            "Chat request for session '%s' completed with route '%s' and %s citations.",
            session.session_id,
            state.get("route", "fallback"),
            len(citations),
        )

        return ChatResponse(
            answer=answer,
            citations=citations,
            route=state.get("route", "fallback"),
            matched_chunks=len(matches),
            session_id=session.session_id,
            memory_summary=session.summary,
            rewritten_question=state.get("rewritten_question"),
            rewrite_strategy=state.get("rewrite_strategy"),
        )
