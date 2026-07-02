from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., description="User question.")
    session_id: str | None = Field(default=None, description="Optional session id.")


class Citation(BaseModel):
    source: str
    snippet: str
    chunk_id: str | None = None
    score: float | None = None
    page: int | None = None
    keyword_score: float | None = None
    fused_score: float | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    route: str = "kb_first"
    matched_chunks: int = 0
    session_id: str | None = None
    memory_summary: str | None = None
    rewritten_question: str | None = None
    rewrite_strategy: str | None = None


class ConversationTurnResponse(BaseModel):
    role: str
    content: str


class SessionResponse(BaseModel):
    session_id: str
    memory_summary: str
    turns: list[ConversationTurnResponse] = Field(default_factory=list)


class IngestResponse(BaseModel):
    status: str
    message: str
    document_id: str
    chunks_indexed: int
    source_path: str
