from __future__ import annotations

import json
import re
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.retriever import KnowledgeRetriever


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def load_eval_set(path: Path) -> list[dict[str, object]]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    eval_path = PROJECT_ROOT / "docs" / "eval" / "retrieval_eval_set.json"
    eval_set = load_eval_set(eval_path)
    retriever = KnowledgeRetriever()

    top1_hits = 0
    top4_hits = 0
    mrr_total = 0.0
    rows: list[dict[str, object]] = []

    for item in eval_set:
        question = str(item["question"])
        expected_page = int(item["expected_page"])
        expected_clues = [str(clue) for clue in item.get("expected_clues", [])]
        results = retriever.search(question, top_k=4)

        hit_positions: list[int] = []
        for index, match in enumerate(results, start=1):
            text = normalize(match.text)
            page_ok = match.page == expected_page
            clue_ok = any(normalize(clue) in text for clue in expected_clues)
            if page_ok and clue_ok:
                hit_positions.append(index)

        if hit_positions:
            top4_hits += 1
            mrr_total += 1.0 / hit_positions[0]
        if 1 in hit_positions:
            top1_hits += 1

        rows.append(
            {
                "question": question,
                "hit_positions": hit_positions,
                "results": [
                    {
                        "page": match.page,
                        "element_type": match.element_type,
                        "fused_score": round(match.fused_score or 0.0, 4),
                        "section_title": match.section_title,
                    }
                    for match in results
                ],
            }
        )

    total = len(eval_set) or 1
    summary = {
        "queries": total,
        "top1_hits": top1_hits,
        "top4_hits": top4_hits,
        "recall_at_1": round(top1_hits / total, 4),
        "recall_at_4": round(top4_hits / total, 4),
        "mrr_at_4": round(mrr_total / total, 4),
    }

    print(json.dumps({"summary": summary, "details": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
