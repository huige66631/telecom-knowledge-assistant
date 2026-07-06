from __future__ import annotations

from typing import Literal, TypedDict

from app.rag.retriever import RetrievedChunk


AgentRoute = Literal["answer", "clarify", "out_of_scope", "fallback"]


class AgentState(TypedDict, total=False):
    question: str
    conversation_summary: str
    recent_turns: list[dict[str, str]]
    route: AgentRoute
    matches: list[RetrievedChunk]
    page_evidence: list[RetrievedChunk]
    table_evidence: list[RetrievedChunk]
    figure_evidence: list[RetrievedChunk]
    answer: str
    used_fallback: bool
    retrieval_query: str
    rewritten_question: str
    rewrite_strategy: str
