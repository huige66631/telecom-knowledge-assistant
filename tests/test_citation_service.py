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


def test_citation_service_prefers_content_block_for_snippet() -> None:
    service = CitationService()
    citations = service.build_citations(
        [
            RetrievedChunk(
                chunk_id="chunk-2",
                text=(
                    "Section Title: 2.3 语音信号采集与量化编码\n"
                    "Page: 11\n"
                    "Element Type: paragraph\n"
                    "Page Summary: heading: 5\n"
                    "Content:\n"
                    "本文语音链路采用 8 kHz 采样率和 16 bit 线性 PCM 编码。"
                ),
                source="paper.pdf",
                source_type="pdf",
                source_path="data/raw/paper.pdf",
                page=11,
                distance=0.2,
                element_type="paragraph",
                section_title="2.3 语音信号采集与量化编码",
            )
        ]
    )

    assert citations[0].snippet == "本文语音链路采用 8 kHz 采样率和 16 bit 线性 PCM 编码。"
