from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(
    page_title="Enterprise Knowledge Assistant",
    page_icon=":material/hub:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


HEADER_TOPLINE = "\u4f01\u4e1a\u77e5\u8bc6\u52a9\u624b"
HEADER_TITLE = "\u8ba9\u4ea7\u54c1\u624b\u518c\u3001FAQ \u4e0e\u6d4b\u8bd5\u89c4\u8303\u771f\u6b63\u53d8\u6210\u53ef\u8ffd\u95ee\u3001\u53ef\u5f15\u7528\u7684\u77e5\u8bc6\u5de5\u4f5c\u53f0"
LABEL_BACKEND = "\u540e\u7aef\u72b6\u6001"
LABEL_ROUTE = "\u5f53\u524d\u94fe\u8def"
LABEL_DOCS = "\u5df2\u4e0a\u4f20\u6587\u6863"
LABEL_SESSION = "\u5f53\u524d\u4f1a\u8bdd"
TEXT_ONLINE = "\u5728\u7ebf"
TEXT_OFFLINE = "\u672a\u8fde\u63a5"
TEXT_NOT_STARTED = "\u672a\u5f00\u59cb"

TITLE_KB = "\u77e5\u8bc6\u5e93\u5de5\u4f5c\u53f0"
COPY_KB = "\u5148\u628a\u8d44\u6599\u9001\u8fdb\u5165\u5e93\u94fe\u8def\uff0c\u518d\u5f00\u59cb\u95ee\u7b54\u3002\u8fd9\u91cc\u66f4\u50cf\u4e00\u5757\u8d44\u6599\u53f0\uff0c\u800c\u4e0d\u662f\u666e\u901a\u4e0a\u4f20\u6846\u3002"
LABEL_SYSTEM = "\u7cfb\u7edf\u72b6\u6001"
LABEL_UPLOAD = "\u4e0a\u4f20\u8d44\u6599\u5e76\u5efa\u7acb\u7d22\u5f15"
UPLOAD_HELP = "\u652f\u6301 PDF\u3001DOCX\u3001TXT\u3001Markdown\uff0c\u53ef\u4e00\u6b21\u9009\u62e9\u591a\u4efd\u8d44\u6599"
BTN_UPLOAD = "\u4e0a\u4f20\u5e76\u5efa\u7acb\u7d22\u5f15"
BTN_CONFIRM_UPLOAD = "\u786e\u8ba4\u4e0a\u4f20"
BTN_CLEAR = "\u6e05\u7a7a\u4f1a\u8bdd"
WARN_PICK_FILE = "\u8bf7\u5148\u9009\u62e9\u81f3\u5c11\u4e00\u4efd\u8d44\u6599\u3002"
LABEL_INGEST_RESULT = "\u6700\u8fd1\u5165\u5e93\u7ed3\u679c"
LABEL_UPLOAD_ERRORS = "\u4e0a\u4f20\u5f02\u5e38"
LABEL_DEMO_PATH = "\u63a8\u8350\u6f14\u793a\u8def\u5f84"
LABEL_SAMPLE_DOCS = "\u5185\u7f6e\u6837\u4f8b\u6587\u6863"
TEXT_SOURCE_PATH = "\u5904\u7406\u6587\u4ef6\u8def\u5f84\uff1a"
DEMO_STEPS = [
    "\u5148\u4e0a\u4f20\u4e24\u4efd\u6837\u4f8b\u8d44\u6599\uff0c\u5efa\u7acb\u57fa\u7840\u77e5\u8bc6\u5e93\u3002",
    "\u95ee\u201c\u67d0\u578b\u53f7\u4ea4\u6362\u673a\u652f\u6301\u54ea\u4e9b\u7ba1\u7406\u534f\u8bae\uff1f\u201d\u770b\u57fa\u7840\u68c0\u7d22\u95ee\u7b54\u3002",
    "\u7ee7\u7eed\u95ee\u201cSNMP \u6709\u54ea\u4e9b\u9650\u5236\uff1f\u201d\u770b\u5f15\u7528\u56de\u7b54\u3002",
    "\u518d\u8ffd\u95ee\u201c\u70ed\u63d2\u62d4\u6062\u590d\u65f6\u95f4\u8981\u6c42\u662f\u591a\u5c11\uff1f\u201d\u770b\u4f1a\u8bdd\u8bb0\u5fc6\u3002",
]

TITLE_CHAT = "\u5bf9\u8bdd\u5de5\u4f5c\u533a"
COPY_CHAT = "\u5237\u65b0\u9875\u9762\u540e\u4f1a\u81ea\u52a8\u5c1d\u8bd5\u6062\u590d\u540c\u4e00\u4e2a session \u7684\u5bf9\u8bdd\u8bb0\u5f55\u548c\u8bb0\u5fc6\u6458\u8981\u3002"
EMPTY_TITLE = "\u8fd8\u6ca1\u6709\u5f00\u59cb\u5bf9\u8bdd"
EMPTY_COPY = "\u5148\u4e0a\u4f20\u4e00\u5230\u4e24\u4efd\u8d44\u6599\uff0c\u7136\u540e\u4ece\u201c\u7ba1\u7406\u534f\u8bae\u3001\u6d4b\u8bd5\u89c4\u8303\u3001\u63a5\u53e3\u6062\u590d\u3001\u914d\u7f6e\u9650\u5236\u201d\u8fd9\u7c7b\u95ee\u9898\u5f00\u59cb\u3002"
CARD1_TITLE = "\u63a8\u8350\u7b2c\u4e00\u4e2a\u95ee\u9898"
CARD1_COPY = "\u67d0\u578b\u53f7\u4ea4\u6362\u673a\u652f\u6301\u54ea\u4e9b\u7ba1\u7406\u534f\u8bae\uff1f"
CARD2_TITLE = "\u63a8\u8350\u8ffd\u95ee"
CARD2_COPY = "SNMP \u6709\u54ea\u4e9b\u9650\u5236\uff1f"
CARD3_TITLE = "\u63a8\u8350\u6d4b\u8bd5\u7c7b\u95ee\u9898"
CARD3_COPY = "\u63a5\u53e3\u7a33\u5b9a\u6027\u6d4b\u8bd5\u91cc\u5bf9\u4e22\u5305\u7387\u6709\u4ec0\u4e48\u8981\u6c42\uff1f"

TAB_CITATION = "\u5f15\u7528\u8bc1\u636e"
TAB_ROUTE = "\u8def\u7531\u4fe1\u606f"
TAB_MEMORY = "\u4f1a\u8bdd\u8bb0\u5fc6"
TEXT_NO_CITATION = "\u5f53\u524d\u8fd8\u6ca1\u6709\u53ef\u5c55\u793a\u7684\u5f15\u7528\u8bc1\u636e\u3002"
TEXT_NO_ROUTE = "\u8fd8\u6ca1\u6709\u8def\u7531\u4fe1\u606f\u3002"
TEXT_MEMORY_TITLE = "\u5f53\u524d\u4f1a\u8bdd\u6458\u8981"
TEXT_NO_MEMORY = "\u5f53\u524d\u4f1a\u8bdd\u8fd8\u6ca1\u6709\u751f\u6210\u6458\u8981\u3002"
TEXT_PAGE = "\u9875\u7801\uff1a"
TEXT_KEYWORD_SCORE = "\u5173\u952e\u8bcd\u5206\uff1a"
TEXT_FUSED_SCORE = "\u878d\u5408\u5206\uff1a"
TEXT_NO_META = "\u672a\u63d0\u4f9b\u989d\u5916\u5143\u4fe1\u606f"
TEXT_REQUEST_FAILED = "\u8bf7\u6c42\u5931\u8d25\uff1a"
TEXT_BACKEND_FAILED = "\u540e\u7aef\u8fde\u63a5\u5931\u8d25\uff1a"


def resolve_api_base_url() -> str:
    env_url = os.getenv("API_BASE_URL")
    if env_url:
        return env_url

    runtime_file = Path(__file__).resolve().parents[1] / "run-logs" / "runtime.json"
    if runtime_file.exists():
        try:
            payload = json.loads(runtime_file.read_text(encoding="utf-8"))
            runtime_url = payload.get("api_base_url")
            if isinstance(runtime_url, str) and runtime_url.strip():
                return runtime_url.strip()
        except Exception:
            pass

    return "http://127.0.0.1:8000"


API_BASE_URL = resolve_api_base_url()


def get_session_runtime_file() -> Path:
    return Path(__file__).resolve().parents[1] / "run-logs" / "last_session.json"


def discover_healthy_api_base_url() -> str:
    candidates: list[str] = []

    runtime_candidate = resolve_api_base_url()
    if runtime_candidate:
        candidates.append(runtime_candidate)

    for port in range(8000, 8011):
        candidate = f"http://127.0.0.1:{port}"
        if candidate not in candidates:
            candidates.append(candidate)

    for candidate in candidates:
        try:
            response = requests.get(f"{candidate}/health", timeout=1.5)
            response.raise_for_status()
            return candidate
        except Exception:
            continue

    return runtime_candidate


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


def load_persisted_session_id() -> str | None:
    runtime_file = get_session_runtime_file()
    if not runtime_file.exists():
        return None

    try:
        payload = json.loads(runtime_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    session_id = payload.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()
    return None


def persist_session_id(session_id: str | None) -> None:
    runtime_file = get_session_runtime_file()
    runtime_file.parent.mkdir(parents=True, exist_ok=True)

    if not session_id:
        runtime_file.unlink(missing_ok=True)
        return

    runtime_file.write_text(
        json.dumps({"session_id": session_id}, ensure_ascii=False),
        encoding="utf-8",
    )


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
            letter-spacing: 0;
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

        .upload-hint {
            min-height: 2.8rem;
            display: flex;
            align-items: center;
            padding: 0.78rem 0.95rem;
            border-radius: 14px;
            border: 1px solid #dce7f2;
            background: rgba(255, 255, 255, 0.72);
            color: var(--ink-soft);
            font-size: 0.86rem;
            line-height: 1.45;
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

        .stFileUploader small,
        .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"],
        .stFileUploader [data-testid="stFileUploaderDropzone"] > div:nth-child(2) {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def check_backend() -> tuple[bool, dict[str, Any] | str]:
    global API_BASE_URL
    API_BASE_URL = discover_healthy_api_base_url()
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
        persist_session_id(session_id)
    elif "session_id" in st.query_params:
        del st.query_params["session_id"]
        persist_session_id(None)


def restore_session() -> None:
    if st.session_state.session_restored:
        return

    session_id = st.query_params.get("session_id") or load_persisted_session_id()
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
        sync_query_params()
    except Exception:
        st.session_state.active_session_id = None
        st.session_state.chat_history = []
        st.session_state.latest_response = None
        persist_session_id(None)
        if "session_id" in st.query_params:
            del st.query_params["session_id"]
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
                timeout=300,
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
            {"role": "assistant", "content": TEXT_REQUEST_FAILED + str(exc)}
        )


def render_header(backend_ok: bool) -> None:
    st.markdown(
        f"""
        <div class="app-header">
            <div class="header-topline">{HEADER_TOPLINE}</div>
            <div class="header-title">{HEADER_TITLE}</div>
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-label">{LABEL_BACKEND}</div>
                    <div class="stat-value">{TEXT_ONLINE if backend_ok else TEXT_OFFLINE}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">{LABEL_ROUTE}</div>
                    <div class="stat-value">Hybrid RAG + Query Rewrite</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">{LABEL_DOCS}</div>
                    <div class="stat-value">{len(st.session_state.ingest_results)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">{LABEL_SESSION}</div>
                    <div class="stat-value">{st.session_state.active_session_id or TEXT_NOT_STARTED}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_left_panel(backend_ok: bool, backend_payload: dict[str, Any] | str) -> None:
    st.markdown(f'<div class="section-title">{TITLE_KB}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-copy">{COPY_KB}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="micro-label">{LABEL_SYSTEM}</div>', unsafe_allow_html=True)
    if backend_ok:
        st.success(backend_payload)
    else:
        st.error(TEXT_BACKEND_FAILED + str(backend_payload))

    st.markdown(f'<div class="micro-label">{LABEL_UPLOAD}</div>', unsafe_allow_html=True)
    col_upload, col_hint = st.columns([0.95, 1.45], gap="small")
    with col_upload:
        with st.popover(BTN_UPLOAD, use_container_width=True):
            uploaded_files = st.file_uploader(
                "\u9009\u62e9\u8d44\u6599",
                type=["pdf", "docx", "txt", "md"],
                accept_multiple_files=True,
                key="upload_files",
            )
            st.caption(UPLOAD_HELP)
            if st.button(BTN_CONFIRM_UPLOAD, use_container_width=True, key="confirm_upload"):
                if not uploaded_files:
                    st.warning(WARN_PICK_FILE)
                else:
                    upload_documents(uploaded_files)
                    st.rerun()
    with col_hint:
        st.markdown(f'<div class="upload-hint">{UPLOAD_HELP}</div>', unsafe_allow_html=True)

    if st.button(BTN_CLEAR, use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.active_session_id = None
        st.session_state.latest_response = None
        st.session_state.session_restored = True
        sync_query_params()
        st.rerun()

    if st.session_state.ingest_results:
        st.markdown(f'<div class="micro-label">{LABEL_INGEST_RESULT}</div>', unsafe_allow_html=True)
        for result in st.session_state.ingest_results[:4]:
            st.markdown(
                f"""
                <div class="detail-card">
                    <div class="detail-title">{result.get("document_id", "document")}</div>
                    <div class="detail-meta">{result.get("message", "")}</div>
                    <div class="detail-copy">{TEXT_SOURCE_PATH}{result.get("source_path", "")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if st.session_state.last_upload_errors:
        st.markdown(f'<div class="micro-label">{LABEL_UPLOAD_ERRORS}</div>', unsafe_allow_html=True)
        for error in st.session_state.last_upload_errors:
            st.error(error)

    steps_html = "".join(f"<li>{step}</li>" for step in DEMO_STEPS)
    st.markdown(f'<div class="micro-label">{LABEL_DEMO_PATH}</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="subtle-box">
            <ol class="sample-list">
                {steps_html}
            </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="micro-label" style="margin-top:0.9rem;">{LABEL_SAMPLE_DOCS}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="pill-row"><span class="pill">device_management_guide.md</span><span class="pill">interface_stability_test_spec.md</span></div>',
        unsafe_allow_html=True,
    )


def render_chat_panel() -> None:
    latest = st.session_state.latest_response or {}
    has_history = bool(st.session_state.chat_history)

    st.markdown(f'<div class="section-title">{TITLE_CHAT}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-copy">{COPY_CHAT}</div>', unsafe_allow_html=True)

    if not has_history:
        st.markdown(
            f"""
            <div class="subtle-box">
                <div class="detail-title">{EMPTY_TITLE}</div>
                <div class="detail-copy">{EMPTY_COPY}</div>
            </div>
            <div class="empty-grid">
                <div class="empty-card">
                    <div class="empty-card-title">{CARD1_TITLE}</div>
                    <div class="empty-card-copy">{CARD1_COPY}</div>
                </div>
                <div class="empty-card">
                    <div class="empty-card-title">{CARD2_TITLE}</div>
                    <div class="empty-card-copy">{CARD2_COPY}</div>
                </div>
                <div class="empty-card">
                    <div class="empty-card-title">{CARD3_TITLE}</div>
                    <div class="empty-card-copy">{CARD3_COPY}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    for item in st.session_state.chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])

    question = st.chat_input("\u8bf7\u8f93\u5165\u95ee\u9898")
    if question:
        send_question(question)
        st.rerun()

    detail_tabs = st.tabs([TAB_CITATION, TAB_ROUTE, TAB_MEMORY])

    with detail_tabs[0]:
        citations = latest.get("citations", [])
        if not citations:
            st.caption(TEXT_NO_CITATION)
        else:
            for citation in citations:
                meta = []
                if citation.get("page") is not None:
                    meta.append(f"{TEXT_PAGE}{citation['page']}")
                if citation.get("keyword_score") is not None:
                    meta.append(f"{TEXT_KEYWORD_SCORE}{citation['keyword_score']:.2f}")
                if citation.get("fused_score") is not None:
                    meta.append(f"{TEXT_FUSED_SCORE}{citation['fused_score']:.4f}")

                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-title">{citation.get("source", "unknown")}</div>
                        <div class="detail-meta">{' | '.join(meta) if meta else TEXT_NO_META}</div>
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
            st.caption(TEXT_NO_ROUTE)

    with detail_tabs[2]:
        summary = latest.get("memory_summary") if latest else None
        if summary:
            st.markdown(
                f"""
                <div class="detail-card">
                    <div class="detail-title">{TEXT_MEMORY_TITLE}</div>
                    <div class="detail-copy">{summary}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.caption(TEXT_NO_MEMORY)


def main() -> None:
    init_state()
    inject_styles()
    backend_ok, backend_payload = check_backend()
    if backend_ok:
        restore_session()

    render_header(backend_ok)

    left_col, right_col = st.columns([0.9, 1.35], gap="large")
    with left_col:
        render_left_panel(backend_ok, backend_payload)
    with right_col:
        render_chat_panel()


main()
