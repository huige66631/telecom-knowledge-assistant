from __future__ import annotations


class SimpleReranker:
    """Apply lightweight heuristic boosting on already-fused retrieval results."""

    def rerank(self, candidates: list[dict[str, object]]) -> list[dict[str, object]]:
        reranked: list[dict[str, object]] = []

        for candidate in candidates:
            score = float(candidate.get("fused_score", 0.0))
            text = str(candidate.get("text", ""))
            metadata = candidate.get("metadata", {})
            source_type = str(metadata.get("source_type", "")) if isinstance(metadata, dict) else ""

            # Slight preference for richer technical snippets.
            if len(text) > 120:
                score += 0.002
            if source_type in {"pdf", "docx"}:
                score += 0.001

            updated = dict(candidate)
            updated["fused_score"] = score
            reranked.append(updated)

        reranked.sort(key=lambda item: float(item.get("fused_score", 0.0)), reverse=True)
        return reranked
