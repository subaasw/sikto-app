from fastapi import APIRouter
from pydantic import BaseModel

from api.agent.retrieval import EmbeddingRetriever
from api.chat.engine import GroundedChat
from api.knowledge.embeddings import embeddings_client_from_settings
from api.knowledge.vector_store import PgVectorStore
from api.visuals.llm import chat_llm_from_settings

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    question: str


class CitationResponse(BaseModel):
    source_id: str
    content: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]


@router.post("/chat", response_model=ChatResponse)
async def grounded_chat(body: ChatRequest) -> ChatResponse:
    retriever = EmbeddingRetriever(embeddings_client_from_settings(), PgVectorStore())
    chat = GroundedChat(retriever, chat_llm_from_settings())
    result = await chat.answer(body.question)
    return ChatResponse(
        answer=result.answer,
        citations=[
            CitationResponse(source_id=p.source_id, content=p.content, score=p.score)
            for p in result.citations
        ],
    )
