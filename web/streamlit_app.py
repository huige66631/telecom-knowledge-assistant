from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


st.set_page_config(
    page_title="Telecom Knowledge Assistant",
    page_icon=":material/hub:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def init_state() -> None:
    defaults = {
        "chat_history": [],
        "active_session_id": None,
        "latest_response": None,
        "ingest_results": [],
        "last_upload_errors": [],
        "session_restored": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #edf3f9;
            --surface: rgba(255, 255, 255, 0.88);
            --surface-strong: #ffffff;
            --surface-soft: #f6f9fc;
            --ink: #13253a;
            --ink-soft: #49627b;
            --line: rgba(19, 37, 58, 0.08);
            --brand: #0e4f8a;
            --brand-strong: #0a3b68;
            --accent: #18a0a8;
            --success: #1e8e5a;
            --warning: #c57918;
            --danger: #c74646;
            --shadow: 0 20px 40px rgba(20, 45, 74, 0.08);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(24, 160, 168, 0.08), transparent 30%),
                radial-gradient(circle at top right, rgba(14, 79, 138, 0.10), transparent 28%),
                linear-gradient(180deg, #eff5fa 0%, #e9f0f7 100%);
        }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }

        h1, h2, h3, h4 {
            color: var(--ink);
            letter-spacing: -0.02em;
        }

        .app-header {
            background: linear-gradient(135deg, #0d3f6d 0%, #0f5d9d 60%, #1890b3 100%);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 28px;
            color: white;
            padding: 1.5rem 1.6rem;
            box-shadow: 0 26px 54px rgba(13, 63, 109, 0.22);
            margin-bottom: 1.2rem;
        }

        .header-topline {
            font-size: 0.82rem;
            opacity: 0.76;
            font-weight: 700;
            margin-bottom: 0.55rem;
        }

        .header-title {
            font-size: 2.15rem;
            font-weight: 750;
            line-height: 1.08;
            margin-bottom: 0.75rem;
            text-wrap: balance;
        }

        .header-copy {
            max-width: 74ch;
            font-size: 0.98rem;
            line-height: 1.65;
            opacity: 0.92;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 0.8rem;
            margin-top: 1.2rem;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 18px;
            padding: 0.9rem 1rem;
            backdrop-filter: blur(10px);
        }

        .stat-label {
            font-size: 0.78rem;
            opacity: 0.75;
            margin-bottom: 0.35rem;
        }

        .stat-value {
            font-size: 1.04rem;
            font-weight: 700;
        }

        .section-title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 0.25rem;
        }

        .section-copy {
            font-size: 0.88rem;
            color: var(--ink-soft);
            line-height: 1.55;
            margin-bottom: 0.85rem;
        }

        .micro-label {
            font-size: 0.78rem;
            font-weight: 700;
            color: var(--ink-soft);
            margin-bottom: 0.55rem;
            letter-spacing: 0.01em;
        }

        .pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.2rem;
        }

        .pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.42rem 0.72rem;
            border-radius: 999px;
            background: #eef5fb;
            border: 1px solid #d7e5f3;
            color: var(--brand-strong);
            font-size: 0.82rem;
            font-weight: 600;
        }

        .subtle-box {
            background: var(--surface-soft);
            border: 1px solid #dce7f2;
            border-radius: 18px;
            padding: 0.9rem 0.95rem;
        }

        .sample-list {
            margin: 0;
            padding-left: 1.1rem;
            color: var(--ink-soft);
            line-height: 1.75;
            font-size: 0.9rem;
        }

        .stChatMessage {
            background: transparent;
        }

        .empty-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.8rem;
            margin-top: 0.8rem;
        }

        .empty-card {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid #dbe8f2;
            border-radius: 18px;
            padding: 0.9rem 0.95rem;
        }

        .empty-card-title {
            font-size: 0.9rem;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 0.35rem;
        }

        .empty-card-copy {
            color: var(--ink-soft);
            font-size: 0.88rem;
            line-height: 1.55;
        }

        .detail-card {
            background: #f8fbfd;
            border: 1px solid #dbe8f2;
            border-radius: 18px;
            padding: 0.9rem 0.95rem;
            margin-bottom: 0.7rem;
        }

        .detail-title {
            color: var(--ink);
            font-size: 0.92rem;
            font-weight: 700;
            margin-bottom: 0.3rem;
        }

        .detail-meta {
            color: var(--ink-soft);
            font-size: 0.8rem;
            margin-bottom: 0.35rem;
        }

        .detail-copy {
            color: #24384f;
            font-size: 0.92rem;
            line-height: 1.6;
        }

        .stButton > button {
            border-radius: 14px;
            border: 1px solid #cad9e7;
            background: white;
            color: var(--ink);
            font-weight: 650;
            min-height: 2.8rem;
        }

        .stButton > button:hover {
            border-color: #9fbddd;
            color: var(--brand-strong);
        }

        .stFileUploader > div {
            background: transparent !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def check_backend() -> tuple[bool, dict[str, Any] | str]:
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        response.raise_for_status()
        return True, response.json()
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


def sync_query_params() -> None:
    session_id = st.session_state.active_session_id
    if session_id:
        st.query_params["session_id"] = session_id
    elif "session_id" in st.query_params:
        del st.query_params["session_id"]


def restore_session_from_query_params() -> None:
    if st.session_state.session_restored:
        return

    session_id = st.query_params.get("session_id")
    if not session_id:
        st.session_state.session_restored = True
        return

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/chat/session/{session_id}",
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        st.session_state.active_session_id = payload.get("session_id")
        st.session_state.chat_history = payload.get("turns", [])
        st.session_state.latest_response = {
            "session_id": payload.get("session_id"),
            "memory_summary": payload.get("memory_summary"),
            "citations": [],
            "matched_chunks": 0,
            "route": "restored_session",
        }
    except Exception:
        st.session_state.active_session_id = None
        st.session_state.chat_history = []
    finally:
        st.session_state.session_restored = True


def upload_documents(uploaded_files: list[Any]) -> None:
    results: list[dict[str, Any]] = []
    failures: list[str] = []

    for uploaded_file in uploaded_files:
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/v1/ingest/file",
                files={
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type or "application/octet-stream",
                    )
                },
                timeout=120,
            )
            response.raise_for_status()
            results.append(response.json())
        except Exception as exc:  # pragma: no cover
            failures.append(f"{uploaded_file.name}: {exc}")

    if results:
        st.session_state.ingest_results = results + st.session_state.ingest_results
    st.session_state.last_upload_errors = failures


