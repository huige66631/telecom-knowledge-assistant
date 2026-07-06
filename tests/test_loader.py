from pathlib import Path

from app.rag.loader import DocumentLoader


def test_loader_builds_structured_sections_from_text_file(tmp_path: Path) -> None:
    loader = DocumentLoader()
    file_path = tmp_path / "sample.md"
    file_path.write_text(
        "\n".join(
            [
                "1. Overview",
                "",
                "The switch supports SNMP and SSH for secure management.",
                "",
                "Table 1 Management Capabilities",
                "Protocol    Support    Notes",
                "SNMPv3      Yes        Secure monitoring",
                "Telnet      No         Disabled by default",
                "",
                "Figure 2 Topology",
                "Access switch uplinks to aggregation layer.",
            ]
        ),
        encoding="utf-8",
    )

    document = loader.load(file_path=file_path, document_id="doc-1")

    assert document.pages
    assert any(section.metadata.get("element_type") == "heading" for section in document.sections)
    assert any(section.metadata.get("element_type") == "table" for section in document.sections)
    assert any(section.metadata.get("element_type") == "figure_caption" for section in document.sections)
    assert any(section.metadata.get("element_type") == "page_summary" for section in document.sections)


def test_loader_filters_repeated_page_noise() -> None:
    loader = DocumentLoader()
    pages = loader._filter_repeated_page_noise(
        [
            loader._load_text_fixture(
                page_number=1,
                blocks=[
                    "Confidential",
                    "1. Overview",
                    "The switch supports SNMP.",
                ],
            ),
            loader._load_text_fixture(
                page_number=2,
                blocks=[
                    "Confidential",
                    "2. Security",
                    "SSH is enabled by default.",
                ],
            ),
        ]
    )

    assert all("Confidential" not in section.text for page in pages for section in page.sections)


def test_loader_does_not_promote_sentence_to_heading() -> None:
    loader = DocumentLoader()

    sections = loader._build_page_sections(
        "3.3 OFDM发射端模块设计\n\nOFDM 发射端由比特填充、调制映射、子载波装载、前导插入、IFFT 和\n\n循环前缀添加组成。",
        page_number=1,
    )

    assert sections[0].metadata["element_type"] == "heading"
    assert sections[1].metadata["element_type"] == "paragraph"
    assert sections[1].metadata["section_title"] == "3.3 OFDM发射端模块设计"


def test_loader_marks_toc_entries() -> None:
    loader = DocumentLoader()

    sections = loader._build_page_sections(
        "3.1 系统总体方案设计 ............................................................ 8\n\n3.2 语音输入与预处理模块设计 ................................................... 8",
        page_number=1,
    )

    assert all(section.metadata["element_type"] == "toc_entry" for section in sections)


def test_loader_builds_mineru_command_for_pipeline_backend(tmp_path: Path) -> None:
    loader = DocumentLoader()
    settings = loader.settings
    original_backend = settings.mineru_backend
    original_method = settings.mineru_method
    original_lang = settings.mineru_lang
    original_effort = settings.mineru_effort
    original_api_url = settings.mineru_api_url
    original_figure_vision = settings.figure_vision_enabled

    try:
        settings.mineru_backend = "pipeline"
        settings.mineru_method = "ocr"
        settings.mineru_lang = "ch"
        settings.mineru_effort = "high"
        settings.mineru_api_url = "http://127.0.0.1:9000"
        settings.figure_vision_enabled = True

        command = loader._build_mineru_command(
            file_path=tmp_path / "sample.pdf",
            output_root=tmp_path / "out",
        )

        assert "-b" in command and "pipeline" in command
        assert "-m" in command and "ocr" in command
        assert "-l" in command and "ch" in command
        assert "--api-url" in command and "http://127.0.0.1:9000" in command
        assert "--effort" not in command
        assert "--image-analysis" not in command
    finally:
        settings.mineru_backend = original_backend
        settings.mineru_method = original_method
        settings.mineru_lang = original_lang
        settings.mineru_effort = original_effort
        settings.mineru_api_url = original_api_url
        settings.figure_vision_enabled = original_figure_vision


def test_loader_builds_mineru_command_for_hybrid_backend(tmp_path: Path) -> None:
    loader = DocumentLoader()
    settings = loader.settings
    original_backend = settings.mineru_backend
    original_method = settings.mineru_method
    original_lang = settings.mineru_lang
    original_effort = settings.mineru_effort
    original_api_url = settings.mineru_api_url
    original_figure_vision = settings.figure_vision_enabled

    try:
        settings.mineru_backend = "hybrid-http-client"
        settings.mineru_method = "auto"
        settings.mineru_lang = "ch"
        settings.mineru_effort = "high"
        settings.mineru_api_url = ""
        settings.figure_vision_enabled = True

        command = loader._build_mineru_command(
            file_path=tmp_path / "sample.pdf",
            output_root=tmp_path / "out",
        )

        assert "-b" in command and "hybrid-http-client" in command
        assert "--effort" in command and "high" in command
        assert "--image-analysis" in command
        assert "-l" not in command
    finally:
        settings.mineru_backend = original_backend
        settings.mineru_method = original_method
        settings.mineru_lang = original_lang
        settings.mineru_effort = original_effort
        settings.mineru_api_url = original_api_url
        settings.figure_vision_enabled = original_figure_vision
