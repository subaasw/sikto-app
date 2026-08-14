from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.chat.agent import stream_agent_chat
from api.chat.stream import ChatMessage
from api.db import get_session

router = APIRouter(tags=["chat"])


class ChatMessageInput(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessageInput]
    model: str | None = None


@router.post("/chat")
async def chat(
    body: ChatRequest, session: AsyncSession = Depends(get_session)
) -> StreamingResponse:
    """Stream the assistant's reply (text/plain). The agent can act on the platform —
    create lessons, list them, check job status, and search the user's material."""
    messages = [ChatMessage(role=m.role, content=m.content) for m in body.messages]
    return StreamingResponse(
        stream_agent_chat(messages, session, model=body.model),
        media_type="text/plain; charset=utf-8",
    )