def send_question(question: str) -> None:
    st.session_state.chat_history.append({"role": "user", "content": question})
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/chat",
            json={
                "question": question,
                "session_id": st.session_state.active_session_id,
            },
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        st.session_state.active_session_id = payload.get("session_id")
        st.session_state.latest_response = payload
        sync_query_params()
        st.session_state.chat_history.append(
            {"role": "assistant", "content": payload.get("answer", "")}
        )
    except Exception as exc:  # pragma: no cover
        st.session_state.chat_history.append(
            {"role": "assistant", "content": f"请求失败：{exc}"}
        )


def render_header(backend_ok: bool) -> None:
    st.markdown(
        f"""
        <div class="app-header">
            <div class="header-topline">通信 / 电子行业企业知识助手</div>
            <div class="header-title">让产品手册、FAQ 与测试规范真正变成可追问、可引用的知识工作台</div>
            <div class="header-copy">
                这个 Demo 强调企业资料场景，而不是通用聊天。它会先构建本地知识库，再通过
                Hybrid RAG 和 KB-first Agent 路由完成问答、引用和连续追问。
            </div>
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-label">后端状态</div>
                    <div class="stat-value">{"在线" if backend_ok else "未连接"}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">当前链路</div>
                    <div class="stat-value">Hybrid RAG + Query Rewrite</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">已上传文档</div>
                    <div class="stat-value">{len(st.session_state.ingest_results)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">当前会话</div>
                    <div class="stat-value">{st.session_state.active_session_id or "未开始"}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_left_panel(backend_ok: bool, backend_payload: dict[str, Any] | str) -> None:
    st.markdown('<div class="section-title">知识库工作台</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">先把资料送进入库链路，再开始问答。这里更像一块资料台，而不是普通上传框。</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="micro-label">系统状态</div>', unsafe_allow_html=True)
    if backend_ok:
        st.success(backend_payload)
    else:
        st.error(f"后端连接失败：{backend_payload}")

    st.markdown('<div class="micro-label">上传资料并建立索引</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "支持 PDF、DOCX、TXT、Markdown，可一次选择多份资料",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    col_upload, col_clear = st.columns([1.35, 0.85], gap="small")
    with col_upload:
        if st.button("上传并建立索引", use_container_width=True):
            if not uploaded_files:
                st.warning("请先选择至少一份资料。")
            else:
                upload_documents(uploaded_files)
    with col_clear:
        if st.button("清空会话", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.active_session_id = None
            st.session_state.latest_response = None
            st.session_state.session_restored = True
            sync_query_params()
            st.rerun()

    if st.session_state.ingest_results:
        st.markdown('<div class="micro-label">最近入库结果</div>', unsafe_allow_html=True)
        for result in st.session_state.ingest_results[:4]:
            st.markdown(
                f"""
                <div class="detail-card">
                    <div class="detail-title">{result.get("document_id", "document")}</div>
                    <div class="detail-meta">{result.get("message", "")}</div>
                    <div class="detail-copy">处理文件路径：{result.get("source_path", "")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if st.session_state.last_upload_errors:
        st.markdown('<div class="micro-label">上传异常</div>', unsafe_allow_html=True)
        for error in st.session_state.last_upload_errors:
            st.error(error)

    st.markdown('<div class="micro-label">推荐演示路径</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="subtle-box">
            <ol class="sample-list">
                <li>先上传两份样例资料，建立基础知识库。</li>
                <li>问“某型号交换机支持哪些管理协议？”看基础检索问答。</li>
                <li>继续问 “SNMP 有哪些限制？” 看引用回答。</li>
                <li>再追问 “热插拔恢复时间要求是多少？” 看会话记忆。</li>
            </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="micro-label" style="margin-top:0.9rem;">内置样例文档</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pill-row"><span class="pill">device_management_guide.md</span><span class="pill">interface_stability_test_spec.md</span></div>',
        unsafe_allow_html=True,
    )


def render_chat_panel() -> None:
    latest = st.session_state.latest_response or {}
    has_history = bool(st.session_state.chat_history)

    st.markdown('<div class="section-title">对话工作区</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">刷新页面后会自动尝试恢复同一个 session 的对话记录和记忆摘要。</div>',
        unsafe_allow_html=True,
    )

    if not has_history:
        st.markdown(
            """
            <div class="subtle-box">
                <div class="detail-title">还没有开始对话</div>
                <div class="detail-copy">
                    先上传一到两份资料，然后从“管理协议、测试规范、接口恢复、配置限制”这类问题开始。
                </div>
            </div>
            <div class="empty-grid">
                <div class="empty-card">
                    <div class="empty-card-title">推荐第一个问题</div>
                    <div class="empty-card-copy">某型号交换机支持哪些管理协议？</div>
                </div>
                <div class="empty-card">
                    <div class="empty-card-title">推荐追问</div>
                    <div class="empty-card-copy">SNMP 有哪些限制？</div>
                </div>
                <div class="empty-card">
                    <div class="empty-card-title">推荐测试类问题</div>
                    <div class="empty-card-copy">接口稳定性测试里对丢包率有什么要求？</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    for item in st.session_state.chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])

    question = st.chat_input("输入一个与通信/电子行业资料相关的问题")
    if question:
        send_question(question)
        st.rerun()

    detail_tabs = st.tabs(["引用证据", "路由信息", "会话记忆"])

    with detail_tabs[0]:
        citations = latest.get("citations", [])
        if not citations:
            st.caption("当前还没有可展示的引用证据。")
        else:
            for citation in citations:
                meta = []
                if citation.get("page") is not None:
                    meta.append(f"页码：{citation['page']}")
                if citation.get("keyword_score") is not None:
                    meta.append(f"关键词分：{citation['keyword_score']:.2f}")
                if citation.get("fused_score") is not None:
                    meta.append(f"融合分：{citation['fused_score']:.4f}")

                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-title">{citation.get("source", "unknown")}</div>
                        <div class="detail-meta">{' | '.join(meta) if meta else '未提供额外元信息'}</div>
                        <div class="detail-copy">{citation.get("snippet", "")}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with detail_tabs[1]:
        if latest:
            st.json(
                {
                    "route": latest.get("route"),
                    "matched_chunks": latest.get("matched_chunks"),
                    "session_id": latest.get("session_id"),
                    "rewrite_strategy": latest.get("rewrite_strategy"),
                    "rewritten_question": latest.get("rewritten_question"),
                }
            )
        else:
            st.caption("还没有路由信息。")

    with detail_tabs[2]:
        summary = latest.get("memory_summary") if latest else None
        if summary:
            st.markdown(
                f"""
                <div class="detail-card">
                    <div class="detail-title">当前会话摘要</div>
                    <div class="detail-copy">{summary}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.caption("当前会话还没有生成摘要。")


def main() -> None:
    init_state()
    inject_styles()
    restore_session_from_query_params()
    backend_ok, backend_payload = check_backend()

    render_header(backend_ok)

    left_col, right_col = st.columns([0.9, 1.35], gap="large")
    with left_col:
        render_left_panel(backend_ok, backend_payload)
    with right_col:
        render_chat_panel()


main()
