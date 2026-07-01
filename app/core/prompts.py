from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.rag.retriever import RetrievedChunk


SYSTEM_PROMPT = """
你是一个面向通信/电子行业企业资料场景的知识助手。

你的任务是基于提供的知识库片段回答问题，要求：
1. 只能依据已提供的检索片段回答，不能编造。
2. 如果证据不足，要明确说明“知识库资料不足”。
3. 优先使用简洁、专业、偏企业文档风格的中文表达。
4. 回答中尽量引用片段编号，例如 [1]、[2]。
5. 不要声称自己看过未提供的文档。
6. 如果用户是在追问，请结合会话上下文理解代词、缩写和省略表达。
""".strip()


def build_rag_user_prompt(
    question: str,
    matches: list[RetrievedChunk],
    conversation_summary: str = "",
) -> str:
    evidence_blocks: list[str] = []

    for index, match in enumerate(matches, start=1):
        location = f"page={match.page}" if match.page is not None else "page=n/a"
        evidence_blocks.append(
            "\n".join(
                [
                    f"[{index}] source={match.source}",
                    f"[{index}] type={match.source_type}",
                    f"[{index}] location={location}",
                    f"[{index}] content={match.text}",
                ]
            )
        )

    evidence_text = "\n\n".join(evidence_blocks)
    memory_block = conversation_summary or "无"

    return f"""
会话上下文摘要：
{memory_block}

用户问题：
{question}

知识库检索片段：
{evidence_text}

请输出一段最终回答：
- 先直接回答问题
- 再在句中或句末标注引用编号，如 [1]
- 若多个片段共同支持一个结论，可以写成 [1][2]
- 若无法根据证据回答，请明确说明证据不足
""".strip()
