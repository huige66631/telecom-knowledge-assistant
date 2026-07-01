from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse, SessionResponse
from app.services.chat_service import ChatService
from app.services.session_service import SessionService


router = APIRouter(prefix="/chat", tags=["chat"])
chat_service = ChatService()
session_service = SessionService()


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return chat_service.reply(request)


@router.get("/session/{session_id}", response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    return session_service.get_session(session_id)
