from app.rag.keyword_index import KeywordIndex


def test_keyword_index_finds_matching_document() -> None:
    index = KeywordIndex(
        [
            {
                "chunk_id": "c1",
                "text": "交换机支持 SNMP SSH Telnet 管理协议。",
                "metadata": {"source_name": "a.txt"},
            },
            {
                "chunk_id": "c2",
                "text": "这是一段无关的市场宣传文案。",
                "metadata": {"source_name": "b.txt"},
            },
        ]
    )

    results = index.search("支持哪些管理协议", top_k=2)

    assert results
    assert results[0]["chunk_id"] == "c1"
