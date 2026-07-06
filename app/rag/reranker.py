from __future__ import annotations

import re


class SimpleReranker:
    """Apply lightweight heuristic boosting on already-fused retrieval results."""

    def rerank(self, candidates: list[dict[str, object]], query: str = "") -> list[dict[str, object]]:
        reranked: list[dict[str, object]] = []
        query_terms = self._extract_query_terms(query)
        query_type = self._classify_query(query)

        for candidate in candidates:
            score = float(candidate.get("fused_score", 0.0))
            text = str(candidate.get("text", ""))
            metadata = candidate.get("metadata", {})
            source_type = str(metadata.get("source_type", "")) if isinstance(metadata, dict) else ""
            element_type = str(metadata.get("element_type", "")) if isinstance(metadata, dict) else ""
            section_title = str(metadata.get("section_title", "")) if isinstance(metadata, dict) else ""
            parent_section = str(metadata.get("parent_section", "")) if isinstance(metadata, dict) else ""
            normalized_text = self._normalize(text)
            normalized_section = self._normalize(section_title)
            normalized_parent = self._normalize(parent_section)

            if len(text) > 120:
                score += 0.002
            if source_type in {"pdf", "docx"}:
                score += 0.001
            if element_type in {"paragraph", "table"}:
                score += 0.010
            if element_type in {"heading", "page_summary", "footnote", "toc_entry"}:
                score -= 0.012

            exact_hits = sum(1 for term in query_terms if len(term) >= 4 and term in normalized_text)
            score += min(exact_hits, 4) * 0.004

            if self._looks_answer_bearing(query_type=query_type, normalized_text=normalized_text):
                score += 0.010
            if self._section_matches_query(query_terms, normalized_section, normalized_parent):
                score += 0.012
            if query_type == "structure":
                score += self._structure_score(normalized_text, element_type)
            elif query_type == "fact":
                score += self._fact_score(normalized_text, element_type)

            updated = dict(candidate)
            updated["fused_score"] = score
            reranked.append(updated)

        reranked.sort(key=lambda item: float(item.get("fused_score", 0.0)), reverse=True)
        return reranked

    def _extract_query_terms(self, query: str) -> list[str]:
        terms: list[str] = []
        for token in re.findall(r"[a-z0-9][a-z0-9 _./+-]{1,}|[\u4e00-\u9fff]{2,}", query.lower()):
            cleaned = re.sub(r"\s+", "", token.strip())
            if len(cleaned) >= 2 and cleaned not in terms:
                terms.append(cleaned)
        return terms

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", "", text.lower())

    def _classify_query(self, query: str) -> str:
        normalized_query = self._normalize(query)
        if any(token in normalized_query for token in ("怎么设计", "设计", "模块", "流程", "步骤", "组成", "实现", "原理")):
            return "structure"
        if any(token in normalized_query for token in ("什么", "哪种", "采用", "多少", "类型", "编码", "参数", "配置")):
            return "fact"
        return "generic"

    def _looks_answer_bearing(self, query_type: str, normalized_text: str) -> bool:
        if query_type == "structure":
            structure_markers = ("组成", "包括", "首先", "随后", "然后", "最终", "装载", "插入", "ifft", "循环前缀", "映射")
            hit_count = sum(1 for marker in structure_markers if marker in normalized_text)
            return hit_count >= 2

        if query_type != "fact":
            return False

        answer_markers = ("采用", "使用", "支持", "配置", "16bit", "8khz", "int16", "pcm编码", "线性pcm")
        return any(marker in normalized_text for marker in answer_markers)

    def _section_matches_query(self, query_terms: list[str], normalized_section: str, normalized_parent: str) -> bool:
        for term in query_terms:
            compact = re.sub(r"\s+", "", term.lower())
            if len(compact) < 4:
                continue
            if compact in normalized_section or compact in normalized_parent:
                return True
        return False

    def _structure_score(self, normalized_text: str, element_type: str) -> float:
        if element_type != "paragraph":
            return 0.0
        markers = (
            "组成",
            "包括",
            "首先",
            "随后",
            "然后",
            "最终",
            "填充",
            "调制",
            "装载",
            "前导",
            "ifft",
            "循环前缀",
            "子载波",
        )
        hit_count = sum(1 for marker in markers if marker in normalized_text)
        return min(hit_count, 5) * 0.006

    def _fact_score(self, normalized_text: str, element_type: str) -> float:
        if element_type != "paragraph":
            return 0.0
        markers = ("采用", "使用", "支持", "16bit", "8khz", "int16", "pcm编码", "线性pcm", "qpsk", "16qam")
        hit_count = sum(1 for marker in markers if marker in normalized_text)
        return min(hit_count, 4) * 0.005
