from __future__ import annotations

from typing import Literal, TypedDict

from app.rag.retriever import RetrievedChunk


AgentRoute = Literal["answer", "clarify", "out_of_scope", "fallback"]


class AgentState(TypedDict, total=False):
    question: str
    conversation_summary: str
    route: AgentRoute
    matches: list[RetrievedChunk]
    answer: str
    used_fallback: bool
