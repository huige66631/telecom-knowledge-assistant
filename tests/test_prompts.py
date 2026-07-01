from app.core.prompts import build_rag_user_prompt
from app.rag.retriever import RetrievedChunk


def test_build_rag_user_prompt_contains_sources() -> None:
    prompt = build_rag_user_prompt(
        question="某设备支持哪些协议？",
        matches=[
            RetrievedChunk(
                chunk_id="chunk-1",
                text="设备支持 SNMP、SSH 和 Telnet。",
                source="manual.pdf",
                source_type="pdf",
                source_path="data/raw/manual.pdf",
                page=3,
                distance=0.12,
            )
        ],
    )

    assert "某设备支持哪些协议" in prompt
    assert "manual.pdf" in prompt
    assert "SNMP" in prompt
