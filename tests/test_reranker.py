from app.rag.reranker import SimpleReranker


def test_reranker_prefers_richer_technical_text() -> None:
    reranker = SimpleReranker()
    results = reranker.rerank(
        [
            {
                "chunk_id": "short",
                "text": "短文本。",
                "metadata": {"source_type": "txt"},
                "fused_score": 0.02,
            },
            {
                "chunk_id": "long",
                "text": "这是一段更长的技术说明文本，用于描述设备支持的管理协议、限制条件和运维建议。" * 3,
                "metadata": {"source_type": "pdf"},
                "fused_score": 0.02,
            },
        ]
    )

    assert results[0]["chunk_id"] == "long"
