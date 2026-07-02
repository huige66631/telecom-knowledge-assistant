from __future__ import annotations

from openai import OpenAI

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError
from app.core.logging import get_logger
from app.core.prompts import (
    QUERY_REWRITE_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_query_rewrite_prompt,
    build_rag_user_prompt,
)
from app.rag.retriever import RetrievedChunk


class GenerationService:
    """Grounded answer generation over retrieved knowledge chunks."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: OpenAI | None = None
        self.logger = get_logger(__name__)

    @property
    def client(self) -> OpenAI:
        if not self.settings.deepseek_api_key:
            raise ConfigurationError("DEEPSEEK_API_KEY is not configured. Add it to your .env before generating answers.")

        if self._client is None:
            self._client = OpenAI(
                api_key=self.settings.deepseek_api_key,
                base_url=self.settings.deepseek_base_url,
            )
        return self._client

    def generate_answer(
        self,
        question: str,
        matches: list[RetrievedChunk],
        conversation_summary: str = "",
    ) -> str:
        prompt = build_rag_user_prompt(
            question=question,
            matches=matches,
            conversation_summary=conversation_summary,
        )

        response = self.client.chat.completions.create(
            model=self.settings.deepseek_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        text = (response.choices[0].message.content or "").strip()
        if not text:
            self.logger.warning("DeepSeek returned an empty completion.")
            raise ConfigurationError("Model response was empty.")
        return text

    def rewrite_query(
        self,
        question: str,
        conversation_summary: str = "",
        recent_turns: list[dict[str, str]] | None = None,
    ) -> str:
        prompt = build_query_rewrite_prompt(
            question=question,
            conversation_summary=conversation_summary,
            recent_turns=recent_turns,
        )

        response = self.client.chat.completions.create(
            model=self.settings.deepseek_model,
            messages=[
                {"role": "system", "content": QUERY_REWRITE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        text = (response.choices[0].message.content or "").strip()
        if not text:
            self.logger.warning("DeepSeek returned an empty query rewrite.")
            raise ConfigurationError("Query rewrite response was empty.")
        return text.splitlines()[0].strip()
