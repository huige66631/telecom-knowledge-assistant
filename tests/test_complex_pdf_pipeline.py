from pathlib import Path

from app.rag.chunker import TextChunker
from app.rag.loader import DocumentLoader


def test_complex_pdf_like_text_keeps_table_and_figure_context(tmp_path: Path) -> None:
    loader = DocumentLoader()
    chunker = TextChunker(chunk_size=140, chunk_overlap=20)
    file_path = tmp_path / "complex.md"
    file_path.write_text(
        "\n".join(
            [
                "2. 接口稳定性测试",
                "",
                "该章节定义了热插拔恢复和接口丢包率约束。",
                "",
                "表 3 热插拔恢复指标",
                "测试项    指标    说明",
                "恢复时间  30秒    热插拔后恢复转发",
                "丢包率    0.1%    恢复期间允许的最大丢包",
                "",
                "图 2 组网拓扑",
                "接入交换机双上联至汇聚交换机。",
            ]
        ),
        encoding="utf-8",
    )

    document = loader.load(file_path=file_path, document_id="doc-complex")
    chunks = chunker.chunk_document(document)

    assert any(chunk.metadata.get("element_type") == "table" for chunk in chunks)
    assert any(chunk.metadata.get("element_type") == "figure_caption" for chunk in chunks)
    assert any("Page Summary:" in chunk.text for chunk in chunks)
    assert any("Table Title:" in chunk.text for chunk in chunks if chunk.metadata.get("element_type") == "table")
