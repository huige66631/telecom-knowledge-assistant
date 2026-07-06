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


def test_reranker_prefers_structure_body_over_heading() -> None:
    reranker = SimpleReranker()
    results = reranker.rerank(
        [
            {
                "chunk_id": "heading",
                "text": "Section Title: 3.3 OFDM发射端模块设计\nContent:\n3.3 OFDM发射端模块设计",
                "metadata": {
                    "source_type": "pdf",
                    "element_type": "heading",
                    "section_title": "3.3 OFDM发射端模块设计",
                },
                "fused_score": 0.03,
            },
            {
                "chunk_id": "body",
                "text": "Section Title: 3.3 OFDM发射端模块设计\nContent:\nOFDM 发射端由比特填充、调制映射、子载波装载、前导插入、IFFT 和循环前缀添加组成。",
                "metadata": {
                    "source_type": "pdf",
                    "element_type": "paragraph",
                    "section_title": "3.3 OFDM发射端模块设计",
                },
                "fused_score": 0.03,
            },
        ],
        query="这个项目的OFDM发射端模块是怎么设计的",
    )

    assert results[0]["chunk_id"] == "body"
