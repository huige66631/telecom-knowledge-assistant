from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agent.router import KBFirstRouter
from app.agent.state import AgentState
from app.rag.retriever import KnowledgeRetriever
from app.services.document_tool_service import DocumentToolService
from app.services.generation_service import GenerationService
from app.services.query_rewrite_service import QueryRewriteService


class KnowledgeAgentGraph:
    """Lightweight KB-first orchestration for the MVP."""

    def __init__(self) -> None:
        self.retriever = KnowledgeRetriever()
        self.generator = GenerationService()
        self.document_tools = DocumentToolService()
        self.rewriter = QueryRewriteService(self.generator)
        self.router = KBFirstRouter()
        self.graph = self._build_graph().compile()

    def invoke(self, question: str) -> AgentState:
        return self.graph.invoke({"question": question})

    def invoke_with_context(
        self,
        question: str,
        conversation_summary: str,
        recent_turns: list[dict[str, str]] | None = None,
    ) -> AgentState:
        return self.graph.invoke(
            {
                "question": question,
                "conversation_summary": conversation_summary,
                "recent_turns": recent_turns or [],
            }
        )

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("answer", self._answer)
        graph.add_node("clarify", self._clarify)
        graph.add_node("out_of_scope", self._out_of_scope)
        graph.add_node("fallback", self._fallback)

        graph.set_entry_point("retrieve")
        graph.add_conditional_edges(
            "retrieve",
            self._route,
            {
                "answer": "answer",
                "clarify": "clarify",
                "out_of_scope": "out_of_scope",
                "fallback": "fallback",
            },
        )
        graph.add_edge("answer", END)
        graph.add_edge("clarify", END)
        graph.add_edge("out_of_scope", END)
        graph.add_edge("fallback", END)
        return graph

    def _retrieve(self, state: AgentState) -> AgentState:
        original_question = state["question"]
        conversation_summary = state.get("conversation_summary", "")
        recent_turns = state.get("recent_turns", [])

        rewrite_result = self.rewriter.rewrite_with_rules(
            question=original_question,
            conversation_summary=conversation_summary,
            recent_turns=recent_turns,
        )
        matches = self.retriever.search(rewrite_result.rewritten_question)
        chosen_result = rewrite_result
        page_evidence = self._expand_page_context(matches, original_question)
        section_evidence = self._expand_section_context(matches, original_question)
        table_evidence = self._extract_table_context(matches, original_question)
        figure_evidence = self._describe_figure_context(matches, original_question)

        if len(matches) < 1 and self.rewriter.should_try_llm_fallback(
            question=original_question,
            conversation_summary=conversation_summary,
            recent_turns=recent_turns,
        ):
            llm_result = self.rewriter.rewrite_with_llm(
                question=original_question,
                conversation_summary=conversation_summary,
                recent_turns=recent_turns,
            )
            if llm_result.rewritten_question != rewrite_result.rewritten_question:
                llm_matches = self.retriever.search(llm_result.rewritten_question)
                if len(llm_matches) > len(matches):
                    matches = llm_matches
                    chosen_result = llm_result
                    page_evidence = self._expand_page_context(matches, original_question)
                    section_evidence = self._expand_section_context(matches, original_question)
                    table_evidence = self._extract_table_context(matches, original_question)
                    figure_evidence = self._describe_figure_context(matches, original_question)

        return {
            "matches": matches,
            "page_evidence": page_evidence,
            "section_evidence": section_evidence,
            "table_evidence": table_evidence,
            "figure_evidence": figure_evidence,
            "retrieval_query": chosen_result.rewritten_question,
            "rewritten_question": chosen_result.rewritten_question,
            "rewrite_strategy": chosen_result.strategy,
        }

    def _route(self, state: AgentState) -> str:
        return self.router.decide(state)

    def _answer(self, state: AgentState) -> AgentState:
        try:
            evidence = self._merge_evidence(
                state.get("matches", []),
                state.get("page_evidence", []),
                state.get("section_evidence", []),
                state.get("table_evidence", []),
                state.get("figure_evidence", []),
            )
            answer = self.generator.generate_answer(
                state["question"],
                evidence,
                conversation_summary=state.get("conversation_summary", ""),
            )
            return {"answer": answer, "route": "answer", "used_fallback": False}
        except Exception:
            return self._fallback(state)

    def _clarify(self, state: AgentState) -> AgentState:
        return {
            "answer": "当前知识库里没有找到足够相关的资料。请补充更具体的模块名、章节名、参数名或关键词，我再继续检索。",
            "route": "clarify",
            "used_fallback": False,
        }

    def _out_of_scope(self, state: AgentState) -> AgentState:
        return {
            "answer": "这个问题看起来不属于当前知识库的资料范围。请尽量改成与产品手册、FAQ、技术规范或测试文档相关的问题。",
            "route": "out_of_scope",
            "used_fallback": False,
        }

    def _fallback(self, state: AgentState) -> AgentState:
        matches = self._merge_evidence(
            state.get("matches", []),
            state.get("page_evidence", []),
            state.get("section_evidence", []),
            state.get("table_evidence", []),
            state.get("figure_evidence", []),
        )
        if not matches:
            return {
                "answer": "暂时没有可返回的检索结果，请换一个更具体的问题。",
                "route": "fallback",
                "used_fallback": True,
            }

        answer_lines = [
            "模型生成暂时不可用，已回退为检索结果展示。下面是知识库中最相关的片段：",
        ]
        answer_lines.extend(
            f"{index}. [{match.source}] {match.text[:180].replace(chr(10), ' ')}"
            for index, match in enumerate(matches, start=1)
        )
        return {
            "answer": "\n".join(answer_lines),
            "route": "fallback",
            "used_fallback": True,
        }

    def _expand_page_context(self, matches: list, question: str) -> list:
        if not matches:
            return []
        if not self._needs_page_read(question, matches):
            return []

        first_match = matches[0]
        if first_match.page is None:
            return []

        return self.document_tools.read_page(source_name=first_match.source, page=first_match.page)[:4]

    def _expand_section_context(self, matches: list, question: str) -> list:
        if not matches:
            return []
        if not self._needs_section_read(question):
            return []

        for match in matches[:3]:
            section_title = match.section_title or ""
            if not section_title:
                continue

            section_chunks = self.document_tools.read_section(
                source_name=match.source,
                section_title=section_title,
                page=match.page,
            )
            if section_chunks:
                return section_chunks[:6]

        return []

    def _extract_table_context(self, matches: list, question: str) -> list:
        if not matches:
            return []
        if not self._needs_table_read(question, matches):
            return []

        first_match = matches[0]
        return self.document_tools.extract_tables(source_name=first_match.source, page=first_match.page)[:4]

    def _describe_figure_context(self, matches: list, question: str) -> list:
        if not matches:
            return []
        if not self._needs_figure_read(question, matches):
            return []

        first_match = matches[0]
        return self.document_tools.describe_figures(source_name=first_match.source, page=first_match.page)[:3]

    def _needs_page_read(self, question: str, matches: list) -> bool:
        if len(matches) <= 1:
            return True
        return any(keyword in question for keyword in ("整页", "本页", "这一页", "上下文", "章节", "说明"))

    def _needs_section_read(self, question: str) -> bool:
        return any(keyword in question for keyword in ("模块", "设计", "流程", "步骤", "组成", "实现"))

    def _needs_table_read(self, question: str, matches: list) -> bool:
        if any(match.element_type == "table" for match in matches):
            return True
        return any(keyword in question for keyword in ("表", "参数", "指标", "对比", "规格", "阈值"))

    def _needs_figure_read(self, question: str, matches: list) -> bool:
        if any(match.element_type == "figure_caption" for match in matches):
            return True
        return any(keyword in question for keyword in ("图", "拓扑", "结构图", "示意图", "架构图", "连接关系"))

    def _merge_evidence(self, *groups: list) -> list:
        merged = []
        seen = set()
        for group in groups:
            for item in group:
                if item.chunk_id in seen:
                    continue
                seen.add(item.chunk_id)
                merged.append(item)
        return merged[:8]
