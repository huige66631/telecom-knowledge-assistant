from pathlib import Path

from app.rag.loader import DocumentLoader


def test_mineru_content_list_mapping_builds_structured_pages(tmp_path: Path) -> None:
    loader = DocumentLoader()
    output_root = tmp_path
    (output_root / "images").mkdir()

    content_list = [
        {
            "type": "text",
            "text": "1 Introduction",
            "text_level": 1,
            "page_idx": 0,
            "bbox": [10, 10, 300, 60],
        },
        {
            "type": "text",
            "text": "This page describes the product architecture.",
            "page_idx": 0,
            "bbox": [10, 80, 400, 140],
        },
        {
            "type": "table",
            "table_caption": ["Table 1 Performance Targets"],
            "table_body": "<table><tr><td>Recovery</td><td>30s</td></tr></table>",
            "table_footnote": ["Measured after hot swap."],
            "img_path": "images/table-1.png",
            "page_idx": 1,
            "bbox": [10, 120, 500, 500],
        },
        {
            "type": "image",
            "image_caption": ["Figure 2 Topology Diagram"],
            "image_footnote": ["Dual uplink from access to aggregation."],
            "img_path": "images/figure-2.png",
            "page_idx": 1,
            "bbox": [10, 520, 500, 900],
        },
    ]

    pages = loader._build_pages_from_mineru_content(content_list=content_list, output_root=output_root)

    assert len(pages) == 2
    assert pages[0].sections[0].metadata["element_type"] == "heading"
    assert pages[1].page_type == "table_heavy"
    assert any(section.metadata.get("element_type") == "table" for section in pages[1].sections)
    assert any(section.metadata.get("element_type") == "figure_caption" for section in pages[1].sections)
