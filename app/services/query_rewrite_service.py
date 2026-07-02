from __future__ import annotations

from dataclasses import dataclass
import re

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.generation_service import GenerationService


CONTEXTUAL_PREFIX_RE = re.compile(r"^(继续问[:：]?\s*|继续\s*|再问[:：]?\s*|再追问[:：]?\s*|那\s*|那么\s*|然后\s*)")
CONTEXTUAL_HINTS = (
    "它",
    "它们",
    "这个",
    "这个问题",
    "这个要求",
    "这些",
    "该",
    "其",
    "那",
    "那么",
    "继续问",
    "再问",
    "再追问",
)
LIGHT_STOPWORDS = {
    "什么",
    "多少",
    "要求",
    "问题",
    "这个",
    "那个",
    "继续",
    "还有",
    "一下",
    "一下子",
}


@dataclass(slots=True)
class QueryRewriteResult:
    rewritten_question: str
    strategy: str = "none"


class QueryRewriteService:
    """Rewrite follow-up questions into standalone retrieval-friendly queries."""

    def __init__(self, generator: GenerationService | None = None) -> None:
        self.settings = get_settings()
        self.generator = generator or GenerationService()
        self.logger = get_logger(__name__)

    def rewrite_with_rules(
        self,
        question: str,
        conversation_summary: str = "",
        recent_turns: list[dict[str, str]] | None = None,
    ) -> QueryRewriteResult:
        normalized = self._normalize(question)
        if not self.settings.query_rewrite_enabled:
            return QueryRewriteResult(rewritten_question=normalized)

        if not self._looks_contextual(normalized, conversation_summary, recent_turns or []):
            return QueryRewriteResult(rewritten_question=normalized)

        focus = self._strip_contextual_prefix(normalized)
        latest_user_turn = self._latest_user_turn(recent_turns or [])
        if latest_user_turn and self._contains_pronoun_hint(normalized):
            return QueryRewriteResult(
                rewritten_question=f"{latest_user_turn}。补充问题：{focus}",
                strategy="rule_followup",
            )

        related_context = self._select_related_context(
            focus=focus,
            conversation_summary=conversation_summary,
            recent_turns=recent_turns or [],
        )
        if related_context:
            return QueryRewriteResult(
                rewritten_question=f"{focus}。相关上下文：{related_context}",
                strategy="rule_context",
            )

        return QueryRewriteResult(rewritten_question=normalized)

    def should_try_llm_fallback(
        self,
        question: str,
        conversation_summary: str = "",
        recent_turns: list[dict[str, str]] | None = None,
    ) -> bool:
        if not self.settings.llm_query_rewrite_enabled:
            return False
        if not (conversation_summary or recent_turns):
            return False
        return self._looks_contextual(question, conversation_summary, recent_turns or [])

    def rewrite_with_llm(
        self,
        question: str,
        conversation_summary: str = "",
        recent_turns: list[dict[str, str]] | None = None,
    ) -> QueryRewriteResult:
        try:
            rewritten = self.generator.rewrite_query(
                question=question,
                conversation_summary=conversation_summary,
                recent_turns=recent_turns or [],
            )
        except Exception as exc:
            self.logger.warning("LLM query rewrite skipped: %s", exc)
            return QueryRewriteResult(rewritten_question=self._normalize(question))

        rewritten = self._normalize(rewritten)
        if not rewritten:
            return QueryRewriteResult(rewritten_question=self._normalize(question))
        return QueryRewriteResult(rewritten_question=rewritten, strategy="llm_fallback")

    def _looks_contextual(
        self,
        question: str,
        conversation_summary: str,
        recent_turns: list[dict[str, str]],
    ) -> bool:
        normalized = self._normalize(question)
        if len(normalized) <= 12 and (conversation_summary or recent_turns):
            return True
        if CONTEXTUAL_PREFIX_RE.match(normalized):
            return True
        return any(hint in normalized for hint in CONTEXTUAL_HINTS)

    def _strip_contextual_prefix(self, question: str) -> str:
        stripped = CONTEXTUAL_PREFIX_RE.sub("", question).strip()
        return stripped or question

    def _select_related_context(
        self,
        focus: str,
        conversation_summary: str,
        recent_turns: list[dict[str, str]],
    ) -> str:
        keywords = self._extract_keywords(focus)
        if not keywords:
            return ""

        fragments: list[str] = []

        for piece in conversation_summary.split("|"):
            fragment = piece.strip()
            if fragment and any(keyword in fragment for keyword in keywords):
                fragments.append(fragment)

        for turn in recent_turns[-self.settings.query_rewrite_context_turns :]:
            content = turn.get("content", "").strip()
            if content and any(keyword in content for keyword in keywords):
                fragments.append(f"{turn.get('role', 'unknown')}: {content}")

        deduped: list[str] = []
        for fragment in fragments:
            if fragment not in deduped:
                deduped.append(fragment)

        if deduped:
            return "；".join(deduped[-2:])

        summary_fallback = [piece.strip() for piece in conversation_summary.split("|") if piece.strip()]
        if summary_fallback:
            return "；".join(summary_fallback[-2:])

        turn_fallback = [
            f"{turn.get('role', 'unknown')}: {turn.get('content', '').strip()}"
            for turn in recent_turns[-2:]
            if turn.get("content", "").strip()
        ]
        return "；".join(turn_fallback)

    def _latest_user_turn(self, recent_turns: list[dict[str, str]]) -> str:
        for turn in reversed(recent_turns):
            if turn.get("role") == "user":
                content = turn.get("content", "").strip()
                if content:
                    return content
        return ""

    def _contains_pronoun_hint(self, question: str) -> bool:
        return any(hint in question for hint in ("它", "它们", "这个", "这些", "该", "其"))

    def _extract_keywords(self, text: str) -> list[str]:
        candidates = re.findall(r"[A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}", text)
        keywords: list[str] = []
        for candidate in candidates:
            if candidate in LIGHT_STOPWORDS:
                continue
            if candidate not in keywords:
                keywords.append(candidate)
        return keywords[:6]

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()
