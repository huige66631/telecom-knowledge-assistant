from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agent.router import KBFirstRouter
from app.agent.state import AgentState
from app.rag.retriever import KnowledgeRetriever
from app.services.generation_service import GenerationService
from app.services.query_rewrite_service import QueryRewriteService


class KnowledgeAgentGraph:
    """Lightweight KB-first orchestration for the MVP."""

    def __init__(self) -> None:
        self.retriever = KnowledgeRetriever()
        self.generator = GenerationService()
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

        return {
            "matches": matches,
            "retrieval_query": chosen_result.rewritten_question,
            "rewritten_question": chosen_result.rewritten_question,
            "rewrite_strategy": chosen_result.strategy,
        }

    def _route(self, state: AgentState) -> str:
        return self.router.decide(state)

    def _answer(self, state: AgentState) -> AgentState:
        try:
            answer = self.generator.generate_answer(
                state["question"],
                state.get("matches", []),
                conversation_summary=state.get("conversation_summary", ""),
            )
            return {"answer": answer, "route": "answer", "used_fallback": False}
        except Exception:
            return self._fallback(state)

    def _clarify(self, state: AgentState) -> AgentState:
        return {
            "answer": (
                "当前知识库里没有找到足够相关的资料。请补充更具体的设备型号、协议名称、"
                "功能模块或文档关键词，我再继续检索。"
            ),
            "route": "clarify",
            "used_fallback": False,
        }

    def _out_of_scope(self, state: AgentState) -> AgentState:
        return {
            "answer": (
                "这个问题看起来不属于当前通信/电子行业企业资料知识库的范围。"
                "如果你希望我回答，请尽量改成与产品手册、FAQ、技术规范或测试文档相关的问题。"
            ),
            "route": "out_of_scope",
            "used_fallback": False,
        }

    def _fallback(self, state: AgentState) -> AgentState:
        matches = state.get("matches", [])
        if not matches:
            return {
                "answer": "暂时没有可回退的检索结果，请换一个更具体的问题。",
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
