from app.rag.chunker import ChunkRecord
from app.services.document_tool_service import DocumentToolService


class FakeVectorStore:
    def __init__(self) -> None:
        self.records = [
            {
                "chunk_id": "c1",
                "text": "Page: 3\nElement Type: paragraph\nContent:\n正文说明",
                "metadata": {
                    "source_name": "manual.pdf",
                    "source_type": "pdf",
                    "source_path": "data/raw/manual.pdf",
                    "page": 3,
                    "element_type": "paragraph",
                    "chunk_index": 1,
                    "section_title": "3.1 概述",
                    "parent_section": "3 系统功能",
                    "page_summary": "paragraph: 正文说明",
                },
            },
            {
                "chunk_id": "c2",
                "text": "Page: 3\nElement Type: table\nContent:\n参数表内容",
                "metadata": {
                    "source_name": "manual.pdf",
                    "source_type": "pdf",
                    "source_path": "data/raw/manual.pdf",
                    "page": 3,
                    "element_type": "table",
                    "chunk_index": 2,
                    "table_title": "表 1 参数要求",
                    "page_summary": "table: 参数表内容",
                },
            },
            {
                "chunk_id": "c3",
                "text": "Page: 3\nElement Type: figure_caption\nContent:\n图 2 组网拓扑",
                "metadata": {
                    "source_name": "manual.pdf",
                    "source_type": "pdf",
                    "source_path": "data/raw/manual.pdf",
                    "page": 3,
                    "element_type": "figure_caption",
                    "chunk_index": 3,
                    "figure_caption": "图 2 组网拓扑",
                    "section_title": "3.2 网络拓扑",
                    "page_summary": "figure_caption: 图 2 组网拓扑",
                },
            },
        ]

    def get_chunks_by_page(self, source_name: str, page: int) -> list[dict[str, object]]:
        return [record for record in self.records if record["metadata"]["source_name"] == source_name and record["metadata"]["page"] == page]

    def get_chunks_by_element(self, source_name: str, element_type: str, page: int | None = None) -> list[dict[str, object]]:
        return [
            record
            for record in self.records
            if record["metadata"]["source_name"] == source_name
            and record["metadata"]["element_type"] == element_type
            and (page is None or record["metadata"]["page"] == page)
        ]


def test_document_tool_service_reads_page() -> None:
    service = DocumentToolService()
    service.vector_store = FakeVectorStore()

    results = service.read_page(source_name="manual.pdf", page=3)

    assert len(results) == 3
    assert results[0].page == 3
    assert any(item.element_type == "figure_caption" for item in results)


def test_document_tool_service_extracts_tables() -> None:
    service = DocumentToolService()
    service.vector_store = FakeVectorStore()

    results = service.extract_tables(source_name="manual.pdf", page=3)

    assert len(results) == 1
    assert results[0].element_type == "table"
    assert results[0].table_title == "表 1 参数要求"


def test_document_tool_service_describes_figures() -> None:
    service = DocumentToolService()
    service.vector_store = FakeVectorStore()
    service.settings.figure_vision_enabled = False

    results = service.describe_figures(source_name="manual.pdf", page=3)

    assert len(results) == 1
    assert results[0].element_type == "figure_description"
