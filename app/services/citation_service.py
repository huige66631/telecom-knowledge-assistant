from __future__ import annotations

import re

from app.models.schemas import Citation
from app.rag.retriever import RetrievedChunk


class CitationService:
    """Convert retrieved chunks into consistent citation payloads."""

    def build_citations(
        self,
        matches: list[RetrievedChunk],
        snippet_length: int = 280,
        query: str = "",
    ) -> list[Citation]:
        citations: list[Citation] = []
        for match in self._select_display_matches(matches, query=query):
            snippet = self._build_snippet(match.text, snippet_length=snippet_length)
            citations.append(
                Citation(
                    source=match.source,
                    snippet=snippet,
                    chunk_id=match.chunk_id,
                    score=match.distance,
                    page=match.page,
                    element_type=match.element_type,
                    section_title=match.section_title,
                    table_title=match.table_title,
                    figure_caption=match.figure_caption,
                    keyword_score=match.keyword_score,
                    fused_score=match.fused_score,
                )
            )
        return citations

    def _select_display_matches(self, matches: list[RetrievedChunk], query: str = "") -> list[RetrievedChunk]:
        ranked_matches = self._rank_display_matches(matches, query=query)
        selected: list[RetrievedChunk] = []
        seen_pages: set[tuple[str, int | None]] = set()
        deferred: list[RetrievedChunk] = []

        for match in ranked_matches:
            key = (match.source, match.page)
            if key in seen_pages and match.element_type in {"heading", "page_summary", "footnote"}:
                continue

            if match.element_type in {"heading", "page_summary", "footnote"}:
                deferred.append(match)
                continue

            selected.append(match)
            seen_pages.add(key)

        if len(selected) < 4:
            for match in deferred:
                key = (match.source, match.page)
                if key in seen_pages and match.element_type in {"heading", "page_summary", "footnote"}:
                    continue
                selected.append(match)
                seen_pages.add(key)
                if len(selected) >= 4:
                    break

        return selected[:4]

    def _rank_display_matches(self, matches: list[RetrievedChunk], query: str) -> list[RetrievedChunk]:
        query_terms = self._extract_query_terms(query)
        scored: list[tuple[float, RetrievedChunk]] = []

        for match in matches:
            snippet = self._extract_content_block(match.text)
            normalized_snippet = self._normalize(snippet)
            score = float(match.fused_score or 0.0)
            overlap = sum(1 for term in query_terms if len(term) >= 4 and term in normalized_snippet)
            score += min(overlap, 4) * 0.02

            if match.element_type == "paragraph":
                score += 0.03
            elif match.element_type == "table":
                score += 0.025
            elif match.element_type == "heading":
                score -= 0.02

            if self._looks_answer_bearing(normalized_snippet):
                score += 0.03

            scored.append((score, match))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [match for _, match in scored]

    def _build_snippet(self, text: str, snippet_length: int) -> str:
        content = self._extract_content_block(text)
        compact = re.sub(r"\s+", " ", content).strip()
        return compact[:snippet_length]

    def _extract_content_block(self, text: str) -> str:
        marker = "Content:"
        if marker in text:
            content = text.split(marker, 1)[1].strip()
            if content:
                return content

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        filtered = [
            line
            for line in lines
            if not (
                line.startswith("Parent Section:")
                or line.startswith("Section Title:")
                or line.startswith("Table Title:")
                or line.startswith("Figure Caption:")
                or line.startswith("Page:")
                or line.startswith("Element Type:")
                or line.startswith("Page Summary:")
            )
        ]
        return "\n".join(filtered) if filtered else text

    def _extract_query_terms(self, query: str) -> list[str]:
        terms: list[str] = []
        for token in re.findall(r"[a-z0-9][a-z0-9 _./+-]{1,}|[\u4e00-\u9fff]{2,}", query.lower()):
            cleaned = re.sub(r"\s+", "", token.strip())
            if len(cleaned) >= 2 and cleaned not in terms:
                terms.append(cleaned)
        return terms

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", "", text.lower())

    def _looks_answer_bearing(self, normalized_text: str) -> bool:
        return any(marker in normalized_text for marker in ("采用", "使用", "为", "是", "支持", "编码", "16bit", "8khz", "int16"))
