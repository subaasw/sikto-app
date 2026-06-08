from dataclasses import dataclass
from typing import Protocol

from api.agent.retrieval import Retriever
from api.agent.types import Passage

CHAT_SYSTEM = (
    "You are Sikto's study assistant. Answer the question using ONLY the provided source "
    "passages. Cite the sources you use inline as [source <id>]. If the passages do not "
    "contain the answer, say you don't have enough information from the provided sources."
)


@dataclass
class GroundedAnswer:
    answer: str
    citations: list[Passage]


class ChatLLM(Protocol):
    async def complete(self, system: str, user: str) -> str: ...


class GroundedChat:
    """Retrieval-grounded Q&A: retrieve source-attributed passages, then answer using
    only those passages with inline citations."""

    def __init__(self, retriever: Retriever, llm: ChatLLM, *, k: int = 5) -> None:
        self._retriever = retriever
        self._llm = llm
        self._k = k

    async def answer(self, question: str) -> GroundedAnswer:
        passages = await self._retriever.retrieve(question, self._k)
        if passages:
            context = "\n---\n".join(f"[source {p.source_id}] {p.content}" for p in passages)
            user = f"Question: {question}\n\nSource passages:\n{context}"
        else:
            user = f"Question: {question}\n\n(No source passages were found.)"
        answer = await self._llm.complete(CHAT_SYSTEM, user)
        return GroundedAnswer(answer=answer, citations=passages)
