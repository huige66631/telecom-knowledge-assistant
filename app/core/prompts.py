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


QUERY_REWRITE_SYSTEM_PROMPT = """
你是企业知识库检索前的 Query Rewrite 助手。

你的任务不是回答问题，而是把用户当前问题改写成更适合知识库检索的独立问题，要求：
1. 保留用户原意，不要扩写成新需求。
2. 如果当前问题依赖上下文，请补全代词、省略主语、简称或上一轮隐含对象。
3. 输出只保留一条改写后的检索问题，不要解释，不要加引号，不要分点。
4. 如果原问题已经足够独立清晰，就原样输出。
5. 改写结果尽量简洁，偏向企业文档检索表达。
""".strip()


FIGURE_DESCRIPTION_SYSTEM_PROMPT = """
你是企业技术文档中的图示理解助手。

你的任务是结合图注、章节上下文和页面摘要，对图表或结构图做简洁、可靠的描述，要求：
1. 只描述图中能确认的结构、连接关系或标签信息。
2. 如果只能根据图注和上下文判断，也要明确描述依据，不要编造不可见细节。
3. 输出偏技术文档风格，简洁清晰。
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


def build_query_rewrite_prompt(
    question: str,
    conversation_summary: str = "",
    recent_turns: list[dict[str, str]] | None = None,
) -> str:
    turn_blocks: list[str] = []
    for turn in (recent_turns or [])[-4:]:
        role = turn.get("role", "unknown")
        content = turn.get("content", "").strip()
        if content:
            turn_blocks.append(f"{role}: {content}")

    turn_text = "\n".join(turn_blocks) if turn_blocks else "无"
    summary_text = conversation_summary or "无"

    return f"""
会话摘要：
{summary_text}

最近对话：
{turn_text}

当前用户问题：
{question}

请输出改写后的检索问题：
""".strip()


def build_figure_description_prompt(
    figure_caption: str,
    page_summary: str = "",
    section_title: str = "",
) -> str:
    return f"""
图注：
{figure_caption or "无"}

所属章节：
{section_title or "无"}

页面摘要：
{page_summary or "无"}

请输出这张图的简洁说明：
""".strip()
