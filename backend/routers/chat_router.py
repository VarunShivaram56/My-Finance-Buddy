from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.models import User
from database.session import get_db
from rag.chatbot_service import ChatbotService
from routers.auth_router import get_current_user


class ChatPayload(BaseModel):
    query: str
    mode: str = "rag"


router = APIRouter()
chatbot_service = ChatbotService()


@router.post("/chat")
def chat(
    payload: ChatPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return chatbot_service.answer(db, current_user, payload.query, payload.mode)
