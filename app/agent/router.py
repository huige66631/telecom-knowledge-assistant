from __future__ import annotations

from app.agent.state import AgentRoute, AgentState
from app.core.config import get_settings


OUT_OF_SCOPE_HINTS = (
    "天气",
    "股票",
    "电影",
    "旅游",
    "菜谱",
    "八卦",
    "娱乐",
    "体育",
    "小说",
    "翻译整篇",
)


class KBFirstRouter:
    """Route queries based on retrieval evidence and obvious domain mismatch."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def decide(self, state: AgentState) -> AgentRoute:
        question = state["question"]
        matches = state.get("matches", [])
        page_evidence = state.get("page_evidence", [])
        table_evidence = state.get("table_evidence", [])
        figure_evidence = state.get("figure_evidence", [])

        if any(hint in question for hint in OUT_OF_SCOPE_HINTS):
            return "out_of_scope"

        if len(matches) + len(page_evidence) + len(table_evidence) + len(figure_evidence) >= self.settings.min_answerable_matches:
            return "answer"

        if not matches:
            return "clarify"

        return "fallback"
