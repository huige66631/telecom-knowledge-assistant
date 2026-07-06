from app.rag.retriever import RetrievedChunk
from app.services.citation_service import CitationService


def test_citation_service_builds_citations() -> None:
    service = CitationService()
    citations = service.build_citations(
        [
            RetrievedChunk(
                chunk_id="chunk-1",
                text="设备支持 SNMPv3 和 SSH。",
                source="manual.pdf",
                source_type="pdf",
                source_path="data/raw/manual.pdf",
                page=2,
                distance=0.15,
                element_type="table",
                section_title="3.1 管理协议",
                table_title="表 2 管理能力",
                keyword_score=2.4,
                fused_score=0.031,
            )
        ]
    )

    assert len(citations) == 1
    assert citations[0].source == "manual.pdf"
    assert citations[0].page == 2
    assert citations[0].element_type == "table"
    assert citations[0].section_title == "3.1 管理协议"
