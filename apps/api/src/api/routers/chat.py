from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.chat.stream import ChatMessage, stream_chat

router = APIRouter(tags=["chat"])


class ChatMessageInput(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessageInput]


@router.post("/chat")
async def chat(body: ChatRequest) -> StreamingResponse:
    """Stream an assistant reply token-by-token (text/plain) over DeepSeek."""
    messages = [ChatMessage(role=m.role, content=m.content) for m in body.messages]
    return StreamingResponse(stream_chat(messages), media_type="text/plain; charset=utf-8")
